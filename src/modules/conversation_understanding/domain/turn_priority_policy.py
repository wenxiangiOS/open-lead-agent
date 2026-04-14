from __future__ import annotations

import re

from src.modules.conversation.domain.turn_understanding_models import (
    TurnPriorityDecision,
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.models import TurnPersistencePlan


class TurnPriorityPolicy:
    """Centralize multi-signal turn priority ordering into one decision."""

    _CONTACT_FIELDS = {"phone", "wechat", "contact"}
    _CORE_FIELDS = {"sex", "age", "location", "education", "occupation"}
    _PREFERENCE_FIELDS = {
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
    _FAQ_INTENT_HINTS = {
        "contact_why",
        "contact_repeat_why",
        "info_collection_why",
        "clarification",
        "mediator",
        "fee",
        "store_location",
        "how_match",
        "contact_exchange",
        "photo",
        "success_rate",
        "service_area",
        "timeline",
        "reliable",
        "privacy",
        "specific_target",
        "marriage_pace",
        "service_confirmation_mid",
    }
    _FAQ_TOPIC_MAP = {
        "safety": "reliable",
        "contact_policy": "contact_why",
        "service_flow": "how_match",
        "pricing": "fee",
    }
    _DIVORCE_COMPLETE_PATTERNS = (
        r"办妥",
        r"办好",
        r"办完",
        r"判决书",
        r"离婚证",
        r"调解书",
        r"恢复单身",
        r"离干净",
    )
    _DIVORCE_INCOMPLETE_PATTERNS = (
        r"没办完",
        r"没办妥",
        r"还没办",
        r"办理中",
        r"手续还在办",
        r"没离干净",
        r"分居中",
    )

    def decide(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        persistence_plan: TurnPersistencePlan | None,
    ) -> TurnPriorityDecision:
        observed_fields = self._collect_observed_fields(
            semantic_result=semantic_result,
            persistence_plan=persistence_plan,
        )
        candidates: list[tuple[int, str, str, str, str | None]] = []
        faq_intent = self._resolve_faq_intent(semantic_result)

        if semantic_result.primary_turn_type == "risk_guard":
            candidates.append((1, "risk_guard", "risk_guard", "answer_only", None))
        elif semantic_result.primary_turn_type == "closing_exit":
            candidates.append((1, "closing_exit", "closing_exit", "hold_only", None))
        elif semantic_result.primary_turn_type == "refusal_boundary_complaint":
            subtype = str(semantic_result.subtype or "").strip() or "boundary_or_complaint"
            reason = f"boundary_or_complaint:{subtype}"
            candidates.append((1, "boundary_or_complaint", reason, "hold_only", None))

        if faq_intent:
            response_mode = "answer_then_resume" if self._has_lower_priority_signal(observed_fields, semantic_result) else "answer_only"
            candidates.append((2, "user_question", f"faq:{faq_intent}", response_mode, None))

        status_field, status_reason = self._resolve_pending_status(
            turn_input=turn_input,
            semantic_result=semantic_result,
            observed_fields=observed_fields,
        )
        if status_field:
            candidates.append((3, "status_confirmation", status_reason, "confirm_only", status_field))

        if self._has_contact_signal(observed_fields, semantic_result) and not self._prefer_profile_collection_over_contact_record(
            turn_input=turn_input,
            semantic_result=semantic_result,
            observed_fields=observed_fields,
        ):
            candidates.append((4, "contact_record", "contact_signal_detected", "record_only", None))

        if observed_fields & self._CORE_FIELDS:
            candidates.append((5, "core_profile_collection", "core_profile_signal_detected", "ask_only", None))

        if observed_fields & self._PREFERENCE_FIELDS:
            candidates.append((6, "preference_collection", "preference_signal_detected", "ask_only", None))

        if not candidates:
            return self._build_default_decision(turn_input=turn_input, semantic_result=semantic_result)

        candidates.sort(key=lambda item: (item[0], item[1]))
        level, primary_task, reason, response_mode, locked_field = candidates[0]
        suppressed_tasks = [task for _, task, _, _, _ in candidates[1:]]

        allow_contact_target = True
        allow_medium_target = True
        prioritize_user_question = False
        defer_complementary_contact = False
        collection_tier = "core"

        if primary_task in {"risk_guard", "closing_exit", "boundary_or_complaint", "status_confirmation"}:
            allow_contact_target = False
            allow_medium_target = False
        elif primary_task == "user_question":
            allow_contact_target = False
            allow_medium_target = False
            prioritize_user_question = True
        elif primary_task == "contact_record":
            allow_contact_target = False
            allow_medium_target = False
            defer_complementary_contact = True
        elif primary_task == "preference_collection":
            collection_tier = "preference"

        return TurnPriorityDecision(
            primary_task=primary_task,
            priority_level=level,
            decision_reason=reason,
            response_mode=response_mode,
            suppressed_tasks=suppressed_tasks,
            locked_field=locked_field,
            prioritized_question_intent=faq_intent,
            collection_tier=collection_tier,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            prioritize_user_question=prioritize_user_question,
            defer_complementary_contact=defer_complementary_contact,
        )

    def _build_default_decision(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
    ) -> TurnPriorityDecision:
        profile = getattr(turn_input, "user_profile", None)
        collection_progress = getattr(profile, "collection_progress", {}) if profile is not None else {}
        has_uncovered_core = any(not bool(collection_progress.get(field, False)) for field in self._CORE_FIELDS)
        primary_task = "core_profile_collection" if has_uncovered_core else "preference_collection"
        return TurnPriorityDecision(
            primary_task=primary_task,
            priority_level=5 if primary_task == "core_profile_collection" else 6,
            decision_reason=f"default_from_{semantic_result.primary_turn_type or 'unknown'}",
            response_mode="ask_only",
            collection_tier="core" if primary_task == "core_profile_collection" else "preference",
        )

    def _resolve_pending_status(
        self,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        observed_fields: set[str],
    ) -> tuple[str | None, str]:
        profile = getattr(turn_input, "user_profile", None)
        message = str(getattr(turn_input, "user_message", "") or "").strip()
        if profile is None:
            return None, ""

        if self._has_divorce_confirmation_pending(profile) and not self._looks_like_divorce_status_answer(message):
            return "marital_status", "divorce_confirmation_pending"

        pending_sex = str(getattr(profile, "pending_sex_confirmation", "") or "").strip()
        if (
            pending_sex
            and "sex" not in observed_fields
            and semantic_result.primary_turn_type != "confirmation"
            and str(getattr(profile, "resume_profile_target", "") or "").strip() != "sex"
        ):
            return "sex", "sex_confirmation_pending"

        pending_bucket = str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
        if pending_bucket and not getattr(profile, "birth_year_confirmation_closed", False):
            if self._looks_like_birth_year_confirmation_answer(message):
                return None, ""
            if (
                "age" not in observed_fields
                and "age_label" not in observed_fields
                and semantic_result.primary_turn_type != "confirmation"
                and str(getattr(profile, "resume_profile_target", "") or "").strip() != "age"
            ):
                return "age", "birth_year_confirmation_pending"

        return None, ""

    @classmethod
    def _has_divorce_confirmation_pending(cls, profile) -> bool:
        marital_status = str(getattr(profile, "marital_status", "") or "").strip()
        return (
            "离异" in marital_status
            and "办妥" not in marital_status
            and not bool(getattr(profile, "divorce_confirmed", False))
            and bool(getattr(profile, "divorce_confirmation_pending", False))
        )

    @classmethod
    def _looks_like_divorce_status_answer(cls, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if any(re.search(pattern, compact) for pattern in cls._DIVORCE_COMPLETE_PATTERNS):
            return True
        if any(re.search(pattern, compact) for pattern in cls._DIVORCE_INCOMPLETE_PATTERNS):
            return True
        return False

    @staticmethod
    def _looks_like_birth_year_confirmation_answer(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if re.search(r"(先不说|先不聊|不方便|不想说|保密|不告诉|不透露)", compact):
            return False

        year_match = re.search(r"(?<!\d)(?:19\d{2}|20\d{2}|\d{2})年(?:的)?(?:出生)?", compact)
        if year_match:
            prefix = compact[max(0, year_match.start() - 6):year_match.start()]
            looks_like_partner_preference = bool(
                re.search(r"(找|想找|希望|最好|起码|至少|不要|对方|另一半|男方|女方)$", prefix)
            )
            if looks_like_partner_preference and year_match.start() != 0 and not re.search(r"(我|本人|自己|今年|出生)", compact):
                return False
            return True

        return bool(re.search(r"(?:我|本人|自己).{0,4}\d{1,2}岁", text))

    def _has_lower_priority_signal(self, observed_fields: set[str], semantic_result: TurnUnderstandingResult) -> bool:
        if semantic_result.primary_turn_type == "contact_answer":
            return True
        return bool(
            observed_fields & self._CONTACT_FIELDS
            or observed_fields & self._CORE_FIELDS
            or observed_fields & self._PREFERENCE_FIELDS
        )

    @classmethod
    def _has_contact_signal(cls, observed_fields: set[str], semantic_result: TurnUnderstandingResult) -> bool:
        if str(getattr(semantic_result, "subtype", "") or "").strip() == "contact_provided":
            return True
        return bool(observed_fields & cls._CONTACT_FIELDS)

    @classmethod
    def _prefer_profile_collection_over_contact_record(
        cls,
        *,
        turn_input: TurnUnderstandingInput,
        semantic_result: TurnUnderstandingResult,
        observed_fields: set[str],
    ) -> bool:
        if not (observed_fields & cls._CONTACT_FIELDS):
            return False
        if not (observed_fields & cls._CORE_FIELDS or observed_fields & cls._PREFERENCE_FIELDS):
            return False

        semantic_frame = getattr(semantic_result, "semantic_frame", None)
        primary_domain = str(getattr(semantic_frame, "primary_domain", "") or "").strip().lower()
        if primary_domain in {"profile", "mixed"}:
            return True

        if semantic_result.primary_turn_type not in {"profile_answer", "opening"}:
            return False

        message = str(getattr(turn_input, "user_message", "") or "").strip()
        compact = re.sub(r"\s+", "", message)
        if not compact:
            return False
        return bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后)", compact)
            or re.search(r"(男生|女生|男的|女的|未婚|单身|离异|本科|大专|硕士|博士|深户)", compact)
            or re.search(r"(想找|找(?:男朋友|女朋友|对象|另一半|[男女]生)|期待遇见|希望对方|最好|优先)", compact)
        )

    def _resolve_faq_intent(self, semantic_result: TurnUnderstandingResult) -> str | None:
        semantic_frame = getattr(semantic_result, "semantic_frame", None)
        user_questions = list(getattr(semantic_frame, "user_questions", []) or [])
        if user_questions:
            topic = str(getattr(user_questions[0], "topic", "") or "").strip()
            topic = self._FAQ_TOPIC_MAP.get(topic, topic)
            if topic:
                return topic

        subtype = str(getattr(semantic_result, "subtype", "") or "").strip()
        if semantic_result.primary_turn_type == "faq_concern":
            return subtype or "faq"
        if semantic_result.answer_first and subtype in self._FAQ_INTENT_HINTS:
            return subtype
        return None

    @classmethod
    def _collect_observed_fields(
        cls,
        *,
        semantic_result: TurnUnderstandingResult,
        persistence_plan: TurnPersistencePlan | None,
    ) -> set[str]:
        fields = set(str(field).strip() for field in dict(getattr(semantic_result, "resolved_slots", {}) or {}).keys() if str(field).strip())
        if persistence_plan is None:
            return fields

        for item in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(item, "field", "") or "").strip()
            if field_name:
                fields.add(field_name)
        for item in list(getattr(persistence_plan, "provisional_fields", []) or []):
            field_name = str(getattr(item, "field", "") or "").strip()
            if field_name:
                fields.add(field_name)
        for item in list(getattr(persistence_plan, "pending_fields", []) or []):
            field_name = str(getattr(item, "field", "") or "").strip()
            if field_name:
                fields.add(field_name)
        return fields
