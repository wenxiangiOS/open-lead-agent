from argparse import Namespace
import asyncio

from scripts.run_real_ai_regression import RUN_PROFILES, apply_filters, apply_profile, load_failed_ids, print_progress
from tests.real_ai.scenario_runner import AssertionEvaluator, ScenarioLoader, ScenarioValidationError


def test_scenario_loader_reads_cases(tmp_path):
    scenario_file = tmp_path / "scenarios.json"
    scenario_file.write_text(
        """
        {
          "scenarios": [
            {
              "id": "demo",
              "category": "contact",
              "description": "demo scenario",
              "messages": ["你好"],
              "assertions": [
                {"type": "final_response_contains_any", "values": ["你好"]}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    scenarios = ScenarioLoader(scenario_file).load()

    assert len(scenarios) == 1
    assert scenarios[0].scenario_id == "demo"
    assert scenarios[0].assertions[0].type == "final_response_contains_any"
    assert scenarios[0].tags == []


def test_scenario_loader_reads_directory(tmp_path):
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "a.json").write_text(
        """
        {"scenarios":[{"id":"a","category":"contact","tags":["critical"],"messages":["1"],"assertions":[]}]}
        """,
        encoding="utf-8",
    )
    (scenario_dir / "b.json").write_text(
        """
        {"scenarios":[{"id":"b","category":"ending","messages":["2"],"assertions":[]}]}
        """,
        encoding="utf-8",
    )

    scenarios = ScenarioLoader(scenario_dir).load()

    assert [item.scenario_id for item in scenarios] == ["a", "b"]
    assert scenarios[0].tags == ["critical"]


def test_scenario_loader_detects_duplicate_ids(tmp_path):
    scenario_file = tmp_path / "dup.json"
    scenario_file.write_text(
        """
        {
          "scenarios": [
            {"id":"dup","category":"contact","messages":["1"],"assertions":[]},
            {"id":"dup","category":"ending","messages":["2"],"assertions":[]}
          ]
        }
        """,
        encoding="utf-8",
    )

    try:
        ScenarioLoader(scenario_file).load()
    except ScenarioValidationError as exc:
        assert "场景 ID 重复: dup" in str(exc)
    else:
        raise AssertionError("expected ScenarioValidationError")


def test_scenario_loader_validate_reports_missing_tags(tmp_path):
    scenario_file = tmp_path / "tags.json"
    scenario_file.write_text(
        """
        {
          "scenarios": [
            {"id":"demo","category":"contact","messages":["1"],"assertions":[]}
          ]
        }
        """,
        encoding="utf-8",
    )

    result = ScenarioLoader(scenario_file).validate(require_tags=False)

    assert result["errors"] == []
    assert result["warnings"] == ["场景 demo 缺少 tags"]


def test_assertion_evaluator_checks_text_and_profile():
    from tests.real_ai.scenario_runner import ScenarioAssertion, ScenarioCase, TurnRecord

    scenario = ScenarioCase(
        scenario_id="demo",
        category="faq",
        tags=["smoke"],
        description="",
        messages=["你好"],
        assertions=[
            ScenarioAssertion(type="response_contains_any", turn=1, values=["联盟"]),
            ScenarioAssertion(type="response_not_contains_any", turn=1, values=["电话"]),
            ScenarioAssertion(type="profile_field_not_equals", field="occupation", expected="值"),
        ],
    )
    turns = [TurnRecord(index=1, user_message="你好", assistant_response="我们是同城脱单联盟，先聊聊。", collected_info={})]
    profile = {"occupation": None}

    failures = AssertionEvaluator().evaluate(scenario, turns, profile)

    assert failures == []


def test_markdown_report_contains_failure_replay(tmp_path):
    from tests.real_ai.scenario_runner import RealAIScenarioRunner

    runner = RealAIScenarioRunner(tmp_path, report_dir=tmp_path)
    report = {
        "started_at": "2026-01-01T10:00:00",
        "ended_at": "2026-01-01T10:01:00",
        "scenario_file": "demo",
        "summary": {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "total_duration_seconds": 1.2,
            "avg_duration_seconds": 1.2,
            "max_duration_seconds": 1.2,
            "token_usage": {"total_tokens": 123, "call_count": 2}
        },
        "results": [
            {
                "scenario_id": "demo",
                "category": "contact",
                "tags": ["critical", "smoke"],
                "passed": False,
                "checks_total": 2,
                "checks_passed": 1,
                "failures": [
                    {
                        "assertion_type": "response_not_contains_any",
                        "message": "turn=2 不应包含关键词 ['电话']",
                        "turn": 2,
                        "field": None
                    }
                ],
                "turns": [
                    {"index": 1, "user_message": "你好", "assistant_response": "你好呀", "collected_info": {}},
                    {"index": 2, "user_message": "你是中介吗", "assistant_response": "我们是同城脱单联盟，方便留个电话吗", "collected_info": {}}
                ],
                "final_profile": {},
                "duration_seconds": 1.2
            }
        ],
    }

    markdown = runner._build_markdown_report(report)

    assert "## 失败详情" in markdown
    assert "失败轮次精简回放" in markdown
    assert "Turn 2 用户: 你是中介吗" in markdown
    assert "critical, smoke" in markdown
    assert "Token: 123" in markdown


def test_load_failed_ids_reads_failed_cases(tmp_path):
    report_path = tmp_path / "latest.json"
    report_path.write_text(
        """
        {
          "results": [
            {"scenario_id": "a", "passed": false},
            {"scenario_id": "b", "passed": true},
            {"scenario_id": "c", "passed": false}
          ]
        }
        """,
        encoding="utf-8",
    )

    failed = load_failed_ids(str(report_path))

    assert failed == {"a", "c"}


def test_apply_filters_supports_shuffle_and_max():
    scenarios = ScenarioLoader("tests/real_ai/scenarios").load()
    args = Namespace(
        category="contact",
        tags=None,
        scenario_ids=None,
        rerun_failed=False,
        rerun_failed_from="",
        shuffle=True,
        seed=1,
        max_scenarios=3,
    )

    filtered = apply_filters(scenarios, args)

    assert len(filtered) == 3
    assert all(item.category == "contact" for item in filtered)


def test_apply_profile_sets_default_tags():
    args = Namespace(
        profile="smoke",
        tags=None,
    )

    updated = apply_profile(args)

    assert updated.tags == RUN_PROFILES["smoke"]["tags"]


def test_print_progress_outputs_start_and_finish(capsys):
    from tests.real_ai.scenario_runner import FailureDetail, ScenarioCase, ScenarioResult, TurnRecord

    scenario = ScenarioCase(
        scenario_id="demo",
        category="contact",
        tags=["smoke"],
        description="",
        messages=["你好"],
        assertions=[],
    )

    print_progress("start", scenario, 1, 2, None)
    print_progress(
        "turn",
        scenario,
        1,
        2,
        TurnRecord(index=1, user_message="你好", assistant_response="你好呀", collected_info={"sex": "未留", "location": "深圳"}),
        verbose=True,
    )
    result = ScenarioResult(
        scenario_id="demo",
        category="contact",
        tags=["smoke"],
        passed=False,
        checks_total=1,
        checks_passed=0,
        failures=[FailureDetail(assertion_type="response_contains_any", message="missing keyword")],
        turns=[TurnRecord(index=1, user_message="你好", assistant_response="你好呀", collected_info={"location": "深圳"})],
        final_profile={},
        duration_seconds=1.23,
    )
    print_progress("finish", scenario, 1, 2, result)

    captured = capsys.readouterr()
    assert "[1/2] RUN demo (contact)" in captured.out
    assert "demo scenario" not in captured.out
    assert "U1: 你好" in captured.out
    assert "I1: location=深圳" in captured.out
    assert "[1/2] FAIL demo (1.23s)" in captured.out
    assert "missing keyword" in captured.out
    assert "transcript:" in captured.out


def test_runner_tolerates_empty_message_for_mq_placeholder_scenario(tmp_path, monkeypatch):
    from tests.real_ai.scenario_runner import RealAIScenarioRunner, ScenarioCase

    runner = RealAIScenarioRunner(tmp_path, report_dir=tmp_path)

    async def _noop_reset(_account_id):
        return None

    async def _noop_profile(_account_id):
        return {"success": True, "profile": {}}

    async def _should_not_be_called(_request):
        raise AssertionError("process_chat_request should not be called for invalid turn")

    monkeypatch.setattr(runner.chat_service, "reset_user_conversation", _noop_reset)
    monkeypatch.setattr(runner.chat_service, "get_user_profile", _noop_profile)
    monkeypatch.setattr(runner.chat_service, "process_chat_request", _should_not_be_called)

    scenario = ScenarioCase(
        scenario_id="invalid_empty_question",
        category="mq",
        tags=["pending"],
        description="",
        messages=[" "],
        assertions=[],
    )

    result = asyncio.run(runner._run_one(scenario))

    assert result.passed is True
    assert result.checks_total == 0
    assert result.checks_passed == 0
    assert result.failures == []


def test_runner_records_runtime_failure_for_non_mq_invalid_turn(tmp_path, monkeypatch):
    from tests.real_ai.scenario_runner import RealAIScenarioRunner, ScenarioCase

    runner = RealAIScenarioRunner(tmp_path, report_dir=tmp_path)

    async def _noop_reset(_account_id):
        return None

    async def _noop_profile(_account_id):
        return {"success": True, "profile": {}}

    async def _should_not_be_called(_request):
        raise AssertionError("process_chat_request should not be called for invalid turn")

    monkeypatch.setattr(runner.chat_service, "reset_user_conversation", _noop_reset)
    monkeypatch.setattr(runner.chat_service, "get_user_profile", _noop_profile)
    monkeypatch.setattr(runner.chat_service, "process_chat_request", _should_not_be_called)

    scenario = ScenarioCase(
        scenario_id="invalid_empty_question_non_mq",
        category="humanlike_queue",
        tags=["pending"],
        description="",
        messages=[" "],
        assertions=[],
    )

    result = asyncio.run(runner._run_one(scenario))

    assert result.passed is False
    assert result.checks_total == 1
    assert result.checks_passed == 0
    assert len(result.failures) == 1
    assert result.failures[0].assertion_type == "scenario_runtime_error"
    assert "Question cannot be empty" in result.failures[0].message
