from src.templates.config import get_active_template, reset_template_cache


def test_default_template_loads(monkeypatch):
    monkeypatch.delenv("ACTIVE_TEMPLATE", raising=False)
    reset_template_cache()

    template = get_active_template()

    assert template.template.id == "matchmaking"
    assert template.agent.language == "zh-CN"
    assert template.agent.role == "婚恋咨询顾问"
    assert "你是小缘，以真实自然的口吻和用户聊天" in template.agent.persona
    assert len(template.agent.goals) == 3
    assert len(template.agent.behavior_rules) == 12
    assert len(template.agent.boundaries) == 4
    assert "自然聊天中推进资料收集" in template.dialogue_policy.turn_goal
    assert [section.title for section in template.dialogue_policy.sections] == [
        "Dialogue priorities",
        "General principles",
        "婚况与分居处理",
        "拟人化表达",
        "生成方式",
        "承接优先",
        "禁止事项",
    ]
    assert len(template.dialogue_policy.sections[0].rules) == 3
    assert len(template.dialogue_policy.sections[1].rules) == 8
    assert len(template.dialogue_policy.sections[2].rules) == 5
    assert len(template.dialogue_policy.sections[3].rules) == 13
    assert len(template.dialogue_policy.sections[4].rules) == 8
    assert len(template.dialogue_policy.sections[5].rules) == 14
    assert len(template.dialogue_policy.sections[6].rules) == 10
    assert len(template.dialogue_policy.examples) == 13
    assert template.public_dict()["summary"]["field_count"] == 11
    assert template.public_dict()["summary"]["core_field_count"] == 5
    assert template.public_dict()["summary"]["medium_field_count"] == 3
    assert template.public_dict()["summary"]["low_field_count"] == 3
    assert template.fields[0].key == "sex"
    assert [field.key for field in template.field_groups.core] == [
        "sex",
        "age",
        "education",
        "occupation",
        "location",
    ]


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
