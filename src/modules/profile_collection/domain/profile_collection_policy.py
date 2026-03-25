"""
资料收集策略服务

统一管理资料收集阶段的字段优先级、联系方式进入条件和轻量用户分类。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
import os
from typing import Dict, List, Optional

from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


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
        "contact",
    ]

    ASK_LIMITS: Dict[str, int] = {
        "sex": 2,
        "age": 2,
        "education": 2,
        "occupation": 2,
        "location": 2,
        "marital_status": 1,
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
    MARITAL_STATUS_TRIGGER_KEYWORDS = [
        "单身",
        "未婚",
        "离异",
        "婚况",
        "感情状态",
        "对象",
        "恋爱",
        "结婚",
    ]

    CONSERVATIVE_KEYWORDS = ["不方便", "这个也要", "不太想说", "先不说", "不想聊"]
    DEFLECTIVE_KEYWORDS = ["还行", "一般", "再说吧", "嗯", "哦", "哈哈", "呵呵"]
    TOPIC_HEAVY_KEYWORDS = ["希望", "喜欢", "想找", "我比较看重", "性格", "感觉", "缘分"]
    REPAIR_OR_DISSATISFACTION_KEYWORDS = [
        "不是问的",
        "不是刚刚",
        "你已经糊涂",
        "你糊涂了",
        "你问乱了",
        "前后不一致",
        "你搞错了",
        "你说错了",
        "怎么又问",
        "你刚不是",
    ]
    ACTIVE = "active"
    PASSIVE_ONLY = "passive_only"
    DISABLED = "disabled"

    @staticmethod
    def has_divorce_confirmation_pending(profile: UserProfile) -> bool:
        marital_status = str(getattr(profile, "marital_status", "") or "").strip()
        return (
            "离异" in marital_status
            and "办妥" not in marital_status
            and not bool(getattr(profile, "divorce_confirmed", False))
            and bool(getattr(profile, "divorce_confirmation_pending", False))
        )

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def decide(
        self,
        profile: UserProfile,
        user_message: str = "",
        message_count: int = 0,
        allow_contact_target: bool = True,
        allow_medium_target: bool = True,
        prioritize_user_question: bool = False,
        primary_move: str = "ack_and_ask",
        resume_profile_collection: bool = False,
    ) -> PolicyDecision:
        """生成当前收集策略决策"""
        user_type = self.classify_user_type(user_message, message_count)
        if self.has_divorce_confirmation_pending(profile):
            return PolicyDecision(
                main_target="marital_status",
                side_target=None,
                user_type=user_type,
                can_enter_contact=False,
                missing_fields=["marital_status"],
            )
        can_enter_contact = self.can_enter_contact(profile)
        effective_allow_medium_target = allow_medium_target and not self.should_block_medium_fields_for_turn(
            profile,
            user_message=user_message,
            allow_contact_target=allow_contact_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            resume_profile_collection=resume_profile_collection,
        )
        missing_fields = self.get_missing_fields(
            profile,
            can_enter_contact,
            allow_contact_target,
            include_medium_fields=effective_allow_medium_target,
        )
        main_target = self.get_main_target(profile, can_enter_contact, allow_contact_target)
        side_target = self.get_side_target(
            profile,
            main_target,
            user_message,
            allow_medium_target=effective_allow_medium_target,
        )

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
        allow_medium_target: bool = True,
    ) -> Optional[str]:
        """获取顺带字段。

        核心字段始终是主线；婚况、择偶要求、月薪只能自然穿插，不能抢主线。
        """
        if not allow_medium_target:
            return None
        if main_target == "contact":
            return None

        if self.can_actively_ask(profile, "partner_requirement"):
            if any(keyword in user_message for keyword in self.PARTNER_REQUIREMENT_TRIGGER_KEYWORDS):
                return "partner_requirement"
            if main_target in {"education", "occupation"}:
                return "partner_requirement"

        if self.can_actively_ask(profile, "marital_status"):
            if any(keyword in user_message for keyword in self.MARITAL_STATUS_TRIGGER_KEYWORDS):
                return "marital_status"
            if main_target == "occupation":
                return "marital_status"

        # 职业语境下可低压顺带问一次月薪。
        if self.can_use_as_side_target(profile, "monthly_income"):
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
        include_medium_fields: bool = True,
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

        if not include_medium_fields:
            return fields

        for field in self.MEDIUM_FIELDS:
            if self.is_missing(profile, field):
                fields.append(field)

        return fields

    def has_ongoing_contact_flow(self, profile: UserProfile) -> bool:
        """判断当前是否处于联系方式阶段或联系方式处理中。"""
        return any(
            [
                bool(profile.phone_ask_count > 0),
                bool(profile.wechat_ask_count > 0),
                bool(profile.phone_collected),
                bool(profile.wechat_collected),
                bool(profile.rejected_phone),
                bool(profile.rejected_wechat),
            ]
        )

    def is_medium_field(self, field: str) -> bool:
        """判断字段是否属于中等字段。"""
        return field in self.MEDIUM_FIELDS

    def is_repair_or_dissatisfaction_turn(self, user_message: str) -> bool:
        """用户在纠错、质疑系统或指出前后不一致时，压制中等字段。"""
        message = (user_message or "").strip()
        if not message:
            return False
        return any(keyword in message for keyword in self.REPAIR_OR_DISSATISFACTION_KEYWORDS)

    def should_block_medium_fields_for_turn(
        self,
        profile: UserProfile,
        user_message: str = "",
        *,
        allow_contact_target: bool = True,
        prioritize_user_question: bool = False,
        primary_move: str = "ack_and_ask",
        resume_profile_collection: bool = False,
    ) -> bool:
        """
        复杂轮次、联系方式轮次、纠错轮次统一禁止中等字段主动出现。
        """
        if prioritize_user_question:
            return True
        if resume_profile_collection:
            return True
        if primary_move in {"answer_then_pause", "soft_hold", "confirm_status_only", "repair_and_release"}:
            return True
        if self.has_divorce_confirmation_pending(profile):
            return True
        if self.is_repair_or_dissatisfaction_turn(user_message):
            return True
        if self.has_ongoing_contact_flow(profile):
            return True
        if allow_contact_target and self.can_enter_contact(profile) and not self.is_collected(profile, "contact"):
            return True
        # Phase 2: 投诉修复模式下禁止中等字段
        if profile.repair_mode and profile.ask_cooldown_turns > 0:
            return True
        return False

    def can_enter_contact(self, profile: UserProfile) -> bool:
        """判断当前是否适合进入联系方式逻辑"""
        if self.has_divorce_confirmation_pending(profile):
            return False
        if self.is_collected(profile, "contact"):
            return True

        core_quasi_collected = sum(
            1 for field in (self.CORE_FIELDS[:-1] + self.QUASI_CORE_FIELDS)
            if self.is_collected(profile, field)
        )

        has_sex = self.is_collected(profile, "sex")
        has_age = self.is_collected(profile, "age")
        has_location = self.is_collected(profile, "location")
        has_occupation = self.is_collected(profile, "occupation")
        has_education = self.is_collected(profile, "education")
        # 联系方式是核心字段，但应后置到基础核心画像足够后再进入。
        if not (has_sex and has_age and has_location and has_education and has_occupation):
            return False

        # 不再要求婚况作为联系方式前置条件；核心字段成功率优先。
        return core_quasi_collected >= 5

    def has_serviceable_profile(self, profile: UserProfile) -> bool:
        """判断资料是否足够进入收尾/后续处理"""
        return self.can_enter_contact(profile)

    def should_allow_contact_instruction(self, profile: UserProfile, action_name: str) -> bool:
        """控制何时允许联系方式提示词生效"""
        if self.has_divorce_confirmation_pending(profile):
            return False
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
        return self.get_field_mode(profile, field) == self.ACTIVE

    def can_use_as_side_target(self, profile: UserProfile, field: str) -> bool:
        """统一判断字段是否可作为顺带目标。"""
        if not self.is_medium_field(field):
            return self.can_actively_ask(profile, field)
        return self.can_actively_ask(profile, field) and not self.is_collected(profile, field)

    def get_field_mode(self, profile: UserProfile, field: str) -> str:
        """统一判断字段当前处于主动收集、仅被动提取或禁用状态。"""
        if field in self.LOW_PRIORITY_FIELDS:
            return self.DISABLED
        if self.is_collected(profile, field):
            return self.DISABLED
        if profile.skipped_fields.get(field, False):
            return self.DISABLED
        if profile.is_active_ask_closed(field):
            return self.PASSIVE_ONLY

        cooldown_turns = self._env_int("MQ_FIELD_ASK_COOLDOWN_TURNS", 2)
        if cooldown_turns > 0 and field in set(profile.get_cooldown_fields(cooldown_turns)):
            return self.DISABLED

        ask_limit = self.ASK_LIMITS.get(field, 0)
        if ask_limit == 0 and field != "contact":
            return self.DISABLED

        ask_count = profile.field_ask_count.get(field, 0)
        if field == "contact":
            return self.ACTIVE if not self.is_collected(profile, "contact") else self.DISABLED
        if ask_count >= ask_limit:
            return self.PASSIVE_ONLY if field in self.MEDIUM_FIELDS else self.DISABLED
        return self.ACTIVE

    def can_passively_extract_only(self, profile: UserProfile, field: str) -> bool:
        """字段是否已关闭主动追问，只允许被动提取。"""
        return self.get_field_mode(profile, field) == self.PASSIVE_ONLY

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

    def should_block_preference_ask(self, profile: UserProfile, user_message: str = "") -> bool:
        """
        Phase 2: 判断是否应该阻止偏好类追问。

        当 partner_requirement 已经收集后，后续所有"最看重哪一点/你更在意什么/按什么方向帮你筛"等
        同义问题都应该被阻止。
        """
        # 一旦择偶要求已收集，或主动追问已被关闭，就禁止任何同义偏好追问。
        if self.is_collected(profile, "partner_requirement") or profile.is_active_ask_closed("partner_requirement"):
            logger.info("[偏好去重] partner_requirement 已收集或已关闭主动追问，阻止偏好追问")
            return True
        return False
