"""主对话编排器。

ConversationEngine 把单轮理解、知识上下文、策略决策、拟人化表达、
回复构建和状态保存串成一轮完整对话流程。
"""

from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from src.collection import (
    CollectionEngine,
    EffectiveAskResolver,
    PendingConfirmationService,
    pending_tasks_from_plan,
)
from src.collection.state import FieldStateService
from src.contact import ContactEngine
from src.conversation.response_builder import ResponseBuilder
from src.humanization import ExpressionPlanner
from src.knowledge import KnowledgeEngine
from src.llm import OpenAICompatibleLLM
from src.policy import TurnPolicy
from src.storage import MemoryStore
from src.templates import TemplateConfig
from src.understanding import TurnUnderstandingEngine


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1, alias="accountId")
    dialog_id: str | None = Field(default=None, alias="dialogId")
    profile: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    success: bool = True
    response: str
    account_id: str
    dialog_id: str | None = None
    collected: dict[str, Any] = Field(default_factory=dict)
    next_field: dict[str, Any] | None = None
    template_id: str
    rag_sources: list[str] = Field(default_factory=list)
    debug_system_prompt: str | None = None
    debug_decision: dict[str, Any] | None = None
    debug_expression_plan: dict[str, Any] | None = None
    debug_quality_check: dict[str, Any] | None = None
    debug_faq_match: dict[str, Any] | None = None
    debug_knowledge_context: dict[str, Any] | None = None
    debug_understanding: dict[str, Any] | None = None
    debug_contact_gate: dict[str, Any] | None = None
    debug_response: dict[str, Any] | None = None
    debug_timing: dict[str, Any] | None = None
    debug_llm_usage: dict[str, Any] | None = None


