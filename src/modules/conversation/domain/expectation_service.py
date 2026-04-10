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

        raw_text = str(value).strip().lower()
        text = raw_text.replace('月薪', '').replace('月收入', '').replace('收入', '')
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if not match:
            return None

        amount = float(match.group(1))
        if any(marker in raw_text for marker in ('年薪', '年收入', '年包')):
            if 'k' in raw_text:
                return amount * 1000 / 12
            if 'w' in raw_text or '万' in raw_text:
                return amount * 10000 / 12
            # 口语里“年薪20左右”通常省略“万”，按 20 万年薪处理。
            if amount <= 100:
                return amount * 10000 / 12
            return amount / 12
        if 'w' in text or '万' in text:
            return amount * 10000
        if 'k' in text or '千' in text:
            return amount * 1000
        return amount

    def parse_age_value(self, value: Optional[object]) -> Optional[int]:
        """将年龄字段稳健解析为整数，兼容 '28' / 28 / '98年' 这类混合值。"""
        if value in (None, ""):
            return None

        if isinstance(value, int):
            return value

        text = str(value).strip()
        if not text:
            return None

        match = re.search(r"(\d{1,3})", text)
        if not match:
            return None

        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    def is_bachelor_or_above(self, education: Optional[str]) -> bool:
        """判断学历是否本科及以上。"""
        if not education:
            return False

        text = str(education).strip()
        keywords = ['本科', '学士', '硕士', '研究生', '博士', 'mba', 'emba']
        return any(keyword.lower() in text.lower() for keyword in keywords)

    def qualifies_fast_match(self, user_profile: UserProfile) -> bool:
        """判断是否满足快速匹配时长条件。"""
        age = self.parse_age_value(user_profile.age)
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
            f"好的，那你等好消息啦，祝你早日脱单🥰 {timeline}哒~ "
            "牵线同事联系前会提前约时间，不打扰你～"
        )

    def build_contact_completion_generation_instruction(self, user_profile: UserProfile) -> str:
        """为第一次 AI 生成提供联系方式完成收尾指令。"""
        timeline = self.get_closing_timeline_text(user_profile)
        return (
            "用户刚刚已经留下了有效联系方式，这一轮不要再追问任何资料，也不要再索要电话或微信，"
            "直接自然收尾。整体语气要轻松自然，像真人顺着把结尾收住。"
            f"必须自然带出“{timeline}”这个时效信息，时间范围不能改。"
            "还要自然表达“牵线同事联系前会提前约时间，不打扰你”这层意思。"
            "“等好消息/好消息”不是必须原词，只要整体意思自然成立即可。"
            "不要说“我存好了”“我记下了”“后面有消息我再联系你”“有符合要求的人我再联系你”"
            "“发资料给你”这类直接暴露收集动作或过度承诺的话。"
        )
