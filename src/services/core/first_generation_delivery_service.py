import re
from typing import Tuple


class FirstGenerationDeliveryService:
    """将第一次 AI 原始结果收敛为唯一可展示正文。"""

    OPENING_INTENT_BLOCK_RE = re.compile(r"<opening_intent>.*?</opening_intent>", re.DOTALL)
    EXTRACT_BLOCK_RE = re.compile(r"<extract>.*?</extract>", re.DOTALL)

    def strip_technical_blocks(self, raw_text: str) -> Tuple[str, list[str]]:
        text = str(raw_text or "")
        removed_blocks: list[str] = []
        if not text:
            return "", removed_blocks

        if self.OPENING_INTENT_BLOCK_RE.search(text):
            removed_blocks.append("opening_intent")
            text = self.OPENING_INTENT_BLOCK_RE.sub("", text)
        if self.EXTRACT_BLOCK_RE.search(text):
            removed_blocks.append("extract")
            text = self.EXTRACT_BLOCK_RE.sub("", text)

        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip(), removed_blocks

    def extract_display_text(self, raw_text: str) -> Tuple[str, list[str]]:
        return self.strip_technical_blocks(raw_text)
