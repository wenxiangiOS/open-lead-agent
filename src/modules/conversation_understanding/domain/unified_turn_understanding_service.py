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

    _DENSE_INTRO_ALLOWED_TYPES = {"opening", "profile_answer", "contact_answer", "confirmation", "correction"}
    _DENSE_INTRO_REPLY_ACTS = {"direct_answer", "contact_answer", "correction", "preference_statement", "off_target_answer"}
    _DENSE_INTRO_SELF_FIELDS = {
        "sex",
        "age",
        "age_label",
        "location",
        "education",
        "occupation",
        "marital_status",
        "monthly_income",
        "height",
        "weight",
    }
    _DENSE_INTRO_CONTACT_FIELDS = {"contact", "phone", "wechat"}
    _DENSE_INTRO_CONTACT_RE = re.compile(r"(?:微信|电话|手机号|联系方式|vx|wx|v[:：]?)|(?:1[3-9]\d{9})")
    _DENSE_INTRO_PARTNER_RE = re.compile(r"(?:找对象|找男朋友|找女朋友|想找|期待|另一半|男生|女生|不要\d{2}|最好|有房有车|工作稳定|同城|本地)")
    _DENSE_INTRO_SELF_SIGNAL_RE = re.compile(
        r"(?:\d{2}后|(?:19|20)?\d{2}年(?:的)?|(?:未婚|单身|离异)|(?:本科|硕士|博士|大专|研究生|港硕)|"
        r"(?:在编|教师|老师|护士|产品|运营|设计|外贸|程序员|研发)|(?:深圳|广州|上海|北京|杭州|成都|苏州)|"
        r"(?:男生|女生|男的|女的|我男|我女)|(?:收入|年薪|月薪|年入))"
    )
    _DENSE_INTRO_QUESTION_RE = re.compile(r"(?:怎么收费|收费|多少钱|价格|费用|流程|怎么安排|靠谱吗|真实吗)")
    _DENSE_INTRO_SELF_CATEGORY_PATTERNS = {
        "age": re.compile(r"(?:\d{2}后|(?:19|20)?\d{2}年(?:的)?)"),
        "marital_status": re.compile(r"(?:未婚|单身|离异)"),
        "education": re.compile(r"(?:本科|硕士|博士|大专|研究生|港硕)"),
        "occupation": re.compile(r"(?:在编|教师|老师|护士|产品|运营|设计|外贸|程序员|研发)"),
        "location": re.compile(r"(?:深圳|广州|上海|北京|杭州|成都|苏州)"),
        "sex": re.compile(r"(?:男生|女生|男的|女的|我男|我女|女教师|男教师)"),
        "monthly_income": re.compile(r"(?:收入|年薪|月薪|年入)"),
    }

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
        turn_mode = self._resolve_turn_mode(
            turn_input=turn_input,
            semantic_result=governed_result,
            reply_act_result=reply_act_result,
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
                turn_mode=turn_mode,
            )
        effective_ai_timeout = ai_timeout_seconds
        if effective_ai_timeout is None and use_ai_semantic and ai_trigger_reason.startswith("sync_dense_intro"):
            effective_ai_timeout = self._resolve_dense_intro_ai_timeout()
        semantic_frame = await self.ai_semantic_extraction_service.extract(
            snapshot=snapshot,
            fallback_result=governed_result,
            enable_ai=use_ai_semantic,
            ai_timeout_seconds=effective_ai_timeout,
            enforce_mainline_blocking_cap=use_ai_semantic and not force_ai,
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
        fallback_merge_note = next(
            (
                str(note).split("=", 1)[1]
                for note in list(getattr(semantic_frame, "notes", []) or [])
                if str(note).startswith("fallback_projection_merge=")
            ),
            "-",
        )
        fallback_refinement_note = next(
            (
                str(note).split("=", 1)[1]
                for note in list(getattr(semantic_frame, "notes", []) or [])
                if str(note).startswith("fallback_projection_refinement=")
            ),
            "-",
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
            "[unified_turn_understanding.ai_semantic_obs] trigger=%s status=%s source=%s pre_filter=%s post_filter=%s pre_fields=%s post_fields=%s allowed=%s blocked=%s accepted=%s provisional=%s pending=%s rejected=%s fallback_merge=%s fallback_refinement=%s",
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
            fallback_merge_note,
            fallback_refinement_note,
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
            notes=[
                f"ai_semantic_trigger={ai_trigger_reason or 'disabled'}",
                f"turn_mode={turn_mode}",
            ],
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
        turn_mode: str = "default",
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
        if turn_mode == "dense_intro" and cls._env_enabled("UNIFIED_TURN_SYNC_AI_DENSE_INTRO_ENABLED", True):
            if cls._dense_intro_can_use_async_backfill_only(
                turn_input=turn_input,
                semantic_result=semantic_result,
            ):
                return False, "dense_intro_async_backfill_only"
            return True, "sync_dense_intro"
        if primary_turn_type in {"contact_answer", "confirmation", "correction"} and has_semantic_payload:
            return True, f"sync_collection_turn:{primary_turn_type}"
        if reply_act in {"direct_answer", "contact_answer", "correction"}:
            return True, f"sync_reply_act:{reply_act}"

        return False, "default_async_backfill_only"

    @staticmethod
    def _resolve_dense_intro_ai_timeout() -> float | None:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_DENSE_INTRO_TIMEOUT_SECONDS", "") or "").strip()
        if not raw:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return max(1.0, value) if value > 0 else None

    @classmethod
    def _dense_intro_can_use_async_backfill_only(
        cls,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
    ) -> bool:
        message = str(getattr(turn_input, "user_message", "") or "").strip()
        if not message:
            return False

        observed_fields = {
            str(field_name).strip()
            for field_name in dict(getattr(semantic_result, "resolved_slots", {}) or {}).keys()
            if str(field_name).strip()
        }
        observed_fields.update(
            str(field_name).strip()
            for field_name in dict(getattr(semantic_result, "slot_candidates", {}) or {}).keys()
            if str(field_name).strip()
        )
        if not observed_fields:
            return False

        self_fields = {field for field in observed_fields if field in cls._DENSE_INTRO_SELF_FIELDS}
        partner_fields = {field for field in observed_fields if cls._is_partner_field(field)}
        contact_fields = {field for field in observed_fields if field in cls._DENSE_INTRO_CONTACT_FIELDS}

        partner_signal = bool(cls._DENSE_INTRO_PARTNER_RE.search(message))
        contact_signal = bool(cls._DENSE_INTRO_CONTACT_RE.search(message))
        question_signal = bool(cls._DENSE_INTRO_QUESTION_RE.search(message))
        self_signal_categories = cls._extract_dense_intro_self_signal_categories(message)
        stable_textual_self_coverage = cls._has_dense_intro_stable_textual_self_coverage(
            self_fields=self_fields,
            self_signal_categories=self_signal_categories,
            partner_fields=partner_fields,
            partner_signal=partner_signal,
            question_signal=question_signal,
        )

        if len(self_fields) < 3 and not stable_textual_self_coverage:
            return False
        # Long self-intros that already expose multiple stable self fields plus contact info
        # can rely on fallback planning even if partner subslots are not yet projected here.
        if len(self_fields) >= 4 and contact_signal and contact_fields and partner_signal:
            return True
        if question_signal:
            return stable_textual_self_coverage
        if partner_signal and not partner_fields:
            return bool(question_signal and stable_textual_self_coverage)
        if contact_signal and not contact_fields and not stable_textual_self_coverage:
            return False

        return bool(partner_fields or contact_fields or len(self_fields) >= 4 or stable_textual_self_coverage)

    @classmethod
    def _extract_dense_intro_self_signal_categories(cls, message: str) -> set[str]:
        text = str(message or "").strip()
        if not text:
            return set()
        return {
            category
            for category, pattern in cls._DENSE_INTRO_SELF_CATEGORY_PATTERNS.items()
            if pattern.search(text)
        }

    @staticmethod
    def _has_dense_intro_stable_textual_self_coverage(
        *,
        self_fields: set[str],
        self_signal_categories: set[str],
        partner_fields: set[str],
        partner_signal: bool,
        question_signal: bool,
    ) -> bool:
        if len(self_fields) < 2:
            return False
        if len(self_signal_categories) < 3:
            return False
        if question_signal and not (partner_signal or partner_fields):
            return False
        return True

    @staticmethod
    def _is_partner_field(field_name: str) -> bool:
        field = str(field_name or "").strip()
        return field == "partner_requirement" or field == "partner_gender_preference" or field.startswith(
            "partner_pref_"
        )

    @classmethod
    def _resolve_turn_mode(
        cls,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        reply_act_result,
    ) -> str:
        if cls._looks_like_dense_intro_turn(
            turn_input=turn_input,
            semantic_result=semantic_result,
            reply_act_result=reply_act_result,
        ):
            return "dense_intro"
        return "default"

    @classmethod
    def _looks_like_dense_intro_turn(
        cls,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        reply_act_result,
    ) -> bool:
        message = str(getattr(turn_input, "user_message", "") or "").strip()
        if len(message) < 20:
            return False
        primary_turn_type = str(getattr(semantic_result, "primary_turn_type", "") or "").strip()
        if primary_turn_type and primary_turn_type not in cls._DENSE_INTRO_ALLOWED_TYPES:
            return False
        reply_act = str(getattr(reply_act_result, "reply_act", "") or "").strip()
        if reply_act and reply_act not in cls._DENSE_INTRO_REPLY_ACTS and primary_turn_type not in {"opening", "profile_answer"}:
            return False

        observed_fields = {
            str(field_name).strip()
            for field_name in dict(getattr(semantic_result, "resolved_slots", {}) or {}).keys()
            if str(field_name).strip()
        }
        observed_fields.update(
            str(field_name).strip()
            for field_name in dict(getattr(semantic_result, "slot_candidates", {}) or {}).keys()
            if str(field_name).strip()
        )
        punctuation_count = len(re.findall(r"[，,、；;。.!！？]", message))
        clause_like_count = max(punctuation_count + 1, len([part for part in re.split(r"[，,、；;。.!！？\s]+", message) if part]))
        self_signal_count = len(cls._DENSE_INTRO_SELF_SIGNAL_RE.findall(message))
        signal_score = 0
        if len(observed_fields) >= 3:
            signal_score += 2
        elif len(observed_fields) >= 2:
            signal_score += 1
        if self_signal_count >= 3:
            signal_score += 2
        elif self_signal_count >= 2:
            signal_score += 1
        if cls._DENSE_INTRO_CONTACT_RE.search(message):
            signal_score += 1
        if cls._DENSE_INTRO_PARTNER_RE.search(message):
            signal_score += 1
        if cls._DENSE_INTRO_QUESTION_RE.search(message):
            signal_score += 1
        if clause_like_count >= 4:
            signal_score += 1
        return signal_score >= 4

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
        if field_name.startswith("partner_pref_"):
            return field_name in allowed_fields or "partner_requirement" in allowed_fields
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
