from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict
from uuid import uuid4

from src.models.requests import ChatRequest
from src.modules.shared.models.use_case_models import ProcessChatTurnCommand, ProcessChatTurnResult

if TYPE_CHECKING:
    from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)


class ProcessChatTurnUseCase:
    """Behavior-preserving extraction of the main chat turn orchestration."""

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service

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

        def _mark(stage: str, begin: float) -> None:
            stage_ms[stage] = int((time.perf_counter() - begin) * 1000)

        def _log_turn(route: str, ok: bool, error: str = "") -> None:
            total_ms = int((time.perf_counter() - start_time) * 1000)
            stages = ",".join(f"{k}:{v}" for k, v in stage_ms.items()) or "-"
            logger.info(
                "[obs.turn] "
                f"trace_id={trace_id} account_id={account_id} dialog_id={request.dialogId or 'na'} "
                f"ok={1 if ok else 0} route={route} response_channel={response_channel} "
                f"prompt_chars={prompt_chars} extracted_fields={extracted_fields_count} "
                f"total_ms={total_ms} stages={stages} error={error or '-'}"
            )

        def _attach_route_meta(payload: Dict[str, Any], route: str) -> Dict[str, Any]:
            if not isinstance(payload, dict):
                return payload
            meta = payload.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["route"] = route
            payload["meta"] = meta
            return payload

        logger.info(f"[⏱️ 性能] 开始处理请求: account_id={account_id}, trace_id={trace_id}")

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
            is_first_user_turn = message_count == 0
            if is_new_user_session:
                t0 = time.perf_counter()
                await self.chat_service.input_fallback_service.reset_nonsense_count(account_id)
                user_profile.conversation_ended = False
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                _mark("new_session_reset", t0)

            if user_profile.conversation_ended and not is_new_user_session:
                final_response = self.chat_service.ending_service.get_ending_response("already_ended") or ""
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                route_name = "already_ended"
                response_channel = "model"
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)

                response_payload = {
                    "response": final_response,
                    "final_response": final_response,
                    "profile": user_profile.to_dict(),
                    "meta": {"route": "already_ended"},
                    "user_profile": user_profile.to_dict(),
                }
                response_payload = _attach_route_meta(response_payload, route_name)
                _log_turn(route_name, ok=True)
                return response_payload

            t0 = time.perf_counter()
            _mark("rule_check", t0)

            t0 = time.perf_counter()
            conversation_context = await self.chat_service.dialogue_manager.get_conversation_context(account_id)
            _mark("context_load", t0)
            recent_responses = conversation_context.get("recent_responses") or []
            last_response = str(recent_responses[-1]).strip() if recent_responses else ""
            decision_profile = self.chat_service._build_shadow_profile_for_decision(  # noqa: SLF001
                user_profile,
                request.question,
                last_response=last_response,
            )
            turn_decision = self.chat_service._build_turn_decision(  # noqa: SLF001
                request.question,
                decision_profile,
                conversation_context=conversation_context,
            )
            response_channel = turn_decision.response_channel
            logger.info(f"[决策器] account_id={account_id}, decision={turn_decision.to_log_dict()}")

            if turn_decision.risk == "high_risk":
                final_response = self.chat_service._get_risk_guard_response(request.question, user_profile)  # noqa: SLF001
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                # Phase 2: FAQ/risk 结束后设置 bridge_back 标记
                user_profile.needs_bridge_back = True
                user_profile.last_side_topic_type = "risk"
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)
                route_name = "risk_guard"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"all_fields": []},
                    request.dialogId,
                    dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
                    response_route=route_name,
                )
                payload = self._sync_payload_response(payload, final_response)
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            self.chat_service.dialogue_manager.update_user_sex(user_profile)
            t0 = time.perf_counter()
            await self.chat_service._handle_refusal_detection(request.question, account_id, user_profile)  # noqa: SLF001
            _mark("refusal_detection", t0)

            if response_channel == "quick_faq":
                final_response = self.chat_service._get_priority_question_response(  # noqa: SLF001
                    request.question,
                    decision_profile,
                    repeat_count=1,
                    recent_responses=conversation_context.get("recent_responses") or (),
                ) or await self.chat_service._build_no_ai_response(account_id, user_profile, request.question)  # noqa: SLF001
                final_response = self.chat_service._apply_priority_question_guard(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    request.question,
                )
                final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    decision_profile,
                    request.question,
                )
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                # Phase 2: FAQ 结束后设置 bridge_back 标记
                user_profile.needs_bridge_back = True
                user_profile.last_side_topic_type = "faq"
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)
                route_name = "quick_faq"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"all_fields": []},
                    request.dialogId,
                    dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
                    response_route=route_name,
                )
                payload = self._sync_payload_response(payload, final_response)
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            if turn_decision.risk == "boundary":
                final_response = self.chat_service._get_boundary_pause_response(request.question)  # noqa: SLF001
                final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                # Phase 2: boundary 结束后设置 bridge_back 标记
                user_profile.needs_bridge_back = True
                user_profile.last_side_topic_type = "boundary"
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)
                route_name = "boundary_pause"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"all_fields": []},
                    request.dialogId,
                    dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
                    response_route=route_name,
                )
                payload = self._sync_payload_response(payload, final_response)
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            if turn_decision.risk == "withdraw":
                user_profile.increment_ask_count("conversation_end_intent")
                final_response, should_close = self.chat_service._build_withdraw_response(  # noqa: SLF001
                    user_profile,
                    user_message=request.question,
                )
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                if should_close:
                    user_profile.conversation_ended = True
                    user_profile.needs_bridge_back = False
                    user_profile.last_side_topic_type = None
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)
                route_name = "withdraw_close" if should_close else "withdraw_retain"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"all_fields": []},
                    request.dialogId,
                    dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
                    response_route=route_name,
                )
                payload = self._sync_payload_response(payload, final_response)
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            # Phase 1: complaint / repair 意图处理
            if turn_decision.intent == "complaint":
                final_response = self.chat_service._get_complaint_repair_response(request.question)  # noqa: SLF001
                final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                # complaint 修复态不再桥接回“继续采集”的主线，避免下一轮又把用户拉回资料追问。
                user_profile.needs_bridge_back = False
                user_profile.last_side_topic_type = None
                user_profile.complaint_cooldown_until = message_count + 2
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                t0 = time.perf_counter()
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                _mark("state_update", t0)
                t0 = time.perf_counter()
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                _mark("profile_reload", t0)
                route_name = "complaint_repair"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"all_fields": []},
                    request.dialogId,
                    dict(user_profile.field_ask_count) if user_profile.field_ask_count else {},
                    response_route=route_name,
                )
                payload = self._sync_payload_response(payload, final_response)
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            # Phase 2: FAQ/边界/complaint 后的 bridge-back 检查（repair_mode 下禁用）
            bridge_prefix = ""
            in_repair_mode = turn_decision.in_repair_mode
            if not in_repair_mode and user_profile.needs_bridge_back:
                bridge_prefix = self.chat_service._build_bridge_back_prefix(  # noqa: SLF001
                    user_profile.last_side_topic_type
                )
                logger.info(
                    f"[bridge_back] account_id={account_id}, "
                    f"side_topic={user_profile.last_side_topic_type}, "
                    f"prefix={bridge_prefix[:20]}..."
                )
                # 重置标记并保存
                user_profile.needs_bridge_back = False
                user_profile.last_side_topic_type = None
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)

            profile_summary = ""

            ai_response = ""
            infra_fail = False
            infra_fail_reason = ""
            t0 = time.perf_counter()
            # 使用完整 prompt
            main_prompt = self.chat_service.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                decision_profile,
                conversation_context,
                prioritize_user_question=turn_decision.prioritize_user_question,
                primary_move=turn_decision.primary_move,
                allow_contact_target=turn_decision.allow_contact_target,
                allow_medium_target=turn_decision.allow_medium_target,
            )
            bridge_instruction = self.chat_service._build_profile_bridge_generation_instruction(  # noqa: SLF001
                user_message=request.question,
                user_profile=decision_profile,
                turn_decision=turn_decision,
                conversation_context=conversation_context,
            )
            if bridge_instruction:
                main_prompt = self.chat_service._augment_prompt_for_profile_bridge_followup(  # noqa: SLF001
                    main_prompt,
                    bridge_instruction,
                )
            opening_intent_detection_enabled = self.chat_service._should_run_opening_intent_detection(  # noqa: SLF001
                conversation_context,
                user_profile,
            ) and turn_decision.response_channel == "model"
            if opening_intent_detection_enabled:
                main_prompt = self.chat_service._augment_prompt_for_opening_intent_detection(main_prompt)  # noqa: SLF001
            _mark("prompt_build", t0)
            prompt_chars = len(main_prompt or "")

            t0 = time.perf_counter()
            await self.chat_service.user_service.save_user_profile(account_id, user_profile)
            _mark("profile_save_pre_ai", t0)

            t0 = time.perf_counter()
            self.chat_service._last_opening_intent_signal = None  # noqa: SLF001
            ai_response = await self.chat_service._call_ai(main_prompt, account_id, request.question)  # noqa: SLF001
            _mark("ai_call", t0)
            if not ai_response:
                infra_fail = True
                infra_fail_reason = getattr(self.chat_service, "_last_ai_failure_reason", None) or "ai_empty_response"
                self.chat_service._last_opening_intent_signal = None  # noqa: SLF001
                t0 = time.perf_counter()
                ai_response = await self.chat_service._build_no_ai_response(account_id, user_profile, request.question)  # noqa: SLF001
                _mark("no_ai_fallback", t0)
            elif turn_decision.response_channel == "model":
                opening_signal = None
                if opening_intent_detection_enabled:
                    opening_signal, ai_response = self.chat_service._extract_opening_intent_block(ai_response)  # noqa: SLF001
                    self.chat_service._last_opening_intent_signal = opening_signal  # noqa: SLF001
                    if opening_signal and opening_signal.parse_failed:
                        logger.info("[opening_intent] parse_failed=1")
                    elif opening_signal and opening_signal.intent:
                        logger.info(
                            "[opening_intent] intent=%s confidence=%.2f secondary=%s",
                            opening_signal.intent,
                            opening_signal.confidence,
                            opening_signal.secondary_intent or "-",
                        )
                    self.chat_service._apply_opening_intent_signal_to_turn_decision(  # noqa: SLF001
                        opening_signal,
                        turn_decision,
                        user_message=request.question,
                    )
                t0 = time.perf_counter()
                ai_response = await self.chat_service._stabilize_style_response(  # noqa: SLF001
                    ai_response,
                    account_id=account_id,
                    user_message=request.question,
                    conversation_context=conversation_context,
                    ask_field=turn_decision.ask_field,
                )
                _mark("style_stabilize", t0)
                t0 = time.perf_counter()
                ai_response = self.chat_service._ensure_short_answer_ack_transition(  # noqa: SLF001
                    ai_response,
                    user_message=request.question,
                    user_profile=user_profile,
                )
                _mark("short_answer_bridge", t0)
                t0 = time.perf_counter()
                ai_response = await self.chat_service._enforce_profile_bridge_response(  # noqa: SLF001
                    ai_response,
                    account_id=account_id,
                    user_message=request.question,
                    user_profile=user_profile,
                    turn_decision=turn_decision,
                    conversation_context=conversation_context,
                )
                _mark("profile_bridge_enforce", t0)
            else:
                self.chat_service._last_opening_intent_signal = None  # noqa: SLF001

            t0 = time.perf_counter()
            if infra_fail:
                ai_extracted_data = {}
            else:
                ai_extracted_data = self.chat_service.extraction_service.extract_json_from_response(ai_response)
            rule_extracted_data = self.chat_service._extract_deterministic_profile_fields(request.question)  # noqa: SLF001
            extracted_data, extraction_meta = self.chat_service._fuse_extracted_fields(  # noqa: SLF001
                ai_extracted_data,
                rule_extracted_data,
                request.question,
            )
            if not extracted_data.get("partner_requirement"):
                pref = self.chat_service._extract_simple_partner_requirement(request.question)  # noqa: SLF001
                if pref:
                    extracted_data["partner_requirement"] = pref
                    extraction_meta["partner_requirement"] = {
                        "source": "rule_fallback",
                        "confidence": 0.86,
                        "source_text": request.question,
                    }
            _mark("extract_fuse", t0)
            extracted_fields_count = len(extracted_data or {})
            contact_gate_before = self.chat_service.collection_policy.can_enter_contact(user_profile)  # noqa: SLF001

            t0 = time.perf_counter()
            profile_result = await self.chat_service.profile_collection_coordinator.process_collection(
                account_id,
                user_profile,
                extracted_data,
                request.question,
                extraction_meta=extraction_meta,
                turn_id=message_count + 1,
            )
            collection_result = profile_result.collection_result
            _mark("collection_process", t0)
            extracted_fields_count = len(collection_result.get("all_fields", []))

            for field_info in collection_result.get("all_fields", []):
                if field_info.get("field") == "partner_requirement":
                    latest_profile = await self.chat_service.user_service.get_user_profile(account_id)
                    latest_profile.close_active_ask("partner_requirement")
                    await self.chat_service.user_service.save_user_profile(account_id, latest_profile)
                    user_profile = latest_profile
                    await self.chat_service.input_fallback_service.reset_confirm_count(account_id)
                    break

            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _ = self.chat_service.profile_collection_coordinator.build_contact_decision(user_profile, request.question)
            preset_response = str(collection_result.get("response") or "").strip()
            if preset_response:
                enhanced_response = preset_response
            else:
                enhanced_response = await self.chat_service._handle_contact_validation(  # noqa: SLF001
                    account_id,
                    user_profile,
                    collection_result,
                    ai_response,
                    request.question,
                )

            response_to_clean = enhanced_response if enhanced_response is not None else ai_response
            ending_info = collection_result.get("ending_info") if isinstance(collection_result, dict) else None
            if isinstance(ending_info, dict) and ending_info.get("use_ai"):
                ai_ending_response = await self.chat_service._generate_ai_ending_response(  # noqa: SLF001
                    account_id=account_id,
                    user_profile=user_profile,
                    user_message=request.question,
                    ending_info=ending_info,
                    fallback_response=response_to_clean,
                )
                if ai_ending_response:
                    response_to_clean = ai_ending_response
                    ending_info["response"] = ai_ending_response
            raw_response_len = len(str(response_to_clean or ""))
            final_response = self.chat_service._clean_response(response_to_clean)  # noqa: SLF001
            cleaned_response_len = len(str(final_response or ""))
            logger.info(
                "[response_lengths] raw_len=%s cleaned_len=%s has_extract=%s has_opening_intent=%s",
                raw_response_len,
                cleaned_response_len,
                int("<extract>" in str(response_to_clean or "")),
                int("<opening_intent>" in str(response_to_clean or "")),
            )
            final_response = self.chat_service._enforce_opening_intent_consistency(  # noqa: SLF001
                final_response,
                getattr(self.chat_service, "_last_opening_intent_signal", None),
                user_message=request.question,
                seed_hint=f"{account_id}:{request.question}",
            )
            final_response = self.chat_service._apply_priority_question_guard(  # noqa: SLF001
                final_response,
                turn_decision,
                request.question,
            )
            final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                final_response,
                turn_decision,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
            )
            final_response = self.chat_service._apply_contact_persuasion_style_policy(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._apply_contact_boundary_softening_policy(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._apply_refusal_respect_guard(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._apply_contact_action_guard(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._apply_contact_context_field_guard(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._enforce_contact_outcome_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                request.question,
            )
            final_response = self.chat_service._apply_contact_context_field_guard(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )
            if collection_result.get("divorce_confirmation_cleared"):
                final_response = self.chat_service._build_divorce_confirmation_cleared_response(  # noqa: SLF001
                    self.chat_service._get_post_divorce_mainline_target(  # noqa: SLF001
                        user_profile,
                        request.question,
                        message_count=message_count,
                    )
                )
            if collection_result.get("divorce_confirmation_pending") or self.chat_service._should_lock_divorce_confirmation(  # noqa: SLF001
                user_profile,
                request.question,
            ):
                final_response = self.chat_service._build_divorce_confirmation_response()  # noqa: SLF001
            final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
            final_response = self.chat_service._apply_income_appreciation_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
            )
            final_response = self.chat_service._apply_field_ask_guard(  # noqa: SLF001
                user_profile,
                final_response,
                user_message=request.question,
                allow_medium_target=turn_decision.allow_medium_target,
            )
            final_response = self.chat_service._avoid_reasking_just_collected_field(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                current_ask_field=turn_decision.ask_field,
                user_message=request.question,
                allow_medium_target=turn_decision.allow_medium_target,
            )
            final_response = self.chat_service._avoid_reasking_already_collected_fields(  # noqa: SLF001
                final_response,
                user_profile,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                allow_medium_target=turn_decision.allow_medium_target,
            )
            if not self.chat_service._is_delivery_viable(final_response):  # noqa: SLF001
                fallback_response = await self.chat_service._build_no_ai_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._clean_response(fallback_response)  # noqa: SLF001
                final_response = self.chat_service._apply_priority_question_guard(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    request.question,
                )
                final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                    final_response,
                    turn_decision,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                    final_response,
                    user_profile,
                    collection_result,
                )
                final_response = self.chat_service._apply_contact_context_field_guard(  # noqa: SLF001
                    final_response,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._enforce_contact_outcome_policy(  # noqa: SLF001
                    final_response,
                    user_profile,
                    collection_result,
                    request.question,
                )
                if collection_result.get("divorce_confirmation_cleared"):
                    final_response = self.chat_service._build_divorce_confirmation_cleared_response(  # noqa: SLF001
                        self.chat_service._get_post_divorce_mainline_target(  # noqa: SLF001
                            user_profile,
                            request.question,
                            message_count=message_count,
                        )
                    )
                if collection_result.get("divorce_confirmation_pending") or self.chat_service._should_lock_divorce_confirmation(  # noqa: SLF001
                    user_profile,
                    request.question,
                ):
                    final_response = self.chat_service._build_divorce_confirmation_response()  # noqa: SLF001
                final_response = self.chat_service._apply_contact_action_guard(  # noqa: SLF001
                    final_response,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._apply_contact_context_field_guard(  # noqa: SLF001
                    final_response,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._sanitize_robotic_tone(final_response)  # noqa: SLF001
                final_response = self.chat_service._apply_income_appreciation_policy(  # noqa: SLF001
                    final_response,
                    user_profile,
                    collection_result,
                )
                final_response = self.chat_service._apply_refusal_respect_guard(  # noqa: SLF001
                    final_response,
                    user_profile,
                    request.question,
                )
                final_response = self.chat_service._apply_field_ask_guard(  # noqa: SLF001
                    user_profile,
                    final_response,
                    user_message=request.question,
                    allow_medium_target=turn_decision.allow_medium_target,
                )
                final_response = self.chat_service._avoid_reasking_just_collected_field(  # noqa: SLF001
                    final_response,
                    user_profile,
                    collection_result,
                    current_ask_field=turn_decision.ask_field,
                    user_message=request.question,
                    allow_medium_target=turn_decision.allow_medium_target,
                )
                final_response = self.chat_service._avoid_reasking_already_collected_fields(  # noqa: SLF001
                    final_response,
                    user_profile,
                    user_message=request.question,
                    response_channel=turn_decision.response_channel,
                    primary_move=turn_decision.primary_move,
                    allow_medium_target=turn_decision.allow_medium_target,
                )
                final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                    final_response,
                    user_profile,
                    collection_result,
                )
            final_response = self.chat_service._apply_humanlike_turn_structure_policy(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
                allow_medium_target=turn_decision.allow_medium_target,
            )
            final_response = self.chat_service._apply_context_ack_policy(  # noqa: SLF001
                final_response,
                turn_decision,
                user_profile,
                request.question,
            )
            final_response = self.chat_service._enforce_natural_completion_transition(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                user_message=request.question,
            )
            previous_asked_field = user_profile.last_asked_field
            final_response = self.chat_service._enforce_core_mainline_followup(  # noqa: SLF001
                final_response,
                user_profile,
                ask_field=turn_decision.ask_field,
                collection_result=collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
            )
            final_response = self.chat_service._enforce_active_target_followup(  # noqa: SLF001
                final_response,
                user_profile,
                ask_field=turn_decision.ask_field,
                collection_result=collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
            )
            final_response = self.chat_service._enforce_pending_partner_requirement_followup(  # noqa: SLF001
                final_response,
                user_profile,
                ask_field=turn_decision.ask_field,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
            )
            final_response = self.chat_service._prepend_multi_field_ack_transition(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                ask_field=turn_decision.ask_field,
                followup_topic=turn_decision.followup_topic,
            )
            final_response = self.chat_service._prepend_single_field_ack_transition(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                ask_field=turn_decision.ask_field,
                followup_topic=turn_decision.followup_topic,
            )
            final_response = self.chat_service._append_safe_short_answer_followup(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                previous_asked_field=previous_asked_field,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                ask_field=turn_decision.ask_field,
                followup_topic=turn_decision.followup_topic,
            )
            final_response = self.chat_service._handoff_to_contact_after_core_completion(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result=collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                contact_gate_before=contact_gate_before,
            )
            final_response = self.chat_service._handoff_to_pending_target_after_core_completion(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result=collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
                contact_gate_before=contact_gate_before,
            )
            final_response = self.chat_service._handoff_to_contact_after_medium_completion(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result=collection_result,
                user_message=request.question,
                response_channel=turn_decision.response_channel,
                primary_move=turn_decision.primary_move,
            )
            final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
            )
            final_response = self.chat_service._collapse_duplicate_ack_segments(  # noqa: SLF001
                final_response,
            )
            final_response = self.chat_service._prevent_no_repeat_hold_from_blocking_progress(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result=collection_result,
                user_message=request.question,
            )
            final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
            )
            final_response = self.chat_service._enforce_contact_outcome_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
                request.question,
            )
            final_response = self.chat_service._apply_contact_context_field_guard(  # noqa: SLF001
                final_response,
                user_profile,
                request.question,
            )

            # Phase 2: 应用 bridge_back 前缀（如果有）
            if bridge_prefix:
                # 确保桥接前缀与后续内容之间有合适的分隔
                if final_response and not final_response.startswith(("好", "嗯", "是", "对")):
                    final_response = f"{bridge_prefix} {final_response}"
                else:
                    # 如果回复以确认词开头，桥接前缀放在确认词后面
                    first_sentence_end = final_response.find("。")
                    if first_sentence_end > 0:
                        final_response = (
                            final_response[: first_sentence_end + 1]
                            + f" {bridge_prefix} "
                            + final_response[first_sentence_end + 1 :]
                        )
                    else:
                        final_response = f"{bridge_prefix} {final_response}"
                logger.info(f"[bridge_back] 已应用桥接前缀，最终回复长度={len(final_response)}")

            final_response = self.chat_service._strip_broken_edge_fragments(final_response)  # noqa: SLF001

            delivery_ok = self.chat_service._is_delivery_viable(final_response)  # noqa: SLF001
            if not delivery_ok:
                final_response = self.chat_service._build_no_ai_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    request.question,
                )
                delivery_ok = True

            if delivery_ok:
                t0 = time.perf_counter()
                user_profile = await self.chat_service._record_delivered_contact_ask_if_needed(  # noqa: SLF001
                    account_id,
                    user_profile,
                    request.question,
                    final_response,
                )
                _mark("contact_ask_record", t0)

            field_ask_count_before = dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}
            t0 = time.perf_counter()
            should_track_asked_fields = (
                delivery_ok
                and not turn_decision.prioritize_user_question
                and turn_decision.primary_move
                not in {"answer_then_pause", "repair_and_release", "soft_hold", "ack_only", "confirm_status_only"}
            )
            await self.chat_service._update_conversation_state(  # noqa: SLF001
                account_id,
                request.question,
                final_response,
                ai_response,
                track_asked_fields=should_track_asked_fields,
            )
            _mark("state_update", t0)
            t0 = time.perf_counter()
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _mark("profile_reload", t0)

            t0 = time.perf_counter()
            user_profile = await self.chat_service._update_progress_runtime_counters(  # noqa: SLF001
                account_id,
                user_profile,
                user_message=request.question,
                collection_result=collection_result,
                turn_decision=turn_decision,
                message_count=message_count,
                previous_asked_field=previous_asked_field,
            )
            _mark("progress_counters", t0)

            final_response = self.chat_service._enforce_terminal_response_policy(  # noqa: SLF001
                final_response,
                user_profile,
                collection_result,
            )

            # Phase 2: repair_mode 冷却递减（每轮结束时）
            if user_profile.repair_mode and user_profile.ask_cooldown_turns > 0:
                user_profile.decrement_cooldown()
                logger.info(
                    f"[repair_mode] 冷却递减，剩余轮数: {user_profile.ask_cooldown_turns}, "
                    f"repair_mode: {user_profile.repair_mode}"
                )
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
            total_duration = time.perf_counter() - start_time
            logger.info(f"[⏱️ 性能] 请求处理完成: account_id={account_id}, 总耗时={total_duration:.3f}秒")
            route_name = "model"
            payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                account_id,
                user_profile,
                final_response,
                collection_result,
                request.dialogId,
                field_ask_count_before,
                response_route=route_name if route_name != "model" else None,
            )
            if infra_fail:
                payload["meta"] = {
                    "infra_fail": True,
                    "infra_fail_reason": infra_fail_reason,
                }
            validation_meta = getattr(self.chat_service, "_last_validation_feedback_meta", None)
            if validation_meta:
                meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
                meta["validation"] = dict(validation_meta)
                payload["meta"] = meta

            ending_info = collection_result.get("ending_info") if isinstance(collection_result, dict) else None
            if isinstance(ending_info, dict) and ending_info.get("scenario") == "both_rejected":
                final_response = self.chat_service.ending_service.get_ending_response("both_rejected") or final_response

            payload = self._sync_payload_response(payload, final_response)
            payload = _attach_route_meta(payload, route_name)
            _log_turn(route_name, True)
            return payload
        except Exception as e:
            total_duration = time.perf_counter() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            _log_turn(route_name or "error", False, str(e))
            from src.core.error_handler import handle_error

            error_response = handle_error(e, context="chat", user_id=account_id)
            return self.chat_service._error_response(  # noqa: SLF001
                error_response.get("error", "处理失败"),
                request.dialogId,
                error_code=error_response.get("error_code"),
                details=error_response.get("details"),
            )
