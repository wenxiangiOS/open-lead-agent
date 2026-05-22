"""轻量关键词 FAQ 匹配器，适合稳定短答案。Lightweight FAQ matcher."""

from dataclasses import dataclass
from typing import Any

from src.templates.config import FAQConfig, TemplateConfig


@dataclass(frozen=True)
class FAQMatch:
    item: FAQConfig
    matched_keyword: str = ""

    @property
    def intent(self) -> str:
        return self.item.intent

    @property
    def answer(self) -> str:
        return self.item.answer

    @property
    def continue_collection(self) -> bool:
        return self.item.continue_collection

    def public_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "matched_keyword": self.matched_keyword,
            "continue_collection": self.continue_collection,
        }


class FAQEngine:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def match(self, user_message: str) -> FAQMatch | None:
        normalized = user_message.lower()
        for item in self.template.faq:
            keyword = self._matched_keyword(item, normalized)
            if keyword:
                return FAQMatch(item=item, matched_keyword=keyword)
        return None

    def match_intent(self, intent: str | None) -> FAQMatch | None:
        if not intent:
            return None
        normalized_intent = intent.strip().lower()
        if not normalized_intent:
            return None
        for item in self.template.faq:
            if item.intent.strip().lower() == normalized_intent:
                return FAQMatch(item=item, matched_keyword="<semantic_intent>")
        return None

    def _matched_keyword(self, item: FAQConfig, normalized_message: str) -> str:
        for keyword in item.keywords:
            normalized_keyword = keyword.lower()
            if normalized_keyword and normalized_keyword in normalized_message:
                return keyword
        return ""
