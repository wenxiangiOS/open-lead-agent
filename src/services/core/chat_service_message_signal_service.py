import re
from typing import Any, Optional

from src.models.user_profile import UserProfile


class ChatServiceMessageSignalService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def is_withdraw_or_stop_message(self, user_message: str) -> bool:
        return self.host._classify_withdraw_intent(user_message) is not None

    @staticmethod
    def is_resume_profile_collection_message(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        from src.services.core.chat_service import RESUME_PROFILE_COLLECTION_PATTERNS

        return any(pattern in message for pattern in RESUME_PROFILE_COLLECTION_PATTERNS)

    @staticmethod
    def is_acknowledgement_only_message(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False

        normalized = re.sub(r"[，。！？!?~～、\s]+", "", message)
        acknowledgement_messages = {
            "好",
            "好的",
            "知道了",
            "了解了",
            "明白了",
            "行",
            "可以",
            "嗯",
            "嗯嗯",
            "哦",
            "收到",
            "没问题",
            "好哦",
        }
        return normalized in acknowledgement_messages

    @staticmethod
    def is_short_answer(user_message: str, max_length: int = 12) -> bool:
        message = (user_message or "").strip()
        if not message:
            return False

        if len(message) > max_length:
            return False

        short_answer_patterns = [
            r"^(男|女|男的|女的|男生|女生)$",
            r"^\d{2,4}$",
            r"^\d{1,2}后$",
            r"^\d{1,2}岁$",
            r"^[北上广深成杭武南京苏][^\s]{0,4}$",
            r"^(本科|大专|硕士|博士|高中|初中|中专)$",
            r"^(已婚|未婚|离异|单身)$",
            r"^(是|对|嗯|好|好的|行|可以|ok)$",
            r"^(不是|不对|没有|没)$",
            r"^同城",
            r"^[\d.]+万?$",
            r"^[\d.]+万左右$",
        ]

        for pattern in short_answer_patterns:
            if re.match(pattern, message):
                return True

        sentence_markers = ["我在", "我是", "我是在", "我在是", "我现在", "我这边"]
        if any(m in message for m in sentence_markers):
            return False

        complex_puncts = {"？", "?", "。", "！", "!", "，", ",", "、"}
        if not any(p in message for p in complex_puncts):
            return True

        return False

    @staticmethod
    def has_any_valid_contact(user_profile: Optional[UserProfile]) -> bool:
        if not user_profile:
            return False
        return bool(
            (user_profile.phone and user_profile.phone_collected)
            or (user_profile.wechat and user_profile.wechat_collected)
            or user_profile.collection_progress.get("contact", False)
        )
