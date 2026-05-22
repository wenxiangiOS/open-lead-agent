"""本地终端聊天与模板工具命令。Interactive terminal chat and template utilities."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.conversation import ChatRequest, ConversationEngine
from src.llm import OpenAICompatibleLLM
from src.storage import MemoryStore
from src.templates import (
    GuidedFAQ,
    GuidedTemplateAnswers,
    GuidedTemplateOptions,
    TemplateScaffoldOptions,
    create_guided_template,
    create_template_scaffold,
    format_validation_report,
    get_active_template,
    parse_comma_list,
    parse_faq_lines,
    validate_template_config,
)
from src.understanding.context import configured_item_map
from src.understanding.normalization import FieldNormalizer

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TIMING_STAGE_LABELS = {
    "state_load": "读取会话资料",
    "understanding": "理解用户与提取字段",
    "profile_update": "写入本轮资料",
    "history_save_user": "保存用户消息",
    "field_skip_check": "判断跳过字段",
    "knowledge": "FAQ/RAG 检索",
    "effective_ask": "有效询问计数",
    "field_state_contact_gate": "字段状态与联系方式门槛",
    "decision": "决定下一步动作",
    "expression_plan": "拟人化表达规划",
    "response_build": "生成 AI 回复",
    "state_save_assistant": "保存 AI 回复",
}

LLM_PURPOSE_LABELS = {
    "understanding": "理解提取 LLM",
    "response": "回复生成 LLM",
}

TURN_MODE_LABELS = {
    "dense_intro": "大段资料输入",
    "default": "普通输入",
}

FIELD_BUCKET_LABELS = {
    "accepted": "已识别",
    "provisional": "低置信暂存",
    "pending": "待确认",
    "rejected": "未采纳",
}

DECISION_ACTION_LABELS = {
    "ask_field": "继续收集资料",
    "answer_only": "只回答/承接，不追问字段",
    "answer_then_ask": "先回答问题，再回到资料收集",
    "confirm_field": "确认字段",
    "ask_contact": "收集联系方式",
    "close": "收尾",
    "end": "结束对话",
}

DECISION_REASON_LABELS = {
    "opening:greeting_pause": "用户刚回应开场问候，先低压承接",
    "natural_followup:contextual_medium_followup": "用户刚提供了相关资料，顺着上下文追问更自然",
    "core_main_with_optional_side": "继续补齐核心资料",
}

ROUTE_LABELS = {
    "model": "模型生成",
    "model+repair": "模型生成后被质量检查修复",
    "decision_response": "系统固定回复",
    "fallback_exception": "模型异常后的兜底回复",
    "fallback_exception+repair": "模型异常后兜底并修复",
    "fallback_empty_response": "模型空回复后的兜底回复",
    "fallback_empty_response+repair": "模型空回复后兜底并修复",
    "fallback_unconfigured_llm": "未配置模型时的兜底回复",
    "fallback_unconfigured_llm+repair": "未配置模型时兜底并修复",
}


def _divider(char: str = "=", width: int = 52) -> str:
    return char * width


def _print_json(label: str, value: Any) -> None:
    print(f"\n{label}:")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _format_error_hint(exc: Exception) -> tuple[str, str]:
    message = str(exc) or exc.__class__.__name__
    lowered = message.lower()
    exc_name = exc.__class__.__name__
    if "timeout" in lowered or "timed out" in lowered or exc_name == "TimeoutError":
        return (
            "模型请求超时 / LLM request timed out",
            "检查网络、LLM_BASE_URL、LLM_MODEL，或临时调大 LLM_TIMEOUT_SECONDS。",
        )
    if "connection" in lowered or "connect" in lowered or "nodename" in lowered:
        return (
            "模型连接失败 / LLM connection failed",
            "检查 LLM_BASE_URL 是否正确、网络是否可用、当前环境是否允许访问模型服务。",
        )
    if "api_key" in lowered or "authentication" in lowered or "unauthorized" in lowered:
        return (
            "模型鉴权失败 / LLM authentication failed",
            "检查 .env 里的 LLM_API_KEY 是否填写正确。",
        )
    return (
        f"AI 调用失败 / AI call failed ({exc_name})",
        "检查 LLM_API_KEY / LLM_MODEL / LLM_BASE_URL，或使用 --debug-turn 查看本轮状态。",
    )


def _print_turn_log(response: Any, llm: OpenAICompatibleLLM, template: Any = None) -> None:
    print("\n[测试日志]")
    field_labels = _field_label_map(template)
    debug_timing = getattr(response, "debug_timing", None)
    if debug_timing:
        _print_timing_log(debug_timing)
    debug_llm_usage = getattr(response, "debug_llm_usage", None)
    if debug_llm_usage:
        _print_llm_usage_log(debug_llm_usage)
    _print_model_log(llm)
    debug_understanding = getattr(response, "debug_understanding", None)
    if debug_understanding:
        _print_understanding_log(debug_understanding, field_labels)
    if getattr(response, "debug_decision", None):
        _print_decision_log(response.debug_decision, field_labels)
    debug_contact_gate = getattr(response, "debug_contact_gate", None)
    if debug_contact_gate:
        _print_contact_gate_log(debug_contact_gate, field_labels)
    debug_response = getattr(response, "debug_response", None)
    if debug_response or getattr(response, "debug_quality_check", None):
        _print_response_log(
            debug_response or {},
            getattr(response, "debug_quality_check", None) or {},
            getattr(response, "rag_sources", []),
        )
    if response.collected:
        print(f"  本轮入库字段: {_format_field_list(response.collected.keys(), field_labels)}")


def _print_model_log(llm: OpenAICompatibleLLM) -> None:
    status = "已配置" if llm.configured else "未配置"
    print("  模型配置:")
    print(f"    - provider: {llm.settings.provider}")
    print(f"    - model: {llm.settings.model or '未填写'}")
    print(f"    - 状态: {status}")


def _print_understanding_log(
    debug_understanding: dict[str, Any],
    field_labels: dict[str, str],
) -> None:
    plan = debug_understanding.get("persistence_plan", {})
    semantic = debug_understanding.get("semantic_frame", {})
    observation_log = plan.get("observation_log") or []
    mode = TURN_MODE_LABELS.get(str(semantic.get("turn_mode") or ""), semantic.get("turn_mode"))
    print("  字段提取:")
    print(f"    - 输入类型: {mode or '未知'}")
    print(f"    - 识别到字段数: {len(observation_log)}")
    _print_field_bucket(
        "accepted",
        plan.get("accepted_fields") or {},
        observation_log,
        field_labels,
    )
    _print_field_bucket(
        "provisional",
        plan.get("provisional_fields") or {},
        observation_log,
        field_labels,
    )
    _print_field_bucket(
        "pending",
        plan.get("pending_fields") or {},
        observation_log,
        field_labels,
    )
    _print_field_bucket(
        "rejected",
        plan.get("rejected_fields") or {},
        observation_log,
        field_labels,
    )


def _print_decision_log(
    decision: dict[str, Any],
    field_labels: dict[str, str],
) -> None:
    action = str(decision.get("action") or "")
    reason = str(decision.get("reason") or "")
    target = decision.get("target")
    side_target = decision.get("side_target")
    print("  下一步决策:")
    print(f"    - 本轮动作: {DECISION_ACTION_LABELS.get(action, action or '未知')}")
    print(f"    - 下一字段: {_field_label(target, field_labels) if target else '无'}")
    if side_target:
        print(f"    - 顺带字段: {_field_label(side_target, field_labels)}")
    reason_label = DECISION_REASON_LABELS.get(reason, reason or "未说明")
    print(f"    - 原因: {reason_label}")


def _print_contact_gate_log(
    gate: dict[str, Any],
    field_labels: dict[str, str],
) -> None:
    required = gate.get("required_fields") or []
    covered = gate.get("covered") or []
    uncovered = gate.get("uncovered") or []
    optional = gate.get("optional_fields") or []
    optional_covered = gate.get("optional_covered") or []
    optional_uncovered = gate.get("optional_uncovered") or []
    print("  联系方式门槛:")
    print(f"    - 是否可以要联系方式: {'是' if gate.get('allowed') else '否'}")
    print(f"    - 核心字段覆盖: {len(covered)}/{len(required)}")
    if uncovered:
        print(f"    - 核心还未覆盖: {_format_field_list(uncovered, field_labels)}")
    else:
        print("    - 核心还未覆盖: 无")
    if optional:
        print(f"    - 中等字段覆盖: {len(optional_covered)}/{len(optional)}")
        if optional_uncovered:
            print(f"    - 中等还未覆盖: {_format_field_list(optional_uncovered, field_labels)}")
        else:
            print("    - 中等还未覆盖: 无")
    if gate.get("min_required_collected", 0) > 0:
        collected = gate.get("collected") or []
        print(
            "    - 核心实际收集: "
            f"{len(collected)}/{gate.get('min_required_collected')}（最低要求）"
        )
    print("    - 覆盖说明: 已收集，或已有效询问到上限，或用户明确跳过")


def _print_response_log(
    debug_response: dict[str, Any],
    quality: dict[str, Any],
    rag_sources: list[str],
) -> None:
    route = str(debug_response.get("route") or "")
    error = str(debug_response.get("error") or "")
    passed = quality.get("passed")
    issues = quality.get("issues") or []
    print("  回复生成:")
    print(f"    - 来源: {ROUTE_LABELS.get(route, route or '未知')}")
    if error:
        print(f"    - 状态: 失败，错误={error}")
    else:
        print("    - 状态: 成功")
    if debug_response.get("chars") is not None:
        print(f"    - 回复长度: {debug_response.get('chars')}字")
    if passed is not None:
        print(f"    - 质量检查: {'通过' if passed else '未通过'}")
    if issues:
        print(f"    - 质量问题: {issues}")
    if rag_sources:
        print(f"    - RAG 来源数: {len(rag_sources)}")


def _print_timing_log(debug_timing: dict[str, Any]) -> None:
    print(f"  总耗时: {_format_seconds(debug_timing.get('total_ms'))}秒")
    stages = debug_timing.get("stages") or {}
    if not stages:
        return
    print("  分步耗时:")
    for name, elapsed_ms in stages.items():
        if name == "total" or not _should_print_timing_stage(elapsed_ms):
            continue
        label = TIMING_STAGE_LABELS.get(name, name)
        print(f"    - {label}: {_format_seconds(elapsed_ms)}秒")


def _print_llm_usage_log(usage: dict[str, Any]) -> None:
    print("  AI Token:")
    print(
        f"    - 总输入: {_format_token_value(usage.get('input_tokens'))} tokens"
        f"{_estimate_suffix(usage, 'input')}"
    )
    print(
        f"    - 总输出: {_format_token_value(usage.get('output_tokens'))} tokens"
        f"{_estimate_suffix(usage, 'output')}"
    )
    print(f"    - 总计: {_format_token_value(usage.get('total_tokens'))} tokens")
    print(f"    - 模型调用: {usage.get('calls', 0)}次")
    if not usage.get("usage_available"):
        print("    - 说明: provider 未返回精确 usage，括号里显示本地估算 token。")
    details = usage.get("details") or []
    if details:
        print("    - 调用明细:")
    for index, call in enumerate(details, start=1):
        purpose = LLM_PURPOSE_LABELS.get(str(call.get("purpose") or ""), "LLM 调用")
        print(
            f"      {index}. {purpose}: "
            f"耗时 {_format_seconds(call.get('elapsed_ms'))}秒, "
            f"输入 {_format_token_value(call.get('input_tokens'))} tokens"
            f"{_estimate_call_suffix(call, 'input')}, "
            f"输出 {_format_token_value(call.get('output_tokens'))} tokens"
            f"{_estimate_call_suffix(call, 'output')}, "
            f"状态={_call_status(call)}"
        )


def _format_token_value(value: Any) -> str:
    return str(value) if value is not None else "N/A"


def _format_seconds(value_ms: Any) -> str:
    if not isinstance(value_ms, int | float):
        return "N/A"
    return f"{value_ms / 1000:.2f}"


def _should_print_timing_stage(value_ms: Any) -> bool:
    if not isinstance(value_ms, int | float):
        return False
    return round(value_ms / 1000, 2) > 0


def _estimate_suffix(usage: dict[str, Any], direction: str) -> str:
    token_key = f"{direction}_tokens"
    estimate_key = f"estimated_{direction}_tokens"
    if usage.get(token_key) is not None:
        return ""
    return f"（估算≈{usage.get(estimate_key, 0)}）"


def _estimate_call_suffix(call: dict[str, Any], direction: str) -> str:
    token_key = f"{direction}_tokens"
    estimate_key = f"estimated_{direction}_tokens"
    if call.get(token_key) is not None:
        return ""
    return f"（估算≈{call.get(estimate_key, 0)}）"


def _call_status(call: dict[str, Any]) -> str:
    error = call.get("error")
    if error:
        return f"失败，错误={error}"
    return "成功"


def _print_field_bucket(
    name: str,
    values: dict[str, Any],
    observation_log: list[dict[str, Any]],
    field_labels: dict[str, str],
) -> None:
    if not values:
        return
    reasons = _observation_reasons(observation_log)
    parts = []
    for key, value in values.items():
        reason = reasons.get(key, "")
        suffix = f"（{_reason_label(reason)}）" if reason and name == "rejected" else ""
        parts.append(f"{_field_label(key, field_labels)}={value}{suffix}")
    print(f"    - {FIELD_BUCKET_LABELS.get(name, name)}: {'、'.join(parts)}")


def _observation_reasons(observation_log: list[dict[str, Any]]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for item in observation_log:
        field = str(item.get("field") or "")
        if field and field not in reasons:
            reasons[field] = str(item.get("reason") or "")
    return reasons


def _field_label_map(template: Any) -> dict[str, str]:
    if template is None:
        return {}
    labels: dict[str, str] = {}
    for field in getattr(template, "fields", []) or []:
        labels[getattr(field, "key", "")] = getattr(field, "label", "")
    contact = getattr(template, "contact", None)
    for method in getattr(contact, "methods", []) or []:
        labels[getattr(method, "key", "")] = getattr(method, "label", "")
    return {key: value for key, value in labels.items() if key and value}


def _field_label(field_key: Any, field_labels: dict[str, str]) -> str:
    key = str(field_key or "")
    if not key:
        return "无"
    label = field_labels.get(key)
    return f"{label}({key})" if label else key


def _format_field_list(field_keys: Any, field_labels: dict[str, str]) -> str:
    return "、".join(_field_label(key, field_labels) for key in field_keys) or "无"


def _reason_label(reason: str) -> str:
    reason_labels = {
        "invalid_format": "格式不符合字段",
        "unknown_field": "未知字段",
        "already_collected": "已有字段未直接覆盖",
        "blocked_by_permission": "字段权限拦截",
    }
    return reason_labels.get(reason, reason)


def _parse_set_command(text: str) -> tuple[str, str] | None:
    raw = text
    if raw.startswith("/set"):
        raw = raw.removeprefix("/set").strip()
    elif raw.startswith("set"):
        raw = raw.removeprefix("set").strip()
    if "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return None
    return key, value


def _normalize_pending_field_value(
    template: Any,
    field_key: str,
    raw_value: str,
) -> tuple[bool, Any]:
    config = configured_item_map(template).get(field_key)
    if config is None:
        return False, None
    normalized = FieldNormalizer().normalize(config, raw_value)
    if normalized in (None, "", []):
        return False, None
    return True, normalized


def _has_invalid_terminal_text(text: str) -> bool:
    return any(0xDC80 <= ord(char) <= 0xDCFF for char in text)


def _normalize_terminal_text(text: str) -> str:
    """Repair or remove terminal surrogateescape bytes without discarding good text."""
    if not _has_invalid_terminal_text(text):
        return text

    if _has_regular_cjk_text(text):
        return _strip_surrogateescape_chars(text)

    raw = text.encode(sys.stdin.encoding or "utf-8", "surrogateescape")
    for encoding in ("utf-8", "gb18030"):
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not _has_invalid_terminal_text(decoded):
            return decoded

    return _strip_surrogateescape_chars(text)


def _has_regular_cjk_text(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text if not _is_surrogateescape(char))


def _strip_surrogateescape_chars(text: str) -> str:
    return "".join(char for char in text if not _is_surrogateescape(char))


def _is_surrogateescape(char: str) -> bool:
    return 0xDC80 <= ord(char) <= 0xDCFF


def _make_dialog_id(account_id: str) -> str:
    return f"{account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _state_id(account_id: str, dialog_id: str) -> str:
    return f"{account_id}:{dialog_id}"


def _print_help() -> None:
    print("命令:")
    print("  quit/exit/q        - 退出")
    print("  user [用户ID]       - 切换用户")
    print("  reset              - 重置当前用户对话")
    print("  profile            - 查看资料")
    print("  history            - 查看历史")
    print("  token              - 查看本地统计")
    print("  template           - 查看当前模板摘要")
    print("  set key=value      - 手动设置资料字段")
    print("  help               - 显示帮助")


def _validate_template_command(template_id: str | None = None) -> int:
    try:
        template = get_active_template(template_id)
    except Exception as exc:
        print("Template validation: FAILED")
        print(f"template: {template_id or 'active'}")
        print(f"- [ERROR] template_load_failed: {exc}")
        return 1

    report = validate_template_config(template)
    print(format_validation_report(report))
    return 0 if report.ok else 1


def _init_template_command(
    template_id: str,
    *,
    name: str = "",
    scenario: str = "lead",
    force: bool = False,
) -> int:
    try:
        result = create_template_scaffold(
            TemplateScaffoldOptions(
                template_id=template_id,
                name=name,
                scenario=scenario,  # type: ignore[arg-type]
                force=force,
            )
        )
    except Exception as exc:
        print("Template scaffold: FAILED")
        print(f"- [ERROR] {exc}")
        return 1

    print("Template scaffold: OK")
    print(f"template: {result.template_id}")
    print(f"directory: {result.template_dir}")
    print("files:")
    for path in result.files:
        print(f"- {path}")
    print(f"\nNext: ACTIVE_TEMPLATE={result.template_id} t --validate-template")
    return 0


def _guided_template_command(
    template_id: str,
    *,
    name: str = "",
    force: bool = False,
) -> int:
    try:
        answers = _collect_guided_template_answers()
        result = create_guided_template(
            GuidedTemplateOptions(
                template_id=template_id,
                name=name or f"{answers.industry}咨询助手",
                answers=answers,
                force=force,
            )
        )
    except (EOFError, KeyboardInterrupt):
        print("\nTemplate guide: cancelled")
        return 1
    except Exception as exc:
        print("Template guide: FAILED")
        print(f"- [ERROR] {exc}")
        return 1

    print("Template guide: OK")
    print(f"template: {result.template_id}")
    print(f"directory: {result.template_dir}")
    print("files:")
    for path in result.files:
        print(f"- {path}")
    print(f"\nNext: ACTIVE_TEMPLATE={result.template_id} t --validate-template")
    print(f"Then: ACTIVE_TEMPLATE={result.template_id} t")
    return 0


def _collect_guided_template_answers() -> GuidedTemplateAnswers:
    print(_divider())
    print("新手模板配置向导")
    print(_divider())
    print("你只需要回答 4 类问题：行业、要收集的字段、联系方式、常见问题。")
    print("看不准的地方可以先用逗号隔开随便写，生成后还能继续改 template.yaml。")
    print(_divider("-"))

    industry = _prompt_required("1. 你是什么行业/场景？例如：教培、招聘、口腔、婚恋")
    fields = parse_comma_list(
        _prompt_required("2. 你要收集哪些字段？用逗号分隔，例如：学生年级, 科目, 学习问题")
    )
    contact_methods = parse_comma_list(
        _prompt_optional("3. 要收集哪些联系方式？用逗号分隔，例如：手机号, 微信, 邮箱")
    )
    faqs = _prompt_faqs()
    opening_message = _prompt_optional(
        "5. 开场白可选。直接回车会自动生成",
        default="",
    )
    if not fields:
        fields = ["需求"]
    return GuidedTemplateAnswers(
        industry=industry,
        fields=fields,
        contact_methods=contact_methods,
        faqs=faqs,
        opening_message=opening_message,
    )


def _prompt_required(prompt: str) -> str:
    while True:
        value = input(f"{prompt}\n> ").strip()
        if value:
            return value
        print("这个不能为空，简单写一句就行。")


def _prompt_optional(prompt: str, *, default: str = "") -> str:
    value = input(f"{prompt}\n> ").strip()
    return value or default


def _prompt_faqs() -> list[GuidedFAQ]:
    print("4. 常见问题怎么答？每行一个，格式：问题=答案")
    print("   例如：怎么收费=收费会根据课程和班型不同，可以先了解需求再说明。")
    print("   直接回车结束。")
    lines = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        lines.append(line)
    return parse_faq_lines(lines)


def _field_items(template: Any) -> list[tuple[str, str]]:
    items = [(field.key, field.label) for field in template.fields]
    items.extend((method.key, method.label) for method in template.contact.methods)
    return items


def _format_profile_value(value: Any) -> str:
    if value in (None, ""):
        return "未留"
    return str(value)


def _print_profile_status(template: Any, profile: dict[str, Any]) -> None:
    print("\n[已收集信息]")
    for key, _label in _field_items(template):
        print(f"  {key}: {_format_profile_value(profile.get(key))}")


def _print_history(history: list[dict[str, str]]) -> None:
    if not history:
        print("\n[历史记录] 暂无")
        return
    print("\n[历史记录]")
    for item in history:
        role = "你" if item["role"] == "user" else "AI"
        print(f"  {role}: {item['content']}")


def _print_token_stats(stats: dict[str, Any]) -> None:
    print("\n[本地统计]")
    print(f"  turns: {stats['turns']}")
    print(f"  prompt_chars: {stats['prompt_chars']}")
    print(f"  response_chars: {stats['response_chars']}")
    print(
        "  exact_tokens: "
        f"input={_format_token_value(stats.get('input_tokens'))}, "
        f"output={_format_token_value(stats.get('output_tokens'))}, "
        f"total={_format_token_value(stats.get('total_tokens'))}"
    )
    print(
        "  estimated_tokens: "
        f"input≈{stats.get('estimated_input_tokens', 0)}, "
        f"output≈{stats.get('estimated_output_tokens', 0)}"
    )
    if not stats.get("has_exact_usage"):
        print("  note: 当前 provider 暂未返回精确 token usage，估算值仅用于本地调试。")


def _new_token_stats() -> dict[str, Any]:
    return {
        "turns": 0,
        "prompt_chars": 0,
        "response_chars": 0,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "estimated_input_tokens": 0,
        "estimated_output_tokens": 0,
        "has_exact_usage": False,
    }


def _update_token_stats(stats: dict[str, Any], response: Any) -> None:
    usage = getattr(response, "debug_llm_usage", None) or {}
    stats["estimated_input_tokens"] += usage.get("estimated_input_tokens") or 0
    stats["estimated_output_tokens"] += usage.get("estimated_output_tokens") or 0
    if usage.get("input_tokens") is not None:
        stats["input_tokens"] = (stats.get("input_tokens") or 0) + usage["input_tokens"]
        stats["has_exact_usage"] = True
    if usage.get("output_tokens") is not None:
        stats["output_tokens"] = (stats.get("output_tokens") or 0) + usage["output_tokens"]
        stats["has_exact_usage"] = True
    if usage.get("total_tokens") is not None:
        stats["total_tokens"] = (stats.get("total_tokens") or 0) + usage["total_tokens"]
        stats["has_exact_usage"] = True


def _print_startup(
    template: Any,
    llm: OpenAICompatibleLLM,
    account_id: str,
    dialog_id: str,
    debug_prompt: bool,
    debug_turn: bool,
) -> None:
    print(_divider())
    print(f"{template.agent.name} AI 客服 - 测试工具")
    print(_divider())
    print(f"模板: {template.template.id} - {template.template.name}")
    print(f"模型: {llm.settings.provider} / {llm.settings.model}")
    print(f"用户ID: {account_id}")
    print(f"对话ID: {dialog_id}")
    if debug_prompt:
        print("调试Prompt: 开启")
    if debug_turn:
        print("测试日志: 开启")
    print(_divider("-"))
    _print_help()
    print(_divider("-"))
    if template.opening.enabled and template.opening.message:
        print(f"{template.agent.name}: {template.opening.message}")
        print("(此条为系统自动发送)")
        for quick_reply in template.opening.quick_replies:
            print(quick_reply)


async def run_chat(
    account_id: str,
    dialog_id: str | None = None,
    debug_prompt: bool = False,
    debug_turn: bool = True,
    template_id: str | None = None,
) -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    template = get_active_template(template_id)
    store = MemoryStore()
    llm = OpenAICompatibleLLM()
    engine = ConversationEngine(template, store, llm, debug_prompt=debug_prompt or debug_turn)

    dialog_id = dialog_id or _make_dialog_id(account_id)
    profile: dict[str, Any] = {}
    pending_field_key: str | None = None
    stats = _new_token_stats()

    _print_startup(template, llm, account_id, dialog_id, debug_prompt, debug_turn)

    while True:
        raw_user_text = input("\n你: ")
        user_text = _normalize_terminal_text(raw_user_text).strip()
        if not user_text:
            continue
        if _has_invalid_terminal_text(user_text):
            print("\n这句里有终端编码乱码，我没能完整识别。麻烦重新输入一次。")
            continue

        normalized_command = user_text.removeprefix("/").strip()

        if normalized_command in {"exit", "quit", "q"}:
            print("bye")
            return

        if normalized_command == "help":
            _print_help()
            continue

        if normalized_command.startswith("user"):
            parts = normalized_command.split(maxsplit=1)
            account_id = parts[1].strip() if len(parts) > 1 else input("新用户ID: ").strip()
            if not account_id:
                print("用户ID不能为空")
                continue
            dialog_id = _make_dialog_id(account_id)
            profile = store.get_profile(_state_id(account_id, dialog_id))
            pending_field_key = None
            stats = _new_token_stats()
            print(f"已切换用户: {account_id}")
            print(f"新对话ID: {dialog_id}")
            continue

        if normalized_command == "reset":
            dialog_id = _make_dialog_id(account_id)
            profile = {}
            pending_field_key = None
            stats = _new_token_stats()
            print(f"当前用户对话已重置，新对话ID: {dialog_id}")
            if template.opening.enabled and template.opening.message:
                print(f"{template.agent.name}: {template.opening.message}")
                print("(此条为系统自动发送)")
                for quick_reply in template.opening.quick_replies:
                    print(quick_reply)
            continue

        if normalized_command == "profile":
            _print_profile_status(template, profile)
            continue

        if normalized_command == "history":
            _print_history(store.get_history(_state_id(account_id, dialog_id)))
            continue

        if normalized_command == "token":
            _print_token_stats(stats)
            continue

        if normalized_command == "template":
            _print_json("template", template.public_dict())
            continue

        if normalized_command.startswith("set"):
            parsed = _parse_set_command(user_text)
            if parsed is None:
                print("用法: set key=value")
                continue
            key, value = parsed
            profile[key] = value
            store.update_profile(_state_id(account_id, dialog_id), {key: value})
            print(f"set {key}={value}")
            continue

        profile_update: dict[str, Any] = {}
        captured_pending_field: dict[str, Any] = {}
        if pending_field_key:
            is_valid_pending, pending_value = _normalize_pending_field_value(
                template,
                pending_field_key,
                user_text,
            )
            if is_valid_pending:
                profile_update[pending_field_key] = pending_value
                profile[pending_field_key] = pending_value
                captured_pending_field[pending_field_key] = pending_value
            pending_field_key = None

        try:
            response = await engine.chat(
                ChatRequest(
                    question=user_text,
                    accountId=account_id,
                    dialogId=dialog_id,
                    profile=profile_update,
                )
            )
        except Exception as exc:
            title, hint = _format_error_hint(exc)
            print(f"\n[测试日志] {title}")
            print(f"  error: {exc}")
            print(f"  hint: {hint}")
            print(
                "  env: "
                f"provider={llm.settings.provider}, model={llm.settings.model}, "
                f"base_url={llm.settings.base_url or '<empty>'}, "
                f"configured={llm.configured}"
            )
            continue

        stats["turns"] += 1
        stats["response_chars"] += len(response.response)
        if response.debug_system_prompt:
            stats["prompt_chars"] += len(response.debug_system_prompt)
        _update_token_stats(stats, response)

        if debug_turn:
            _print_turn_log(response, llm, template)

        if debug_prompt and captured_pending_field:
            _print_json("本轮回答字段", captured_pending_field)

        if debug_prompt and response.debug_system_prompt:
            print("\n--- debug system prompt ---")
            print(response.debug_system_prompt)
            print("--- end debug system prompt ---")

        if debug_prompt and response.debug_decision:
            _print_json("本轮决策", response.debug_decision)
        if debug_prompt and response.debug_faq_match:
            _print_json("FAQ命中", response.debug_faq_match)
        if debug_prompt and response.debug_knowledge_context:
            _print_json("知识上下文", response.debug_knowledge_context)
        if debug_prompt and response.debug_expression_plan:
            _print_json("表达计划", response.debug_expression_plan)
        if debug_prompt and response.debug_quality_check:
            _print_json("回复质量检查", response.debug_quality_check)

        if response.collected:
            profile.update(response.collected)
        if debug_prompt and response.collected:
            _print_json("本轮收集", response.collected)

        if response.next_field:
            pending_field_key = response.next_field["key"]
        if debug_prompt and response.next_field:
            print(f"\n[下一字段] {response.next_field['key']} ({response.next_field['label']})")

        print(f"\n{template.agent.name}: {response.response}")
        _print_profile_status(template, profile)

        if response.rag_sources:
            _print_json("rag_sources", response.rag_sources)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive open-lead-agent chat")
    parser.add_argument(
        "--account-id", default="terminal-user", help="Account id for this chat session"
    )
    parser.add_argument("--dialog-id", default=None, help="Dialog id for this chat session")
    parser.add_argument(
        "--debug-prompt",
        action="store_true",
        help="Print the system prompt sent to the LLM after each turn",
    )
    parser.add_argument(
        "--debug-turn",
        action="store_true",
        default=True,
        help="Print compact per-turn test logs for understanding, decision, and quality checks",
    )
    parser.add_argument(
        "--quiet-turn",
        action="store_false",
        dest="debug_turn",
        help="Hide compact per-turn test logs",
    )
    parser.add_argument("--template", default=None, help="Template id to use")
    parser.add_argument(
        "--validate-template",
        action="store_true",
        help="Validate template configuration and exit",
    )
    parser.add_argument(
        "--init-template",
        default=None,
        help="Create a starter template with this id and exit",
    )
    parser.add_argument(
        "--guided-template",
        default=None,
        help="Interactively create a template by answering beginner questions",
    )
    parser.add_argument("--template-name", default="", help="Name for --init-template")
    parser.add_argument(
        "--scenario",
        choices=["lead", "support", "education"],
        default="lead",
        help="Starter template scenario for --init-template",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite starter files when using --init-template",
    )
    args = parser.parse_args()
    if args.guided_template:
        raise SystemExit(
            _guided_template_command(
                args.guided_template,
                name=args.template_name,
                force=args.force,
            )
        )
    if args.init_template:
        raise SystemExit(
            _init_template_command(
                args.init_template,
                name=args.template_name,
                scenario=args.scenario,
                force=args.force,
            )
        )
    if args.validate_template:
        raise SystemExit(_validate_template_command(args.template))
    asyncio.run(
        run_chat(
            args.account_id,
            dialog_id=args.dialog_id,
            debug_prompt=args.debug_prompt,
            debug_turn=args.debug_turn,
            template_id=args.template,
        )
    )


if __name__ == "__main__":
    main()
