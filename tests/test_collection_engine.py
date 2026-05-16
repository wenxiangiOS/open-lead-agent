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


def test_next_field_respects_ask_limit(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    engine = CollectionEngine(get_active_template())

    field = engine.next_field({"student_grade": "Grade 8"}, {"subject": 2})

    assert field is not None
    assert field.key == "learning_problem"


def test_matchmaking_grouped_fields_collect_by_tier(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = CollectionEngine(get_active_template())

    field = engine.next_field(
        {
            "sex": "男",
            "age": 30,
            "education": "本科",
            "occupation": "工程师",
            "location": "上海",
        }
    )

    assert field is not None
    assert field.key == "marital_status"
    assert field.tier == "medium"


def test_matchmaking_low_tier_fields_are_passive(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    engine = CollectionEngine(get_active_template())

    field = engine.next_field(
        {
            "sex": "男",
            "age": 30,
            "education": "本科",
            "occupation": "工程师",
            "location": "上海",
            "marital_status": "未婚",
            "partner_requirement": "价值观稳定",
            "monthly_income": "2万-5万",
        }
    )
    collected = engine.extract_configured_fields({"last_name": "王", "height": 178, "weight": 70})

    assert field is None
    assert collected == {"last_name": "王", "height": 178, "weight": 70}
