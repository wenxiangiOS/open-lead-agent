import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class ChatServiceEndingGenerationService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def generate_ai_ending_response(
        self,
        *,
        account_id: str,
        user_profile,
        user_message: str,
        ending_info: Optional[Dict[str, Any]],
        fallback_response: str = "",
    ) -> str:
        """为 use_ai 的收尾场景单独生成最终收尾句。"""
        info = dict(ending_info or {})
        if not info or not info.get("use_ai"):
            return str(fallback_response or "").strip()

        extra = str(info.get("extra_instructions") or "").strip()
        scenario = str(info.get("scenario") or "").strip()
        if not extra:
            return str(fallback_response or "").strip()

        profile_bits = [
            f"性别:{getattr(user_profile, 'sex', None) or '-'}",
            f"年龄:{getattr(user_profile, 'age_label', None) or getattr(user_profile, 'age', None) or '-'}",
            f"城市:{getattr(user_profile, 'location', None) or '-'}",
            f"学历:{getattr(user_profile, 'education', None) or '-'}",
            f"职业:{getattr(user_profile, 'occupation', None) or '-'}",
            f"婚况:{getattr(user_profile, 'marital_status', None) or '-'}",
            f"电话拒绝:{bool(getattr(user_profile, 'rejected_phone', False))}",
            f"微信拒绝:{bool(getattr(user_profile, 'rejected_wechat', False))}",
        ]
        fallback = str(fallback_response or "").strip() or "那我们就先聊到这里。"
        prompt = (
            "你在收尾一段中文婚恋咨询对话，请只输出最终要发给用户的一段中文收尾回复。\n"
            "要求：\n"
            "1. 只输出1到2句自然口语，不要解释规则，不要提AI、系统、配置。\n"
            "2. 不要再追问任何资料，不要再索要电话或微信。\n"
            "3. 不要使用项目符号，不要使用引号，不要输出额外说明。\n"
            f"收尾场景：{scenario or '-'}\n"
            f"收尾指令：{extra}\n"
            f"用户当前资料：{' | '.join(profile_bits)}\n"
            f"用户本轮原话：{user_message or '-'}\n"
            f"如果生成不出来，可参考这个语气：{fallback}\n"
        )
        try:
            response = await self.host._call_ai(prompt, account_id, user_message or scenario or "ending")
            cleaned = self.host._legacy_clean_response(response).strip() if response else ""
            return cleaned or fallback
        except Exception as exc:
            logger.warning("[收尾AI] 生成收尾回复失败: %s", exc)
            return fallback
