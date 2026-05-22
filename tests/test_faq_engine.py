from src.faq import FAQEngine
from src.templates.config import get_active_template, reset_template_cache


def test_faq_engine_matches_configured_keyword(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    engine = FAQEngine(get_active_template())

    match = engine.match("How much is the tuition?")

    assert match is not None
    assert match.intent == "pricing"
    assert match.matched_keyword == "tuition"
    assert match.continue_collection is True
    assert "课程价格" in match.answer


def test_faq_engine_returns_none_without_keyword(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    engine = FAQEngine(get_active_template())

    assert engine.match("hello") is None
