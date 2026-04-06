from typing import Any

from src.models.user_profile import UserProfile


class ChatServiceContactResumeService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def get_contact_terminal_or_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """
        联系方式流程结束后的统一出口。
        """
        if self.host._can_end_with_contact_completion(user_profile):
            return self.host._get_contact_completion_ending_response(user_profile)
        if self.host._can_end_without_contact(user_profile):
            return self.host._get_no_contact_completion_response()
        return self.build_post_contact_resume_response(user_profile, user_message)

    def build_post_contact_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        resume_field = str(getattr(user_profile, "resume_profile_target", "") or "").strip()
        if resume_field and not self.host.collection_policy.is_field_covered(user_profile, resume_field):
            prompt = self.host._build_followup_seed_for_model_rewrite(
                resume_field,
                user_profile,
                user_message=user_message,
            ).strip()
            if prompt:
                return prompt

        decision = self.host.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        )
        next_field = decision.main_target
        if next_field and next_field != "contact":
            prompt = self.host._build_followup_seed_for_model_rewrite(
                next_field,
                user_profile,
                user_message=user_message,
            ).strip()
            if prompt:
                return prompt
        unresolved_core_fields = self.host.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core_fields:
            prompt = self.host._build_followup_seed_for_model_rewrite(
                unresolved_core_fields[0],
                user_profile,
                user_message=user_message,
            ).strip()
            if prompt:
                return prompt
        unresolved_medium_fields = self.host.collection_policy.get_uncovered_medium_fields(user_profile)
        if unresolved_medium_fields:
            prompt = self.host._build_followup_seed_for_model_rewrite(
                unresolved_medium_fields[0],
                user_profile,
                user_message=user_message,
            ).strip()
            if prompt:
                return prompt
        return "你继续说，我顺着往下了解。"
