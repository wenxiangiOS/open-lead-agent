from __future__ import annotations

import logging
import os
import re

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput, TurnUnderstandingResult
from src.modules.conversation_understanding.domain.ai_semantic_extraction_service import AISemanticExtractionService
from src.modules.conversation_understanding.domain.compat.persistence_plan_to_followup_inputs_adapter import (
    PersistencePlanToFollowupInputsAdapter,
)
from src.modules.conversation_understanding.domain.compat.persistence_plan_to_resolved_slots_adapter import (
    PersistencePlanToResolvedSlotsAdapter,
)
from src.modules.conversation_understanding.domain.compat.turn_semantic_frame_to_turn_understanding_result_adapter import (
    TurnSemanticFrameToTurnUnderstandingResultAdapter,
)
from src.modules.conversation_understanding.domain.contextual_slot_governance_layer import (
    ContextualSlotGovernanceLayer,
)
from src.modules.conversation_understanding.domain.field_acceptance_service import FieldAcceptanceService
from src.modules.conversation_understanding.domain.field_derivation_layer import FieldDerivationLayer
from src.modules.conversation_understanding.domain.field_permission_layer import FieldPermissionLayer
from src.modules.conversation_understanding.domain.field_update_policy_service import FieldUpdatePolicyService
from src.modules.conversation_understanding.domain.followup_planning_layer import FollowupPlanningLayer
from src.modules.conversation_understanding.domain.lexical_signal_layer import LexicalSignalLayer
from src.modules.conversation_understanding.domain.models import UnifiedTurnUnderstandingResult
from src.modules.conversation_understanding.domain.persistence_plan_service import PersistencePlanService
from src.modules.conversation_understanding.domain.reply_act_classification_layer import ReplyActClassificationLayer
from src.modules.conversation_understanding.domain.semantic_normalization_service import SemanticNormalizationService
from src.modules.conversation_understanding.domain.semantic_understanding_layer import SemanticUnderstandingLayer
from src.modules.conversation_understanding.domain.turn_priority_policy import TurnPriorityPolicy
from src.modules.conversation_understanding.domain.turn_input_assembly_service import TurnInputAssemblyService

logger = logging.getLogger(__name__)


