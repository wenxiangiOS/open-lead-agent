import logging
import os
import re
from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import (
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.services.core.chat_service_models import (
    AlreadyEndedPreparation,
    TurnExecutionPreparation,
)
from src.services.core.chat_service_bridge_text_service import ChatServiceBridgeTextService
from src.services.core.chat_service_contact_context_service import (
    ChatServiceContactContextService,
)
from src.services.core.chat_service_pre_generation_resolution_service import (
    ChatServicePreGenerationResolutionService,
)

logger = logging.getLogger(__name__)


class ChatServicePreparationService:
    def __init__(self, host: Any) -> None:
        self.host = host
        self.contact_context_service = ChatServiceContactContextService(host)
        self.pre_generation_resolution_service = ChatServicePreGenerationResolutionService(host)

    async def prepare_turn_execution(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any],
        last_response: str,
        message_count: int,
    ) -> TurnExecutionPreparation:
        understanding = await self.host.unified_turn_understanding_service.analyze(
            TurnUnderstandingInput(
                user_message=user_message,
                last_response=last_response,
                message_count=message_count,
                user_profile=user_profile,
                conversation_context=conversation_context,
                in_contact_flow=self.contact_context_service.has_active_contact_context(
                    user_profile,
                    user_message=user_message,
                ),
                pending_confirmation_field="sex" if getattr(user_profile, "pending_sex_confirmation", None) else None,
            )
        )
        self.pre_generation_resolution_service.resolve_state_before_generation(
            user_profile=user_profile,
            user_message=user_message,
            last_response=last_response,
            understanding=understanding,
        )
        pre_generation_resolution = understanding.pre_generation_resolution
        decision_profile = self.host._build_shadow_profile_for_decision(
            user_profile,
            user_message,
            last_response=last_response,
            understanding_result=understanding,
        )
        turn_decision = await self.host._build_turn_decision(
            user_message,
            decision_profile,
            conversation_context=conversation_context,
            understanding_result=understanding,
        )
        self._apply_post_answer_resume_override(
            turn_decision=turn_decision,
            understanding=understanding,
            user_profile=user_profile,
            decision_profile=decision_profile,
            user_message=user_message,
            last_response=last_response,
        )
        self._apply_confirmation_followup_override(
            turn_decision=turn_decision,
            understanding=understanding,
            decision_profile=decision_profile,
            user_message=user_message,
        )
        self._apply_contextual_short_reply_followup_override(
            turn_decision=turn_decision,
            understanding=understanding,
            decision_profile=decision_profile,
        )
        await self._sync_decision_profile_state(
            user_profile=user_profile,
            decision_profile=decision_profile,
            understanding=understanding,
        )
        response_channel = turn_decision.response_channel
        if self.host._should_force_model_expression(
            understanding=understanding,
            turn_decision=turn_decision,
            user_message=user_message,
        ):
            logger.info(
                "[response_channel_override] quick_faq -> model: turn=%s/%s intent=%s secondary=%s",
                understanding.primary_turn_type,
                understanding.subtype or "-",
                turn_decision.intent,
                ",".join(understanding.secondary_signals or []) or "-",
            )
            turn_decision.response_channel = "model"
            response_channel = "model"
        return TurnExecutionPreparation(
            understanding=understanding,
            decision_profile=decision_profile,
            turn_decision=turn_decision,
            response_channel=response_channel,
            pre_generation_resolution=pre_generation_resolution,
        )

    def _apply_post_answer_resume_override(
        self,
        *,
        turn_decision: TurnDecision,
        understanding: TurnUnderstandingResult,
        user_profile: UserProfile,
        decision_profile: UserProfile,
        user_message: str,
        last_response: str,
    ) -> None:
        """运行时最终兜底：FAQ 答疑后的确认语必须恢复被打断字段。"""
        plan = self.host.unified_turn_understanding_service.followup_planning_layer.resolve_resume_after_faq(
            understanding=understanding,
            turn_decision=turn_decision,
            user_profile=user_profile,
            decision_profile=decision_profile,
            user_message=user_message,
            last_response=last_response,
            resolve_interrupted_followup_field=self.host._resolve_interrupted_followup_field,  # noqa: SLF001
            is_field_covered=self.host.collection_policy.is_field_covered,  # noqa: SLF001
        )
        if not plan.field:
            return

        resume_field = plan.field
        previous_intent = turn_decision.intent
        turn_decision.intent = "general"
        turn_decision.primary_move = "light_followup"
        turn_decision.ask_field = resume_field
        turn_decision.prioritize_user_question = False
        turn_decision.allow_contact_target = False
        turn_decision.allow_medium_target = False
        turn_decision.response_channel = "model"
        turn_decision.user_concern_type = None
        turn_decision.resume_target = resume_field
        turn_decision.resume_applied = True
        decision_profile.resume_profile_target = resume_field
        logger.info(
            "[prepare_resume_after_faq_override] ask_field=%s source=%s previous_intent=%s",
            resume_field,
            plan.source or "-",
            previous_intent,
        )

    def _apply_confirmation_followup_override(
        self,
        *,
        turn_decision: TurnDecision,
        understanding: TurnUnderstandingResult,
        decision_profile: UserProfile,
        user_message: str,
    ) -> None:
        """确认类回答已成功写入字段时，当前轮直接恢复主线，不留空悬承接。"""
        if understanding.primary_turn_type != "confirmation":
            return
        effective_resolved_slots = self._effective_resolved_slots(understanding)
        if not effective_resolved_slots:
            return
        if turn_decision.ask_field:
            return

        policy_decision = self.host.collection_policy.decide(
            decision_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="light_followup",
        )
        next_field = str(getattr(policy_decision, "main_target", "") or "").strip()
        if not next_field:
            contact_policy_decision = self.host.collection_policy.decide(
                decision_profile,
                user_message=user_message,
                allow_contact_target=True,
                allow_medium_target=True,
                prioritize_user_question=False,
                primary_move="light_followup",
            )
            next_field = str(getattr(contact_policy_decision, "main_target", "") or "").strip()
            if next_field:
                policy_decision = contact_policy_decision
        if not next_field:
            return
        if next_field == "contact" and not self.host.collection_policy.can_enter_contact(decision_profile):
            return
        if not self.host.collection_policy.can_actively_ask(decision_profile, next_field):
            return

        turn_decision.intent = "general"
        turn_decision.primary_move = "light_followup"
        turn_decision.ask_field = next_field
        turn_decision.prioritize_user_question = False
        turn_decision.allow_contact_target = next_field == "contact"
        turn_decision.allow_medium_target = bool(getattr(policy_decision, "allow_medium_target", True))
        turn_decision.response_channel = "model"
        turn_decision.user_concern_type = None
        turn_decision.resume_target = next_field
        turn_decision.resume_applied = True
        decision_profile.resume_profile_target = next_field
        logger.info(
            "[prepare_confirmation_followup_override] resolved=%s ask_field=%s",
            sorted(effective_resolved_slots.keys()),
            next_field,
        )

    def _apply_contextual_short_reply_followup_override(
        self,
        *,
        turn_decision: TurnDecision,
        understanding: TurnUnderstandingResult,
        decision_profile: UserProfile,
    ) -> None:
        """短答上下文补回 sex 后，优先回到 age 主线，避免被位置变体顺序打散。"""
        resolution = understanding.pre_generation_resolution
        if resolution is None or resolution.source != "contextual_short_reply_backfill":
            return
        resolved_slots = self._effective_resolved_slots(understanding)
        if "sex" not in resolved_slots:
            return
        if not self.host.collection_policy.can_actively_ask(decision_profile, "age"):
            return
        if str(getattr(turn_decision, "ask_field", "") or "").strip() == "age":
            return

        turn_decision.intent = "general"
        turn_decision.primary_move = "light_followup"
        turn_decision.ask_field = "age"
        turn_decision.prioritize_user_question = False
        turn_decision.allow_contact_target = False
        turn_decision.allow_medium_target = False
        turn_decision.response_channel = "model"
        turn_decision.user_concern_type = None
        turn_decision.resume_target = "age"
        turn_decision.resume_applied = True
        decision_profile.resume_profile_target = "age"
        logger.info(
            "[prepare_contextual_short_reply_override] resolved=%s ask_field=age",
            sorted(resolved_slots.keys()),
        )

    @staticmethod
    def _effective_resolved_slots(understanding: TurnUnderstandingResult) -> Dict[str, str]:
        resolved_slots: Dict[str, str] = dict(getattr(understanding, "resolved_slots", {}) or {})
        persistence_plan = getattr(understanding, "persistence_plan", None)
        if persistence_plan is None:
            return resolved_slots

        for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(field, "field", "") or "").strip()
            scope = str(getattr(field, "scope", "") or "").strip()
            if not field_name or scope not in {"self", "contact", "partner"}:
                continue
            resolved_slots[field_name] = str(getattr(field, "normalized_value", "") or "")
        return resolved_slots

    async def _sync_decision_profile_state(
        self,
        *,
        user_profile: UserProfile,
        decision_profile: UserProfile,
        understanding: TurnUnderstandingResult,
    ) -> None:
        """把只在决策阶段产生、但后续轮次需要依赖的状态同步回真实 profile。"""
        changed = False
        collection_policy = getattr(self.host, "collection_policy", None)

        def _resume_field_needs_followup(field_name: Any) -> bool:
            candidate = str(field_name or "").strip()
            if not candidate or collection_policy is None:
                return bool(candidate)
            return not collection_policy.is_field_covered(decision_profile, candidate)

        decision_resume_target = getattr(decision_profile, "resume_profile_target", None)
        if not _resume_field_needs_followup(decision_resume_target):
            decision_resume_target = None
        if getattr(user_profile, "resume_profile_target", None) != decision_resume_target:
            user_profile.resume_profile_target = decision_resume_target
            changed = True
        if getattr(user_profile, "resume_profile_mode", None) != getattr(decision_profile, "resume_profile_mode", None):
            user_profile.resume_profile_mode = decision_profile.resume_profile_mode
            changed = True
        if getattr(user_profile, "last_user_concern_type", None) != getattr(decision_profile, "last_user_concern_type", None):
            user_profile.last_user_concern_type = decision_profile.last_user_concern_type
            changed = True

        semantic_frame = getattr(understanding, "semantic_frame", None)
        persistence_plan = getattr(understanding, "persistence_plan", None)
        if semantic_frame is not None:
            semantic_summary_payload = {
                "primary_domain": getattr(semantic_frame, "primary_domain", None),
                "acts": list(getattr(semantic_frame, "acts", []) or []),
                "user_questions": [
                    str(getattr(item, "topic", "") or "").strip()
                    for item in list(getattr(semantic_frame, "user_questions", []) or [])
                    if str(getattr(item, "topic", "") or "").strip()
                ],
                "observed_fields": [
                    str(getattr(item, "field", "") or "").strip()
                    for item in list(getattr(semantic_frame, "field_observations", []) or [])
                    if str(getattr(item, "field", "") or "").strip()
                ],
                "pending_fields": [
                    str(getattr(item, "field", "") or "").strip()
                    for item in list(getattr(persistence_plan, "pending_fields", []) or [])
                    if str(getattr(item, "field", "") or "").strip()
                ],
                "resume_target": getattr(persistence_plan, "next_resume_target", None) if persistence_plan is not None else None,
            }
            if dict(getattr(user_profile, "last_semantic_summary", {}) or {}) != semantic_summary_payload:
                user_profile.set_last_semantic_summary(semantic_summary_payload)
                changed = True

        if persistence_plan is not None:
            update_prompt_state = getattr(persistence_plan, "update_prompt_state", None)
            if update_prompt_state is not None:
                prompt_state_payload = {
                    "question_intent": getattr(update_prompt_state, "prompt_type", None),
                    "asked_fields": [getattr(update_prompt_state, "main_target", None)] if getattr(update_prompt_state, "main_target", None) else [],
                    "side_fields": list(getattr(update_prompt_state, "side_targets", []) or []),
                    "expected_scope": (
                        (list(getattr(update_prompt_state, "expected_scopes", []) or []) or ["self"])[0]
                    ),
                    "allow_mixed_answer": bool(getattr(update_prompt_state, "allows_mixed_answer", True)),
                    "resume_target": getattr(persistence_plan, "next_resume_target", None),
                }
                if dict(getattr(user_profile, "last_question_state", {}) or {}) != prompt_state_payload:
                    user_profile.set_last_question_state(prompt_state_payload)
                    changed = True
            resume_target = getattr(persistence_plan, "next_resume_target", None)
            if resume_target and _resume_field_needs_followup(resume_target) and getattr(user_profile, "resume_profile_target", None) != resume_target:
                user_profile.resume_profile_target = resume_target
                changed = True

        current_resume_target = str(getattr(user_profile, "resume_profile_target", "") or "").strip()
        if current_resume_target and not _resume_field_needs_followup(current_resume_target):
            user_profile.clear_resume_profile_target()
            changed = True

        if not changed:
            return

        logger.info(
            "[decision_profile_sync] resume_target=%s resume_mode=%s concern=%s semantic_primary=%s",
            getattr(user_profile, "resume_profile_target", None) or "-",
            getattr(user_profile, "resume_profile_mode", None) or "-",
            getattr(user_profile, "last_user_concern_type", None) or "-",
            str((getattr(user_profile, "last_semantic_summary", {}) or {}).get("primary_domain") or "-"),
        )
        await self.host.user_service.save_user_profile(user_profile.account_id, user_profile)

    async def consume_bridge_back_prefix(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        in_repair_mode: bool,
    ) -> str:
        if in_repair_mode or not user_profile.needs_bridge_back:
            return ""
        bridge_prefix = ChatServiceBridgeTextService.build_bridge_back_prefix(
            user_profile.last_side_topic_type
        )
        logger.info(
            "[bridge_back] account_id=%s, side_topic=%s, prefix=%s...",
            account_id,
            user_profile.last_side_topic_type,
            bridge_prefix[:20],
        )
        user_profile.needs_bridge_back = False
        user_profile.last_side_topic_type = None
        await self.host.user_service.save_user_profile(account_id, user_profile)
        return bridge_prefix

    async def maybe_build_pre_generation_short_circuit_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        message_count: int,
    ) -> tuple[Optional[str], Optional[Dict[str, Any]], UserProfile]:
        route_name, payload, user_profile = await self.pre_generation_resolution_service.maybe_build_resolution_short_circuit_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            turn_understanding=turn_understanding,
        )
        if route_name is not None and payload is not None:
            return route_name, payload, user_profile

        if turn_decision.risk == "high_risk":
            final_response = self.host._sanitize_robotic_tone(
                self.host._get_risk_guard_response(user_message, user_profile)
            )
            user_profile.needs_bridge_back = True
            user_profile.last_side_topic_type = "risk"
            await self.host.user_service.save_user_profile(account_id, user_profile)
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": []},
                dialog_id=dialog_id,
                response_route="risk_guard",
            )
            return "risk_guard", payload, user_profile

        if turn_decision.risk == "boundary":
            if self._is_model_generated_repair_enabled():
                user_profile.needs_bridge_back = False
                user_profile.last_side_topic_type = None
                await self.host.user_service.save_user_profile(account_id, user_profile)
                logger.info("[model_generated_repair] boundary handled by model route")
                return None, None, user_profile
            final_response = self.host._get_boundary_pause_response(user_message)
            final_response = self.host._apply_context_ack_policy(
                final_response,
                turn_decision,
                user_profile,
                user_message,
            )
            final_response = self.host._sanitize_robotic_tone(final_response)
            user_profile.needs_bridge_back = True
            user_profile.last_side_topic_type = "boundary"
            await self.host.user_service.save_user_profile(account_id, user_profile)
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": []},
                dialog_id=dialog_id,
                response_route="boundary_pause",
            )
            return "boundary_pause", payload, user_profile

        if turn_decision.risk == "withdraw" or (
            self.host._is_withdraw_or_stop_message(user_message)
            and turn_understanding.primary_turn_type != "risk_guard"
        ):
            user_profile.increment_ask_count("conversation_end_intent")
            final_response, should_close = self.host._build_withdraw_response(
                user_profile,
                user_message=user_message,
            )
            final_response = self.host._sanitize_robotic_tone(final_response)
            if should_close:
                user_profile.conversation_ended = True
                user_profile.needs_bridge_back = False
                user_profile.last_side_topic_type = None
            await self.host.user_service.save_user_profile(account_id, user_profile)
            route_name = "withdraw_close" if should_close else "withdraw_retain"
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": []},
                dialog_id=dialog_id,
                response_route=route_name,
            )
            return route_name, payload, user_profile

        if turn_decision.intent == "complaint":
            if self._is_model_generated_repair_enabled():
                user_profile.needs_bridge_back = False
                user_profile.last_side_topic_type = None
                user_profile.complaint_cooldown_until = message_count + 2
                await self.host.user_service.save_user_profile(account_id, user_profile)
                logger.info("[model_generated_repair] complaint handled by model route")
                return None, None, user_profile
            final_response = self.host._get_complaint_repair_response(user_message)
            final_response = self.host._apply_context_ack_policy(
                final_response,
                turn_decision,
                user_profile,
                user_message,
            )
            final_response = self.host._sanitize_robotic_tone(final_response)
            user_profile.needs_bridge_back = False
            user_profile.last_side_topic_type = None
            user_profile.complaint_cooldown_until = message_count + 2
            await self.host.user_service.save_user_profile(account_id, user_profile)
            payload = await self.host.build_short_circuit_payload(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                final_response=final_response,
                collection_result={"all_fields": []},
                dialog_id=dialog_id,
                response_route="complaint_repair",
            )
            return "complaint_repair", payload, user_profile

        return None, None, user_profile

    @staticmethod
    def _is_model_generated_repair_enabled() -> bool:
        raw = str(os.getenv("MQ_MODEL_GENERATED_REPAIR_ENABLED", "1") or "").strip().lower()
        return raw not in {"0", "false", "off", "no"}

    @staticmethod
    def _normalize_compact_text(text: str) -> str:
        return re.sub(r"[\s，,。！？!?~～、:：;；'\"（）()]+", "", str(text or "").lower()).strip()

    def _looks_like_already_ended_reopen(self, text: str) -> bool:
        message = str(text or "").strip()
        if not message:
            return False
        reopen_patterns = (
            "继续聊",
            "继续问",
            "继续了解",
            "重新聊",
            "重新开始",
            "接着聊",
            "往下聊",
            "我再补",
            "再补一个",
            "补个微信",
            "补个电话",
            "补充一下",
        )
        return any(pattern in message for pattern in reopen_patterns) or self.host._is_resume_profile_collection_message(message)

    def _is_low_info_confirmation_text(self, text: str) -> bool:
        normalized = self._normalize_compact_text(text)
        if normalized in {
            "好",
            "好的",
            "好呢",
            "嗯",
            "嗯嗯",
            "ok",
            "okay",
            "收到",
            "行",
            "知道了",
            "好哒",
            "好的呢",
            "谢谢",
            "谢谢啦",
            "感谢",
            "感谢啦",
            "谢谢你",
            "感谢你",
            "好呢感谢",
            "好呢谢谢",
            "好的感谢",
            "好的谢谢",
            "好哒感谢",
            "好哒谢谢",
        }:
            return True
        return bool(
            re.fullmatch(
                r"(好|好的|好呢|好哒|嗯|嗯嗯|ok|okay|收到|收到啦|行|知道了|谢谢|谢谢啦|感谢|感谢啦|谢谢你|感谢你)+",
                normalized,
            )
        )

    def _is_already_ended_reply_variant(self, text: str, base_response: str) -> bool:
        normalized = self._normalize_compact_text(text)
        if not normalized:
            return False
        if self._looks_like_terminal_reply(text):
            return True
        variants = {
            self._normalize_compact_text(base_response),
            self._normalize_compact_text("嗯嗯"),
            self._normalize_compact_text("好呀"),
            self._normalize_compact_text("收到啦"),
        }
        return normalized in variants

    def _looks_like_terminal_reply(self, text: str) -> bool:
        normalized = self._normalize_compact_text(text)
        if not normalized:
            return False
        markers = (
            "等好消息",
            "祝你早日脱单",
            "匹配一般1-8小时",
            "匹配一般18小时",
            "匹配一般1-2天",
            "匹配一般12天",
            "提前约时间",
            "不打扰你",
            "会联系你",
            "优先打你留的电话联系你",
            "通过微信联系你",
        )
        return any(self._normalize_compact_text(marker) in normalized for marker in markers)

    async def _classify_already_ended_intent(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        recent_responses: list[str] | tuple[str, ...] | None = None,
    ) -> str:
        message = str(user_message or "").strip()
        if not message:
            return "end_ack"

        if self._is_low_info_confirmation_text(message) or self.host._is_acknowledgement_only_message(message):
            return "end_ack"

        if self.host._is_withdraw_or_stop_message(message):
            return "end_ack"

        if self.host._get_priority_question_response(
            message,
            user_profile,
            repeat_count=1,
            recent_responses=recent_responses or (),
            understanding_result=None,
        ):
            return "end_faq"

        if self._looks_like_already_ended_reopen(message):
            return "end_reopen"

        extracted = self.host.turn_understanding_service._extract_deterministic_profile_fields(message)  # noqa: SLF001
        if extracted or self.host.turn_understanding_service._extract_simple_partner_requirement(message):  # noqa: SLF001
            return "end_profile_update"

        last_response = str((recent_responses or [])[-1] or "").strip() if recent_responses else ""
        understanding = await self.host.unified_turn_understanding_service.analyze(
            TurnUnderstandingInput(
                user_message=message,
                last_response=last_response,
                message_count=len(recent_responses or []),
                user_profile=user_profile,
                conversation_context={"recent_responses": list(recent_responses or [])},
                in_contact_flow=self.contact_context_service.has_active_contact_context(
                    user_profile,
                    user_message=message,
                ),
                pending_confirmation_field="sex" if getattr(user_profile, "pending_sex_confirmation", None) else None,
            )
        )

        if understanding.primary_turn_type == "faq_concern":
            return "end_faq"
        if understanding.resume_profile_collection:
            return "end_reopen"
        if understanding.primary_turn_type in {"profile_answer", "contact_answer"}:
            return "end_profile_update"
        if understanding.primary_turn_type in {"confirmation", "invalid_input", "opening"}:
            return "end_ack"
        return "end_unclear"

    def _build_already_ended_reply(
        self,
        user_message: str,
        base_response: str,
        recent_responses: list[str] | tuple[str, ...] | None = None,
    ) -> str:
        if not self._is_low_info_confirmation_text(user_message):
            return base_response

        recent = [str(item or "").strip() for item in (recent_responses or []) if str(item or "").strip()]
        if not recent:
            return base_response

        trailing_ended_replies = 0
        for item in reversed(recent):
            if self._is_already_ended_reply_variant(item, base_response):
                trailing_ended_replies += 1
                continue
            break

        normalized_base = self._normalize_compact_text(base_response)
        normalized_last = self._normalize_compact_text(recent[-1])
        variants = ("嗯嗯", "好呀", "收到啦")
        if trailing_ended_replies >= 2:
            return ""
        if normalized_last == normalized_base:
            idx = len(recent) % len(variants)
            return variants[idx]
        if self._is_already_ended_reply_variant(recent[-1], base_response):
            return variants[trailing_ended_replies % len(variants)]
        return base_response

    def _build_already_ended_question_reply(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        recent_responses: list[str] | tuple[str, ...] | None = None,
    ) -> str:
        faq_response = self.host._get_priority_question_response(
            user_message,
            user_profile,
            repeat_count=1,
            recent_responses=recent_responses or (),
        )
        return str(faq_response or "").strip()

    async def maybe_build_already_ended_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        is_new_user_session: bool,
    ) -> Optional[AlreadyEndedPreparation]:
        if not is_new_user_session and user_profile.conversation_ended:
            conversation_context = await self.host.dialogue_manager.get_conversation_context(account_id)
            recent_responses = conversation_context.get("recent_responses") or []
            last_response = str(recent_responses[-1] or "").strip() if recent_responses else ""
            ended_intent = await self._classify_already_ended_intent(
                user_message=user_message,
                user_profile=user_profile,
                recent_responses=recent_responses,
            )
            if ended_intent in {"end_reopen", "end_profile_update"} and self.host._can_end_with_contact_completion(user_profile):
                ended_intent = "end_ack"
            if ended_intent in {"end_reopen", "end_profile_update"}:
                logger.info("[already_ended_intent] reopen session: intent=%s", ended_intent)
                user_profile.conversation_ended = False
                await self.host.user_service.save_user_profile(account_id, user_profile)
                return None

            if ended_intent == "end_ack" and last_response and self._looks_like_terminal_reply(last_response):
                final_response = self._build_already_ended_reply(user_message, last_response, recent_responses)
                if not self._looks_like_terminal_reply(final_response):
                    final_response = self.host._sanitize_robotic_tone(final_response)
                payload = {
                    "success": True,
                    "response": final_response,
                    "dialogId": dialog_id,
                    "meta": {"route": "already_ended"},
                }
                await self.host._update_conversation_state(
                    account_id,
                    user_message,
                    final_response,
                    final_response,
                    track_asked_fields=False,
                )
                return AlreadyEndedPreparation(
                    route_name="already_ended",
                    final_response=final_response,
                    payload=payload,
                )

        if user_profile.conversation_ended and not is_new_user_session:
            conversation_context = await self.host.dialogue_manager.get_conversation_context(account_id)
            recent_responses = conversation_context.get("recent_responses") or []
            ended_intent = await self._classify_already_ended_intent(
                user_message=user_message,
                user_profile=user_profile,
                recent_responses=recent_responses,
            )
            if ended_intent == "end_faq":
                faq_response = self._build_already_ended_question_reply(
                    user_message=user_message,
                    user_profile=user_profile,
                    recent_responses=recent_responses,
                )
                if faq_response:
                    final_response = self.host._sanitize_robotic_tone(faq_response)
                    await self.host._update_conversation_state(
                        account_id,
                        user_message,
                        final_response,
                        final_response,
                        track_asked_fields=False,
                    )
                    reloaded_profile = await self.host.user_service.get_user_profile(account_id)
                    payload = await self.host._build_chat_response(
                        account_id,
                        reloaded_profile,
                        final_response,
                        {"all_fields": [], "ending_info": {"scenario": "already_ended"}},
                        dialog_id,
                        dict(reloaded_profile.field_ask_count) if reloaded_profile.field_ask_count else {},
                        response_route="already_ended",
                    )
                    return AlreadyEndedPreparation(
                        route_name="already_ended",
                        final_response=final_response,
                        payload=payload,
                    )
            if self.host._can_end_with_contact_completion(user_profile):
                base_response = self.host._get_contact_completion_ending_response(user_profile)
                final_response = self._build_already_ended_reply(
                    user_message,
                    base_response,
                    recent_responses,
                )
                if not self._looks_like_terminal_reply(final_response):
                    final_response = self.host._sanitize_robotic_tone(final_response)
                ending_scenario = "normal_complete"
            elif self.host._can_end_without_contact(user_profile):
                base_response = self.host._get_no_contact_completion_response()
                final_response = self.host._sanitize_robotic_tone(
                    self._build_already_ended_reply(
                        user_message,
                        base_response,
                        recent_responses,
                    )
                )
                ending_scenario = "contact_closed"
            else:
                final_response = self.host._sanitize_robotic_tone(
                    self._build_already_ended_reply(
                        user_message,
                        self.host.ending_service.get_ending_response("already_ended") or "",
                        recent_responses,
                    )
                )
                ending_scenario = "already_ended"
            await self.host._update_conversation_state(
                account_id,
                user_message,
                final_response,
                final_response,
                track_asked_fields=False,
            )
            reloaded_profile = await self.host.user_service.get_user_profile(account_id)
            payload = await self.host._build_chat_response(
                account_id,
                reloaded_profile,
                final_response,
                {"all_fields": [], "ending_info": {"scenario": ending_scenario}},
                dialog_id,
                dict(reloaded_profile.field_ask_count) if reloaded_profile.field_ask_count else {},
                response_route="already_ended",
            )
            return AlreadyEndedPreparation(
                route_name="already_ended",
                final_response=final_response,
                payload=payload,
            )

        return None

    async def maybe_build_quick_faq_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        decision_profile: UserProfile,
        conversation_context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if turn_decision.response_channel != "quick_faq" or turn_decision.intent in {"boundary", "complaint"}:
            return None

        final_response = self.host._get_priority_question_response(
            user_message,
            decision_profile,
            repeat_count=1,
            recent_responses=conversation_context.get("recent_responses") or (),
            understanding_result=turn_understanding,
        ) or self._build_quick_faq_direct_response(
            account_id=account_id,
            user_message=user_message,
            turn_understanding=turn_understanding,
        )
        should_resume_after_quick_answer = (
            final_response
            and turn_understanding.primary_turn_type == "faq_concern"
            and not self.host._looks_like_strong_concern_interrupt(user_message)
        )
        if should_resume_after_quick_answer:
            final_response = self.host._build_resume_after_interrupt_response(
                final_response,
                decision_profile,
                user_message=user_message,
                last_response=str((conversation_context.get("recent_responses") or [""])[-1] or ""),
            )
        final_response = self.host._apply_priority_question_guard(
            final_response,
            turn_decision,
            user_message,
        )
        final_response = self.host._apply_context_ack_policy(
            final_response,
            turn_decision,
            decision_profile,
            user_message,
        )
        final_response = self.host._ensure_humanlike_memory_ack(
            user_message,
            decision_profile,
            final_response,
        )
        if turn_decision.response_channel != "quick_faq":
            final_response = self.host._sanitize_robotic_tone(final_response)

        user_profile, collection_result = await self._apply_quick_faq_collection(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            turn_understanding=turn_understanding,
            conversation_context=conversation_context,
        )
        user_profile.needs_bridge_back = True
        user_profile.last_side_topic_type = "faq"
        await self.host.user_service.save_user_profile(account_id, user_profile)
        return await self.host.build_short_circuit_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            collection_result=collection_result,
            dialog_id=dialog_id,
            response_route="quick_faq",
        )

    async def _apply_quick_faq_collection(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_understanding: TurnUnderstandingResult,
        conversation_context: Dict[str, Any],
    ) -> tuple[UserProfile, Dict[str, Any]]:
        last_response = str((conversation_context.get("recent_responses") or [""])[-1] or "")
        rule_extracted_data = self.host._extract_turn_level_fields(  # noqa: SLF001
            user_message,
            understanding_result=turn_understanding,
            last_response=last_response,
        )
        fused_extracted_data, extraction_meta = self.host._fuse_extracted_fields(  # noqa: SLF001
            {},
            {
                **dict(rule_extracted_data or {}),
                **(
                    {"age": int(str((rule_extracted_data or {}).get("age") or "").strip())}
                    if isinstance((rule_extracted_data or {}).get("age"), str)
                    and str((rule_extracted_data or {}).get("age") or "").strip().isdigit()
                    else {}
                ),
            },
            user_message,
            user_profile=user_profile,
            last_response=last_response,
            understanding_result=turn_understanding,
        )
        if not fused_extracted_data:
            return user_profile, {"all_fields": []}

        profile_result = await self.host.profile_collection_coordinator.process_collection(
            account_id,
            user_profile,
            fused_extracted_data,
            user_message,
            extraction_meta=extraction_meta,
            turn_id=int(conversation_context.get("message_count", 0)) + 1,
            understanding_result=turn_understanding,
        )
        collection_result = self.host.generation_service._merge_persistence_plan_into_collection_result(  # noqa: SLF001
            collection_result=profile_result.collection_result,
            understanding_result=turn_understanding,
            user_profile=getattr(profile_result, "user_profile", None) or user_profile,
        )
        rich_partner_requirement = str(fused_extracted_data.get("partner_requirement") or "").strip()
        if rich_partner_requirement and not any(
            isinstance(item, dict) and str(item.get("field") or "").strip() == "partner_requirement"
            for item in list(collection_result.get("all_fields") or [])
        ):
            display_fields = dict(collection_result.get("display_fields") or {})
            display_fields.setdefault("partner_requirement", rich_partner_requirement)
            collection_result["display_fields"] = display_fields
        refreshed_profile = await self.host.user_service.get_user_profile(account_id)
        logger.info(
            "[quick_faq_collection] applied_fields=%s",
            [
                str(item.get("field") or "").strip()
                for item in list(collection_result.get("all_fields") or [])
                if isinstance(item, dict) and str(item.get("field") or "").strip()
            ],
        )
        return refreshed_profile, collection_result

    def _build_quick_faq_direct_response(
        self,
        *,
        account_id: str,
        user_message: str,
        turn_understanding: TurnUnderstandingResult,
    ) -> str:
        """quick_faq 直返只走确定性文案，不再依赖已删除的 no-ai fallback。"""
        seed_hint = f"{account_id}:quick_faq:{str(user_message or '').strip()}"
        if turn_understanding.primary_turn_type != "opening":
            return ""
        if turn_understanding.subtype == "greeting":
            return self.host.greeting_service.get_open_self_intro_response(seed_hint=seed_hint)
        if turn_understanding.subtype == "opening_clarify":
            return self.host.greeting_service.get_opening_clarify_response(seed_hint=seed_hint)
        if turn_understanding.subtype == "matchmaking_intent":
            return self.host._build_opening_matchmaking_response(
                user_message=user_message,
                seed_hint=seed_hint,
                understanding=turn_understanding,
            )
        return ""
