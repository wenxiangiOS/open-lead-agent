from pathlib import Path

from src.templates.config import get_active_template, reset_template_cache
from src.templates.guided import (
    GuidedFAQ,
    GuidedTemplateAnswers,
    GuidedTemplateOptions,
    create_guided_template,
    parse_comma_list,
    parse_faq_lines,
)
from src.templates.scaffold import TemplateScaffoldOptions, create_template_scaffold
from src.templates.validation import validate_template_config


def test_create_lead_template_scaffold(monkeypatch, tmp_path):
    templates_dir = tmp_path / "templates"
    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    reset_template_cache()

    result = create_template_scaffold(
        TemplateScaffoldOptions(
            template_id="dental",
            name="口腔咨询助手",
            scenario="lead",
        )
    )

    assert result.template_dir == templates_dir / "dental"
    assert (templates_dir / "dental" / "template.yaml").exists()
    assert (templates_dir / "dental" / "knowledge" / "README.md").exists()
    assert (templates_dir / "dental" / "prompts" / "README.md").exists()

    template = get_active_template("dental")
    report = validate_template_config(template)

    assert template.template.name == "口腔咨询助手"
    assert [field.key for field in template.field_groups.core] == ["need", "location"]
    assert template.contact.enabled is True
    assert report.ok is True
    assert report.warnings == []


def test_create_support_template_scaffold(monkeypatch, tmp_path):
    templates_dir = tmp_path / "templates"
    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    reset_template_cache()

    create_template_scaffold(
        TemplateScaffoldOptions(
            template_id="support",
            name="官网客服",
            scenario="support",
        )
    )

    template = get_active_template("support")
    report = validate_template_config(template)

    assert template.template.name == "官网客服"
    assert template.fields == []
    assert template.contact.enabled is False
    assert report.ok is True
    assert report.warnings == []


def test_create_education_template_scaffold(monkeypatch, tmp_path):
    templates_dir = tmp_path / "templates"
    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    reset_template_cache()

    create_template_scaffold(
        TemplateScaffoldOptions(
            template_id="my_edu",
            name="我的教培咨询助手",
            scenario="education",
        )
    )

    template = get_active_template("my_edu")
    report = validate_template_config(template)

    assert template.template.name == "我的教培咨询助手"
    assert [field.key for field in template.field_groups.core] == [
        "student_grade",
        "subject",
    ]
    assert [method.key for method in template.contact.methods] == ["phone"]
    assert template.contact.trigger.required_fields == ["student_grade", "subject"]
    assert report.ok is True
    assert report.warnings == []


def test_create_guided_template_from_beginner_answers(monkeypatch, tmp_path):
    templates_dir = tmp_path / "templates"
    monkeypatch.setenv("TEMPLATES_DIR", str(templates_dir))
    reset_template_cache()

    create_guided_template(
        GuidedTemplateOptions(
            template_id="guided_edu",
            name="教培咨询助手",
            answers=GuidedTemplateAnswers(
                industry="教培",
                fields=["学生年级", "科目", "学习问题"],
                contact_methods=["手机号", "微信"],
                faqs=[
                    GuidedFAQ(
                        question="怎么收费",
                        answer="收费会根据年级、科目和班型不同而变化。",
                    )
                ],
            ),
        )
    )

    template = get_active_template("guided_edu")
    report = validate_template_config(template)

    assert [field.key for field in template.field_groups.core] == [
        "student_grade",
        "subject",
        "learning_problem",
    ]
    assert [method.key for method in template.contact.methods] == ["phone", "wechat"]
    assert template.faq[0].keywords == ["怎么收费", "收费"]
    assert template.contact.trigger.required_fields == [
        "student_grade",
        "subject",
        "learning_problem",
    ]
    assert report.ok is True
    assert report.warnings == []


def test_guided_template_parses_beginner_lists_and_faqs():
    assert parse_comma_list("手机号, 微信、邮箱\nQQ") == ["手机号", "微信", "邮箱", "QQ"]

    faqs = parse_faq_lines(["怎么收费=按课程收费", "有门店吗：有线下校区"])

    assert faqs[0].question == "怎么收费"
    assert faqs[0].answer == "按课程收费"
    assert faqs[1].question == "有门店吗"
    assert faqs[1].answer == "有线下校区"


def test_scaffold_rejects_path_like_template_ids(tmp_path):
    try:
        create_template_scaffold(
            TemplateScaffoldOptions(
                template_id="../bad",
                templates_dir=tmp_path,
            )
        )
    except ValueError as exc:
        assert "letters, numbers" in str(exc)
    else:
        raise AssertionError("Expected unsafe template id to be rejected")


def test_scaffold_does_not_overwrite_without_force(tmp_path):
    create_template_scaffold(
        TemplateScaffoldOptions(
            template_id="demo",
            templates_dir=Path(tmp_path),
        )
    )

    try:
        create_template_scaffold(
            TemplateScaffoldOptions(
                template_id="demo",
                templates_dir=Path(tmp_path),
            )
        )
    except FileExistsError as exc:
        assert "--force" in str(exc)
    else:
        raise AssertionError("Expected existing scaffold to require force")
