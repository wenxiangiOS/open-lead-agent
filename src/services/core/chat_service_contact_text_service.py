import random
import re


class ChatServiceContactTextService:
    OPENING_INTENT_BLOCK_RE = re.compile(r"<opening_intent>.*?</opening_intent>", re.DOTALL)
    EXTRACT_BLOCK_RE = re.compile(r"<extract>.*?</extract>", re.DOTALL)

    @classmethod
    def _strip_technical_blocks(cls, response: str) -> str:
        text = str(response or "")
        if not text:
            return ""
        text = cls.OPENING_INTENT_BLOCK_RE.sub("", text)
        text = cls.EXTRACT_BLOCK_RE.sub("", text)
        return text.strip()

    @staticmethod
    def response_mentions_phone_request(response: str) -> bool:
        text = ChatServiceContactTextService._strip_technical_blocks(response)
        return any(marker in text for marker in ("电话", "手机号", "号码"))

    @staticmethod
    def response_mentions_wechat_request(response: str) -> bool:
        text = ChatServiceContactTextService._strip_technical_blocks(response)
        return "微信" in text

    @staticmethod
    def build_contact_collection_ack(contact_type: str) -> str:
        if contact_type == "wechat":
            return "微信我看到了，我们接着往下聊就行。"
        return "电话我收到了，我们接着往下聊就行。"

    @staticmethod
    def build_contact_followup_response(next_action_value: str, collected_type: str) -> str:
        if collected_type == "phone":
            if next_action_value == "ask_wechat":
                variants = (
                    "电话我收到了。方便的话，微信也可以发我一下。",
                    "电话这边我记下了。你要是方便，也可以顺手留个微信。",
                    "电话我收到了。要是你方便的话，再补个微信也行。",
                )
                return random.choice(variants)
            if next_action_value == "persuade_wechat":
                variants = (
                    "电话我收到了。你要是方便的话，微信也可以顺手留一个。",
                    "电话这边没问题了。你要是更习惯微信的话，也可以留个常用微信。",
                    "电话我先记下了。要是你方便，再留个微信也行。",
                )
                return random.choice(variants)
            return "电话我收到了，我们接着往下聊就行。"

        if next_action_value == "ask_phone":
            return "微信我看到了。你要是方便的话，也可以留个常用手机号。"
        if next_action_value == "persuade_phone":
            return "微信我看到了。你要是方便的话，也可以补个常用手机号。"
        return "微信我看到了，我们接着往下聊就行。"

    @staticmethod
    def build_ask_wechat_fallback() -> str:
        variants = (
            "你要是方便的话，留个常用微信也行。",
            "如果你更习惯微信的话，发个常用微信给我就行。",
            "方便的话，也可以留个常用微信。",
        )
        return random.choice(variants)

    @staticmethod
    def build_persuade_wechat_fallback() -> str:
        variants = (
            "我再轻轻问一句，你要是方便的话，留个常用微信就行。",
            "明白你现在对微信这块还有点顾虑。你要是方便的话，发个常用微信给我就可以。",
            "我懂，你现在不太想留也正常。你要是方便的话，留个常用微信就行。",
        )
        return random.choice(variants)

    @staticmethod
    def build_phone_persuasion_fallback() -> str:
        variants = (
            "电话这块我再轻轻问一句，你要是方便的话，留个常用手机号就行，后面联系你也更顺。",
            "我再确认一下，你要是方便的话，发个常用手机号给我就行，后面沟通也方便些。",
            "这边电话我再问一句，方便的话留个常用手机号就好，后面联系也更顺一点。",
            "你要是现在对电话这块还有点顾虑我能理解，方便的话留个常用手机号就行，后面沟通起来也方便。",
        )
        return random.choice(variants)

    @staticmethod
    def build_dual_contact_ack() -> str:
        return "电话和微信我都看到了。你要是还有别的想法，也可以接着说。"
