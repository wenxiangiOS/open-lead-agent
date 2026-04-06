from typing import Any

from src.models.user_profile import UserProfile


class ChatServiceEndingStateService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def has_any_contact(user_profile: UserProfile) -> bool:
        return bool(
            (user_profile.phone_collected and user_profile.phone)
            or (user_profile.wechat_collected and user_profile.wechat)
            or user_profile.collection_progress.get("contact", False)
        )

    def is_profile_collection_complete_or_exhausted(self, user_profile: UserProfile) -> bool:
        if self._has_pending_resume_profile_target(user_profile):
            return False
        return self.host.collection_policy.is_coverage_complete(user_profile)

    def can_end_with_contact_completion(self, user_profile: UserProfile) -> bool:
        if self._has_pending_resume_profile_target(user_profile):
            return False
        return (
            self.has_any_contact(user_profile)
            and self.host.contact_service.is_contact_complete(user_profile)
            and self.is_profile_collection_complete_or_exhausted(user_profile)
        )

    def can_end_without_contact(self, user_profile: UserProfile) -> bool:
        if self._has_pending_resume_profile_target(user_profile):
            return False
        return (
            not self.has_any_contact(user_profile)
            and self.host.contact_service.is_contact_complete(user_profile)
        )

    def _has_pending_resume_profile_target(self, user_profile: UserProfile) -> bool:
        field = str(getattr(user_profile, "resume_profile_target", "") or "").strip()
        if not field:
            return False
        return not self.host.collection_policy.is_field_covered(user_profile, field)

    @staticmethod
    def get_no_contact_completion_response() -> str:
        return "这边就先不往下追着问啦，后面你要是方便，再来找我聊就行。"

    def get_contact_completion_ending_response(self, user_profile: UserProfile) -> str:
        if not self.has_any_contact(user_profile):
            return self.get_no_contact_completion_response()
        return self.host.expectation_service.get_contact_completion_response(user_profile)

    def get_already_ended_response(self) -> str:
        return self.host.ending_service.get_ending_response("already_ended") or ""

    def get_both_rejected_ending_response(self) -> str:
        return self.host.ending_service.get_ending_response("both_rejected") or ""