class UnifiedTurnUnderstandingService:
    """Single entrypoint for turn understanding.

    The primary path now centers on ``TurnSemanticFrame`` and
    ``TurnPersistencePlan``. Legacy turn-understanding outputs are retained
    only as fallback input and compatibility projections during the migration.
    """

    def __init__(self, semantic_service, ai_service) -> None:
        self.turn_input_assembly_service = TurnInputAssemblyService()
        self.lexical_layer = LexicalSignalLayer(semantic_service)
        self.semantic_layer = SemanticUnderstandingLayer(semantic_service)
        self.slot_governance_layer = ContextualSlotGovernanceLayer(semantic_service)
        self.reply_act_layer = ReplyActClassificationLayer()
        self.field_permission_layer = FieldPermissionLayer()
        self.field_derivation_layer = FieldDerivationLayer()
        self.followup_planning_layer = FollowupPlanningLayer()
        self.ai_semantic_extraction_service = AISemanticExtractionService(semantic_service, ai_service)
        self.semantic_normalization_service = SemanticNormalizationService()
        self.field_acceptance_service = FieldAcceptanceService()
        self.field_update_policy_service = FieldUpdatePolicyService()
        self.persistence_plan_service = PersistencePlanService()
        self.turn_priority_policy = TurnPriorityPolicy()
        self.turn_result_adapter = TurnSemanticFrameToTurnUnderstandingResultAdapter()
        self.resolved_slots_adapter = PersistencePlanToResolvedSlotsAdapter()
        self.followup_inputs_adapter = PersistencePlanToFollowupInputsAdapter()

    async def analyze(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        force_ai: bool = False,
        ai_timeout_seconds: float | None = None,
    ) -> TurnUnderstandingResult:
        snapshot = self.turn_input_assembly_service.build_snapshot(turn_input)
        lexical_signals = self.lexical_layer.analyze(turn_input)
        semantic_result = self.semantic_layer.analyze(turn_input)
        decision_source = "semantic"
        if lexical_signals.can_short_circuit:
            decision_source = "lexical+semantic"
        governed_result = self.slot_governance_layer.govern(
            turn_input=turn_input,
            result=semantic_result,
        )
        question_state = self._get_question_state(turn_input)
        reply_act_result = self.reply_act_layer.classify(
            turn_input=turn_input,
            semantic_result=governed_result,
            question_state=question_state,
        )
        field_permission_result = self.field_permission_layer.decide(
            turn_input=turn_input,
            semantic_result=governed_result,
            reply_act_result=reply_act_result,
            question_state=question_state,
        )
        if force_ai:
            use_ai_semantic = True
            ai_trigger_reason = "forced"
        else:
            use_ai_semantic, ai_trigger_reason = self._should_enable_sync_ai_semantic(
                turn_input=turn_input,
                question_state=question_state,
                semantic_result=governed_result,
                reply_act_result=reply_act_result,
            )
        semantic_frame = await self.ai_semantic_extraction_service.extract(
            snapshot=snapshot,
            fallback_result=governed_result,
            enable_ai=use_ai_semantic,
            ai_timeout_seconds=ai_timeout_seconds,
        )
        pre_filter_observed = len(list(getattr(semantic_frame, "field_observations", []) or []))
        pre_filter_fields = sorted(
            {
                str(getattr(item, "field", "") or "").strip()
                for item in list(getattr(semantic_frame, "field_observations", []) or [])
                if str(getattr(item, "field", "") or "").strip()
            }
        )
        ai_semantic_success = getattr(semantic_frame, "source", "") == "ai_structured_extraction"
        if ai_semantic_success:
            decision_source = "ai_semantic_extraction"
        elif ai_trigger_reason:
            decision_source = f"semantic[{ai_trigger_reason}:fallback]"
        semantic_frame = self.semantic_normalization_service.normalize(semantic_frame)
        semantic_frame = self._filter_semantic_frame(
            frame=semantic_frame,
            permission_result=field_permission_result,
        )
        post_filter_observed = len(list(getattr(semantic_frame, "field_observations", []) or []))
        post_filter_fields = sorted(
            {
                str(getattr(item, "field", "") or "").strip()
                for item in list(getattr(semantic_frame, "field_observations", []) or [])
                if str(getattr(item, "field", "") or "").strip()
            }
        )
        semantic_status = next(
            (
                str(note).split("=", 1)[1]
                for note in list(getattr(semantic_frame, "notes", []) or [])
                if str(note).startswith("ai_semantic_status=")
            ),
            "disabled" if not use_ai_semantic else "unknown",
        )
        accepted_fields, provisional_fields, pending_fields, rejected_fields = self.field_acceptance_service.accept(
            frame=semantic_frame
        )
        (
            accepted_fields,
            provisional_fields,
            pending_fields,
            expected_profile_version,
            expected_profile_updated_at,
        ) = (
            self.field_update_policy_service.resolve_updates(
                frame=semantic_frame,
                accepted_fields=accepted_fields,
                provisional_fields=provisional_fields,
                pending_fields=pending_fields,
                user_profile=turn_input.user_profile,
            )
        )
        logger.info(
            "[unified_turn_understanding.ai_semantic_obs] trigger=%s status=%s source=%s pre_filter=%s post_filter=%s pre_fields=%s post_fields=%s allowed=%s blocked=%s accepted=%s provisional=%s pending=%s rejected=%s",
            ai_trigger_reason or "disabled",
            semantic_status,
            getattr(semantic_frame, "source", "") or "-",
            pre_filter_observed,
            post_filter_observed,
            ",".join(pre_filter_fields) if pre_filter_fields else "-",
            ",".join(post_filter_fields) if post_filter_fields else "-",
            ",".join(sorted(field_permission_result.allowed_fields or set())) if field_permission_result.allowed_fields else "-",
            ",".join(sorted(field_permission_result.blocked_fields or set())) if field_permission_result.blocked_fields else "-",
            len(accepted_fields),
            len(provisional_fields),
            len(pending_fields),
            len(rejected_fields),
        )
        persistence_plan = self.persistence_plan_service.build_plan(
            frame=semantic_frame,
            accepted_fields=accepted_fields,
            provisional_fields=provisional_fields,
            pending_fields=pending_fields,
            rejected_fields=rejected_fields,
            expected_profile_version=expected_profile_version,
            expected_profile_updated_at=expected_profile_updated_at,
        )
        governed_result = self.turn_result_adapter.project(
            frame=semantic_frame,
            fallback_result=governed_result,
        )
        previous_evidence = dict(getattr(governed_result, "resolved_field_evidence", {}) or {})
        governed_result.resolved_slots = self.resolved_slots_adapter.project_slots(plan=persistence_plan)
        governed_result.resolved_field_evidence = self.resolved_slots_adapter.project_evidence(
            plan=persistence_plan,
            fallback_evidence=previous_evidence,
        )
        setattr(governed_result, "persistence_plan", persistence_plan)
        setattr(governed_result, "followup_inputs", self.followup_inputs_adapter.project(plan=persistence_plan))
        governed_result = self.field_derivation_layer.derive(result=governed_result)
        priority_decision = self.turn_priority_policy.decide(
            turn_input=turn_input,
            semantic_result=governed_result,
            persistence_plan=persistence_plan,
        )
        governed_result.priority_decision = priority_decision
        semantic_result = governed_result
        unified_result = UnifiedTurnUnderstandingResult(
            lexical_signals=lexical_signals,
            semantic_result=semantic_result,
            decision_source=decision_source,
            reply_act_result=reply_act_result,
            field_permission_result=field_permission_result,
            priority_decision=priority_decision,
            resolved_field_evidence=dict(governed_result.resolved_field_evidence or {}),
            field_derivations=dict(governed_result.field_derivations or {}),
            semantic_frame=semantic_frame,
            persistence_plan=persistence_plan,
            notes=[f"ai_semantic_trigger={ai_trigger_reason or 'disabled'}"],
        )
        lexical_true = sorted(name for name, value in (lexical_signals.signals or {}).items() if value)
        inferred_occupation_candidate = str(
            getattr(turn_input.user_profile, "occupation_inference_candidate", "") or ""
        ).strip()
        inferred_occupation_confidence = 0.0
        logger.info(
            "[unified_turn_understanding] source=%s ai_trigger=%s lexical=%s semantic=%s/%s conf=%.2f reply_act=%s priority=%s/%s observed=%s accepted=%s provisional=%s pending=%s rejected=%s occupation_inference_candidate=%s occupation_inference_confidence=%s",
            decision_source,
            ai_trigger_reason or "disabled",
            lexical_true,
            semantic_result.primary_turn_type,
            semantic_result.subtype,
            float(semantic_result.confidence or 0.0),
            reply_act_result.reply_act or "-",
            priority_decision.primary_task,
            priority_decision.decision_reason or "-",
            len(semantic_frame.field_observations or []),
            len(persistence_plan.accepted_fields or []),
            len(getattr(persistence_plan, "provisional_fields", []) or []),
            len(persistence_plan.pending_fields or []),
            len(persistence_plan.rejected_fields or []),
            inferred_occupation_candidate or "-",
            f"{float(inferred_occupation_confidence or 0.66):.2f}" if inferred_occupation_candidate else "-",
        )
        return unified_result.to_turn_understanding_result()

    @staticmethod
    def _get_question_state(turn_input: TurnUnderstandingInput) -> dict:
        profile = getattr(turn_input, "user_profile", None)
        raw = getattr(profile, "last_question_state", None) if profile is not None else None
        if isinstance(raw, dict):
            return dict(raw)
        return {}

    @staticmethod
    def _env_enabled(name: str, default: bool = True) -> bool:
        raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
        return raw not in {"0", "false", "off", "no"}

    @classmethod
    def _extract_asked_fields_from_question_state(cls, question_state: dict) -> set[str]:
        asked_fields = set()
        for item in list((question_state or {}).get("asked_fields", []) or []):
            field = str(item or "").strip()
            if field:
                asked_fields.add(field)
        for item in list((question_state or {}).get("side_fields", []) or []):
            field = str(item or "").strip()
            if field:
                asked_fields.add(field)
        return asked_fields

    @classmethod
    def _should_enable_sync_ai_semantic(
        cls,
        *,
        turn_input: TurnUnderstandingInput,
        question_state: dict,
        semantic_result: TurnUnderstandingResult,
        reply_act_result,
    ) -> tuple[bool, str]:
        if not cls._env_enabled("UNIFIED_TURN_SYNC_AI_HIGH_RISK_ENABLED", True):
            return False, "default_async_backfill_only"

        message = str(getattr(turn_input, "user_message", "") or "").strip()
        if not message:
            return False, "default_async_backfill_only"

        asked_fields = cls._extract_asked_fields_from_question_state(question_state)
        high_risk_asked = sorted(field for field in asked_fields if field in cls._SYNC_HIGH_RISK_FIELDS)
        if high_risk_asked:
            return True, f"sync_high_risk_followup:{','.join(high_risk_asked)}"

        primary_turn_type = str(getattr(semantic_result, "primary_turn_type", "") or "").strip()
        reply_act = str(getattr(reply_act_result, "reply_act", "") or "").strip()
        has_semantic_payload = bool(getattr(semantic_result, "resolved_slots", {}) or getattr(semantic_result, "slot_candidates", {}))
        if primary_turn_type in {"contact_answer", "confirmation", "correction"} and has_semantic_payload:
            return True, f"sync_collection_turn:{primary_turn_type}"
        if reply_act in {"direct_answer", "contact_answer", "correction"}:
            return True, f"sync_reply_act:{reply_act}"

        return False, "default_async_backfill_only"

    @staticmethod
    def _filter_semantic_frame(
        *,
        frame,
        permission_result,
    ):
        allowed = set(getattr(permission_result, "allowed_fields", set()) or set())
        blocked = set(getattr(permission_result, "blocked_fields", set()) or set())
        if not allowed and not blocked:
            return frame

        filtered_observations = []
        for observation in list(frame.field_observations or []):
            field_name = str(getattr(observation, "field", "") or "").strip()
            if not field_name:
                continue
            authoritative_observation = UnifiedTurnUnderstandingService._is_authoritative_direct_write_observation(
                frame=frame,
                observation=observation,
            )
            if field_name in blocked and not authoritative_observation:
                continue
            if (
                allowed
                and field_name not in allowed
                and not UnifiedTurnUnderstandingService._is_allowed_structured_field(
                    field_name=field_name,
                    allowed_fields=allowed,
                )
                and not authoritative_observation
            ):
                continue
            filtered_observations.append(observation)

        frame.field_observations = filtered_observations
        return frame

    @staticmethod
    def _is_allowed_structured_field(*, field_name: str, allowed_fields: set[str]) -> bool:
        if field_name in {"partner_pref_height", "partner_pref_age", "partner_pref_income"}:
            return "partner_requirement" in allowed_fields
        if field_name == "partner_pref_age_relation":
            return "partner_pref_age" in allowed_fields or "partner_requirement" in allowed_fields
        return False

    @staticmethod
    def _is_authoritative_direct_write_observation(*, frame, observation) -> bool:
        if str(getattr(frame, "source", "") or "").strip() != "ai_structured_extraction":
            return False
        if str(getattr(observation, "write_mode", "") or "").strip() != "direct_write":
            return False
        scope = str(getattr(observation, "scope", "") or "").strip()
        return scope in {"self", "partner", "contact"}
    _SYNC_HIGH_RISK_FIELDS = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
