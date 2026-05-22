"""单轮理解的数据结构。

这个文件只定义结构，不放业务流程。下游模块应该消费这些结构化结果，
不要再各自重新解释用户原话。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldObservation:
    """用户本轮可能提供的一个字段事实。"""

    field: str
    value: Any
    normalized_value: Any = None
    scope: str = "self"
    owner: str = "user"
    evidence_text: str = ""
    confidence: float = 1.0
    write_mode: str = "direct_write"
    source: str = "llm"
    reason: str = ""

    @property
    def committed_value(self) -> Any:
        if self.normalized_value not in (None, ""):
            return self.normalized_value
        return self.value

    def public_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "scope": self.scope,
            "owner": self.owner,
            "evidence_text": self.evidence_text,
            "confidence": self.confidence,
            "write_mode": self.write_mode,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TurnSemanticFrame:
    """单轮语义理解结果。"""

    intents: list[str] = field(default_factory=list)
    observations: list[FieldObservation] = field(default_factory=list)
    turn_mode: str = "default"
    no_reask_fields: list[str] = field(default_factory=list)
    faq_intent: str | None = None
    compliance_signals: list[str] = field(default_factory=list)
    reply_act: str = "continue"
    confidence: float = 1.0
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def has_intent(self, *names: str) -> bool:
        normalized = {item.strip().lower() for item in self.intents}
        return any(name.strip().lower() in normalized for name in names)

    @property
    def wants_to_stop(self) -> bool:
        stop_reply_acts = {
            "stop",
            "end",
            "close",
            "conversation_end",
            "refuse_collection",
            "refusal",
        }
        if self.reply_act.strip().lower() in stop_reply_acts:
            return True
        return self.has_intent(
            "stop",
            "end",
            "conversation_end",
            "refusal",
            "refuse_collection",
            "do_not_continue",
        )

    @property
    def has_contact_intent(self) -> bool:
        return self.has_intent("contact", "contact_intent", "leave_contact")

    def public_dict(self) -> dict[str, Any]:
        return {
            "intents": self.intents,
            "observations": [item.public_dict() for item in self.observations],
            "turn_mode": self.turn_mode,
            "no_reask_fields": self.no_reask_fields,
            "faq_intent": self.faq_intent,
            "compliance_signals": self.compliance_signals,
            "reply_act": self.reply_act,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class PersistencePlan:
    """字段写入计划。

    accepted 会写入 profile；其它状态只用于调试、确认或后续增强。
    """

    accepted_fields: dict[str, Any] = field(default_factory=dict)
    provisional_fields: dict[str, Any] = field(default_factory=dict)
    pending_fields: dict[str, Any] = field(default_factory=dict)
    rejected_fields: dict[str, Any] = field(default_factory=dict)
    observation_log: list[FieldObservation] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {
            "accepted_fields": self.accepted_fields,
            "provisional_fields": self.provisional_fields,
            "pending_fields": self.pending_fields,
            "rejected_fields": self.rejected_fields,
            "observation_log": [item.public_dict() for item in self.observation_log],
        }


@dataclass(frozen=True)
class TurnUnderstandingResult:
    """单轮理解总结果。"""

    semantic_frame: TurnSemanticFrame
    persistence_plan: PersistencePlan

    @property
    def accepted_fields(self) -> dict[str, Any]:
        return self.persistence_plan.accepted_fields

    def public_dict(self) -> dict[str, Any]:
        return {
            "semantic_frame": self.semantic_frame.public_dict(),
            "persistence_plan": self.persistence_plan.public_dict(),
        }
