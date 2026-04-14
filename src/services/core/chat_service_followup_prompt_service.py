from typing import Any, Dict, Optional

from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService
from src.services.core.chat_service_summary_helper_service import (
    ChatServiceSummaryHelperService,
)


class ChatServiceFollowupPromptService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def build_soft_occupation_ack_prefix(user_profile=None) -> str:
        return ""

    def build_soft_occupation_confirmation_prompt(
        self,
        user_profile=None,
        *,
        user_message: str = "",
        stage: str = "trust",
    ) -> str:
        candidate = str(getattr(user_profile, "occupation_inference_candidate", "") or "").strip()
        if not candidate or str(getattr(user_profile, "occupation", "") or "").strip():
            return self.host.dialogue_expression_service.render_field_question(
                "occupation",
                profile=user_profile,
                stage=stage,
                user_message=user_message,
            )
        variants = (
            "你现在主要做哪方面工作的呀？",
            "你平时主要是做哪块工作的呀？",
            "你这边现在主要从事什么方向的工作呀？",
        )
        return variants[0]

    def build_local_field_fallback_prompt(
        self,
        field: Optional[str],
        user_profile=None,
        *,
        user_message: str = "",
        stage: str = "trust",
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        if field == "sex" and user_profile and not getattr(user_profile, "sex", None):
            preference_hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(
                collection_result,
                profile=user_profile,
            )
            soft_confirmation = self.host.dialogue_expression_service._build_soft_gender_confirmation_prompt(  # noqa: SLF001
                user_profile,
                user_message=user_message,
                preference_hint=preference_hint,
            )
            if soft_confirmation:
                return soft_confirmation
        if field == "occupation":
            return self.build_soft_occupation_confirmation_prompt(
                user_profile,
                user_message=user_message,
                stage=stage,
            )
        return self.host.dialogue_expression_service.render_field_question(
            field,
            profile=user_profile,
            stage=stage,
            user_message=user_message,
            preference_hint=(
                ChatServiceSummaryHelperService.extract_partner_requirement_hint(collection_result)
                if field == "sex"
                else ""
            ),
        )

    def build_policy_field_prompt(
        self,
        field: Optional[str],
        user_profile=None,
        *,
        user_message: str = "",
        stage: str = "trust",
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.build_local_field_fallback_prompt(
            field,
            user_profile,
            user_message=user_message,
            stage=stage,
            collection_result=collection_result,
        )

    def build_followup_seed_for_model_rewrite(
        self,
        field: Optional[str],
        user_profile=None,
        *,
        user_message: str = "",
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not field:
            return ""
        if field == "contact" and user_profile is not None:
            phone_ready = bool(getattr(user_profile, "phone_collected", False) and getattr(user_profile, "phone", None))
            wechat_ready = bool(getattr(user_profile, "wechat_collected", False) and getattr(user_profile, "wechat", None))
            if phone_ready and not wechat_ready and not getattr(user_profile, "rejected_wechat", False):
                try:
                    next_action = self.host.contact_service.get_next_action(user_profile, user_message)
                    action_value = getattr(next_action, "value", str(next_action))
                except Exception:
                    action_value = "ask_wechat"
                if action_value in {"ask_wechat", "persuade_wechat"}:
                    return ChatServiceContactTextService.build_contact_followup_response(action_value, "phone")
                return ChatServiceContactTextService.build_contact_collection_ack("phone")
            if wechat_ready and not phone_ready and not getattr(user_profile, "rejected_phone", False):
                try:
                    next_action = self.host.contact_service.get_next_action(user_profile, user_message)
                    action_value = getattr(next_action, "value", str(next_action))
                except Exception:
                    action_value = "ask_phone"
                if action_value in {"ask_phone", "persuade_phone"}:
                    return ChatServiceContactTextService.build_contact_followup_response(action_value, "wechat")
                return ChatServiceContactTextService.build_contact_collection_ack("wechat")
        if (
            field == "marital_status"
            and user_profile is not None
            and self.host.collection_policy.has_divorce_confirmation_pending(user_profile)
        ):
            return self.host._build_divorce_confirmation_response()
        if field == "sex":
            preference_hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(
                collection_result,
                profile=user_profile,
            )
            soft_confirmation = self.host.dialogue_expression_service._build_soft_gender_confirmation_prompt(  # noqa: SLF001
                user_profile,
                user_message=user_message,
                preference_hint=preference_hint,
            )
            if soft_confirmation:
                return soft_confirmation
        if field == "partner_requirement":
            gender_preference = (
                str(getattr(user_profile, "partner_gender_preference", "") or "").strip()
                if user_profile
                else ""
            )
            if gender_preference == "男":
                return "除了偏男生这点，你还会更看重对方哪一点？"
            if gender_preference == "女":
                return "除了偏女生这点，你还会更看重对方哪一点？"
            return "你找对象时还会更看重哪一点？"
        if field == "age":
            return self.build_policy_field_prompt(
                field,
                user_profile,
                user_message=user_message,
                collection_result=collection_result,
            )
        if field == "occupation":
            return self.build_policy_field_prompt(
                field,
                user_profile,
                user_message=user_message,
                collection_result=collection_result,
            )

        seed_map = {
            "sex": "我再确认一下，你这边是男生还是女生呀？",
            "location": "我再确认一下，你现在主要在哪个城市生活呀？",
            "education": "我再确认一下，你大概是什么学历呀？",
            "marital_status": "我再确认一下，你现在的感情状态方便说个大概吗？",
            "monthly_income": "我再轻问一句，你收入大概在哪个区间？",
        }
        return seed_map.get(
            field,
            self.build_policy_field_prompt(
                field,
                user_profile,
                user_message=user_message,
                collection_result=collection_result,
            ),
        )
