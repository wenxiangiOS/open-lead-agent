from src.collection import CollectionEngine
from src.templates.config import get_active_template, reset_template_cache


def test_next_field_prefers_required_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    engine = CollectionEngine(get_active_template())

    field = engine.next_field({"student_grade": "Grade 8"})

    assert field is not None
    assert field.key == "subject"


def test_next_field_moves_to_optional_after_required(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    engine = CollectionEngine(get_active_template())

    field = engine.next_field({"student_grade": "Grade 8", "subject": "Math"})

    assert field is not None
    assert field.key == "learning_problem"
