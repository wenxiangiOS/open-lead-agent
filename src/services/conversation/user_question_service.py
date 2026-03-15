"""识别需要优先答疑的用户问题。"""

from __future__ import annotations

import re


class UserQuestionService:
    """判断用户当前是否在表达常见疑问或顾虑。"""

    QUESTION_PATTERNS = (
        r'收费',
        r'怎么收费',
        r'多少钱',
        r'门店',
        r'线下门店',
        r'在哪里',
        r'位置在哪',
        r'怎么匹配',
        r'怎么牵线',
        r'怎么联系',
        r'能加对方微信',
        r'能直接联系',
        r'要对方照片',
        r'发照片',
        r'中介吗',
        r'你们是做什么的',
        r'靠谱吗',
        r'真的假的',
        r'安全吗',
    )

    def is_priority_question(self, text: str) -> bool:
        """命中常见业务疑问时，本轮先答疑。"""
        message = (text or "").strip().lower()
        if not message:
            return False

        return any(re.search(pattern, message) for pattern in self.QUESTION_PATTERNS)
