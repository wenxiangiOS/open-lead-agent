"""
资料收集策略服务

统一管理资料收集阶段的字段优先级、联系方式进入条件和轻量用户分类。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.models.user_profile import UserProfile


@dataclass
class PolicyDecision:
    """资料收集策略决策结果"""
    main_target: Optional[str]
    side_target: Optional[str]
    user_type: str
    can_enter_contact: bool
    missing_fields: List[str]


class ProfileCollectionPolicy:
    """统一资料收集策略"""

    CORE_FIELDS = ["sex", "age", "education", "occupation", "location", "contact"]
    QUASI_CORE_FIELDS = ["marital_status"]
    MEDIUM_FIELDS = ["monthly_income", "partner_requirement"]
    LOW_PRIORITY_FIELDS = ["height", "last_name", "weight"]

    PRIORITY_ORDER = [
        "sex",
        "age",
        "location",
        "education",
        "occupation",
        "marital_status",
        "contact",
    ]

    ASK_LIMITS: Dict[str, int] = {
        "sex": 2,
        "age": 2,
        "education": 2,
        "occupation": 2,
        "location": 2,
        "marital_status": 2,
        "monthly_income": 1,
        "partner_requirement": 1,
        "height": 0,
        "last_name": 0,
        "weight": 0,
        "contact": 0,  # 联系方式由 ContactCollectionService 接管
    }

    PARTNER_REQUIREMENT_TRIGGER_KEYWORDS = [
        "喜欢什么样",
        "找什么样",
        "择偶",
        "有什么要求",
        "期待",
        "看重",
        "另一半",
    ]

    INCOME_TRIGGER_KEYWORDS = [
        "收入",
        "工资",
        "薪资",
        "月薪",
        "待遇",
        "年薪",
    ]

    CONSERVATIVE_KEYWORDS = ["不方便", "这个也要", "不太想说", "先不说", "不想聊"]
    DEFLECTIVE_KEYWORDS = ["还行", "一般", "再说吧", "嗯", "哦", "哈哈", "呵呵"]
    TOPIC_HEAVY_KEYWORDS = ["希望", "喜欢", "想找", "我比较看重", "性格", "感觉", "缘分"]

    def decide(
        self,
        profile: UserProfile,
        user_message: str = "",
        message_count: int = 0,
        allow_contact_target: bool = True,
    ) -> PolicyDecision:
        """生成当前收集策略决策"""
        user_type = self.classify_user_type(user_message, message_count)
        can_enter_contact = self.can_enter_contact(profile)
        missing_fields = self.get_missing_fields(profile, can_enter_contact, allow_contact_target)
        main_target = self.get_main_target(profile, can_enter_contact, allow_contact_target)
        side_target = self.get_side_target(profile, main_target, user_message)

        return PolicyDecision(
            main_target=main_target,
            side_target=side_target,
            user_type=user_type,
            can_enter_contact=can_enter_contact,
            missing_fields=missing_fields,
        )

    def get_main_target(
        self,
        profile: UserProfile,
        can_enter_contact: Optional[bool] = None,
        allow_contact_target: bool = True,
    ) -> Optional[str]:
        """获取当前主目标字段"""
        can_enter_contact = self.can_enter_contact(profile) if can_enter_contact is None else can_enter_contact

        for field in self.PRIORITY_ORDER:
            if field == "contact":
                if not allow_contact_target or not can_enter_contact:
                    continue
            if self.can_actively_ask(profile, field):
                return field
        return None

    def get_side_target(
        self,
        profile: UserProfile,
        main_target: Optional[str],
        user_message: str = "",
    ) -> Optional[str]:
        """获取顺带字段"""
        if self.can_enter_contact(profile) and not self.is_collected(profile, "contact"):
            return None

        if self.can_actively_ask(profile, "partner_requirement"):
            if main_target in {"age", "marital_status"}:
                return "partner_requirement"
            if any(keyword in user_message for keyword in self.PARTNER_REQUIREMENT_TRIGGER_KEYWORDS):
                return "partner_requirement"

        if self.can_actively_ask(profile, "monthly_income"):
            if main_target == "occupation":
                return "monthly_income"
            if any(keyword in user_message for keyword in self.INCOME_TRIGGER_KEYWORDS):
                return "monthly_income"

        return None

    def get_missing_fields(
        self,
        profile: UserProfile,
        can_enter_contact: Optional[bool] = None,
        allow_contact_target: bool = True,
    ) -> List[str]:
        """获取策略层可展示的缺失字段"""
        can_enter_contact = self.can_enter_contact(profile) if can_enter_contact is None else can_enter_contact
        fields: List[str] = []

        for field in self.PRIORITY_ORDER:
            if field == "contact" and (not can_enter_contact or not allow_contact_target):
                continue
            if self.is_missing(profile, field):
                fields.append(field)

        if not self.is_collected(profile, "contact"):
            return fields

        for field in self.MEDIUM_FIELDS:
            if self.is_missing(profile, field):
                fields.append(field)

        return fields

    def can_enter_contact(self, profile: UserProfile) -> bool:
        """判断当前是否适合进入联系方式逻辑"""
        if self.is_collected(profile, "contact"):
            return True

        core_quasi_collected = sum(
            1 for field in (self.CORE_FIELDS[:-1] + self.QUASI_CORE_FIELDS)
            if self.is_collected(profile, field)
        )

        has_age = self.is_collected(profile, "age")
        has_location = self.is_collected(profile, "location")
        has_background = self.is_collected(profile, "occupation") or self.is_collected(profile, "education")
        has_marital_status = self.is_collected(profile, "marital_status")

        return core_quasi_collected >= 4 or (has_age and has_location and has_background and has_marital_status)

    def has_serviceable_profile(self, profile: UserProfile) -> bool:
        """判断资料是否足够进入收尾/后续处理"""
        return self.can_enter_contact(profile)

    def should_allow_contact_instruction(self, profile: UserProfile, action_name: str) -> bool:
        """控制何时允许联系方式提示词生效"""
        ongoing_contact_flow = any([
            profile.phone_ask_count > 0,
            profile.wechat_ask_count > 0,
            profile.phone_collected,
            profile.wechat_collected,
            profile.rejected_phone,
            profile.rejected_wechat,
        ])

        if ongoing_contact_flow:
            return True

        if action_name in {"PERSUADE_PHONE", "PERSUADE_WECHAT", "END_CONVERSATION"}:
            return True

        return self.can_enter_contact(profile)

    def classify_user_type(self, user_message: str, message_count: int = 0) -> str:
        """轻量用户类型判断，用于提示词节奏控制"""
        message = (user_message or "").strip()

        if any(keyword in message for keyword in self.CONSERVATIVE_KEYWORDS):
            return "保守型"
        if any(keyword in message for keyword in self.TOPIC_HEAVY_KEYWORDS):
            return "话题型"
        if len(message) <= 4 or any(keyword == message for keyword in self.DEFLECTIVE_KEYWORDS):
            return "敷衍型"
        if message_count <= 2:
            return "配合型"
        return "配合型"

    def can_actively_ask(self, profile: UserProfile, field: str) -> bool:
        """判断字段是否还能主动问"""
        if field in self.LOW_PRIORITY_FIELDS:
            return False
        if self.is_collected(profile, field):
            return False
        if profile.skipped_fields.get(field, False):
            return False

        ask_limit = self.ASK_LIMITS.get(field, 0)
        if ask_limit == 0 and field != "contact":
            return False

        ask_count = profile.field_ask_count.get(field, 0)
        if field == "contact":
            return not self.is_collected(profile, "contact")
        return ask_count < ask_limit

    def is_missing(self, profile: UserProfile, field: str) -> bool:
        """判断字段是否缺失"""
        return not self.is_collected(profile, field) and not profile.skipped_fields.get(field, False)

    def is_collected(self, profile: UserProfile, field: str) -> bool:
        """统一判断字段是否已收集"""
        if field == "contact":
            return bool(
                profile.collection_progress.get("contact", False) or
                (profile.phone and profile.phone_collected) or
                (profile.wechat and profile.wechat_collected)
            )
        return bool(profile.collection_progress.get(field, False))
