#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

GOLDEN_FILE="tests/real_ai/scenarios_golden/golden_long_chain_quality.json"
COMMON_ARGS=(
  --seed 42
  --strict-humanlike
  --ack-overuse-threshold 0.25
  --core-streak-max 2
)

RUNNER_PREFIX=()
if [[ "${OSTYPE:-}" == darwin* ]] && command -v caffeinate >/dev/null 2>&1; then
  RUNNER_PREFIX=(caffeinate -dimsu)
fi

archive_and_print_failure_summary() {
  local stage="$1"
  local latest_json="reports/real_ai_realism/latest.json"
  local latest_md="reports/real_ai_realism/latest.md"
  local out_dir="reports/real_ai_realism/gate_failures"
  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$out_dir"

  if [[ -f "$latest_json" ]]; then
    cp "$latest_json" "$out_dir/quality_gate_fail_${ts}_${stage}.json"
  fi
  if [[ -f "$latest_md" ]]; then
    cp "$latest_md" "$out_dir/quality_gate_fail_${ts}_${stage}.md"
  fi

  echo "[quality-gate] FAIL(stage=${stage})，报告已归档到: $out_dir"

  if [[ -f "$latest_json" ]]; then
    python3 - <<'PY'
import json
from pathlib import Path

path = Path("reports/real_ai_realism/latest.json")
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"[quality-gate] 无法解析 latest.json: {exc}")
    raise SystemExit(0)

analysis = payload.get("analysis") or {}
humanlike = analysis.get("humanlike_quality") or {}
extract_acc = analysis.get("extraction_accuracy") or {}
qg = analysis.get("quality_guardrails") or {}

print("[quality-gate] Top 失败项摘要:")
for item in (humanlike.get("top_turn_failures") or [])[:5]:
    print(f"- turn_failure::{item.get('name')} = {item.get('count')}")
for item in (humanlike.get("top_policy_failures") or [])[:5]:
    print(f"- policy_failure::{item.get('name')} = {item.get('count')}")
for item in (extract_acc.get("top_failures") or [])[:5]:
    print(f"- field_failure::{item.get('name')} = {item.get('count')}")

memory_cases = qg.get("memory_reuse_cases", 0)
memory_acc = qg.get("memory_reuse_accuracy", 1.0)
print(f"[quality-gate] memory_reuse_accuracy={memory_acc:.3f} (cases={memory_cases})")
PY
  fi
}

run_or_fail() {
  local stage="$1"
  shift
  if ! "$@"; then
    archive_and_print_failure_summary "$stage"
    exit 1
  fi
}

echo "[quality-gate] 1/2 运行金标长链回放（strict gate）"
run_or_fail "golden" "${RUNNER_PREFIX[@]}" python3 scripts/run_random_user_simulation.py \
  --cover-scenarios \
  --scenario-file "$GOLDEN_FILE" \
  --max-scenarios 1 \
  --max-turns 24 \
  "${COMMON_ARGS[@]}"

echo "[quality-gate] 2/2 运行全量覆盖场景（strict gate）"
run_or_fail "coverage" "${RUNNER_PREFIX[@]}" python3 scripts/run_random_user_simulation.py \
  --cover-scenarios \
  "${COMMON_ARGS[@]}"

echo "[quality-gate] PASS"
