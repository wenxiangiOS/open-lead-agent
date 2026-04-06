from typing import Any, Dict, Optional


class ChatServicePresetResponseService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def maybe_build_preset_response_payload(
        self,
        *,
        account_id: str,
        user_profile,
        user_message: str,
        dialog_id: str,
        collection_result: Dict[str, Any],
    ) -> Optional[tuple[str, Dict[str, Any]]]:
        preset_response = str(collection_result.get("response") or "").strip()
        if not preset_response:
            return None

        final_response = self.host._sanitize_robotic_tone(
            self.host._legacy_clean_response(preset_response)
        )
        field_ask_count_before = (
            dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}
        )
        await self.host._update_conversation_state(
            account_id,
            user_message,
            final_response,
            final_response,
            track_asked_fields=False,
        )
        refreshed_user_profile = await self.host.user_service.get_user_profile(account_id)
        payload = await self.host._build_chat_response(
            account_id,
            refreshed_user_profile,
            final_response,
            collection_result,
            dialog_id,
            field_ask_count_before,
            response_route="preset_response",
        )
        return final_response, payload
