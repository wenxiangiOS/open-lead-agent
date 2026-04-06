from __future__ import annotations

from src.modules.conversation_response.domain.opening_intent_prompt_formatter import OpeningIntentPromptFormatter
from src.modules.conversation_response.domain.profile_bridge_prompt_formatter import ProfileBridgePromptFormatter
from src.modules.conversation_response.domain.response_plan_prompt_formatter import ResponsePlanPromptFormatter


class PromptAssemblyService:
    """负责按固定优先级拼装模型生成提示，减少主流程直接操作 prompt 文本。"""

    def __init__(
        self,
        *,
        profile_bridge_prompt_formatter: ProfileBridgePromptFormatter,
        response_plan_prompt_formatter: ResponsePlanPromptFormatter,
        opening_intent_prompt_formatter: OpeningIntentPromptFormatter,
    ) -> None:
        self.profile_bridge_prompt_formatter = profile_bridge_prompt_formatter
        self.response_plan_prompt_formatter = response_plan_prompt_formatter
        self.opening_intent_prompt_formatter = opening_intent_prompt_formatter

    def assemble_for_generation(
        self,
        base_prompt: str,
        *,
        profile_bridge_instruction: str = "",
        response_plan_instruction: str = "",
        opening_intent_detection_enabled: bool = False,
    ) -> str:
        prompt = self.profile_bridge_prompt_formatter.prepend_instruction(
            base_prompt,
            profile_bridge_instruction,
        )
        prompt = self.response_plan_prompt_formatter.prepend_instruction(
            prompt,
            response_plan_instruction,
        )
        if opening_intent_detection_enabled:
            prompt = self.opening_intent_prompt_formatter.prepend_instruction(
                prompt,
                self.opening_intent_prompt_formatter.build_detection_instruction(),
            )
        return prompt
