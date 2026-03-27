from __future__ import annotations

import re
from typing import Dict, Optional

from src.models.user_profile import UserProfile


class DialogueExpressionService:
    """负责将结构化意图翻译成更自然的人类化表达。"""

    def __init__(self) -> None:
        self._cursor: Dict[str, int] = {}

    CORE_FIELD_PROMPTS = {
        "sex": (
            "先随便聊聊，你这边是男生还是女生呀？",
            "我先认识你一下，你这边是男生还是女生呀？",
            "我先简单了解下，你这边是男生还是女生呀？",
        ),
        "age": (
            "你今年大概多大呀？",
            "方便说下你今年多大吗？",
            "你现在大概什么年龄段？",
        ),
        "location": (
            "你现在主要在哪个城市生活呀？",
            "你平时主要在哪边生活？",
            "你现在是在什么城市生活呀？",
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

    OPENING_INTENT_BRIDGES = (
        "好呀，你也可以先简单介绍下自己，我顺着了解会更自然一点。或者我先问你一个小问题，你这边是男生还是女生呀？",
        "行呀，那我先认识下你。你也可以先简单说说自己，我这边顺着了解会更顺一点；要不我先问你，你这边是男生还是女生呀？",
    )

    CONTACT_PROMPTS = (
        "我大概了解你的情况了。后面要是继续聊得合适，留个手机号方便联系吗？",
        "你这边的情况我大概有数了。要是后面继续聊，留个手机号方便联系吗？",
        "整体我这边已经了解得差不多了。要是后面继续聊，留个手机号方便联系你吗？",
    )

    TRANSITION_PREFIXES = {
        "age": ("好呀", "那我再了解下", "顺着聊到这儿"),
        "location": ("好呀", "那我再问你一个", "顺着聊到这儿"),
        "education": ("好呀", "那我再了解下", "顺着聊到这儿"),
        "occupation": ("好呀", "那我再问你一个", "顺着聊到这儿"),
        "contact": ("我大概了解得差不多了", "这样的话"),
    }

    SENSITIVE_REASON_VARIANTS = {
        "age": (
            "这样我心里会更有数一点。",
            "后面我也更好往合适的方向聊。",
        ),
        "location": (
            "后面我也能优先往同城这边留意。",
            "这样我后面更好先看同城方向。",
        ),
        "education": (
            "这样我对你的情况会更有数一点。",
            "后面我也更好往相对合适的方向帮你看。",
        ),
        "monthly_income": (
            "这样我后面更好往条件相近的方向留意。",
            "我心里也更好有个大概范围。",
        ),
        "marital_status": (
            "这个我先确认清楚，后面聊起来会更顺一点。",
            "这个点先对齐了，后面就不容易聊岔。",
        ),
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
        if field == "sex" and self._looks_like_opening_matchmaking_intent(user_message):
            return self._next_variant("opening:intent_bridge", self.OPENING_INTENT_BRIDGES)
        if field == "partner_requirement":
            return "你对另一半大概有什么要求呀？比如年龄、城市、性格这些，你会更看重哪方面？"
        if field == "marital_status":
            return self._maybe_add_reason(
                "marital_status",
                "我顺手确认一下，你现在是单身状态吗？",
            )
        if field == "monthly_income":
            return self._maybe_add_reason(
                "monthly_income",
                "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？不方便说也没关系。",
            )
        prompts = self.CORE_FIELD_PROMPTS.get(field)
        if not prompts:
            return "你继续说，我顺着往下了解。"
        if field == "occupation":
            contextual_occupation = self._build_contextual_occupation_prompt(user_message)
            if contextual_occupation:
                return contextual_occupation
        base = self._next_variant(f"core:{field}", prompts)
        base = self._maybe_add_reason(field, base)
        return self._maybe_add_transition_prefix(field, base, user_message=user_message)

    def render_contact_question(
        self,
        *,
        profile: Optional[UserProfile] = None,
        stage: str = "collect",
        user_message: str = "",
    ) -> str:
        base = self._next_variant("contact", self.CONTACT_PROMPTS)
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
        prefix = self._next_variant(f"prefix:{field}", prefixes)
        if field == "contact":
            if prefix == "我大概了解得差不多了":
                return f"{prefix}。留个手机号方便联系吗？"
            if prefix == "这样的话":
                return f"{prefix}，留个手机号方便联系吗？"
            return base

        if prefix in {"好呀", "那我再了解下", "顺着聊到这儿", "那我再问你一个"}:
            return f"{prefix}，{base}"
        return base

    def _maybe_add_reason(self, field: str, base: str) -> str:
        variants = self.SENSITIVE_REASON_VARIANTS.get(field) or ()
        if not variants:
            return base
        idx = self._cursor.get(f"reason:{field}", 0)
        self._cursor[f"reason:{field}"] = idx + 1
        # 控制解释出现频率：年龄/城市更低频，其他敏感字段适中。
        modulo = 5 if field in {"age", "location"} else 3
        if idx % modulo != 0:
            return base
        reason = variants[idx % len(variants)]
        if "？" in base:
            return base.replace("？", f"？{reason}")
        return f"{base} {reason}"

    def _next_variant(self, key: str, candidates: tuple[str, ...]) -> str:
        if not candidates:
            return ""
        idx = self._cursor.get(key, 0) % len(candidates)
        self._cursor[key] = idx + 1
        return candidates[idx]

    @staticmethod
    def _looks_like_opening_matchmaking_intent(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        if not re.search(r"(找对象|想找对象|帮我找个对象|相亲|脱单|找另一半|找个男朋友|找个女朋友|认真聊聊)", message):
            return False
        if re.search(r"(男生|男的|女生|女的|90后|\d{2}岁|深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|本科|硕士|博士|it|运营|程序员|单身|离异)", message.lower()):
            return False
        return True

    @staticmethod
    def _build_contextual_occupation_prompt(user_message: str) -> Optional[str]:
        message = str(user_message or "").strip()
        if not message:
            return None
        city_match = re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", message)
        if not city_match:
            return None
        city = city_match.group(1)
        return f"在{city}这边是吧。你平时也是在{city}工作吗，主要做什么呀？"
