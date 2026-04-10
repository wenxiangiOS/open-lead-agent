import logging
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from src.core.exceptions import AIServiceException
from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import (
    SlotCandidate,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.slot_governance_rules import (
    message_has_explicit_age_semantics,
)


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
        resolved_age = str((understanding.resolved_slots or {}).get("age") or "").strip() or None
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

        marital_status = str((understanding.resolved_slots or {}).get("marital_status") or "").strip()
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
        if (understanding.resolved_slots or {}):
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
        if not extracted:
            return

        understanding.resolved_slots.update(extracted)
        for field, value in extracted.items():
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
