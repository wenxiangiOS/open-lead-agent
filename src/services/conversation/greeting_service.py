"""
打招呼服务

负责纯问候识别、时间问候纠正和开场快捷回复。
"""

import logging
import random
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GreetingService:
    """管理打招呼相关的识别与回复。"""

    GREETING_RESPONSES: Dict[str, List[str]] = {
        "formal": [
            "你好呀～在的，我可以先快速了解你两三点，也可以先听你说想找什么类型，你更想先聊哪边？",
            "你好呀～我在呢。你是想先说说自己的情况，还是我先问你一两个关键点？",
        ],
        "casual": [
            "哈喽～我在呢。你想先随便聊聊你的情况，还是我先快速问你两三点呀？",
            "嗨～收到。你可以先讲你最在意的点，我再帮你顺着往下聊～",
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
    }

    GREETING_KEYWORDS: Dict[str, List[str]] = {
        "formal": ["你好", "您好"],
        "casual": ["哈喽", "哈罗", "嗨", "hello", "hi", "Hi", "在吗", "在不在"],
        "time_morning": ["早上好", "早安", "上午好"],
        "time_afternoon": ["下午好"],
        "time_evening": ["晚上好"],
    }

    FOLLOWUP_GREETING_RESPONSES: List[str] = [
        "在的呀～你是想先说说你的情况，还是我先帮你快速梳理两三个关键点？",
        "我在呢～你可以先讲你最在意的点，我再顺着帮你往下聊。",
        "在哈～如果你想先自由聊也行，要我先问你一个关键问题也可以。",
    ]

    def detect_greeting_type(self, text: str) -> Optional[str]:
        """检测纯问候类型。"""
        text_stripped = text.strip().lower()
        if len(text_stripped) > 10:
            return None

        normalized_text = re.sub(r"[\s,，。！？!?.～~、：:；;（）()\"'`]+", "", text_stripped)
        if not normalized_text:
            return None

        for greeting_type in ["time_morning", "time_afternoon", "time_evening", "formal", "casual"]:
            keywords = self.GREETING_KEYWORDS.get(greeting_type, [])
            for keyword in keywords:
                if normalized_text == keyword.lower():
                    return greeting_type
        return None

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

    def get_greeting_response(self, text: str) -> str:
        """获取问候回复。"""
        greeting_type = self.detect_greeting_type(text)
        current_period = self.get_current_time_period()

        if greeting_type and greeting_type.startswith("time_"):
            user_period = greeting_type.replace("time_", "")
            if user_period != current_period:
                correction_key = f"{user_period}_to_{current_period}"
                if correction_key in self.TIME_CORRECTION_RESPONSES:
                    logger.info(f"[时间纠正] 用户说{user_period}，实际是{current_period}，使用幽默纠正")
                    return random.choice(self.TIME_CORRECTION_RESPONSES[correction_key])

        if greeting_type and greeting_type in self.GREETING_RESPONSES:
            return random.choice(self.GREETING_RESPONSES[greeting_type])

        return random.choice(self.GREETING_RESPONSES["formal"])

    def get_followup_greeting_response(self, text: str) -> str:
        """获取非首轮寒暄回复。"""
        if self.detect_greeting_type(text):
            return random.choice(self.FOLLOWUP_GREETING_RESPONSES)
        return random.choice(self.GREETING_RESPONSES["casual"])
