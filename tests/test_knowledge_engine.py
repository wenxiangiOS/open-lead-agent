from src.knowledge import KnowledgeEngine
from src.templates.config import TemplateConfig


def test_knowledge_engine_aggregates_faq_and_rag(tmp_path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "pricing.md").write_text("课程价格和试听课说明", encoding="utf-8")
    template = TemplateConfig(
        template={"id": "demo", "name": "Demo"},
        faq=[
            {
                "intent": "pricing",
                "keywords": ["价格"],
                "answer": "价格会按班型不同而变化。",
                "continue_collection": True,
            }
        ],
        rag={
            "enabled": True,
            "knowledge_base_path": str(knowledge_dir),
            "top_k": 3,
        },
        fields=[],
        contact={"enabled": False, "methods": []},
    )
    engine = KnowledgeEngine(template)

    context = engine.resolve("价格")

    assert context.faq_match is not None
    assert context.faq_match.intent == "pricing"
    assert len(context.rag_results) == 1
    assert context.rag_sources == [str(knowledge_dir / "pricing.md")]
    assert context.public_dict()["rag_result_count"] == 1


def test_knowledge_engine_handles_empty_knowledge():
    template = TemplateConfig(
        template={"id": "demo", "name": "Demo"},
        fields=[],
        contact={"enabled": False, "methods": []},
    )
    engine = KnowledgeEngine(template)

    context = engine.resolve("hello")

    assert context.faq_match is None
    assert context.rag_results == []
    assert context.public_dict() == {
        "faq_match": None,
        "rag_sources": [],
        "rag_result_count": 0,
    }
