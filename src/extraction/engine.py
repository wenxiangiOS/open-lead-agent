"""旧版资料提取兼容门面。

新的正式语义入口在 src.understanding。这个类保留 extract() 旧用法，
方便已有代码和开源用户平滑迁移。
"""

from typing import Any

from src.templates import TemplateConfig
from src.understanding import TurnUnderstandingEngine


class ExtractionEngine:
    def __init__(self, template: TemplateConfig, llm: Any):
        self.understanding = TurnUnderstandingEngine(template, llm)

    async def extract(
        self,
        user_message: str,
        profile: dict[str, Any],
        *,
        expected_field: str = "",
        last_question: str = "",
    ) -> dict[str, Any]:
        result = await self.understanding.analyze(
            user_message,
            profile,
            expected_field=expected_field,
            last_question=last_question,
        )
        return result.accepted_fields
