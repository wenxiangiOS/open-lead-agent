from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict

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
        start_time = time.time()
        account_id = request.accountId
        logger.info(f"[⏱️ 性能] 开始处理请求: account_id={account_id}")

        try:
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)

            if request.sex in ["男", "女"] and not user_profile.sex:
                user_profile.sex = request.sex
                user_profile.collection_progress["sex"] = True
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)

            is_empty = user_profile.is_empty()
            message_count = await self.chat_service.dialogue_manager.get_message_count(account_id)
            is_new_user_session = is_empty and message_count == 0
            is_first_user_turn = message_count == 0
            if is_new_user_session:
                await self.chat_service.input_fallback_service.reset_nonsense_count(account_id)
                user_profile.conversation_ended = False
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)

            rule_result = await self.chat_service.conversation_rule_service.try_handle(
                request,
                user_profile,
                is_first_user_turn=is_first_user_turn,
                message_count=message_count,
            )
            if rule_result.handled:
                return rule_result.response_payload or {}

            self.chat_service.dialogue_manager.update_user_sex(user_profile)
            await self.chat_service._handle_refusal_detection(request.question, account_id, user_profile)  # noqa: SLF001

            if self.chat_service._looks_like_fake_info(request.question):  # noqa: SLF001
                self.chat_service.ending_service.update_profile_for_ending("fake_info", user_profile)
                await self.chat_service.user_service.save_user_profile(account_id, user_profile)
                fake_info_response = self.chat_service.ending_service.get_ending_response("fake_info") or ""
                return await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    fake_info_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                    response_route="ending_template",
                )

            conversation_context = await self.chat_service.dialogue_manager.get_conversation_context(account_id)
            prioritize_user_question = self.chat_service.user_question_service.is_priority_question(request.question)
            if prioritize_user_question:
                faq_intent = self.chat_service.user_question_service.detect_quick_faq_intent(request.question)
                faq_state = await self.chat_service.user_service.get_user_preference(account_id, "faq_state", {}) or {}
                last_intent = faq_state.get("last_intent")
                repeat_count = int(faq_state.get("repeat_count", 0)) + 1 if faq_intent and faq_intent == last_intent else 1
                recent = faq_state.get("recent_responses", [])
                quick_faq_response = self.chat_service.user_question_service.get_quick_faq_response(
                    request.question,
                    repeat_count=repeat_count,
                    recent_responses=tuple(recent),
                )
                if quick_faq_response:
                    final_response = self.chat_service._ensure_conservative_empathy(request.question, quick_faq_response)  # noqa: SLF001
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
                    return await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        final_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="quick_faq",
                    )

            main_prompt = self.chat_service.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                user_profile,
                conversation_context,
                prioritize_user_question=prioritize_user_question,
            )
            await self.chat_service.user_service.save_user_profile(account_id, user_profile)

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
                    return await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        natural_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="rule_followup_greeting",
                    )
                if is_ending:
                    last_response = await self.chat_service.dialogue_manager.get_last_response(account_id)
                    timeline_text = self.chat_service.expectation_service.get_closing_timeline_text(user_profile)
                    closing_message = f"好的呀～那你等好消息啦，祝你早日脱单🥰 {timeline_text}，牵线同事联系前会提前约时间，不会打扰你的～"
                    if last_response and closing_message in last_response:
                        return await self.chat_service._build_chat_response(  # noqa: SLF001
                            account_id,
                            user_profile,
                            "",
                            {"collected": False, "all_fields": []},
                            request.dialogId,
                            response_route="ending_template",
                        )
                    return await self.chat_service._build_chat_response(  # noqa: SLF001
                        account_id,
                        user_profile,
                        closing_message,
                        {"collected": False, "all_fields": []},
                        request.dialogId,
                        response_route="ending_template",
                    )

            ai_response = await self.chat_service._call_ai(main_prompt, account_id, request.question)  # noqa: SLF001
            if not ai_response:
                ai_response = await self.chat_service._build_no_ai_response(account_id, user_profile, request.question)  # noqa: SLF001

            extracted_data = self.chat_service.extraction_service.extract_json_from_response(ai_response)
            if not extracted_data:
                extracted_data = self.chat_service._extract_basic_fields_from_message(request.question)  # noqa: SLF001

            profile_result = await self.chat_service.profile_collection_coordinator.process_collection(
                account_id,
                user_profile,
                extracted_data,
                request.question,
            )
            collection_result = profile_result.collection_result

            if collection_result.get("success") and "response" in collection_result:
                final_response = collection_result.get("response", "")
                await self.chat_service._update_conversation_state(  # noqa: SLF001
                    account_id,
                    request.question,
                    final_response,
                    ai_response,
                    track_asked_fields=False,
                )
                user_profile = await self.chat_service.user_service.get_user_profile(account_id)
                return await self.chat_service._build_chat_response(  # noqa: SLF001
                    account_id,
                    user_profile,
                    final_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                )

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
            final_response = self.chat_service._ensure_conservative_empathy(request.question, final_response)  # noqa: SLF001
            final_response = self.chat_service._ensure_humanlike_memory_ack(request.question, user_profile, final_response)  # noqa: SLF001

            field_ask_count_before = dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}
            await self.chat_service._update_conversation_state(  # noqa: SLF001
                account_id,
                request.question,
                final_response,
                ai_response,
                track_asked_fields=not prioritize_user_question,
            )
            user_profile = await self.chat_service.user_service.get_user_profile(account_id)
            total_duration = time.time() - start_time
            logger.info(f"[⏱️ 性能] 请求处理完成: account_id={account_id}, 总耗时={total_duration:.3f}秒")
            return await self.chat_service._build_chat_response(  # noqa: SLF001
                account_id,
                user_profile,
                final_response,
                collection_result,
                request.dialogId,
                field_ask_count_before,
            )
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            from src.core.error_handler import handle_error

            error_response = handle_error(e, context="chat", user_id=account_id)
            return self.chat_service._error_response(error_response.get("error", "处理失败"), request.dialogId)  # noqa: SLF001
