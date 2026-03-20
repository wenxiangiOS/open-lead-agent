from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.modules.shared.models.chat_flow import RuleCheckResult
from src.utils.validators import InputValidator

if TYPE_CHECKING:
    from src.models.requests import ChatRequest
    from src.models.user_profile import UserProfile
    from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)


@dataclass
class ConversationRuleContext:
    chat_service: "ChatService"
    request: "ChatRequest"
    user_profile: "UserProfile"
    is_first_user_turn: bool
    message_count: int

    @property
    def account_id(self) -> str:
        return self.request.accountId

    @property
    def user_message(self) -> str:
        return self.request.question


class ConversationRule:
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        raise NotImplementedError


class ConversationEndedRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        if not ctx.user_profile.conversation_ended:
            return RuleCheckResult(handled=False)

        logger.info(f"[对话已结束] 用户继续发消息，返回简短告别: {ctx.account_id}")
        sex = ctx.user_profile.sex
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
        last_response = await ctx.chat_service.dialogue_manager.get_last_response(ctx.account_id) or ""
        if "有需要随时再来找我哦～拜拜" in last_response or "下次再聊～拜拜啦" in last_response:
                response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
                    ctx.account_id,
                    ctx.user_profile,
                    "",
                    {"collected": False, "all_fields": []},
                    ctx.request.dialogId,
                    response_route="rule_conversation_ended",
                )
        else:
            response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
                ctx.account_id,
                ctx.user_profile,
                f"好的～{call_name}，那先这样啦～有需要随时再来找我哦～拜拜👋",
                {"collected": False, "all_fields": []},
                ctx.request.dialogId,
                response_route="rule_conversation_ended",
            )
        return RuleCheckResult(handled=True, response_payload=response_payload)


class CompletedCollectionAffirmativeRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        if not (ctx.user_profile.is_collection_complete() and ctx.user_profile.contact):
            return RuleCheckResult(handled=False)
        affirmative_words = ["嗯", "好", "好的", "行", "可以", "ok", "是的", "对", "是"]
        if ctx.user_message.strip() not in affirmative_words:
            return RuleCheckResult(handled=False)
        return RuleCheckResult(
            handled=True,
            response_payload={
                "success": True,
                "response": "",
                "collected_info": {},
                "collection_complete": True,
                "dialogId": ctx.request.dialogId,
            },
        )


class ContactFlowAffirmativeRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        extraction_service = ctx.chat_service.extraction_service
        collected_info_summary = extraction_service.get_collected_info_summary(ctx.user_profile)
        has_contact = "已留联系" in collected_info_summary
        affirmative_words = ["嗯", "好", "好的", "行", "可以", "ok", "是的", "对", "是", "恩", "嗯嗯", "好的呢", "好呀"]
        is_affirmative = ctx.user_message.strip() in affirmative_words
        last_response = await ctx.chat_service.dialogue_manager.get_last_response(ctx.account_id) or ""
        contact_context_markers = ["电话", "手机号", "号码", "微信", "联系方式", "留个", "联系你"]
        last_response_about_contact = any(marker in last_response for marker in contact_context_markers)
        has_contact_stage_signal = any(
            [
                bool(ctx.user_profile.phone_ask_count > 0),
                bool(ctx.user_profile.wechat_ask_count > 0),
                bool(ctx.user_profile.phone_collected),
                bool(ctx.user_profile.wechat_collected),
                bool(ctx.user_profile.rejected_phone),
                bool(ctx.user_profile.rejected_wechat),
            ]
        )

        # 仅在「明确联系方式语境」才允许确认词路由到联系方式，
        # 避免把普通“嗯/好/可以”误判成“同意留电话/微信”。
        in_explicit_contact_context = last_response_about_contact or has_contact_stage_signal
        if in_explicit_contact_context and not has_contact and is_affirmative:
            confirm_count = await ctx.chat_service.input_fallback_service.increment_confirm_count(ctx.account_id)
            logger.info(f"[确认词检测] 用户第{confirm_count}次回复确认词但没留联系方式: {ctx.user_message.strip()}")
            confirm_response = ctx.chat_service.input_fallback_service.get_confirm_word_response(ctx.user_profile, confirm_count)
            if confirm_response is not None:
                response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
                    ctx.account_id,
                    ctx.user_profile,
                    confirm_response,
                    {"collected": False, "all_fields": []},
                    ctx.request.dialogId,
                    response_route="rule_confirm_word",
                )
                return RuleCheckResult(handled=True, response_payload=response_payload)
        elif has_contact:
            await ctx.chat_service.input_fallback_service.reset_confirm_count(ctx.account_id)

        return RuleCheckResult(handled=False)


class MatchingTimelineRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        if not ctx.chat_service.expectation_service.is_matching_timeline_question(ctx.user_message):
            return RuleCheckResult(handled=False)
        timeline_response = ctx.chat_service.expectation_service.get_matching_timeline_response(ctx.user_profile)
        response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
            ctx.account_id,
            ctx.user_profile,
            timeline_response,
            {"collected": False, "all_fields": []},
            ctx.request.dialogId,
            response_route="rule_timeline",
        )
        return RuleCheckResult(handled=True, response_payload=response_payload)


class UnclearInputRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        if InputValidator.is_understandable(ctx.user_message):
            return RuleCheckResult(handled=False)
        response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
            ctx.account_id,
            ctx.user_profile,
            "抱歉，我没太理解您的意思，能换个方式说吗？",
            {"collected": False, "all_fields": []},
            ctx.request.dialogId,
            response_route="rule_unclear_input",
        )
        return RuleCheckResult(
            handled=True,
            response_payload=response_payload,
        )


class SeparationStatusRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        end_intent_keywords = [
            "不说了", "不聊了", "不想聊", "算了", "算了算了", "不填了", "不填", "不写了", "不写", "下次吧",
            "先这样", "不用了", "不用", "不要了", "不要", "没兴趣", "没意思", "太麻烦", "太复杂", "太细了",
            "问的太细", "问的太多", "问题太多", "太费事", "不想说了", "豆不想说了", "不想填了", "拒绝了", "不再问了",
            "不回答了", "不答了", "不聊", "不回", "不回复", "不提供", "不给", "不愿意", "不方便", "不想给",
        ]
        user_input_lower = ctx.user_message.strip().lower()
        if any(kw in user_input_lower for kw in end_intent_keywords):
            ctx.user_profile.increment_ask_count("conversation_end_intent")
            await ctx.chat_service.user_service.save_user_profile(ctx.account_id, ctx.user_profile)

        separation_keywords = ["分居中", "正在分居", "分居状态", "分居的", "处于分居", "已经分居", "目前分居", "现在分居", "还在分居"]
        if not any(kw in user_input_lower for kw in separation_keywords):
            return RuleCheckResult(handled=False)

        ctx.user_profile.conversation_ended = True
        ctx.user_profile.marital_status = "离异（分居中）"
        await ctx.chat_service.user_service.save_user_profile(ctx.account_id, ctx.user_profile)
        response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
            ctx.account_id,
            ctx.user_profile,
            "嗯嗯理解～分居中的话暂时还不符合我们的服务条件呢～等手续都办妥了再来找我吧，祝你顺利～",
            {"collected": False, "all_fields": []},
            ctx.request.dialogId,
            response_route="rule_separation",
        )
        return RuleCheckResult(handled=True, response_payload=response_payload)


class NonsenseInputRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        last_ai_response = await ctx.chat_service.dialogue_manager.get_last_response(ctx.account_id) or ""
        nonsense_response = await ctx.chat_service.input_fallback_service.check_and_handle_nonsense(
            ctx.user_message,
            ctx.account_id,
            ctx.user_profile,
            last_ai_response,
        )
        if not nonsense_response:
            return RuleCheckResult(handled=False)
        response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
            ctx.account_id,
            ctx.user_profile,
            nonsense_response,
            {},
            ctx.request.dialogId,
            response_route="rule_nonsense",
        )
        return RuleCheckResult(handled=True, response_payload=response_payload)


class GreetingRule(ConversationRule):
    async def apply(self, ctx: ConversationRuleContext) -> RuleCheckResult:
        has_contact_refusal = any(kw in ctx.user_message for kw in ["不留微信", "不留电话", "不留联系方式", "不给微信", "不给电话"])
        is_pure_greeting = ctx.chat_service.greeting_service.is_greeting(ctx.user_message)
        if not is_pure_greeting or has_contact_refusal:
            return RuleCheckResult(handled=False)

        if ctx.is_first_user_turn:
            greeting_response = ctx.chat_service.greeting_service.get_greeting_response(ctx.user_message)
            await ctx.chat_service._simulate_human_reply_delay(first_turn=True)  # noqa: SLF001
            await ctx.chat_service._update_conversation_state(  # noqa: SLF001
                ctx.account_id,
                ctx.user_message,
                greeting_response,
                greeting_response,
                track_asked_fields=False,
            )
            response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
                ctx.account_id,
                ctx.user_profile,
                greeting_response,
                {},
                ctx.request.dialogId,
            )
            return RuleCheckResult(handled=True, response_payload=response_payload)

        if not ctx.chat_service._should_route_followup_greeting_to_ai():  # noqa: SLF001
            followup_response = ctx.chat_service.greeting_service.get_followup_greeting_response(ctx.user_message)
            await ctx.chat_service._simulate_human_reply_delay(first_turn=False)  # noqa: SLF001
            await ctx.chat_service._update_conversation_state(  # noqa: SLF001
                ctx.account_id,
                ctx.user_message,
                followup_response,
                followup_response,
                track_asked_fields=False,
            )
            response_payload = await ctx.chat_service._build_chat_response(  # noqa: SLF001
                ctx.account_id,
                ctx.user_profile,
                followup_response,
                {},
                ctx.request.dialogId,
            )
            return RuleCheckResult(handled=True, response_payload=response_payload)

        return RuleCheckResult(handled=False)
