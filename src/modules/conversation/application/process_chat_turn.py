from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Dict
from uuid import uuid4

from src.models.requests import ChatRequest
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput
from src.modules.shared.models.use_case_models import ProcessChatTurnCommand, ProcessChatTurnResult
from src.modules.conversation_understanding.domain.async_semantic_backfill_policy_service import (
    AsyncSemanticBackfillDecision,
    AsyncSemanticBackfillPolicyService,
)

if TYPE_CHECKING:
    from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)


class ProcessChatTurnUseCase:
    """Behavior-preserving extraction of the main chat turn orchestration."""

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service
        self.async_semantic_backfill_policy_service = AsyncSemanticBackfillPolicyService()
        self._async_backfill_tasks: set[asyncio.Task] = set()
        self._async_backfill_accounts_inflight: set[str] = set()
        self._async_backfill_cooldown_until_by_account: dict[str, float] = {}
        self._async_backfill_recent_fingerprints: dict[str, dict[str, float]] = {}
        self._async_backfill_obs: dict[str, int] = {
            "evaluated": 0,
            "scheduled": 0,
            "skip": 0,
            "success": 0,
            "failed": 0,
        }

    @staticmethod
    def _sync_payload_response(payload: Dict[str, Any], final_response: str) -> Dict[str, Any]:
        """确保用户可见回复和主流程最终回复完全一致。"""
        if not isinstance(payload, dict):
            return payload
        payload_response = str(payload.get("response") or "")
        canonical_response = str(final_response or "")
        if payload_response != canonical_response:
            logger.warning(
                "[响应一致性] payload.response 与 final_response 不一致，已强制对齐: "
                f"payload_len={len(payload_response)}, final_len={len(canonical_response)}"
            )
            payload["response"] = canonical_response
            meta = payload.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["response_synced"] = True
            payload["meta"] = meta
        return payload

    @staticmethod
    def _sync_decision_profile_contact_state(source_profile: Any, decision_profile: Any) -> Any:
        """拒绝检测会更新真实画像；提示词构建前需要把联系方式状态同步到决策副本。"""
        if decision_profile is None or source_profile is None:
            return decision_profile
        contact_fields = (
            "phone",
            "wechat",
            "contact",
            "phone_collected",
            "wechat_collected",
            "rejected_phone",
            "rejected_wechat",
            "phone_ask_count",
            "wechat_ask_count",
            "phone_effective_ask_count",
            "wechat_effective_ask_count",
            "phone_invalid_input_count",
            "wechat_invalid_input_count",
            "phone_invalid_input_closed",
            "wechat_invalid_input_closed",
            "last_contact_request_type",
            "contact_complete",
            "spam_user",
            "conversation_ended",
            "is_hongkong_user",
        )
        for field in contact_fields:
            if hasattr(source_profile, field) and hasattr(decision_profile, field):
                setattr(decision_profile, field, getattr(source_profile, field))
        return decision_profile

    @staticmethod
    def _to_command(request: ChatRequest | ProcessChatTurnCommand) -> ProcessChatTurnCommand:
        if isinstance(request, ProcessChatTurnCommand):
            return request
        return ProcessChatTurnCommand(
            question=request.question,
            account_id=request.accountId,
            dialog_id=request.dialogId,
            sex=request.sex,
            timestamp=request.timestamp,
        )

    async def execute_command(self, command: ProcessChatTurnCommand) -> ProcessChatTurnResult:
        payload = await self.execute(command)
        return ProcessChatTurnResult(
            success=bool(payload.get("success", False)),
            response=str(payload.get("response") or ""),
            dialog_id=payload.get("dialogId"),
            payload=payload,
        )

    async def execute(self, request: ChatRequest | ProcessChatTurnCommand) -> Dict[str, Any]:
        command = self._to_command(request)
        request = ChatRequest(
            question=command.question,
            accountId=command.account_id,
            dialogId=command.dialog_id,
            sex=command.sex,
            timestamp=command.timestamp,
        )
        start_time = time.perf_counter()
        account_id = request.accountId
        trace_id = f"{account_id}:{(request.dialogId or 'no_dialog')}:{uuid4().hex[:8]}"
        stage_ms: Dict[str, int] = {}
        prompt_chars = 0
        extracted_fields_count = 0
        route_name = "unknown"
        response_channel = "unknown"
        turn_understanding = None
        pre_generation_resolution = None
        refusal_detection_done = False
        conversation_context: Dict[str, Any] = {}

        def _mark(stage: str, begin: float) -> None:
            stage_ms[stage] = int((time.perf_counter() - begin) * 1000)

        def _log_turn(route: str, ok: bool, error: str = "") -> None:
            total_ms = int((time.perf_counter() - start_time) * 1000)
            stages = ",".join(f"{k}:{v}" for k, v in stage_ms.items()) or "-"
            alignment_obs = getattr(self.chat_service, "_last_turn_alignment_obs", None)
            if not isinstance(alignment_obs, dict):
                alignment_obs = {}
            alignment_ask_field = str(alignment_obs.get("ask_field") or "-")
            alignment_asked_fields = str(alignment_obs.get("asked_fields") or "-")
            alignment_mismatch = 1 if bool(alignment_obs.get("ask_field_mismatch_detected", False)) else 0
            alignment_rewritten = 1 if bool(alignment_obs.get("ask_field_mismatch_rewritten", False)) else 0
            alignment_reask_after_commit = 1 if bool(alignment_obs.get("reask_after_commit_detected", False)) else 0
            logger.info(
                "[obs.turn] "
                f"trace_id={trace_id} account_id={account_id} dialog_id={request.dialogId or 'na'} "
                f"ok={1 if ok else 0} route={route} response_channel={response_channel} "
                f"prompt_chars={prompt_chars} extracted_fields={extracted_fields_count} "
                f"occupation={getattr(user_profile, 'occupation', None) or '-'} "
                f"occupation_inference_candidate={getattr(user_profile, 'occupation_inference_candidate', None) or '-'} "
                f"total_ms={total_ms} stages={stages} "
                f"pre_gen_source={getattr(pre_generation_resolution, 'source', '') or '-'} "
                f"pre_gen_reason={getattr(pre_generation_resolution, 'transition_reason', '') or '-'} "
                f"pre_gen_fields={','.join(getattr(pre_generation_resolution, 'resolved_fields', []) or []) or '-'} "
                f"ask_field={alignment_ask_field} asked_fields={alignment_asked_fields} "
                f"ask_field_mismatch={alignment_mismatch} ask_field_rewritten={alignment_rewritten} "
                f"reask_after_commit={alignment_reask_after_commit} "
                f"error={error or '-'}"
            )

        def _attach_route_meta(payload: Dict[str, Any], route: str) -> Dict[str, Any]:
            if not isinstance(payload, dict):
                return payload
            meta = payload.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["route"] = route
            if turn_understanding is not None:
                meta["turn_understanding"] = turn_understanding.to_dict()
            if pre_generation_resolution is not None:
                meta["pre_generation_resolution"] = asdict(pre_generation_resolution)
            payload["meta"] = meta
            return payload

        logger.info(f"[⏱️ 性能] 开始处理请求: account_id={account_id}, trace_id={trace_id}")
        self.chat_service._last_unified_generation_record = None
        self.chat_service._last_validation_feedback_meta = None
        self.chat_service._last_turn_alignment_obs = None

        try:
            t0 = time.perf_counter()
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _mark("profile_load", t0)

            if request.sex in ["男", "女"] and not user_profile.sex:
                t0 = time.perf_counter()
                user_profile.sex = request.sex
                user_profile.collection_progress["sex"] = True
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                _mark("prefill_sex", t0)

            is_empty = user_profile.is_empty()
            t0 = time.perf_counter()
            message_count = await self.chat_service.dialogue_manager.get_message_count(account_id)
            _mark("message_count", t0)
            is_new_user_session = is_empty and message_count == 0
            if is_new_user_session:
                t0 = time.perf_counter()
                await self.chat_service.input_fallback_service.reset_nonsense_count(account_id)
                user_profile.conversation_ended = False
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                _mark("new_session_reset", t0)

            t0 = time.perf_counter()
            already_ended = await self.chat_service.maybe_build_already_ended_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                dialog_id=request.dialogId,
                is_new_user_session=is_new_user_session,
            )
            if already_ended is not None:
                route_name = already_ended.route_name
                response_channel = "model"
                _mark("state_update", t0)
                payload = self._sync_payload_response(already_ended.payload or {}, already_ended.final_response)
                payload = _attach_route_meta(payload, route_name)
                self._schedule_async_semantic_backfill(
                    route_name=route_name,
                    account_id=account_id,
                    user_message=request.question,
                    dialog_id=request.dialogId,
                    message_count=message_count,
                    conversation_context=conversation_context,
                    turn_understanding=turn_understanding,
                )
                _log_turn(route_name, ok=True)
                return payload

            t0 = time.perf_counter()
            _mark("rule_check", t0)

            t0 = time.perf_counter()
            conversation_context = await self.chat_service.dialogue_manager.get_conversation_context(account_id)
            _mark("context_load", t0)
            recent_responses = conversation_context.get("recent_responses") or []
            last_response = str(recent_responses[-1]).strip() if recent_responses else ""
            turn_prep = await self.chat_service.prepare_turn_execution(
                user_message=request.question,
                user_profile=user_profile,
                conversation_context=conversation_context,
                last_response=last_response,
                message_count=message_count,
            )
            turn_understanding = turn_prep.understanding
            pre_generation_resolution = turn_prep.pre_generation_resolution
            decision_profile = turn_prep.decision_profile
            turn_decision = turn_prep.turn_decision
            response_channel = turn_prep.response_channel
            logger.info(f"[决策器] account_id={account_id}, decision={turn_decision.to_log_dict()}")

            if getattr(turn_decision, "risk", None) != "high_risk":
                t0 = time.perf_counter()
                await self.chat_service.handle_refusal_detection(
                    request.question,
                    account_id,
                    user_profile,
                    understanding_result=turn_understanding,
                )
                decision_profile = self._sync_decision_profile_contact_state(user_profile, decision_profile)
                refusal_detection_done = True
                _mark("refusal_detection", t0)

            t0 = time.perf_counter()
            short_route, short_payload, user_profile = await self.chat_service.maybe_build_pre_generation_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                dialog_id=request.dialogId,
                turn_decision=turn_decision,
                turn_understanding=turn_understanding,
                message_count=message_count,
            )
            if short_payload is not None and short_route is not None:
                _mark("state_update", t0)
                payload = self._sync_payload_response(short_payload, str(short_payload.get("response") or ""))
                payload = _attach_route_meta(payload, short_route)
                self._schedule_async_semantic_backfill(
                    route_name=short_route,
                    account_id=account_id,
                    user_message=request.question,
                    dialog_id=request.dialogId,
                    message_count=message_count,
                    conversation_context=conversation_context,
                    turn_understanding=turn_understanding,
                )
                _log_turn(short_route, True)
                return payload

            self.chat_service.dialogue_manager.update_user_sex(user_profile)
            if not refusal_detection_done:
                t0 = time.perf_counter()
                await self.chat_service.handle_refusal_detection(
                    request.question,
                    account_id,
                    user_profile,
                    understanding_result=turn_understanding,
                )
                decision_profile = self._sync_decision_profile_contact_state(user_profile, decision_profile)
                _mark("refusal_detection", t0)

            t0 = time.perf_counter()
            quick_faq_payload = await self.chat_service.maybe_build_quick_faq_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                dialog_id=request.dialogId,
                turn_decision=turn_decision,
                turn_understanding=turn_understanding,
                decision_profile=decision_profile,
                conversation_context=conversation_context,
            )
            if quick_faq_payload is not None:
                route_name = "quick_faq"
                payload = quick_faq_payload
                _mark("state_update", t0)
                payload = self._sync_payload_response(payload, str(payload.get("response") or ""))
                payload = _attach_route_meta(payload, route_name)
                self._schedule_async_semantic_backfill(
                    route_name=route_name,
                    account_id=account_id,
                    user_message=request.question,
                    dialog_id=request.dialogId,
                    message_count=message_count,
                    conversation_context=conversation_context,
                    turn_understanding=turn_understanding,
                )
                _log_turn(route_name, True)
                return payload

            # Phase 2: FAQ/边界/complaint 后的 bridge-back 检查（repair_mode 下禁用）
            in_repair_mode = turn_decision.in_repair_mode
            bridge_prefix = await self.chat_service.consume_bridge_back_prefix(
                account_id=account_id,
                user_profile=user_profile,
                in_repair_mode=in_repair_mode,
            )

            t0 = time.perf_counter()
            main_prompt = self.chat_service.build_generation_prompt(
                user_message=request.question,
                user_profile=decision_profile,
                conversation_context=conversation_context,
                turn_decision=turn_decision,
                understanding_result=turn_understanding,
            )
            _mark("prompt_build", t0)
            prompt_chars = len(main_prompt or "")

            t0 = time.perf_counter()
            await self.chat_service.user_service.save_user_profile(account_id, user_profile)
            _mark("profile_save_pre_ai", t0)

            t0 = time.perf_counter()
            generation_phase = await self.chat_service.run_generation_collection_phase(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                dialog_id=request.dialogId,
                main_prompt=main_prompt,
                last_response=last_response,
                message_count=message_count,
                understanding_result=turn_understanding,
                conversation_context=conversation_context,
                turn_decision=turn_decision,
            )
            stage_ms["ai_call"] = generation_phase.ai_call_ms
            stage_ms["extract_fuse"] = generation_phase.extract_fuse_ms
            stage_ms["collection_process"] = generation_phase.collection_process_ms
            user_profile = generation_phase.user_profile
            collection_result = generation_phase.collection_result
            ai_response = generation_phase.ai_response
            turn_decision = generation_phase.turn_decision
            response_channel = generation_phase.response_channel
            extracted_fields_count = generation_phase.extracted_fields_count
            contact_gate_before = generation_phase.contact_gate_before
            infra_fail = generation_phase.infra_fail
            infra_fail_reason = generation_phase.infra_fail_reason
            t0 = time.perf_counter()
            preset_payload = generation_phase.preset_payload
            if preset_payload is not None:
                route_name = "preset_response"
                final_response, payload = preset_payload
                _mark("state_update", t0)
                payload = _attach_route_meta(payload, route_name)
                self._schedule_async_semantic_backfill(
                    route_name=route_name,
                    account_id=account_id,
                    user_message=request.question,
                    dialog_id=request.dialogId,
                    message_count=message_count,
                    conversation_context=conversation_context,
                    turn_understanding=turn_understanding,
                )
                _log_turn(route_name, True)
                return payload
            response_to_clean = await self.chat_service.build_enhanced_response_to_clean(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                collection_result=collection_result,
                ai_response=ai_response,
            )
            previous_asked_field = user_profile.last_asked_field
            previous_asked_side_field = user_profile.last_asked_side_field
            t0 = time.perf_counter()
            final_response, delivery_ok, user_profile = await self.chat_service.finalize_generated_response(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                turn_decision=turn_decision,
                turn_understanding=turn_understanding,
                collection_result=collection_result,
                response_to_clean=response_to_clean,
                ai_response=ai_response,
                bridge_prefix=bridge_prefix,
                contact_gate_before=contact_gate_before,
                message_count=message_count,
            )
            _mark("response_finalize", t0)

            t0 = time.perf_counter()
            final_response, user_profile = await self.chat_service.sync_post_delivery_state(
                account_id=account_id,
                user_profile=user_profile,
                user_message=request.question,
                final_response=final_response,
                ai_response=ai_response,
                delivery_ok=delivery_ok,
                turn_decision=turn_decision,
                collection_result=collection_result,
                message_count=message_count,
                previous_asked_field=previous_asked_field,
                previous_asked_side_field=previous_asked_side_field,
            )
            _mark("state_update", t0)
            _mark("profile_reload", t0)
            _mark("progress_counters", t0)
            total_duration = time.perf_counter() - start_time
            logger.info(f"[⏱️ 性能] 请求处理完成: account_id={account_id}, 总耗时={total_duration:.3f}秒")
            route_name = "model"
            payload = await self.chat_service.build_final_turn_payload(
                account_id=account_id,
                user_profile=user_profile,
                final_response=final_response,
                collection_result=collection_result,
                dialog_id=request.dialogId,
                route_name=route_name,
                infra_fail=infra_fail,
                infra_fail_reason=infra_fail_reason,
            )
            payload = self._sync_payload_response(payload, final_response)
            payload = _attach_route_meta(payload, route_name)
            self._schedule_async_semantic_backfill(
                route_name=route_name,
                account_id=account_id,
                user_message=request.question,
                dialog_id=request.dialogId,
                message_count=message_count,
                conversation_context=conversation_context,
                turn_understanding=turn_understanding,
            )
            _log_turn(route_name, True)
            return payload
        except Exception as e:
            total_duration = time.perf_counter() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            _log_turn(route_name or "error", False, str(e))
            from src.core.error_handler import handle_error

            error_response = handle_error(e, context="chat", user_id=account_id)
            return self.chat_service.build_error_response(
                error_response.get("error", "处理失败"),
                request.dialogId,
                error_code=error_response.get("error_code"),
                details=error_response.get("details"),
            )

    @staticmethod
    def _env_enabled(name: str, default: bool) -> bool:
        raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
        if raw in {"0", "false", "no", "off", "disable", "disabled"}:
            return False
        if raw in {"1", "true", "yes", "on", "enable", "enabled"}:
            return True
        return default

    @staticmethod
    def _env_positive_float(name: str, default: float, min_value: float = 1.0) -> float:
        raw = str(os.getenv(name, str(default)) or "").strip()
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = default
        return max(min_value, value)

    def _build_async_backfill_policy_decision(
        self,
        *,
        route_name: str,
        user_message: str,
        turn_understanding: Any,
    ) -> AsyncSemanticBackfillDecision:
        return self.async_semantic_backfill_policy_service.decide(
            route_name=route_name,
            user_message=user_message,
            turn_understanding=turn_understanding,
        )

    def _async_backfill_runtime_skip_reason(
        self,
        *,
        account_id: str,
        decision: AsyncSemanticBackfillDecision,
    ) -> str | None:
        if not self._env_enabled("UNIFIED_TURN_ASYNC_BACKFILL_ENABLED", True):
            return "env_disabled"
        if getattr(self.chat_service, "unified_turn_understanding_service", None) is None:
            return "missing_unified_service"
        if not hasattr(self.chat_service, "collection_extraction_service"):
            return "missing_collection_extraction_service"
        if account_id in self._async_backfill_accounts_inflight:
            return "inflight"

        now = time.monotonic()
        cooldown_until = float(self._async_backfill_cooldown_until_by_account.get(account_id, 0.0) or 0.0)
        if cooldown_until > now:
            remaining = max(1, int(cooldown_until - now))
            return f"cooldown:{remaining}s"
        self._async_backfill_cooldown_until_by_account.pop(account_id, None)

        fingerprint = str(decision.fingerprint or "").strip()
        if fingerprint:
            self._prune_async_backfill_recent_fingerprints(account_id=account_id, now=now)
            account_fingerprints = self._async_backfill_recent_fingerprints.get(account_id, {})
            if fingerprint in account_fingerprints:
                return "duplicate_fingerprint"
        return None

    def _prune_async_backfill_recent_fingerprints(self, *, account_id: str, now: float | None = None) -> None:
        ttl_seconds = self._env_positive_float(
            "UNIFIED_TURN_ASYNC_BACKFILL_FINGERPRINT_TTL_SECONDS",
            600.0,
            min_value=1.0,
        )
        current = float(now if now is not None else time.monotonic())
        account_fingerprints = dict(self._async_backfill_recent_fingerprints.get(account_id, {}) or {})
        if not account_fingerprints:
            self._async_backfill_recent_fingerprints.pop(account_id, None)
            return
        fresh = {
            fingerprint: ts
            for fingerprint, ts in account_fingerprints.items()
            if current - float(ts or 0.0) <= ttl_seconds
        }
        if fresh:
            self._async_backfill_recent_fingerprints[account_id] = fresh
        else:
            self._async_backfill_recent_fingerprints.pop(account_id, None)

    def _remember_async_backfill_fingerprint(self, *, account_id: str, fingerprint: str) -> None:
        normalized = str(fingerprint or "").strip()
        if not normalized:
            return
        now = time.monotonic()
        self._prune_async_backfill_recent_fingerprints(account_id=account_id, now=now)
        account_fingerprints = dict(self._async_backfill_recent_fingerprints.get(account_id, {}) or {})
        account_fingerprints[normalized] = now
        self._async_backfill_recent_fingerprints[account_id] = account_fingerprints

    def _arm_async_backfill_cooldown(self, *, account_id: str, reason: str) -> None:
        cooldown_seconds = self._env_positive_float(
            "UNIFIED_TURN_ASYNC_BACKFILL_COOLDOWN_SECONDS",
            300.0,
            min_value=1.0,
        )
        if str(reason or "").strip() not in {"ai_not_ready", "exception", "task_exception"}:
            return
        self._async_backfill_cooldown_until_by_account[account_id] = time.monotonic() + cooldown_seconds

    def _record_async_backfill_observability(
        self,
        *,
        event: str,
        account_id: str,
        route_name: str = "",
        reason: str = "",
        latency_ms: int | None = None,
        applied: int | None = None,
        target_fields: list[str] | None = None,
        fingerprint: str = "",
    ) -> None:
        event_key = str(event or "").strip()
        if event_key in self._async_backfill_obs:
            self._async_backfill_obs[event_key] += 1
        logger.info(
            "[async_semantic_backfill.obs] account_id=%s route=%s event=%s reason=%s target_fields=%s fingerprint=%s latency_ms=%s applied=%s evaluated=%s scheduled=%s skip=%s success=%s failed=%s",
            account_id,
            route_name or "-",
            event_key or "-",
            reason or "-",
            ",".join(str(item).strip() for item in list(target_fields or []) if str(item).strip()) or "-",
            fingerprint or "-",
            latency_ms if latency_ms is not None else "-",
            applied if applied is not None else "-",
            self._async_backfill_obs.get("evaluated", 0),
            self._async_backfill_obs.get("scheduled", 0),
            self._async_backfill_obs.get("skip", 0),
            self._async_backfill_obs.get("success", 0),
            self._async_backfill_obs.get("failed", 0),
        )

    async def _sync_async_backfill_summary(
        self,
        *,
        account_id: str,
        status: str,
        reason: str,
        latency_ms: int,
        applied_fields: list[str] | None = None,
        semantic_source: str | None = None,
    ) -> None:
        try:
            profile = await self.chat_service.user_service.get_user_profile(account_id)
        except Exception:  # noqa: BLE001
            return

        summary = dict(getattr(profile, "last_semantic_summary", {}) or {})
        payload = {
            "status": str(status or "").strip() or "unknown",
            "reason": str(reason or "").strip() or "-",
            "latency_ms": max(0, int(latency_ms or 0)),
            "applied_fields": [str(item).strip() for item in list(applied_fields or []) if str(item).strip()],
            "semantic_source": str(semantic_source or "").strip() or "-",
            "updated_at_ms": int(time.time() * 1000),
        }
        summary["async_backfill"] = payload
        profile.set_last_semantic_summary(summary)
        try:
            await self.chat_service.user_service.save_user_profile(account_id, profile)
        except Exception:  # noqa: BLE001
            logger.warning("[async_semantic_backfill] failed to persist summary: account_id=%s", account_id)

    def _schedule_async_semantic_backfill(
        self,
        *,
        route_name: str,
        account_id: str,
        user_message: str,
        dialog_id: str | None,
        message_count: int,
        conversation_context: Dict[str, Any],
        turn_understanding: Any,
    ) -> None:
        decision = self._build_async_backfill_policy_decision(
            route_name=route_name,
            user_message=user_message,
            turn_understanding=turn_understanding,
        )
        self._record_async_backfill_observability(
            event="evaluated",
            account_id=account_id,
            route_name=route_name,
            reason=decision.reason,
            target_fields=decision.target_fields,
            fingerprint=decision.fingerprint,
        )
        if not decision.should_schedule:
            self._record_async_backfill_observability(
                event="skip",
                account_id=account_id,
                route_name=route_name,
                reason=decision.reason,
                target_fields=decision.target_fields,
                fingerprint=decision.fingerprint,
            )
            return
        skip_reason = self._async_backfill_runtime_skip_reason(account_id=account_id, decision=decision)
        if skip_reason is not None:
            self._record_async_backfill_observability(
                event="skip",
                account_id=account_id,
                route_name=route_name,
                reason=skip_reason,
                target_fields=decision.target_fields,
                fingerprint=decision.fingerprint,
            )
            return
        timeout_seconds = self._env_positive_float(
            "UNIFIED_TURN_ASYNC_BACKFILL_AI_TIMEOUT_SECONDS",
            8.0,
            min_value=2.0,
        )
        self._async_backfill_accounts_inflight.add(account_id)
        self._remember_async_backfill_fingerprint(account_id=account_id, fingerprint=decision.fingerprint)
        task = asyncio.create_task(
            self._run_async_semantic_backfill(
                account_id=account_id,
                user_message=user_message,
                dialog_id=dialog_id,
                message_count=message_count,
                conversation_context=dict(conversation_context or {}),
                timeout_seconds=timeout_seconds,
                started_at=time.perf_counter(),
            ),
            name=f"async-semantic-backfill:{account_id}",
        )
        self._record_async_backfill_observability(
            event="scheduled",
            account_id=account_id,
            route_name=route_name,
            reason=decision.reason,
            target_fields=decision.target_fields,
            fingerprint=decision.fingerprint,
        )
        self._async_backfill_tasks.add(task)
        task.add_done_callback(self._on_async_backfill_task_done)

    def _on_async_backfill_task_done(self, task: asyncio.Task) -> None:
        self._async_backfill_tasks.discard(task)
        try:
            result = task.result()
        except asyncio.CancelledError:
            task_name = str(getattr(task, "get_name", lambda: "")() or "")
            account_id = task_name.split(":", 1)[1] if task_name.startswith("async-semantic-backfill:") else ""
            if account_id:
                self._async_backfill_accounts_inflight.discard(account_id)
            logger.info("[async_semantic_backfill] task cancelled: account_id=%s", account_id or "-")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("[async_semantic_backfill] task failed: %s", exc)
            self._record_async_backfill_observability(event="failed", account_id="-", reason="task_exception")
            return
        account_id = str((result or {}).get("account_id") or "")
        outcome = str((result or {}).get("outcome") or "").strip()
        reason = str((result or {}).get("reason") or "").strip()
        latency_ms = int((result or {}).get("latency_ms") or 0)
        applied = int((result or {}).get("applied") or 0)
        if outcome == "success":
            if account_id:
                self._async_backfill_cooldown_until_by_account.pop(account_id, None)
            self._record_async_backfill_observability(
                event="success",
                account_id=account_id or "-",
                reason=reason,
                latency_ms=latency_ms,
                applied=applied,
            )
        elif outcome == "failed":
            if account_id:
                self._arm_async_backfill_cooldown(account_id=account_id, reason=reason or "unknown")
            self._record_async_backfill_observability(
                event="failed",
                account_id=account_id or "-",
                reason=reason or "unknown",
                latency_ms=latency_ms,
                applied=applied,
            )
        if account_id:
            self._async_backfill_accounts_inflight.discard(account_id)

    async def _run_async_semantic_backfill(
        self,
        *,
        account_id: str,
        user_message: str,
        dialog_id: str | None,
        message_count: int,
        conversation_context: Dict[str, Any],
        timeout_seconds: float,
        started_at: float,
    ) -> Dict[str, Any]:
        try:
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            get_last_response = getattr(self.chat_service.dialogue_manager, "get_last_response", None)
            if callable(get_last_response):
                last_response = await get_last_response(account_id) or ""
            else:
                last_response = ""
            pending_confirmation_field = "sex" if getattr(user_profile, "pending_sex_confirmation", None) else None
            in_contact_flow = bool(
                getattr(user_profile, "pending_contact_field", None)
                or (
                    getattr(user_profile, "last_contact_request_type", None)
                    and not bool(getattr(user_profile, "contact_complete", False))
                )
            )
            turn_input = TurnUnderstandingInput(
                user_message=user_message,
                last_response=last_response,
                message_count=max(1, int(message_count or 0)),
                user_profile=user_profile,
                conversation_context=dict(conversation_context or {}),
                in_contact_flow=in_contact_flow,
                pending_confirmation_field=pending_confirmation_field,
            )
            understanding = await self.chat_service.unified_turn_understanding_service.analyze(
                turn_input,
                force_ai=True,
                ai_timeout_seconds=timeout_seconds,
            )
            semantic_frame = getattr(understanding, "semantic_frame", None)
            semantic_source = str(getattr(semantic_frame, "source", "") or "").strip()
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            if semantic_source != "ai_structured_extraction":
                logger.info(
                    "[async_semantic_backfill] skip apply: account_id=%s reason=ai_not_ready semantic_source=%s",
                    account_id,
                    semantic_source or "-",
                )
                await self._sync_async_backfill_summary(
                    account_id=account_id,
                    status="skipped",
                    reason="ai_not_ready",
                    latency_ms=latency_ms,
                    applied_fields=[],
                    semantic_source=semantic_source or "-",
                )
                return {
                    "account_id": account_id,
                    "applied": 0,
                    "reason": "ai_not_ready",
                    "outcome": "failed",
                    "latency_ms": latency_ms,
                }

            latest_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _, collection_result, _ = await self.chat_service.collection_extraction_service.run_extraction(
                account_id=account_id,
                user_profile=latest_profile,
                extracted_data={},
                user_message=user_message,
                extraction_meta={},
                turn_id=max(1, int(message_count or 0)) + 1,
                understanding_result=understanding,
            )
            applied_fields = [
                str(item.get("field") or "").strip()
                for item in list((collection_result or {}).get("all_fields", []) or [])
                if isinstance(item, dict) and str(item.get("field") or "").strip()
            ]
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            await self._sync_async_backfill_summary(
                account_id=account_id,
                status="success",
                reason="ok",
                latency_ms=latency_ms,
                applied_fields=applied_fields,
                semantic_source=semantic_source or "-",
            )
            logger.info(
                "[async_semantic_backfill] applied: account_id=%s dialog_id=%s fields=%s latency_ms=%s",
                account_id,
                dialog_id or "-",
                ",".join(applied_fields) or "-",
                latency_ms,
            )
            return {
                "account_id": account_id,
                "applied": len(applied_fields),
                "reason": "ok",
                "outcome": "success",
                "latency_ms": latency_ms,
            }
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            logger.warning("[async_semantic_backfill] failed: account_id=%s error=%s", account_id, exc)
            await self._sync_async_backfill_summary(
                account_id=account_id,
                status="failed",
                reason="exception",
                latency_ms=latency_ms,
                applied_fields=[],
                semantic_source="-",
            )
            return {
                "account_id": account_id,
                "applied": 0,
                "reason": "exception",
                "outcome": "failed",
                "latency_ms": latency_ms,
            }
        finally:
            self._async_backfill_accounts_inflight.discard(account_id)
