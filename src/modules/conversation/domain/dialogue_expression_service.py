from __future__ import annotations

import random
from typing import Optional

from src.models.user_profile import UserProfile


class DialogueExpressionService:
    """负责将结构化意图翻译成更自然的人类化表达。"""

    CORE_FIELD_PROMPTS = {
        "sex": (
            "我先问个最基础的，你是男生还是女生？",
            "先简单认识下，你是男生还是女生呀？",
            "方便说下你是男生还是女生吗？",
        ),
        "age": (
            "那你今年大概多大呀？",
            "方便说下你今年多大吗？",
            "你现在大概什么年龄段？",
        ),
        "location": (
            "你现在主要在哪个城市生活？",
            "你平时在哪边生活呀？",
            "你现在是在什么城市？",
        ),
        "education": (
            "你大概是什么学历呀？",
            "方便说下你的学历吗？",
            "你的学历背景大概是怎样的？",
        ),
        "occupation": (
            "你现在主要做哪方面工作呀？",
            "平时是做什么工作的？",
            "工作这块你现在主要在哪个方向？",
        ),
    }

    CONTACT_PROMPTS = (
        "我大概了解你的情况了。后面要是继续聊得合适，留个手机号方便联系吗？",
        "你这边的情况我大概有数了。要是后面继续聊，留个手机号方便联系吗？",
        "整体我这边已经了解得差不多了。要是后面继续聊，留个手机号方便联系你吗？",
    )

    TRANSITION_PREFIXES = {
        "age": ("那", "方便的话"),
        "location": ("那",),
        "education": ("那", "对了"),
        "occupation": ("那", "对了"),
        "contact": ("我大概了解得差不多了", "这样的话"),
    }

    def render_field_question(
        self,
        field: Optional[str],
        *,
        profile: Optional[UserProfile] = None,
        stage: str = "collect",
        user_message: str = "",
    ) -> str:
        if not field:
            return "你继续说，我顺着往下了解。"
        if field == "contact":
            return self.render_contact_question(profile=profile, stage=stage, user_message=user_message)
        if field == "partner_requirement":
            return "你对另一半大概有什么要求呀？比如年龄、城市、性格这些，你会更在意哪方面？"
        if field == "marital_status":
            return "我顺手确认一下，你现在是单身状态吗？"
        if field == "monthly_income":
            return "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？不方便说也没关系。"
        prompts = self.CORE_FIELD_PROMPTS.get(field)
        if not prompts:
            return "你继续说，我顺着往下了解。"
        base = random.choice(prompts)
        return self._maybe_add_transition_prefix(field, base, user_message=user_message)

    def render_contact_question(
        self,
        *,
        profile: Optional[UserProfile] = None,
        stage: str = "collect",
        user_message: str = "",
    ) -> str:
        base = random.choice(self.CONTACT_PROMPTS)
        return self._maybe_add_transition_prefix("contact", base, user_message=user_message)

    def _maybe_add_transition_prefix(self, field: str, base: str, *, user_message: str = "") -> str:
        message = str(user_message or "").strip()
        if not message:
            return base

        short_answer = len(message) <= 8 and not any(token in message for token in ("？", "?", "吗", "怎么", "为什么"))
        if not short_answer:
            return base

        prefixes = self.TRANSITION_PREFIXES.get(field) or ()
        if not prefixes:
            return base
        prefix = random.choice(prefixes)
        if field == "contact":
            if prefix == "我大概了解得差不多了":
                return f"{prefix}。留个手机号方便联系吗？"
            if prefix == "这样的话":
                return f"{prefix}，留个手机号方便联系吗？"
            return base

        if prefix in {"那", "平时的话", "对了", "方便的话"}:
            if prefix == "那":
                return f"{prefix}，{base}"
            if prefix == "方便的话":
                return f"{prefix}，{base}"
            return f"{prefix}，{base}"
        return base
