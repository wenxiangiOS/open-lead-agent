import re


class ChatServiceResponseCleanupService:
    @staticmethod
    def looks_like_truncated_response(response: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return True

        from src.services.core.chat_service import DELIVERY_DANGLING_ENDINGS

        return any(text.endswith(ending) for ending in DELIVERY_DANGLING_ENDINGS)

    @staticmethod
    def is_delivery_viable(response: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return False
        return not ChatServiceResponseCleanupService.looks_like_truncated_response(text)

    @staticmethod
    def strip_broken_edge_fragments(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        text = re.sub(r"^(?:(?:了|啦|呀|呢|哈|啊|哦|嗯)[。．！？!?]\s*)+", "", text).strip()

        text = re.sub(
            r"^(?:我看你(?:资料|情况|这边资料|这边情况)?[^。！？!?]{0,8}"
            r"|你这边(?:资料|情况)?[^。！？!?]{0,8}"
            r"|资料[^。！？!?]{0,8}"
            r"|情况[^。！？!?]{0,8})"
            r"(?:和|跟|以及|还有|然后)[。．！？!?]\s*",
            "",
            text,
        ).strip()

        sentence_match = re.match(r"^([^。！？!?]{1,4}[。！？!?])\s*(.+)$", text)
        if sentence_match:
            first_sentence = sentence_match.group(1).strip()
            remainder = sentence_match.group(2).strip()
            first_body = re.sub(r"[。！？!?]", "", first_sentence).strip()
            if first_body in {"了", "啦", "呀", "呢", "哈", "啊", "哦", "嗯"}:
                text = remainder

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def compress_multi_action_response(response: str) -> str:
        text = str(response or "").strip()
        if not text or ("？" not in text and "?" not in text):
            return text

        explanatory_tail_patterns = (
            r"这样我(?:心里|对你的情况)?会更有数一点[。．]?$",
            r"后面我也更好往[^。！？!?]{1,20}(?:聊|看)[。．]?$",
            r"这个先对齐了，后面聊起来也会顺一点[。．]?$",
            r"这样后面聊起来会更顺一点[。．]?$",
            r"我心里也更好有个大概范围[。．]?$",
        )
        if any(re.search(pattern, text) for pattern in explanatory_tail_patterns):
            question_pos = max(text.rfind("？"), text.rfind("?"))
            if question_pos != -1 and question_pos < len(text) - 1:
                tail = text[question_pos + 1 :].strip()
                if tail and any(re.search(pattern, tail) for pattern in explanatory_tail_patterns):
                    return text[: question_pos + 1].strip()
        return text

    @staticmethod
    def strip_question_clause_for_field(response: str, field: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        patterns = {
            "monthly_income": (
                r"[，,、]\s*(?:大概|顺便|另外)?\s*(?:收入|月收入|月薪|工资)[^。！？!?]*?(?:范围|多少|什么范围|什么区间|区间|水平)?[^。！？!?]*[？?]",
                r"[，,、]\s*(?:收入|月收入|月薪|工资)[^。！？!?]*?(?:范围|多少|什么范围|什么区间|区间|水平)?[^。！？!?]*[？?]",
                r"(?:大概|顺便|另外)?\s*(?:收入|月收入|月薪|工资)[^。！？!?]*?(?:范围|多少|什么范围|什么区间|区间|水平)?[^。！？!?]*[？?]",
                r"(?:收入|月收入|月薪|工资)[^。！？!?]*?(?:范围|多少|什么范围|什么区间|区间|水平)?[^。！？!?]*[？?]",
            ),
            "partner_requirement": (
                r"[，,、]\s*(?:你)?(?:想找|喜欢|更看重|对另一半|择偶要求)[^。！？!?]*[？?]",
                r"(?:你)?(?:想找|喜欢|更看重|对另一半|择偶要求)[^。！？!?]*[？?]",
            ),
        }

        for pattern in patterns.get(field, ()):
            updated = re.sub(pattern, "", text)
            if updated != text:
                text = updated.strip()

        text = re.sub(r"[，,、]\s*$", "", text).strip()
        text = re.sub(r"[，,、]\s*[？?]$", "？", text)
        text = re.sub(r"([。！？!?])\s*[？?]$", r"\1", text)
        if text and not re.search(r"[。！？!?]$", text):
            if re.search(r"(吗|么|嘛|呢|呀|对吧|是不是|工作(?:的)?呀|什么工作(?:的)?呀)$", text):
                text = f"{text}？"
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_redundant_confirmation_phrasing(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        text = re.sub(
            r"^(我(?:这边)?确认一下|我再确认下|我顺手确认一下)，那我确认一下，",
            r"\1，",
            text,
        )
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def soften_awkward_age_question(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        text = re.sub(
            r"^(挺好的|好呀|好的|嗯，不错呀|行呀)[，,]\s*你是哪年的呀([？?])$",
            r"\1，那你大概是哪一年出生的呀\2",
            text,
        )
        text = re.sub(r"^你是哪年的呀([？?])$", r"你大概是哪一年出生的呀\1", text)
        return re.sub(r"\s+", " ", text).strip()
