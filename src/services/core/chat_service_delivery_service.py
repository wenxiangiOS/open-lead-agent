from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision


class ChatServiceDeliveryService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def build_enhanced_response_to_clean(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        collection_result: Dict[str, Any],
        ai_response: str,
    ) -> str:
        all_fields = list((collection_result or {}).get("all_fields") or [])
        has_contact_field = any(
            isinstance(field_info, dict)
            and str(field_info.get("field") or "").strip() in {"contact", "phone", "wechat"}
            and str(field_info.get("value") or "").strip()
            for field_info in all_fields
        )
        if has_contact_field:
            return await self.host._handle_contact_validation(
                account_id,
                user_profile,
                collection_result,
                ai_response,
                user_message,
            )
        return ai_response

    async def sync_post_delivery_state(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        ai_response: str,
        delivery_ok: bool,
        turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
        message_count: int,
        previous_asked_field: Optional[str],
        previous_asked_side_field: Optional[str] = None,
    ) -> tuple[str, UserProfile]:
        if not delivery_ok:
            await self.host.dialogue_manager.add_to_history(account_id, "user", user_message)
            await self.host.dialogue_manager.increment_message_count(account_id)
            user_profile = await self.host.user_service.get_user_profile(account_id)
            user_profile = await self.host._update_progress_runtime_counters(
                account_id,
                user_profile,
                user_message=user_message,
                collection_result=collection_result,
                turn_decision=turn_decision,
                message_count=message_count,
                previous_asked_field=previous_asked_field,
                previous_asked_side_field=previous_asked_side_field,
            )
            return "", user_profile

        should_track_asked_fields = (
            delivery_ok
            and not turn_decision.prioritize_user_question
            and turn_decision.primary_move
            not in {"answer_then_pause", "repair_and_release", "soft_hold", "ack_only", "confirm_status_only"}
        )
        await self.host._update_conversation_state(
            account_id,
            user_message,
            final_response,
            ai_response,
            turn_decision=turn_decision,
            track_asked_fields=should_track_asked_fields,
        )
        user_profile = await self.host.user_service.get_user_profile(account_id)
        user_profile = await self.host._update_progress_runtime_counters(
            account_id,
            user_profile,
            user_message=user_message,
            collection_result=collection_result,
            turn_decision=turn_decision,
            message_count=message_count,
            previous_asked_field=previous_asked_field,
            previous_asked_side_field=previous_asked_side_field,
        )
        if user_profile.repair_mode and user_profile.ask_cooldown_turns > 0:
            user_profile.decrement_cooldown()
            await self.host.user_service.save_user_profile(account_id, user_profile)
        return final_response, user_profile

    async def build_final_turn_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        final_response: str,
        collection_result: Dict[str, Any],
        dialog_id: str,
        route_name: str,
        infra_fail: bool = False,
        infra_fail_reason: str = "",
    ) -> Dict[str, Any]:
        payload = await self.host._build_chat_response(
            account_id,
            user_profile,
            final_response,
            collection_result,
            dialog_id,
            dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
            response_route=route_name if route_name != "model" else None,
        )
        if infra_fail:
            payload["meta"] = {
                "infra_fail": True,
                "infra_fail_reason": infra_fail_reason,
            }
        validation_meta = getattr(self.host, "_last_validation_feedback_meta", None)
        if validation_meta:
            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            meta["validation"] = dict(validation_meta)
            payload["meta"] = meta
        unified_meta = getattr(self.host, "_last_unified_generation_record", None)
        if unified_meta:
            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            meta["ai_response_unified_generation"] = dict(unified_meta)
            payload["meta"] = meta
        payload["response"] = final_response
        return payload