class ConversationEngine:
    def __init__(
        self,
        template: TemplateConfig,
        store: MemoryStore,
        llm: OpenAICompatibleLLM,
        *,
        debug_prompt: bool = False,
    ):
        self.template = template
        self.store = store
        self.llm = llm
        self.debug_prompt = debug_prompt
        self.collection = CollectionEngine(template)
        self.effective_ask = EffectiveAskResolver()
        self.pending_confirmation = PendingConfirmationService()
        self.field_state = FieldStateService(template)
        self.contact = ContactEngine(template)
        self.understanding = TurnUnderstandingEngine(template, llm)
        self.knowledge = KnowledgeEngine(template)
        self.expression_planner = ExpressionPlanner(template)
        self.response_builder = ResponseBuilder(template, llm)
        self.policy = TurnPolicy(template)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        started_at = perf_counter()
        timings: dict[str, float] = {}
        self._reset_llm_diagnostics()

        stage_started = perf_counter()
        state_id = self._state_id(request)
        current_profile = self.store.get_profile(state_id)
        existing_pending = self.store.get_pending_confirmation(state_id)
        pending_resolution = self.pending_confirmation.resolve(request.question, existing_pending)
        if pending_resolution.clear_task:
            self.store.clear_current_pending_confirmation(state_id)
        known_profile = {
            **current_profile,
            **request.profile,
            **pending_resolution.values,
        }
        ask_counts = self.store.get_ask_counts(state_id)
        skipped_fields = self.store.get_skipped_fields(state_id)
        previous_target = self.store.get_last_target(state_id)
        previous_assistant_question = self._last_assistant_message(self.store.get_history(state_id))
        self._record_timing(timings, "state_load", stage_started)

        stage_started = perf_counter()
        understanding = await self.understanding.analyze(
            request.question,
            known_profile,
            expected_field=previous_target or "",
            last_question=previous_assistant_question,
        )
        understanding_llm_calls = self._llm_call_count()
        self._record_timing(timings, "understanding", stage_started)

        stage_started = perf_counter()
        extracted = understanding.accepted_fields
        profile = self.store.update_profile(
            state_id,
            {
                **request.profile,
                **pending_resolution.values,
                **extracted,
            },
        )
        collected = {
            **self.collection.extract_configured_fields(request.profile),
            **pending_resolution.values,
            **extracted,
        }
        self._record_timing(timings, "profile_update", stage_started)

        stage_started = perf_counter()
        self.store.append_message(state_id, "user", request.question)
        self._store_pending_confirmation(state_id, understanding.persistence_plan.pending_fields)
        self._record_timing(timings, "history_save_user", stage_started)

        stage_started = perf_counter()
        newly_skipped = self.field_state.infer_skipped_fields(
            user_message=request.question,
            target_key=previous_target,
        )
        if newly_skipped:
            self.store.mark_skipped_fields(state_id, newly_skipped)
            skipped_fields.update(newly_skipped)
        self._record_timing(timings, "field_skip_check", stage_started)

        stage_started = perf_counter()
        knowledge_context = self.knowledge.resolve(request.question, understanding.semantic_frame)
        self._record_timing(timings, "knowledge", stage_started)

        stage_started = perf_counter()
        effective_ask = self.effective_ask.resolve(
            pending_field_key=previous_target,
            collected_this_turn=collected,
            skipped_fields=skipped_fields,
            semantic_frame=understanding.semantic_frame,
            faq_match=knowledge_context.faq_match,
            user_message=request.question,
        )
        for field_key in effective_ask.increment_fields:
            self.store.increment_ask_count(state_id, field_key)
        ask_counts = self.store.get_ask_counts(state_id)
        self._record_timing(timings, "effective_ask", stage_started)

        stage_started = perf_counter()
        field_states = self.field_state.build_states(profile, ask_counts, skipped_fields)
        contact_gate_summary = self.policy.contact_gate.explain(profile, ask_counts, field_states)
        self._record_timing(timings, "field_state_contact_gate", stage_started)

        stage_started = perf_counter()
        decision = self.policy.decide(
            profile=profile,
            ask_counts=ask_counts,
            collected_this_turn=collected,
            field_states=field_states,
            faq_match=knowledge_context.faq_match,
            semantic_frame=understanding.semantic_frame,
            pending_confirmation=self.store.get_pending_confirmation(state_id),
            user_message=request.question,
            recent_history=self.store.get_history(state_id)[:-1],
        )
        self._record_timing(timings, "decision", stage_started)

        stage_started = perf_counter()
        expression_plan = self.expression_planner.build(
            decision=decision,
            user_message=request.question,
            collected_this_turn=collected,
            recent_history=self.store.get_history(state_id),
        )
        self._record_timing(timings, "expression_plan", stage_started)

        stage_started = perf_counter()
        next_field = decision.target
        built_response = await self.response_builder.build(
            user_message=request.question,
            decision=decision,
            expression_plan=expression_plan,
            knowledge_context=knowledge_context,
            profile=profile,
            collected=collected,
        )
        self._record_timing(timings, "response_build", stage_started)

        stage_started = perf_counter()
        if next_field:
            self.store.set_last_target(state_id, next_field.key)
        else:
            self.store.set_last_target(state_id, None)
        self.store.append_message(state_id, "assistant", built_response.response)
        self._record_timing(timings, "state_save_assistant", stage_started)

        total_ms = round((perf_counter() - started_at) * 1000, 2)
        timings["total"] = total_ms
        llm_usage = self._llm_diagnostics(understanding_llm_calls=understanding_llm_calls)
        return ChatResponse(
            response=built_response.response,
            account_id=request.account_id,
            dialog_id=request.dialog_id,
            collected=collected,
            next_field=next_field.model_dump() if next_field else None,
            template_id=self.template.template.id,
            rag_sources=knowledge_context.rag_sources,
            debug_system_prompt=built_response.system_prompt if self.debug_prompt else None,
            debug_decision=decision.public_dict() if self.debug_prompt else None,
            debug_expression_plan=expression_plan.public_dict() if self.debug_prompt else None,
            debug_quality_check=built_response.quality_check.public_dict()
            if self.debug_prompt
            else None,
            debug_faq_match=knowledge_context.faq_match.public_dict()
            if self.debug_prompt and knowledge_context.faq_match is not None
            else None,
            debug_knowledge_context=knowledge_context.public_dict() if self.debug_prompt else None,
            debug_understanding=understanding.public_dict() if self.debug_prompt else None,
            debug_contact_gate=contact_gate_summary if self.debug_prompt else None,
            debug_response={
                "route": built_response.route,
                "error": built_response.error,
                "chars": len(built_response.response),
            }
            if self.debug_prompt
            else None,
            debug_timing={"total_ms": total_ms, "stages": timings} if self.debug_prompt else None,
            debug_llm_usage=llm_usage if self.debug_prompt else None,
        )

    def _state_id(self, request: ChatRequest) -> str:
        if not request.dialog_id:
            return request.account_id
        return f"{request.account_id}:{request.dialog_id}"

    def _last_assistant_message(self, history: list[dict[str, str]]) -> str:
        for item in reversed(history):
            if item.get("role") == "assistant":
                return item.get("content", "")
        return ""

    def _store_pending_confirmation(
        self,
        state_id: str,
        pending_fields: dict[str, Any],
    ) -> None:
        tasks = pending_tasks_from_plan(pending_fields)
        if tasks:
            self.store.add_pending_confirmations(state_id, tasks)

    def _record_timing(
        self,
        timings: dict[str, float],
        name: str,
        started_at: float,
    ) -> None:
        timings[name] = round((perf_counter() - started_at) * 1000, 2)

    def _reset_llm_diagnostics(self) -> None:
        reset = getattr(self.llm, "reset_diagnostics", None)
        if callable(reset):
            reset()

    def _llm_call_count(self) -> int:
        diagnostics = self._llm_diagnostics()
        if diagnostics is None:
            return 0
        return int(diagnostics.get("calls") or 0)

    def _llm_diagnostics(
        self,
        *,
        understanding_llm_calls: int = 0,
    ) -> dict[str, Any] | None:
        diagnostics = getattr(self.llm, "diagnostics", None)
        if not callable(diagnostics):
            return None
        result = diagnostics()
        if not isinstance(result, dict):
            return None
        self._label_llm_calls(result, understanding_llm_calls)
        return result

    def _label_llm_calls(
        self,
        diagnostics: dict[str, Any],
        understanding_llm_calls: int,
    ) -> None:
        details = diagnostics.get("details")
        if not isinstance(details, list):
            return
        for index, call in enumerate(details):
            if not isinstance(call, dict):
                continue
            call["purpose"] = "understanding" if index < understanding_llm_calls else "response"
