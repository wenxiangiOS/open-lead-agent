"""真实 AI 多轮场景回归执行器。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.models.requests import ChatRequest
from src.services.ai_service import AIService
from src.services.core.chat_service import ChatService
from src.services.data.user_service import UserService


def _clear_proxy_env() -> None:
    """避免本地代理影响火山引擎请求。"""
    for proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
        os.environ.pop(proxy_var, None)
    os.environ["NO_PROXY"] = ".bigmodel.cn,bigmodel.cn,.doubao.com,doubao.com,.volces.com,volces.com,localhost,127.0.0.1,::1,.cn"
    os.environ["no_proxy"] = ".bigmodel.cn,bigmodel.cn,.doubao.com,doubao.com,.volces.com,volces.com,localhost,127.0.0.1,::1,.cn"


class ScenarioValidationError(ValueError):
    """场景定义不合法。"""


@dataclass
class ScenarioAssertion:
    """单条断言。"""

    type: str
    values: List[str] = field(default_factory=list)
    field: Optional[str] = None
    expected: Any = None
    turn: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioAssertion":
        return cls(
            type=data["type"],
            values=list(data.get("values", [])),
            field=data.get("field"),
            expected=data.get("expected"),
            turn=data.get("turn"),
        )


@dataclass
class ScenarioCase:
    """单个多轮场景。"""

    scenario_id: str
    category: str
    tags: List[str]
    description: str
    messages: List[str]
    assertions: List[ScenarioAssertion]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioCase":
        return cls(
            scenario_id=data["id"],
            category=data["category"],
            tags=list(data.get("tags", [])),
            description=data.get("description", ""),
            messages=list(data["messages"]),
            assertions=[ScenarioAssertion.from_dict(item) for item in data.get("assertions", [])],
        )


@dataclass
class TurnRecord:
    """单轮对话记录。"""

    index: int
    user_message: str
    assistant_response: str
    collected_info: Dict[str, Any]


@dataclass
class FailureDetail:
    """断言失败详情。"""

    assertion_type: str
    message: str
    turn: Optional[int] = None
    field: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assertion_type": self.assertion_type,
            "message": self.message,
            "turn": self.turn,
            "field": self.field,
        }


@dataclass
class ScenarioResult:
    """单个场景执行结果。"""

    scenario_id: str
    category: str
    tags: List[str]
    passed: bool
    checks_total: int
    checks_passed: int
    failures: List[FailureDetail]
    turns: List[TurnRecord]
    final_profile: Dict[str, Any]
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "tags": self.tags,
            "passed": self.passed,
            "checks_total": self.checks_total,
            "checks_passed": self.checks_passed,
            "failures": [item.to_dict() for item in self.failures],
            "turns": [
                {
                    "index": turn.index,
                    "user_message": turn.user_message,
                    "assistant_response": turn.assistant_response,
                    "collected_info": turn.collected_info,
                }
                for turn in self.turns
            ],
            "final_profile": self.final_profile,
            "duration_seconds": round(self.duration_seconds, 3),
        }


class ScenarioLoader:
    """加载 JSON 场景定义。"""

    def __init__(self, scenario_file: str | Path):
        self.scenario_file = Path(scenario_file)

    def load(self) -> List[ScenarioCase]:
        scenario_files = self._resolve_files()
        scenarios: List[ScenarioCase] = []
        for file_path in scenario_files:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            scenarios.extend(ScenarioCase.from_dict(item) for item in raw["scenarios"])
        errors, _warnings = self.validate_scenarios(scenarios)
        if errors:
            raise ScenarioValidationError("; ".join(errors))
        return scenarios

    def validate(self, require_tags: bool = False) -> Dict[str, List[str]]:
        scenario_files = self._resolve_files()
        scenarios: List[ScenarioCase] = []
        for file_path in scenario_files:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            scenarios.extend(ScenarioCase.from_dict(item) for item in raw["scenarios"])
        errors, warnings = self.validate_scenarios(scenarios, require_tags=require_tags)
        return {"errors": errors, "warnings": warnings}

    def _resolve_files(self) -> List[Path]:
        if self.scenario_file.is_dir():
            return sorted(self.scenario_file.glob("*.json"))
        return [self.scenario_file]

    @staticmethod
    def validate_scenarios(
        scenarios: List[ScenarioCase],
        require_tags: bool = False,
    ) -> tuple[List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []
        seen_ids: Dict[str, int] = {}

        for scenario in scenarios:
            seen_ids[scenario.scenario_id] = seen_ids.get(scenario.scenario_id, 0) + 1
            if not scenario.category:
                errors.append(f"场景 {scenario.scenario_id} 缺少 category")
            if not scenario.messages:
                errors.append(f"场景 {scenario.scenario_id} 缺少 messages")
            if not scenario.tags:
                message = f"场景 {scenario.scenario_id} 缺少 tags"
                if require_tags:
                    errors.append(message)
                else:
                    warnings.append(message)

        duplicate_ids = sorted([scenario_id for scenario_id, count in seen_ids.items() if count > 1])
        for scenario_id in duplicate_ids:
            errors.append(f"场景 ID 重复: {scenario_id}")

        return errors, warnings


class AssertionEvaluator:
    """执行场景断言。"""

    def evaluate(self, scenario: ScenarioCase, turns: List[TurnRecord], final_profile: Dict[str, Any]) -> List[FailureDetail]:
        failures: List[FailureDetail] = []

        for assertion in scenario.assertions:
            detail = self._evaluate_one(assertion, turns, final_profile)
            if detail:
                failures.append(detail)

        return failures

    def _evaluate_one(
        self,
        assertion: ScenarioAssertion,
        turns: List[TurnRecord],
        final_profile: Dict[str, Any],
    ) -> Optional[FailureDetail]:
        if assertion.type.startswith("response_"):
            response = self._get_turn_response(assertion.turn, turns)
            if response is None:
                return FailureDetail(
                    assertion_type=assertion.type,
                    turn=assertion.turn,
                    message=f"turn={assertion.turn} 不存在，无法执行断言 {assertion.type}",
                )
            return self._evaluate_text_assertion(assertion, response, prefix=f"turn={assertion.turn}")

        if assertion.type.startswith("final_response_"):
            response = turns[-1].assistant_response if turns else ""
            mapped = ScenarioAssertion(
                type=assertion.type.replace("final_", "", 1),
                values=assertion.values,
            )
            detail = self._evaluate_text_assertion(mapped, response, prefix="final_response")
            if detail:
                detail.assertion_type = assertion.type
                detail.turn = len(turns) if turns else None
            return detail

        if assertion.type == "profile_field_equals":
            actual = final_profile.get(assertion.field or "")
            if actual != assertion.expected:
                return FailureDetail(
                    assertion_type=assertion.type,
                    field=assertion.field,
                    message=f"profile.{assertion.field} 期望 {assertion.expected!r}，实际 {actual!r}",
                )
            return None

        if assertion.type == "profile_field_not_equals":
            actual = final_profile.get(assertion.field or "")
            if actual == assertion.expected:
                return FailureDetail(
                    assertion_type=assertion.type,
                    field=assertion.field,
                    message=f"profile.{assertion.field} 不应等于 {assertion.expected!r}",
                )
            return None

        if assertion.type == "profile_field_truthy":
            actual = final_profile.get(assertion.field or "")
            if not actual:
                return FailureDetail(
                    assertion_type=assertion.type,
                    field=assertion.field,
                    message=f"profile.{assertion.field} 期望为真值，实际 {actual!r}",
                )
            return None

        if assertion.type == "profile_field_falsey":
            actual = final_profile.get(assertion.field or "")
            if actual:
                return FailureDetail(
                    assertion_type=assertion.type,
                    field=assertion.field,
                    message=f"profile.{assertion.field} 期望为空/假值，实际 {actual!r}",
                )
            return None

        return FailureDetail(
            assertion_type=assertion.type,
            message=f"未知断言类型: {assertion.type}",
        )

    def _evaluate_text_assertion(
        self,
        assertion: ScenarioAssertion,
        text: str,
        prefix: str,
    ) -> Optional[FailureDetail]:
        if assertion.type.endswith("not_contains_any"):
            hits = [value for value in assertion.values if value in text]
            if hits:
                return FailureDetail(
                    assertion_type=assertion.type,
                    turn=assertion.turn,
                    message=f"{prefix} 不应包含关键词 {hits!r}，实际 {text!r}",
                )
            return None

        if assertion.type.endswith("contains_any"):
            if not any(value in text for value in assertion.values):
                return FailureDetail(
                    assertion_type=assertion.type,
                    turn=assertion.turn,
                    message=f"{prefix} 需要包含任一关键词 {assertion.values!r}，实际 {text!r}",
                )
            return None

        return FailureDetail(
            assertion_type=assertion.type,
            turn=assertion.turn,
            message=f"未知文本断言类型: {assertion.type}",
        )

    @staticmethod
    def _get_turn_response(turn: Optional[int], turns: List[TurnRecord]) -> Optional[str]:
        if turn is None:
            return None
        if turn < 1 or turn > len(turns):
            return None
        return turns[turn - 1].assistant_response


class RealAIScenarioRunner:
    """真实 AI 场景回归执行器。"""

    def __init__(self, scenario_file: str | Path, report_dir: str | Path = "reports/real_ai") -> None:
        _clear_proxy_env()
        self.scenario_file = Path(scenario_file)
        self.report_dir = Path(report_dir)
        self.loader = ScenarioLoader(self.scenario_file)
        self.evaluator = AssertionEvaluator()
        self.ai_service = AIService()
        self.user_service = UserService()
        self.chat_service = ChatService(self.ai_service, self.user_service)

    def load_scenarios(self) -> List[ScenarioCase]:
        return self.loader.load()

    async def run(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        scenario_ids: Optional[List[str]] = None,
        stop_on_failure: bool = False,
        progress_callback=None,
    ) -> Dict[str, Any]:
        await AIService.reset_token_usage()
        scenarios = self.load_scenarios()
        if category:
            scenarios = [item for item in scenarios if item.category == category]
        if tags:
            required = set(tags)
            scenarios = [item for item in scenarios if required.issubset(set(item.tags))]
        if scenario_ids:
            allowed = set(scenario_ids)
            scenarios = [item for item in scenarios if item.scenario_id in allowed]

        results: List[ScenarioResult] = []
        started_at = datetime.now()

        total = len(scenarios)
        for index, scenario in enumerate(scenarios, start=1):
            if progress_callback:
                progress_callback("start", scenario, index, total, None)
            result = await self._run_one(scenario, progress_callback, index, total)
            results.append(result)
            if progress_callback:
                progress_callback("finish", scenario, index, total, result)
            if stop_on_failure and not result.passed:
                break

        token_usage = await AIService.get_token_usage()
        report = self._build_report(results, started_at, token_usage)
        self._write_report(report)
        return report

    async def _run_one(self, scenario: ScenarioCase, progress_callback=None, scenario_index: Optional[int] = None, total: Optional[int] = None) -> ScenarioResult:
        started = datetime.now()
        account_id = f"real_ai_{scenario.scenario_id}_{uuid.uuid4().hex[:8]}"
        dialog_id = f"real_ai_{uuid.uuid4().hex[:10]}"

        await self.chat_service.reset_user_conversation(account_id)

        turns: List[TurnRecord] = []

        for index, message in enumerate(scenario.messages, start=1):
            request = ChatRequest(
                question=message,
                accountId=account_id,
                dialogId=f"{dialog_id}_{index}",
            )
            result = await self.chat_service.process_chat_request(request)
            turn = TurnRecord(
                index=index,
                user_message=message,
                assistant_response=result.get("response", ""),
                collected_info=result.get("collected_info", {}),
            )
            turns.append(turn)
            if progress_callback:
                progress_callback("turn", scenario, scenario_index, total, turn)
            await asyncio.sleep(0.1)

        profile_result = await self.chat_service.get_user_profile(account_id)
        final_profile = profile_result.get("profile", {}) if profile_result.get("success") else {}

        failures = self.evaluator.evaluate(scenario, turns, final_profile)
        duration = (datetime.now() - started).total_seconds()
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            category=scenario.category,
            tags=scenario.tags,
            passed=not failures,
            checks_total=len(scenario.assertions),
            checks_passed=len(scenario.assertions) - len(failures),
            failures=failures,
            turns=turns,
            final_profile=final_profile,
            duration_seconds=duration,
        )

    def _build_report(
        self,
        results: List[ScenarioResult],
        started_at: datetime,
        token_usage: Dict[str, int],
    ) -> Dict[str, Any]:
        passed = sum(1 for item in results if item.passed)
        failed = len(results) - passed
        ended_at = datetime.now()
        durations = [item.duration_seconds for item in results]
        total_duration = round(sum(durations), 3) if durations else 0.0
        avg_duration = round(total_duration / len(durations), 3) if durations else 0.0
        max_duration = round(max(durations), 3) if durations else 0.0

        return {
            "started_at": started_at.isoformat(timespec="seconds"),
            "ended_at": ended_at.isoformat(timespec="seconds"),
            "scenario_file": str(self.scenario_file),
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "total_duration_seconds": total_duration,
                "avg_duration_seconds": avg_duration,
                "max_duration_seconds": max_duration,
                "token_usage": token_usage,
            },
            "results": [item.to_dict() for item in results],
        }

    def _write_report(self, report: Dict[str, Any]) -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"real_ai_regression_{timestamp}.json"
        latest_path = self.report_dir / "latest.json"
        markdown_path = self.report_dir / f"real_ai_regression_{timestamp}.md"
        markdown_latest_path = self.report_dir / "latest.md"
        json_text = json.dumps(report, ensure_ascii=False, indent=2)
        json_path.write_text(json_text, encoding="utf-8")
        latest_path.write_text(json_text, encoding="utf-8")
        markdown_text = self._build_markdown_report(report)
        markdown_path.write_text(markdown_text, encoding="utf-8")
        markdown_latest_path.write_text(markdown_text, encoding="utf-8")

    def _build_markdown_report(self, report: Dict[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# 真实 AI 回归报告",
            "",
            f"- 开始时间: {report['started_at']}",
            f"- 结束时间: {report['ended_at']}",
            f"- 场景源: `{report['scenario_file']}`",
            f"- 总场景: {summary['total']}",
            f"- 通过: {summary['passed']}",
            f"- 失败: {summary['failed']}",
            f"- 总耗时: {summary['total_duration_seconds']}s",
            f"- 平均耗时: {summary['avg_duration_seconds']}s",
            f"- 最长耗时: {summary['max_duration_seconds']}s",
            f"- Token: {summary['token_usage']['total_tokens']} (调用 {summary['token_usage']['call_count']} 次)",
            "",
            "## 结果概览",
            "",
        ]

        for item in report["results"]:
            status = "PASS" if item["passed"] else "FAIL"
            tags = ", ".join(item.get("tags", [])) or "-"
            lines.append(f"- `{status}` `{item['scenario_id']}` | category=`{item['category']}` | tags=`{tags}`")

        failed_results = [item for item in report["results"] if not item["passed"]]
        if not failed_results:
            lines.extend(["", "## 失败详情", "", "无失败场景。"])
            return "\n".join(lines)

        lines.extend(["", "## 失败详情", ""])
        for item in failed_results:
            lines.append(f"### {item['scenario_id']}")
            lines.append("")
            lines.append(f"- 分类: `{item['category']}`")
            lines.append(f"- 标签: `{', '.join(item.get('tags', [])) or '-'}`")
            lines.append(f"- 断言通过: {item['checks_passed']}/{item['checks_total']}")
            lines.append("- 失败摘要:")
            for failure in item["failures"]:
                turn_label = f"turn={failure['turn']}" if failure.get("turn") else "turn=-"
                field_label = f" field={failure['field']}" if failure.get("field") else ""
                lines.append(f"  - [{failure['assertion_type']}] {turn_label}{field_label} {failure['message']}")
            lines.append("- 失败轮次精简回放:")
            failure_turns = sorted({failure["turn"] for failure in item["failures"] if failure.get("turn")})
            if failure_turns:
                for turn in item["turns"]:
                    if turn["index"] in failure_turns:
                        response = turn["assistant_response"].replace("\n", " ")
                        lines.append(f"  - Turn {turn['index']} 用户: {turn['user_message']}")
                        lines.append(f"    AI: {response}")
            lines.append("- 对话回放:")
            for turn in item["turns"]:
                response = turn["assistant_response"].replace("\n", " ")
                lines.append(f"  - Turn {turn['index']} 用户: {turn['user_message']}")
                lines.append(f"    AI: {response}")
            lines.append("")

        return "\n".join(lines)
