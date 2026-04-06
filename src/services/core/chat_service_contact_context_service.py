from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile


class ChatServiceContactContextService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def has_active_contact_context(
        self,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> bool:
        result = collection_result or {}
        all_fields = result.get("all_fields", []) or []
        collected_fields = {
            str(item.get("field") or "").strip()
            for item in all_fields
            if isinstance(item, dict)
        }
        ending_info = result.get("ending_info") if isinstance(result, dict) else None
        contact_complete = bool(self.host.contact_service.is_contact_complete(user_profile))
        has_pending_contact_confirmation = any(
            bool(str(getattr(user_profile, attr, "") or "").strip())
            for attr in ("pending_contact_candidate", "pending_contact_field", "pending_contact_hint")
        )
        has_open_contact_request = any(
            [
                bool(
                    user_profile.phone_ask_count > 0
                    and not user_profile.phone_collected
                    and not user_profile.rejected_phone
                    and not getattr(user_profile, "phone_invalid_input_closed", False)
                ),
                bool(
                    user_profile.wechat_ask_count > 0
                    and not user_profile.wechat_collected
                    and not user_profile.rejected_wechat
                    and not getattr(user_profile, "wechat_invalid_input_closed", False)
                ),
                bool(user_profile.rejected_phone and not user_profile.phone_collected),
                bool(user_profile.rejected_wechat and not user_profile.wechat_collected),
                bool(
                    str(getattr(user_profile, "last_contact_request_type", "") or "").strip() == "phone"
                    and not user_profile.phone_collected
                    and not user_profile.rejected_phone
                ),
                bool(
                    str(getattr(user_profile, "last_contact_request_type", "") or "").strip() == "wechat"
                    and not user_profile.wechat_collected
                    and not user_profile.rejected_wechat
                ),
            ]
        )
        has_current_turn_contact_signal = bool({"phone", "contact", "wechat"} & collected_fields) or bool(
            self.host._is_contact_like_user_message(user_message)
        )

        if contact_complete and not any(
            [bool(ending_info), has_pending_contact_confirmation, has_current_turn_contact_signal]
        ):
            return False

        return any(
            [
                bool(ending_info),
                has_pending_contact_confirmation,
                has_open_contact_request,
                has_current_turn_contact_signal,
            ]
        )

    def is_contact_context_active(
        self,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> bool:
        return self.has_active_contact_context(
            user_profile,
            collection_result=collection_result,
            user_message=user_message,
        )
