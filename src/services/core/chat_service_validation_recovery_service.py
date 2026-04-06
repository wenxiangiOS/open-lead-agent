import logging
import re
from typing import Any, Dict, Optional

from src.services.core.chat_service_contact_validation_text_service import (
    ChatServiceContactValidationTextService,
)

logger = logging.getLogger(__name__)


class ChatServiceValidationRecoveryService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def build_validation_feedback(
        self,
        *,
        account_id: str,
        user_profile,
        user_message: str,
        invalid_value: Optional[str],
        error_info: Optional[Dict[str, Any]],
    ) -> str:
        info = dict(error_info or {})
        error_code = info.get("code") or "VALIDATION_ERROR"
        self.host._last_validation_feedback_meta = {
            "error_code": error_code,
            "field": info.get("field"),
            "attempt": info.get("attempt"),
            "silent": bool(info.get("silent")),
            "retry_active": True,
            "retry_lock_response": True,
        }
        contact_type = str(info.get("field") or "contact")
        if contact_type not in {"phone", "wechat"}:
            last_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
            contact_type = last_type if last_type in {"phone", "wechat"} else "contact"

        if contact_type in {"phone", "wechat"}:
            self.host.contact_service.record_invalid_input(user_profile, contact_type)
            self.host.contact_service.is_contact_complete(user_profile)
            detail = self.classify_contact_validation_detail(
                field=contact_type,
                invalid_value=invalid_value,
                detail=info.get("detail"),
                user_profile=user_profile,
            )
            if detail == "soft_region_mismatch_hk":
                candidate = str(invalid_value or "").strip()
                user_profile.pending_contact_candidate = candidate or None
                user_profile.pending_contact_field = contact_type
                user_profile.pending_contact_hint = detail
            else:
                user_profile.pending_contact_candidate = None
                user_profile.pending_contact_field = None
                user_profile.pending_contact_hint = None
            await self.host.user_service.save_user_profile(account_id, user_profile)

        if info.get("silent"):
            if contact_type == "wechat":
                return ChatServiceContactValidationTextService.build_contact_invalid_input_close_response("wechat")
            if contact_type == "phone":
                return ChatServiceContactValidationTextService.build_contact_invalid_input_close_response("phone")
            return ""

        return await self.generate_validation_retry_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info=info,
        )

    async def generate_validation_retry_response(
        self,
        *,
        account_id: str,
        user_profile,
        user_message: str,
        invalid_value: Optional[str],
        error_info: Dict[str, Any],
    ) -> str:
        field = error_info.get("field") or "contact"
        field_label = "微信号" if field == "wechat" else "联系方式"
        attempt = error_info.get("attempt") or 1
        detail = self.classify_contact_validation_detail(
            invalid_value=invalid_value,
            field=field,
            detail=error_info.get("detail"),
            user_profile=user_profile,
        )
        prompt = (
            "你在继续一段婚恋咨询对话。"
            "用户刚发来的联系方式需要重新确认，请只输出一条自然、简短、口语化的中文回复。\n"
            "要求：\n"
            "1. 不要提 AI、系统、校验规则、错误码。\n"
            "2. 根据给定判断，自然提醒对方核对并重新发一个可用的联系方式。\n"
            "3. 保持一到两句，像真人聊天，不要模板腔。\n"
            "4. 如果判断是地区不一致但仍像有效号码，不要直接否定，先柔性确认这是不是对方常用联系方式。\n"
            "5. 不要说“现在不方便可以稍后再发”这类退让句，只聚焦让对方核对后重发。\n"
            "6. 如果当前字段是电话，就只提醒对方重发手机号，不要提微信，不要把微信当替代项。\n"
            "7. 如果当前字段是微信，就只提醒对方重发微信，不要提手机号。\n"
            f"当前字段：{field_label}\n"
            f"判断结果：{detail}\n"
            f"第几次无效输入：{attempt}\n"
            f"用户地区：{getattr(user_profile, 'location', None) or '-'}\n"
            f"是否香港用户：{user_profile.check_is_hongkong_user()}\n"
            f"用户称呼：{user_profile.get_greeting()}\n"
            f"用户原话：{user_message or '-'}\n"
            f"本次疑似输入：{invalid_value or '-'}\n"
        )
        try:
            response = await self.host._call_ai(prompt, account_id, user_message or str(invalid_value or ""))
            if response and response.strip():
                return response.strip()
        except Exception as exc:
            logger.warning("[联系方式验证] 生成 AI 引导失败: %s", exc)
        return ChatServiceContactValidationTextService.build_contact_validation_retry_fallback(
            field=field,
            attempt=attempt,
            detail=detail,
        ) or ""

    @staticmethod
    def classify_contact_validation_detail(
        *,
        invalid_value: Optional[str],
        field: str,
        detail: Optional[str],
        user_profile,
    ) -> str:
        if field == "wechat":
            return "invalid_format"

        digits = re.sub(r"\D", "", str(invalid_value or ""))
        if not digits:
            return "invalid_format"

        is_hk_user = user_profile.check_is_hongkong_user()
        has_known_location = bool(str(getattr(user_profile, "location", "") or "").strip())

        if re.fullmatch(r"1[3-9]\d{10}", digits):
            return "valid_cn"
        if re.fullmatch(r"(?:852)?[5-9]\d{7}", digits):
            if is_hk_user or not has_known_location:
                return "valid_hk"
            return "soft_region_mismatch_hk"
        if re.fullmatch(r"1[3-9]\d{11,}", digits):
            return "too_long_cn"
        if re.fullmatch(r"1[3-9]\d{7,9}", digits):
            return "too_short_cn"
        if re.fullmatch(r"[5-9]\d{8,}", digits):
            return "too_long_hk"
        if re.fullmatch(r"[5-9]\d{5,6}", digits):
            return "too_short_hk"

        normalized_detail = str(detail or "").lower()
        if "placeholder" in normalized_detail:
            return "invalid_format"
        return "invalid_format"
