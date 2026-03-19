#!/usr/bin/env python3
"""
EXTRACTION 回归结果校验脚本。

用法示例:
python3 scripts/check_extraction_regression.py \
  --cases tests/manual/extraction_regression_cases.json \
  --results tests/manual/extraction_results.sample.json

results 文件支持两种形式:
1) 列表:
[
  {"id": "E001", "response": "xxx<extract>\\n年龄:31岁\\n</extract>"},
  {"id": "E002", "extracted": {"年龄": "28岁"}}
]

2) 对象:
{"results": [ ...同上... ]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXTRACT_PATTERN = re.compile(r"<extract>\s*\n?(.*?)\n?</extract>", re.DOTALL)
FIELD_LINE_PATTERN = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.*?)\s*$")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip().strip('"').strip("'")
    if not text:
        return None
    if text.lower() == "null":
        return None
    return text


def parse_extract_block(response: str) -> Dict[str, Any]:
    match = EXTRACT_PATTERN.search(response or "")
    if not match:
        return {}

    content = match.group(1)
    result: Dict[str, Any] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = FIELD_LINE_PATTERN.match(line)
        if not m:
            continue
        field, value = m.group(1).strip(), m.group(2).strip()
        result[field] = normalize_value(value)
    return result


def resolve_expected(value: Any) -> Any:
    text = normalize_value(value)
    if text is None:
        return None

    # 支持占位符: {current_year_minus_1998}岁
    m = re.fullmatch(r"\{current_year_minus_(\d{4})\}岁", text)
    if m:
        year = int(m.group(1))
        return f"{datetime.now().year - year}岁"
    return text


def load_results(path: Path) -> Dict[str, Dict[str, Any]]:
    raw = load_json(path)
    items = raw.get("results", []) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("results 文件格式错误，应为 list 或 {\"results\": list}")

    by_id: Dict[str, Dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        case_id = item.get("id")
        if not case_id:
            continue

        if "extracted" in item and isinstance(item["extracted"], dict):
            extracted = {k: normalize_value(v) for k, v in item["extracted"].items()}
        else:
            response = str(item.get("response", ""))
            extracted = parse_extract_block(response)

        by_id[case_id] = extracted
    return by_id


def evaluate(
    cases: List[Dict[str, Any]], results_by_id: Dict[str, Dict[str, Any]]
) -> Tuple[int, int, List[str]]:
    total_checks = 0
    failed_checks = 0
    failures: List[str] = []

    for case in cases:
        case_id = case.get("id", "<unknown>")
        case_name = case.get("name", "")
        expected = case.get("expected", {})
        actual = results_by_id.get(case_id, {})

        if not isinstance(expected, dict):
            continue

        for field, expected_value in expected.items():
            total_checks += 1
            expected_norm = resolve_expected(expected_value)
            actual_norm = normalize_value(actual.get(field))

            if expected_norm != actual_norm:
                failed_checks += 1
                failures.append(
                    f"[{case_id}] {case_name} | 字段={field} | 期望={expected_norm} | 实际={actual_norm}"
                )

    return total_checks, failed_checks, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 EXTRACTION 回归结果")
    parser.add_argument(
        "--cases",
        default="tests/manual/extraction_regression_cases.json",
        help="回归用例 JSON 路径",
    )
    parser.add_argument(
        "--results",
        required=True,
        help="模型输出结果 JSON 路径（含 id + response 或 extracted）",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=20,
        help="最多展示失败明细条数",
    )
    args = parser.parse_args()

    cases_data = load_json(Path(args.cases))
    cases = cases_data.get("cases", []) if isinstance(cases_data, dict) else []
    if not isinstance(cases, list) or not cases:
        print("未读取到有效 cases。")
        return 2

    results_by_id = load_results(Path(args.results))
    total_checks, failed_checks, failures = evaluate(cases, results_by_id)

    passed_checks = total_checks - failed_checks
    pass_rate = (passed_checks / total_checks) if total_checks else 0.0

    print("=== EXTRACTION 回归结果 ===")
    print(f"总检查数: {total_checks}")
    print(f"通过数: {passed_checks}")
    print(f"失败数: {failed_checks}")
    print(f"通过率: {pass_rate:.1%}")

    if failures:
        print("\n--- 失败明细 ---")
        for line in failures[: max(0, args.show_failures)]:
            print(line)

    return 1 if failed_checks > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
