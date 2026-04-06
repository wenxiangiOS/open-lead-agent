import logging
import re
from typing import Any, Dict

from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService
from src.utils.validators import ContactValidator, PhoneValidator, WechatValidator

logger = logging.getLogger(__name__)


class ChatServiceContactValidationFlowService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def _resolve_contact_attempt_context(user_profile, next_action_value: str) -> str:
        action_value = str(next_action_value or "").strip()
        if action_value in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}:
            return action_value

        last_requested_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
        if last_requested_type == "phone":
            return "ask_phone"
        if last_requested_type == "wechat":
            return "ask_wechat"
        return action_value

    def classify_contact_candidate(
        self,
        *,
        user_message: str,
        user_profile,
        next_action_value: str,
    ) -> Dict[str, str]:
        message = str(user_message or "").strip()
        if not message:
            return {}

        effective_action = self._resolve_contact_attempt_context(user_profile, next_action_value)
        fallback_contact = self.host.turn_understanding_service._extract_contact_candidate(message)  # noqa: SLF001
        fallback_candidate = str((fallback_contact or {}).get("value") or "").strip()
        fallback_hint = str((fallback_contact or {}).get("type") or "").strip()

        candidate, inferred_hint = self.host._infer_contact_attempt_from_context(message, effective_action)
        if not candidate and fallback_candidate:
            candidate = fallback_candidate
            inferred_hint = fallback_hint
        if not candidate:
            return {}

        hinted_type = "wechat" if inferred_hint == "wechat" else "phone"
        if hinted_type == "wechat":
            is_valid, _ = WechatValidator.is_valid(candidate)
            return {
                "candidate": candidate,
                "contact_type": "wechat",
                "classification": "valid_wechat" if is_valid else "invalid_wechat_candidate",
            }

        digits = re.sub(r"\D", "", candidate)
        if digits.startswith("86") and len(digits) == 13 and digits[2] == "1":
            digits = digits[2:]
        if PhoneValidator.is_valid(digits)[0]:
            return {
                "candidate": digits,
                "contact_type": "phone",
                "classification": "valid_phone",
            }
        return {
            "candidate": candidate,
            "contact_type": "phone",
            "classification": "invalid_phone_candidate",
        }

    async def handle_contact_validation(
        self,
        account_id: str,
        user_profile,
        collection_result: Dict[str, Any],
        ai_response: str,
        user_message: str = "",
    ) -> str:
        """处理联系方式验证。"""
        self.host._last_validation_feedback_meta = None
        collected_contact = None
        collected_phone = None
        collected_wechat = None
        for field_info in collection_result.get("all_fields", []):
            if field_info.get("field") == "contact":
                collected_contact = field_info.get("value")
            elif field_info.get("field") == "phone":
                collected_phone = field_info.get("value")
            elif field_info.get("field") == "wechat":
                collected_wechat = field_info.get("value")

        fallback_contacts = self.host._extract_contacts_from_message(user_message)
        fallback_contact = self.host.turn_understanding_service._extract_contact_candidate(user_message)  # noqa: SLF001
        fallback_candidate = fallback_contact["value"] if fallback_contact else None
        fallback_hint = fallback_contact["type"] if fallback_contact else None
        fallback_contaminated = bool(fallback_contact.get("contaminated")) if fallback_contact else False
        next_action = self.host.contact_service.get_next_action(user_profile, user_message)
        candidate_meta = self.classify_contact_candidate(
            user_message=user_message,
            user_profile=user_profile,
            next_action_value=getattr(next_action, "value", str(next_action)),
        )
        contact_value = collected_phone or collected_contact
        invalid_contact_attempt = collection_result.get("invalid_contact_attempt") or fallback_candidate

        if contact_value is None and fallback_contacts.get("phone"):
            contact_value = fallback_contacts["phone"]
        if collected_wechat is None and fallback_contacts.get("wechat"):
            collected_wechat = fallback_contacts["wechat"]

        if contact_value is None and collected_wechat is None and fallback_candidate:
            is_valid_fallback, fallback_type, _ = ContactValidator.is_valid_contact(fallback_candidate)
            if is_valid_fallback and not fallback_contaminated:
                if fallback_hint == "wechat":
                    collected_wechat = fallback_candidate
                else:
                    contact_value = fallback_candidate
                logger.info(
                    "[联系方式兜底] 从原始消息恢复联系方式: type=%s, value=%s",
                    fallback_hint or fallback_type,
                    fallback_candidate,
                )
            elif is_valid_fallback and fallback_contaminated:
                logger.info(
                    "[联系方式兜底] 检测到污染输入，拒绝自动收集: type=%s, value=%s",
                    fallback_hint or fallback_type,
                    fallback_candidate,
                )

        if contact_value is None and collected_wechat is None and not invalid_contact_attempt:
            effective_action = self._resolve_contact_attempt_context(user_profile, next_action.value)
            hinted_attempt, hinted_type = self.host._infer_contact_attempt_from_context(user_message, effective_action)
            if hinted_attempt:
                invalid_contact_attempt = hinted_attempt
                fallback_hint = fallback_hint or hinted_type

        if contact_value is None and collected_wechat is None and candidate_meta:
            classification = candidate_meta.get("classification")
            candidate_value = candidate_meta.get("candidate")
            candidate_type = candidate_meta.get("contact_type")
            if classification == "valid_phone":
                contact_value = candidate_value
            elif classification == "valid_wechat":
                collected_wechat = candidate_value
            elif classification in {"invalid_phone_candidate", "invalid_wechat_candidate"}:
                invalid_contact_attempt = candidate_value
                fallback_hint = candidate_type

        if candidate_meta and candidate_meta.get("classification") in {"invalid_phone_candidate", "invalid_wechat_candidate"}:
            candidate_value = str(candidate_meta.get("candidate") or "").strip()
            if candidate_value and str(contact_value or "").strip() == candidate_value:
                invalid_contact_attempt = candidate_value
                contact_value = None
                collected_contact = None

        contact_value = contact_value or collected_phone or collected_contact
        logger.debug(
            "[联系方式检查] collected_contact=%s, collected_wechat=%s, all_fields=%s",
            contact_value,
            collected_wechat,
            collection_result.get("all_fields", []),
        )

        if collected_wechat:
            user_profile.wechat = collected_wechat
            user_profile.wechat_collected = True
            user_profile.pending_contact_candidate = None
            user_profile.pending_contact_field = None
            user_profile.pending_contact_hint = None
            self.host.contact_service.reset_invalid_input(user_profile, "wechat")
            self.host.contact_service.is_contact_complete(user_profile)
            is_hong_user = self.host._is_hong_user(user_profile.location)
            if not is_hong_user:
                user_profile.collection_progress["contact"] = True
            await self.host.user_service.save_user_profile(account_id, user_profile)
            logger.info("[微信收集] 设置 wechat_collected=True, 香港用户=%s", is_hong_user)

        if contact_value is None and collected_wechat is None:
            if invalid_contact_attempt:
                logger.debug("[联系方式检查] 检测到疑似无效联系方式输入: %s", invalid_contact_attempt)
                if fallback_hint == "wechat" or "微信" in user_message:
                    is_valid, error_info = await self.host.validation_service.validate_wechat(
                        invalid_contact_attempt,
                        user_profile,
                        account_id,
                        self.host.user_service,
                    )
                else:
                    is_valid, error_info, _ = await self.host.validation_service.validate_contact(
                        invalid_contact_attempt,
                        user_profile,
                        account_id,
                        self.host.user_service,
                    )
                if not is_valid:
                    return await self.host._build_validation_feedback(
                        account_id=account_id,
                        user_profile=user_profile,
                        user_message=user_message,
                        invalid_value=invalid_contact_attempt,
                        error_info=error_info,
                    )

            profile_complete_or_exhausted = self.host._is_profile_collection_complete_or_exhausted(user_profile)
            contact_collected = (
                user_profile.collection_progress.get("contact", False)
                or (user_profile.wechat and user_profile.wechat_collected)
            )

            if profile_complete_or_exhausted and contact_collected:
                from src.services.collection.contact_collection_service import NextAction

                next_action = self.host.contact_service.get_next_action(user_profile)
                if not self.host.contact_service.is_contact_complete(user_profile) and next_action not in [
                    NextAction.NONE,
                    NextAction.END_CONVERSATION,
                ]:
                    logger.info("[收尾检查] 联系方式收集流程未结束，next_action=%s", next_action.value)
                    return ai_response

                logger.info("[收尾检查] 所有字段已完成，优先返回 AI 原回复")
                return ai_response

            return ai_response

        await self.host.input_fallback_service.reset_confirm_count(account_id)
        logger.info("[联系方式验证] 用户提供了联系方式，重置确认词计数器")

        if contact_value is None and collected_wechat:
            has_phone_already = bool(user_profile.phone_collected and user_profile.phone)
            user_message_text = str(user_message or "")
            mentions_phone = any(marker in user_message_text for marker in ("电话", "手机", "手机号", "号码"))

            if (
                not has_phone_already
                and not user_profile.rejected_phone
                and user_profile.phone_ask_count > 0
                and not mentions_phone
            ):
                logger.info(
                    "[微信收集] 用户主动先给微信，重置未兑现的电话询问计数: phone_ask_count=%s",
                    user_profile.phone_ask_count,
                )
                self.host.contact_service.clear_pending_request_state(user_profile, "phone")
                await self.host.user_service.save_user_profile(account_id, user_profile)

            next_action = self.host.contact_service.get_next_action(user_profile)
            contact_collected = (
                user_profile.collection_progress.get("contact", False)
                or (user_profile.wechat and user_profile.wechat_collected)
            )
            profile_complete_or_exhausted = self.host._is_profile_collection_complete_or_exhausted(user_profile)

            if next_action.value in {"ask_phone", "persuade_phone"}:
                logger.info("[微信收集] 按状态机继续电话流程: next_action=%s", next_action.value)
                return ChatServiceContactTextService.build_contact_followup_response(next_action.value, "wechat")

            if (
                profile_complete_or_exhausted
                and contact_collected
                and self.host.contact_service.is_contact_complete(user_profile)
            ):
                self.host.contact_service.clear_contact_context_state(user_profile)
                logger.info("[微信收集] 联系方式流程已结束，进入统一收尾链: next_action=%s", next_action.value)
                await self.host._mark_remaining_fields_as_skipped(account_id, user_profile)
                collection_result["ending_info"] = self.host.ending_service.build_ending_info("normal_complete", user_profile)
                await self.host.user_service.save_user_profile(account_id, user_profile)
                return ai_response

            if self.host.contact_service.is_contact_complete(user_profile):
                self.host.contact_service.clear_contact_context_state(user_profile)
                await self.host.user_service.save_user_profile(account_id, user_profile)
                return self.host._get_contact_terminal_or_resume_response(user_profile, str(user_message or ""))

            if not self.host.collection_policy.has_serviceable_profile(user_profile):
                decision = self.host.collection_policy.decide(user_profile, allow_contact_target=False)
                logger.info("[微信收集] 资料未达到可服务阈值，继续推进字段: target=%s", decision.main_target)
                return ChatServiceContactTextService.build_contact_collection_ack("wechat")

            decision = self.host.collection_policy.decide(user_profile, allow_contact_target=False)
            logger.info(
                "[微信收集] 不进入电话追问，继续推进字段: next_action=%s, target=%s",
                next_action.value,
                decision.main_target,
            )
            return ChatServiceContactTextService.build_contact_collection_ack("wechat")

        logger.info("[联系方式验证] 开始验证电话: %s", contact_value)
        is_valid, error_info, _success_msg = await self.host.validation_service.validate_contact(
            contact_value,
            user_profile,
            account_id,
            self.host.user_service,
        )

        if is_valid:
            logger.info("[联系方式验证成功]")
            normalized_contact = str(contact_value or "").strip()
            _, contact_type, _ = ContactValidator.is_valid_contact(normalized_contact)
            normalized_phone = re.sub(r"\D", "", normalized_contact)
            if normalized_phone.startswith("86") and len(normalized_phone) == 13 and normalized_phone[2] == "1":
                normalized_phone = normalized_phone[2:]

            if contact_type == "wechat":
                user_profile.wechat = normalized_contact
                user_profile.wechat_collected = True
                self.host.contact_service.reset_invalid_input(user_profile, "wechat")
                user_profile.contact = user_profile.get_contact_status()
                await self.host.user_service.save_user_profile(account_id, user_profile)
                next_action = self.host.contact_service.get_next_action(user_profile, user_message)
                if next_action.value in {"ask_phone", "persuade_phone"}:
                    if ChatServiceContactTextService.response_mentions_phone_request(ai_response):
                        return ai_response
                    logger.info("[微信收集] AI 原回复未顺带追问电话，改用联系方式 followup 回复")
                    return ChatServiceContactTextService.build_contact_followup_response(
                        next_action.value,
                        "wechat",
                    )
                if self.host.contact_service.is_contact_complete(user_profile):
                    self.host.contact_service.clear_contact_context_state(user_profile)
                    await self.host.user_service.save_user_profile(account_id, user_profile)
                    return self.host._get_contact_terminal_or_resume_response(user_profile, str(user_message or ""))
                return ai_response

            user_profile.phone = normalized_phone or normalized_contact
            user_profile.phone_collected = True
            user_profile.pending_contact_candidate = None
            user_profile.pending_contact_field = None
            user_profile.pending_contact_hint = None
            self.host.contact_service.reset_invalid_input(user_profile, "phone")
            self.host.contact_service.is_contact_complete(user_profile)
            user_profile.contact = user_profile.get_contact_status()
            logger.info("[联系方式验证] 设置 phone=%s, phone_collected=True", user_profile.phone)

            user_profile.phone_ask_count = 0
            await self.host.user_service.save_user_profile(account_id, user_profile)
            logger.info("[联系方式验证] 重置 phone_ask_count = 0 并保存")

            next_action = self.host.contact_service.get_next_action(user_profile)
            logger.info("[联系方式验证] 下一步动作: %s", next_action)

            if next_action.value == "ask_wechat":
                logger.info(
                    "[联系方式验证] 电话已收集，需要询问微信，wechat_ask_count=%s",
                    user_profile.wechat_ask_count,
                )
                if ChatServiceContactTextService.response_mentions_wechat_request(ai_response):
                    return ai_response
                logger.info("[联系方式验证] AI 原回复未顺带追问微信，改用联系方式 followup 回复")
                return ChatServiceContactTextService.build_contact_followup_response(
                    next_action.value,
                    "phone",
                )
            if next_action.value == "persuade_wechat":
                logger.info(
                    "[联系方式验证] 电话已收集，需要继续争取微信，wechat_ask_count=%s",
                    user_profile.wechat_ask_count,
                )
                if ChatServiceContactTextService.response_mentions_wechat_request(ai_response):
                    return ai_response
                logger.info("[联系方式验证] AI 原回复未顺带争取微信，改用联系方式 followup 回复")
                return ChatServiceContactTextService.build_contact_followup_response(
                    next_action.value,
                    "phone",
                )

            if user_profile.wechat_collected and user_profile.wechat and self.host.contact_service.is_contact_complete(user_profile):
                self.host.contact_service.clear_contact_context_state(user_profile)
                logger.info("[联系方式验证] 电话和微信均已收齐，返回稳定双联系方式确认")
                return ChatServiceContactTextService.build_dual_contact_ack()

            contact_collected = (
                user_profile.collection_progress.get("contact", False)
                or (user_profile.wechat and user_profile.wechat_collected)
            )
            profile_complete_or_exhausted = self.host._is_profile_collection_complete_or_exhausted(user_profile)

            if profile_complete_or_exhausted and contact_collected:
                self.host.contact_service.clear_contact_context_state(user_profile)
                logger.info("[核心字段] 全部收集完成，进入统一收尾链")
                await self.host._mark_remaining_fields_as_skipped(account_id, user_profile)
                collection_result["ending_info"] = self.host.ending_service.build_ending_info("normal_complete", user_profile)
                await self.host.user_service.save_user_profile(account_id, user_profile)
                return ai_response
            if self.host.contact_service.is_contact_complete(user_profile):
                self.host.contact_service.clear_contact_context_state(user_profile)
                await self.host.user_service.save_user_profile(account_id, user_profile)
                return self.host._get_contact_terminal_or_resume_response(user_profile, str(user_message or ""))

            decision = self.host.collection_policy.decide(user_profile, allow_contact_target=False)
            logger.info("[核心字段] 资料未完成，继续推进字段: %s", decision.main_target)
            return ai_response

        user_profile.contact = None
        user_profile.collection_progress["contact"] = False
        await self.host.user_service.save_user_profile(account_id, user_profile)
        logger.info("[联系方式验证失败] 已撤销保存")
        return await self.host._build_validation_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=contact_value,
            error_info=error_info,
        )
