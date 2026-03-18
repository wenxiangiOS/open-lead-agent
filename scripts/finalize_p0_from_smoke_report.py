#!/usr/bin/env python3
"""Finalize P0 status from production smoke report.

Usage:
  python3 scripts/finalize_p0_from_smoke_report.py \
    --report reports/mq/p0_production_smoke_xxx.md \
    --status docs/message_queue_status.yaml
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


def _report_is_pass(report_text: str) -> bool:
    for line in report_text.splitlines():
        if line.strip().lower().startswith("- status:"):
            return "pass" in line.strip().lower()
    return False


def _update_status_yaml(status_text: str) -> str:
    lines = status_text.splitlines()
    out = []
    in_p0 = False
    for line in lines:
        stripped = line.strip()
        if stripped == "p0:":
            in_p0 = True
            out.append(line)
            continue
        if in_p0 and stripped.endswith(":") and not stripped.startswith("state") and stripped != "checklist:" and stripped != "evidence:":
            # entering next section under status
            in_p0 = False

        if in_p0 and stripped.startswith("state:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}state: DONE")
            continue
        if in_p0 and stripped.startswith("summary:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{indent}summary: "P0 已完成真实生产端点联调并通过"')
            continue
        out.append(line)

    # update last_updated
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    out2 = []
    replaced = False
    for line in out:
        if line.startswith("last_updated:") and not replaced:
            out2.append(f'last_updated: "{now}"')
            replaced = True
        else:
            out2.append(line)
    return "\n".join(out2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize p0 status from smoke report")
    parser.add_argument("--report", required=True)
    parser.add_argument("--status", default="docs/message_queue_status.yaml")
    args = parser.parse_args()

    report_path = Path(args.report)
    status_path = Path(args.status)

    if not report_path.exists():
        print(f"[FAIL] report not found: {report_path}")
        return 1
    if not status_path.exists():
        print(f"[FAIL] status file not found: {status_path}")
        return 1

    report_text = report_path.read_text(encoding="utf-8")
    if not _report_is_pass(report_text):
        print("[SKIP] report status is not PASS, keep p0 unchanged")
        return 2

    status_text = status_path.read_text(encoding="utf-8")
    updated = _update_status_yaml(status_text)
    status_path.write_text(updated, encoding="utf-8")
    print(f"[PASS] updated {status_path} -> p0 DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
