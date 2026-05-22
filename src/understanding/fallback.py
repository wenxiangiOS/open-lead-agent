"""理解层保守兜底。

当 LLM 不可用或解析失败时，先返回空理解结果，避免误写字段。
"""

from src.understanding.models import PersistencePlan, TurnSemanticFrame, TurnUnderstandingResult


class UnderstandingFallback:
    def empty_result(self) -> TurnUnderstandingResult:
        return TurnUnderstandingResult(
            semantic_frame=TurnSemanticFrame(confidence=0.0),
            persistence_plan=PersistencePlan(),
        )
