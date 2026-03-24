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

            t0 = time.perf_counter()
            rule_result = await self.chat_service.conversation_rule_service.try_handle(
                request,
                user_profile,
                is_first_user_turn=is_first_user_turn,
                message_count=message_count,
            )
            _mark("rule_check", t0)
            if rule_result.handled:
                payload = rule_result.response_payload or {}
                response_text = str(payload.get("response") or "")
                if response_text:
                    # 规则分支若未更新上下文，会导致后续拒绝检测读取到旧 last_response。
                    t0 = time.perf_counter()
                    last_response = await self.chat_service.dialogue_manager.get_last_response(account_id)
                    if last_response != response_text:
                        await self.chat_service._update_conversation_state(  # noqa: SLF001
                            account_id,
                            request.question,
                            response_text,
                            response_text,
                            track_asked_fields=False,
                        )
                    _mark("rule_state_update", t0)
                route_name = str(payload.get("route") or "rule")
                response_channel = "rule"
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            t0 = time.perf_counter()
            conversation_context = await self.chat_service.dialogue_manager.get_conversation_context(account_id)
            _mark("context_load", t0)
            turn_decision = self.chat_service._build_turn_decision(  # noqa: SLF001
                request.question,
                user_profile,
                conversation_context=conversation_context,
            )
            response_channel = turn_decision.response_channel
            logger.info(f"[决策器] account_id={account_id}, decision={turn_decision.to_log_dict()}")

            if turn_decision.next_action == "risk_guard":
                risk_guard_response = self.chat_service._get_risk_guard_response(request.question, user_profile) or ""  # noqa: SLF001
                risk_guard_response = self.chat_service._ensure_listener_first_ack(request.question, risk_guard_response)  # noqa: SLF001
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    risk_guard_response,
                    risk_guard_response,
                    track_asked_fields=False,
                )
                route_name = "risk_guard"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    risk_guard_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                    response_route="risk_guard",
                )
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            self.chat_service.dialogue_manager.update_user_sex(user_profile)
            t0 = time.perf_counter()
            await self.chat_service._handle_refusal_detection(request.question, account_id, user_profile)  # noqa: SLF001
            _mark("refusal_detection", t0)

            if turn_decision.next_action == "boundary_pause":
                boundary_pause_response = self.chat_service._get_boundary_pause_response(request.question) or ""  # noqa: SLF001
                boundary_pause_response = self.chat_service._ensure_listener_first_ack(request.question, boundary_pause_response)  # noqa: SLF001
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    boundary_pause_response,
                    boundary_pause_response,
                    track_asked_fields=False,
                )
                route_name = "boundary_pause"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    boundary_pause_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                    response_route="boundary_pause",
                )
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            if self.chat_service._looks_like_fake_info(request.question):  # noqa: SLF001
                self.chat_service.ending_service.update_profile_for_ending("fake_info", user_profile)
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                fake_info_response = self.chat_service.ending_service.get_ending_response("fake_info") or ""
                route_name = "ending_template"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    fake_info_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                    response_route="ending_template",
                )
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            prioritize_user_question = turn_decision.response_channel == "quick_faq"
            if prioritize_user_question:
                faq_intent = turn_decision.intent if turn_decision.intent != "general" else self.chat_service.user_question_service.detect_quick_faq_intent(request.question)
                faq_state_raw = await self.chat_service.user_service.get_user_preference(account_id, "faq_state", {})
                faq_state = faq_state_raw if isinstance(faq_state_raw, dict) else {}
                last_intent = faq_state.get("last_intent")
                repeat_count = int(faq_state.get("repeat_count", 0)) + 1 if faq_intent and faq_intent == last_intent else 1
                recent = faq_state.get("recent_responses", [])
                if not isinstance(recent, list):
                    recent = []
                last_response = await self.chat_service.dialogue_manager.get_last_response(account_id) or ""  # noqa: SLF001
                quick_faq_response = ""
                if faq_intent == "clarification":
                    quick_faq_response = self.chat_service._build_contextual_clarification_reply(last_response, request.question)  # noqa: SLF001
                if not quick_faq_response:
                    quick_faq_response = self.chat_service.user_question_service.get_quick_faq_response(
                        request.question,
                        repeat_count=repeat_count,
                        recent_responses=tuple(recent),
                    )
                if quick_faq_response:
                    final_response = self.chat_service._ensure_faq_humanlike_ack(request.question, quick_faq_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_listener_first_ack(request.question, final_response)  # noqa: SLF001
                    if faq_intent:
                        faq_state = {
                            "last_intent": faq_intent,
                            "repeat_count": repeat_count,
                            "recent_responses": (recent + [final_response])[-3:],
                        }
                        await self.chat_service.user_service.update_user_preference(account_id, "faq_state", faq_state)
                    await self.chat_service._update_conversation_state(  # noqa: SLF001
                        account_id,
                        request.question,
                        final_response,
                        final_response,
                        track_asked_fields=False,
                    )
                    route_name = "quick_faq"
                    payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        final_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="quick_faq",
                    )
                    payload = _attach_route_meta(payload, route_name)
                    _log_turn(route_name, True)
                    return payload

            deterministic_fields = self.chat_service._extract_deterministic_profile_fields(request.question)  # noqa: SLF001
            if self.chat_service._should_use_rule_profile_fast_path(  # noqa: SLF001
                request.question,
                deterministic_fields,
                turn_decision.response_channel,
            ):
                profile_result = await self.chat_service.profile_collection_coordinator.process_collection(
                    account_id,
                    user_profile,
                    deterministic_fields,
                    request.question,
                    extraction_meta=None,
                    turn_id=message_count + 1,
                )
                collection_result = profile_result.collection_result

                if collection_result.get("success") and "response" in collection_result:
                    final_response = collection_result.get("response", "")
                    final_response = self.chat_service._clean_response(final_response)  # noqa: SLF001
                    final_response = self.chat_service._apply_field_ask_guard(user_profile, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_listener_first_ack(request.question, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_humanlike_memory_ack(request.question, user_profile, final_response)  # noqa: SLF001
                    final_response = self.chat_service._apply_dialogue_style_guard(  # noqa: SLF001
                        conversation_context.get("last_response", ""),
                        final_response,
                        user_profile,
                        user_message=request.question,
                        tone_policy=turn_decision.tone_policy or {},
                    )
                    await self.chat_service._update_conversation_state(  # noqa: SLF001
                        account_id,
                        request.question,
                        final_response,
                        final_response,
                        track_asked_fields=False,
                    )
                    user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                    route_name = "collection_short_circuit"
                    payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        final_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="collection_short_circuit",
                    )
                    payload = _attach_route_meta(payload, route_name)
                    extracted_fields_count = len(collection_result.get("all_fields", []))
                    _log_turn(route_name, True)
                    return payload

                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                final_response = self.chat_service._build_rule_profile_fast_response(  # noqa: SLF001
                    user_profile,
                    user_message=request.question,
                )
                if final_response:
                    final_response = self.chat_service._clean_response(final_response)  # noqa: SLF001
                    final_response = self.chat_service._apply_field_ask_guard(user_profile, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_listener_first_ack(request.question, final_response)  # noqa: SLF001
                    final_response = self.chat_service._ensure_humanlike_memory_ack(request.question, user_profile, final_response)  # noqa: SLF001
                    final_response = self.chat_service._apply_dialogue_style_guard(  # noqa: SLF001
                        conversation_context.get("last_response", ""),
                        final_response,
                        user_profile,
                        user_message=request.question,
                        tone_policy=turn_decision.tone_policy or {},
                    )
                    field_ask_count_before = dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}
                    await self.chat_service._update_conversation_state(  # noqa: SLF001
                        account_id,
                        request.question,
                        final_response,
                        final_response,
                        track_asked_fields=True,
                    )
                    user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                    total_duration = time.perf_counter() - start_time
                    logger.info(f"[⏱️ 性能] 请求处理完成(规则快路径): account_id={account_id}, 总耗时={total_duration:.3f}秒")
                    route_name = "rule_profile_fast_path"
                    payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        final_response,
                        collection_result,
                        request.dialogId,
                        field_ask_count_before,
                        response_route="rule_profile_fast_path",
                    )
                    payload = _attach_route_meta(payload, route_name)
                    extracted_fields_count = len(collection_result.get("all_fields", []))
                    _log_turn(route_name, True)
                    return payload

            t0 = time.perf_counter()
            main_prompt = self.chat_service.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                user_profile,
                conversation_context,
                prioritize_user_question=prioritize_user_question,
            )
            _mark("prompt_build", t0)
            prompt_chars = len(main_prompt or "")

            t0 = time.perf_counter()
            await self.chat_service.user_service.save_user_profile(account_id, user_profile)
            _mark("profile_save_pre_ai", t0)

            collected_info = self.chat_service.extraction_service.get_collected_info_summary(user_profile)
            has_contact = "已留联系" in collected_info
            has_requirement = "要求:" in collected_info
            if has_contact and has_requirement:
                user_input = request.question.strip()
                ending_signals = [
                    "没有了", "没啦", "没了", "就这些", "就这点", "暂时没有", "暂时没", "先这样", "差不多", "应该没了",
                    "应该没", "没有了呢", "没啥了", "其他没了", "其他没", "暂时就这些", "目前没", "目前没有",
                ]
                is_ending = any(signal in user_input for signal in ending_signals)
                greeting_words = ["在吗", "在不在", "你好", "您好", "嗨", "哈喽", "hello", "hi"]
                is_greeting = any(word in user_input for word in greeting_words)
                if is_greeting:
                    natural_response = f"在的呀～{user_profile.get_greeting()}，你要是还有想了解的可以直接跟我说"
                    route_name = "rule_followup_greeting"
                    payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        natural_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="rule_followup_greeting",
                    )
                    payload = _attach_route_meta(payload, route_name)
                    _log_turn(route_name, True)
                    return payload
                if is_ending:
                    last_response = await self.chat_service.dialogue_manager.get_last_response(account_id)
                    closing_message = self.chat_service._build_rotating_ending_message(  # noqa: SLF001
                        user_profile,
                        last_response or "",
                    )
                    route_name = "ending_template"
                    payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        closing_message,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="ending_template",
                    )
                    payload = _attach_route_meta(payload, route_name)
                    _log_turn(route_name, True)
                    return payload

            t0 = time.perf_counter()
            ai_response = await self.chat_service._call_ai(main_prompt, account_id, request.question)  # noqa: SLF001
            _mark("ai_call", t0)
            infra_fail = False
            infra_fail_reason = ""
            if not ai_response:
                infra_fail = True
                infra_fail_reason = getattr(self.chat_service, "_last_ai_failure_reason", None) or "ai_empty_response"
                t0 = time.perf_counter()
                ai_response = await self.chat_service._build_no_ai_response(account_id, user_profile, request.question)  # noqa: SLF001
                _mark("no_ai_fallback", t0)
                if not str(ai_response or "").strip():
                    ai_response = "我先接住你这句话，我们继续聊你最在意的匹配条件就好。"

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

            if collection_result.get("success") and "response" in collection_result:
                final_response = collection_result.get("response", "")
                final_response = self.chat_service._clean_response(final_response)  # noqa: SLF001
                final_response = self.chat_service._apply_field_ask_guard(user_profile, final_response)  # noqa: SLF001
                last_response = await self.chat_service.dialogue_manager.get_last_response(account_id) or ""
                final_response = self.chat_service._apply_dialogue_style_guard(  # noqa: SLF001
                    last_response,
                    final_response,
                    user_profile,
                    user_message=request.question,
                    tone_policy=turn_decision.tone_policy,
                )
                final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
                final_response = self.chat_service._ensure_listener_first_ack(request.question, final_response)  # noqa: SLF001
                final_response = self.chat_service._avoid_preference_hard_ending(request.question, final_response)  # noqa: SLF001
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    ai_response,
                    track_asked_fields=False,
                )
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                route_name = "collection_short_circuit"
                payload = await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                    response_route="collection_short_circuit",
                )
                if infra_fail:
                    payload["meta"] = {
                        "infra_fail": True,
                        "infra_fail_reason": infra_fail_reason,
                    }
                payload = _attach_route_meta(payload, route_name)
                _log_turn(route_name, True)
                return payload

            for field_info in collection_result.get("all_fields", []):
                if field_info.get("field") == "partner_requirement":
                    await self.chat_service.input_fallback_service.reset_confirm_count(account_id)
                    break

            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _ = self.chat_service.profile_collection_coordinator.build_contact_decision(user_profile, request.question)
            enhanced_response = await self.chat_service._handle_contact_validation(  # noqa: SLF001
                account_id,
                user_profile,
                collection_result,
                ai_response,
                request.question,
            )

            is_hong_user = self.chat_service._is_hong_user(user_profile.location)  # noqa: SLF001
            contact_just_collected = any(f.get("field") == "contact" for f in collection_result.get("all_fields", []))
            if is_hong_user and contact_just_collected and not user_profile.wechat:
                enhanced_response = f"好的呀～{user_profile.get_greeting()}的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～"

            response_to_clean = enhanced_response if enhanced_response is not None else ai_response
            final_response = self.chat_service._clean_response(response_to_clean)  # noqa: SLF001
            if prioritize_user_question:
                final_response = self.chat_service._strip_collection_prompts_for_faq(final_response)  # noqa: SLF001
            final_response = self.chat_service._apply_field_ask_guard(user_profile, final_response)  # noqa: SLF001
            last_response = await self.chat_service.dialogue_manager.get_last_response(account_id) or ""
            final_response = self.chat_service._apply_dialogue_style_guard(
                last_response,
                final_response,
                user_profile,
                user_message=request.question,
                tone_policy=turn_decision.tone_policy,
            )  # noqa: SLF001
            final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
            final_response = self.chat_service._ensure_listener_first_ack(request.question, final_response)  # noqa: SLF001
            final_response = self.chat_service._ensure_humanlike_memory_ack(request.question, user_profile, final_response)  # noqa: SLF001

            field_ask_count_before = dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}
            t0 = time.perf_counter()
            await self.chat_service._update_conversation_state(  # noqa: SLF001
                account_id,
                request.question,
                final_response,
                ai_response,
                track_asked_fields=not prioritize_user_question,
            )
            _mark("state_update", t0)
            t0 = time.perf_counter()
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            _mark("profile_reload", t0)
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
            )
            if infra_fail:
                payload["meta"] = {
                    "infra_fail": True,
                    "infra_fail_reason": infra_fail_reason,
                }
            payload = _attach_route_meta(payload, route_name)
            _log_turn(route_name, True)
            return payload
        except Exception as e:
            total_duration = time.perf_counter() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            _log_turn(route_name or "error", False, str(e))
            from src.core.error_handler import handle_error

            error_response = handle_error(e, context="chat", user_id=account_id)
            return self.chat_service._error_response(error_response.get("error", "处理失败"), request.dialogId)  # noqa: SLF001
