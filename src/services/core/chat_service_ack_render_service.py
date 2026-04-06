import re


class ChatServiceAckRenderService:
    @staticmethod
    def render_preference_for_ack(preference: str) -> str:
        text = str(preference or "").strip()
        if not text:
            return text

        text = re.sub(r"^(喜欢|想找|想要|找)\s*", "", text)
        text = re.sub(r"^一个", "", text)
        text = text.strip("，,。 ")

        if text.endswith("的女生"):
            return text[:-3] + "女生"
        if text.endswith("的男生"):
            return text[:-3] + "男生"
        if text.endswith("的女孩子"):
            return text[:-4] + "女孩子"
        if text.endswith("的男孩子"):
            return text[:-4] + "男孩子"
        return text

    @staticmethod
    def render_occupation_for_ack(value: str) -> str:
        text = str(value or "").strip()
        if text.endswith("的") and len(text) >= 3:
            text = text[:-1]
        return text

    @staticmethod
    def render_marital_status_for_ack(value: str) -> str:
        text = str(value or "").strip()
        if text == "单身":
            return "单身"
        if text in {"未婚", "离异", "已婚"}:
            return text
        return text

    @staticmethod
    def render_age_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return text
        if text.endswith(("岁", "后", "年")):
            return text
        if text.isdigit():
            return f"{text}岁"
        return text
