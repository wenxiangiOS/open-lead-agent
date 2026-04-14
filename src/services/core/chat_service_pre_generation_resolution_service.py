import logging
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from src.core.exceptions import AIServiceException
from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import (
    ResolvedFieldEvidence,
    SlotCandidate,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.slot_governance_rules import (
    message_has_explicit_age_semantics,
)
from src.modules.conversation_understanding.domain.models import FieldObservation


logger = logging.getLogger(__name__)


def _is_affirmative_confirmation_answer(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
            r"(?:[呀呢啊哦哈啦嘛]*)?"
            r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
            str(text or ""),
        )
    )


class ChatServicePreGenerationResolutionService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def resolve_state_before_generation(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        last_response: str,
        understanding: TurnUnderstandingResult,
    ) -> None:
        self._resolve_income_unit_clarification_from_context(
            user_profile=user_profile,
            user_message=user_message,
            last_response=last_response,
            understanding=understanding,
        )
        self._backfill_birth_year_confirmation_from_compound_message(
            user_profile=user_profile,
            user_message=user_message,
            last_response=last_response,
            understanding=understanding,
        )
        self._backfill_understanding_from_contextual_short_reply(
            user_profile=user_profile,
            user_message=user_message,
            last_response=last_response,
            understanding=understanding,
        )
        self._resolve_divorce_confirmation_state(
            user_profile=user_profile,
            user_message=user_message,
            last_response=last_response,
            understanding=understanding,
        )

    async def maybe_build_resolution_short_circuit_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        turn_understanding: TurnUnderstandingResult,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], UserProfile]:
        stable_self_age = await self._resolve_short_circuit_self_age(
            user_message=user_message,
            understanding=turn_understanding,
        )
        if stable_self_age is not None and stable_self_age < 24:
            user_profile.age = stable_self_age
            user_profile.age_under_limit = True
            user_profile.conversation_ended = True
            await self.host.user_service.save_user_profile(account_id, user_profile)
            final_response = self.host._sanitize_robotic_tone(
                self.host.ending_service.get_ending_response("age_under_limit") or ""
            )
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": [], "ending_info": {"scenario": "age_under_limit"}},
                dialog_id=dialog_id,
                response_route="age_under_limit",
            )
            return "age_under_limit", payload, user_profile
        if user_profile.conversation_ended and "离异（手续未办妥）" in str(getattr(user_profile, "marital_status", "") or ""):
            final_response = self.host._sanitize_robotic_tone(
                self.host.ending_service.get_ending_response("divorce_incomplete") or ""
            )
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": [], "ending_info": {"scenario": "divorce_incomplete"}},
                dialog_id=dialog_id,
                response_route="divorce_incomplete",
            )
            return "divorce_incomplete", payload, user_profile
        return None, None, user_profile

    async def _resolve_short_circuit_self_age(
        self,
        *,
        user_message: str,
        understanding: TurnUnderstandingResult,
    ) -> Optional[int]:
        resolved_slots = self._effective_resolved_slots(understanding)
        resolved_age = str(resolved_slots.get("age") or "").strip() or None
        stable_self_age, numeric_analysis = self.host.extraction_service.resolve_stable_self_age(
            user_message=user_message,
            resolved_age=resolved_age,
        )
        if stable_self_age is None:
            return None
        if stable_self_age >= 24:
            return stable_self_age
        if not bool((numeric_analysis or {}).get("has_multiple_age_roles")):
            return stable_self_age
        reviewed_age = await self._review_high_risk_age_conflict_with_ai(
            user_message=user_message,
            stable_self_age=stable_self_age,
            numeric_analysis=numeric_analysis,
        )
        return reviewed_age

    async def _review_high_risk_age_conflict_with_ai(
        self,
        *,
        user_message: str,
        stable_self_age: int,
        numeric_analysis: Dict[str, Any],
    ) -> Optional[int]:
        ai_service = getattr(self.host, "ai_service", None)
        if ai_service is None:
            logger.info("[高风险年龄复核] ai_service 不可用，跳过短路")
            return None

        system_prompt = (
            "你是一个高风险年龄语义复核器。"
            "请只输出一行 JSON，不要输出解释。"
            '格式：{"self_age":36,"partner_age_gap":3,"allow_age_under_limit":false}'
        )
        prompt = (
            f"用户原句：{str(user_message or '').strip() or '-'}\n"
            f"统一理解链当前本人年龄：{stable_self_age}\n"
            f"数字语义分析：{json.dumps(numeric_analysis, ensure_ascii=False)}\n"
            "任务：判断用户本人年龄是多少；如果句中出现择偶年龄差/范围，也要区分出来；"
            "只有在能明确确认用户本人年龄小于24岁时，allow_age_under_limit 才能为 true。"
        )
        try:
            raw = await ai_service.generate_response(
                prompt,
                system_prompt,
                temperature=0.0,
                max_tokens=80,
                timeout=self._resolve_high_risk_age_review_timeout(),
            )
        except AIServiceException as exc:
            logger.warning("[高风险年龄复核] AI 复核失败，跳过短路: %s", exc)
            return None

        parsed = self._parse_json_payload(raw)
        if not parsed:
            logger.warning("[高风险年龄复核] AI 返回无法解析，跳过短路: %s", raw)
            return None

        allow = bool(parsed.get("allow_age_under_limit"))
        reviewed_age = self.host.extraction_service._parse_age(parsed.get("self_age"))  # noqa: SLF001
        if allow and reviewed_age is not None and reviewed_age < 24:
            logger.info("[高风险年龄复核] AI 确认用户年龄=%s，允许 age_under_limit", reviewed_age)
            return reviewed_age
        logger.info("[高风险年龄复核] AI 未确认低龄，跳过短路")
        return None

    @staticmethod
    def _resolve_high_risk_age_review_timeout() -> float:
        try:
            timeout = float(os.getenv("HIGH_RISK_AGE_REVIEW_TIMEOUT_SECONDS", "8"))
        except (TypeError, ValueError):
            timeout = 8.0
        return max(1.0, timeout)

    @staticmethod
    def _parse_json_payload(raw: str) -> Optional[Dict[str, Any]]:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _resolve_divorce_confirmation_state(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        last_response: str,
        understanding: TurnUnderstandingResult,
    ) -> None:
        if bool(getattr(user_profile, "divorce_confirmation_pending", False)) and self.host._is_divorce_confirmation_question(
            last_response
        ):
            if self.host._is_divorce_status_complete_message(user_message) or _is_affirmative_confirmation_answer(user_message):
                user_profile.marital_status = "离异（手续已办妥）"
                user_profile.divorce_confirmed = True
                user_profile.divorce_confirmation_pending = False
                user_profile.collection_progress["marital_status"] = True
                self._set_transition_reason(understanding, "resume_after_divorce_confirmation_complete")
                logger.info("[离异手续已办妥-生成前] 用户说: %s，生成前恢复资料主线", user_message)
                return
            if self.host._is_divorce_status_incomplete_message(user_message) or (
                self.host._is_short_negative_reply(user_message)
                and self.host._is_divorce_confirmation_question(last_response)
            ):
                user_profile.marital_status = "离异（手续未办妥）"
                user_profile.divorce_confirmed = False
                user_profile.divorce_confirmation_pending = False
                user_profile.conversation_ended = True
                user_profile.collection_progress["marital_status"] = True
                self._set_transition_reason(understanding, "end_after_divorce_confirmation_incomplete")
                logger.info("[离异手续未办妥-生成前] 用户说: %s，生成前进入结束态", user_message)
                return

        marital_status = str(self._effective_resolved_slots(understanding).get("marital_status") or "").strip()
        if "离异" not in marital_status:
            return
        if "办妥" in marital_status or bool(getattr(user_profile, "divorce_confirmed", False)):
            return
        if self.host._is_divorce_status_complete_message(user_message) or self.host._is_divorce_status_incomplete_message(
            user_message
        ):
            return
        if not bool(getattr(user_profile, "divorce_confirmation_pending", False)):
            logger.info("[离异手续待确认-生成前] 用户说: %s，生成前锁定本轮只确认手续", user_message)
        user_profile.divorce_confirmation_pending = True
        self._set_transition_reason(understanding, "lock_divorce_confirmation")

    def _backfill_understanding_from_contextual_short_reply(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        last_response: str,
        understanding: TurnUnderstandingResult,
    ) -> None:
        if self._effective_resolved_slots(understanding):
            return
        if (
            understanding.primary_turn_type != "invalid_input"
            and self._has_existing_semantic_progress(understanding)
        ):
            return
        if (
            understanding.primary_turn_type != "invalid_input"
            and self.host.turn_understanding_service._looks_like_short_ack_message(user_message)  # noqa: SLF001
        ):
            return

        compact_message = re.sub(r"\s+", "", str(user_message or ""))
        in_contact_like_context = (
            understanding.primary_turn_type == "contact_answer"
            or understanding.subtype == "contact_context_reply"
            or self.host.contact_context_service.has_active_contact_context(
                user_profile,
                user_message=user_message,
            )
        )
        looks_like_numeric_contact_attempt = bool(re.fullmatch(r"(?:\+?86)?[\d\s-]{7,17}", compact_message))
        if (
            in_contact_like_context
            and looks_like_numeric_contact_attempt
            and not message_has_explicit_age_semantics(user_message)
        ):
            return

        deterministic = self.host.turn_understanding_service._extract_deterministic_profile_fields(user_message)  # noqa: SLF001
        extracted = self.host.turn_understanding_service._apply_extraction_guards(  # noqa: SLF001
            deterministic,
            user_message,
            last_response=last_response,
        )
        asked_fields = self._resolve_context_asked_fields(last_response=last_response)
        extracted = self._filter_contextual_backfill_fields(
            extracted=extracted,
            user_message=user_message,
            asked_fields=asked_fields,
        )
        if not extracted:
            return

        for field, value in extracted.items():
            self._upsert_understanding_field(
                understanding=understanding,
                field_name=field,
                value=value,
                source_text=str(user_message or ""),
                confidence=0.88,
            )
            if field in understanding.slot_candidates:
                continue
            understanding.slot_candidates[field] = SlotCandidate(
                value=str(value),
                confidence=0.88,
                source="pre_generation_resolution",
                source_text=str(user_message or ""),
            )
        if understanding.primary_turn_type == "invalid_input":
            understanding.primary_turn_type = "profile_answer"
            understanding.subtype = "multi_slot_compound" if len(extracted) >= 2 else "single_slot_answer"
            understanding.confidence = max(float(understanding.confidence or 0.0), 0.88)
        self._set_resolution_meta(
            understanding,
            source="contextual_short_reply_backfill",
            resolved_fields=sorted(extracted.keys()),
            default_transition_reason="contextual_short_reply_backfill",
        )
        understanding.notes.append("pre_generation_contextual_short_reply_backfill")
        logger.info(
            "[生成前补识别] 用户说: %s，补回字段=%s，turn=%s/%s",
            user_message,
            sorted(extracted.keys()),
            understanding.primary_turn_type,
            understanding.subtype or "-",
        )

    def _backfill_birth_year_confirmation_from_compound_message(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        last_response: str,
        understanding: TurnUnderstandingResult,
    ) -> None:
        """待确认出生年场景下，即使本轮已有其他语义进展，也补提取具体出生年。"""
        pending_bucket = str(getattr(user_profile, "pending_birth_year_bucket", "") or "").strip()
        if not pending_bucket or getattr(user_profile, "birth_year_confirmation_closed", False):
            return

        effective = self._effective_resolved_slots(understanding)
        if "age" in effective and "age_label" in effective:
            return

        service = self.host.turn_understanding_service
        asked_field_detector = getattr(service, "_detect_which_field_is_asked", None)  # noqa: SLF001
        asked_field = ""
        if callable(asked_field_detector):
            try:
                asked_field = str(asked_field_detector(str(last_response or "")) or "").strip()
            except Exception:  # noqa: BLE001
                asked_field = ""
        is_age_prompt_context = bool(
            asked_field == "age"
            or self.host._is_birth_year_bucket_question(last_response)  # noqa: SLF001
        )

        explicit_age_answer = False
        explicit_checker = getattr(service, "_message_explicitly_answers_field", None)  # noqa: SLF001
        if callable(explicit_checker):
            try:
                explicit_age_answer = bool(explicit_checker("age", str(user_message or "")))
            except Exception:  # noqa: BLE001
                explicit_age_answer = False
        if not (is_age_prompt_context or explicit_age_answer):
            return

        deterministic = service._extract_deterministic_profile_fields(user_message)  # noqa: SLF001
        extracted = service._apply_extraction_guards(  # noqa: SLF001
            deterministic,
            user_message,
            last_response=last_response,
        )
        age_value = str((extracted or {}).get("age") or "").strip()
        age_label = str((extracted or {}).get("age_label") or "").strip()

        if not age_value:
            contextual_age_parser = getattr(service, "_extract_age_answer_from_age_question", None)  # noqa: SLF001
            if callable(contextual_age_parser) and is_age_prompt_context:
                try:
                    parsed = contextual_age_parser(str(user_message or ""))
                except Exception:  # noqa: BLE001
                    parsed = None
                if parsed is not None:
                    age_value, age_label = str(parsed[0] or "").strip(), str(parsed[1] or "").strip()

        if not age_value.isdigit():
            return
        age_int = int(age_value)
        if age_int < 18 or age_int > 100:
            return
        if not age_label:
            year_match = re.search(r"(?<!\d)(19\d{2}|20\d{2}|\d{2})年(?:的)?(?:出生)?", str(user_message or ""))
            if year_match:
                age_label = f"{year_match.group(1)}年"

        self._upsert_understanding_field(
            understanding=understanding,
            field_name="age",
            value=str(age_int),
            source_text=str(user_message or ""),
            confidence=0.92,
            source_type="semantic_explicit_self_marker",
            source_label="pre_generation_birth_year_confirmation",
        )
        understanding.slot_candidates["age"] = SlotCandidate(
            value=str(age_int),
            confidence=0.92,
            source="pre_generation_birth_year_confirmation",
            source_text=str(user_message or ""),
        )
        resolved_fields = ["age"]

        if age_label:
            self._upsert_understanding_field(
                understanding=understanding,
                field_name="age_label",
                value=age_label,
                source_text=str(user_message or ""),
                confidence=0.92,
                source_type="semantic_explicit_self_marker",
                source_label="pre_generation_birth_year_confirmation",
            )
            understanding.slot_candidates["age_label"] = SlotCandidate(
                value=age_label,
                confidence=0.92,
                source="pre_generation_birth_year_confirmation",
                source_text=str(user_message or ""),
            )
            resolved_fields.append("age_label")

        if understanding.primary_turn_type == "invalid_input":
            understanding.primary_turn_type = "profile_answer"
            understanding.subtype = "multi_slot_compound" if len(self._effective_resolved_slots(understanding)) >= 2 else "single_slot_answer"
            understanding.confidence = max(float(understanding.confidence or 0.0), 0.9)

        self._set_resolution_meta(
            understanding,
            source="birth_year_confirmation_backfill",
            resolved_fields=resolved_fields,
            default_transition_reason="birth_year_confirmation_backfill",
        )
        understanding.notes.append("pre_generation_birth_year_confirmation_backfill")
        logger.info(
            "[生成前补识别] 出生年确认补回: user_message=%s resolved=%s turn=%s/%s",
            user_message,
            resolved_fields,
            understanding.primary_turn_type,
            understanding.subtype or "-",
        )

    def _resolve_context_asked_fields(self, *, last_response: str) -> set[str]:
        detector = getattr(self.host.turn_understanding_service, "_detect_asked_fields_from_context", None)  # noqa: SLF001
        if not callable(detector):
            return set()
        try:
            fields = set(detector(str(last_response or "")))
        except Exception:  # noqa: BLE001
            return set()
        if "age" in fields:
            fields.add("age_label")
        return {str(field or "").strip() for field in fields if str(field or "").strip()}

    def _filter_contextual_backfill_fields(
        self,
        *,
        extracted: Dict[str, str],
        user_message: str,
        asked_fields: set[str],
    ) -> Dict[str, str]:
        if not extracted:
            return {}

        message = str(user_message or "").strip()
        service = self.host.turn_understanding_service
        filtered: Dict[str, str] = {}

        for field, value in dict(extracted or {}).items():
            field_name = str(field or "").strip()
            if not field_name:
                continue

            if field_name in asked_fields:
                filtered[field_name] = value
                continue

            explicitly_answers_field = False
            checker = getattr(service, "_message_explicitly_answers_field", None)  # noqa: SLF001
            if callable(checker):
                try:
                    explicitly_answers_field = bool(checker(field_name, message))
                except Exception:  # noqa: BLE001
                    explicitly_answers_field = False
            if explicitly_answers_field:
                filtered[field_name] = value
                continue

            if field_name == "occupation":
                explicit_self_occupation = False
                self_occupation_detector = getattr(service, "_has_explicit_self_occupation_signal", None)  # noqa: SLF001
                if callable(self_occupation_detector):
                    try:
                        explicit_self_occupation = bool(self_occupation_detector(message))
                    except Exception:  # noqa: BLE001
                        explicit_self_occupation = False
                if explicit_self_occupation:
                    filtered[field_name] = value
                continue

        if "age_label" in filtered and "age" not in filtered and "age" in dict(extracted or {}):
            filtered["age"] = dict(extracted or {}).get("age")
        if "age" in filtered and "age_label" not in filtered and "age_label" in dict(extracted or {}):
            filtered["age_label"] = dict(extracted or {}).get("age_label")
        return filtered

    @staticmethod
    def _has_existing_semantic_progress(understanding: TurnUnderstandingResult) -> bool:
        persistence_plan = getattr(understanding, "persistence_plan", None)
        if persistence_plan is None:
            return False
        return any(
            list(getattr(persistence_plan, attr, []) or [])
            for attr in ("accepted_fields", "provisional_fields", "pending_fields", "rejected_fields")
        )

    def _resolve_income_unit_clarification_from_context(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        last_response: str,
        understanding: TurnUnderstandingResult,
    ) -> None:
        service = self.host.turn_understanding_service
        clarification = service._extract_income_unit_clarification(user_message)  # noqa: SLF001
        if not clarification:
            return

        asked_field = service._detect_which_field_is_asked(last_response)  # noqa: SLF001
        current_income = str(getattr(user_profile, "monthly_income", "") or "").strip()
        if asked_field != "monthly_income" and not current_income:
            return

        merged_income = service._merge_income_value_and_unit(current_income, clarification)  # noqa: SLF001
        if not merged_income:
            return

        self._remove_understanding_field(understanding=understanding, field_name="occupation")
        understanding.slot_candidates.pop("occupation", None)
        self._upsert_understanding_field(
            understanding=understanding,
            field_name="monthly_income",
            value=merged_income,
            source_text=str(user_message or ""),
            confidence=0.9,
        )
        understanding.slot_candidates["monthly_income"] = SlotCandidate(
            value=str(merged_income),
            confidence=0.9,
            source="pre_generation_resolution",
            source_text=str(user_message or ""),
        )
        understanding.primary_turn_type = "profile_answer"
        understanding.subtype = "single_slot_answer"
        understanding.confidence = max(float(understanding.confidence or 0.0), 0.9)
        self._set_resolution_meta(
            understanding,
            source="income_unit_clarification",
            resolved_fields=["monthly_income"],
            default_transition_reason="income_unit_clarification",
        )
        understanding.notes.append("pre_generation_income_unit_clarification")
        logger.info(
            "[生成前补识别] 收入单位澄清命中: user_message=%s current=%s merged=%s",
            user_message,
            current_income or "-",
            merged_income,
        )

    @staticmethod
    def _set_transition_reason(understanding: TurnUnderstandingResult, reason: str) -> None:
        understanding.set_pre_generation_transition_reason(reason)

    @staticmethod
    def _set_resolution_meta(
        understanding: TurnUnderstandingResult,
        *,
        source: str,
        resolved_fields: list[str],
        default_transition_reason: str,
    ) -> None:
        understanding.set_pre_generation_resolution(
            source=source,
            resolved_fields=resolved_fields,
            default_transition_reason=default_transition_reason,
        )

    @staticmethod
    def _upsert_understanding_field(
        *,
        understanding: TurnUnderstandingResult,
        field_name: str,
        value: Any,
        source_text: str,
        confidence: float,
        source_type: str = "pre_generation_resolution",
        source_label: str = "pre_generation_resolution",
    ) -> None:
        normalized_value = str(value)
        understanding.resolved_slots[field_name] = normalized_value
        scope = ChatServicePreGenerationResolutionService._infer_field_scope(field_name)
        understanding.resolved_field_evidence[field_name] = ResolvedFieldEvidence(
            field=field_name,
            value=normalized_value,
            scope=scope,
            source_span=normalized_value,
            source_text=source_text,
            confidence=confidence,
            source_type=source_type,
        )

        semantic_frame = getattr(understanding, "semantic_frame", None)
        if semantic_frame is not None:
            observations = list(getattr(semantic_frame, "field_observations", []) or [])
            observations = [
                item
                for item in observations
                if str(getattr(item, "field", "") or "").strip() != field_name
            ]
            observations.append(
                FieldObservation(
                    field=field_name,
                    value=value,
                    normalized_value=value,
                    scope=scope,
                    owner="self" if scope in {"self", "contact"} else scope,
                    evidence_text=source_text,
                    evidence_span=str(value),
                    confidence=confidence,
                    write_mode="direct_write",
                    source=source_label,
                )
            )
            semantic_frame.field_observations = observations

    @staticmethod
    def _remove_understanding_field(
        *,
        understanding: TurnUnderstandingResult,
        field_name: str,
    ) -> None:
        understanding.resolved_slots.pop(field_name, None)

        semantic_frame = getattr(understanding, "semantic_frame", None)
        if semantic_frame is not None:
            semantic_frame.field_observations = [
                item
                for item in list(getattr(semantic_frame, "field_observations", []) or [])
                if str(getattr(item, "field", "") or "").strip() != field_name
            ]

    @staticmethod
    def _infer_field_scope(field_name: str) -> str:
        if field_name in {"phone", "wechat", "contact"}:
            return "contact"
        if field_name.startswith("partner_") or field_name == "partner_requirement":
            return "partner"
        return "self"

    @staticmethod
    def _effective_resolved_slots(understanding: TurnUnderstandingResult) -> Dict[str, str]:
        resolved_slots: Dict[str, str] = dict(getattr(understanding, "resolved_slots", {}) or {})
        persistence_plan = getattr(understanding, "persistence_plan", None)
        if persistence_plan is None:
            return resolved_slots
        for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(field, "field", "") or "").strip()
            scope = str(getattr(field, "scope", "") or "").strip()
            if not field_name or scope not in {"self", "contact", "partner"}:
                continue
            resolved_slots[field_name] = str(getattr(field, "normalized_value", "") or "")
        return resolved_slots
