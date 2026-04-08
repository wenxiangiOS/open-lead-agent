"""
资料收集策略服务

统一管理资料收集阶段的字段优先级、联系方式进入条件和轻量用户分类。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dataclass_field
import os
import re
from typing import Dict, List, Optional

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.modules.conversation_understanding.domain.followup_planning_layer import FollowupPlanningLayer

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """资料收集策略决策结果"""
    main_target: Optional[str]
    side_target: Optional[str]
    user_type: str
    can_enter_contact: bool
    missing_fields: List[str]
    coverage_passed: bool = False
    profile_sufficient: bool = False
    turn_quality_passed: bool = False
    engagement_mode: str = "full"
    next_mode: str = "collect_core"
    unresolved_core_fields: List[str] = dataclass_field(default_factory=list)
    unresolved_medium_fields: List[str] = dataclass_field(default_factory=list)
    forced_cover_target: Optional[str] = None
    core_success_count: int = 0
    allow_contact_push: bool = False
    reason: str = ""
    must_answer_first: bool = False
    primary_move: str = "ack_and_ask"
    prioritize_user_question: bool = False
    allow_contact_target: bool = True
    allow_medium_target: bool = True
    user_concern_type: Optional[str] = None
    resume_mode: Optional[str] = None
    resume_target: Optional[str] = None
    made_effective_progress: bool = False


class ProfileCollectionPolicy:
    """统一资料收集策略"""

    def __init__(self) -> None:
        self.followup_planning_layer = FollowupPlanningLayer(policy=self)

    SIDE_TARGET_HOST_ORDERS: Dict[str, tuple[str, ...]] = {
        "monthly_income": ("occupation", "location", "age", "education"),
        "marital_status": ("age", "location", "occupation", "education", "sex"),
        "partner_requirement": ("age", "location", "occupation", "education", "marital_status", "sex"),
    }

    CORE_FIELDS = ["sex", "age", "education", "occupation", "location", "contact"]
    QUASI_CORE_FIELDS = ["marital_status"]
    MEDIUM_FIELDS = ["monthly_income", "partner_requirement"]
    LOW_PRIORITY_FIELDS = ["height", "last_name", "weight"]
    CORE_CONTACT_FIELDS = ["sex", "age", "education", "occupation", "location"]
    MEDIUM_COVERAGE_FIELDS = ["marital_status", "partner_requirement", "monthly_income"]
    MEDIUM_PRIORITY_ORDER = ["marital_status", "partner_requirement", "monthly_income"]

    PRIORITY_ORDER = [
        "sex",
        "age",
        "location",
        "education",
        "occupation",
        "marital_status",
        "contact",
    ]

    CORE_ORDER_VARIANTS = [
        ["sex", "age", "location", "education", "occupation"],
        ["sex", "location", "age", "education", "occupation"],
        ["sex", "age", "education", "location", "occupation"],
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
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> PolicyDecision:
        """生成当前收集策略决策"""
        user_type = self.classify_user_type(user_message, message_count)
        complaint_reason = getattr(understanding_result, "complaint_reason", None) if understanding_result else None
        if understanding_result:
            if understanding_result.primary_turn_type == "refusal_boundary_complaint" and understanding_result.subtype == "contact_refusal":
                prioritize_user_question = False
                allow_contact_target = True
                allow_medium_target = False
                primary_move = "ack_and_ask"
            if understanding_result.primary_turn_type in {"faq_concern", "refusal_boundary_complaint"}:
                if not (understanding_result.primary_turn_type == "refusal_boundary_complaint" and understanding_result.subtype == "contact_refusal"):
                    prioritize_user_question = True
                    allow_contact_target = False
                    allow_medium_target = False
                    primary_move = "answer_then_resume" if understanding_result.primary_turn_type == "faq_concern" else "ack_and_hold"
            elif understanding_result.primary_turn_type in {"closing_exit", "risk_guard"}:
                allow_contact_target = False
                allow_medium_target = False
                primary_move = "soft_hold"
            elif understanding_result.primary_turn_type == "contact_answer":
                allow_medium_target = False
                if understanding_result.subtype in {"contact_refusal", "contact_preference_switch"}:
                    allow_contact_target = True
            elif understanding_result.primary_turn_type == "confirmation":
                allow_contact_target = False

        if self.has_divorce_confirmation_pending(profile):
            return PolicyDecision(
                main_target="marital_status",
                side_target=None,
                user_type=user_type,
                can_enter_contact=False,
                missing_fields=["marital_status"],
                reason="divorce_confirmation_pending",
                primary_move="confirm_status_only",
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
            )
        coverage_passed = self.is_coverage_complete(profile)
        core_success_count = self.get_core_success_count(profile)
        profile_sufficient = self.is_profile_sufficient_for_contact(profile)
        turn_quality_passed = self.is_turn_ready_for_contact(
            profile,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            allow_contact_target=allow_contact_target,
        )
        engagement_mode = self.get_engagement_mode(profile, message_count=message_count)
        unresolved_core_fields = self.get_uncovered_core_fields(profile)
        unresolved_medium_fields = self.get_uncovered_medium_fields(profile)
        ongoing_contact_flow = self.has_ongoing_contact_flow(profile)
        can_enter_contact = ongoing_contact_flow or (coverage_passed and profile_sufficient)
        allow_contact_push = (
            allow_contact_target
            and can_enter_contact
            and (ongoing_contact_flow or turn_quality_passed)
            and engagement_mode in {"full", "compact"}
        )
        next_mode = self.get_next_mode(
            coverage_passed=coverage_passed,
            profile_sufficient=profile_sufficient,
            turn_quality_passed=turn_quality_passed,
            engagement_mode=engagement_mode,
            profile=profile,
        )
        effective_allow_medium_target = allow_medium_target and not self.should_block_medium_fields_for_turn(
            profile,
            user_message=user_message,
            allow_contact_target=allow_contact_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            resume_profile_collection=resume_profile_collection,
        )
        if next_mode in {"open_profile_repair", "low_pressure_chat", "terminate_conversion", "contact_hold"}:
            effective_allow_medium_target = False
        missing_fields = self.get_missing_fields(
            profile,
            can_enter_contact,
            allow_contact_target,
            include_medium_fields=effective_allow_medium_target,
        )
        main_target: Optional[str] = None
        side_target: Optional[str] = None
        forced_cover_target: Optional[str] = None
        if next_mode == "collect_core":
            followup_plan = self.followup_planning_layer.choose_followup_targets(
                profile=profile,
                can_enter_contact=False,
                allow_contact_target=False,
                user_message=user_message,
                message_count=message_count,
                allow_medium_target=effective_allow_medium_target,
            )
            main_target = followup_plan.main_target
            side_target = followup_plan.side_target
        elif next_mode == "collect_medium":
            forced_cover_target = self.get_forced_cover_target(profile)
            main_target = forced_cover_target
        elif next_mode == "contact_flow" and allow_contact_push:
            main_target = "contact"

        if next_mode == "collect_core":
            if understanding_result and understanding_result.primary_turn_type == "profile_answer":
                if understanding_result.subtype == "multi_slot_compound" and side_target in understanding_result.resolved_slots:
                    side_target = None
        else:
            side_target = None

        resolved_primary_move = primary_move
        if complaint_reason:
            resolved_primary_move = "repair_and_release"
        elif understanding_result:
            if understanding_result.primary_turn_type == "risk_guard":
                resolved_primary_move = "answer_then_pause"
            elif understanding_result.primary_turn_type in {"faq_concern"}:
                resolved_primary_move = "answer_then_pause"
            elif understanding_result.primary_turn_type == "refusal_boundary_complaint":
                if understanding_result.subtype != "contact_refusal":
                    resolved_primary_move = "soft_hold"
            elif understanding_result.primary_turn_type == "closing_exit":
                resolved_primary_move = "soft_hold"
        if resume_profile_collection:
            resolved_primary_move = "light_followup"
        elif len((user_message or "").strip()) <= 4 and resolved_primary_move == "ack_and_ask":
            resolved_primary_move = "light_followup"

        resolved_allow_contact_target = allow_contact_target
        resolved_allow_medium_target = effective_allow_medium_target
        if resume_profile_collection:
            resolved_allow_contact_target = False
            resolved_allow_medium_target = False
        if next_mode == "open_profile_repair":
            main_target = None
            resolved_allow_contact_target = False
            resolved_allow_medium_target = False
        elif next_mode in {"low_pressure_chat", "terminate_conversion"}:
            resolved_primary_move = "soft_hold"
            main_target = None
            resolved_allow_contact_target = False
            resolved_allow_medium_target = False
        elif next_mode == "contact_hold":
            main_target = None
            resolved_allow_contact_target = False
        elif next_mode == "contact_flow" and allow_contact_push:
            main_target = "contact"

        user_concern_type: Optional[str] = None
        if complaint_reason:
            user_concern_type = "complaint"
        elif understanding_result and understanding_result.primary_turn_type == "faq_concern":
            user_concern_type = self._normalize_user_concern_type(understanding_result.subtype)

        resume_mode: Optional[str] = None
        resume_target: Optional[str] = None
        if (
            prioritize_user_question
            and next_mode not in {"contact_flow", "terminate_conversion"}
            and main_target
        ):
            resume_mode = next_mode
            resume_target = main_target

        return PolicyDecision(
            main_target=main_target,
            side_target=side_target,
            user_type=user_type,
            can_enter_contact=can_enter_contact,
            missing_fields=missing_fields,
            coverage_passed=coverage_passed,
            profile_sufficient=profile_sufficient,
            turn_quality_passed=turn_quality_passed,
            engagement_mode=engagement_mode,
            next_mode=next_mode,
            unresolved_core_fields=unresolved_core_fields,
            unresolved_medium_fields=unresolved_medium_fields,
            forced_cover_target=forced_cover_target,
            core_success_count=core_success_count,
            allow_contact_push=allow_contact_push,
            reason=self.get_decision_reason(
                coverage_passed=coverage_passed,
                profile_sufficient=profile_sufficient,
                turn_quality_passed=turn_quality_passed,
                engagement_mode=engagement_mode,
                unresolved_core_fields=unresolved_core_fields,
                unresolved_medium_fields=unresolved_medium_fields,
                ongoing_contact_flow=ongoing_contact_flow,
            ),
            must_answer_first=prioritize_user_question,
            primary_move=resolved_primary_move,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=resolved_allow_contact_target,
            allow_medium_target=resolved_allow_medium_target,
            user_concern_type=user_concern_type,
            resume_mode=resume_mode,
            resume_target=resume_target,
        )

    @staticmethod
    def _normalize_user_concern_type(intent: str | None) -> str:
        intent_value = str(intent or "").strip().lower()
        if intent_value in {"reliable", "privacy"}:
            return intent_value
        if intent_value in {"clarification", "service_area", "timeline", "photo", "success_rate", "mediator", "fee"}:
            return "faq"
        return "faq"

    def get_main_target(
        self,
        profile: UserProfile,
        can_enter_contact: Optional[bool] = None,
        allow_contact_target: bool = True,
        user_message: str = "",
        message_count: int = 0,
    ) -> Optional[str]:
        """获取当前主目标字段"""
        can_enter_contact = self.can_enter_contact(profile) if can_enter_contact is None else can_enter_contact
        return self.followup_planning_layer.choose_main_target(
            profile=profile,
            can_enter_contact=can_enter_contact,
            allow_contact_target=allow_contact_target,
            user_message=user_message,
            message_count=message_count,
        )

    def get_side_target(
        self,
        profile: UserProfile,
        main_target: Optional[str],
        user_message: str = "",
        message_count: int = 0,
        allow_medium_target: bool = True,
    ) -> Optional[str]:
        """获取顺带字段。

        核心字段始终是主线；婚况、择偶要求、月薪只能自然穿插，不能抢主线。
        """
        return self.followup_planning_layer.choose_side_target(
            profile=profile,
            main_target=main_target,
            user_message=user_message,
            message_count=message_count,
            allow_medium_target=allow_medium_target,
        )

    def _allow_early_side_target(
        self,
        profile: UserProfile,
        *,
        main_target: Optional[str],
        user_message: str = "",
        message_count: int = 0,
    ) -> bool:
        """在核心字段未收完时，仅放开少量高相关拼接问。"""
        if not main_target:
            return False
        if message_count > 4:
            return False
        if not self._message_contains_profile_context(user_message):
            return False

        cue_order = self._extract_message_field_cue_order(user_message)
        for field in ("monthly_income", "marital_status", "partner_requirement"):
            score = self._score_side_target_candidate(
                profile,
                field=field,
                main_target=main_target,
                user_message=user_message,
                message_count=message_count,
                cue_order=cue_order,
                early_phase=True,
            )
            if score > 0:
                return True

        return False

    def _score_side_target_candidate(
        self,
        profile: UserProfile,
        *,
        field: str,
        main_target: Optional[str],
        user_message: str,
        message_count: int,
        cue_order: List[str],
        early_phase: bool = False,
    ) -> int:
        if early_phase and not self._is_early_side_target_pair_allowed(
            field=field,
            main_target=main_target,
            profile=profile,
            cue_order=cue_order,
        ):
            return -1

        if field == "monthly_income":
            if not self.can_use_as_side_target(profile, field):
                return -1
        elif not self.can_actively_ask(profile, field):
            return -1

        if field == "partner_requirement" and main_target == "contact":
            return -1

        message = str(user_message or "")
        latest_cue = cue_order[-1] if cue_order else ""
        profile_sufficient = self.is_profile_sufficient_for_contact(profile)
        trigger_map = {
            "monthly_income": self.INCOME_TRIGGER_KEYWORDS,
            "marital_status": self.MARITAL_STATUS_TRIGGER_KEYWORDS,
            "partner_requirement": self.PARTNER_REQUIREMENT_TRIGGER_KEYWORDS,
        }
        score = 0

        if any(keyword in message for keyword in trigger_map.get(field, [])):
            score += 100

        if field == "monthly_income" and main_target == "occupation" and (
            message_count == 0 or message_count >= 2 or self._message_contains_profile_context(message)
        ):
            score += 90
        if field == "partner_requirement" and main_target in {"age", "location", "occupation"}:
            score += 90

        host_order = self.SIDE_TARGET_HOST_ORDERS.get(field, ())
        if main_target in host_order:
            score += max(0, 70 - host_order.index(main_target) * 10)

        if latest_cue in host_order:
            score += max(0, 30 - host_order.index(latest_cue) * 5)

        host_context_bonus = self._get_side_target_host_context_bonus(profile, field, main_target=main_target)
        score += host_context_bonus

        if field == "marital_status":
            if main_target in {"age", "location", "occupation"} and (
                latest_cue in {"age", "location", "occupation"} or profile_sufficient
            ):
                score += 35
            elif main_target in {"age", "location", "occupation", "education"} and (
                message_count >= 5 or profile_sufficient
            ):
                score += 18

        if field == "partner_requirement" and main_target in {"age", "location", "occupation", "education"} and (
            message_count >= 5 or profile_sufficient
        ):
            score += 24

        if field == "monthly_income" and main_target in {"location", "age"}:
            if self.is_collected(profile, "occupation") or profile.collection_progress.get("occupation"):
                score += 28
            elif "occupation" in cue_order:
                score += 18

        if early_phase:
            if message_count > 4 or not self._message_contains_profile_context(message):
                return -1
            if score < 50:
                return -1
            return score

        return score

    def _is_early_side_target_pair_allowed(
        self,
        *,
        field: str,
        main_target: Optional[str],
        profile: UserProfile,
        cue_order: List[str],
    ) -> bool:
        """opening 阶段只放开少数高相关拼接，避免泛化到不相邻字段。"""
        if field == "monthly_income":
            if main_target == "occupation":
                return True
            if main_target in {"location", "age"} and (
                self.is_collected(profile, "occupation")
                or profile.collection_progress.get("occupation")
                or "occupation" in cue_order
            ):
                return True
            return False

        if field == "marital_status":
            return main_target in {"age", "location", "occupation"}

        if field == "partner_requirement":
            return main_target in {"age", "location", "occupation"}

        return False

    def _get_side_target_host_context_bonus(
        self,
        profile: UserProfile,
        field: str,
        *,
        main_target: Optional[str],
    ) -> int:
        bonus = 0
        for index, host in enumerate(self.SIDE_TARGET_HOST_ORDERS.get(field, ())):
            if host == main_target:
                continue
            if self.is_collected(profile, host) or profile.collection_progress.get(host):
                bonus = max(bonus, max(0, 24 - index * 4))
                break
        return bonus

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

        for field in self._get_priority_order(profile):
            if field == "contact" and (not can_enter_contact or not allow_contact_target):
                continue
            if field == "contact":
                if not self.is_collected(profile, field):
                    fields.append(field)
                continue
            if not self.is_field_covered(profile, field):
                fields.append(field)

        if not include_medium_fields:
            return fields

        for field in self.MEDIUM_COVERAGE_FIELDS:
            if field in fields:
                continue
            if not self.is_field_covered(profile, field):
                fields.append(field)

        return fields

    def get_core_success_count(self, profile: UserProfile) -> int:
        return sum(1 for field in self.CORE_CONTACT_FIELDS if self.is_collected(profile, field))

    def _get_priority_order(self, profile: UserProfile) -> List[str]:
        """返回当前用户的受控主线顺序。

        目标不是完全随机，而是在不打乱主线骨架的前提下，让 age/location/education
        之间存在轻微换位，减少流程感。
        """
        account_id = str(getattr(profile, "account_id", "") or "")
        stable_seed = sum(ord(ch) for ch in account_id)
        core_order = self.CORE_ORDER_VARIANTS[stable_seed % len(self.CORE_ORDER_VARIANTS)]
        return [*core_order, "marital_status", "contact"]

    def _get_contextual_core_target(
        self,
        profile: UserProfile,
        *,
        user_message: str = "",
        message_count: int = 0,
    ) -> Optional[str]:
        """根据用户刚给出的资料，优先选择更像顺着聊的下一个核心字段。"""
        message = str(user_message or "").strip()
        if not message:
            return None

        cue_order = self._extract_message_field_cue_order(message)
        if not cue_order:
            return None
        cues = {field: True for field in cue_order}
        pending_birth_year_bucket = str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
        birth_year_pending = bool(
            pending_birth_year_bucket and not getattr(profile, "birth_year_confirmation_closed", False)
        )

        if birth_year_pending and cues.get("age") and self.can_actively_ask(profile, "age"):
            return "age"

        if cues.get("location") and self.can_actively_ask(profile, "occupation"):
            return "occupation"

        if cues.get("location") and cues.get("occupation"):
            if self.can_actively_ask(profile, "occupation"):
                return "occupation"
            for field in ("education", "age", "sex"):
                if self.can_actively_ask(profile, field):
                    return field

        latest_cue = cue_order[-1]

        if latest_cue == "location":
            for field in ("occupation", "education"):
                if self.can_actively_ask(profile, field):
                    return field

        if latest_cue == "occupation":
            if self.can_actively_ask(profile, "occupation"):
                return "occupation"
            for field in ("education", "age"):
                if self.can_actively_ask(profile, field):
                    return field

        if latest_cue == "age":
            if birth_year_pending and self.can_actively_ask(profile, "age"):
                return "age"
            for field in ("sex", "location"):
                if self.can_actively_ask(profile, field):
                    return field

        if latest_cue == "education":
            for field in ("occupation", "location", "age"):
                if self.can_actively_ask(profile, field):
                    return field

        if latest_cue == "sex":
            for field in ("location", "occupation"):
                if self.can_actively_ask(profile, field):
                    return field

        return None

    @staticmethod
    def _message_contains_profile_context(user_message: str) -> bool:
        return bool(ProfileCollectionPolicy._extract_message_field_cue_order(user_message))

    @staticmethod
    def _extract_message_field_cues(user_message: str) -> Dict[str, bool]:
        cue_order = ProfileCollectionPolicy._extract_message_field_cue_order(user_message)
        return {
            "sex": "sex" in cue_order,
            "age": "age" in cue_order,
            "location": "location" in cue_order,
            "education": "education" in cue_order,
            "occupation": "occupation" in cue_order,
        }

    @staticmethod
    def _extract_message_field_cue_order(user_message: str) -> List[str]:
        message = str(user_message or "").strip().lower()
        if not message:
            return []

        compact = re.sub(r"[，,、。！？!?~～\s]+", "", message)
        education_tokens = ("博士", "硕士", "研究生", "本科", "大专", "中专", "高中")
        occupation_tokens = ("it", "ui", "hr", "qa", "产品", "运营", "设计", "开发", "程序员", "销售", "老师", "医生", "公务员")
        found: List[tuple[int, str]] = []

        sex_match = re.search(r"(男生|男的|女生|女的|我是男|我是女)", message)
        if sex_match:
            found.append((sex_match.start(), "sex"))

        age_match = re.search(r"(\d{2}后|\d{2}岁|\d{4}年|\d{2}年生|90后|95后|85后)", message)
        if age_match:
            found.append((age_match.start(), "age"))

        location_span = ProfileCollectionPolicy._find_location_cue_span(message, compact)
        if location_span is not None:
            found.append((location_span, "location"))

        for token in education_tokens:
            idx = compact.find(token)
            if idx != -1:
                found.append((idx, "education"))
                break

        occupation_match = re.search(r"(做|从事|工作是|工作做|职业是)\S{1,10}", message)
        if occupation_match:
            found.append((occupation_match.start(), "occupation"))
        else:
            for token in occupation_tokens:
                idx = compact.find(token)
                if idx != -1:
                    found.append((idx, "occupation"))
                    break

        found.sort(key=lambda item: item[0])
        ordered_fields: List[str] = []
        for _, field in found:
            if field not in ordered_fields:
                ordered_fields.append(field)
        return ordered_fields

    @staticmethod
    def _find_location_cue_span(message: str, compact: str | None = None) -> int | None:
        content = str(message or "").strip().lower()
        normalized = compact if compact is not None else re.sub(r"[，,、。！？!?~～\s]+", "", content)
        if not content or not normalized:
            return None

        common_cities = (
            "深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港",
        )
        city_match = re.search(
            rf"(?:我(?:是|在|住|来自)?|现在在|来自)?(?P<loc>{'|'.join(common_cities)})(?:这边|这座|这座城市|的|人)?",
            content,
        )
        if city_match:
            return city_match.start("loc")
        if re.search(r"(喜欢|想找|找对象|找另一半|另一半|对象).{0,8}(?:在|来自|住在)", content):
            return None
        if ProfileCollectionPolicy._extract_location_like_text(content):
            phrase_match = re.search(
                r"(?:我在|我目前在|我现在在|我长期在|我一直在|我住在|我来自|我人在|目前在|现在在|长期在|一直在|住在|来自|在)",
                content,
            )
            if phrase_match:
                return phrase_match.start()
            return 0
        return None

    @staticmethod
    def _extract_location_like_text(message: str) -> str | None:
        content = str(message or "").strip()
        if not content:
            return None

        common_terms = (
            "台湾",
            "澳门",
            "香港",
            "国外",
            "国内",
            "老家",
            "家里",
            "县城",
            "小县城",
            "小城市",
            "老城区",
        )
        phrase_patterns = [
            r"(?:我在|我目前在|我现在在|我长期在|我一直在|我住在|我来自|我人在|目前在|现在在|长期在|一直在|住在|来自|在)\s*(?:一个)?(?P<loc>[\u4e00-\u9fa5]{2,12}(?:市|省|县|区|州|特别行政区|地区|小县城|小城市|县城)?|台湾|澳门|香港|国外|国内|老家|家里)(?:这边|这里|那边)?(?:呢|呀|哦|哈|啊|啦)?",
            r"^(?P<loc>台湾|澳门|香港|国外|国内|老家|家里|县城|小县城|小城市)(?:呢|呀|哦|哈|啊|啦)?$",
        ]
        for pattern in phrase_patterns:
            match = re.search(pattern, content)
            if not match:
                continue
            candidate = str(match.group("loc") or "").strip("，,、。！？!?~～ ")
            candidate = re.sub(r"(这边|这里|那边|呢|呀|哦|哈|啊|啦)$", "", candidate)
            candidate = candidate.lstrip("一个")
            if not candidate:
                continue
            if candidate in common_terms:
                return candidate
            if re.search(r"(本科|大专|硕士|博士|研究生|单身|离异|未婚|已婚|做|工作|收入|月薪)", candidate):
                continue
            if re.fullmatch(r"[\u4e00-\u9fa5]{2,12}(?:市|省|县|区|州|特别行政区|地区)?", candidate):
                return candidate
        return None

    def is_core_field_covered(self, profile: UserProfile, field: str) -> bool:
        if profile.skipped_fields.get(field, False) or profile.is_active_ask_closed(field):
            return True
        if self._has_pending_resume_for_field(profile, field):
            return False
        if (
            field == "age"
            and str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
            and not getattr(profile, "birth_year_confirmation_closed", False)
        ):
            return False
        return self.is_collected(profile, field) or profile.get_effective_ask_count(field) >= 2

    def is_medium_field_covered(self, profile: UserProfile, field: str) -> bool:
        if profile.skipped_fields.get(field, False) or profile.is_active_ask_closed(field):
            return True
        if self._has_pending_resume_for_field(profile, field):
            return False
        return self.is_collected(profile, field) or profile.get_effective_ask_count(field) >= 1

    @staticmethod
    def _has_pending_resume_for_field(profile: UserProfile, field: str) -> bool:
        if not field:
            return False
        if str(getattr(profile, "resume_profile_target", "") or "").strip() == field:
            return True
        if str(getattr(profile, "pending_retry_field", "") or "").strip() == field:
            return True
        return False

    def is_field_covered(self, profile: UserProfile, field: str) -> bool:
        if field in self.CORE_CONTACT_FIELDS:
            return self.is_core_field_covered(profile, field)
        if field in self.MEDIUM_COVERAGE_FIELDS:
            return self.is_medium_field_covered(profile, field)
        if field == "contact":
            return self.is_collected(profile, "contact")
        return self.is_collected(profile, field) or profile.skipped_fields.get(field, False)

    def get_uncovered_core_fields(self, profile: UserProfile) -> List[str]:
        return [field for field in self.CORE_CONTACT_FIELDS if not self.is_core_field_covered(profile, field)]

    def get_uncovered_medium_fields(self, profile: UserProfile) -> List[str]:
        return [field for field in self.MEDIUM_PRIORITY_ORDER if not self.is_medium_field_covered(profile, field)]

    def is_coverage_complete(self, profile: UserProfile) -> bool:
        return not self.get_uncovered_core_fields(profile) and not self.get_uncovered_medium_fields(profile)

    def is_profile_sufficient_for_contact(self, profile: UserProfile) -> bool:
        if self.is_collected(profile, "contact"):
            return True
        return self.get_core_success_count(profile) >= 3

    def is_turn_ready_for_contact(
        self,
        profile: UserProfile,
        *,
        prioritize_user_question: bool = False,
        primary_move: str = "ack_and_ask",
        allow_contact_target: bool = True,
    ) -> bool:
        if not allow_contact_target:
            return False
        if prioritize_user_question:
            return False
        if profile.repair_mode and profile.ask_cooldown_turns > 0:
            return False
        if self.has_divorce_confirmation_pending(profile):
            return False
        if primary_move in {"answer_then_pause", "soft_hold", "confirm_status_only", "repair_and_release", "ack_only"}:
            return False
        return True

    def get_engagement_mode(self, profile: UserProfile, *, message_count: int = 0) -> str:
        if getattr(profile, "conversation_ended", False):
            return "close"
        if getattr(profile, "non_cooperation_turns", 0) >= 4 or getattr(profile, "off_topic_turns", 0) >= 4:
            return "close"
        if (
            getattr(profile, "non_cooperation_turns", 0) >= 3
            or getattr(profile, "off_topic_turns", 0) >= 3
            or getattr(profile, "open_profile_attempts", 0) >= 2
        ):
            return "light"
        if message_count >= 6:
            return "compact"
        return "full"

    def get_forced_cover_target(self, profile: UserProfile) -> Optional[str]:
        if self.get_uncovered_core_fields(profile):
            return None
        for field in self.MEDIUM_PRIORITY_ORDER:
            if not self.is_medium_field_covered(profile, field) and self.can_actively_ask(profile, field):
                return field
        return None

    def get_medium_transition_host(self, profile: UserProfile, medium_field: str) -> Optional[str]:
        """为剩余中等字段寻找更自然的融合宿主。"""
        for host in self.SIDE_TARGET_HOST_ORDERS.get(medium_field, ()):
            if getattr(profile, host, None) or profile.collection_progress.get(host):
                return host
        return None

    def get_next_mode(
        self,
        *,
        coverage_passed: bool,
        profile_sufficient: bool,
        turn_quality_passed: bool,
        engagement_mode: str,
        profile: UserProfile,
    ) -> str:
        if engagement_mode == "close":
            return "terminate_conversion"
        if engagement_mode == "light":
            return "low_pressure_chat"
        if self.has_ongoing_contact_flow(profile):
            return "contact_flow"
        if not coverage_passed:
            return "collect_core" if self.get_uncovered_core_fields(profile) else "collect_medium"
        if not profile_sufficient:
            return "open_profile_repair" if getattr(profile, "open_profile_attempts", 0) < 2 else "low_pressure_chat"
        if not turn_quality_passed:
            return "contact_hold"
        return "contact_flow"

    @staticmethod
    def get_decision_reason(
        *,
        coverage_passed: bool,
        profile_sufficient: bool,
        turn_quality_passed: bool,
        engagement_mode: str,
        unresolved_core_fields: List[str],
        unresolved_medium_fields: List[str],
        ongoing_contact_flow: bool = False,
    ) -> str:
        if ongoing_contact_flow:
            return "ongoing_contact_flow_freeze_profile_collection"
        if engagement_mode == "close":
            return "cost_control_close"
        if engagement_mode == "light":
            return "cost_control_light"
        if unresolved_core_fields:
            return "core_fields_not_covered"
        if unresolved_medium_fields:
            return "medium_fields_not_covered"
        if not coverage_passed:
            return "coverage_not_passed"
        if not profile_sufficient:
            return "profile_not_sufficient"
        if not turn_quality_passed:
            return "turn_not_suitable_for_contact"
        return "contact_ready"

    def has_ongoing_contact_flow(self, profile: UserProfile) -> bool:
        """判断当前是否处于联系方式阶段或联系方式处理中。"""
        if (
            bool(getattr(profile, "contact_complete", False))
            or (
                bool(getattr(profile, "phone_collected", False) and getattr(profile, "phone", None))
                and bool(getattr(profile, "wechat_collected", False) and getattr(profile, "wechat", None))
            )
            or (
                bool(getattr(profile, "phone_collected", False) and getattr(profile, "phone", None))
                and bool(getattr(profile, "rejected_wechat", False))
            )
            or (
                bool(getattr(profile, "wechat_collected", False) and getattr(profile, "wechat", None))
                and bool(getattr(profile, "rejected_phone", False))
            )
        ):
            if not any(
                [
                    bool(str(getattr(profile, "pending_contact_field", "") or "").strip()),
                    bool(str(getattr(profile, "pending_contact_candidate", "") or "").strip()),
                    bool(str(getattr(profile, "pending_contact_hint", "") or "").strip()),
                    bool(
                        getattr(profile, "phone_ask_count", 0) > 0
                        and not getattr(profile, "phone_collected", False)
                        and not getattr(profile, "rejected_phone", False)
                    ),
                    bool(
                        getattr(profile, "wechat_ask_count", 0) > 0
                        and not getattr(profile, "wechat_collected", False)
                        and not getattr(profile, "rejected_wechat", False)
                    ),
                ]
            ):
                return False
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
        if (
            self.get_core_success_count(profile) >= 4
            and self.is_collected(profile, "marital_status")
            and self.is_collected(profile, "partner_requirement")
            and self.is_collected(profile, "monthly_income")
        ):
            return True
        return self.is_coverage_complete(profile) and self.is_profile_sufficient_for_contact(profile)

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
        if (
            field == "age"
            and str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
            and not getattr(profile, "birth_year_confirmation_closed", False)
        ):
            return self.ACTIVE
        if str(getattr(profile, "pending_retry_field", "") or "").strip() == field:
            return self.ACTIVE
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

        ask_count = profile.get_effective_ask_count(field)
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
        if field == "age":
            pending_bucket = str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
            if pending_bucket and not getattr(profile, "birth_year_confirmation_closed", False):
                return False
        return bool(profile.collection_progress.get(field, False))

    def should_block_preference_ask(self, profile: UserProfile, user_message: str = "") -> bool:
        """
        Phase 2: 判断是否应该阻止偏好类追问。

        当 partner_requirement 已经收集后，后续所有"最看重哪一点/你更在意什么/按什么方向帮你筛"等
        同义问题都应该被阻止。
        """
        # 一旦择偶要求已收集，或主动追问已被关闭，就禁止任何同义偏好追问。
        if self.is_collected(profile, "partner_requirement") or profile.is_active_ask_closed("partner_requirement"):
            logger.debug("[偏好去重] partner_requirement 已收集或已关闭主动追问，阻止偏好追问")
            return True
        return False
