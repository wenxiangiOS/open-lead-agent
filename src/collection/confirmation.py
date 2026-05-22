"""待确认字段任务。

当理解层发现字段低置信度或与旧值冲突时，不直接写入 profile，
而是生成一个轻量确认任务，让后续轮次先确认。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PendingConfirmation:
    field_key: str
    proposed_value: Any
    current_value: Any = None
    reason: str = "pending"

    def public_dict(self) -> dict[str, Any]:
        return {
            "field_key": self.field_key,
            "proposed_value": self.proposed_value,
            "current_value": self.current_value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ConfirmationResolution:
    action: str
    values: dict[str, Any]
    clear_task: bool = False

    @property
    def accepted(self) -> bool:
        return self.action == "accept"

    @property
    def rejected(self) -> bool:
        return self.action == "reject"


class PendingConfirmationService:
    accept_patterns = (
        "对",
        "是",
        "对的",
        "没错",
        "就是",
        "用新的",
        "按新的",
        "改成",
        "更新",
        "yes",
        "y",
        "correct",
    )
    reject_patterns = (
        "不是",
        "不对",
        "还是原来",
        "旧的",
        "不用改",
        "不改",
        "算了",
        "no",
        "n",
        "wrong",
    )

    def resolve(
        self,
        user_message: str,
        task: PendingConfirmation | None,
    ) -> ConfirmationResolution:
        if task is None:
            return ConfirmationResolution(action="none", values={})
        normalized = user_message.strip().lower()
        if not normalized:
            return ConfirmationResolution(action="none", values={})
        proposed_text = str(task.proposed_value).strip().lower()
        current_text = str(task.current_value).strip().lower()

        if any(pattern in normalized for pattern in self.reject_patterns):
            return ConfirmationResolution(action="reject", values={}, clear_task=True)
        if current_text and current_text in normalized:
            return ConfirmationResolution(action="reject", values={}, clear_task=True)
        if proposed_text and proposed_text in normalized:
            return ConfirmationResolution(
                action="accept",
                values={task.field_key: task.proposed_value},
                clear_task=True,
            )
        if any(pattern in normalized for pattern in self.accept_patterns):
            return ConfirmationResolution(
                action="accept",
                values={task.field_key: task.proposed_value},
                clear_task=True,
            )
        return ConfirmationResolution(action="none", values={})


def pending_tasks_from_plan(pending_fields: dict[str, Any]) -> list[PendingConfirmation]:
    tasks: list[PendingConfirmation] = []
    for field_key, value in pending_fields.items():
        if isinstance(value, dict) and "new" in value:
            tasks.append(
                PendingConfirmation(
                    field_key=field_key,
                    proposed_value=value.get("new"),
                    current_value=value.get("current"),
                    reason="conflict",
                )
            )
        else:
            tasks.append(
                PendingConfirmation(
                    field_key=field_key,
                    proposed_value=value,
                    reason="low_confidence",
                )
            )
    return tasks
