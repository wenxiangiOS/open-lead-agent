from dataclasses import dataclass
from pathlib import Path

from src.templates.config import RAGConfig


@dataclass(frozen=True)
class RAGResult:
    content: str
    source: str


class RAGEngine:
    def __init__(self, config: RAGConfig):
        self.config = config

    def search(self, query: str) -> list[RAGResult]:
        if not self.config.enabled or not self.config.knowledge_base_path:
            return []
        base = Path(self.config.knowledge_base_path)
        if not base.exists():
            return []

        query_terms = {term.lower() for term in query.split() if term.strip()}
        results: list[RAGResult] = []
        for path in list(base.rglob("*.md")) + list(base.rglob("*.txt")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            haystack = text.lower()
            if not query_terms or any(term in haystack for term in query_terms):
                results.append(RAGResult(content=text[:1200], source=str(path)))
            if len(results) >= self.config.top_k:
                break
        return results
