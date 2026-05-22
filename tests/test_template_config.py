from src.templates.config import TemplateConfig, get_active_template, reset_template_cache
from src.templates.validation import format_validation_report, validate_template_config


def test_default_template_loads(monkeypatch):
    monkeypatch.delenv("ACTIVE_TEMPLATE", raising=False)
    reset_template_cache()

    template = get_active_template()

    assert template.template.id == "matchmaking"
    assert template.agent.language == "zh-CN"
    assert template.agent.role == "婚恋咨询顾问"
    assert not template.agent.persona.startswith("#")
    assert "你是小缘，以真实自然的口吻和用户聊天" in template.agent.persona
    assert len(template.agent.goals) == 3
    assert len(template.agent.behavior_rules) == 12
    assert len(template.agent.boundaries) == 4
    assert template.extraction.enabled is True
    assert template.opening.enabled is True
    assert template.opening.message == template.agent.welcome_message
    assert template.field_routing.mode == "auto"
    assert template.contact.trigger.mode == "coverage_gate"
    assert template.contact.trigger.min_required_collected == 0
    assert template.contact.trigger.require_all_core_covered is True
    assert template.contact.trigger.require_all_optional_covered is True
    assert template.compliance.enabled is True
    assert template.compliance.rules[0].id == "underage"
    assert template.closing.enabled is True
    assert template.humanization.enabled is True
    assert "婚恋咨询对话中提取本轮用户新提供的资料" in template.extraction.prompt
    assert "{user_message}" in template.extraction.prompt
    assert "{configured_fields}" in template.extraction.prompt
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


def test_public_template_config_redacts_internal_prompt_content(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()

    public_config = get_active_template().public_dict()

    assert "dialogue_policy" not in public_config
    assert "source_path" not in public_config
    assert "persona" not in public_config["agent"]
    assert "goals" not in public_config["agent"]
    assert "behavior_rules" not in public_config["agent"]
    assert "boundaries" not in public_config["agent"]
    assert "knowledge_base_path" not in public_config["rag"]
    assert public_config["extraction"] == {"enabled": True, "custom_prompt": True}
    assert "prompt" not in public_config["extraction"]
    assert public_config["field_routing"]["mode"] == "auto"
    assert public_config["humanization"]["enabled"] is True


def test_template_file_references_must_stay_inside_template_directory(monkeypatch, tmp_path):
    templates_dir = tmp_path / "templates"
    bad_template_dir = templates_dir / "bad"
    bad_template_dir.mkdir(parents=True)
    (templates_dir / "secret.md").write_text("secret", encoding="utf-8")
    (bad_template_dir / "template.yaml").write_text(
        """
template:
  id: bad
  name: Bad Template
agent:
  persona_file: ../secret.md
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    monkeypatch.setenv("ACTIVE_TEMPLATE", "bad")
    reset_template_cache()

    try:
        get_active_template()
    except ValueError as exc:
        assert "inside the template directory" in str(exc)
    else:
        raise AssertionError("Expected unsafe template reference to be rejected")


def test_default_template_validation_has_no_issues(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()

    report = validate_template_config(get_active_template())

    assert report.ok is True
    assert report.errors == []
    assert report.warnings == []


def test_template_validation_reports_blocking_configuration_errors():
    template = TemplateConfig(
        template={"id": "bad", "name": "Bad"},
        fields=[
            {
                "key": "age",
                "label": "年龄",
                "required": True,
                "ask_limit": 1,
                "ask": "年龄？",
                "risk": "dangerous",
            },
            {"key": "age", "label": "重复年龄", "required": True, "ask_limit": 1, "ask": "年龄？"},
        ],
        contact={
            "enabled": True,
            "trigger": {"required_fields": ["unknown"], "min_required_collected": 2},
            "methods": [
                {"key": "age", "label": "电话", "type": "phone", "risk": "dangerous"}
            ],
        },
        faq=[{"intent": "pricing", "keywords": ["收费"], "answer": ""}],
        compliance={
            "enabled": True,
            "rules": [
                {
                    "id": "bad_rule",
                    "when": {"field": "missing", "operator": "near"},
                    "action": "end",
                }
            ],
        },
        field_permissions={
            "rules": [
                {
                    "intents": ["preference"],
                    "allow_fields": ["missing_allow"],
                    "block_fields": ["missing_block"],
                    "expected_fields": ["missing_expected"],
                }
            ]
        },
    )

    report = validate_template_config(template)
    codes = {issue.code for issue in report.issues}

    assert report.ok is False
    assert "duplicate_field_key" in codes
    assert "field_contact_key_conflict" in codes
    assert "contact_unknown_required_field" in codes
    assert "faq_without_answer" in codes
    assert "compliance_unknown_field" in codes
    assert "unsupported_compliance_operator" in codes
    assert "field_permission_unknown_allow_field" in codes
    assert "field_permission_unknown_block_field" in codes
    assert "field_permission_unknown_expected_field" in codes
    assert "unknown_field_risk" in codes
    assert "unknown_contact_risk" in codes


def test_format_validation_report_is_human_readable():
    template = TemplateConfig(
        template={"id": "warn", "name": "Warn"},
        fields=[{"key": "age", "label": "年龄", "required": True, "ask_limit": 0}],
    )

    output = format_validation_report(validate_template_config(template))

    assert "Template validation: OK" in output
    assert "[WARN] required_field_never_asked" in output
