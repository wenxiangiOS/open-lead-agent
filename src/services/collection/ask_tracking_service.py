"""
追问跟踪服务

负责识别 AI 主动询问了哪些字段，并维护字段追问次数与自动跳过逻辑。
"""

import logging

from src.services.data.user_service import UserService

logger = logging.getLogger(__name__)


class AskTrackingService:
    """管理智能追问字段计数。"""

    PARTNER_REQUIREMENT_CONTEXT_KEYWORDS = [
        '找什么样的', '有什么要求', '择偶要求', '找什么类型',
        '喜欢什么样的', '对...有要求', '要求对方', '对方的要求',
        '想找', '希望找', '要求是', '有什么择偶'
    ]

    PARTNER_REQUIREMENT_FIELDS = {'height', 'age', 'education', 'location', 'monthly_income', 'occupation'}
    LOW_PRIORITY_FIELDS = {'height', 'weight', 'last_name'}
    MEDIUM_FIELDS = {'monthly_income', 'partner_requirement'}

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def track_ai_asked_fields(self, account_id: str, ai_response: str) -> None:
        """追踪 AI 询问的字段。"""
        from src.config.settings import get_field_keywords

        field_keywords = get_field_keywords()
        is_asking_partner_requirement = any(
            kw in ai_response for kw in self.PARTNER_REQUIREMENT_CONTEXT_KEYWORDS
        )

        asked_fields = []
        ai_response_lower = ai_response.lower()

        for field, keywords in field_keywords.items():
            if is_asking_partner_requirement and field in self.PARTNER_REQUIREMENT_FIELDS:
                continue
            if field in self.LOW_PRIORITY_FIELDS:
                continue
            if field == 'partner_requirement':
                continue

            for keyword in keywords:
                if keyword in ai_response_lower or keyword in ai_response:
                    asked_fields.append(field)
                    break

        if not asked_fields:
            return

        user_profile = await self.user_service.get_user_profile(account_id)

        for field in asked_fields:
            is_collected = user_profile.collection_progress.get(field, False)
            is_skipped = field in user_profile.skipped_fields

            if is_collected or is_skipped:
                continue

            if field == 'contact':
                phone_keywords = ['电话', '手机号', '号码']
                wechat_keywords = ['微信']
                asked_phone = any(kw in ai_response_lower for kw in phone_keywords)
                asked_wechat = any(kw in ai_response_lower for kw in wechat_keywords)
                if asked_phone or asked_wechat:
                    logger.debug("[智能追问] 检测到联系方式询问，由 ContactCollectionService 管理")
                    continue

            if field in self.MEDIUM_FIELDS:
                continue

            user_profile.increment_ask_count(field)
            current_count = user_profile.get_ask_count(field)
            logger.info(f"[智能追问] AI询问了字段 {field}，当前追问次数: {current_count}")

            if current_count >= 2:
                user_profile.skipped_fields[field] = True
                logger.info(f"[智能追问] 字段 {field} 已问2次未回答，自动标记为跳过")

        await self.user_service.save_user_profile(account_id, user_profile)
