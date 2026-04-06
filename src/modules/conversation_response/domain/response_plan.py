from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResponsePlan:
    """结构化表达计划，供 AI 一次性生成自然回复。"""

    mode: str
    ack_items: list[str] = field(default_factory=list)
    next_move: str = ""
    ask_field: str | None = None
    side_target: str | None = None
    resolved_slots: dict[str, str] = field(default_factory=dict)
    secondary_signals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def to_generation_instruction(self, *, header: str, context_summary: str) -> str:
        ack_summary = "；".join(item for item in self.ack_items if item) or "自然接住用户当前这句"
        constraint_summary = "\n".join(
            f"{idx}. {item}" for idx, item in enumerate(self.constraints, start=1) if item
        )
        if not constraint_summary:
            constraint_summary = "1. 最终只生成一段自然回复。"
        ask_bits: list[str] = []
        if self.ask_field:
            ask_bits.append(f"主任务是自然追问“{self.ask_field}”")
        if self.side_target:
            ask_bits.append(f"如果顺着聊合适，请把“{self.side_target}”自然融合进同一句或紧邻句")
        plan_summary = "；".join([ack_summary, *ask_bits, self.next_move]).strip("；")
        return (
            f"【当前轮生成模式：{header}】\n"
            f"{context_summary}\n"
            f"本轮 response plan：{plan_summary}。\n"
            "要求：\n"
            f"{constraint_summary}\n"
        )
