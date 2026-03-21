#!/usr/bin/env python3
"""Generate a single markdown index for report directories.

Usage:
  python3 scripts/generate_report_index.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_ROOT = PROJECT_ROOT / "reports"
OUTPUT_FILE = REPORTS_ROOT / "INDEX.md"


@dataclass(frozen=True)
class ReportBucket:
    name: str
    relative_dir: str
    hint_command: str

    @property
    def path(self) -> Path:
        return REPORTS_ROOT / self.relative_dir


BUCKETS = (
    ReportBucket(
        name="真实用户仿真回归",
        relative_dir="real_ai_realism",
        hint_command="python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose",
    ),
    ReportBucket(
        name="Chat 回归",
        relative_dir="real_ai",
        hint_command="python3 scripts/run_real_ai_regression.py",
    ),
    ReportBucket(
        name="MQ 负载回归",
        relative_dir="mq_load",
        hint_command="python3 scripts/run_mq_load_test.py --base-url http://127.0.0.1:8000 --accounts 20 --messages-per-account 10 --concurrency 20 --include-dashboard --gate",
    ),
    ReportBucket(
        name="MQ 生产 smoke",
        relative_dir="mq",
        hint_command="python3 scripts/run_mq_p0_production_smoke.py --timeout-seconds 30 --report-file reports/mq/p0_production_smoke_$(date +%Y%m%d_%H%M%S).md",
    ),
)


def _iter_report_files(folder: Path) -> Iterable[Path]:
    if not folder.exists():
        return ()
    return sorted(
        (
            p
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in {".md", ".json"}
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _build_bucket_section(bucket: ReportBucket) -> list[str]:
    lines = [f"## {bucket.name}", f"- 目录：`reports/{bucket.relative_dir}`"]
    files = list(_iter_report_files(bucket.path))
    if not files:
        lines.append("- 最新报告：无")
        lines.append(f"- 生成命令：`{bucket.hint_command}`")
        lines.append("")
        return lines

    latest = files[0]
    latest_rel = latest.relative_to(PROJECT_ROOT).as_posix()
    lines.append(f"- 最新报告：`{latest_rel}`")
    lines.append(f"- 更新时间：`{_fmt_time(latest.stat().st_mtime)}`")
    lines.append(f"- 报告总数：`{len(files)}`")
    lines.append(f"- 生成命令：`{bucket.hint_command}`")
    lines.append("")
    lines.append("最近 5 份：")
    for report in files[:5]:
        rel = report.relative_to(PROJECT_ROOT).as_posix()
        updated = _fmt_time(report.stat().st_mtime)
        lines.append(f"- `{rel}` ({updated})")
    lines.append("")
    return lines


def main() -> int:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 报告索引（自动生成）",
        "",
        f"更新时间：`{now}`",
        "",
        "使用说明：",
        "- 每次跑完回归后执行：`python3 scripts/generate_report_index.py`",
        "- 统一从本文件查看各类报告最新路径，避免忘记目录。",
        "",
    ]
    for bucket in BUCKETS:
        lines.extend(_build_bucket_section(bucket))

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[ok] report index generated: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
