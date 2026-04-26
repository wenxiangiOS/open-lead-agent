from __future__ import annotations

import re

from src.modules.conversation_understanding.domain.models import (
    AcceptedField,
    FieldObservation,
    PendingField,
    RejectedField,
    TurnSemanticFrame,
)
from src.modules.profile_collection.domain.extraction_service import ExtractionService


class FieldAcceptanceService:
    """Validate observations and classify them into accepted/pending/rejected."""

    _CORE_FIELDS = {"sex", "age", "location", "education", "occupation", "contact"}
    _MEDIUM_FIELDS = {"marital_status", "partner_requirement", "monthly_income"}
    _LOW_FIELDS = {"last_name", "height", "weight"}
    _HIGH_RISK_FIELDS = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
    _COMMIT_THRESHOLD = {"high": 0.92, "core": 0.88, "medium": 0.82, "low": 0.72}
    _WEAK_PARTNER_REQUIREMENT_VALUES = {"都行", "都可以", "可以", "随缘", "看感觉", "再说"}
    _SELF_PROFILE_NOISE_IN_PARTNER_REQUIREMENT_RE = re.compile(r"(做饭|旅游|原生家庭|感情经历|[EI]人)")

    def accept(
        self,
        *,
        frame: TurnSemanticFrame,
    ) -> tuple[list[AcceptedField], list[AcceptedField], list[PendingField], list[RejectedField]]:
        accepted: list[AcceptedField] = []
        provisional: list[AcceptedField] = []
        pending: list[PendingField] = []
        rejected: list[RejectedField] = []
        best_partner_requirement = self._resolve_best_partner_requirement_observation(frame=frame)

        for observation in frame.field_observations:
            rejection_reason = self._validate(observation)
            if rejection_reason:
                rejected.append(
                    RejectedField(
                        field=observation.field,
                        candidate_value=observation.normalized_value,
                        reason=rejection_reason,
                        scope=observation.scope,
                    )
                )
                continue

            field_name = str(observation.field or "").strip()
            source_channel = self._resolve_source_channel(frame=frame, observation=observation)
            risk_level = self._resolve_risk_level(field_name)
            mode = str(observation.write_mode or "soft_confirm")
            explicit_self_marker_commit = self._allows_non_ai_high_risk_commit(
                observation=observation,
                source_channel=source_channel,
            )
            explicit_partner_marker_commit = self._allows_non_ai_partner_requirement_commit(
                observation=observation,
                source_channel=source_channel,
            )
            if mode != "direct_write":
                pending.append(
                    PendingField(
                        field=field_name,
                        candidate_value=observation.normalized_value,
                        reason="soft_confirm",
                        scope=observation.scope,
                        confirmation_question_type="soft_confirm",
                        persistence_state="pending_confirm",
                        risk_level=risk_level,
                        source_channel=source_channel,
                    )
                )
                continue

            # 高风险字段只允许 AI 结构化语义直接进入 committed，其余进入 provisional。
            if (
                field_name in self._HIGH_RISK_FIELDS
                and source_channel != "ai"
                and not explicit_self_marker_commit
                and not explicit_partner_marker_commit
            ):
                provisional.append(
                    AcceptedField(
                        field=field_name,
                        value=observation.value,
                        normalized_value=observation.normalized_value,
                        scope=observation.scope,
                        evidence_text=observation.evidence_text,
                        confidence=observation.confidence,
                        acceptance_reason="high_risk_non_ai_guard",
                        update_action="stage_as_provisional",
                        persistence_state="provisional",
                        risk_level=risk_level,
                        source_channel=source_channel,
                    )
                )
                continue

            threshold = self._resolve_commit_threshold(field_name)
            confidence = float(observation.confidence or 0.0)
            if field_name == "partner_requirement" and explicit_partner_marker_commit:
                threshold = min(threshold, 0.90)
            if source_channel == "ai":
                accepted.append(
                    AcceptedField(
                        field=field_name,
                        value=observation.value,
                        normalized_value=observation.normalized_value,
                        scope=observation.scope,
                        evidence_text=observation.evidence_text,
                        confidence=confidence,
                        acceptance_reason="direct_write",
                        update_action="accept_as_new",
                        persistence_state="committed",
                        risk_level=risk_level,
                        source_channel=source_channel,
                    )
                )
                continue
            accepted_value = observation.value
            accepted_normalized_value = observation.normalized_value
            accepted_evidence_text = observation.evidence_text
            if field_name == "partner_requirement" and explicit_partner_marker_commit and best_partner_requirement is not None:
                accepted_value = best_partner_requirement.value
                accepted_normalized_value = best_partner_requirement.normalized_value
                accepted_evidence_text = best_partner_requirement.evidence_text
                confidence = max(confidence, float(best_partner_requirement.confidence or 0.0))
            if confidence >= threshold:
                acceptance_reason = "direct_write"
                if explicit_self_marker_commit:
                    acceptance_reason = "explicit_self_marker"
                elif explicit_partner_marker_commit:
                    acceptance_reason = "explicit_partner_marker"
                accepted.append(
                    AcceptedField(
                        field=field_name,
                        value=accepted_value,
                        normalized_value=accepted_normalized_value,
                        scope=observation.scope,
                        evidence_text=accepted_evidence_text,
                        confidence=confidence,
                        acceptance_reason=acceptance_reason,
                        update_action="accept_as_new",
                        persistence_state="committed",
                        risk_level=risk_level,
                        source_channel=source_channel,
                    )
                )
            else:
                if field_name in self._HIGH_RISK_FIELDS or field_name in self._CORE_FIELDS:
                    pending.append(
                        PendingField(
                            field=field_name,
                            candidate_value=observation.normalized_value,
                            reason="low_confidence_high_risk",
                            scope=observation.scope,
                            confirmation_question_type="confidence_confirm",
                            persistence_state="pending_confirm",
                            risk_level=risk_level,
                            source_channel=source_channel,
                        )
                    )
                else:
                    provisional.append(
                        AcceptedField(
                            field=field_name,
                            value=observation.value,
                            normalized_value=observation.normalized_value,
                            scope=observation.scope,
                            evidence_text=observation.evidence_text,
                            confidence=confidence,
                            acceptance_reason="low_confidence_stage",
                            update_action="stage_as_provisional",
                            persistence_state="provisional",
                            risk_level=risk_level,
                            source_channel=source_channel,
                        )
                    )

        return accepted, provisional, pending, rejected

    @staticmethod
    def _validate(observation: FieldObservation) -> str | None:
        field_name = observation.field
        value = observation.normalized_value

        if field_name == "phone":
            return None if re.fullmatch(r"1\d{10}", str(value or "")) else "invalid_phone_format"
        if field_name == "wechat":
            text = str(value or "")
            return None if 5 <= len(text) <= 64 else "invalid_wechat_format"
        if field_name == "height":
            try:
                number = int(value)
            except (TypeError, ValueError):
                return "invalid_height"
            return None if 120 <= number <= 230 else "height_out_of_range"
        if field_name == "weight":
            try:
                number = int(value)
            except (TypeError, ValueError):
                return "invalid_weight"
            return None if 60 <= number <= 400 else "weight_out_of_range"
        return None

    def _resolve_risk_level(self, field_name: str) -> str:
        if field_name in self._HIGH_RISK_FIELDS:
            return "high"
        if field_name in self._CORE_FIELDS:
            return "core"
        if field_name in self._MEDIUM_FIELDS:
            return "medium"
        if field_name in self._LOW_FIELDS:
            return "low"
        return "normal"

    def _resolve_commit_threshold(self, field_name: str) -> float:
        risk_level = self._resolve_risk_level(field_name)
        if risk_level == "high":
            return self._COMMIT_THRESHOLD["high"]
        if risk_level == "core":
            return self._COMMIT_THRESHOLD["core"]
        if risk_level == "medium":
            return self._COMMIT_THRESHOLD["medium"]
        if risk_level == "low":
            return self._COMMIT_THRESHOLD["low"]
        return 0.85

    @staticmethod
    def _resolve_source_channel(*, frame: TurnSemanticFrame, observation: FieldObservation) -> str:
        frame_source = str(getattr(frame, "source", "") or "").strip()
        obs_source = str(getattr(observation, "source", "") or "").strip()
        if frame_source == "ai_structured_extraction" and (not obs_source or obs_source.startswith("ai_")):
            return "ai"
        if frame_source.startswith("legacy") or obs_source.startswith("legacy"):
            return "fallback"
        if frame_source.startswith("hybrid") or obs_source.startswith("semantic_"):
            return "hybrid"
        if frame_source == "ai_structured_extraction":
            return "ai"
        return "fallback"

    @staticmethod
    def _allows_non_ai_high_risk_commit(*, observation: FieldObservation, source_channel: str) -> bool:
        if source_channel == "ai":
            return True
        field_name = str(getattr(observation, "field", "") or "").strip()
        if field_name not in {"sex", "age", "occupation", "monthly_income"}:
            return False
        if str(getattr(observation, "scope", "") or "").strip() != "self":
            return False
        source = str(getattr(observation, "source", "") or "").strip()
        if field_name == "sex":
            if source != "semantic_explicit_self_marker":
                return False
            return str(getattr(observation, "normalized_value", "") or "").strip() in {"男", "女"}
        if field_name == "age":
            if source != "semantic_explicit_self_marker":
                return False
            normalized = str(getattr(observation, "normalized_value", "") or "").strip()
            evidence = str(getattr(observation, "evidence_text", "") or "").strip()
            if not normalized.isdigit():
                return False
            age = int(normalized)
            if age < 18 or age > 100:
                return False
            return bool(re.search(r"(\d{1,2}岁|(?:19|20)\d{2}年(?:的)?|\d{2}(?:年(?:的)?|后|的))", evidence))
        if field_name == "occupation":
            if source != "semantic_explicit_self_marker":
                return False
            return bool(str(getattr(observation, "normalized_value", "") or "").strip())
        if source not in {"semantic_deterministic", "semantic_explicit_self_marker"}:
            return False
        normalized_value = str(getattr(observation, "normalized_value", "") or "").strip()
        if not normalized_value:
            return False
        evidence = str(getattr(observation, "evidence_text", "") or "").strip()
        if source == "semantic_explicit_self_marker":
            return True
        if not evidence:
            return False
        if not re.search(r"(?:我|自己|本人)", evidence):
            return False
        return bool(re.search(r"(收入|工资|月薪|月收入|年薪|年收入|年包|一年|每年)", evidence))

    @classmethod
    def _allows_non_ai_partner_requirement_commit(
        cls,
        *,
        observation: FieldObservation,
        source_channel: str,
    ) -> bool:
        if source_channel == "ai":
            return True
        if str(getattr(observation, "scope", "") or "").strip() != "partner":
            return False
        source = str(getattr(observation, "source", "") or "").strip()
        if not (
            source.startswith("semantic_")
            or source.startswith("legacy_")
            or source in {"governance", "test_stub"}
        ):
            return False
        confidence = float(getattr(observation, "confidence", 0.0) or 0.0)
        if confidence < 0.90:
            return False
        normalized_value = str(getattr(observation, "normalized_value", "") or "").strip()
        if not normalized_value or normalized_value in cls._WEAK_PARTNER_REQUIREMENT_VALUES:
            return False
        compact_value = re.sub(r"\s+", "", normalized_value)
        if re.fullmatch(r"(找)?(?:男(?:生|朋友)?|女(?:生|朋友)?)", compact_value):
            return False
        evidence = str(getattr(observation, "evidence_text", "") or "").strip()
        compact_evidence = re.sub(r"\s+", "", evidence)
        return bool(
            re.search(r"(喜欢|想找|找(?:男朋友|女朋友|对象|另一半|[男女]生)|希望对方|看重|最好|起码|至少|优先|不要)", compact_evidence)
            or re.search(r"(身高|学历|收入|工作稳定|成熟稳重|多金|90后|80后|年纪|年龄|\d{2,3}\+)", compact_evidence)
        )

    @staticmethod
    def _resolve_best_partner_requirement_observation(*, frame: TurnSemanticFrame) -> FieldObservation | None:
        best: FieldObservation | None = None
        best_score: tuple[int, int, int, int, float] = (-1, -1, -1, -1, -1.0)
        for observation in list(getattr(frame, "field_observations", []) or []):
            if str(getattr(observation, "field", "") or "").strip() != "partner_requirement":
                continue
            scope = str(getattr(observation, "scope", "") or "").strip()
            if scope not in {"partner", "mixed"}:
                continue
            value_text = str(getattr(observation, "normalized_value", "") or "").strip()
            if not value_text:
                continue
            source = str(getattr(observation, "source", "") or "").strip()
            source_rank = 0
            if source == "semantic_chunk_partner_requirement":
                source_rank = 4
            elif source.startswith("ai_"):
                source_rank = 3
            elif source == "semantic_chunk_partner_preference":
                source_rank = 2
            elif source.startswith("semantic_"):
                source_rank = 1
            subslot_count = len(ExtractionService._extract_partner_preference_subslots(value_text))  # noqa: SLF001
            noise_free = 0 if FieldAcceptanceService._SELF_PROFILE_NOISE_IN_PARTNER_REQUIREMENT_RE.search(value_text) else 1
            score = (
                noise_free,
                subslot_count,
                len(value_text),
                source_rank,
                float(getattr(observation, "confidence", 0.0) or 0.0),
            )
            if score > best_score:
                best = observation
                best_score = score
        return best
