from src.templates.config import get_active_template, reset_template_cache


def test_default_template_loads(monkeypatch):
    monkeypatch.delenv("ACTIVE_TEMPLATE", raising=False)
    reset_template_cache()

    template = get_active_template()

    assert template.template.id == "matchmaking"
    assert template.agent.language == "zh-CN"
    assert template.public_dict()["summary"]["field_count"] == 4
    assert template.fields[0].key == "sex"


def test_education_template_loads(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()

    template = get_active_template()

    assert template.template.id == "education"
    assert template.agent.language == "zh-CN"
    assert [field.key for field in template.fields if field.required] == [
        "student_grade",
        "subject",
    ]
    assert template.contact.methods[0].key == "phone"
