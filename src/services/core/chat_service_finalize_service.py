from typing import Any, Dict

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService


class ChatServiceFinalizeService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def finalize_generated_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
        response_to_clean: str,
        ai_response: str,
        bridge_prefix: str,
        contact_gate_before: bool,
        message_count: int,
    ) -> tuple[str, bool, UserProfile]:
        invalid_contact_feedback = await self._maybe_override_invalid_contact_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            collection_result=collection_result,
        )
        if invalid_contact_feedback is not None:
            refreshed_profile = await self.host.user_service.get_user_profile(account_id)
            return invalid_contact_feedback, bool(str(invalid_contact_feedback).strip()), refreshed_profile

        return await self._finalize_unified_raw_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            response_to_clean=response_to_clean,
            ai_response=ai_response,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            collection_result=collection_result,
        )

    async def _maybe_override_invalid_contact_feedback(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
    ) -> str | None:
        invalid_value = str(collection_result.get("invalid_contact_attempt") or "").strip()
        if not invalid_value:
            return None

        collected_fields = collection_result.get("all_fields", []) or []
        has_valid_contact_field = any(
            str(field_info.get("field") or "").strip() in {"phone", "wechat", "contact"}
            and str(field_info.get("value") or "").strip()
            for field_info in collected_fields
            if isinstance(field_info, dict)
        )
        if has_valid_contact_field:
            return None

        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        primary_turn_type = str(getattr(turn_understanding, "primary_turn_type", "") or "").strip()
        subtype = str(getattr(turn_understanding, "subtype", "") or "").strip()
        in_contact_context = (
            ask_field == "contact"
            or primary_turn_type == "contact_answer"
            or subtype == "contact_context_reply"
            or self.host.contact_context_service.is_contact_context_active(user_profile)
        )
        if not in_contact_context:
            return None

        field = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
        if field not in {"phone", "wechat"}:
            field = "phone"

        return await self.host._build_validation_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info={
                "code": "CONTACT_INVALID_FORMAT",
                "field": field,
                "detail": "invalid_format",
                "silent": False,
            },
        )

    async def _finalize_unified_raw_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        response_to_clean: str,
        ai_response: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
    ) -> tuple[str, bool, UserProfile]:
        raw_response = str(ai_response or "")
        draft = self.host.unified_response_draft_service.build(raw_ai_response=raw_response)
        validation_result = self.host.unified_response_validation_service.validate(
            raw_ai_response=draft.raw_ai_response,
            infra_fail=not bool(str(ai_response or "").strip()) and bool(getattr(self.host, "_last_ai_failure_reason", None)),
            infra_fail_reason=getattr(self.host, "_last_ai_failure_reason", "") or "",
        )

        display_text, removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
            draft.raw_ai_response
        )
        rewritten_text, rewritten_removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
            response_to_clean
        )
        if rewritten_text:
            display_text = rewritten_text
            removed_blocks = list(dict.fromkeys([*removed_blocks, *rewritten_removed_blocks]))
        delivery = self.host.unified_response_delivery_service.deliver(
            draft=draft,
            validation_result=validation_result,
            cleaned_response=display_text,
            safe_cleaned=True,
            fallback_response="",
        )
        final_response = str(delivery.display_response or "").strip()
        final_response = self.host._enforce_question_budget_guard(
            final_response,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
        )
        final_response = self.host._downgrade_premature_profile_summary(
            final_response,
            user_profile,
            collection_result=collection_result,
            ask_field=str(getattr(turn_decision, "ask_field", "") or "").strip(),
        )
        final_response = await self._maybe_repair_contact_completion_ending(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            collection_result=collection_result,
        )
        final_response = self._maybe_enforce_main_followup_alignment(
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            turn_decision=turn_decision,
        )
        delivery_ok = bool(final_response)
        final_response = self._maybe_enforce_contact_followup_response(
            user_profile=user_profile,
            final_response=final_response,
            user_message=user_message,
        )
        delivery_ok = bool(final_response)
        if delivery_ok:
            user_profile = await self.host._record_delivered_contact_ask_if_needed(
                account_id,
                user_profile,
                user_message,
                final_response,
            )

        record = self.host.unified_response_observability_service.build_record(
            draft=draft,
            delivery=delivery,
            validation_result=validation_result,
            cleaned_response=display_text,
        )
        record["technical_blocks_removed"] = removed_blocks
        record["first_generation_only"] = True
        self.host._last_unified_generation_record = record
        self.host.unified_response_observability_service.log(
            account_id=account_id,
            record=self.host._last_unified_generation_record,
        )
        return final_response, delivery_ok, user_profile

    def _maybe_enforce_contact_followup_response(
        self,
        *,
        user_profile: UserProfile,
        final_response: str,
        user_message: str,
    ) -> str:
        text = str(final_response or "").strip()
        if not text:
            return text
        if not getattr(user_profile, "phone_collected", False) or not getattr(user_profile, "phone", None):
            return text
        if getattr(user_profile, "wechat_collected", False) or getattr(user_profile, "rejected_wechat", False):
            return text

        try:
            next_action = self.host.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value not in {"ask_wechat", "persuade_wechat"}:
            return text
        if ChatServiceContactTextService.response_mentions_wechat_request(text):
            return text

        return ChatServiceContactTextService.build_contact_followup_response(action_value, "phone")

    def _maybe_enforce_main_followup_alignment(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        turn_decision: TurnDecision,
    ) -> str:
        text = str(final_response or "").strip()
        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        if not text or not ask_field or ask_field == "contact":
            return text

        asked_fields = self.host._detect_asked_fields_in_response(text) | self.host._detect_all_questioned_fields_in_response(text)
        if not asked_fields:
            return text
        if ask_field in asked_fields:
            return text

        fallback = self.host._build_budget_guard_fallback_response(
            user_profile=user_profile,
            user_message=user_message,
            ask_field=ask_field,
            allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False)),
        )
        return str(fallback or text).strip()

    async def _maybe_repair_contact_completion_ending(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        collection_result: Dict[str, Any],
    ) -> str:
        text = str(final_response or "").strip()
        ending_info = dict(collection_result.get("ending_info") or {})
        scenario = str(ending_info.get("scenario") or "").strip()
        if scenario != "normal_complete":
            return text
        if not self.host._can_end_with_contact_completion(user_profile):
            return text

        expected_timeline = self.host.expectation_service.get_closing_timeline_text(user_profile)
        normalized = self.host.preparation_service._normalize_compact_text(text) if text else ""
        has_expected_timeline = expected_timeline in text
        contains_question = "？" in text or "?" in text
        banned_markers = (
            "我都记清楚",
            "记清楚啦",
            "我再跟你同步",
            "再跟你同步",
            "有合适的人选",
            "后面有合适的人选",
            "我记下了",
            "我记下来",
        )
        looks_like_valid_ending = (
            bool(text)
            and not contains_question
            and has_expected_timeline
            and "提前约时间" in text
            and "不打扰你" in text
            and ("等好消息" in text or "好消息" in text)
            and "祝你早日脱单" in text
            and not any(marker in text for marker in banned_markers)
        )
        if looks_like_valid_ending:
            return text

        fallback = self.host._get_contact_completion_ending_response(user_profile)
        regenerated = await self.host._generate_ai_ending_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            ending_info=ending_info,
            fallback_response=fallback,
        )
        regenerated = str(regenerated or "").strip()
        if not regenerated:
            return fallback

        regenerated_has_expected_timeline = expected_timeline in regenerated
        regenerated_contains_question = "？" in regenerated or "?" in regenerated
        regenerated_valid = (
            not regenerated_contains_question
            and regenerated_has_expected_timeline
            and "提前约时间" in regenerated
            and "不打扰你" in regenerated
            and ("等好消息" in regenerated or "好消息" in regenerated)
            and "祝你早日脱单" in regenerated
            and not any(marker in regenerated for marker in banned_markers)
        )
        return regenerated if regenerated_valid else fallback
