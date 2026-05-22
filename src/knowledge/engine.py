"""把 FAQ 和 RAG 检索结果合并成本轮知识上下文。Knowledge context builder."""

from dataclasses import dataclass
from typing import Any

from src.faq import FAQEngine, FAQMatch
from src.rag import RAGEngine, RAGResult
from src.templates.config import TemplateConfig
from src.understanding import TurnSemanticFrame


@dataclass(frozen=True)
class KnowledgeContext:
    faq_match: FAQMatch | None
    rag_results: list[RAGResult]

    @property
    def rag_sources(self) -> list[str]:
        return [result.source for result in self.rag_results]

    def public_dict(self) -> dict[str, Any]:
        return {
            "faq_match": self.faq_match.public_dict() if self.faq_match else None,
            "rag_sources": self.rag_sources,
            "rag_result_count": len(self.rag_results),
        }


class KnowledgeEngine:
    def __init__(self, template: TemplateConfig):
        self.faq = FAQEngine(template)
        self.rag = RAGEngine(template.rag)

    def resolve(
        self,
        user_message: str,
        semantic_frame: TurnSemanticFrame | None = None,
    ) -> KnowledgeContext:
        faq_match = self.faq.match(user_message)
        if faq_match is None and semantic_frame is not None:
            faq_match = self.faq.match_intent(semantic_frame.faq_intent)
        return KnowledgeContext(
            faq_match=faq_match,
            rag_results=self.rag.search(user_message),
        )
