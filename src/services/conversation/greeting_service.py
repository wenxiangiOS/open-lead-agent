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
            "你好呀～有什么可以帮您的吗？",
            "你好呀～是帮自己找对象吗？",
        ],
        "casual": [
            "哈喽～你也在深圳吗？",
            "哈喽～有什么可以帮您的吗？",
        ],
        "time_morning": [
            "早上好呀～有什么可以帮您的吗？",
            "早安～是帮自己找对象吗？",
        ],
        "time_afternoon": [
            "下午好呀～有什么可以帮您的吗？",
            "下午好～是帮自己找对象吗？",
        ],
        "time_evening": [
            "晚上好呀～有什么可以帮您的吗？",
            "晚上好～是帮自己找对象吗？",
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
