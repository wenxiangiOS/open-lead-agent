from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.shared.models.chat_flow import ContactDecision, ProfileCollectionResult

if TYPE_CHECKING:
    from src.models.user_profile import UserProfile
    from src.services.core.chat_service import ChatService


class ProfileCollectionCoordinator:
    """Thin orchestration layer around the existing profile collection flow."""

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service

    async def process_collection(
        self,
        account_id: str,
        user_profile: "UserProfile",
        extracted_data: dict,
        user_message: str,
    ) -> ProfileCollectionResult:
        collection_result = await self.chat_service._process_collection_result(  # noqa: SLF001
            account_id,
            user_profile,
            extracted_data,
            user_message,
        )
        refreshed_profile = await self.chat_service.user_service.get_user_profile(account_id)
        policy_decision = self.chat_service.collection_policy.decide(refreshed_profile)
        return ProfileCollectionResult(
            collection_result=collection_result,
            policy_decision=policy_decision,
            user_profile=refreshed_profile,
        )

    def build_contact_decision(self, user_profile: "UserProfile", user_message: str = "") -> ContactDecision:
        next_action = self.chat_service.contact_service.get_next_action(user_profile, user_message)
        prompt_instruction, _ = self.chat_service.contact_service.build_instruction(user_profile, user_message)
        return ContactDecision(
            next_action=next_action.value,
            prompt_instruction=prompt_instruction,
            should_end_conversation=self.chat_service.contact_service.should_end_conversation(user_profile),
            metadata={"next_action_name": next_action.name},
        )
