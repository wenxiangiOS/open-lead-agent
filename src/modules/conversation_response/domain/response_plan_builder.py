from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.modules.conversation_response.domain.response_plan import ResponsePlan


@dataclass
class ResponsePlanPromptSpec:
    header: str
    context_summary: str
    plan: ResponsePlan

    def to_generation_instruction(self) -> str:
        return self.plan.to_generation_instruction(
            header=self.header,
            context_summary=self.context_summary,
        )


class ResponsePlanBuilder:
    """把结构化理解和业务决策转换成统一的表达计划。"""

    FIELD_LABEL_MAP = {
        "sex": "性别",
        "age": "年龄/出生年份",
        "location": "常住城市",
        "education": "学历",
        "occupation": "工作方向",
        "marital_status": "感情状态/婚况",
        "monthly_income": "收入区间",
        "partner_requirement": "择偶要求/更看重哪一点",
        "contact": "联系方式",
    }
    _ASK_FIELD_FOLLOWUP_BLOCK_MAP = {
        "occupation": ["年龄/出生年份", "感情状态/婚况", "联系方式", "择偶要求/更看重哪一点"],
        "education": ["年龄/出生年份", "感情状态/婚况", "联系方式"],
        "monthly_income": ["年龄/出生年份", "感情状态/婚况", "联系方式"],
        "sex": ["年龄/出生年份", "感情状态/婚况", "联系方式"],
        "contact": ["年龄/出生年份", "感情状态/婚况"],
    }

    def __init__(self, *, collection_policy: Any, turn_understanding_service: Any) -> None:
        self.collection_policy = collection_policy
        self.turn_understanding_service = turn_understanding_service

    @staticmethod
    def _render_semantic_summary_context(user_profile: UserProfile) -> str:
        semantic_summary = dict(getattr(user_profile, "last_semantic_summary", {}) or {})
        soft_profile_summary = str(semantic_summary.get("soft_profile_summary") or "").strip()
        partner_summary = str(semantic_summary.get("partner_summary") or "").strip()
        lines: list[str] = []
        if soft_profile_summary:
            lines.append(f"本轮自然画像摘要：{soft_profile_summary}。")
        if partner_summary:
            lines.append(f"本轮择偶摘要：{partner_summary}。")
        return "\n".join(lines)

    def build(
        self,
        *,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        user_message: str,
        understanding_result: TurnUnderstandingResult,
    ) -> ResponsePlanPromptSpec | None:
        if turn_decision.response_channel != "model":
            return None

        primary_turn_type = understanding_result.primary_turn_type or ""
        subtype = understanding_result.subtype or ""
        secondary_signals = set(understanding_result.secondary_signals or [])
        resolved_slots = self._effective_resolved_slots(understanding_result)

        repair_spec = self._build_repair_or_hold_spec(
            turn_decision=turn_decision,
            primary_turn_type=primary_turn_type,
            subtype=subtype,
            secondary_signals=secondary_signals,
            resolved_slots=resolved_slots,
        )
        if repair_spec:
            return repair_spec

        opening_spec = self._build_opening_spec(
            primary_turn_type=primary_turn_type,
            subtype=subtype,
            secondary_signals=secondary_signals,
            resolved_slots=resolved_slots,
            user_profile=user_profile,
            user_message=user_message,
        )
        if opening_spec:
            return opening_spec

        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        if ask_field:
            return self._build_field_followup_spec(
                ask_field=ask_field,
                turn_decision=turn_decision,
                user_profile=user_profile,
                user_message=user_message,
                primary_turn_type=primary_turn_type,
                subtype=subtype,
                secondary_signals=secondary_signals,
                resolved_slots=resolved_slots,
            )

        return None

    def _build_repair_or_hold_spec(
        self,
        *,
        turn_decision: TurnDecision,
        primary_turn_type: str,
        subtype: str,
        secondary_signals: set[str],
        resolved_slots: dict[str, str],
    ) -> ResponsePlanPromptSpec | None:
        intent = str(getattr(turn_decision, "intent", "") or "").strip()
        risk = str(getattr(turn_decision, "risk", "") or "").strip()
        primary_move = str(getattr(turn_decision, "primary_move", "") or "").strip()

        if intent == "complaint" or primary_move == "repair_and_release":
            plan = ResponsePlan(
                mode="complaint_repair",
                ack_items=[
                    "先明确承认刚才问法让用户不舒服或有重复感",
                    "用一小句降压，说明这轮先不继续追资料",
                ],
                next_move="给出一个明确可执行的继续方式，避免空悬收口",
                resolved_slots=resolved_slots,
                secondary_signals=sorted(secondary_signals),
                constraints=[
                    "最终只生成一段自然回复，1-2句为主，不要分条。",
                    "禁止复用固定模板句式，不能输出“这个点先收住，我们接着往下聊”这类空悬收口。",
                    "必须包含一个可执行的下一步，例如让用户先说最在意的择偶点或想先聊的方向。",
                    "这轮不要继续追问新资料字段，不要索要联系方式。",
                    "语气像真人修复，不要流程腔或策略泄漏。",
                ],
            )
            return ResponsePlanPromptSpec(
                header="RESPONSE_PLAN（投诉修复优先）",
                context_summary=(
                    "当前轮命中 complaint 修复模式，必须以体验修复优先。\n"
                    f"结构化理解：turn={primary_turn_type}/{subtype}；"
                    f"secondary={','.join(sorted(secondary_signals)) or '-'}；"
                    f"slots={json.dumps(resolved_slots, ensure_ascii=False) if resolved_slots else '{}'}。"
                ),
                plan=plan,
            )

        if risk == "boundary" or intent == "boundary" or primary_move == "soft_hold":
            plan = ResponsePlan(
                mode="boundary_hold",
                ack_items=[
                    "先接住用户边界或顾虑，明确这轮不强推资料",
                ],
                next_move="给一个低压力承接句，允许用户按自己节奏继续",
                resolved_slots=resolved_slots,
                secondary_signals=sorted(secondary_signals),
                constraints=[
                    "最终只生成一段自然回复，1-2句为主，不要分条。",
                    "不要继续追问新资料，不要索要电话或微信。",
                    "禁止使用固定模板化边界句式，避免重复客服腔。",
                    "必须保持轻口语，像真人接住边界，不要教育用户。",
                ],
            )
            return ResponsePlanPromptSpec(
                header="RESPONSE_PLAN（边界承接优先）",
                context_summary=(
                    "当前轮命中 boundary 承接模式，必须先稳住用户体验。\n"
                    f"结构化理解：turn={primary_turn_type}/{subtype}；"
                    f"secondary={','.join(sorted(secondary_signals)) or '-'}；"
                    f"slots={json.dumps(resolved_slots, ensure_ascii=False) if resolved_slots else '{}'}。"
                ),
                plan=plan,
            )
        return None

    def _build_opening_spec(
        self,
        *,
        primary_turn_type: str,
        subtype: str,
        secondary_signals: set[str],
        resolved_slots: dict[str, str],
        user_profile: UserProfile,
        user_message: str,
    ) -> ResponsePlanPromptSpec | None:
        if primary_turn_type != "opening" or subtype not in {
            "matchmaking_intent",
            "service_confirmation_opening",
            "low_pressure_opening",
            "opening_clarify",
        }:
            return None

        partner_gender_preference = str(
            resolved_slots.get("partner_gender_preference")
            or getattr(user_profile, "partner_gender_preference", "")
            or ""
        ).strip()
        gender_label = "男生" if partner_gender_preference == "男" else "女生" if partner_gender_preference == "女" else ""
        inferred_sex_label = self._infer_user_sex_label(
            user_profile=user_profile,
            user_message=user_message,
            resolved_slots=resolved_slots,
        )

        ack_items: list[str] = []
        if "opening_greeting" in secondary_signals or self.turn_understanding_service._looks_like_greeting(user_message):  # noqa: SLF001
            ack_items.append("轻接住用户的开场问候")
        if (
            subtype == "service_confirmation_opening"
            or "service_confirmation_like" in secondary_signals
            or self.turn_understanding_service._is_service_confirmation_like(user_message)  # noqa: SLF001
        ):
            ack_items.append("如果用户在确认能不能帮忙介绍，用一句很轻的口语化回应接住“可以帮忙介绍”这个点，不要自我介绍式强调服务身份")
        if subtype == "matchmaking_intent":
            ack_items.append("自然接住用户是在认真找对象，不要把这句说成客服记录需求")
        if gender_label:
            ack_items.append(f"自然接住用户偏向找{gender_label}这点")
        if inferred_sex_label and not str(getattr(user_profile, "sex", "") or "").strip():
            ack_items.append(f"当前语境下高概率可推断用户是{inferred_sex_label}，可顺手做轻量软确认")
        if not ack_items:
            ack_items.append("自然接住用户当前这句开场")

        next_move = "邀请用户简单介绍自己，方便顺着了解"
        if inferred_sex_label and not str(getattr(user_profile, "sex", "") or "").strip():
            next_move = "如果顺着聊合适，可先轻量软确认性别，再自然进入资料了解"

        plan = ResponsePlan(
            mode="opening",
            ack_items=ack_items,
            next_move=next_move,
            resolved_slots=resolved_slots,
            secondary_signals=sorted(secondary_signals),
            constraints=[
                "最终只生成一段自然回复，不要分条，不要机械拼接，不要出现三段并列话术。",
                "不要重复表达同一个意思，尤其不要重复两次自我介绍引导。",
                "要像真人顺着用户这句话往下接，不要回退成通用“你好呀先介绍自己”。",
                "如果已经确认服务，不要再重复解释太多；一句带过即可。",
                "保持轻口语、自然、简洁，优先 1-2 句完成。",
                "单轮最多只推进两个信息点；如果这轮还要顺手软确认性别，性别确认本身也算一个信息点，不能再额外追第三个字段。",
                "不要使用固定模板话术，不能把任何一句样板话重复复用成统一句式。",
                "避免高重复客服腔，比如“我们这边就是帮忙牵线介绍对象的哈”“你的需求我先记下来啦”这类说法。",
                "如果需要确认性别，优先做轻量软确认，不要默认退化成‘你是女生还是男生’这种二选一硬问。",
                "软确认要像顺手核对一个小点，允许自然变化，不要固定使用同一转折词。",
            ],
        )
        return ResponsePlanPromptSpec(
            header="RESPONSE_PLAN（高优先级）",
            context_summary=(
                "这条模式优先级高于 quick_faq 风格、固定开场模板和本地拼接式回复。\n"
                f"当前结构化理解：turn={primary_turn_type}/{subtype}；"
                f"secondary={','.join(sorted(secondary_signals)) or '-'}；"
                f"slots={json.dumps(resolved_slots, ensure_ascii=False) if resolved_slots else '{}'}。"
                f"{chr(10) + self._render_semantic_summary_context(user_profile) if self._render_semantic_summary_context(user_profile) else ''}"
            ),
            plan=plan,
        )

    def _build_field_followup_spec(
        self,
        *,
        ask_field: str,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        user_message: str,
        primary_turn_type: str,
        subtype: str,
        secondary_signals: set[str],
        resolved_slots: dict[str, str],
    ) -> ResponsePlanPromptSpec:
        semantic_summary = dict(getattr(user_profile, "last_semantic_summary", {}) or {})
        limit_to_single_field = str(semantic_summary.get("turn_mode") or "").strip() == "dense_intro"
        side_target = ""
        if getattr(turn_decision, "allow_medium_target", False) and not limit_to_single_field:
            try:
                policy_decision = self.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=getattr(turn_decision, "allow_contact_target", False),
                    allow_medium_target=True,
                    prioritize_user_question=getattr(turn_decision, "prioritize_user_question", False),
                    primary_move=getattr(turn_decision, "primary_move", "ack_and_ask"),
                )
                if policy_decision.main_target == ask_field:
                    side_target = str(policy_decision.side_target or "").strip()
                    if side_target and not self.collection_policy.can_actively_ask(user_profile, side_target):
                        side_target = ""
            except Exception:
                side_target = ""

        main_label = self.FIELD_LABEL_MAP.get(ask_field, ask_field)
        side_label = self.FIELD_LABEL_MAP.get(side_target, side_target) if side_target else ""
        plan_items = [f"主任务是自然追问“{main_label}”"]
        ack_items: list[str] = []
        inferred_sex_label = self._infer_user_sex_label(
            user_profile=user_profile,
            user_message=user_message,
            resolved_slots=resolved_slots,
        )

        if ask_field == "contact":
            location = str(getattr(user_profile, "location", "") or "").strip()
            occupation = str(getattr(user_profile, "occupation", "") or "").strip()
            if location and occupation:
                ack_items.append(f"自然带上用户在{location}做{occupation}这块的上下文")
            elif location:
                ack_items.append(f"自然带上用户目前在{location}这边的上下文")
            elif occupation:
                ack_items.append(f"自然带上用户做{occupation}这块的上下文")
            ack_items.append("轻量说明留联系方式是为了后面有合适方向时更方便继续联系")

        if side_label:
            plan_items.append(f"如果顺着聊合适，请把“{side_label}”自然融合在同一句或紧邻句里")
            plan_items.append("主字段仍然是主线，顺带字段只能轻轻带出，不能抢主线")
        if ask_field == "partner_requirement" and getattr(user_profile, "partner_gender_preference", None):
            gender_label = "男生" if user_profile.partner_gender_preference == "男" else "女生"
            plan_items.append(f"已知用户偏向找{gender_label}，本轮不要再把这个当成择偶要求本体，要追问除此之外更看重哪一点")
        if ask_field == "sex" and inferred_sex_label:
            plan_items.append(f"当前语境下高概率可推断用户是{inferred_sex_label}，本轮优先做轻量软确认，不要直接生硬二选一")
            plan_items.append("性别确认要像顺手核对一个小点，不要退化成固定的“你是男生还是女生”问法")
        if side_target == "marital_status":
            plan_items.append("婚况只能轻问感情状态/婚况大概怎样，不要并列枚举未婚和离异")
            plan_items.append("婚况最好自然补半句解释，比如有的人分居中也会直接说自己单身，所以想确认准一点")
            plan_items.append("不要默认问成‘你现在是单身状态吗’或‘你现在单身吗’这类把婚况窄化成单身确认的句式")
            plan_items.append("绝对不要出现‘单身状态’四个字，优先使用‘婚况’或‘感情状态’")
        if side_target == "monthly_income":
            plan_items.append("月薪和工作要自然拼接在一起问，不要像切出去单独盘问收入")
        if ask_field == "marital_status":
            plan_items.append("本轮主问婚况时，也要用开放式问法，优先问感情状态/婚况大概怎样")
            plan_items.append("如果需要解释，只给一小句自然原因，解释方向围绕‘有些情况不适合直接按单身理解’，但不要固定复用同一句")
            plan_items.append("禁止默认生成‘你现在是单身状态吗’‘现在单身吗’这种单身确认句式")
            plan_items.append("绝对不要出现‘单身状态’四个字，必须改成‘婚况’或‘感情状态’")
        if ask_field == "contact":
            plan_items.append("保持轻量自然，不要承诺具体结果，不要过度施压")
            plan_items.append("如果上一句刚收下偏好或资料，先顺手接住半句，再自然转到联系方式，不要直接硬切")
        blocked_labels = [
            label
            for label in self._ASK_FIELD_FOLLOWUP_BLOCK_MAP.get(ask_field, [])
            if label and label != main_label and label != side_label
        ]
        if blocked_labels:
            plan_items.append(
                "除主字段"
                + (f"和顺带字段“{side_label}”" if side_label else "")
                + "外，本轮不要擅自改问"
                + "、".join(f"“{label}”" for label in blocked_labels)
            )

        plan = ResponsePlan(
            mode="field_followup",
            ack_items=ack_items or plan_items[:1],
            next_move="顺着当前资料自然往下追问",
            ask_field=main_label,
            side_target=side_label or None,
            resolved_slots=resolved_slots,
            secondary_signals=sorted(secondary_signals),
            constraints=[
                "最终只生成一段自然回复，不要列表，不要模板化，不要连续硬问两句毫无衔接的问题。",
                "如果用户这轮刚给了资料，先轻接住，再顺着问下一步；不要机械复读。",
                "如果需要问 side-target，要融合得自然，不能像表单。",
                "单轮最多推进两个信息点，不要一口气问超过两个字段；如果这轮还要补软确认性别，性别确认也计入总数。",
                "不要重复表达同一个引导，不要把同一字段问两次。",
                "保持 1-2 句，像真人顺着聊。",
                "不要使用固定模板话术，不要反复用完全相同的起手句或转折句。",
                "如果需要补解释，解释只能作为自然变体方向，不能固定复用某一句样板话。",
                "涉及婚况时，禁止使用‘单身状态’这种窄化问法，必须用‘婚况’或‘感情状态’。",
                *(plan_items[1:] if len(plan_items) > 1 else []),
            ],
        )
        return ResponsePlanPromptSpec(
            header="FIELD_RESPONSE_PLAN（高优先级）",
            context_summary=(
                f"当前结构化理解：turn={primary_turn_type or '-'} / {subtype or '-'}；"
                f"ask_field={ask_field}；secondary={','.join(sorted(secondary_signals)) or '-'}；"
                f"slots={json.dumps(resolved_slots, ensure_ascii=False) if resolved_slots else '{}'}。"
                f"{chr(10) + self._render_semantic_summary_context(user_profile) if self._render_semantic_summary_context(user_profile) else ''}"
            ),
            plan=plan,
        )

    def _infer_user_sex_label(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        resolved_slots: dict[str, str],
    ) -> str:
        preference = str(
            resolved_slots.get("partner_gender_preference")
            or getattr(user_profile, "partner_gender_preference", "")
            or self.turn_understanding_service._extract_partner_gender_preference(user_message)  # noqa: SLF001
            or ""
        ).strip()
        if preference == "男":
            return "女生"
        if preference == "女":
            return "男生"
        return ""

    @staticmethod
    def _effective_resolved_slots(understanding_result: TurnUnderstandingResult) -> dict[str, str]:
        persistence_plan = getattr(understanding_result, "persistence_plan", None)
        if persistence_plan is None:
            return {k: str(v) for k, v in (getattr(understanding_result, "resolved_slots", {}) or {}).items()}
        resolved_slots: dict[str, str] = {}

        for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
            field_name = str(getattr(field, "field", "") or "").strip()
            scope = str(getattr(field, "scope", "") or "").strip()
            if not field_name or scope not in {"self", "contact", "partner"}:
                continue
            resolved_slots[field_name] = str(getattr(field, "normalized_value", "") or "")
        return resolved_slots
