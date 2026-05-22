"""对话回复构建与一致性修复。

这个模块负责 system prompt、LLM 调用、默认回复兜底和回复质量复检，
让 ConversationEngine 只做主流程编排。
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.humanization import ExpressionPlan, ResponseQualityChecker
from src.knowledge import KnowledgeContext
from src.llm import OpenAICompatibleLLM
from src.policy import TurnDecision
from src.templates import TemplateConfig
from src.templates.config import DialogueExampleConfig, DialoguePolicySectionConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuiltResponse:
    response: str
    system_prompt: str
    quality_check: Any
    route: str = "model"
    error: str = ""


class ResponseBuilder:
    def __init__(self, template: TemplateConfig, llm: OpenAICompatibleLLM):
        self.template = template
        self.llm = llm
        self.quality_checker = ResponseQualityChecker(template)

    async def build(
        self,
        *,
        user_message: str,
        decision: TurnDecision,
        expression_plan: ExpressionPlan,
        knowledge_context: KnowledgeContext,
        profile: dict[str, Any],
        collected: dict[str, Any],
    ) -> BuiltResponse:
        system_prompt = self._build_system_prompt(
            decision,
            expression_plan,
            knowledge_context,
            profile,
            collected,
        )
        response, route, error = await self._initial_response(
            user_message,
            decision,
            knowledge_context,
            system_prompt,
        )
        response = self._enforce_response_limit(response)
        quality_check = self.quality_checker.check(
            response=response,
            decision=decision,
            expression_plan=expression_plan,
        )
        if self._should_repair_response(quality_check):
            response = self._fallback_target_response(decision)
            route = f"{route}+repair"
            response = self._enforce_response_limit(response)
            quality_check = self.quality_checker.check(
                response=response,
                decision=decision,
                expression_plan=expression_plan,
            )
        return BuiltResponse(
            response=response,
            system_prompt=system_prompt,
            quality_check=quality_check,
            route=route,
            error=error,
        )

    async def _initial_response(
        self,
        user_message: str,
        decision: TurnDecision,
        knowledge_context: KnowledgeContext,
        system_prompt: str,
    ) -> tuple[str, str, str]:
        if decision.action in {"end", "close"} and decision.response:
            return decision.response, "decision_response", ""
        if (
            decision.action in {"answer_only", "answer_then_ask", "confirm_field"}
            and decision.response
        ):
            return self._decision_response(decision), "decision_response", ""

        try:
            response = await self.llm.generate(system_prompt, user_message)
        except Exception as exc:
            logger.debug("response_llm_failed: %s", exc)
            return self._fallback_target_response(decision), "fallback_exception", str(exc)
        if decision.target and not response.strip():
            fallback = decision.target.ask or f"请补充一下{decision.target.label}可以吗？"
            return fallback, "fallback_empty_response", ""
        if decision.target and not self.llm.configured and knowledge_context.faq_match is None:
            fallback = decision.target.ask or f"请补充一下{decision.target.label}可以吗？"
            return fallback, "fallback_unconfigured_llm", ""
        return response, "model", ""

    def _build_system_prompt(
        self,
        decision: TurnDecision,
        expression_plan: ExpressionPlan,
        knowledge_context: KnowledgeContext,
        profile: dict[str, Any],
        collected: dict[str, Any],
    ) -> str:
        lines = [
            f"You are {self.template.agent.name}.",
            f"Role: {self.template.agent.role}.",
            f"Reply language: {self.template.agent.language}.",
            f"Tone: {self.template.agent.tone}",
            f"Business: {self.template.template.name}",
            "Always respond in the configured reply language unless the user explicitly "
            "requests another language.",
            "Answer the user naturally. If a next field is provided, ask for it conversationally.",
        ]
        if self.template.agent.persona:
            lines.append(f"Persona:\n{self.template.agent.persona}")
        if self.template.agent.goals:
            lines.append("Goals:")
            lines.extend(f"- {goal}" for goal in self.template.agent.goals)
        if self.template.agent.behavior_rules:
            lines.append("Behavior rules:")
            lines.extend(f"- {rule}" for rule in self.template.agent.behavior_rules)
        if self.template.agent.boundaries:
            lines.append("Boundaries:")
            lines.extend(f"- {boundary}" for boundary in self.template.agent.boundaries)
        lines.extend(self._format_dialogue_policy())
        lines.append("Known collected profile:")
        lines.append(self._format_json(profile))
        if collected:
            lines.append("Current turn collected values:")
            lines.append(self._format_json(collected))
            lines.append(
                "The current user message has already been accepted as the values above. "
                "Acknowledge it naturally and continue to the next field; do not say you "
                "did not understand solely because the raw value is short, numeric, or an "
                "account handle."
            )
        lines.append("Turn decision:")
        lines.append(self._format_json(decision.public_dict()))
        if decision.target is not None:
            lines.append(
                f"Next field to collect: {decision.target.key} ({decision.target.label})."
            )
        if decision.side_target is not None:
            lines.append(
                "Optional related side field: "
                f"{decision.side_target.key} ({decision.side_target.label})."
            )
            lines.append(
                "The side field is not the main task. Mention it only if it sounds like a "
                "natural follow-up; do not create a form-like list of questions."
            )
        if decision.expression_hint:
            lines.append(f"Expression hint: {decision.expression_hint}")
        lines.append("Humanized expression plan:")
        lines.append(self._format_json(expression_plan.public_dict()))
        lines.append(
            "Use this expression plan to make the reply feel natural, but never reveal "
            "the plan, field routing, or internal policy to the user."
        )
        if knowledge_context.rag_results:
            lines.append("Knowledge base context:")
            for result in knowledge_context.rag_results:
                lines.append(f"- Source: {result.source}\n{result.content}")
        return "\n".join(lines)

    def _format_dialogue_policy(self) -> list[str]:
        policy = self.template.dialogue_policy
        lines: list[str] = []
        if policy.turn_goal:
            lines.append(f"Turn goal:\n{policy.turn_goal}")
        for section in policy.sections:
            self._append_policy_section(lines, section)
        if policy.examples:
            lines.append("Dialogue examples:")
            lines.extend(self._format_dialogue_example(example) for example in policy.examples)
        return lines

    def _append_policy_section(
        self, lines: list[str], section: DialoguePolicySectionConfig
    ) -> None:
        if not section.rules:
            return
        lines.append(f"{section.title}:")
        lines.extend(f"- {rule}" for rule in section.rules)

    def _format_dialogue_example(self, example: DialogueExampleConfig) -> str:
        parts = [f"- User: {example.user}", f"  Better: {example.better}"]
        if example.worse:
            parts.append(f"  Worse: {example.worse}")
        return "\n".join(parts)

    def _format_json(self, value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def _decision_response(self, decision: TurnDecision) -> str:
        if decision.action != "answer_then_ask" or decision.target is None:
            return decision.response
        ask = decision.target.ask or f"请补充一下{decision.target.label}可以吗？"
        return f"{decision.response}\n\n{ask}"

    def _should_repair_response(self, quality_check: Any) -> bool:
        if not self.template.humanization.enforce_target_consistency:
            return False
        return any(issue.startswith("missing_target:") for issue in quality_check.issues)

    def _fallback_target_response(self, decision: TurnDecision) -> str:
        if decision.action == "answer_then_ask" and decision.response and decision.target:
            ask = decision.target.ask or f"请补充一下{decision.target.label}可以吗？"
            return f"{decision.response}\n\n{ask}"
        if decision.response and decision.action == "confirm_field":
            return decision.response
        if decision.target is None:
            return decision.response
        return decision.target.ask or f"请补充一下{decision.target.label}可以吗？"

    def _enforce_response_limit(self, response: str) -> str:
        max_chars = self.template.conversation.response_max_chars
        if max_chars <= 0 or len(response) <= max_chars:
            return response
        if max_chars <= 3:
            return response[:max_chars]
        return response[: max_chars - 3].rstrip() + "..."
