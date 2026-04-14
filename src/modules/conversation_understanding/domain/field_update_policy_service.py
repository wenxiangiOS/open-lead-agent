from __future__ import annotations

from src.modules.conversation_understanding.domain.models import AcceptedField, PendingField, TurnSemanticFrame


class FieldUpdatePolicyService:
    """Resolve accepted fields against the current profile without re-reading the raw message."""

    _STABLE_FIELDS = {"sex", "age", "birth_year", "location", "education", "occupation", "marital_status", "monthly_income"}
    _HIGH_RISK_FIELDS = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}

    def resolve_updates(
        self,
        *,
        frame: TurnSemanticFrame,
        accepted_fields: list[AcceptedField],
        provisional_fields: list[AcceptedField],
        pending_fields: list[PendingField],
        user_profile: object,
    ) -> tuple[list[AcceptedField], list[AcceptedField], list[PendingField], int | None, str | None]:
        resolved_accepted: list[AcceptedField] = []
        resolved_provisional: list[AcceptedField] = []
        resolved_pending = list(pending_fields)
        expected_profile_version = self._resolve_profile_version(user_profile)
        expected_profile_updated_at = self._resolve_profile_updated_at(user_profile)

        for field in accepted_fields:
            current_value = getattr(user_profile, field.field, None) if user_profile is not None else None
            action = self._resolve_action(field=field, current_value=current_value, frame=frame)
            if action == "hold_for_confirmation":
                resolved_pending.append(
                    PendingField(
                        field=field.field,
                        candidate_value=field.normalized_value,
                        reason="conflict_with_existing_value",
                        scope=field.scope,
                        confirmation_question_type="conflict_confirm",
                        persistence_state="pending_confirm",
                        risk_level=str(getattr(field, "risk_level", "normal") or "normal"),
                        source_channel=str(getattr(field, "source_channel", "unknown") or "unknown"),
                    )
                )
                continue

            field_version = self._resolve_next_field_version(field.field, user_profile)
            resolved_accepted.append(
                AcceptedField(
                    field=field.field,
                    value=field.value,
                    normalized_value=field.normalized_value,
                    scope=field.scope,
                    evidence_text=field.evidence_text,
                    confidence=field.confidence,
                    acceptance_reason=field.acceptance_reason,
                    update_action=action,
                    persistence_state="committed",
                    risk_level=str(getattr(field, "risk_level", "normal") or "normal"),
                    source_channel=str(getattr(field, "source_channel", "unknown") or "unknown"),
                    field_version=field_version,
                    expected_profile_version=expected_profile_version,
                    expected_profile_updated_at=expected_profile_updated_at,
                )
            )

        for field in provisional_fields:
            current_value = getattr(user_profile, field.field, None) if user_profile is not None else None
            has_conflict = self._has_value_conflict(current_value=current_value, candidate=field.normalized_value)
            if has_conflict and field.field in self._HIGH_RISK_FIELDS:
                resolved_pending.append(
                    PendingField(
                        field=field.field,
                        candidate_value=field.normalized_value,
                        reason="high_risk_provisional_conflict",
                        scope=field.scope,
                        confirmation_question_type="conflict_confirm",
                        persistence_state="pending_confirm",
                        risk_level=str(getattr(field, "risk_level", "high") or "high"),
                        source_channel=str(getattr(field, "source_channel", "unknown") or "unknown"),
                    )
                )
                continue
            resolved_provisional.append(
                AcceptedField(
                    field=field.field,
                    value=field.value,
                    normalized_value=field.normalized_value,
                    scope=field.scope,
                    evidence_text=field.evidence_text,
                    confidence=field.confidence,
                    acceptance_reason=field.acceptance_reason,
                    update_action="stage_as_provisional",
                    persistence_state="provisional",
                    risk_level=str(getattr(field, "risk_level", "normal") or "normal"),
                    source_channel=str(getattr(field, "source_channel", "unknown") or "unknown"),
                    field_version=self._resolve_next_field_version(field.field, user_profile),
                    expected_profile_version=expected_profile_version,
                    expected_profile_updated_at=expected_profile_updated_at,
                )
            )

        return (
            resolved_accepted,
            resolved_provisional,
            resolved_pending,
            expected_profile_version,
            expected_profile_updated_at,
        )

    @staticmethod
    def _resolve_profile_version(user_profile: object | None) -> int | None:
        if user_profile is None:
            return None
        raw = getattr(user_profile, "profile_version", None)
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _resolve_action(self, *, field: AcceptedField, current_value: object, frame: TurnSemanticFrame) -> str:
        if current_value in (None, "", [], {}, ()):
            return "accept_as_new"

        current_text = str(current_value).strip()
        new_text = str(field.normalized_value).strip()
        if not current_text or current_text == new_text:
            return "accept_as_new"

        if field.field == "location":
            if current_text in new_text and current_text != new_text:
                return "accept_as_refinement"
            if new_text in current_text and current_text != new_text:
                return "accept_as_refinement"

        if field.field == "occupation":
            if current_text in new_text and current_text != new_text:
                return "accept_as_refinement"

        if field.field == "marital_status":
            # 语义同桶视为一致，避免“未婚单身 vs 单身”被误判冲突后反复确认。
            current_bucket = self._normalize_marital_status_bucket(current_text)
            new_bucket = self._normalize_marital_status_bucket(new_text)
            if current_bucket and new_bucket and current_bucket == new_bucket:
                return "accept_as_refinement"

        if field.field in self._STABLE_FIELDS:
            if "correct_profile" in (frame.acts or []):
                return "replace_existing"
            return "hold_for_confirmation"

        return "replace_existing"

    @staticmethod
    def _normalize_marital_status_bucket(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if "离异" in text:
            return "divorced"
        if "已婚" in text or "结婚" in text:
            return "married"
        if "未婚" in text or "单身" in text:
            return "single"
        if "分居" in text:
            return "separated"
        return text

    @staticmethod
    def _resolve_profile_updated_at(user_profile: object | None) -> str | None:
        updated_at = getattr(user_profile, "updated_at", None) if user_profile is not None else None
        if updated_at is None:
            return None
        if hasattr(updated_at, "isoformat"):
            return str(updated_at.isoformat())
        return str(updated_at)

    @staticmethod
    def _resolve_next_field_version(field_name: str, user_profile: object | None) -> int:
        if user_profile is None:
            return 1
        evidence = dict(getattr(user_profile, "extraction_evidence", {}) or {}).get(field_name) or {}
        try:
            current_version = int(evidence.get("field_version", 0) or 0)
        except (TypeError, ValueError):
            current_version = 0
        return max(1, current_version + 1)

    @staticmethod
    def _has_value_conflict(*, current_value: object, candidate: object) -> bool:
        current_text = str(current_value).strip() if current_value not in (None, "", [], {}, ()) else ""
        candidate_text = str(candidate).strip() if candidate not in (None, "", [], {}, ()) else ""
        if not current_text or not candidate_text:
            return False
        return current_text != candidate_text
