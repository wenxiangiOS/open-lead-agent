from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AsyncSemanticBackfillDecision:
    should_schedule: bool
    reason: str
    route_name: str
    target_fields: list[str] = field(default_factory=list)
    fingerprint: str = ""
    primary_turn_type: str = ""
    priority_task: str = ""
    observed_count: int = 0


class AsyncSemanticBackfillPolicyService:
    """Decide whether a turn is valuable enough for async AI semantic backfill."""

    _HIGH_RISK_FIELDS = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
    _CONTACT_FIELDS = {"phone", "wechat", "contact"}
    _PARTNER_FIELDS = {
        "partner_requirement",
        "partner_gender_preference",
        "partner_pref_age",
        "partner_pref_location",
        "partner_pref_industry",
        "partner_pref_age_relation",
        "partner_pref_locality",
        "partner_pref_height",
        "partner_pref_education",
        "partner_pref_personality",
        "partner_pref_income",
        "partner_pref_other",
    }
    _LOW_SIGNAL_TURN_TYPES = {"closing_exit", "confirmation", "invalid_input"}
    _SOFT_PROFILE_SUMMARY_RE = re.compile(r"(喜欢|爱好|旅游|做饭|原生家庭|感情经历|[EI]人|性格|慢热|外向|内向)")
    _PARTNER_SUMMARY_RE = re.compile(
        r"(找对象|找男朋友|找女朋友|想找|想着|期待|遇见|希望对方|最好|优先|不要\d{2}|不要|同城|本地|同在|有房有车|工作稳定|积极阳光|三观正|情绪稳定)"
    )

    def decide(
        self,
        *,
        route_name: str,
        user_message: str,
        turn_understanding: Any,
    ) -> AsyncSemanticBackfillDecision:
        route = str(route_name or "unknown").strip() or "unknown"
        if turn_understanding is None:
            return AsyncSemanticBackfillDecision(
                should_schedule=False,
                reason="missing_understanding",
                route_name=route,
            )

        persistence_plan = getattr(turn_understanding, "persistence_plan", None)
        if persistence_plan is None:
            return AsyncSemanticBackfillDecision(
                should_schedule=False,
                reason="missing_persistence_plan",
                route_name=route,
            )

        semantic_frame = getattr(turn_understanding, "semantic_frame", None)
        semantic_source = str(getattr(semantic_frame, "source", "") or "").strip()
        primary_turn_type = str(getattr(turn_understanding, "primary_turn_type", "") or "").strip()
        has_conflict = primary_turn_type == "correction" or self._has_conflict_observation(semantic_frame)
        summary_gap = self._has_summary_gap(
            user_message=user_message,
            semantic_frame=semantic_frame,
        )

        target_fields = self._collect_target_fields(persistence_plan)
        if semantic_source == "ai_structured_extraction" and not (target_fields or has_conflict or summary_gap):
            return AsyncSemanticBackfillDecision(
                should_schedule=False,
                reason="already_ai",
                route_name=route,
            )
        observed_fields = self._collect_observed_fields(turn_understanding=turn_understanding, persistence_plan=persistence_plan)
        high_risk_fields = sorted({field for field in observed_fields if self._is_high_risk_field(field)})
        priority_task = str(
            getattr(getattr(turn_understanding, "priority_decision", None), "primary_task", "") or ""
        ).strip()
        user_questions = list(getattr(semantic_frame, "user_questions", []) or [])
        observation_count = len(list(getattr(semantic_frame, "field_observations", []) or []))

        reason_parts: list[str] = []
        if target_fields:
            reason_parts.append("pending_or_provisional")
        if high_risk_fields:
            reason_parts.append("high_risk")
        if self._is_mixed_question_turn(route=route, priority_task=priority_task, user_questions=user_questions, observed_fields=observed_fields):
            reason_parts.append("mixed_question")
        if self._is_multi_slot_turn(observed_fields=observed_fields, observation_count=observation_count):
            reason_parts.append("multi_slot")
        if has_conflict:
            reason_parts.append("correction_or_conflict")
        if summary_gap:
            reason_parts.append("missing_summary")
        if self._has_partner_signal(observed_fields=observed_fields):
            reason_parts.append("partner_preference")
        if priority_task == "status_confirmation" and observed_fields:
            reason_parts.append("status_confirmation")

        if not reason_parts:
            if priority_task == "user_question" and not observed_fields:
                skip_reason = "pure_user_question"
            elif primary_turn_type in self._LOW_SIGNAL_TURN_TYPES and not observed_fields:
                skip_reason = "low_signal_turn"
            else:
                skip_reason = "low_value_turn"
            return AsyncSemanticBackfillDecision(
                should_schedule=False,
                reason=skip_reason,
                route_name=route,
                target_fields=target_fields,
                primary_turn_type=primary_turn_type,
                priority_task=priority_task,
                observed_count=observation_count,
            )

        fingerprint = self._build_fingerprint(
            route_name=route,
            user_message=user_message,
            target_fields=target_fields or sorted(observed_fields),
            primary_turn_type=primary_turn_type,
            priority_task=priority_task,
        )
        return AsyncSemanticBackfillDecision(
            should_schedule=True,
            reason="+".join(reason_parts),
            route_name=route,
            target_fields=target_fields,
            fingerprint=fingerprint,
            primary_turn_type=primary_turn_type,
            priority_task=priority_task,
            observed_count=observation_count,
        )

    @classmethod
    def _collect_target_fields(cls, persistence_plan: Any) -> list[str]:
        fields: list[str] = []
        for item in list(getattr(persistence_plan, "pending_fields", []) or []):
            field_name = str(getattr(item, "field", "") or "").strip()
            if field_name:
                fields.append(field_name)
        for item in list(getattr(persistence_plan, "provisional_fields", []) or []):
            field_name = str(getattr(item, "field", "") or "").strip()
            if field_name:
                fields.append(field_name)
        ordered_unique: list[str] = []
        seen: set[str] = set()
        for field_name in fields:
            if field_name in seen:
                continue
            seen.add(field_name)
            ordered_unique.append(field_name)
        return ordered_unique

    @classmethod
    def _collect_observed_fields(cls, *, turn_understanding: Any, persistence_plan: Any) -> set[str]:
        fields = {
            str(field_name).strip()
            for field_name in dict(getattr(turn_understanding, "resolved_slots", {}) or {}).keys()
            if str(field_name).strip()
        }
        for group_name in ("accepted_fields", "provisional_fields", "pending_fields"):
            for item in list(getattr(persistence_plan, group_name, []) or []):
                field_name = str(getattr(item, "field", "") or "").strip()
                if field_name:
                    fields.add(field_name)
        return fields

    @classmethod
    def _has_partner_signal(cls, *, observed_fields: set[str]) -> bool:
        return any(field in cls._PARTNER_FIELDS or field.startswith("partner_pref_") for field in observed_fields)

    @classmethod
    def _has_conflict_observation(cls, semantic_frame: Any) -> bool:
        for observation in list(getattr(semantic_frame, "field_observations", []) or []):
            if str(getattr(observation, "conflict_hint", "") or "").strip():
                return True
        return False

    @classmethod
    def _has_summary_gap(cls, *, user_message: str, semantic_frame: Any) -> bool:
        notes = {
            str(note).split("=", 1)[0]: str(note).split("=", 1)[1]
            for note in list(getattr(semantic_frame, "notes", []) or [])
            if "=" in str(note)
        }
        text = str(user_message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return False
        if cls._PARTNER_SUMMARY_RE.search(compact) and not str(notes.get("partner_summary") or "").strip():
            return True
        if cls._SOFT_PROFILE_SUMMARY_RE.search(compact) and not str(notes.get("soft_profile_summary") or "").strip():
            return True
        return False

    @classmethod
    def _is_high_risk_field(cls, field_name: str) -> bool:
        canonical = cls._canonical_field(field_name)
        return canonical in cls._HIGH_RISK_FIELDS

    @classmethod
    def _canonical_field(cls, field_name: str) -> str:
        field = str(field_name or "").strip()
        if field in cls._CONTACT_FIELDS:
            return "contact"
        if field.startswith("partner_pref_"):
            return "partner_requirement"
        return field

    @staticmethod
    def _is_mixed_question_turn(
        *,
        route: str,
        priority_task: str,
        user_questions: list[Any],
        observed_fields: set[str],
    ) -> bool:
        return bool(
            priority_task == "user_question"
            and user_questions
            and observed_fields
            and route in {"quick_faq", "preset_response", "model"}
        )

    @staticmethod
    def _is_multi_slot_turn(*, observed_fields: set[str], observation_count: int) -> bool:
        return len(observed_fields) >= 3 or observation_count >= 4

    @staticmethod
    def _build_fingerprint(
        *,
        route_name: str,
        user_message: str,
        target_fields: list[str],
        primary_turn_type: str,
        priority_task: str,
    ) -> str:
        normalized_message = re.sub(r"\s+", "", str(user_message or "").strip().lower())
        payload = "|".join(
            [
                str(route_name or "").strip(),
                normalized_message,
                ",".join(sorted(str(item).strip() for item in list(target_fields or []) if str(item).strip())),
                str(primary_turn_type or "").strip(),
                str(priority_task or "").strip(),
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
