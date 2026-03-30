"""
匹配预期服务

负责识别用户对匹配时长的询问，并根据资料条件返回统一规则结果。
"""

import re
from typing import Optional

from src.models.user_profile import UserProfile


class ExpectationService:
    """管理匹配时长相关的业务规则。"""

    TIMELINE_KEYWORDS = [
        '多久', '多长时间', '多久能', '多久可以', '多久会',
        '什么时候能', '什么时候会', '几天', '几小时',
        '多久匹配', '多久有消息', '多久联系', '多久安排',
        '匹配时间', '出结果', '有结果'
    ]

    def is_matching_timeline_question(self, text: str) -> bool:
        """判断用户是否在询问匹配时长。"""
        if not text:
            return False
        text_stripped = text.strip()
        return any(keyword in text_stripped for keyword in self.TIMELINE_KEYWORDS)

    def parse_monthly_income_amount(self, value: Optional[str]) -> Optional[float]:
        """将月收入字段粗略转换为元，用于匹配时长判断。"""
        if not value:
            return None

        text = str(value).strip().lower().replace('月薪', '').replace('月收入', '').replace('收入', '')
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if not match:
            return None

        amount = float(match.group(1))
        if 'w' in text or '万' in text:
            return amount * 10000
        if 'k' in text or '千' in text:
            return amount * 1000
        return amount

    def is_bachelor_or_above(self, education: Optional[str]) -> bool:
        """判断学历是否本科及以上。"""
        if not education:
            return False

        text = str(education).strip()
        keywords = ['本科', '学士', '硕士', '研究生', '博士', 'mba', 'emba']
        return any(keyword.lower() in text.lower() for keyword in keywords)

    def qualifies_fast_match(self, user_profile: UserProfile) -> bool:
        """判断是否满足快速匹配时长条件。"""
        age = user_profile.age
        if age is None or age < 27:
            return False

        if not self.is_bachelor_or_above(user_profile.education):
            return False

        income_amount = self.parse_monthly_income_amount(user_profile.monthly_income)
        if income_amount is None:
            return False

        if user_profile.sex == '男':
            return income_amount >= 20000
        if user_profile.sex == '女':
            return income_amount >= 10000
        return False

    def get_matching_timeline_response(self, user_profile: UserProfile) -> str:
        """根据资料条件返回匹配时长回复。"""
        has_any_contact = bool(
            (user_profile.phone_collected and user_profile.phone)
            or (user_profile.wechat_collected and user_profile.wechat)
        )

        if self.qualifies_fast_match(user_profile):
            if has_any_contact:
                return "按你现在的情况，快的话一般1-8小时会有推进，不过也还是要看前面沟通和匹配节奏；真有合适的，我会先跟你说一声。"
            return "按你现在的情况，快的话一般1-8小时会有推进，不过也得先把你的基本情况聊清楚，再看后面怎么往下走。"

        if has_any_contact:
            return "按你现在的情况，常见是1-2天会有推进，不过也还是要看前面沟通和匹配节奏；真有合适的，我会先跟你说一声。"
        return "按你现在的情况，常见是1-2天会有推进，不过也得先把你的基本情况聊清楚，再看后面怎么往下走。"

    def get_closing_timeline_text(self, user_profile: UserProfile) -> str:
        """返回收尾场景使用的匹配时长文案片段。"""
        if self.qualifies_fast_match(user_profile):
            return "匹配一般1-8小时"
        return "匹配一般1-2天"

    def get_contact_completion_response(self, user_profile: UserProfile) -> str:
        """联系方式完成后的业务收尾话术。"""
        timeline = self.get_closing_timeline_text(user_profile)
        return (
            f"好的，这边我先帮你记下了。按你现在的情况，{timeline}会有推进；"
            "真有合适的，我会先跟你说一声，再往下接。"
        )
