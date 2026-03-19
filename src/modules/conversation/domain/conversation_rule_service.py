from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.modules.conversation.domain.conversation_rules import (
    CompletedCollectionAffirmativeRule,
    ContactFlowAffirmativeRule,
    ConversationEndedRule,
    ConversationRule,
    ConversationRuleContext,
    GreetingRule,
    MatchingTimelineRule,
    NonsenseInputRule,
    SeparationStatusRule,
    UnclearInputRule,
)
from src.modules.shared.models.chat_flow import RuleCheckResult

if TYPE_CHECKING:
    from src.models.requests import ChatRequest
    from src.models.user_profile import UserProfile
    from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)


class ConversationRuleService:
    """Centralizes early-return conversation rules without changing their semantics."""

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service
        self.rules: list[ConversationRule] = [
            ConversationEndedRule(),
            CompletedCollectionAffirmativeRule(),
            ContactFlowAffirmativeRule(),
            MatchingTimelineRule(),
            UnclearInputRule(),
            SeparationStatusRule(),
            NonsenseInputRule(),
            GreetingRule(),
        ]

    async def try_handle(
        self,
        request: "ChatRequest",
        user_profile: "UserProfile",
        *,
        is_first_user_turn: bool,
        message_count: int,
    ) -> RuleCheckResult:
        ctx = ConversationRuleContext(
            chat_service=self.chat_service,
            request=request,
            user_profile=user_profile,
            is_first_user_turn=is_first_user_turn,
            message_count=message_count,
        )
        for rule in self.rules:
            result = await rule.apply(ctx)
            if result.handled:
                return result
        return RuleCheckResult(handled=False)
