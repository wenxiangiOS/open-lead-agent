import re
from typing import Any


class ChatServiceTextPolicyService:
    @staticmethod
    def contains_contact_push_markers(response: str) -> bool:
        text = (response or "").strip()
        if not text:
            return False

        from src.services.core.chat_service import CONTACT_ASK_MARKERS

        if any(marker in text for marker in CONTACT_ASK_MARKERS):
            return True
        return any(marker in text for marker in ("加你", "加下", "微信号", "手机号", "联系到你"))

    @staticmethod
    def looks_like_low_information_model_reply(text: str) -> bool:
        content = str(text or "").strip()
        if not content:
            return True
        generic_patterns = (
            r"你继续说，我先顺着听[。.]?$",
            r"你继续说[。.]?$",
            r"顺着往下了解[。.]?$",
            r"顺着听[。.]?$",
            r"接着往下聊[。.]?$",
            r"先顺着聊[。.]?$",
            r"好，我先顺着听，你想聊什么就聊什么[。.]?$",
            r"这个我先放这儿，我们先顺着你这句聊[。.]?$",
        )
        return any(re.search(pattern, content) for pattern in generic_patterns)

    @staticmethod
    def collapse_duplicate_ack_segments(response: str) -> str:
        from src.services.core.chat_service import ChatService

        text = str(response or "").strip()
        if not text:
            return text

        natural_response, extract_block = ChatService._split_response_and_extract(text)
        if not natural_response:
            return text

        parts = [segment.strip() for segment in re.split(r"(?<=[。！？?!])\s*", natural_response) if segment.strip()]
        if len(parts) < 2:
            return text

        collapsed: list[str] = []
        previous_field: str | None = None
        previous_is_ack = False

        def detect_ack_field(segment: str) -> str | None:
            if any(token in segment for token in ("男生", "女生", "男的", "女的")):
                return "sex"
            if any(token in segment for token in ("90后", "80后", "00后", "岁")):
                return "age"
            if any(token in segment for token in ("深圳", "广州", "上海", "北京", "杭州", "成都")):
                return "location"
            if any(token in segment for token in ("本科", "大专", "硕士", "博士")):
                return "education"
            if "单身" in segment or "离异" in segment or "未婚" in segment:
                return "marital_status"
            return None

        def is_ack_segment(segment: str) -> bool:
            if "？" in segment or "?" in segment:
                return False
            return any(
                token in segment
                for token in (
                    "明白了", "知道了", "是吧", "我知道了", "我记住了", "好嘞", "好，", "好。", "好的", "收到",
                    "你这边是", "你是", "嗯嗯我知道啦", "你说的这些我都记下啦", "这个我知道了", "这个点我记住了",
                )
            )

        def question_segment_repeats_ack(segment: str, field: str | None) -> bool:
            if not field or ("？" not in segment and "?" not in segment):
                return False
            prefix = re.split(r"[？?]", segment, maxsplit=1)[0]
            return detect_ack_field(prefix) == field and any(
                token in prefix for token in ("好", "好的", "明白", "知道", "是吧", "你是", "你这边是")
            )

        for part in parts:
            current_field = detect_ack_field(part)
            current_is_ack = is_ack_segment(part)
            if collapsed and previous_is_ack and current_is_ack:
                if previous_field and not current_field:
                    previous_is_ack = current_is_ack
                    continue
                if current_field and not previous_field:
                    collapsed[-1] = part
                    previous_field = current_field
                    previous_is_ack = current_is_ack
                    continue
            if collapsed and previous_is_ack and current_is_ack and previous_field and current_field == previous_field:
                collapsed[-1] = part
                previous_field = current_field
                previous_is_ack = current_is_ack
                continue
            if collapsed and previous_is_ack and previous_field and question_segment_repeats_ack(part, previous_field):
                collapsed[-1] = part
                previous_field = current_field or previous_field
                previous_is_ack = False
                continue
            collapsed.append(part)
            previous_field = current_field
            previous_is_ack = current_is_ack

        merged = " ".join(collapsed).strip()
        if extract_block:
            return f"{merged}\n{extract_block}"
        return merged

    @staticmethod
    def response_already_acks_field(response: str, field_name: str, value: Any) -> bool:
        text = str(response or "").strip()
        rendered = str(value or "").strip()
        if not text or not rendered:
            return False

        if field_name == "location":
            return rendered in text and any(marker in text for marker in ("这边", "知道", "是吧", "挺好", "常住", "生活"))
        if field_name == "occupation":
            return rendered in text and any(marker in text for marker in ("工作", "做", "方向", "知道", "明白"))
        if field_name == "education":
            return rendered in text and any(marker in text for marker in ("学历", "知道", "明白", "是吧"))
        if field_name == "marital_status":
            return rendered in text and any(marker in text for marker in ("状态", "婚况", "知道", "明白"))
        if field_name == "age":
            return rendered in text and any(marker in text for marker in ("岁", "知道", "明白", "是吧"))
        if field_name == "sex":
            return any(marker in text for marker in ("男生", "女生", "男的", "女的", "性别"))

        return rendered in text

    @staticmethod
    def response_already_absorbs_location_context(response: str, value: Any) -> bool:
        text = str(response or "").strip()
        rendered = str(value or "").strip()
        if not text or not rendered or rendered not in text:
            return False

        context_markers = (
            f"在{rendered}",
            f"主要在{rendered}",
            f"目前在{rendered}",
            f"现在在{rendered}",
            f"{rendered}主要",
        )
        return any(marker in text for marker in context_markers)

    @staticmethod
    def response_already_acknowledges_short_answer(text: str, user_message: str, *, ack: str = "") -> bool:
        normalized_text = str(text or "").strip()
        normalized_user_message = str(user_message or "").strip()
        if not normalized_text or not normalized_user_message:
            return False

        head = normalized_text[:32]
        if head.startswith(
            ("好，", "好。", "好的", "嗯，", "嗯。", "明白", "知道", "收到", "深圳", "本科", "90后", "男生", "女生", "单身")
        ):
            return True

        if ack and ack[:4] in head:
            return True

        short_answer_aliases = {
            "男的": ("男的", "男生", "男性", "你是男"),
            "女的": ("女的", "女生", "女性", "你是女"),
            "男": ("男", "男生", "男性", "你是男"),
            "女": ("女", "女生", "女性", "你是女"),
            "单身": ("单身", "未婚"),
            "未婚": ("未婚", "单身"),
        }
        candidate_tokens = short_answer_aliases.get(normalized_user_message, (normalized_user_message,))
        return any(token and token in head for token in candidate_tokens)
