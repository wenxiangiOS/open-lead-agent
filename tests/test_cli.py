from types import SimpleNamespace

from src.cli import (
    _field_items,
    _format_error_hint,
    _format_profile_value,
    _guided_template_command,
    _has_invalid_terminal_text,
    _init_template_command,
    _normalize_pending_field_value,
    _normalize_terminal_text,
    _parse_set_command,
    _print_turn_log,
    _state_id,
    _validate_template_command,
)
from src.templates.config import get_active_template, reset_template_cache


def test_parse_set_command():
    assert _parse_set_command("/set age=28") == ("age", "28")
    assert _parse_set_command("set age=28") == ("age", "28")


def test_invalid_terminal_text_detects_surrogateescaped_bytes():
    assert _has_invalid_terminal_text("你\udce8\udcbf好")


def test_invalid_terminal_text_accepts_normal_chinese():
    assert not _has_invalid_terminal_text("你好")


def test_terminal_text_normalizer_keeps_good_chinese_and_strips_bad_bytes():
    assert _normalize_terminal_text("做在职教师\udce8") == "做在职教师"


def test_terminal_text_normalizer_recovers_gb18030_bytes():
    raw = "做在职教师".encode("gb18030").decode("utf-8", "surrogateescape")

    assert _has_invalid_terminal_text(raw)
    assert _normalize_terminal_text(raw) == "做在职教师"


def test_pending_field_value_uses_template_normalization(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()

    assert _normalize_pending_field_value(template, "sex", "女生呢") == (True, "女")
    assert _normalize_pending_field_value(template, "education", "本科呢") == (True, "本科")
    assert _normalize_pending_field_value(template, "marital_status", "单身呢") == (
        True,
        "单身",
    )


def test_pending_phone_value_rejects_invalid_number(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    template = get_active_template()

    assert _normalize_pending_field_value(template, "phone", "17682839482349234") == (
        False,
        None,
    )
    assert _normalize_pending_field_value(template, "phone", "17688987654") == (
        True,
        "17688987654",
    )


def test_format_error_hint_identifies_timeout():
    title, hint = _format_error_hint(TimeoutError("Request timed out."))

    assert "模型请求超时" in title
    assert "LLM_TIMEOUT_SECONDS" in hint


def test_print_turn_log_outputs_compact_debug_summary(capsys):
    response = SimpleNamespace(
        debug_understanding={
            "semantic_frame": {"intents": ["profile"], "turn_mode": "dense_intro"},
            "persistence_plan": {
                "accepted_fields": {"location": "深圳"},
                "pending_fields": {},
                "rejected_fields": {"monthly_income": "30岁"},
                "provisional_fields": {},
                "observation_log": [
                    {"field": "location", "reason": "accepted"},
                    {"field": "monthly_income", "reason": "invalid_format"},
                ],
            },
        },
        debug_decision={
            "action": "ask_field",
            "reason": "natural_followup",
            "target": "occupation",
            "side_target": None,
        },
        collected={"location": "深圳"},
        debug_contact_gate={
            "allowed": False,
            "required_fields": ["sex", "age", "location"],
            "collected": ["location"],
            "missing": ["sex", "age"],
        },
        debug_response={"route": "model", "chars": 12, "error": ""},
        debug_timing={
            "total_ms": 123.4,
            "stages": {
                "state_load": 1.0,
                "understanding": 20.0,
                "response_build": 80.0,
                "total": 123.4,
            },
        },
        debug_llm_usage={
            "calls": 2,
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
            "estimated_input_tokens": 130,
            "estimated_output_tokens": 32,
            "usage_available": True,
            "details": [
                {
                    "route": "model",
                    "elapsed_ms": 20.0,
                    "input_tokens": 50,
                    "output_tokens": 10,
                    "estimated_input_tokens": 55,
                    "estimated_output_tokens": 11,
                    "error": "",
                    "purpose": "understanding",
                }
            ],
        },
        debug_quality_check={"passed": True, "issues": []},
        rag_sources=[],
    )
    llm = SimpleNamespace(
        settings=SimpleNamespace(provider="openai_compatible", model="demo"),
        configured=True,
    )

    _print_turn_log(response, llm)

    output = capsys.readouterr().out
    assert "[测试日志]" in output
    assert "总耗时: 0.12秒" in output
    assert "理解用户与提取字段: 0.02秒" in output
    assert "读取会话资料: 0.00秒" not in output
    assert "总输入: 120 tokens" in output
    assert "总输出: 30 tokens" in output
    assert "理解提取 LLM: 耗时 0.02秒" in output
    assert "状态=成功" in output
    assert "字段提取:" in output
    assert "已识别: location=深圳" in output
    assert "未采纳: monthly_income=30岁（格式不符合字段）" in output
    assert "下一步决策:" in output
    assert "下一字段: occupation" in output
    assert "联系方式门槛:" in output
    assert "是否可以要联系方式: 否" in output
    assert "回复生成:" in output
    assert "来源: 模型生成" in output
    assert "error=-" not in output


def test_state_id_uses_account_and_dialog():
    assert _state_id("user-1", "dialog-1") == "user-1:dialog-1"


def test_profile_value_formats_missing_values():
    assert _format_profile_value(None) == "未留"
    assert _format_profile_value("") == "未留"
    assert _format_profile_value("深圳") == "深圳"


def test_field_items_include_template_fields_and_contact_methods(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()

    keys = [key for key, _label in _field_items(get_active_template())]

    assert "sex" in keys
    assert "partner_requirement" in keys
    assert "phone" in keys
    assert "wechat" in keys


def test_validate_template_command_prints_report(monkeypatch, capsys):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()

    exit_code = _validate_template_command("matchmaking")

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Template validation: OK" in output
    assert "template: matchmaking" in output


def test_init_template_command_creates_template(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TEMPLATES_DIR", str(tmp_path / "templates"))
    reset_template_cache()

    exit_code = _init_template_command("demo", name="Demo", scenario="support")

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Template scaffold: OK" in output
    assert "template: demo" in output
    assert (tmp_path / "templates" / "demo" / "template.yaml").exists()


def test_guided_template_command_creates_template(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TEMPLATES_DIR", str(tmp_path / "templates"))
    reset_template_cache()
    answers = iter(
        [
            "教培",
            "学生年级, 科目, 学习问题",
            "手机号, 微信",
            "怎么收费=按课程和班型收费",
            "",
            "",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    exit_code = _guided_template_command("guided_demo", name="教培咨询助手")

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Template guide: OK" in output
    assert "template: guided_demo" in output
    assert (tmp_path / "templates" / "guided_demo" / "template.yaml").exists()
