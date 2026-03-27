"""
打招呼服务

负责纯问候识别、时间问候纠正和开场快捷回复。
"""

import logging
import hashlib
import random
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GreetingService:
    """管理打招呼相关的识别与回复。"""

    def __init__(self) -> None:
        # Keep a lightweight in-process cursor so greeting templates rotate
        # instead of repeatedly hitting the same sentence.
        self._response_cursor: Dict[str, int] = {}

    GREETING_RESPONSES: Dict[str, List[str]] = {
        "formal": [
            "你好呀，我在呢。你这边是想找对象，还是先了解下呀？",
            "你好呀，在的。你是想认真聊聊，还是先问问情况呀？",
        ],
        "casual": [
            "在呢，你这边是想找对象，还是先了解下呀？",
            "在呀，你是想先看看情况，还是已经准备认真聊聊了？",
        ],
        "time_morning": [
            "早上好呀～我在呢。你想先说说你想找什么类型，还是我先快速了解你两三点？",
            "早安～今天我们可以轻松聊，你想先讲你的期待，还是我先问一个小问题？",
        ],
        "time_afternoon": [
            "下午好呀～我在。你想先说说自己的情况，还是我先问你一两个关键点呀？",
            "下午好～可以先随便聊聊你的想法，我再帮你整理成合适的方向～",
        ],
        "time_evening": [
            "晚上好呀～我在呢。你想先聊你的择偶想法，还是我先快速了解你两三点？",
            "晚上好～别有压力，你先说你最在意的一点，我来帮你往下推进～",
        ],
        "light_consult": [
            "可以呀，你这边是想找对象，还是先了解下这边怎么聊的？",
            "当然可以，你是想先看看情况，还是已经准备认真聊聊了？",
        ],
    }

    TIME_CORRECTION_RESPONSES: Dict[str, List[str]] = {
        "morning_to_afternoon": [
            "哈哈，现在已经是下午啦～下午好呀～是帮自己找对象吗？",
            "哎呀，现在下午了呢～下午好呀～有什么可以帮您的吗？",
        ],
        "morning_to_evening": [
            "哈哈，现在已经是晚上啦～晚上好呀～是帮自己找对象吗？",
            "哎呀，现在晚上了呢～晚上好呀～有什么可以帮您的吗？",
        ],
        "afternoon_to_morning": [
            "哈哈，现在还是上午呢～早上好呀～是帮自己找对象吗？",
            "哎呀，现在是上午哦～早上好呀～有什么可以帮您的吗？",
        ],
        "afternoon_to_evening": [
            "哈哈，现在已经是晚上啦～晚上好呀～是帮自己找对象吗？",
            "哎呀，现在晚上了呢～晚上好呀～有什么可以帮您的吗？",
        ],
        "evening_to_morning": [
            "哈哈，现在还是早上呢～早上好呀～你这边是想找对象，还是先了解下呀？",
            "哎呀，现在还是上午哦～早上好呀～你是想先看看情况，还是认真聊聊呀？",
        ],
        "evening_to_afternoon": [
            "哈哈，现在已经下午啦～下午好呀～你这边是想找对象，还是先了解下呀？",
            "哎呀，现在是下午呢～下午好呀～你是想先看看情况，还是认真聊聊呀？",
        ],
    }

    GREETING_KEYWORDS: Dict[str, List[str]] = {
        "formal": ["你好", "您好"],
        "casual": [
            "哈喽", "哈罗", "嗨", "hello", "hi", "Hi", "hey",
            "在吗", "在不在", "有人吗", "有人在吗", "有空吗", "方便聊吗", "可以聊吗", "能聊聊吗",
        ],
        "time_morning": ["早上好", "早安", "上午好", "早啊"],
        "time_afternoon": ["下午好"],
        "time_evening": ["晚上好", "晚安"],
        "light_consult": ["想了解下", "想了解一下", "了解一下", "先咨询下", "咨询一下", "看看情况", "想问一下"],
    }

    FOLLOWUP_GREETING_RESPONSES: List[str] = [
        "在呢，你是想先看看情况，还是想直接聊你的想法呀？",
        "我在呢，你可以先说你想了解什么，我顺着跟你聊。",
        "在呀，你想先随便聊聊，还是我先问你一个关键点？",
    ]

    OPEN_SELF_INTRO_RESPONSES: List[str] = [
        "好呀，你也可以先简单介绍下自己，我顺着了解会更自然一点。",
        "行呀，那你可以先简单说说自己，我顺着了解会更顺一点。",
        "好，那你先简单讲讲你现在的大概情况，我顺着了解。",
    ]

    OPENING_CLARIFY_RESPONSES: List[str] = [
        "我这句有点没看懂，你是想找对象，还是先了解下呀？",
        "刚刚这句我没太接住，你是想找对象，还是先看看情况呀？",
        "你刚刚这句我有点没看明白，你是想找对象，还是先问问情况呀？",
        "我这句有点没反应过来，你是想找对象，还是先问问情况呀？",
    ]

    def detect_greeting_type(self, text: str) -> Optional[str]:
        """检测纯问候类型。"""
        text_stripped = text.strip().lower()
        if len(text_stripped) > 10:
            return None

        split_parts = [
            part
            for part in re.split(r"[\s,，。！？!?.～~、：:；;（）()\"'`]+", text_stripped)
            if part
        ]
        split_match = self._detect_greeting_type_from_parts(split_parts)
        if split_match:
            return split_match

        normalized_text = re.sub(r"[\s,，。！？!?.～~、：:；;（）()\"'`]+", "", text_stripped)
        if not normalized_text:
            return None

        return self._detect_greeting_type_from_normalized(normalized_text)

    def is_greeting(self, text: str) -> bool:
        """判断是否为纯问候。"""
        return self.detect_greeting_type(text) is not None

    def get_current_time_period(self) -> str:
        """获取当前时间段。"""
        from datetime import datetime

        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 18:
            return "afternoon"
        return "evening"

    def get_greeting_response(self, text: str, seed_hint: str | None = None) -> str:
        """获取问候回复。"""
        greeting_type = self.detect_greeting_type(text)
        current_period = self.get_current_time_period()

        if greeting_type and greeting_type.startswith("time_"):
            user_period = greeting_type.replace("time_", "")
            if user_period != current_period:
                correction_key = f"{user_period}_to_{current_period}"
                if correction_key in self.TIME_CORRECTION_RESPONSES:
                    logger.info(f"[时间纠正] 用户说{user_period}，实际是{current_period}，使用幽默纠正")
                    return self._pick_response(
                        key=f"time_correction:{correction_key}",
                        candidates=self.TIME_CORRECTION_RESPONSES[correction_key],
                        seed_hint=seed_hint,
                    )

        if greeting_type and greeting_type in self.GREETING_RESPONSES:
            return self._pick_response(
                key=f"greeting:{greeting_type}",
                candidates=self.GREETING_RESPONSES[greeting_type],
                seed_hint=seed_hint,
            )

        return self._pick_response(
            key="greeting:formal",
            candidates=self.GREETING_RESPONSES["formal"],
            seed_hint=seed_hint,
        )

    def get_followup_greeting_response(self, text: str, seed_hint: str | None = None) -> str:
        """获取非首轮寒暄回复。"""
        if self.detect_greeting_type(text):
            return self._pick_response(
                key="followup:greeting",
                candidates=self.FOLLOWUP_GREETING_RESPONSES,
                seed_hint=seed_hint,
            )
        return self._pick_response(
            key="greeting:casual",
            candidates=self.GREETING_RESPONSES["casual"],
            seed_hint=seed_hint,
        )

    def get_open_self_intro_response(self, seed_hint: str | None = None) -> str:
        """获取明确找对象意图后的开放自述入口回复。"""
        return self._pick_response(
            key="opening:self_intro",
            candidates=self.OPEN_SELF_INTRO_RESPONSES,
            seed_hint=seed_hint,
        )

    def get_opening_clarify_response(self, seed_hint: str | None = None) -> str:
        """获取首轮无法稳定理解时的轻澄清回复。"""
        return self._pick_response(
            key="opening:clarify",
            candidates=self.OPENING_CLARIFY_RESPONSES,
            seed_hint=seed_hint,
        )

    def _pick_response(self, key: str, candidates: List[str], seed_hint: str | None = None) -> str:
        """Pick a seeded response when possible, otherwise fall back to cursor rotation."""
        if seed_hint:
            return self._seeded_response(key, candidates, seed_hint)
        return self._next_response(key, candidates)

    def _detect_greeting_type_from_parts(self, parts: List[str]) -> Optional[str]:
        if not parts:
            return None
        matched_types: List[str] = []
        for part in parts:
            matched = self._detect_single_greeting_type(part)
            if not matched:
                return None
            matched_types.append(matched)
        return self._merge_greeting_types(matched_types)

    def _detect_greeting_type_from_normalized(self, normalized_text: str) -> Optional[str]:
        single_match = self._detect_single_greeting_type(normalized_text)
        if single_match:
            return single_match

        tokens = self._segment_greeting_tokens(normalized_text)
        if not tokens:
            return None
        token_types = [self._detect_single_greeting_type(token) for token in tokens]
        if any(token_type is None for token_type in token_types):
            return None
        return self._merge_greeting_types([token_type for token_type in token_types if token_type])

    def _detect_single_greeting_type(self, text: str) -> Optional[str]:
        for greeting_type in ["time_morning", "time_afternoon", "time_evening", "formal", "casual", "light_consult"]:
            keywords = self.GREETING_KEYWORDS.get(greeting_type, [])
            for keyword in keywords:
                if text == keyword.lower():
                    return greeting_type
        return None

    def _segment_greeting_tokens(self, normalized_text: str) -> Optional[List[str]]:
        all_keywords = sorted(
            {keyword.lower() for keywords in self.GREETING_KEYWORDS.values() for keyword in keywords},
            key=len,
            reverse=True,
        )
        index = 0
        tokens: List[str] = []
        while index < len(normalized_text):
            matched = None
            for keyword in all_keywords:
                if normalized_text.startswith(keyword, index):
                    matched = keyword
                    break
            if matched is None:
                return None
            tokens.append(matched)
            index += len(matched)
        return tokens

    @staticmethod
    def _merge_greeting_types(greeting_types: List[str]) -> Optional[str]:
        if not greeting_types:
            return None
        for greeting_type in ["time_morning", "time_afternoon", "time_evening"]:
            if greeting_type in greeting_types:
                return greeting_type
        if "light_consult" in greeting_types:
            return "light_consult"
        if "formal" in greeting_types:
            return "formal"
        if "casual" in greeting_types:
            return "casual"
        return None

    def _seeded_response(self, key: str, candidates: List[str], seed_hint: str) -> str:
        """Return a stable but non-fixed template based on a seed."""
        if not candidates:
            return ""
        digest = hashlib.sha1(f"{key}:{seed_hint}".encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(candidates)
        return candidates[idx]

    def _next_response(self, key: str, candidates: List[str]) -> str:
        """Return a rotating template to avoid repeated fixed phrasing."""
        if not candidates:
            return ""
        idx = self._response_cursor.get(key, 0) % len(candidates)
        self._response_cursor[key] = (idx + 1) % len(candidates)
        return candidates[idx]
