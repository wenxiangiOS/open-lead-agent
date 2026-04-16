from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Iterable

from src.core.exceptions import AIServiceException
from src.modules.conversation.domain.turn_understanding_models import (
    ResolvedFieldEvidence,
    SlotCandidate,
    TurnUnderstandingResult,
)
from src.modules.conversation_understanding.domain.models import (
    FieldObservation,
    TurnInputSnapshot,
    TurnSemanticFrame,
    UserQuestion,
)

logger = logging.getLogger(__name__)


class AISemanticExtractionService:
    """Build the primary semantic frame used by the unified pipeline.

    During the current migration stage this service still combines direct
    semantic observations from the message with legacy fallback signals. The
    target end state remains a pure AI-first structured extractor.
    """

    _QUESTION_TOPIC_PATTERNS: tuple[tuple[str, str], ...] = (
        ("pricing", r"(怎么收费|收费|多少钱|价格|费用)"),
        ("service_flow", r"(怎么安排|流程|怎么操作|怎么弄)"),
        ("safety", r"(靠谱吗|安全|真实吗|正规吗)"),
        ("contact_policy", r"(怎么联系|能不能直接联系|联系方式)"),
    )
    _COMPACT_INTRO_FILLER_PATTERN = r"(?:可以(?:啊|呀|哒)?|好(?:呀|的)?|嗯(?:嗯)?|你好|嗨)"
    _SUPPORTED_EXTRACTION_FIELDS: tuple[str, ...] = (
        "sex",
        "age",
        "age_label",
        "location",
        "education",
        "occupation",
        "marital_status",
        "monthly_income",
        "phone",
        "wechat",
        "partner_gender_preference",
        "partner_requirement",
        "partner_pref_age",
        "partner_pref_location",
        "partner_pref_education",
        "partner_pref_industry",
        "partner_pref_personality",
        "partner_pref_income",
        "partner_pref_other",
        "partner_pref_height",
        "partner_pref_age_relation",
        "partner_pref_locality",
    )
    _TRANSPORT_FAILURE_MARKERS: tuple[str, ...] = (
        "超时",
        "timeout",
        "timed out",
        "connection error",
        "connecterror",
        "readerror",
        "read error",
        "apiconnectionerror",
        "nodename nor servname provided",
        "temporary failure in name resolution",
    )
    _SYNC_AI_CIRCUIT_BREAKER_STATE: dict[str, float | int] = {
        "consecutive_transport_failures": 0,
        "open_until_monotonic": 0.0,
    }

    def __init__(self, semantic_service: object | None = None, ai_service: object | None = None) -> None:
        self.semantic_service = semantic_service
        self.ai_service = ai_service

    async def extract(
        self,
        *,
        snapshot: TurnInputSnapshot,
        fallback_result: TurnUnderstandingResult,
        enable_ai: bool = False,
        ai_timeout_seconds: float | None = None,
        enforce_mainline_blocking_cap: bool = False,
    ) -> TurnSemanticFrame:
        if not enable_ai:
            frame = self._project_from_fallback(snapshot=snapshot, fallback_result=fallback_result)
            frame = self._merge_direct_evidence_into_frame(
                frame=frame,
                snapshot=snapshot,
            )
            self._attach_chunk_summary_notes(frame, snapshot.user_message)
            return frame
        skip_status = self._current_sync_ai_skip_status()
        if skip_status is not None:
            logger.info(
                "[unified_understanding.ai_semantic_extraction] skipped: status=%s message_chars=%s",
                skip_status,
                len(str(snapshot.user_message or "")),
            )
            frame = self._project_from_fallback(snapshot=snapshot, fallback_result=fallback_result)
            frame = self._merge_direct_evidence_into_frame(
                frame=frame,
                snapshot=snapshot,
            )
            frame.notes.append(f"ai_semantic_status=skipped:{skip_status}")
            self._attach_chunk_summary_notes(frame, snapshot.user_message)
            return frame
        ai_frame, ai_status = await self._extract_via_ai(
            snapshot=snapshot,
            fallback_result=fallback_result,
            ai_timeout_seconds=ai_timeout_seconds,
            enforce_mainline_blocking_cap=enforce_mainline_blocking_cap,
        )
        if ai_frame is not None:
            ai_frame = self._merge_fallback_projection_into_ai_frame(
                frame=ai_frame,
                snapshot=snapshot,
                fallback_result=fallback_result,
            )
            ai_frame = self._merge_direct_evidence_into_frame(
                frame=ai_frame,
                snapshot=snapshot,
            )
            self._attach_chunk_summary_notes(ai_frame, snapshot.user_message)
            return ai_frame
        fallback_frame = self._project_from_fallback(snapshot=snapshot, fallback_result=fallback_result)
        fallback_frame = self._merge_direct_evidence_into_frame(
            frame=fallback_frame,
            snapshot=snapshot,
        )
        if ai_status:
            fallback_frame.notes.append(f"ai_semantic_status={ai_status}")
        self._attach_chunk_summary_notes(fallback_frame, snapshot.user_message)
        return fallback_frame

    def _merge_direct_evidence_into_frame(
        self,
        *,
        frame: TurnSemanticFrame,
        snapshot: TurnInputSnapshot,
    ) -> TurnSemanticFrame:
        merged_observations = list(getattr(frame, "field_observations", []) or [])
        direct_observations = self._extract_direct_observations(snapshot)
        if direct_observations and str(getattr(frame, "source", "") or "").strip() == "ai_structured_extraction":
            seen = {
                (str(getattr(item, "field", "") or "").strip(), str(getattr(item, "normalized_value", "") or ""), str(getattr(item, "scope", "") or "").strip())
                for item in merged_observations
            }
            for observation in direct_observations:
                self._append_observation(merged_observations, seen, observation)
        merged_observations = self._arbitrate_evidence_first_observations(merged_observations)
        notes = list(getattr(frame, "notes", []) or [])
        if not any(str(note).startswith("evidence_merge=") for note in notes):
            notes.append(f"evidence_merge=direct:{len(direct_observations)}")
        frame.field_observations = merged_observations
        frame.notes = notes
        return frame

    def _merge_fallback_projection_into_ai_frame(
        self,
        *,
        frame: TurnSemanticFrame,
        snapshot: TurnInputSnapshot,
        fallback_result: TurnUnderstandingResult,
    ) -> TurnSemanticFrame:
        if str(getattr(frame, "source", "") or "").strip() != "ai_structured_extraction":
            return frame

        merged_observations = list(getattr(frame, "field_observations", []) or [])
        ai_field_scope_pairs = {
            (
                str(getattr(item, "field", "") or "").strip(),
                str(getattr(item, "scope", "") or "").strip(),
            )
            for item in merged_observations
            if str(getattr(item, "field", "") or "").strip()
        }
        seen = {
            (
                str(getattr(item, "field", "") or "").strip(),
                str(getattr(item, "normalized_value", "") or ""),
                str(getattr(item, "scope", "") or "").strip(),
            )
            for item in merged_observations
        }
        supplemented = 0
        refinement_candidates = 0
        fallback_observations = self._collect_observations(snapshot, fallback_result)
        for observation in fallback_observations:
            field_name = str(getattr(observation, "field", "") or "").strip()
            scope = str(getattr(observation, "scope", "") or "").strip()
            if not field_name:
                continue
            has_same_field_scope = (field_name, scope) in ai_field_scope_pairs
            if has_same_field_scope:
                if not self._should_include_fallback_same_field_in_ai_arbitration(
                    observation=observation,
                    existing_observations=merged_observations,
                ):
                    continue
                refinement_candidates += 1
            before_count = len(merged_observations)
            self._append_observation(merged_observations, seen, observation)
            if len(merged_observations) > before_count:
                supplemented += 1

        if supplemented <= 0 and refinement_candidates <= 0:
            return frame
        notes = list(getattr(frame, "notes", []) or [])
        if not any(str(note).startswith("fallback_projection_merge=") for note in notes):
            notes.append(f"fallback_projection_merge=added:{supplemented}")
        if refinement_candidates > 0 and not any(str(note).startswith("fallback_projection_refinement=") for note in notes):
            notes.append(f"fallback_projection_refinement=candidates:{refinement_candidates}")
        frame.field_observations = merged_observations
        frame.notes = notes
        return frame

    def _should_include_fallback_same_field_in_ai_arbitration(
        self,
        *,
        observation: FieldObservation,
        existing_observations: list[FieldObservation],
    ) -> bool:
        field_name = str(getattr(observation, "field", "") or "").strip()
        scope = str(getattr(observation, "scope", "") or "").strip()
        candidate_value = str(getattr(observation, "normalized_value", "") or "").strip()
        if not field_name or not scope or not candidate_value:
            return False

        competing = [
            item
            for item in existing_observations
            if str(getattr(item, "field", "") or "").strip() == field_name
            and str(getattr(item, "scope", "") or "").strip() == scope
        ]
        if not competing:
            return False

        for current in competing:
            current_value = str(getattr(current, "normalized_value", "") or "").strip()
            if not current_value or current_value == candidate_value:
                continue
            if self._is_refinement_observation(
                field_name=field_name,
                candidate=observation,
                baseline=current,
            ):
                return True
            if field_name == "partner_requirement":
                richer = self._pick_richer_partner_requirement(current_value, candidate_value)
                if richer == candidate_value and richer != current_value:
                    return True
            if self._is_authoritative_direct_observation(observation) and self._observation_priority(observation) > self._observation_priority(current):
                return True

        return False

    def _project_from_fallback(
        self,
        *,
        snapshot: TurnInputSnapshot,
        fallback_result: TurnUnderstandingResult,
    ) -> TurnSemanticFrame:
        observations = self._collect_observations(snapshot, fallback_result)
        direct_count = sum(1 for item in observations if item.source.startswith("semantic_"))
        return TurnSemanticFrame(
            version="v1",
            source="hybrid_semantic_projection" if direct_count else "legacy_projection",
            primary_domain=self._resolve_primary_domain(fallback_result),
            acts=self._build_acts(fallback_result, observations),
            user_questions=self._extract_user_questions(snapshot.user_message),
            field_observations=observations,
            risk_flags=list(fallback_result.risk_flags or []),
            boundaries=self._build_boundaries(fallback_result),
            notes=[
                f"projected_from={fallback_result.primary_turn_type}/{fallback_result.subtype or '-'}",
                f"direct_observations={direct_count}",
            ],
            confidence=float(fallback_result.confidence or 0.0),
        )

    async def _extract_via_ai(
        self,
        *,
        snapshot: TurnInputSnapshot,
        fallback_result: TurnUnderstandingResult,
        ai_timeout_seconds: float | None = None,
        enforce_mainline_blocking_cap: bool = False,
    ) -> tuple[TurnSemanticFrame | None, str]:
        if self.ai_service is None:
            return None, "disabled:no_ai_service"

        asked_fields = sorted(self._extract_prompt_asked_fields(snapshot.prompt_state or {}))
        system_prompt, prompt = self._build_extraction_prompt(
            user_message=snapshot.user_message,
            asked_fields=asked_fields,
        )

        attempts = self._build_ai_attempt_plan(
            ai_timeout_seconds,
            enforce_blocking_cap=enforce_mainline_blocking_cap,
        )
        last_error: AIServiceException | None = None
        last_failure_stage = "unknown"
        for index, attempt in enumerate(attempts, start=1):
            timeout = float(attempt.get("timeout") or 0.0)
            model_name = str(attempt.get("model_name") or "").strip() or None
            max_tokens = self._resolve_ai_max_tokens()
            reasoning_effort = self._resolve_ai_reasoning_effort()
            temperature = self._resolve_ai_temperature()
            logger.info(
                "[unified_understanding.ai_semantic_extraction] request: attempt=%s/%s timeout=%.1fs model=%s max_tokens=%s reasoning_effort=%s temperature=%.2f prompt_chars=%s system_chars=%s asked_fields=%s",
                index,
                len(attempts),
                timeout,
                model_name or "-",
                max_tokens,
                reasoning_effort or "-",
                temperature,
                len(prompt),
                len(system_prompt),
                ",".join(asked_fields) if asked_fields else "-",
            )
            try:
                raw = await self.ai_service.generate_response(
                    prompt,
                    system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    model_name=model_name,
                    disable_retry=True,
                    use_max_completion_tokens=False,
                    reasoning_effort=reasoning_effort,
                )
            except AIServiceException as exc:
                last_error = exc
                last_failure_stage = "request_failed"
                if self._is_transport_failure(exc):
                    self._record_transport_failure(exc)
                else:
                    self._reset_transport_failure_streak(reason="non_transport_error")
                logger.warning(
                    "[unified_understanding.ai_semantic_extraction] failed: attempt=%s/%s timeout=%.1fs model=%s max_tokens=%s reasoning_effort=%s temperature=%.2f error=%s",
                    index,
                    len(attempts),
                    timeout,
                    model_name or "-",
                    max_tokens,
                    reasoning_effort or "-",
                    temperature,
                    exc,
                )
                continue

            frame, parse_stage, parse_detail = self._parse_ai_frame(raw)
            last_failure_stage = parse_stage
            if frame is not None and not list(getattr(frame, "field_observations", []) or []):
                logger.warning(
                    "[unified_understanding.ai_semantic_extraction] empty_observations: attempt=%s/%s timeout=%.1fs model=%s parse_stage=%s detail=%s raw_preview=%r",
                    index,
                    len(attempts),
                    timeout,
                    model_name or "-",
                    parse_stage,
                    parse_detail,
                    self._build_preview(raw),
                )
                last_failure_stage = "empty_observations"
                frame = None
            if frame is None:
                logger.warning(
                    "[unified_understanding.ai_semantic_extraction] invalid_frame: attempt=%s/%s timeout=%.1fs model=%s max_tokens=%s reasoning_effort=%s temperature=%.2f parse_stage=%s detail=%s raw_preview=%r",
                    index,
                    len(attempts),
                    timeout,
                    model_name or "-",
                    max_tokens,
                    reasoning_effort or "-",
                    temperature,
                    parse_stage,
                    parse_detail,
                    self._build_preview(raw),
                )
                self._reset_transport_failure_streak(reason=f"parse_failure:{parse_stage or '-'}")
                continue
            self._reset_transport_failure_streak(reason="ai_success")
            logger.info(
                "[unified_understanding.ai_semantic_extraction] parsed_frame: attempt=%s/%s model=%s parse_stage=%s observations=%s primary_domain=%s",
                index,
                len(attempts),
                model_name or "-",
                parse_stage,
                len(list(getattr(frame, "field_observations", []) or [])),
                getattr(frame, "primary_domain", "") or "-",
            )
            if parse_stage:
                frame.notes.append(f"ai_semantic_status=success:{parse_stage}")
            if index > 1:
                logger.info(
                    "[unified_understanding.ai_semantic_extraction] recovered_on_retry: attempt=%s/%s timeout=%.1fs model=%s",
                    index,
                    len(attempts),
                    timeout,
                    model_name or "-",
                )
            return frame, f"success:{parse_stage}"

        if last_error is not None:
            logger.warning(
                "[unified_understanding.ai_semantic_extraction] all_attempts_failed: attempts=%s last_error=%s",
                len(attempts),
                last_error,
            )
        logger.warning(
            "[unified_understanding.ai_semantic_extraction] fallback_to_projection: attempts=%s final_stage=%s fallback_source=%s/%s",
            len(attempts),
            last_failure_stage,
            fallback_result.primary_turn_type,
            fallback_result.subtype or "-",
        )
        if last_error is not None:
            return None, f"failed:{last_failure_stage}"
        return None, f"failed:{last_failure_stage}"

    def _parse_ai_frame(self, raw: str) -> tuple[TurnSemanticFrame | None, str, str]:
        text = str(raw or "").strip()
        if not text:
            return None, "empty_response", "raw_empty"

        parsed = self._parse_json_payload(text)
        if isinstance(parsed, dict):
            frame = self._build_frame_from_ai_payload(parsed)
            if frame is not None:
                return frame, "json_frame", self._describe_payload_keys(parsed)
            frame = self._build_frame_from_slim_payload(parsed)
            if frame is not None:
                return frame, "slim_json_frame", self._describe_payload_keys(parsed)
            return None, "json_schema_invalid", self._describe_payload_keys(parsed)

        compact_payload = self._parse_compact_line_payload(text)
        frame = self._build_frame_from_compact_payload(compact_payload)
        if frame is not None:
            return frame, "compact_line_frame", "parsed_via_compact_lines"

        salvaged_payload = self._build_salvaged_payload_from_json_like_text(text)
        if salvaged_payload is not None:
            frame = self._build_frame_from_slim_payload(salvaged_payload)
            if frame is not None:
                return frame, "json_like_recovered", self._describe_payload_keys(salvaged_payload)

        if "{" in text or "[" in text:
            return None, "malformed_json", "json_like_but_unparseable"
        return None, "non_json_output", "no_json_object_detected"

    def _build_extraction_prompt(self, *, user_message: str, asked_fields: list[str]) -> tuple[str, str]:
        supported = ",".join(self._SUPPORTED_EXTRACTION_FIELDS)
        system_prompt = (
            "你是信息抽取器。只输出一行 JSON，不要解释，不要 markdown，不要补充说明。"
            '固定格式：{"primary_domain":"profile|mixed|contact|faq|boundary|risk|closing","items":[{"field":"","scope":"self|partner|contact","value":""}]}。'
            f"field 只能从以下枚举中选：{supported}。"
            "不要输出 birthYear、currentLocation、industry 这类别名；要改写成枚举字段。"
            "同一句同时含自我信息、择偶要求、联系方式时，primary_domain 必须是 mixed。"
            "未知字段不要输出，最多输出 12 个 items。"
        )
        prompt = (
            f"用户原话：{user_message or '-'}\n"
            f"最近追问字段：{','.join(asked_fields) if asked_fields else '-'}\n"
            '示例：{"primary_domain":"mixed","items":[{"field":"location","scope":"self","value":"深圳南山"},{"field":"partner_requirement","scope":"partner","value":"90后，在深圳发展"},{"field":"wechat","scope":"contact","value":"abc12345"}]}'
        )
        return system_prompt, prompt

    @staticmethod
    def _describe_payload_keys(payload: dict[str, Any]) -> str:
        keys = sorted(str(key).strip() for key in payload.keys() if str(key).strip())
        if not keys:
            return "keys=-"
        return f"keys={','.join(keys[:8])}"

    def _build_salvaged_payload_from_json_like_text(self, raw: str) -> dict[str, Any] | None:
        text = str(raw or "").strip()
        if not text or "{" not in text:
            return None

        section_pattern = re.compile(r'"(?P<section>userInfo|user_info|profile|partnerPreference|partner_preference|择偶偏好|contactInfo|contact)"\s*:\s*\{')
        pair_pattern = re.compile(
            r'"(?P<key>[A-Za-z0-9_\-\u4e00-\u9fa5]+)"\s*:\s*(?P<value>"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?)'
        )

        events: list[tuple[int, str, str]] = []
        for match in section_pattern.finditer(text):
            events.append((match.start(), "section", str(match.group("section") or "").strip()))
        for match in pair_pattern.finditer(text):
            events.append((match.start(), "pair", match.group(0)))
        if not events:
            return None

        events.sort(key=lambda item: item[0])
        current_scope = "mixed"
        items: list[dict[str, Any]] = []
        primary_domain = ""
        seen: set[tuple[str, str, str]] = set()

        for _, kind, payload in events:
            if kind == "section":
                section = payload
                if section in {"userInfo", "user_info", "profile"}:
                    current_scope = "self"
                elif section in {"partnerPreference", "partner_preference", "择偶偏好"}:
                    current_scope = "partner"
                elif section in {"contactInfo", "contact"}:
                    current_scope = "contact"
                continue

            match = pair_pattern.match(payload)
            if not match:
                continue
            key = str(match.group("key") or "").strip()
            value_literal = str(match.group("value") or "").strip()
            if key == "primary_domain":
                primary_domain = value_literal.strip('"').strip()
                continue
            if key in {"items", "acts", "user_questions", "risk_flags", "boundaries", "notes", "confidence"}:
                continue

            try:
                value = json.loads(value_literal)
            except json.JSONDecodeError:
                value = value_literal.strip('"')
            if value in (None, "", [], {}):
                continue
            dedupe_key = (current_scope, key, str(value))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append(
                {
                    "field": key,
                    "scope": current_scope,
                    "value": value,
                    "write_mode": "direct_write",
                    "confidence": 0.86,
                }
            )

        if not items:
            return None
        return {"primary_domain": primary_domain, "items": items}

    @staticmethod
    def _build_preview(raw: str, limit: int = 160) -> str:
        text = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not text:
            return ""
        text = re.sub(r"\d{7,}", "<digits>", text)
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."

    def _collect_observations(
        self,
        snapshot: TurnInputSnapshot,
        result: TurnUnderstandingResult,
    ) -> list[FieldObservation]:
        observations: list[FieldObservation] = []
        seen: set[tuple[str, str, str]] = set()
        allow_self_from_legacy = self._allows_self_projection_from_legacy(
            message=snapshot.user_message,
            result=result,
        )

        for obs in self._extract_direct_observations(snapshot):
            self._append_observation(observations, seen, obs)

        for field, evidence in (result.resolved_field_evidence or {}).items():
            obs = self._from_evidence(field, evidence)
            if not allow_self_from_legacy and obs.scope == "self":
                continue
            self._append_observation(observations, seen, obs)

        for field, value in (result.resolved_slots or {}).items():
            scope = self._infer_scope(field)
            if not allow_self_from_legacy and scope == "self":
                continue
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=field,
                    value=value,
                    normalized_value=value,
                    scope=scope,
                    owner="self" if scope in {"self", "contact"} else scope,
                    evidence_text=str(value),
                    evidence_span=str(value),
                    confidence=0.9,
                    write_mode="direct_write",
                    source="legacy_resolved_slot",
                )
            )

        for field, candidate in (result.slot_candidates or {}).items():
            observation = self._from_candidate(field, candidate)
            if not allow_self_from_legacy and observation.scope == "self":
                continue
            self._append_observation(observations, seen, observation)

        return observations

    def _arbitrate_evidence_first_observations(
        self,
        observations: list[FieldObservation],
    ) -> list[FieldObservation]:
        curated = list(observations or [])
        curated = self._arbitrate_single_value_field(curated, "sex")
        curated = self._arbitrate_single_value_field(curated, "age_label")
        curated = self._arbitrate_age_from_authoritative_label(curated)
        curated = self._arbitrate_single_value_field(curated, "age")
        curated = self._arbitrate_single_value_field(curated, "location")
        curated = self._arbitrate_single_value_field(curated, "education")
        curated = self._arbitrate_single_value_field(curated, "occupation")
        curated = self._arbitrate_single_value_field(curated, "marital_status")
        curated = self._arbitrate_single_value_field(curated, "monthly_income")
        curated = self._arbitrate_single_value_field(curated, "partner_gender_preference")
        curated = self._arbitrate_single_value_field(curated, "wechat")
        curated = self._arbitrate_single_value_field(curated, "phone")
        curated = self._arbitrate_contact_channel_conflicts(curated)
        return self._dedupe_observations_preserving_order(curated)

    def _arbitrate_single_value_field(
        self,
        observations: list[FieldObservation],
        field_name: str,
    ) -> list[FieldObservation]:
        candidates = [
            observation
            for observation in observations
            if str(getattr(observation, "field", "") or "").strip() == field_name
        ]
        if len(candidates) <= 1:
            return observations

        best = candidates[0]
        for candidate in candidates[1:]:
            best = self._pick_preferred_single_value_observation(
                field_name=field_name,
                current=best,
                candidate=candidate,
            )
        resolved: list[FieldObservation] = []
        inserted = False
        for observation in observations:
            if str(getattr(observation, "field", "") or "").strip() != field_name:
                resolved.append(observation)
                continue
            if not inserted:
                resolved.append(best)
                inserted = True
        return resolved

    def _arbitrate_age_from_authoritative_label(
        self,
        observations: list[FieldObservation],
    ) -> list[FieldObservation]:
        age_label_observation = next(
            (
                observation
                for observation in observations
                if str(getattr(observation, "field", "") or "").strip() == "age_label"
                and str(getattr(observation, "scope", "") or "").strip() == "self"
            ),
            None,
        )
        if age_label_observation is None:
            return observations

        derived_age = self._derive_precise_age_from_label(
            str(getattr(age_label_observation, "normalized_value", "") or "").strip()
        )
        if derived_age is None:
            return observations

        derived_observation = FieldObservation(
            field="age",
            value=str(derived_age),
            normalized_value=str(derived_age),
            scope="self",
            owner="self",
            evidence_text=str(getattr(age_label_observation, "evidence_text", "") or "").strip()
            or str(getattr(age_label_observation, "normalized_value", "") or "").strip(),
            evidence_span=str(getattr(age_label_observation, "evidence_span", "") or "").strip()
            or str(getattr(age_label_observation, "normalized_value", "") or "").strip(),
            confidence=max(0.98, float(getattr(age_label_observation, "confidence", 0.0) or 0.0)),
            write_mode=str(getattr(age_label_observation, "write_mode", "") or "direct_write").strip() or "direct_write",
            source="semantic_age_label_derived",
            raw_value=str(getattr(age_label_observation, "normalized_value", "") or "").strip(),
        )

        resolved: list[FieldObservation] = []
        inserted_age = False
        for observation in observations:
            field_name = str(getattr(observation, "field", "") or "").strip()
            scope = str(getattr(observation, "scope", "") or "").strip()
            if field_name == "age" and scope == "self":
                if not inserted_age:
                    resolved.append(derived_observation)
                    inserted_age = True
                continue
            resolved.append(observation)
            if (
                field_name == "age_label"
                and scope == "self"
                and not inserted_age
            ):
                resolved.append(derived_observation)
                inserted_age = True
        if not inserted_age:
            resolved.append(derived_observation)
        return resolved

    def _arbitrate_contact_channel_conflicts(
        self,
        observations: list[FieldObservation],
    ) -> list[FieldObservation]:
        best_wechat = self._find_best_field_observation(observations, "wechat")
        best_phone = self._find_best_field_observation(observations, "phone")
        if best_wechat is None or best_phone is None:
            return observations

        wechat_value = str(getattr(best_wechat, "normalized_value", "") or "").strip()
        phone_value = str(getattr(best_phone, "normalized_value", "") or "").strip()
        if not wechat_value or wechat_value != phone_value:
            return observations

        if self._is_authoritative_direct_observation(best_wechat) and self._is_ai_observation(best_phone):
            return [
                observation
                for observation in observations
                if not (
                    str(getattr(observation, "field", "") or "").strip() == "phone"
                    and str(getattr(observation, "normalized_value", "") or "").strip() == phone_value
                )
            ]
        if self._is_authoritative_direct_observation(best_phone) and self._is_ai_observation(best_wechat):
            return [
                observation
                for observation in observations
                if not (
                    str(getattr(observation, "field", "") or "").strip() == "wechat"
                    and str(getattr(observation, "normalized_value", "") or "").strip() == wechat_value
                )
            ]
        return observations

    def _find_best_field_observation(
        self,
        observations: list[FieldObservation],
        field_name: str,
    ) -> FieldObservation | None:
        candidates = [
            observation
            for observation in observations
            if str(getattr(observation, "field", "") or "").strip() == field_name
        ]
        if not candidates:
            return None
        return max(candidates, key=self._observation_priority)

    def _pick_preferred_single_value_observation(
        self,
        *,
        field_name: str,
        current: FieldObservation,
        candidate: FieldObservation,
    ) -> FieldObservation:
        candidate_refines_current = self._is_refinement_observation(
            field_name=field_name,
            candidate=candidate,
            baseline=current,
        )
        current_refines_candidate = self._is_refinement_observation(
            field_name=field_name,
            candidate=current,
            baseline=candidate,
        )
        if candidate_refines_current and not current_refines_candidate:
            return candidate
        if current_refines_candidate and not candidate_refines_current:
            return current
        return candidate if self._observation_priority(candidate) > self._observation_priority(current) else current

    def _is_refinement_observation(
        self,
        *,
        field_name: str,
        candidate: FieldObservation,
        baseline: FieldObservation,
    ) -> bool:
        candidate_value = str(getattr(candidate, "normalized_value", "") or "").strip()
        baseline_value = str(getattr(baseline, "normalized_value", "") or "").strip()
        if not candidate_value or not baseline_value or candidate_value == baseline_value:
            return False
        if field_name == "location":
            return baseline_value in candidate_value and len(candidate_value) > len(baseline_value)
        if field_name == "occupation":
            return self._is_occupation_refinement(candidate_value, baseline_value)
        if field_name == "education":
            return self._is_education_refinement(candidate_value, baseline_value)
        if field_name == "age_label":
            return self._is_age_label_refinement(candidate_value, baseline_value)
        return False

    @staticmethod
    def _is_occupation_refinement(candidate_value: str, baseline_value: str) -> bool:
        candidate = str(candidate_value or "").strip()
        baseline = str(baseline_value or "").strip()
        if not candidate or not baseline or candidate == baseline:
            return False
        if baseline not in candidate or len(candidate) <= len(baseline):
            return False
        if re.search(r"(?:行业|(?:行业)?工作)$", candidate):
            return False
        return True

    @staticmethod
    def _education_bucket(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if "博士" in text:
            return "博士"
        if any(token in text for token in ("硕", "研究生")):
            return "硕士"
        if any(token in text for token in ("本",)):
            return "本科"
        if any(token in text for token in ("大专", "专科")):
            return "大专"
        return text

    @classmethod
    def _education_precision_rank(cls, value: str) -> int:
        text = str(value or "").strip()
        if not text:
            return 0
        bucket = cls._education_bucket(text)
        if bucket not in {"本科", "硕士", "博士", "大专"}:
            return 1
        if any(token in text for token in ("港", "海归", "海外", "留学")):
            return 3
        return 2

    @classmethod
    def _is_education_refinement(cls, candidate_value: str, baseline_value: str) -> bool:
        candidate_bucket = cls._education_bucket(candidate_value)
        baseline_bucket = cls._education_bucket(baseline_value)
        if not candidate_bucket or candidate_bucket != baseline_bucket:
            return False
        return cls._education_precision_rank(candidate_value) > cls._education_precision_rank(baseline_value)

    @staticmethod
    def _age_label_precision_rank(value: str) -> int:
        text = str(value or "").strip()
        if re.fullmatch(r"(19\d{2}|20\d{2})年", text):
            return 4
        if re.fullmatch(r"\d{2}年", text):
            return 3
        if re.fullmatch(r"\d{1,2}岁", text):
            return 2
        if re.fullmatch(r"\d{2}后", text):
            return 1
        return 0

    @classmethod
    def _normalize_age_label_key(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        exact_year_match = re.fullmatch(r"(19\d{2}|20\d{2})年", text)
        if exact_year_match:
            return f"birth_year:{exact_year_match.group(1)}"
        short_year_match = re.fullmatch(r"(\d{2})年", text)
        if short_year_match:
            suffix = int(short_year_match.group(1))
            current_suffix = datetime.now().year % 100
            birth_year = 2000 + suffix if suffix <= current_suffix else 1900 + suffix
            return f"birth_year:{birth_year}"
        age_match = re.fullmatch(r"(\d{1,2})岁", text)
        if age_match:
            return f"age:{age_match.group(1)}"
        cohort_match = re.fullmatch(r"(\d{2})后", text)
        if cohort_match:
            return f"cohort:{cohort_match.group(1)}"
        return text

    @classmethod
    def _is_age_label_refinement(cls, candidate_value: str, baseline_value: str) -> bool:
        candidate_rank = cls._age_label_precision_rank(candidate_value)
        baseline_rank = cls._age_label_precision_rank(baseline_value)
        if candidate_rank <= baseline_rank:
            return False
        candidate_key = cls._normalize_age_label_key(candidate_value)
        baseline_key = cls._normalize_age_label_key(baseline_value)
        if candidate_key and candidate_key == baseline_key:
            return True
        baseline_cohort = re.fullmatch(r"(\d{2})后", str(baseline_value or "").strip())
        candidate_year = re.fullmatch(r"(\d{2})年", str(candidate_value or "").strip())
        if baseline_cohort and candidate_year and baseline_cohort.group(1) == candidate_year.group(1):
            return True
        return False

    @classmethod
    def _dedupe_observations_preserving_order(
        cls,
        observations: list[FieldObservation],
    ) -> list[FieldObservation]:
        deduped: list[FieldObservation] = []
        seen: set[tuple[str, str, str]] = set()
        for observation in observations:
            key = (
                str(getattr(observation, "field", "") or "").strip(),
                str(getattr(observation, "normalized_value", "") or ""),
                str(getattr(observation, "scope", "") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(observation)
        return deduped

    @classmethod
    def _observation_priority(
        cls,
        observation: FieldObservation,
    ) -> tuple[int, float, int, int, int]:
        source = str(getattr(observation, "source", "") or "").strip()
        source_rank = 50
        if source == "semantic_explicit_self_marker":
            source_rank = 100
        elif source == "semantic_contact_candidate":
            source_rank = 99
        elif source == "semantic_age_label_derived":
            source_rank = 98
        elif source == "semantic_chunk_partner_requirement":
            source_rank = 97
        elif source == "semantic_deterministic":
            source_rank = 96
        elif source == "semantic_chunk_partner_preference":
            source_rank = 95
        elif source == "semantic_chunk_deterministic":
            source_rank = 94
        elif source.startswith("semantic_"):
            source_rank = 93
        elif source.startswith("ai_"):
            source_rank = 80
        elif source.startswith("legacy_"):
            source_rank = 70
        confidence = float(getattr(observation, "confidence", 0.0) or 0.0)
        evidence_span_rank = 1 if str(getattr(observation, "evidence_span", "") or "").strip() else 0
        value_length = len(str(getattr(observation, "normalized_value", "") or "").strip())
        scope_rank = 1 if str(getattr(observation, "scope", "") or "").strip() != "mixed" else 0
        return source_rank, confidence, evidence_span_rank, value_length, scope_rank

    @staticmethod
    def _is_ai_observation(observation: FieldObservation | None) -> bool:
        if observation is None:
            return False
        source = str(getattr(observation, "source", "") or "").strip()
        return source.startswith("ai_")

    @staticmethod
    def _is_authoritative_direct_observation(observation: FieldObservation | None) -> bool:
        if observation is None:
            return False
        source = str(getattr(observation, "source", "") or "").strip()
        return source.startswith("semantic_")

    @staticmethod
    def _derive_precise_age_from_label(label: str) -> int | None:
        text = str(label or "").strip()
        if not text:
            return None

        exact_year_match = re.fullmatch(r"(19\d{2}|20\d{2})年", text)
        if exact_year_match:
            return max(1, datetime.now().year - int(exact_year_match.group(1)))

        short_year_match = re.fullmatch(r"(\d{2})年", text)
        if short_year_match:
            suffix = int(short_year_match.group(1))
            current_suffix = datetime.now().year % 100
            birth_year = 2000 + suffix if suffix <= current_suffix else 1900 + suffix
            return max(1, datetime.now().year - birth_year)

        age_match = re.fullmatch(r"(\d{1,2})岁", text)
        if age_match:
            return int(age_match.group(1))

        return None

    def _extract_direct_observations(self, snapshot: TurnInputSnapshot) -> list[FieldObservation]:
        text = str(getattr(snapshot, "user_message", "") or "").strip()
        if not text:
            return []

        observations: list[FieldObservation] = []
        seen: set[tuple[str, str, str]] = set()
        prompt_state = getattr(snapshot, "prompt_state", {}) or {}
        asked_fields = self._extract_prompt_asked_fields(prompt_state)
        deterministic_fields = self._extract_deterministic_fields(text, prompt_state=prompt_state)
        extraction_service = self._get_extraction_service()
        explicit_self_sex_evidence = self._resolve_explicit_self_sex_evidence(
            text,
            prompt_state=prompt_state,
            deterministic_fields=deterministic_fields,
        )
        explicit_self_age_evidence = self._resolve_explicit_self_age_evidence(
            text,
            prompt_state=prompt_state,
            deterministic_fields=deterministic_fields,
        )
        explicit_self_occupation_evidence = self._resolve_explicit_self_occupation_evidence(
            text,
            prompt_state=prompt_state,
            deterministic_fields=deterministic_fields,
        )

        for field_name, value in deterministic_fields.items():
            scope = self._infer_scope(field_name)
            confidence = 0.96 if scope in {"self", "contact"} else 0.93
            evidence_span = str(value)
            source = "semantic_deterministic"
            if field_name == "sex" and explicit_self_sex_evidence:
                confidence = 0.98
                evidence_span = explicit_self_sex_evidence
                source = "semantic_explicit_self_marker"
            elif field_name == "age" and explicit_self_age_evidence:
                confidence = 0.98
                evidence_span = explicit_self_age_evidence
                source = "semantic_explicit_self_marker"
            elif field_name == "age_label" and explicit_self_age_evidence and "age" in asked_fields:
                confidence = 0.98
                evidence_span = explicit_self_age_evidence
                source = "semantic_explicit_self_marker"
            elif field_name == "occupation" and explicit_self_occupation_evidence:
                confidence = 0.98
                evidence_span = explicit_self_occupation_evidence
                source = "semantic_explicit_self_marker"
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=field_name,
                    value=value,
                    normalized_value=value,
                    scope=scope,
                    owner="self" if scope in {"self", "contact"} else scope,
                    evidence_text=text,
                    evidence_span=evidence_span,
                    confidence=confidence,
                    write_mode="direct_write",
                    source=source,
                ),
            )

        if extraction_service is not None and hasattr(extraction_service, "analyze_numeric_semantics"):
            analysis = extraction_service.analyze_numeric_semantics(text)
            self._append_numeric_observations(observations, seen, text, analysis)

        self._append_height_weight_shorthand(observations, seen, text)
        self._append_chunk_level_observations(
            observations,
            seen,
            text,
            prompt_state=prompt_state,
        )
        self._append_partner_numeric_preference_observations(observations, seen, text)
        self._append_contact_observations(observations, seen, text)
        return observations

    @staticmethod
    def _resolve_ai_timeout(timeout_override: float | None = None) -> float:
        if timeout_override is not None:
            try:
                return max(1.0, float(timeout_override))
            except (TypeError, ValueError):
                pass
        configured = str(os.getenv("UNIFIED_TURN_SYNC_AI_TIMEOUT_SECONDS", "") or "").strip()
        raw = configured
        if not raw:
            raw = str(os.getenv("CHAT_AI_TIMEOUT_SECONDS", "45") or "").strip()
        try:
            return max(1.0, float(raw))
        except (TypeError, ValueError):
            return 45.0

    @staticmethod
    def _resolve_sync_ai_blocking_cap() -> float | None:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_MAX_BLOCKING_SECONDS", "20") or "").strip()
        try:
            cap = float(raw)
        except (TypeError, ValueError):
            cap = 20.0
        if cap <= 0:
            return None
        return max(1.0, cap)

    @staticmethod
    def _resolve_primary_model_name() -> str | None:
        model_name = str(os.getenv("UNIFIED_TURN_SYNC_AI_MODEL", "") or "").strip()
        return model_name or None

    @classmethod
    def _resolve_ai_retry_timeout(cls, primary_timeout: float) -> float:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_RETRY_TIMEOUT_SECONDS", "") or "").strip()
        retry_timeout = max(8.0, primary_timeout * 0.6)
        if raw:
            try:
                retry_timeout = float(raw)
            except (TypeError, ValueError):
                retry_timeout = max(8.0, primary_timeout * 0.6)
        if retry_timeout <= 0:
            retry_timeout = max(8.0, primary_timeout * 0.6)
        return max(1.0, min(primary_timeout, retry_timeout))

    @staticmethod
    def _sync_ai_retry_enabled() -> bool:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_RETRY_ENABLED", "0") or "").strip().lower()
        return raw not in {"0", "false", "off", "no"}

    @staticmethod
    def _resolve_retry_model_name() -> str | None:
        model_name = str(os.getenv("UNIFIED_TURN_SYNC_AI_RETRY_MODEL", "") or "").strip()
        return model_name or None

    @staticmethod
    def _resolve_ai_max_tokens() -> int:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_MAX_TOKENS", "220") or "").strip()
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 220
        return max(64, min(900, value))

    @staticmethod
    def _resolve_ai_reasoning_effort() -> str | None:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_REASONING_EFFORT", "low") or "").strip().lower()
        if raw in {"low", "medium", "high"}:
            return raw
        return None

    @staticmethod
    def _resolve_ai_temperature() -> float:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_TEMPERATURE", "0.2") or "").strip()
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = 0.2
        return max(0.0, min(1.0, value))

    @classmethod
    def _build_ai_attempt_plan(
        cls,
        timeout_override: float | None,
        *,
        enforce_blocking_cap: bool = False,
    ) -> list[dict[str, object]]:
        primary_timeout = cls._resolve_ai_timeout(timeout_override)
        if timeout_override is None or enforce_blocking_cap:
            blocking_cap = cls._resolve_sync_ai_blocking_cap()
            if blocking_cap is not None:
                primary_timeout = min(primary_timeout, blocking_cap)
        primary_model = cls._resolve_primary_model_name()
        attempts: list[dict[str, object]] = [{"timeout": primary_timeout, "model_name": primary_model}]
        if not cls._sync_ai_retry_enabled():
            return attempts
        retry_timeout = cls._resolve_ai_retry_timeout(primary_timeout)
        retry_model = cls._resolve_retry_model_name()
        attempts.append({"timeout": retry_timeout, "model_name": retry_model})
        return attempts

    @staticmethod
    def _env_enabled(name: str, default: bool) -> bool:
        raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
        return raw not in {"0", "false", "off", "no"}

    @classmethod
    def _sync_ai_circuit_breaker_enabled(cls) -> bool:
        return cls._env_enabled("UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_ENABLED", True)

    @staticmethod
    def _resolve_sync_ai_circuit_breaker_threshold() -> int:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_THRESHOLD", "2") or "").strip()
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 2
        return max(1, min(10, value))

    @staticmethod
    def _resolve_sync_ai_circuit_breaker_cooldown_seconds() -> float:
        raw = str(os.getenv("UNIFIED_TURN_SYNC_AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "180") or "").strip()
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = 180.0
        return max(5.0, value)

    @classmethod
    def _reset_sync_ai_circuit_breaker_state(cls) -> None:
        cls._SYNC_AI_CIRCUIT_BREAKER_STATE["consecutive_transport_failures"] = 0
        cls._SYNC_AI_CIRCUIT_BREAKER_STATE["open_until_monotonic"] = 0.0

    @classmethod
    def _current_sync_ai_skip_status(cls) -> str | None:
        if not cls._sync_ai_circuit_breaker_enabled():
            return None
        open_until = float(cls._SYNC_AI_CIRCUIT_BREAKER_STATE.get("open_until_monotonic") or 0.0)
        if open_until > time.monotonic():
            return "circuit_open"
        return None

    @classmethod
    def _is_transport_failure(cls, exc: Exception) -> bool:
        message = str(exc or "").strip().lower()
        if not message:
            return False
        return any(marker in message for marker in cls._TRANSPORT_FAILURE_MARKERS)

    @classmethod
    def _record_transport_failure(cls, exc: Exception) -> None:
        if not cls._sync_ai_circuit_breaker_enabled():
            return
        state = cls._SYNC_AI_CIRCUIT_BREAKER_STATE
        consecutive_failures = int(state.get("consecutive_transport_failures") or 0) + 1
        state["consecutive_transport_failures"] = consecutive_failures
        threshold = cls._resolve_sync_ai_circuit_breaker_threshold()
        if consecutive_failures < threshold:
            logger.info(
                "[unified_understanding.ai_semantic_extraction.circuit_breaker] transport_failure: consecutive=%s threshold=%s error=%s",
                consecutive_failures,
                threshold,
                exc,
            )
            return
        cooldown_seconds = cls._resolve_sync_ai_circuit_breaker_cooldown_seconds()
        state["open_until_monotonic"] = time.monotonic() + cooldown_seconds
        logger.warning(
            "[unified_understanding.ai_semantic_extraction.circuit_breaker] opened: consecutive=%s threshold=%s cooldown=%.1fs error=%s",
            consecutive_failures,
            threshold,
            cooldown_seconds,
            exc,
        )

    @classmethod
    def _reset_transport_failure_streak(cls, *, reason: str) -> None:
        if not cls._sync_ai_circuit_breaker_enabled():
            return
        state = cls._SYNC_AI_CIRCUIT_BREAKER_STATE
        consecutive_failures = int(state.get("consecutive_transport_failures") or 0)
        open_until = float(state.get("open_until_monotonic") or 0.0)
        if consecutive_failures <= 0 and open_until <= 0:
            return
        state["consecutive_transport_failures"] = 0
        state["open_until_monotonic"] = 0.0
        logger.info(
            "[unified_understanding.ai_semantic_extraction.circuit_breaker] reset: reason=%s previous_consecutive=%s was_open=%s",
            reason,
            consecutive_failures,
            1 if open_until > time.monotonic() else 0,
        )

    @staticmethod
    def _serialize_profile(user_profile: object | None) -> str:
        if user_profile is None:
            return "{}"
        fields = {}
        for name in ("sex", "age", "age_label", "location", "education", "occupation", "marital_status", "monthly_income"):
            value = getattr(user_profile, name, None)
            if value not in (None, "", 0):
                fields[name] = value
        return json.dumps(fields, ensure_ascii=False)

    @staticmethod
    def _parse_json_payload(raw: str) -> dict[str, Any] | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _build_frame_from_ai_payload(self, payload: dict[str, Any]) -> TurnSemanticFrame | None:
        primary_domain = str(payload.get("primary_domain") or "").strip()
        if primary_domain not in {"profile", "contact", "faq", "boundary", "risk", "closing", "mixed"}:
            return None

        observations: list[FieldObservation] = []
        for item in list(payload.get("field_observations") or []):
            observation = self._parse_ai_observation(item)
            if observation is not None:
                observations.append(observation)
        if not observations and any(isinstance(item, dict) for item in list(payload.get("items") or [])):
            slim_frame = self._build_frame_from_slim_payload(payload)
            if slim_frame is not None:
                observations = list(getattr(slim_frame, "field_observations", []) or [])

        questions: list[UserQuestion] = []
        for item in list(payload.get("user_questions") or []):
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic") or "").strip()
            question_text = str(item.get("question_text") or "").strip()
            confidence = float(item.get("confidence") or 0.0)
            if not topic or not question_text:
                continue
            questions.append(UserQuestion(topic=topic, question_text=question_text, confidence=confidence))

        acts = [str(item).strip() for item in list(payload.get("acts") or []) if str(item).strip()]
        risk_flags = [str(item).strip() for item in list(payload.get("risk_flags") or []) if str(item).strip()]
        boundaries = [str(item).strip() for item in list(payload.get("boundaries") or []) if str(item).strip()]
        notes = [str(item).strip() for item in list(payload.get("notes") or []) if str(item).strip()]
        confidence = float(payload.get("confidence") or 0.0)

        return TurnSemanticFrame(
            version="v1",
            source="ai_structured_extraction",
            primary_domain=primary_domain,
            acts=acts,
            user_questions=questions,
            field_observations=observations,
            risk_flags=risk_flags,
            boundaries=boundaries,
            notes=notes,
            confidence=confidence,
        )

    def _build_frame_from_slim_payload(self, payload: dict[str, Any]) -> TurnSemanticFrame | None:
        if not isinstance(payload, dict):
            return None
        observations: list[FieldObservation] = []
        raw_items = self._extract_slim_items(payload)
        for item in raw_items:
            normalized_item = self._normalize_slim_item(item)
            if normalized_item is None:
                continue
            parsed = self._parse_ai_observation(normalized_item)
            if parsed is not None:
                observations.append(parsed)

        primary_domain = str(payload.get("primary_domain") or "").strip().lower()
        if primary_domain not in {"profile", "contact", "faq", "boundary", "risk", "closing", "mixed"}:
            if not observations:
                return None
            has_partner = any(obs.scope == "partner" for obs in observations)
            has_contact = any(obs.scope == "contact" for obs in observations)
            has_self = any(obs.scope == "self" for obs in observations)
            if has_contact and not (has_self or has_partner):
                primary_domain = "contact"
            elif has_self and has_partner:
                primary_domain = "mixed"
            else:
                primary_domain = "profile"

        return TurnSemanticFrame(
            version="v1",
            source="ai_structured_extraction",
            primary_domain=primary_domain,
            acts=[],
            user_questions=[],
            field_observations=observations,
            risk_flags=[],
            boundaries=[],
            notes=["format=slim_json_payload"],
            confidence=0.9 if observations else 0.0,
        )

    def _extract_slim_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        direct_items = list(payload.get("items") or [])
        if any(isinstance(item, dict) for item in direct_items):
            return [item for item in direct_items if isinstance(item, dict)]

        normalized_items: list[dict[str, Any]] = []
        self_section = payload.get("userInfo") or payload.get("user_info") or payload.get("profile")
        partner_section = payload.get("择偶偏好") or payload.get("partner_preference") or payload.get("partnerPreference")
        contact_section = (
            payload.get("contact")
            if isinstance(payload.get("contact"), dict)
            else (payload.get("contactInfo") if isinstance(payload.get("contactInfo"), dict) else None)
        )

        normalized_items.extend(self._flatten_section_to_items(self_section, scope="self"))
        normalized_items.extend(self._flatten_section_to_items(partner_section, scope="partner"))
        normalized_items.extend(self._flatten_section_to_items(contact_section, scope="contact"))

        if normalized_items:
            return normalized_items

        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                continue
            normalized_items.append(
                {
                    "field": key,
                    "value": value,
                    "scope": "mixed",
                    "write_mode": "direct_write",
                    "confidence": 0.86,
                }
            )
        return normalized_items

    @staticmethod
    def _flatten_section_to_items(section: Any, *, scope: str) -> list[dict[str, Any]]:
        if not isinstance(section, dict):
            return []
        items: list[dict[str, Any]] = []
        for key, value in section.items():
            if isinstance(value, (dict, list)):
                continue
            items.append(
                {
                    "field": key,
                    "value": value,
                    "scope": scope,
                    "write_mode": "direct_write",
                    "confidence": 0.9 if scope in {"self", "partner"} else 0.86,
                }
            )
        return items

    def _normalize_slim_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        raw_field_name = str(item.get("field") or "").strip()
        field_name = self._normalize_ai_field_name(raw_field_name)
        scope = str(item.get("scope") or "").strip().lower() or "mixed"
        write_mode = str(item.get("write_mode") or "").strip().lower() or "direct_write"
        value = item.get("value")
        if value in (None, ""):
            return None
        if field_name in {"hometown", "household_registration", "hukou", "personality_type", "extrovert"}:
            return None
        if scope not in {"self", "partner", "contact", "faq", "meta", "mixed"}:
            scope = "mixed"

        if scope == "partner":
            if field_name == "sex":
                field_name = "partner_gender_preference"
            elif field_name in {"age", "age_label"}:
                field_name = "partner_pref_age"
            elif field_name == "height":
                field_name = "partner_pref_height"
            elif field_name == "monthly_income":
                field_name = "partner_pref_income"
            elif field_name == "location":
                field_name = "partner_pref_location"
            elif field_name == "education":
                field_name = "partner_pref_education"
            elif field_name == "occupation":
                field_name = "partner_pref_industry"
            elif field_name == raw_field_name:
                partner_key = re.sub(r"\s+", "", raw_field_name)
                if re.search(r"(身高)", partner_key):
                    field_name = "partner_pref_height"
                elif re.search(r"(年龄|年纪|年龄段|90后|95后|80后)", partner_key):
                    field_name = "partner_pref_age"
                elif re.search(r"(收入|经济|多金|有钱|条件)", partner_key):
                    field_name = "partner_pref_income"
                elif re.search(r"(学历|本科|大专|硕士|博士)", partner_key):
                    field_name = "partner_pref_education"
                elif re.search(r"(地区|城市|同城|本地|地点|地域|深圳|广州|上海|北京)", partner_key):
                    field_name = "partner_pref_location"
                elif re.search(r"(性格|成熟|稳重)", partner_key):
                    field_name = "partner_pref_personality"
                elif re.search(r"(工作|职业|行业|稳定)", partner_key):
                    field_name = "partner_pref_other"
                else:
                    field_name = "partner_requirement"
        elif scope == "self" and field_name == raw_field_name:
            self_key = re.sub(r"\s+", "", raw_field_name)
            if re.search(r"(性别|gender)", self_key, flags=re.IGNORECASE):
                field_name = "sex"
            elif re.search(r"(城市|地区|所在地|location)", self_key, flags=re.IGNORECASE):
                field_name = "location"
            elif re.search(r"(学历|education)", self_key, flags=re.IGNORECASE):
                field_name = "education"
            elif re.search(r"(婚况|婚姻|marital)", self_key, flags=re.IGNORECASE):
                field_name = "marital_status"
            elif re.search(r"(收入|年收入|月收入|income|salary)", self_key, flags=re.IGNORECASE):
                field_name = "monthly_income"
            elif re.search(r"(职业|工作|occupation|job)", self_key, flags=re.IGNORECASE):
                field_name = "occupation"
        if scope == "contact" and field_name in {"contact", "phone", "wechat"}:
            pass

        if not field_name:
            return None
        if write_mode not in {"direct_write", "soft_confirm"}:
            write_mode = "soft_confirm"
        try:
            confidence = float(item.get("confidence") or 0.9)
        except (TypeError, ValueError):
            confidence = 0.9
        confidence = max(0.0, min(1.0, confidence))
        normalized_value = str(value).strip()
        if not normalized_value:
            return None

        return {
            "field": field_name,
            "value": normalized_value,
            "normalized_value": normalized_value,
            "scope": scope if scope != "mixed" else self._infer_scope(field_name),
            "owner": "self" if scope in {"self", "contact"} else (scope if scope != "mixed" else self._infer_scope(field_name)),
            "evidence_text": normalized_value,
            "evidence_span": normalized_value,
            "confidence": confidence,
            "write_mode": write_mode,
            "source": "ai_semantic_extraction",
        }

    @staticmethod
    def _parse_ai_observation(item: Any) -> FieldObservation | None:
        if not isinstance(item, dict):
            return None
        field_name = AISemanticExtractionService._normalize_ai_field_name(str(item.get("field") or "").strip())
        scope = str(item.get("scope") or "").strip().lower()
        owner = str(item.get("owner") or "").strip().lower()
        write_mode = str(item.get("write_mode") or "").strip().lower()
        if not field_name:
            return None
        if scope not in {"self", "partner", "contact", "faq", "meta", "mixed"}:
            scope = AISemanticExtractionService._infer_scope(field_name)
        if owner not in {"self", "partner", "contact", "faq", "meta", "mixed"}:
            owner = "self" if scope in {"self", "contact"} else scope
        if write_mode not in {"direct_write", "soft_confirm"}:
            write_mode = "soft_confirm"
        raw_value = item.get("value")
        normalized_value = item.get("normalized_value")
        if raw_value in (None, ""):
            raw_value = normalized_value
        if normalized_value in (None, ""):
            normalized_value = raw_value
        if normalized_value in (None, ""):
            return None
        evidence_text = str(item.get("evidence_text") or normalized_value or raw_value or "").strip()
        try:
            confidence = float(item.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        return FieldObservation(
            field=field_name,
            value=raw_value,
            normalized_value=normalized_value,
            scope=scope,
            owner=owner,
            evidence_text=evidence_text,
            evidence_span=str(item.get("evidence_span") or "").strip() or None,
            confidence=confidence,
            write_mode=write_mode,
            source=str(item.get("source") or "ai_semantic_extraction").strip() or "ai_semantic_extraction",
            raw_value=item.get("raw_value"),
            unit=str(item.get("unit") or "").strip() or None,
            relation=str(item.get("relation") or "").strip() or None,
            conflict_hint=str(item.get("conflict_hint") or "").strip() or None,
        )

    @staticmethod
    def _normalize_ai_field_name(raw_field: str) -> str:
        field = str(raw_field or "").strip()
        if not field:
            return ""
        alias = {
            "性别": "sex",
            "gender": "sex",
            "年龄": "age",
            "年龄段": "age_label",
            "年龄标签": "age_label",
            "所在地": "location",
            "当前居住地": "location",
            "现居地": "location",
            "居住地": "location",
            "residence": "location",
            "城市": "location",
            "city": "location",
            "location": "location",
            "birthYear": "age_label",
            "birth_year": "age_label",
            "出生年份": "age_label",
            "出生年": "age_label",
            "currentLocation": "location",
            "current_location": "location",
            "currentArea": "location",
            "current_area": "location",
            "currentResidence": "location",
            "industry": "occupation",
            "currentIndustry": "occupation",
            "profession": "occupation",
            "jobTitle": "occupation",
            "job_title": "occupation",
            "学历": "education",
            "最高学历": "education",
            "education": "education",
            "婚姻状态": "marital_status",
            "婚况": "marital_status",
            "marital_status": "marital_status",
            "marital": "marital_status",
            "收入": "monthly_income",
            "年收入": "monthly_income",
            "年薪": "monthly_income",
            "月收入": "monthly_income",
            "income": "monthly_income",
            "annual_income": "monthly_income",
            "salary": "monthly_income",
            "职业": "occupation",
            "工作": "occupation",
            "occupation": "occupation",
            "job": "occupation",
            "联系方式": "contact",
            "手机号": "phone",
            "phoneNumber": "phone",
            "phone_number": "phone",
            "mobile": "phone",
            "mobileNumber": "phone",
            "mobile_number": "phone",
            "电话": "phone",
            "微信": "wechat",
            "wechatId": "wechat",
            "wechat_id": "wechat",
            "weixin": "wechat",
            "身高": "height",
            "体重": "weight",
            "择偶性别": "partner_gender_preference",
            "择偶要求性别": "partner_gender_preference",
            "择偶要求": "partner_requirement",
            "择偶条件": "partner_requirement",
            "身高要求": "partner_pref_height",
            "年龄要求": "partner_pref_age",
            "年龄段要求": "partner_pref_age",
            "收入要求": "partner_pref_income",
            "学历要求": "partner_pref_education",
            "地区要求": "partner_pref_location",
            "城市要求": "partner_pref_location",
            "工作要求": "partner_pref_other",
            "稳定要求": "partner_pref_other",
            "性格要求": "partner_pref_personality",
            "择偶要求身高": "partner_pref_height",
            "择偶身高": "partner_pref_height",
            "择偶年龄": "partner_pref_age",
            "择偶年龄段": "partner_pref_age",
            "择偶收入": "partner_pref_income",
            "择偶地区": "partner_pref_location",
            "择偶本地偏好": "partner_pref_locality",
            "择偶学历": "partner_pref_education",
            "择偶性格": "partner_pref_personality",
            "择偶行业": "partner_pref_industry",
            "择偶年龄关系": "partner_pref_age_relation",
            "择偶其他": "partner_pref_other",
            "需求": "partner_requirement",
            "交友需求": "partner_requirement",
            "对象需求": "partner_requirement",
            "择偶需求": "partner_requirement",
            "residenceCity": "location",
            "residence_city": "location",
            "currentCity": "location",
            "current_city": "location",
            "livingCity": "location",
            "living_city": "location",
            "maritalStatus": "marital_status",
            "annualIncome": "monthly_income",
            "partnerGenderPreference": "partner_gender_preference",
            "partnerRequirement": "partner_requirement",
            "partnerHeight": "partner_pref_height",
            "partnerAge": "partner_pref_age",
            "partnerLocation": "partner_pref_location",
            "preferredLocation": "partner_pref_location",
            "preferredCity": "partner_pref_location",
            "partnerEducation": "partner_pref_education",
            "preferredEducation": "partner_pref_education",
            "partnerIncome": "partner_pref_income",
            "preferredIncome": "partner_pref_income",
            "partnerIndustry": "partner_pref_industry",
            "preferredIndustry": "partner_pref_industry",
            "partnerPersonality": "partner_pref_personality",
            "preferredPersonality": "partner_pref_personality",
            "partnerOther": "partner_pref_other",
            "preferredAge": "partner_pref_age",
            "preferredAgeRange": "partner_pref_age",
        }
        mapped = alias.get(field)
        if mapped:
            return mapped

        compact_field = re.sub(r"[\s_\-]+", "", field).lower()
        compact_alias = {
            "residencecity": "location",
            "residence": "location",
            "cityofresidence": "location",
            "livingcity": "location",
            "currentcity": "location",
            "currentlocation": "location",
            "currentarea": "location",
            "currentresidence": "location",
            "birthyear": "age_label",
            "birthdate": "age_label",
            "industry": "occupation",
            "currentindustry": "occupation",
            "profession": "occupation",
            "jobtitle": "occupation",
            "maritalstatus": "marital_status",
            "annualincome": "monthly_income",
            "phonenumber": "phone",
            "mobilenumber": "phone",
            "mobile": "phone",
            "wechatid": "wechat",
            "weixin": "wechat",
            "partnergenderpreference": "partner_gender_preference",
            "partnerrequirement": "partner_requirement",
            "partnerheight": "partner_pref_height",
            "partnerage": "partner_pref_age",
            "partnerlocation": "partner_pref_location",
            "preferredlocation": "partner_pref_location",
            "preferredcity": "partner_pref_location",
            "partnereducation": "partner_pref_education",
            "preferrededucation": "partner_pref_education",
            "partnerincome": "partner_pref_income",
            "preferredincome": "partner_pref_income",
            "partnerindustry": "partner_pref_industry",
            "preferredindustry": "partner_pref_industry",
            "partnerpersonality": "partner_pref_personality",
            "preferredpersonality": "partner_pref_personality",
            "partnerother": "partner_pref_other",
            "preferredage": "partner_pref_age",
            "preferredagerange": "partner_pref_age",
            "requirement": "partner_requirement",
            "requirements": "partner_requirement",
            "demand": "partner_requirement",
        }
        return compact_alias.get(compact_field, field)

    def _parse_compact_line_payload(self, raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        if not text:
            return {"primary_domain": "", "field_observations": []}
        primary_domain = ""
        observations: list[dict[str, Any]] = []
        allowed_scope = {"self", "partner", "contact", "faq", "meta", "mixed"}
        allowed_write_mode = {"direct_write", "soft_confirm"}
        for line in text.splitlines():
            clean = str(line or "").strip().strip("`").strip()
            if not clean:
                continue
            if clean.lower().startswith("primary_domain="):
                primary_domain = clean.split("=", 1)[1].strip().lower()
                continue
            parts = [part.strip() for part in clean.split("|")]
            if len(parts) >= 4:
                field_name = self._normalize_ai_field_name(parts[0])
                scope = parts[1].lower()
                write_mode = parts[2].lower()
                value = parts[3]
                confidence = 0.9
                if len(parts) >= 5:
                    try:
                        confidence = float(parts[4])
                    except (TypeError, ValueError):
                        confidence = 0.9
                if not field_name or not value:
                    continue
                if scope not in allowed_scope:
                    scope = self._infer_scope(field_name)
                if write_mode not in allowed_write_mode:
                    write_mode = "soft_confirm"
                observations.append(
                    {
                        "field": field_name,
                        "value": value,
                        "normalized_value": value,
                        "scope": scope,
                        "owner": "self" if scope in {"self", "contact"} else scope,
                        "confidence": max(0.0, min(1.0, confidence)),
                        "write_mode": write_mode,
                        "source": "ai_semantic_extraction",
                    }
                )
                continue
            if "=" in clean:
                key, value = clean.split("=", 1)
                field_name = self._normalize_ai_field_name(str(key or "").strip())
                value = str(value or "").strip()
                if not field_name or not value:
                    continue
                scope = self._infer_scope(field_name)
                observations.append(
                    {
                        "field": field_name,
                        "value": value,
                        "normalized_value": value,
                        "scope": scope,
                        "owner": "self" if scope in {"self", "contact"} else scope,
                        "confidence": 0.9,
                        "write_mode": "direct_write",
                        "source": "ai_semantic_extraction",
                    }
                )
        return {"primary_domain": primary_domain, "field_observations": observations}

    def _build_frame_from_compact_payload(self, payload: dict[str, Any]) -> TurnSemanticFrame | None:
        if not isinstance(payload, dict):
            return None
        observations: list[FieldObservation] = []
        for item in list(payload.get("field_observations") or []):
            parsed = self._parse_ai_observation(item)
            if parsed is not None:
                observations.append(parsed)
        if not observations:
            return None
        primary_domain = str(payload.get("primary_domain") or "").strip().lower()
        if primary_domain not in {"profile", "contact", "faq", "boundary", "risk", "closing", "mixed"}:
            has_partner = any(obs.scope == "partner" for obs in observations)
            has_contact = any(obs.scope == "contact" for obs in observations)
            has_self = any(obs.scope == "self" for obs in observations)
            if has_contact and not (has_self or has_partner):
                primary_domain = "contact"
            elif has_self and has_partner:
                primary_domain = "mixed"
            else:
                primary_domain = "profile"
        return TurnSemanticFrame(
            version="v1",
            source="ai_structured_extraction",
            primary_domain=primary_domain,
            acts=[],
            user_questions=[],
            field_observations=observations,
            risk_flags=[],
            boundaries=[],
            notes=["format=compact_line_payload"],
            confidence=0.9,
        )

    def _extract_deterministic_fields(
        self,
        message: str,
        *,
        prompt_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        fields.update(self._extract_compact_intro_overrides(message))

        if self.semantic_service is not None and hasattr(self.semantic_service, "_extract_deterministic_profile_fields"):
            extracted = self.semantic_service._extract_deterministic_profile_fields(message)  # noqa: SLF001
            if isinstance(extracted, dict):
                for key, value in extracted.items():
                    if key not in fields and value not in (None, ""):
                        fields[key] = value

        extraction_service = self._get_extraction_service()
        if extraction_service is not None and hasattr(extraction_service, "_extract_deterministic_self_field_candidates"):
            extra = extraction_service._extract_deterministic_self_field_candidates(message)  # noqa: SLF001
            if isinstance(extra, dict):
                for field_name, value in extra.items():
                    if self._infer_scope(field_name) == "self" and hasattr(extraction_service, "_is_high_quality_field_value"):
                        is_high_quality = extraction_service._is_high_quality_field_value(  # noqa: SLF001
                            str(field_name),
                            value,
                            user_message=message,
                            scope="self",
                        )
                        if not is_high_quality:
                            continue
                    if field_name not in fields and value not in (None, ""):
                        fields[field_name] = value

        if "partner_gender_preference" not in fields and self.semantic_service is not None and hasattr(
            self.semantic_service,
            "_extract_partner_gender_preference",
        ):
            partner_gender = self.semantic_service._extract_partner_gender_preference(message)  # noqa: SLF001
            if partner_gender:
                fields["partner_gender_preference"] = partner_gender

        if (
            extraction_service is not None
            and hasattr(extraction_service, "_extract_partner_preference_subslots")
            and self._looks_like_partner_preference_context(message)
        ):
            structured_subslots = extraction_service._extract_partner_preference_subslots(message)  # noqa: SLF001
            normalized_subslots: dict[str, Any] = {}
            for field_name, value in dict(structured_subslots or {}).items():
                clean_value = str(value or "").strip()
                if not clean_value:
                    continue
                normalized_subslots[field_name] = clean_value
                existing_value = str(fields.get(field_name) or "").strip()
                if not existing_value or len(clean_value) > len(existing_value):
                    fields[field_name] = clean_value
            if normalized_subslots:
                resolved_requirement = ""
                if hasattr(extraction_service, "_resolve_partner_requirement_from_message"):
                    resolved_requirement = str(
                        extraction_service._resolve_partner_requirement_from_message(  # noqa: SLF001
                            message,
                            allow_legacy_fallback=True,
                            prefer_structured=True,
                        )
                        or ""
                    ).strip()
                existing_requirement = str(fields.get("partner_requirement") or "").strip()
                if resolved_requirement:
                    fields["partner_requirement"] = self._pick_richer_partner_requirement(
                        existing_requirement,
                        resolved_requirement,
                    )
                elif hasattr(extraction_service, "_compose_partner_requirement_from_subslots"):
                    composed_requirement = str(
                        extraction_service._compose_partner_requirement_from_subslots(  # noqa: SLF001
                            normalized_subslots,
                            existing_requirement,
                        )
                        or ""
                    )
                    fields["partner_requirement"] = self._pick_richer_partner_requirement(
                        existing_requirement,
                        composed_requirement.strip(),
                    )

        correction_overrides = self._extract_explicit_correction_overrides(message)
        for field_name, value in correction_overrides.items():
            if value not in (None, ""):
                fields[field_name] = value

        if not self._looks_like_profile_intro(message):
            asked_fields = self._extract_prompt_asked_fields(prompt_state)
            followup_self_fields = asked_fields & {
                "sex",
                "age",
                "location",
                "education",
                "occupation",
                "marital_status",
                "monthly_income",
            }
            if correction_overrides:
                followup_self_fields.update(
                    field_name
                    for field_name in correction_overrides
                    if self._infer_scope(field_name) == "self"
                )
            if "age" in followup_self_fields:
                followup_self_fields.add("age_label")
            for field_name in list(fields.keys()):
                if self._infer_scope(field_name) == "self" and field_name not in followup_self_fields:
                    fields.pop(field_name, None)

        occupation = str(fields.get("occupation") or "").strip()
        if occupation and self._is_low_quality_occupation_text(occupation):
            fields.pop("occupation", None)

        return fields

    @staticmethod
    def _pick_richer_partner_requirement(current_value: str, candidate_value: str) -> str:
        current = str(current_value or "").strip()
        candidate = str(candidate_value or "").strip()
        if not current:
            return candidate
        if not candidate:
            return current
        if current == candidate:
            return current
        if current in candidate and len(candidate) > len(current):
            return candidate
        if candidate in current and len(current) >= len(candidate):
            return current

        def _score(text: str) -> tuple[int, int, int, int]:
            compact = re.sub(r"\s+", "", text)
            noise_free = 0 if re.search(r"(做饭|旅游|原生家庭|感情经历|[EI]人)", compact) else 1
            signal_count = len(
                re.findall(
                    r"(同老家|同在|同城|本地|最好|优先|不要\d{2}|不要|有房有车|工作稳定|积极阳光|三观正|情绪稳定|成熟稳重|90后|80后|学历|身高|收入|行业|年龄|比自己大|比自己小)",
                    compact,
                )
            )
            segment_count = len([part for part in re.split(r"[，,、]", compact) if part])
            return noise_free, signal_count, segment_count, len(compact)

        return candidate if _score(candidate) >= _score(current) else current

    @staticmethod
    def _looks_like_partner_preference_context(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        return bool(
            re.search(
                r"(另一半|对象|择偶|想找|找(?:男朋友|女朋友|对象|[男女]生)|期待|遇见|希望对方|看重|偏好|偏向|最好)",
                compact,
            )
        )

    def _extract_compact_intro_overrides(self, message: str) -> dict[str, Any]:
        text = str(message or "").strip()
        if not text:
            return {}

        fields: dict[str, Any] = {}
        precise_age_label = self._extract_compact_intro_age_label(text)
        if precise_age_label:
            fields["age_label"] = precise_age_label
        precise_location = self._extract_precise_self_location(text)
        if precise_location:
            fields["location"] = precise_location
        precise_education = self._extract_precise_self_education(text)
        if precise_education:
            fields["education"] = precise_education
        compact_match = self._match_compact_intro(text)
        if compact_match:
            location = str(compact_match.group("location") or "").strip()
            occupation = str(compact_match.group("occupation") or "").strip()
            if location and "location" not in fields:
                fields["location"] = location
            normalized_occupation = self._normalize_occupation_candidate(occupation)
            if normalized_occupation:
                fields["occupation"] = normalized_occupation
            inferred_sex = self._infer_sex_from_occupation_token(occupation)
            if inferred_sex:
                fields["sex"] = inferred_sex

        return fields

    @staticmethod
    def _extract_compact_intro_age_label(text: str) -> str:
        message = str(text or "").strip()
        if not message:
            return ""
        message = AISemanticExtractionService._strip_compact_intro_leading_fillers(message)
        if not message:
            return ""
        match = re.match(
            r"^\s*(?P<age>(?:19\d{2}|20\d{2})年|\d{2}(?:年|后)?)"
            r"(?=(?:\s|，|,|、)?(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华|坪山|"
            r"男生|女生|男的|女的|未婚|单身|离异|在编|教师|老师|护士|医生|程序员|开发|运营|产品|设计|财务|销售|行政|客服|外贸|本科|大专|硕士|博士|研究生))",
            message,
        )
        if not match:
            return ""
        age_token = str(match.group("age") or "").strip()
        if not age_token:
            return ""
        if re.fullmatch(r"\d{2}", age_token):
            return f"{age_token}年"
        return age_token

    @classmethod
    def _strip_compact_intro_leading_fillers(cls, text: str) -> str:
        message = str(text or "").strip()
        if not message:
            return ""
        return re.sub(
            rf"^\s*(?:(?:{cls._COMPACT_INTRO_FILLER_PATTERN})[\s，,、。！？!?]*)+",
            "",
            message,
            count=1,
        ).strip()

    @staticmethod
    def _extract_precise_self_location(text: str) -> str:
        message = str(text or "").strip()
        if not message:
            return ""
        location_pattern = (
            r"(?P<location>"
            r"(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)"
            r"(?:南山|福田|宝安|龙岗|龙华|坪山|罗湖|盐田|光明)?"
            r")"
        )
        explicit_patterns = (
            rf"(?:我在|人在|目前在|现在在|住在|现居|坐标){location_pattern}",
            rf"(?:男生|女生|男的|女的|先生|女士)在{location_pattern}",
            rf"(?:来自[\u4e00-\u9fa5]{{1,8}}(?:的)?(?:男生|女生|男的|女的)?在){location_pattern}",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, message)
            if match:
                return str(match.group("location") or "").strip()
        return ""

    @staticmethod
    def _extract_precise_self_education(text: str) -> str:
        message = str(text or "").strip()
        if not message:
            return ""
        match = re.search(r"(港硕|港本)", message)
        if match:
            return str(match.group(1) or "").strip()
        return ""

    @staticmethod
    def _match_compact_intro(text: str):
        return re.search(
            r"(?:\d{2}(?:年|后)?)?"
            r"(?P<location>(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)(?:南山|福田|宝安|龙岗|龙华|坪山)?)"
            r"(?P<occupation>在编(?:男|女)?(?:教师|老师)|(?:男|女)?(?:教师|老师|程序员|开发|运营|产品|设计|财务|医生|销售|行政|客服))",
            text,
        )

    @staticmethod
    def _infer_sex_from_occupation_token(occupation: str) -> str | None:
        text = str(occupation or "").strip()
        if not text:
            return None
        match = re.search(
            r"(?:^|在编)(?P<sex>男|女)(?:教师|老师|程序员|开发|运营|产品|设计|财务|医生|销售|行政|客服)$",
            text,
        )
        if match:
            return "男" if match.group("sex") == "男" else "女"
        if text.startswith("女"):
            return "女"
        if text.startswith("男"):
            return "男"
        return None

    def _resolve_explicit_self_sex_evidence(
        self,
        message: str,
        *,
        prompt_state: dict[str, Any] | None = None,
        deterministic_fields: dict[str, Any] | None = None,
    ) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None

        explicit_patterns = (
            r"(?:我是|本人|我)\s*(?:男生|女生|男的|女的|男|女)",
            r"^\s*(?:男生|女生|男的|女的|男|女)\s*(?:单身|未婚|离异|已婚|分居)",
            r"(?:^|[，,、\s])(?:男生|女生|男的|女的)\s*找(?:个|一个)?(?:男朋友|女朋友|对象|另一半)(?:$|[，,、\s])",
            r"(?:^|[，,、\s])(?:[\u4e00-\u9fa5]{1,6})?(?:男生|女生|男的|女的)\s*(?:在|现居|坐标|来自|人在)",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        if self._looks_like_explicit_sex_short_answer(text):
            return text

        compact_match = self._match_compact_intro(text)
        if compact_match and self._is_explicit_self_compact_intro_match(text, compact_match):
            occupation = str(compact_match.group("occupation") or "").strip()
            if self._infer_sex_from_occupation_token(occupation):
                return compact_match.group(0)

        asked_fields = self._extract_prompt_asked_fields(prompt_state)
        if (
            "sex" in asked_fields
            and str((deterministic_fields or {}).get("sex") or "").strip() in {"男", "女"}
            and self._looks_like_explicit_sex_short_answer(text)
        ):
            return text

        return None

    @staticmethod
    def _looks_like_explicit_sex_short_answer(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if re.search(r"(找|想找|喜欢|偏好|偏向|希望|对象|另一半)", text):
            return False
        normalized = re.sub(r"[，,、。！？!?~～\s]+", "", text)
        if not normalized:
            return False
        if re.search(r"(男朋友|女朋友)", normalized):
            return False
        return bool(
            re.fullmatch(
                r"(?:(?:是的|对|对的|嗯|嗯嗯|好的|好|没错|就是|肯定)[呀呢啊哦哈啦嘛]*)?"
                r"(?:男生|女生|男的|女的|男|女)"
                r"(?:[呀呢啊哦哈啦嘛]*(?:肯定的?|就是|必须|当然)?[呀呢啊哦哈啦嘛]*)*"
                r"(?:(?:男生|女生|男的|女的|男|女)[呀呢啊哦哈啦嘛]*)?",
                normalized,
            )
        )

    @staticmethod
    def _extract_prompt_asked_fields(prompt_state: dict[str, Any] | None) -> set[str]:
        state = prompt_state if isinstance(prompt_state, dict) else {}
        fields: set[str] = set()
        for key in ("asked_fields", "side_fields"):
            for item in list(state.get(key, []) or []):
                field = str(item or "").strip()
                if field:
                    fields.add(field)
        return fields

    @staticmethod
    def _looks_like_occupation_followup_answer(text: str) -> bool:
        message = str(text or "").strip()
        if not message:
            return False
        if "?" in message or "？" in message:
            return False
        if re.search(r"(找(?:男朋友|女朋友|对象)|另一半|希望对方|偏好|最好|要求)", message):
            return False
        return len(message) <= 24

    def _resolve_explicit_self_occupation_evidence(
        self,
        message: str,
        *,
        prompt_state: dict[str, Any] | None = None,
        deterministic_fields: dict[str, Any] | None = None,
    ) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        explicit_patterns = (
            r"(?:我是|我做|我在做|我从事|职业是|工作是|目前做|现在做)\s*[^\s，,。！？!?]{1,16}",
            r"[A-Za-z\u4e00-\u9fa5]{2,12}(?:行业)?工作",
            r"^\s*(?:在编)?(?:教师|老师|程序员|开发|运营|产品|设计|财务|医生|护士|销售|行政|客服|外贸)\s*$",
            r"^\s*(?:\d{2}(?:年|后)?\s*)?(?:(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)(?:南山|福田|宝安|龙岗|龙华|坪山|罗湖|盐田|光明)?\s*)?"
            r"(?:在编(?:男|女)?(?:教师|老师)|(?:男|女)?(?:教师|老师|程序员|开发|运营|产品|设计|财务|医生|护士|销售|行政|客服|外贸))"
            r"(?:(?:\s|，|,|、)*(?:本科|大专|硕士|博士|研究生|未婚|单身|离异|找|想找|最好|希望|偏向|倾向|同在|同城)|$)",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        compact_match = self._match_compact_intro(text)
        if compact_match and self._is_explicit_self_compact_intro_match(text, compact_match):
            occupation = str(compact_match.group("occupation") or "").strip()
            if occupation:
                return compact_match.group(0)
        asked_fields = self._extract_prompt_asked_fields(prompt_state)
        normalized_occupation = str((deterministic_fields or {}).get("occupation") or "").strip()
        if (
            "occupation" in asked_fields
            and normalized_occupation
            and self._looks_like_occupation_followup_answer(text)
        ):
            return text
        return None

    def _resolve_explicit_self_age_evidence(
        self,
        message: str,
        *,
        prompt_state: dict[str, Any] | None = None,
        deterministic_fields: dict[str, Any] | None = None,
    ) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        explicit_patterns = (
            r"(?:我|本人|自己).{0,8}(?:\d{1,2}岁|(?:19|20)\d{2}年|\d{2}后)",
            r"^\s*(?:\d{1,2}岁|(?:19|20)\d{2}年|\d{2}后)\s*(?:呀|呢|哈|哦|啊)?\s*$",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        asked_fields = self._extract_prompt_asked_fields(prompt_state)
        if "age" not in asked_fields:
            return None
        has_age_candidate = any(
            str((deterministic_fields or {}).get(name) or "").strip()
            for name in ("age", "age_label")
        )
        if has_age_candidate and self._looks_like_age_followup_answer(text):
            return text
        leading_compact_age = self._extract_compact_intro_age_label(text)
        if leading_compact_age:
            raw_match = re.match(
                rf"^\s*(?:(?:{self._COMPACT_INTRO_FILLER_PATTERN})[\s，,、。！？!?]*)*((?:19\d{2}|20\d{2})年|\d{2}(?:年|后)?)",
                text,
            )
            if raw_match:
                return str(raw_match.group(1) or "").strip()
        return None

    def _extract_explicit_correction_overrides(self, message: str) -> dict[str, Any]:
        text = str(message or "").strip()
        if not text or not self._looks_like_correction_message(text):
            return {}

        correction_tail_match = re.search(
            r"(?:不是|不在|不做|不算|说错了|搞错了).{0,12}?(?:是|在|做|改成|改为)\s*(?P<tail>.+)$",
            text,
        )
        if not correction_tail_match:
            return {}
        correction_tail = str(correction_tail_match.group("tail") or "").strip("，,、。！？!? ")
        if not correction_tail:
            return {}

        overrides: dict[str, Any] = {}
        tail_fields = self._extract_self_field_candidates_from_fragment(correction_tail)
        for field_name, value in tail_fields.items():
            if self._infer_scope(field_name) == "self" and value not in (None, ""):
                overrides[field_name] = value
        return overrides

    def _extract_self_field_candidates_from_fragment(self, message: str) -> dict[str, Any]:
        text = str(message or "").strip()
        if not text:
            return {}

        fields: dict[str, Any] = {}
        fields.update(self._extract_compact_intro_overrides(text))

        if self.semantic_service is not None and hasattr(self.semantic_service, "_extract_deterministic_profile_fields"):
            extracted = self.semantic_service._extract_deterministic_profile_fields(text)  # noqa: SLF001
            if isinstance(extracted, dict):
                for field_name, value in extracted.items():
                    normalized_field = str(field_name or "").strip()
                    if self._infer_scope(normalized_field) == "self" and value not in (None, ""):
                        fields[normalized_field] = value

        extraction_service = self._get_extraction_service()
        if extraction_service is not None and hasattr(extraction_service, "_extract_deterministic_self_field_candidates"):
            extra = extraction_service._extract_deterministic_self_field_candidates(text)  # noqa: SLF001
            if isinstance(extra, dict):
                for field_name, value in extra.items():
                    normalized_field = str(field_name or "").strip()
                    if self._infer_scope(normalized_field) != "self":
                        continue
                    if hasattr(extraction_service, "_is_high_quality_field_value"):
                        is_high_quality = extraction_service._is_high_quality_field_value(  # noqa: SLF001
                            normalized_field,
                            value,
                            user_message=text,
                            scope="self",
                        )
                        if not is_high_quality:
                            continue
                    if value not in (None, ""):
                        fields[normalized_field] = value
        return fields

    def _looks_like_correction_message(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self.semantic_service is not None and hasattr(self.semantic_service, "_looks_like_correction"):
            return bool(self.semantic_service._looks_like_correction(text))  # noqa: SLF001
        return bool(re.search(r"(不是.+是.+|不是这个|刚刚说的是|说错了|改成|改为)", text))

    @staticmethod
    def _looks_like_age_followup_answer(text: str) -> bool:
        message = str(text or "").strip()
        if not message:
            return False
        if "?" in message or "？" in message:
            return False
        if re.search(r"(找|想找|另一半|对象|希望对方|看重|要求|偏好|偏向|最好)", message):
            return False
        normalized = re.sub(r"[，,、。！？!?~～\s]+", "", message)
        if not normalized:
            return False
        return bool(
            re.fullmatch(
                r"(?:(?:是的|对|对的|嗯|嗯嗯|好的|好|没错|就是|肯定)[呀呢啊哦哈啦嘛]*)?"
                r"(?:\d{1,2}岁|(?:19|20)\d{2}年|\d{2}后)"
                r"(?:[呀呢啊哦哈啦嘛]*)?",
                normalized,
            )
        )

    @staticmethod
    def _is_explicit_self_compact_intro_match(text: str, compact_match) -> bool:
        prefix = re.sub(r"\s+", "", text[max(0, compact_match.start() - 6):compact_match.start()])
        if not prefix:
            return True
        return not bool(re.search(r"(找|想找|要找|最好|希望|喜欢|偏向|倾向)$", prefix))

    def _append_numeric_observations(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        message: str,
        analysis: dict[str, Any],
    ) -> None:
        for field_name, candidates, unit in (
            ("height", analysis.get("height_candidates") or [], "cm"),
            ("weight", analysis.get("weight_candidates") or [], "jin"),
        ):
            if not candidates:
                continue
            raw = str(candidates[0]).strip()
            number = self._extract_first_integer(raw)
            if number is None:
                continue
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=field_name,
                    value=number,
                    normalized_value=number,
                    scope="self",
                    owner="self",
                    evidence_text=message,
                    evidence_span=raw,
                    confidence=0.95,
                    write_mode="direct_write",
                    source="semantic_numeric_analysis",
                    raw_value=raw,
                    unit=unit,
                ),
            )

    def _append_height_weight_shorthand(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        message: str,
    ) -> None:
        shorthand_match = re.search(r"(?<!\d)(1[4-9]\d)\s*/\s*([5-9]\d|1\d{2})(?!\d)", message)
        if not shorthand_match:
            return
        raw = shorthand_match.group(0)
        height = int(shorthand_match.group(1))
        weight = int(shorthand_match.group(2))
        self._append_observation(
            observations,
            seen,
            FieldObservation(
                field="height",
                value=height,
                normalized_value=height,
                scope="self",
                owner="self",
                evidence_text=message,
                evidence_span=raw,
                confidence=0.97,
                write_mode="direct_write",
                source="semantic_height_weight_shorthand",
                raw_value=raw,
                unit="cm",
            ),
        )
        self._append_observation(
            observations,
            seen,
            FieldObservation(
                field="weight",
                value=weight,
                normalized_value=weight,
                scope="self",
                owner="self",
                evidence_text=message,
                evidence_span=raw,
                confidence=0.97,
                write_mode="direct_write",
                source="semantic_height_weight_shorthand",
                raw_value=raw,
                unit="jin",
            ),
        )

    def _append_contact_observations(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        message: str,
    ) -> None:
        candidates: list[dict[str, Any]] = []
        if self.semantic_service is not None and hasattr(self.semantic_service, "_extract_contact_candidate"):
            candidate = self.semantic_service._extract_contact_candidate(message)  # noqa: SLF001
            if candidate:
                candidates.append(candidate)
        if self.semantic_service is not None and hasattr(self.semantic_service, "_extract_bare_contact_candidate"):
            bare_candidate = self.semantic_service._extract_bare_contact_candidate(message)  # noqa: SLF001
            if bare_candidate:
                candidates.append(bare_candidate)

        for candidate in candidates:
            value = str(candidate.get("value") or "").strip()
            hinted_type = str(candidate.get("type") or "").strip()
            if not value or hinted_type not in {"phone", "wechat"}:
                continue
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=hinted_type,
                    value=value,
                    normalized_value=value,
                    scope="contact",
                    owner="self",
                    evidence_text=message,
                    evidence_span=value,
                    confidence=0.98,
                    write_mode="direct_write",
                    source="semantic_contact_candidate",
                ),
            )
            if not self._looks_like_same_number_contact_reply(message):
                continue
            mirrored_field = "wechat" if hinted_type == "phone" else "phone"
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=mirrored_field,
                    value=value,
                    normalized_value=value,
                    scope="contact",
                    owner="self",
                    evidence_text=message,
                    evidence_span=value,
                    confidence=0.97,
                    write_mode="direct_write",
                    source="semantic_contact_same_as_other_channel",
                ),
            )

    def _looks_like_same_number_contact_reply(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self.semantic_service is not None and hasattr(self.semantic_service, "_looks_like_wechat_same_as_phone_reply"):
            return bool(self.semantic_service._looks_like_wechat_same_as_phone_reply(text))  # noqa: SLF001
        compact = re.sub(r"\s+", "", text)
        patterns = (
            r"(?:微信|wx|vx).*(?:同号|一个号|一样|同一个)",
            r"(?:跟|和)?(?:电话|手机号|号码).*(?:一样|同号|同一个号)",
            r"(?:电话|手机号|号码).*(?:也可以加|也能加|也可以搜到|也能搜到|可以搜到|能搜到|可以加到|能加到)",
            r"(?:上面|刚才|前面)(?:那个|这个|的)?号(?:就行|可以|也行)",
            r"(?:电话|号码)也可以(?:当|做)?微信",
            r"(?:号码|电话)(?:也)?可以搜微信",
        )
        return any(re.search(pattern, compact) for pattern in patterns)

    def _append_chunk_level_observations(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        message: str,
        *,
        prompt_state: dict[str, Any] | None = None,
    ) -> None:
        chunks = self._split_semantic_chunks(message)
        if not chunks:
            return

        extraction_service = self._get_extraction_service()
        partner_parts: list[str] = []
        for chunk_type, chunk_text in chunks:
            if chunk_type == "partner":
                partner_parts.append(chunk_text)
                continue
            if chunk_type != "self_profile":
                continue
            normalized_chunk_text = self._sanitize_self_profile_chunk(chunk_text)
            normalized_chunk_text, partner_tail = self._split_partner_tail_from_self_chunk(normalized_chunk_text)
            if partner_tail:
                partner_parts.append(partner_tail)
            if not normalized_chunk_text:
                continue

            chunk_fields: dict[str, Any] = {}
            if self.semantic_service is not None and hasattr(self.semantic_service, "_extract_deterministic_profile_fields"):
                extracted = self.semantic_service._extract_deterministic_profile_fields(normalized_chunk_text)  # noqa: SLF001
                if isinstance(extracted, dict):
                    for field_name, value in extracted.items():
                        if value not in (None, ""):
                            chunk_fields[str(field_name).strip()] = value
            if extraction_service is not None and hasattr(extraction_service, "_extract_deterministic_self_field_candidates"):
                deterministic_self = extraction_service._extract_deterministic_self_field_candidates(normalized_chunk_text)  # noqa: SLF001
                if isinstance(deterministic_self, dict):
                    for field_name, value in deterministic_self.items():
                        normalized_field = str(field_name or "").strip()
                        if value not in (None, "") and normalized_field not in chunk_fields:
                            chunk_fields[normalized_field] = value
            if "sex" not in chunk_fields:
                explicit_sex = self._extract_explicit_self_sex_candidate_from_chunk(normalized_chunk_text)
                if explicit_sex:
                    chunk_fields["sex"] = explicit_sex

            explicit_self_sex_evidence = self._resolve_explicit_self_sex_evidence(
                normalized_chunk_text,
                prompt_state=prompt_state,
                deterministic_fields=chunk_fields,
            )
            explicit_self_age_evidence = self._resolve_explicit_self_age_evidence(
                normalized_chunk_text,
                prompt_state=prompt_state,
                deterministic_fields=chunk_fields,
            )
            explicit_self_occupation_evidence = self._resolve_explicit_self_occupation_evidence(
                normalized_chunk_text,
                prompt_state=prompt_state,
                deterministic_fields=chunk_fields,
            )

            for field_name, value in chunk_fields.items():
                if self._infer_scope(field_name) != "self":
                    continue
                if field_name not in {
                    "sex",
                    "age",
                    "age_label",
                    "location",
                    "education",
                    "occupation",
                    "marital_status",
                    "monthly_income",
                }:
                    continue
                confidence = 0.95
                source = "semantic_chunk_deterministic"
                evidence_span = str(value)
                if field_name == "sex" and explicit_self_sex_evidence:
                    confidence = 0.98
                    source = "semantic_explicit_self_marker"
                    evidence_span = explicit_self_sex_evidence
                elif field_name == "age" and explicit_self_age_evidence:
                    confidence = 0.98
                    source = "semantic_explicit_self_marker"
                    evidence_span = explicit_self_age_evidence
                elif field_name == "occupation" and explicit_self_occupation_evidence:
                    confidence = 0.98
                    source = "semantic_explicit_self_marker"
                    evidence_span = explicit_self_occupation_evidence
                elif field_name in {"education", "location", "marital_status"}:
                    confidence = 0.96

                self._append_observation(
                    observations,
                    seen,
                    FieldObservation(
                        field=field_name,
                        value=value,
                        normalized_value=value,
                        scope="self",
                        owner="self",
                        evidence_text=normalized_chunk_text,
                        evidence_span=evidence_span,
                        confidence=confidence,
                        write_mode="direct_write",
                        source=source,
                    ),
                )

        if partner_parts:
            self._append_partner_chunk_observations(
                observations,
                seen,
                "，".join(partner_parts),
            )

    def _append_partner_chunk_observations(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        partner_text: str,
    ) -> None:
        text = str(partner_text or "").strip()
        if not text:
            return
        extraction_service = self._get_extraction_service()
        if extraction_service is None:
            return
        if hasattr(extraction_service, "_extract_partner_preference_subslots"):
            subslots = extraction_service._extract_partner_preference_subslots(text)  # noqa: SLF001
            for field_name, value in dict(subslots or {}).items():
                normalized_field = str(field_name or "").strip()
                normalized_value = str(value or "").strip()
                if not normalized_field or not normalized_value:
                    continue
                self._append_observation(
                    observations,
                    seen,
                    FieldObservation(
                        field=normalized_field,
                        value=normalized_value,
                        normalized_value=normalized_value,
                        scope="partner",
                        owner="partner",
                        evidence_text=text,
                        evidence_span=normalized_value,
                        confidence=0.94,
                        write_mode="direct_write",
                        source="semantic_chunk_partner_preference",
                    ),
                )
        if hasattr(extraction_service, "_resolve_partner_requirement_from_message"):
            partner_requirement = str(
                extraction_service._resolve_partner_requirement_from_message(  # noqa: SLF001
                    text,
                    allow_legacy_fallback=True,
                    prefer_structured=True,
                )
                or ""
            ).strip()
            if partner_requirement:
                self._append_observation(
                    observations,
                    seen,
                    FieldObservation(
                        field="partner_requirement",
                        value=partner_requirement,
                        normalized_value=partner_requirement,
                        scope="partner",
                        owner="partner",
                        evidence_text=text,
                        evidence_span=partner_requirement,
                        confidence=0.93,
                        write_mode="direct_write",
                        source="semantic_chunk_partner_requirement",
                    ),
                )

    @staticmethod
    def _extract_explicit_self_sex_candidate_from_chunk(chunk_text: str) -> str | None:
        text = str(chunk_text or "").strip()
        if not text:
            return None
        if re.search(r"(?:女生|女的|女教师|女老师|女士)", text):
            return "女"
        if re.search(r"(?:男生|男的|男教师|男老师|先生)", text):
            return "男"
        if re.fullmatch(r"(?:女|男)", text):
            return text
        return None

    @staticmethod
    def _sanitize_self_profile_chunk(chunk_text: str) -> str:
        text = str(chunk_text or "").strip()
        if not text:
            return ""
        return re.sub(
            r"^\s*(?:(?:是的|对|对的|嗯|嗯嗯|好的|好呀|好哒|好|可以啊|可以呀|可以哒|可以|行啊|行的|行|ok|OK)[，,、 ]*)+",
            "",
            text,
        ).strip()

    @classmethod
    def _split_partner_tail_from_self_chunk(cls, chunk_text: str) -> tuple[str, str]:
        text = str(chunk_text or "").strip()
        if not text:
            return "", ""
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return "", ""
        pure_partner_like_patterns = (
            r"^(?:想着\d{2}后(?:男生|女生).*)$",
            r"^(?:想找|找(?:对象|男朋友|女朋友|个对象|个男朋友|个女朋友)|希望对方|最好|优先|能接受).*$",
            r"^(?:\d{2}后.{0,8}(?:工作稳定|情绪稳定|都可以|就行)).*$",
        )
        if any(re.search(pattern, compact) for pattern in pure_partner_like_patterns):
            return "", text

        split_patterns = (
            r"[，,、]\s*(?P<partner>想着\d{2}后(?:男生|女生).*)$",
            r"[，,、]\s*(?P<partner>(?:想找|找(?:起码|至少|对象|男朋友|女朋友|个对象|个男朋友|个女朋友)|希望对方|最好|优先|能接受).*)$",
            r"[，,、]\s*(?P<partner>(?:\d{2}后.{0,8}(?:工作稳定|情绪稳定|都可以|就行)).*)$",
            r"[，,、]\s*(?P<partner>(?:起码\d{2,3}\+|至少\d{2,3}\+|身高\d{2,3}\+).*)$",
        )
        for pattern in split_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            partner_text = str(match.group("partner") or "").strip("，,、 ")
            self_text = text[:match.start()].strip("，,、 ")
            if partner_text:
                return self_text, partner_text
        return text, ""

    @classmethod
    def _split_semantic_chunks(cls, message: str) -> list[tuple[str, str]]:
        text = str(message or "").strip()
        if not text:
            return []
        raw_parts = [part.strip() for part in re.split(r"[，,、；;。！？!?]\s*", text) if part.strip()]
        if len(raw_parts) <= 1:
            return []

        chunks: list[tuple[str, str]] = []
        previous_type = ""
        for part in raw_parts:
            chunk_type = cls._classify_semantic_chunk(part, previous_type=previous_type)
            if not chunk_type:
                continue
            if chunks and chunks[-1][0] == chunk_type:
                chunks[-1] = (chunk_type, f"{chunks[-1][1]}，{part}")
            else:
                chunks.append((chunk_type, part))
            previous_type = chunk_type
        return chunks

    @classmethod
    def _classify_semantic_chunk(cls, chunk_text: str, *, previous_type: str = "") -> str:
        text = str(chunk_text or "").strip()
        if not text:
            return ""
        compact = re.sub(r"\s+", "", text)
        if re.search(r"(?:微信|电话|手机号|联系方式|vx|wx|weixin)|(?:1[3-9]\d{9})", compact, flags=re.IGNORECASE):
            return "contact"
        if re.search(r"(怎么收费|收费|多少钱|价格|费用|流程|怎么安排|靠谱吗|真实吗|正规吗)", compact):
            return "faq"
        if cls._looks_like_partner_chunk(compact, previous_type=previous_type):
            return "partner"
        if cls._looks_like_self_profile_chunk(compact):
            return "self_profile"
        if cls._looks_like_soft_trait_chunk(compact):
            return "soft_trait"
        return ""

    @staticmethod
    def _looks_like_partner_chunk(compact_text: str, *, previous_type: str = "") -> bool:
        if not compact_text:
            return False
        if re.search(r"(?:找对象|找男朋友|找女朋友|想找|想着|期待|遇见|希望|另一半|对象|最好|优先|不要\d{2}|不要|同城|本地|同在|有房有车|能接受)", compact_text):
            return True
        if re.search(r"(?:\d{2}后.{0,8}(?:工作稳定|情绪稳定|都可以|就行)|起码\d{2,3}\+|至少\d{2,3}\+|身高\d{2,3}\+)", compact_text):
            return True
        if previous_type in {"partner", "soft_trait"} and re.search(r"(积极阳光|三观正|情绪稳定|成熟稳重|工作稳定|有房有车|深户|本科|硕士|博士|未婚)", compact_text):
            return True
        return False

    @staticmethod
    def _looks_like_self_profile_chunk(compact_text: str) -> bool:
        if not compact_text:
            return False
        return bool(
            re.search(r"(?:19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁)", compact_text)
            or re.search(r"(女生|男生|女的|男的).{0,6}(?:在|现居|坐标|来自|人在)", compact_text)
            or re.search(r"(?:我在|来自|人在|目前在|现在在|住在|坐标)(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)", compact_text)
            or re.search(r"(本科|大专|硕士|博士|港硕|未婚|单身|离异|已婚|在编|教师|老师|护士|医生|程序员|开发|运营|产品|设计|财务|销售|外贸|年薪|月薪|收入|深户)", compact_text)
        )

    @staticmethod
    def _looks_like_soft_trait_chunk(compact_text: str) -> bool:
        if not compact_text:
            return False
        return bool(re.search(r"([EI]人|喜欢|爱好|旅游|做饭|原生家庭|感情经历|性格|慢热|外向|内向)", compact_text))

    def _attach_chunk_summary_notes(self, frame: TurnSemanticFrame, user_message: str) -> None:
        summaries = self._extract_chunk_summaries(user_message)
        if not summaries:
            return
        notes = list(getattr(frame, "notes", []) or [])
        existing_prefixes = {str(note).split("=", 1)[0] for note in notes if "=" in str(note)}
        for key, value in summaries.items():
            if not value or key in existing_prefixes:
                continue
            notes.append(f"{key}={value}")
        frame.notes = notes

    @classmethod
    def _extract_chunk_summaries(cls, user_message: str) -> dict[str, str]:
        chunks = cls._split_semantic_chunks(user_message)
        if not chunks:
            return {}

        def _unique_join(values: list[str]) -> str:
            ordered: list[str] = []
            seen: set[str] = set()
            for item in values:
                clean = str(item or "").strip()
                if not clean or clean in seen:
                    continue
                seen.add(clean)
                ordered.append(clean)
            return "，".join(ordered)

        partner_parts = [chunk_text for chunk_type, chunk_text in chunks if chunk_type == "partner"]
        soft_parts = [chunk_text for chunk_type, chunk_text in chunks if chunk_type == "soft_trait"]
        summaries: dict[str, str] = {}
        partner_summary = _unique_join(partner_parts)
        soft_profile_summary = _unique_join(soft_parts)
        if partner_summary:
            summaries["partner_summary"] = partner_summary
        if soft_profile_summary:
            summaries["soft_profile_summary"] = soft_profile_summary
        return summaries

    def _append_partner_numeric_preference_observations(
        self,
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        message: str,
    ) -> None:
        if self.semantic_service is None or not hasattr(
            self.semantic_service,
            "_extract_structured_numeric_partner_preference_semantics",
        ):
            return
        semantics = self.semantic_service._extract_structured_numeric_partner_preference_semantics(message)  # noqa: SLF001
        if not isinstance(semantics, list):
            return

        field_map = {
            "height": "partner_pref_height",
            "age": "partner_pref_age",
            "income": "partner_pref_income",
        }
        for item in semantics:
            raw_field = str(item.get("field") or "").strip()
            mapped_field = field_map.get(raw_field)
            if not mapped_field:
                continue
            operator = str(item.get("operator") or "").strip()
            raw_value = str(item.get("value") or "").strip()
            if raw_field == "age" and self._has_self_income_semantics_near_numeric_value(message, raw_value):
                continue
            normalized_value = self._normalize_partner_numeric_preference_value(raw_field, operator, raw_value)
            if not normalized_value:
                continue
            evidence_span = self._find_partner_numeric_evidence_span(message, raw_value, operator)
            self._append_observation(
                observations,
                seen,
                FieldObservation(
                    field=mapped_field,
                    value=normalized_value,
                    normalized_value=normalized_value,
                    scope="partner",
                    owner="partner",
                    evidence_text=message,
                    evidence_span=evidence_span or raw_value or None,
                    confidence=0.94,
                    write_mode="direct_write",
                    source="semantic_partner_numeric_preference",
                    raw_value=raw_value or None,
                    relation=operator or None,
                ),
            )

    @staticmethod
    def _has_self_income_semantics_near_numeric_value(message: str, raw_value: str) -> bool:
        text = str(message or "")
        value = str(raw_value or "").strip()
        if not text or not value:
            return False
        income_pattern = r"(收入|月入|月薪|工资|年薪|年新|年收入|年包|税前|税后|k|K|w|W|万)"
        clause_delimiters = ("，", ",", "、", "；", ";", "。", "！", "？", "!", "?")
        for match in re.finditer(re.escape(value), text):
            clause_start = max(text.rfind(delimiter, 0, match.start()) for delimiter in clause_delimiters)
            right_boundaries = [
                boundary
                for delimiter in clause_delimiters
                if (boundary := text.find(delimiter, match.end())) != -1
            ]
            clause_end = min(right_boundaries) if right_boundaries else len(text)
            clause = text[clause_start + 1:clause_end]
            relative_start = max(0, match.start() - (clause_start + 1))
            prefix_window = clause[max(0, relative_start - 12):relative_start]
            # Only treat the numeric as income-like when the income cue is in the
            # same clause and appears before the number. This keeps
            # "年薪20左右" blocked while allowing "30+的，月入2w+的".
            if re.search(income_pattern, prefix_window):
                return True
        return False

    def _get_extraction_service(self) -> object | None:
        chat_service = getattr(self.semantic_service, "chat_service", None)
        if chat_service is None:
            return None
        return getattr(chat_service, "extraction_service", None)

    def _build_acts(
        self,
        result: TurnUnderstandingResult,
        observations: Iterable[FieldObservation],
    ) -> list[str]:
        acts: list[str] = []
        primary = result.primary_turn_type
        if primary in {"profile_answer", "opening"} and any(obs.scope == "self" for obs in observations):
            acts.append("provide_profile")
        if primary == "contact_answer" or any(obs.scope == "contact" for obs in observations):
            acts.append("provide_contact")
        if any(obs.scope == "partner" for obs in observations):
            acts.append("state_partner_preference")
        if primary == "faq_concern":
            acts.append("ask_service_question")
        if primary == "correction":
            acts.append("correct_profile")
        if primary == "confirmation":
            acts.append("confirm_or_ack")
        if primary == "refusal_boundary_complaint":
            acts.append("set_boundary")
        return acts or ["unknown"]

    def _extract_user_questions(self, message: str) -> list[UserQuestion]:
        text = str(message or "").strip()
        questions: list[UserQuestion] = []
        for topic, pattern in self._QUESTION_TOPIC_PATTERNS:
            if re.search(pattern, text):
                questions.append(UserQuestion(topic=topic, question_text=text, confidence=0.9))
        return questions

    @staticmethod
    def _build_boundaries(result: TurnUnderstandingResult) -> list[str]:
        boundaries: list[str] = []
        if result.primary_turn_type == "refusal_boundary_complaint":
            boundaries.append(result.subtype or "boundary")
        return boundaries

    @staticmethod
    def _resolve_primary_domain(result: TurnUnderstandingResult) -> str:
        primary = result.primary_turn_type
        if primary == "contact_answer":
            return "contact"
        if primary == "faq_concern":
            return "faq"
        if primary == "risk_guard":
            return "risk"
        if primary == "closing_exit":
            return "closing"
        if primary in {"profile_answer", "correction", "confirmation", "opening"}:
            return "profile"
        if primary == "refusal_boundary_complaint":
            return "boundary"
        return "mixed"

    @staticmethod
    def _infer_scope(field_name: str) -> str:
        if field_name in {"phone", "wechat", "contact"}:
            return "contact"
        if field_name.startswith("partner_") or field_name == "partner_requirement":
            return "partner"
        if field_name in {"pricing", "service_flow", "contact_policy"}:
            return "faq"
        return "self"

    def _from_evidence(self, field_name: str, evidence: ResolvedFieldEvidence) -> FieldObservation:
        scope = str(evidence.scope or self._infer_scope(field_name))
        return FieldObservation(
            field=field_name,
            value=evidence.value,
            normalized_value=evidence.value,
            scope=scope,
            owner="self" if scope in {"self", "contact"} else scope,
            evidence_text=evidence.source_text,
            evidence_span=evidence.source_span or None,
            confidence=float(evidence.confidence or 0.0),
            write_mode="direct_write",
            source=evidence.source_type or "legacy_evidence",
        )

    def _from_candidate(self, field_name: str, candidate: SlotCandidate) -> FieldObservation:
        scope = str(getattr(candidate, "scope", "") or self._infer_scope(field_name))
        return FieldObservation(
            field=field_name,
            value=getattr(candidate, "value", None),
            normalized_value=getattr(candidate, "value", None),
            scope=scope,
            owner="self" if scope in {"self", "contact"} else scope,
            evidence_text=getattr(candidate, "source_text", "") or "",
            evidence_span=getattr(candidate, "source_span", None) or None,
            confidence=float(getattr(candidate, "confidence", 0.0) or 0.0),
            write_mode="soft_confirm",
            source=getattr(candidate, "source", None) or "legacy_candidate",
        )

    @staticmethod
    def _append_observation(
        observations: list[FieldObservation],
        seen: set[tuple[str, str, str]],
        observation: FieldObservation,
    ) -> None:
        if observation.field == "partner_requirement" and observation.scope in {"partner", "mixed"}:
            for index, existing in enumerate(observations):
                if existing.field != observation.field or existing.scope != observation.scope:
                    continue
                chosen_value = AISemanticExtractionService._pick_richer_partner_requirement(
                    str(getattr(existing, "normalized_value", "") or ""),
                    str(getattr(observation, "normalized_value", "") or ""),
                )
                if chosen_value == str(getattr(existing, "normalized_value", "") or ""):
                    return
                existing_key = (existing.field, str(existing.normalized_value), existing.scope)
                if existing_key in seen:
                    seen.remove(existing_key)
                observations[index] = observation
                seen.add((observation.field, str(observation.normalized_value), observation.scope))
                return
        key = (observation.field, str(observation.normalized_value), observation.scope)
        if key in seen:
            return
        seen.add(key)
        observations.append(observation)

    @staticmethod
    def _extract_first_integer(value: object) -> int | None:
        match = re.search(r"\d{2,3}", str(value or ""))
        if not match:
            return None
        return int(match.group(0))

    @staticmethod
    def _normalize_partner_numeric_preference_value(field_name: str, operator: str, raw_value: str) -> str:
        value = str(raw_value or "").strip()
        if field_name == "height":
            if not value:
                return ""
            if operator == "lower_bound":
                return f"身高{value}cm以上"
            if operator == "around":
                return f"身高{value}cm左右"
            return f"身高{value}cm"
        if field_name == "age":
            if not value:
                return ""
            if operator == "lower_bound":
                return f"年龄{value}以上"
            if operator == "around":
                return f"年龄{value}左右"
            return f"年龄{value}"
        if field_name == "income":
            if operator == "not_too_low":
                return "收入别太低"
            if not value:
                return ""
            if operator == "lower_bound":
                return f"收入{value}以上"
            if operator == "around":
                return f"收入{value}左右"
            return f"收入{value}"
        return ""

    @staticmethod
    def _find_partner_numeric_evidence_span(message: str, raw_value: str, operator: str) -> str | None:
        text = str(message or "")
        value = str(raw_value or "").strip()
        if not text:
            return None
        if operator == "not_too_low":
            match = re.search(r"(收入过得去就行|收入过得去就好|收入别太低)", text)
            return match.group(1) if match else None
        if not value:
            return None
        match = re.search(rf"([^\s，,。！？!?]{{0,4}}{re.escape(value)}[^\s，,。！？!?]{{0,4}})", text)
        if match:
            return match.group(1)
        return value

    @staticmethod
    def _looks_like_profile_intro(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        return bool(
            re.search(r"(男生|女生|男的|女的|本科|大专|硕士|博士|未婚|离异|单身)", text)
            or re.search(r"(?:深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)(?:南山|福田|宝安|龙岗|龙华)?", text)
            or re.search(r"(教师|老师|程序员|开发|运营|产品|设计|财务|医生|销售|行政|客服)", text)
            or re.search(r"(?<!\d)(1[4-9]\d)\s*/\s*([5-9]\d|1\d{2})(?!\d)", text)
        )

    def _normalize_occupation_candidate(self, occupation: str) -> str:
        text = str(occupation or "").strip()
        if not text:
            return ""
        if self.semantic_service is not None and hasattr(self.semantic_service, "_normalize_occupation_candidate"):
            normalized = str(self.semantic_service._normalize_occupation_candidate(text) or "").strip()  # noqa: SLF001
            if normalized in {"在编女教师", "在编男教师"}:
                return "在编教师"
            return normalized
        text = re.sub(r"^(男|女)", "", text)
        text = text.replace("在编女教师", "在编教师").replace("在编男教师", "在编教师")
        if text in {"教师", "老师", "在编教师"}:
            return "在编教师" if "在编" in str(occupation or "") else "教师"
        return text

    def _is_low_quality_occupation_text(self, occupation: str) -> bool:
        text = str(occupation or "").strip()
        if not text:
            return True
        if self.semantic_service is not None and hasattr(self.semantic_service, "_is_low_quality_occupation_text"):
            return bool(self.semantic_service._is_low_quality_occupation_text(text))  # noqa: SLF001
        return text in {"可以", "可以哒", "了解", "先了解", "机构", "资源"}

    def _allows_self_projection_from_legacy(self, *, message: str, result: TurnUnderstandingResult) -> bool:
        if self._looks_like_profile_intro(message):
            return True
        return result.primary_turn_type != "faq_concern"
