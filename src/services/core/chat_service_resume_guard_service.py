from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile
from src.services.core.chat_service_contact_resume_service import (
    ChatServiceContactResumeService,
)


class ChatServiceResumeGuardService:
    def __init__(self, host: Any) -> None:
        self.host = host
        self.contact_resume_service = ChatServiceContactResumeService(host)

    def enforce_divorce_cleared_resume_policy(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        if not text:
            return text
        if not (collection_result or {}).get("divorce_confirmation_cleared"):
            return text

        next_field = self.host._get_post_divorce_mainline_target(user_profile, user_message)
        ack = self.host._build_divorce_confirmation_cleared_response(next_field).strip()
        if next_field and next_field != "contact":
            followup = self.host._build_followup_seed_for_model_rewrite(
                next_field,
                user_profile,
                user_message=user_message,
            ).strip()
            if followup:
                return f"{ack} {followup}".strip()
        return ack or text

    def enforce_contact_resume_after_completion(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        if not text or user_profile.conversation_ended:
            return text
        if not self.host.contact_service.is_contact_complete(user_profile):
            return text
        if self.host._can_end_with_contact_completion(user_profile) or self.host._can_end_without_contact(user_profile):
            return text
        if not (
            self.host._contains_contact_push_markers(text)
            or "联系方式" in text
            or "电话这块" in text
            or "微信这块" in text
        ):
            return text
        return self.contact_resume_service.build_post_contact_resume_response(user_profile, user_message)

    def enforce_resume_profile_collection_policy(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        if not text:
            return text
        if not self.host._is_resume_profile_collection_message(user_message):
            return text

        if self.host._has_remaining_profile_fields(user_profile):
            if self.host._contains_contact_push_markers(text):
                decision = self.host.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=False,
                    allow_medium_target=True,
                    prioritize_user_question=False,
                    primary_move="light_followup",
                )
                next_field = decision.main_target
                if next_field and next_field != "contact":
                    followup = self.host._build_followup_seed_for_model_rewrite(
                        next_field,
                        user_profile,
                        user_message=user_message,
                    ).strip()
                    if followup:
                        return followup
            return text

        if self.host.collection_policy.can_enter_contact(user_profile) and self.host._contains_contact_push_markers(text):
            return "你的基本情况我这边已经了解得差不多了，现在主要差一个后面方便联系到你的方式。"
        return text
