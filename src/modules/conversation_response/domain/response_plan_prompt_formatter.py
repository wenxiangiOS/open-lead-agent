from __future__ import annotations

from src.modules.conversation_response.domain.response_plan_builder import ResponsePlanPromptSpec


class ResponsePlanPromptFormatter:
    """负责把 ResponsePlanPromptSpec 序列化成模型提示片段。"""

    @staticmethod
    def build_generation_instruction(spec: ResponsePlanPromptSpec | None) -> str:
        if spec is None:
            return ""
        return spec.to_generation_instruction()

    @staticmethod
    def prepend_instruction(prompt: str, instruction: str) -> str:
        if not instruction:
            return prompt
        return f"{instruction.strip()}\n\n{prompt}"
