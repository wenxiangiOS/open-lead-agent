import re
from typing import Any, Dict, Optional

from src.utils.validators import PhoneValidator, WechatValidator


class ChatServiceCollectionExtractionService:
    _HIGH_RISK_FIELDS = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
    _SAME_NUMBER_CONTACT_PATTERNS = (
        r"(?:微信|wx|vx).*(?:同号|一个号|一样|同一个)",
        r"(?:跟|和)?(?:电话|手机号|号码).*(?:一样|同号|同一个号)",
        r"(?:电话|手机号|号码).*(?:也可以加|也能加|也可以搜到|也能搜到|可以搜到|能搜到)",
        r"(?:电话|号码)也可以(?:当|做)?微信",
        r"(?:号码|电话)(?:也)?可以搜微信",
    )

    def __init__(self, host: Any) -> None:
        self.host = host

    async def run_extraction(
        self,
        *,
        account_id: str,
        user_profile,
        extracted_data: Dict[str, Any],
        user_message: str,
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
        turn_id: Optional[int] = None,
        understanding_result: Any = None,
    ) -> tuple[str, Dict[str, Any], Any]:
        last_response = await self.host.dialogue_manager.get_last_response(account_id) or ""
        collection_result = await self._apply_authoritative_persistence_plan(
            account_id=account_id,
            user_profile=user_profile,
            understanding_result=understanding_result,
            turn_id=turn_id,
        )
        if collection_result is not None:
            refreshed_user_profile = await self.host.user_service.get_user_profile(account_id)
            return last_response, collection_result, refreshed_user_profile

        guarded_extracted_data = self.host.turn_understanding_service._apply_extraction_guards(  # noqa: SLF001
            extracted_data,
            user_message,
            last_response=last_response,
        )
        guarded_extracted_data, extraction_meta = self._merge_persistence_plan_accepted_fields(
            extracted_data=guarded_extracted_data,
            extraction_meta=extraction_meta,
            understanding_result=understanding_result,
            user_profile=user_profile,
        )
        collection_result = await self.host.extraction_service.process_extracted_data(
            account_id,
            user_profile,
            guarded_extracted_data,
            user_message=user_message,
            last_response=last_response,
            extraction_meta=extraction_meta,
            turn_id=turn_id,
        )
        refreshed_user_profile = await self.host.user_service.get_user_profile(account_id)
        return last_response, collection_result, refreshed_user_profile

    async def _apply_authoritative_persistence_plan(
        self,
        *,
        account_id: str,
        user_profile: Any,
        understanding_result: Any,
        turn_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        persistence_plan = getattr(understanding_result, "persistence_plan", None)
        if persistence_plan is None:
            return None
        if self._cas_guard_blocked(persistence_plan=persistence_plan, user_profile=user_profile):
            return None

        accepted_fields = self._authoritative_plan_fields(persistence_plan)
        if not accepted_fields:
            return None

        collected_fields: list[Dict[str, Any]] = []
        invalid_contact_attempt = None
        accepted_field_names = {
            str(getattr(field, "field", "") or "").strip()
            for field in accepted_fields
            if str(getattr(field, "field", "") or "").strip()
        }

        for field in accepted_fields:
            field_name = str(getattr(field, "field", "") or "").strip()
            if not field_name:
                continue
            value = getattr(field, "normalized_value", None)
            routed_field, routed_value, invalid_candidate = self._normalize_plan_field(field_name=field_name, value=value)
            if invalid_candidate is not None:
                invalid_contact_attempt = invalid_candidate
                continue
            if not routed_field:
                continue
            if routed_field == "wechat":
                is_valid_wechat, _ = WechatValidator.is_valid(str(routed_value or "").strip())
                if not is_valid_wechat and not self._allows_same_number_wechat_from_plan(
                    field=field,
                    routed_value=routed_value,
                ):
                    invalid_contact_attempt = str(routed_value or "").strip()
                    continue

            current_value = getattr(user_profile, routed_field, None) if hasattr(user_profile, routed_field) else None
            success = await self.host.user_service.update_user_profile_field(account_id, routed_field, routed_value)
            if not success:
                continue

            user_profile = await self.host.user_service.get_user_profile(account_id)
            final_value = getattr(user_profile, routed_field, routed_value)
            if self._is_effectively_same_value(current_value, final_value):
                continue

            collected_fields.append({"field": routed_field, "value": final_value})
            user_profile.set_extraction_evidence(
                field_name=routed_field,
                value=final_value,
                source_text=str(getattr(field, "evidence_text", "") or final_value or ""),
                turn_id=turn_id,
                confidence=float(getattr(field, "confidence", 0.0) or 0.0),
                source=f"persistence_plan:{str(getattr(field, 'source_channel', 'unknown') or 'unknown').strip()}",
                reason=str(getattr(field, "acceptance_reason", "") or "").strip() or None,
            )
            await self.host.user_service.save_user_profile(account_id, user_profile)

            if routed_field == "age" and "age_label" not in accepted_field_names:
                derived_age_label = self._derive_age_label_from_value(
                    value=getattr(field, "evidence_text", None) or value
                )
                if derived_age_label:
                    previous_age_label = getattr(user_profile, "age_label", None)
                    age_label_updated = await self.host.user_service.update_user_profile_field(
                        account_id,
                        "age_label",
                        derived_age_label,
                    )
                    if age_label_updated:
                        user_profile = await self.host.user_service.get_user_profile(account_id)
                        final_age_label = getattr(user_profile, "age_label", derived_age_label)
                        if not self._is_effectively_same_value(previous_age_label, final_age_label):
                            collected_fields.append({"field": "age_label", "value": final_age_label})
                            user_profile.set_extraction_evidence(
                                field_name="age_label",
                                value=final_age_label,
                                source_text=str(getattr(field, "evidence_text", "") or derived_age_label),
                                turn_id=turn_id,
                                confidence=float(getattr(field, "confidence", 0.0) or 0.0),
                                source=f"persistence_plan:{str(getattr(field, 'source_channel', 'unknown') or 'unknown').strip()}",
                                reason="derived_age_label_from_authoritative_age",
                            )
                            await self.host.user_service.save_user_profile(account_id, user_profile)

        if collected_fields:
            await self.host.user_service.save_user_profile(account_id, user_profile)
            return {
                "collected": True,
                "field": collected_fields[0]["field"],
                "value": collected_fields[0]["value"],
                "all_fields": collected_fields,
            }

        result = {"collected": False, "all_fields": []}
        if invalid_contact_attempt:
            result["invalid_contact_attempt"] = invalid_contact_attempt
        return result

    @classmethod
    def _authoritative_plan_fields(cls, persistence_plan: Any) -> list[Any]:
        authoritative_fields: list[Any] = []
        for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(field, "field", "") or "").strip()
            scope = str(getattr(field, "scope", "") or "").strip()
            persistence_state = str(getattr(field, "persistence_state", "committed") or "committed").strip()
            source_channel = str(getattr(field, "source_channel", "unknown") or "unknown").strip()
            if not field_name or scope not in {"self", "contact", "partner"} or persistence_state != "committed":
                continue
            if source_channel not in {"ai", "hybrid", "fallback"}:
                continue
            if field_name in cls._HIGH_RISK_FIELDS and not cls._allows_high_risk_field_from_plan(field):
                continue
            authoritative_fields.append(field)
        return authoritative_fields

    @staticmethod
    def _normalize_plan_field(*, field_name: str, value: Any) -> tuple[str | None, Any, str | None]:
        if field_name == "contact":
            raw_contact = str(value or "").strip()
            digits_only = "".join(ch for ch in raw_contact if ch.isdigit())
            if digits_only.startswith("86") and len(digits_only) == 13 and digits_only[2] == "1":
                digits_only = digits_only[2:]
            is_valid_phone, _ = PhoneValidator.is_valid(digits_only)
            if is_valid_phone:
                return "phone", digits_only, None
            wechat_candidate = re.sub(
                r"^(?:微信号?|weixin|vx|wx)\s*[:：]\s*",
                "",
                raw_contact,
                flags=re.IGNORECASE,
            ).strip()
            is_valid_wechat, _ = WechatValidator.is_valid(wechat_candidate)
            if is_valid_wechat:
                return "wechat", wechat_candidate, None
            return None, None, raw_contact
        return field_name, value, None

    @staticmethod
    def _derive_age_label_from_value(*, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        suffix_match = re.search(r"(\d{2})后", text)
        if suffix_match:
            return f"{suffix_match.group(1)}后"
        year_match = re.search(r"((?:19\d{2}|20\d{2})年(?:的)?|(?:\d{2})年(?:的)?)", text)
        if year_match:
            canonical = str(year_match.group(1) or "").strip()
            return canonical[:-1] if canonical.endswith("的") else canonical
        year_suffix_match = re.search(r"(?<!\d)(\d{2})的(?!\d)", text)
        if year_suffix_match:
            return f"{year_suffix_match.group(1)}年"
        return ""

    @staticmethod
    def _is_effectively_same_value(current_value: Any, new_value: Any) -> bool:
        current_text = str(current_value).strip() if current_value not in (None, "", [], {}, ()) else ""
        new_text = str(new_value).strip() if new_value not in (None, "", [], {}, ()) else ""
        if not current_text and not new_text:
            return True
        return bool(current_text and new_text and current_text == new_text)

    @classmethod
    def _allows_same_number_wechat_from_plan(
        cls,
        *,
        field: Any,
        routed_value: Any,
    ) -> bool:
        candidate = str(routed_value or "").strip()
        if not candidate or not candidate.isdigit():
            return False

        is_valid_phone, _ = PhoneValidator.is_valid(candidate)
        if not is_valid_phone:
            return False

        evidence_text = str(getattr(field, "evidence_text", "") or "").strip()
        compact_evidence = re.sub(r"\s+", "", evidence_text)
        return any(re.search(pattern, compact_evidence) for pattern in cls._SAME_NUMBER_CONTACT_PATTERNS)

    @staticmethod
    def _merge_persistence_plan_accepted_fields(
        *,
        extracted_data: Dict[str, Any],
        extraction_meta: Optional[Dict[str, Dict[str, Any]]],
        understanding_result: Any,
        user_profile: Any = None,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        persistence_plan = getattr(understanding_result, "persistence_plan", None)
        if persistence_plan is None:
            return dict(extracted_data or {}), dict(extraction_meta or {})

        merged_data = dict(extracted_data or {})
        merged_meta = dict(extraction_meta or {})
        if ChatServiceCollectionExtractionService._cas_guard_blocked(
            persistence_plan=persistence_plan,
            user_profile=user_profile,
        ):
            blocked_fields = [
                str(getattr(field, "field", "") or "").strip()
                for field in list(getattr(persistence_plan, "accepted_fields", []) or [])
                if str(getattr(field, "field", "") or "").strip()
            ]
            merged_meta["__persistence_plan_guard__"] = {
                "source": "persistence_plan_cas_guard",
                "reason": "profile_version_mismatch",
                "blocked_fields": blocked_fields,
            }
            return merged_data, merged_meta

        committed_high_risk_fields = {
            str(getattr(field, "field", "") or "").strip()
            for field in list(getattr(persistence_plan, "accepted_fields", []) or [])
            if str(getattr(field, "field", "") or "").strip() in ChatServiceCollectionExtractionService._HIGH_RISK_FIELDS
            and str(getattr(field, "persistence_state", "committed") or "committed").strip() == "committed"
            and ChatServiceCollectionExtractionService._allows_high_risk_field_from_plan(field)
        }
        # 高风险字段只允许由 committed + ai 的 persistence plan 进入主档，避免 response extract 脏写。
        for field_name in list(ChatServiceCollectionExtractionService._HIGH_RISK_FIELDS):
            if field_name in committed_high_risk_fields:
                continue
            if ChatServiceCollectionExtractionService._allows_high_risk_field_from_merged_meta(
                field_name=field_name,
                field_value=merged_data.get(field_name),
                field_meta=merged_meta.get(field_name),
            ):
                continue
            merged_data.pop(field_name, None)
            merged_meta.pop(field_name, None)

        for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(field, "field", "") or "").strip()
            scope = str(getattr(field, "scope", "") or "").strip()
            persistence_state = str(getattr(field, "persistence_state", "committed") or "committed").strip()
            if not field_name or scope not in {"self", "contact", "partner"} or persistence_state != "committed":
                continue
            if (
                field_name in ChatServiceCollectionExtractionService._HIGH_RISK_FIELDS
                and not ChatServiceCollectionExtractionService._allows_high_risk_field_from_plan(field)
            ):
                continue
            source_channel = str(getattr(field, "source_channel", "unknown") or "unknown").strip()
            merged_data[field_name] = getattr(field, "normalized_value", None)
            merged_meta[field_name] = {
                "source": "persistence_plan_acceptance",
                "confidence": float(getattr(field, "confidence", 0.0) or 0.0),
                "scope": scope,
                "source_text": str(getattr(field, "evidence_text", "") or ""),
                "persistence_state": persistence_state,
                "source_channel": source_channel,
                "field_version": int(getattr(field, "field_version", 1) or 1),
            }

        return merged_data, merged_meta

    @staticmethod
    def _cas_guard_blocked(*, persistence_plan: Any, user_profile: Any) -> bool:
        if persistence_plan is None or user_profile is None:
            return False
        expected_version_raw = getattr(persistence_plan, "expected_profile_version", None)
        if expected_version_raw is not None:
            try:
                expected_version = int(expected_version_raw)
                current_version = int(getattr(user_profile, "profile_version", expected_version))
                if current_version != expected_version:
                    return True
                return False
            except (TypeError, ValueError):
                pass
        expected = str(getattr(persistence_plan, "expected_profile_updated_at", "") or "").strip()
        if not expected:
            return False
        current_raw = getattr(user_profile, "updated_at", None)
        if current_raw is None:
            return False
        current = str(current_raw.isoformat()) if hasattr(current_raw, "isoformat") else str(current_raw)
        return bool(current and current != expected)

    @staticmethod
    def _allows_high_risk_field_from_plan(field: Any) -> bool:
        source_channel = str(getattr(field, "source_channel", "unknown") or "unknown").strip()
        if source_channel == "ai":
            return True
        field_name = str(getattr(field, "field", "") or "").strip()
        acceptance_reason = str(getattr(field, "acceptance_reason", "") or "").strip()
        if field_name in {"sex", "age", "occupation", "monthly_income"} and acceptance_reason == "explicit_self_marker":
            return True
        if field_name == "partner_requirement" and acceptance_reason == "explicit_partner_marker":
            return True
        return False

    @staticmethod
    def _allows_high_risk_field_from_merged_meta(
        *,
        field_name: str,
        field_value: Any,
        field_meta: Any,
    ) -> bool:
        if field_name != "age":
            return False
        if not isinstance(field_meta, dict):
            return False
        source = str(field_meta.get("source", "") or "").strip()
        if source not in {"semantic_explicit_self_marker", "understanding:semantic_explicit_self_marker"}:
            return False
        age_text = str(field_value or "").strip()
        if not age_text.isdigit():
            return False
        age_value = int(age_text)
        if age_value < 18 or age_value > 100:
            return False
        source_text = str(field_meta.get("source_text", "") or "")
        return bool(re.search(r"(\d{1,2}岁|(?:19|20)\d{2}年|\d{2}后|\d{2}年)", source_text))
