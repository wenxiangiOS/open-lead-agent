from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from src.modules.shared.models.chat_flow import RuleCheckResult


@dataclass
class ConversationRuleService:
    """兼容旧链路的规则服务壳层。

    现在主流程已由 ProcessChatTurnUseCase 接管，这里只保留最小能力：
    允许测试或旧调用方注入 rule objects，并按顺序执行，返回第一个 handled 结果。
    """

    chat_service: Any
    rules: List[Any] = field(default_factory=list)

    async def try_handle(
        self,
        request: Any,
        user_profile: Any,
        *,
        is_first_user_turn: bool = False,
        message_count: int = 0,
    ) -> RuleCheckResult:
        context = {
            "request": request,
            "user_profile": user_profile,
            "is_first_user_turn": is_first_user_turn,
            "message_count": message_count,
        }
        for rule in self.rules:
            result = await rule.apply(context)
            if result and getattr(result, "handled", False):
                return result
        return RuleCheckResult(handled=False)
