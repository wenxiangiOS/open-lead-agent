"""单轮理解总入口。

这层负责串起提示词、LLM、解析、字段接受计划。它不负责决定下一问，
也不直接生成用户可见回复。
"""

import logging
from typing import Any

from src.templates import TemplateConfig
from src.understanding.acceptance import FieldAcceptanceService
from src.understanding.context import UnderstandingContext, configured_items
from src.understanding.dense_intro import DenseIntroDetector
from src.understanding.fallback import UnderstandingFallback
from src.understanding.governance import FieldGovernanceService
from src.understanding.models import TurnUnderstandingResult
from src.understanding.parser import UnderstandingParser
from src.understanding.prompt_builder import UnderstandingPromptBuilder

logger = logging.getLogger(__name__)


class TurnUnderstandingEngine:
    def __init__(self, template: TemplateConfig, llm: Any):
        self.template = template
        self.llm = llm
        self.prompt_builder = UnderstandingPromptBuilder(template)
        self.parser = UnderstandingParser()
        self.dense_intro = DenseIntroDetector()
        self.governance = FieldGovernanceService(template)
        self.acceptance = FieldAcceptanceService(template)
        self.fallback = UnderstandingFallback()

    async def analyze(
        self,
        user_message: str,
        profile: dict[str, Any],
        *,
        expected_field: str = "",
        last_question: str = "",
    ) -> TurnUnderstandingResult:
        if (
            not self.template.extraction.enabled
            or not getattr(self.llm, "configured", False)
            or not configured_items(self.template)
        ):
            return self.fallback.empty_result()

        context = UnderstandingContext(
            known_profile=profile,
            expected_field=expected_field,
            last_question=last_question,
        )
        prompt = self.prompt_builder.build(user_message, context)
        try:
            raw_response = await self.llm.generate(prompt, user_message)
        except Exception as exc:
            logger.debug("understanding_llm_failed: %s", exc)
            return self.fallback.empty_result()
        semantic_frame = self.parser.parse(raw_response)
        if not semantic_frame.raw_payload:
            return self.fallback.empty_result()
        semantic_frame = self.dense_intro.detect(semantic_frame, user_message=user_message)
        governance = self.governance.govern(
            semantic_frame,
            expected_field=expected_field,
            user_message=user_message,
        )
        plan = self.acceptance.build_plan(governance.frame, profile)
        plan = self.governance.merge_blocked_into_plan(plan, governance.blocked_observations)
        return TurnUnderstandingResult(semantic_frame=governance.frame, persistence_plan=plan)
