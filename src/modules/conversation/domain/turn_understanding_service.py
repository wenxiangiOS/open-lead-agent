from __future__ import annotations

import logging
import random
import re
from datetime import datetime
from typing import TYPE_CHECKING, Dict

from src.modules.conversation.domain.turn_understanding_models import (
    BlockedSlot,
    SlotCandidate,
    TurnType,
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation.domain.collection_concern_detector import CollectionConcernDetector
from src.modules.conversation_understanding.domain.contextual_slot_governance_layer import (
    ContextualSlotGovernanceLayer,
)

if TYPE_CHECKING:
    from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)

COMPLAINT_HINT_PATTERNS = (
    r"怎么一直问",
    r"你不是刚问过",
    r"问这么细",
    r"怎么又问",
    r"别再问",
)
TOPIC_SHIFT_HINT_PATTERNS = (
    r"先说这个",
    r"先聊这个",
    r"先不说那个",
    r"先不聊那个",
    r"先讲这个",
    r"换个话题",
    r"先说别的",
)
WORK_BUSY_HINT_PATTERNS = (
    r"忙",
    r"加班",
    r"工作挺忙",
    r"上班忙",
)
LOCATION_REUSE_HINT_PATTERNS = (
    r"你们那边",
    r"我那边",
    r"在那边",
    r"那边的话",
)
PREFERENCE_REUSE_HINT_PATTERNS = (
    r"这种类型",
    r"这类",
    r"推荐",
    r"合适的",
)
SELF_HARM_GUARD_PATTERNS = (
    r"不想活",
    r"活不下去",
    r"想自杀",
    r"结束自己",
    r"轻生",
)
MEDICAL_GUARD_PATTERNS = (
    r"抑郁",
    r"吃什么药",
    r"医疗",
    r"诊断",
)
LEGAL_GUARD_PATTERNS = (
    r"法律",
    r"起诉",
    r"合同",
    r"财产分割",
)
OVERREACH_GUARD_PATTERNS = (
    r"私人微信",
    r"内部名单",
    r"发我.*名单",
    r"绕过流程",
    r"直接给我资料",
)
AI_IDENTITY_GUARD_PATTERNS = (
    r"你是ai吗",
    r"你是AI吗",
    r"你是不是ai",
    r"你是真人还是机器人",
    r"你是不是机器人",
    r"你是机器人吗",
)
ABUSE_GUARD_PATTERNS = (
    r"傻",
    r"滚",
    r"闭嘴",
    r"烦不烦",
    r"有病",
    r"操",
    r"草",
    r"妈的",
    r"去死",
    r"智障",
)
BOUNDARY_PAUSE_PATTERNS = (
    r"不给电话",
    r"不方便",
    r"不想留",
    r"不太想说",
    r"不太想展开",
    r"先不说",
    r"先不留",
    r"暂时不留",
    r"先别问我这些",
    r"先别问这些",
    r"问得太细",
    r"问这么细",
    r"先不聊资料",
    r"先别聊资料",
    r"先不聊这个",
    r"先聊这个",
    r"换个话题",
    r"先聊别的",
)
SERVICE_CONFIRMATION_SUBJECT_PATTERNS = (
    "你们",
    "这边",
    "这里",
    "你家",
    "你们这",
)
SERVICE_CONFIRMATION_SERVICE_PATTERNS = (
    "介绍对象",
    "介绍",
    "牵线",
    "找对象",
    "相亲",
    "脱单",
)
SERVICE_CONFIRMATION_QUESTION_PATTERNS = (
    "吗",
    "是吧",
    "对吧",
    "啊",
    "呀",
    "?",
    "？",
)
SERVICE_CONFIRMATION_DIRECT_PATTERNS = (
    r"你们.*介绍对象",
    r"你们.*牵线",
    r"你们.*找对象",
    r"这边.*介绍对象",
    r"这边.*牵线",
    r"这边.*找对象",
    r"这里.*介绍对象",
    r"这里.*牵线",
    r"帮.*介绍对象",
    r"帮.*找对象",
    r"做.*相亲介绍",
    r"做.*介绍对象",
    r"做.*牵线",
)
WITHDRAW_STRONG_PATTERNS = (
    r"(先)?不聊了",
    r"不想(再)?聊了",
    r"不想(再)?说了",
    r"(先)?不说了",
    r"不想继续(聊|说|了解)?了",
    r"算了(吧)?",
    r"(就)?先这样(吧)?",
    r"(先)?到这(儿)?吧",
    r"(今天)?先到这(儿)?吧",
    r"(改天|回头|下次)(再|再来)?说",
    r"(暂时)?不考虑了",
    r"没必要继续了",
    r"别问了",
    r"不想回答了",
)
WITHDRAW_SOFT_PATTERNS = (
    r"先这样",
    r"先停一下",
    r"先暂停吧",
    r"晚点再聊",
    r"有空再聊",
    r"我先忙",
    r"现在不方便聊",
    r"我先去忙了",
    r"之后再说",
    r"我再想想",
    r"我考虑考虑",
    r"先不往下说了",
    r"先不往下聊了",
    r"这个先不展开了",
)
COMPLAINT_PATTERNS = (
    r"问这么多",
    r"怎么问这么多",
    r"怎么问这么多信息",
    r"问这么多信息",
    r"信息问这么多",
    r"问太多",
    r"问的太多",
    r"问太多了",
    r"问的次数太多",
    r"次数太多",
    r"一直问",
    r"老问",
    r"怎么一直问",
    r"怎么老问",
    r"问了一遍又一遍",
    r"问一遍又一遍",
    r"别一直问",
    r"别老问",
    r"有点烦",
    r"太烦了",
    r"有点啰嗦",
    r"太啰嗦",
    r"查户口",
    r"问这么细",
    r"问这么详细",
    r"问得太细",
    r"问得太详细",
    r"重复问",
    r"重复了",
    r"又问这个",
    r"怎么又问",
    r"刚不是问过",
    r"刚不是问了",
    r"前面不是说了",
)
REPEAT_ASK_COMPLAINT_PATTERNS = (
    r"不是说了[吗嘛]",
    r"不是说[了过]",
    r"不是回答[了过]",
    r"不是告诉你[了过]",
    r"不是跟你说[了过]",
    r"刚才不是[说讲]",
    r"刚不是[说讲]",
    r"前面不是[说讲]",
    r"上轮不是[说讲]",
    r"别再问",
    r"不要再问",
    r"不用再问",
    r"怎么还问",
    r"怎么又来问",
    r"你怎么还问",
    r"你怎么又问",
    r"你还问",
    r"又来这套",
    r"换个话题",
    r"换个方向",
    r"别问这个",
    r"不问这个",
    r"不用问这个",
    r"说过了",
    r"讲过了",
    r"都说了",
    r"都讲过了",
    r"已经说[了过]",
    r"已经回答[了过]",
    r"我前面说",
    r"我刚才说",
    r"我之前说",
)
RESUME_PROFILE_COLLECTION_PATTERNS = (
    "你不问其他了",
    "你倒是问",
    "继续问",
    "继续聊资料",
    "继续问我",
    "接着问",
    "往下问",
)
FAQ_ANSWER_MARKERS = (
    "收费",
    "免费",
    "隐私",
    "流程",
    "联系方式只是为了",
    "方便联系",
    "不会随便",
    "不会外泄",
    "保护你的隐私",
    "给你说清楚",
    "我先跟你说清楚",
    "我先说清楚",
    "你可以放心",
    "理解偏了",
    "乱登记",
    "乱用",
    "这些资料主要是为了",
    "不会拿去",
    "不是拿去",
    "我知道你会在意",
    "问得太细",
    "了解得这么清楚",
    "匹配对象的时候更精准",
    "匹配更符合你预期",
    "不符合你要求的男生",
    "严格保密",
)
ACKNOWLEDGEMENT_MESSAGES = {
    "好",
    "好的",
    "知道了",
    "了解了",
    "明白了",
    "行",
    "可以",
    "嗯",
    "嗯嗯",
    "哦",
    "收到",
    "没问题",
    "好哦",
}
FAST_PATH_PREFERENCE_ACK_VARIANTS = (
    "你这边更偏向{preference}这一类。",
    "听起来你会更看重{preference}这一点。",
    "{preference}这个点我先记下了。",
)
WECHAT_INTENT_KEYWORDS = (
    "留微信可以吗", "微信可以", "微信方便", "留微信行吗", "给微信可以吗",
    "我先给微信", "先给微信吧", "留微信吧",
    "用微信联系", "加微信", "微信联系", "用微信", "留个微信",
)
PHONE_REFUSAL_PREFERENCE_KEYWORDS = (
    "电话不方便", "电话不行", "电话不方便留", "不方便留电话", "电话不好留",
)
CONTACT_PREFERENCE_KEYWORDS = (
    "用微信联系吧", "微信吧", "用微信吧", "加微信吧", "微信也行",
)


class TurnUnderstandingService:
    _OCCUPATION_ALIASES = {
        "it": "IT",
        "ui": "UI",
        "hr": "HR",
        "qa": "QA",
        "产品": "产品",
        "运营": "运营",
        "设计": "设计",
        "开发": "开发",
        "程序员": "程序员",
        "销售": "销售",
        "老师": "老师",
        "医生": "医生",
        "公务员": "公务员",
        "美容": "美容",
        "美容师": "美容师",
        "美业": "美业",
        "医美": "医美",
    }
    _OCCUPATION_FALLBACK_CHARS = {"恶", "呃", "额", "嗯", "啊", "哈", "哎"}
    """统一单轮理解：分类、信号、槽位解析。

    只负责识别这轮发生了什么，不负责最终文案，也不负责
    contact/ending 状态机。

    当前该类已经是单轮理解的唯一实现入口：
    - turn type / subtype / secondary signals
    - slot resolve / extraction guards
    - context ack type / payload
    - FAQ / opening / complaint / boundary / closing / risk 判断

    允许依赖底层领域服务，但不应再反向依赖 ChatService 私有 helper，
    也不应在此返回固定回复文案。
    """

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service
        self.collection_concern_detector = CollectionConcernDetector()
        self.slot_governance_layer = ContextualSlotGovernanceLayer(self)

    def analyze(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:
        return self._analyze(turn_input, apply_slot_governance=True)

    def analyze_without_slot_governance(self, turn_input: TurnUnderstandingInput) -> TurnUnderstandingResult:
        return self._analyze(turn_input, apply_slot_governance=False)

    def _analyze(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        apply_slot_governance: bool,
    ) -> TurnUnderstandingResult:
        message = str(turn_input.user_message or "").strip()
        if not message:
            return TurnUnderstandingResult(
                primary_turn_type="invalid_input",
                subtype="empty_input",
                confidence=0.99,
                notes=["empty_message"],
            )

        slot_candidates, resolved_slots, blocked_slots = self._resolve_slots(
            turn_input,
            apply_slot_governance=apply_slot_governance,
        )
        primary_turn_type, subtype, confidence = self._classify_turn_type(
            turn_input,
            resolved_slots=resolved_slots,
        )
        complaint_reason = self._derive_complaint_reason(
            turn_input,
            primary_turn_type=primary_turn_type,
            subtype=subtype,
        )
        resume_profile_collection = self._looks_like_resume_profile_collection(turn_input)
        post_answer_reentry = self._looks_like_post_answer_reentry(turn_input)
        secondary_signals = self._detect_secondary_signals(
            turn_input,
            primary_turn_type=primary_turn_type,
            resolved_slots=resolved_slots,
        )
        answer_first = primary_turn_type in {"faq_concern", "refusal_boundary_complaint", "risk_guard"}
        resume_hint = "profile_mainline" if primary_turn_type in {"faq_concern", "refusal_boundary_complaint"} else None
        context_ack_type = self._derive_context_ack_type(
            turn_input,
            primary_turn_type=primary_turn_type,
            subtype=subtype,
            resolved_slots=resolved_slots,
            secondary_signals=secondary_signals,
        )
        context_ack_payload = self._build_context_ack_payload(
            turn_input,
            context_ack_type=context_ack_type,
        )
        context_ack_occupation = None
        context_ack_location = None
        context_ack_preference = None
        if context_ack_type == "work_busy":
            context_ack_occupation = str(context_ack_payload.get("occupation") or "").strip() or None
        elif context_ack_type == "location_reuse":
            context_ack_location = str(context_ack_payload.get("location") or "").strip() or None
        elif context_ack_type == "preference_reuse":
            context_ack_preference = str(context_ack_payload.get("preference") or "").strip() or None
        context_ack_field_ack = None
        if context_ack_type in {"profile_partial_with_boundary", "opening_profile_ack"}:
            context_ack_field_ack = str(context_ack_payload.get("field_ack") or "").strip() or None
        soft_retry_field = None
        if context_ack_type == "field_soft_refusal_retry":
            soft_retry_field = str(context_ack_payload.get("field") or "").strip() or None
        risk_flags = []
        if primary_turn_type == "risk_guard":
            risk_flags.append(subtype or "risk")

        result = TurnUnderstandingResult(
            primary_turn_type=primary_turn_type,
            subtype=subtype,
            complaint_reason=complaint_reason,
            resume_profile_collection=resume_profile_collection,
            post_answer_reentry=post_answer_reentry,
            secondary_signals=secondary_signals,
            risk_flags=risk_flags,
            slot_candidates=slot_candidates,
            resolved_slots=resolved_slots,
            blocked_slots=blocked_slots,
            answer_first=answer_first,
            resume_hint=resume_hint,
            context_ack_type=context_ack_type,
            context_ack_payload=context_ack_payload,
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
            confidence=confidence,
        )
        logger.info("[turn_understanding] %s", result.to_dict())
        return result

    def _resolve_slots(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        apply_slot_governance: bool = True,
    ) -> tuple[Dict[str, SlotCandidate], Dict[str, str], Dict[str, BlockedSlot]]:
        message = str(turn_input.user_message or "").strip()
        last_response = str(turn_input.last_response or "").strip()
        candidates: Dict[str, SlotCandidate] = {}
        resolved: Dict[str, str] = {}
        blocked: Dict[str, BlockedSlot] = {}

        raw_fields = self._extract_profile_fields(message, last_response=last_response)
        raw_fields.update(self._extract_extra_contextual_fields(message))
        if apply_slot_governance:
            raw_fields, pre_blocked = self.slot_governance_layer.govern_raw_fields(
                turn_input=turn_input,
                raw_fields=raw_fields,
                message=message,
                last_response=last_response,
            )
            blocked.update(pre_blocked)

        asked_field = self._detect_which_field_is_asked(last_response)
        if asked_field == "partner_requirement":
            partner_preference = self._extract_simple_partner_requirement(message)
            if partner_preference:
                raw_fields["partner_requirement"] = partner_preference
                if "age" in raw_fields or "age_label" in raw_fields:
                    raw_fields.pop("age", None)
                    raw_fields.pop("age_label", None)
                    logger.info("[提取保护] 槽位解析命中择偶要求上下文，移除 age/age_label 数字污染")
        elif self._extract_numeric_height_preference(message) and "partner_requirement" in raw_fields:
            if "age" in raw_fields or "age_label" in raw_fields:
                raw_fields.pop("age", None)
                raw_fields.pop("age_label", None)
                logger.info("[提取保护] 槽位解析命中数字身高偏好，移除 age/age_label 数字污染")

        compact_message = re.sub(r"\s+", "", message)
        if "sex" not in raw_fields and re.search(r"(^|[，,、])(?:男生|男的|男)(?=$|[，,、])", compact_message):
            raw_fields["sex"] = "男"
        elif "sex" not in raw_fields and re.search(r"(^|[，,、])(?:女生|女的|女)(?=$|[，,、])", compact_message):
            raw_fields["sex"] = "女"

        if (
            "education" in raw_fields
            and "partner_requirement" not in raw_fields
            and not re.search(r"(另一半|对方|择偶|想找|希望|要求|看重)", message)
        ):
            raw_fields["partner_requirement"] = str(raw_fields["education"]).strip()

        contact_candidate = self._extract_contact_candidate(message)
        if not contact_candidate and bool(getattr(turn_input, "in_contact_flow", False)):
            bare_candidate = self._extract_bare_contact_candidate(message)
            if bare_candidate:
                if bare_candidate["type"] == "wechat" and not getattr(turn_input.user_profile, "wechat_collected", False):
                    contact_candidate = bare_candidate
                elif bare_candidate["type"] == "phone" and not getattr(turn_input.user_profile, "phone_collected", False):
                    contact_candidate = bare_candidate
        if contact_candidate and contact_candidate.get("value"):
            slot_name = "wechat" if contact_candidate.get("type") == "wechat" else "phone"
            raw_fields[slot_name] = str(contact_candidate["value"]).strip()

        profile_phone = str(getattr(turn_input.user_profile, "phone", "") or "").strip()
        pending_contact_field = str(getattr(turn_input.user_profile, "pending_contact_field", "") or "").strip()
        last_contact_request_type = str(getattr(turn_input.user_profile, "last_contact_request_type", "") or "").strip()
        if (
            profile_phone
            and getattr(turn_input.user_profile, "phone_collected", False)
            and not getattr(turn_input.user_profile, "wechat_collected", False)
            and "wechat" not in raw_fields
            and re.search(r"(电话.*加微信|微信.*电话一样|电话同微信|这个号码也是微信|微信就是手机号|号码也是微信|这个号也是微信)", message)
        ):
            raw_fields["wechat"] = profile_phone

        if (
            profile_phone
            and getattr(turn_input.user_profile, "phone_collected", False)
            and not getattr(turn_input.user_profile, "wechat_collected", False)
            and "wechat" not in raw_fields
            and (pending_contact_field == "wechat" or last_contact_request_type == "wechat")
            and re.search(r"(就是电话|就是号码|号码就行|跟电话一样|和电话一样|同一个号|同号|电话就可以加微信)", message)
        ):
            raw_fields["wechat"] = profile_phone

        if "wechat" not in raw_fields and re.search(r"(微信|微信号|加微信)", message):
            embedded_phone = self._extract_bare_contact_candidate(message)
            if embedded_phone and embedded_phone.get("type") == "phone":
                raw_fields["wechat"] = str(embedded_phone["value"]).strip()

        pending_contact_candidate = str(getattr(turn_input.user_profile, "pending_contact_candidate", "") or "").strip()
        pending_contact_hint = str(getattr(turn_input.user_profile, "pending_contact_hint", "") or "").strip()
        if (
            pending_contact_candidate
            and pending_contact_field in {"phone", "wechat"}
            and pending_contact_hint == "soft_region_mismatch_hk"
            and pending_contact_field not in raw_fields
            and (
                self._is_affirmative_confirmation_answer(message)
                or "香港手机号" in message
                or "香港号码" in message
                or "港号" in message
                or "这个是香港" in message
                or "这是香港" in message
                or "常用号码" in message
            )
        ):
            raw_fields[pending_contact_field] = pending_contact_candidate

        for field_name, value in raw_fields.items():
            normalized_value = "" if value is None else str(value).strip()
            if not normalized_value:
                continue
            candidates[field_name] = SlotCandidate(
                value=normalized_value,
                confidence=0.9,
                source="rule",
                source_text=message,
            )

        if "partner_requirement" in candidates and "education" in candidates:
            pref_value = candidates["partner_requirement"].value
            edu_value = candidates["education"].value
            if pref_value == edu_value and not re.search(r"(另一半|对方|择偶|想找|希望|要求|看重)", message):
                blocked["partner_requirement"] = BlockedSlot(
                    value=pref_value,
                    reason="looks_like_education_not_preference",
                    source="rule",
                    source_text=message,
                )
                candidates.pop("partner_requirement", None)

        for field_name, candidate in candidates.items():
            if field_name == "sex" and self._looks_like_preference_only(turn_input.user_message):
                blocked[field_name] = BlockedSlot(
                    value=candidate.value,
                    reason="preference_should_not_overwrite_sex",
                    source=candidate.source,
                    source_text=candidate.source_text,
                )
                continue
            if field_name in {"phone", "wechat"} and self._looks_like_contaminated_contact(turn_input.user_message, candidate.value):
                blocked[field_name] = BlockedSlot(
                    value=candidate.value,
                    reason="contaminated_contact_input",
                    source=candidate.source,
                    source_text=candidate.source_text,
                )
                continue
            resolved[field_name] = candidate.value

        return candidates, resolved, blocked

    @staticmethod
    def _extract_extra_contextual_fields(message: str) -> Dict[str, str]:
        extracted: Dict[str, str] = {}
        if re.search(r"(已经结婚了|我已婚|已婚了?)", message):
            extracted["marital_status"] = "已婚"
        elif re.search(r"(离过婚|已经离婚|我是离异|离异了?)", message):
            extracted["marital_status"] = "离异"
        elif re.search(r"(我是单身|目前单身|现在单身)", message):
            extracted["marital_status"] = "单身"

        # 这里只吃明确年龄表达，避免把“我88年的”误识别成 88 岁。
        age_match = re.search(r"我(?:今年|现在)?\s*(\d{2})(?!后|年)\s*岁\b", message)
        if age_match:
            extracted["age"] = age_match.group(1)

        for city in ("深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港"):
            if re.search(rf"(我在|人在|住在|目前在|现在在)?{city}", message):
                extracted.setdefault("location", city)
                break
        return extracted

    def _classify_turn_type(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        resolved_slots: Dict[str, str],
    ) -> tuple[TurnType, str | None, float]:
        message = str(turn_input.user_message or "").strip()
        profile = turn_input.user_profile
        message_count = int(turn_input.message_count or 0)
        opening_signals = self._extract_opening_signals(turn_input, resolved_slots)

        if self._is_risk_guard(message):
            return "risk_guard", "risk_pattern", 0.99

        withdraw_intent = self._classify_withdraw_intent(message)
        if withdraw_intent:
            return "closing_exit", withdraw_intent, 0.97

        if self._looks_like_correction(message):
            return "correction", "active_revise", 0.95

        contact_subtype = self._contact_subtype(message, resolved_slots)
        if contact_subtype in {"contact_preference_switch", "contact_provided"}:
            return "contact_answer", contact_subtype, 0.93

        faq_intent = self._detect_faq_intent(message)
        if faq_intent:
            return "faq_concern", faq_intent, 0.94

        contextual_faq_intent = self._detect_contextual_profile_collection_concern(turn_input)
        if contextual_faq_intent:
            return "faq_concern", contextual_faq_intent, 0.9

        soft_refusal_field = self._detect_soft_refusal_current_field(turn_input, resolved_slots)
        if soft_refusal_field:
            return "invalid_input", "soft_refusal_current_field", 0.88

        if self._is_complaint_message(message):
            return "refusal_boundary_complaint", "complaint", 0.93
        if self._is_boundary_pause(message, profile):
            subtype = "contact_refusal" if turn_input.in_contact_flow else "boundary_defensive"
            return "refusal_boundary_complaint", subtype, 0.92
        if self._looks_like_refusal(message):
            return "refusal_boundary_complaint", "refusal", 0.89

        if any(field in resolved_slots for field in {"phone", "wechat"}):
            return "contact_answer", contact_subtype, 0.93

        if turn_input.in_contact_flow and not resolved_slots:
            return "contact_answer", contact_subtype, 0.93

        if self._looks_like_confirmation(message, turn_input):
            return "confirmation", "weak_confirmation", 0.85

        if opening_signals.get("matchmaking_intent"):
            confidence = 0.92 if opening_signals.get("greeting") else 0.9
            return "opening", "matchmaking_intent", confidence

        if opening_signals.get("service_confirmation"):
            return "opening", "service_confirmation_opening", 0.91

        if opening_signals.get("low_pressure"):
            return "opening", "low_pressure_opening", 0.89

        if self._looks_like_mid_service_confirmation(turn_input, resolved_slots):
            return "faq_concern", "service_confirmation_mid", 0.9

        if opening_signals.get("clarify"):
            return "opening", "opening_clarify", 0.9

        if opening_signals.get("greeting"):
            return "opening", "greeting", 0.88

        if resolved_slots:
            return "profile_answer", self._profile_subtype(message, message_count, resolved_slots), 0.91

        if self._looks_like_invalid_input(message):
            return "invalid_input", "garbled_or_typo", 0.84

        if message_count <= 1:
            return "opening", self._opening_subtype(message), 0.82

        return "invalid_input", "ambiguous_short_answer", 0.51

    def _detect_secondary_signals(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        primary_turn_type: TurnType,
        resolved_slots: Dict[str, str],
    ) -> list[str]:
        message = str(turn_input.user_message or "").strip()
        signals: list[str] = []
        opening_signals = self._extract_opening_signals(turn_input, resolved_slots)
        if primary_turn_type == "profile_answer":
            if turn_input.message_count == 0 or self._is_explicit_matchmaking_intent_message(message):
                signals.append("proactive_profile_provide")
            if len(resolved_slots) >= 2:
                signals.append("multi_slot_compound")
            if opening_signals.get("greeting"):
                signals.append("opening_greeting")
        if primary_turn_type == "contact_answer" and any(field in resolved_slots for field in {"phone", "wechat"}):
            signals.append("proactive_contact_provide")
        if primary_turn_type == "opening":
            if opening_signals.get("greeting") and "opening_greeting" not in signals:
                signals.append("opening_greeting")
            if opening_signals.get("matchmaking_intent"):
                signals.append("opening_matchmaking_intent")
            if opening_signals.get("service_confirmation"):
                signals.append("service_confirmation_like")
        if primary_turn_type == "confirmation" and len(message) <= 2:
            signals.append("weak_confirmation")
        if primary_turn_type == "invalid_input" and len(message) <= 4:
            signals.append("ambiguous_short_answer")
        if primary_turn_type == "invalid_input" and (turn_input.last_response or "") and (turn_input.user_message or ""):
            soft_refusal_field = self._detect_soft_refusal_current_field(turn_input, resolved_slots)
            if soft_refusal_field:
                signals.append("soft_refusal_current_field")
        if turn_input.conversation_context.get("recent_responses") and primary_turn_type in {"faq_concern", "refusal_boundary_complaint"}:
            signals.append("needs_resume_mainline")
        return signals

    def _derive_context_ack_type(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        primary_turn_type: TurnType,
        subtype: str | None,
        resolved_slots: Dict[str, str],
        secondary_signals: list[str],
    ) -> str | None:
        message = str(turn_input.user_message or "").strip()
        profile = turn_input.user_profile
        message_count = int(turn_input.message_count or 0)

        if self._matches_any_pattern(message, TOPIC_SHIFT_HINT_PATTERNS):
            return "topic_shift"

        if primary_turn_type == "refusal_boundary_complaint":
            if resolved_slots:
                return "profile_partial_with_boundary"
            if subtype in {"boundary_defensive", "refusal", "contact_refusal"}:
                return subtype
            return None

        if primary_turn_type == "invalid_input" and subtype == "soft_refusal_current_field":
            return "field_soft_refusal_retry"

        if getattr(profile, "occupation", None) and self._matches_any_pattern(message, WORK_BUSY_HINT_PATTERNS):
            return "work_busy"
        if getattr(profile, "location", None) and self._matches_any_pattern(message, LOCATION_REUSE_HINT_PATTERNS):
            return "location_reuse"
        if getattr(profile, "partner_requirement", None) and self._matches_any_pattern(message, PREFERENCE_REUSE_HINT_PATTERNS):
            return "preference_reuse"

        if message_count >= 1 and getattr(profile, "location", None) and "那边" in message:
            return "location_reuse"
        if message_count >= 1 and getattr(profile, "partner_requirement", None) and any(token in message for token in ("推荐", "合适", "这类", "这种")):
            return "preference_reuse"

        if primary_turn_type == "faq_concern":
            return "faq_then_resume"
        if primary_turn_type == "profile_answer" and resolved_slots:
            return "profile_ack"
        if message_count <= 1:
            lightweight_preference = self._extract_simple_partner_requirement(message)
            if resolved_slots or lightweight_preference:
                return "opening_profile_ack"
        if "pending_confirmation_reply" in secondary_signals:
            return "confirmation_ack"
        return None

    def _detect_soft_refusal_current_field(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> str | None:
        message = str(turn_input.user_message or "").strip()
        if not message or resolved_slots:
            return None
        if not self._looks_like_refusal(message):
            return None
        if self._detect_faq_intent(message):
            return None
        previous_field = self._resolve_previous_asked_field(turn_input)
        if previous_field not in {
            "sex",
            "age",
            "education",
            "occupation",
            "location",
            "marital_status",
            "monthly_income",
            "partner_requirement",
        }:
            return None
        if getattr(turn_input, "in_contact_flow", False):
            return None
        return previous_field

    def _resolve_previous_asked_field(self, turn_input: TurnUnderstandingInput) -> str:
        previous_field = str(getattr(turn_input.user_profile, "last_asked_field", "") or "").strip()
        if previous_field:
            return previous_field

        expected_field_getter = getattr(turn_input.user_profile, "get_expected_field_for_short_answer", None)
        if callable(expected_field_getter):
            try:
                previous_field = str(expected_field_getter(int(turn_input.message_count or 0)) or "").strip()
            except Exception:  # noqa: BLE001
                previous_field = ""
            if previous_field:
                return previous_field

        response_candidates = [str(turn_input.last_response or "").strip()]
        recent_responses = turn_input.conversation_context.get("recent_responses") or []
        response_candidates.extend(
            str(candidate or "").strip()
            for candidate in reversed(recent_responses)
            if str(candidate or "").strip()
        )
        for candidate in response_candidates:
            previous_field = self._detect_which_field_is_asked(candidate)
            if previous_field:
                return previous_field
        return ""

    def _derive_complaint_reason(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        primary_turn_type: TurnType,
        subtype: str | None,
    ) -> str | None:
        if primary_turn_type != "refusal_boundary_complaint" or subtype != "complaint":
            return None
        message = str(turn_input.user_message or "").strip()
        if not message:
            return None
        if self._matches_any_pattern(message, REPEAT_ASK_COMPLAINT_PATTERNS):
            return "repeat_ask"
        if self._matches_any_pattern(message, COMPLAINT_PATTERNS):
            return "over_questioning"
        if self._has_faq_priority_signal(message):
            return None
        return None

    def _detect_faq_intent(self, message: str) -> str | None:
        """FAQ/顾虑识别统一收口在 understanding，直接复用底层服务能力。"""
        text = str(message or "").strip()
        if not text:
            return None
        user_question_service = getattr(self.chat_service, "user_question_service", None)
        if user_question_service is not None:
            intent = user_question_service.detect_quick_faq_intent(text)  # noqa: SLF001
            if intent:
                return intent
        expectation_service = getattr(self.chat_service, "expectation_service", None)
        if expectation_service is not None and expectation_service.is_matching_timeline_question(text):  # noqa: SLF001
            return "timeline"
        return None

    def _detect_contextual_profile_collection_concern(self, turn_input: TurnUnderstandingInput) -> str | None:
        """统一交给独立 detector，用上下文裁决资料收集顾虑。"""
        message = str(turn_input.user_message or "").strip()
        if not message:
            return None
        if self._detect_faq_intent(message):
            return None
        match = self.collection_concern_detector.detect(
            message=message,
            last_asked_field=self._resolve_previous_asked_field(turn_input),
            last_response=str(turn_input.last_response or ""),
            recent_responses=tuple(turn_input.conversation_context.get("recent_responses") or ()),
            in_contact_flow=bool(getattr(turn_input, "in_contact_flow", False)),
        )
        return match.intent if match else None

    def _has_faq_priority_signal(self, message: str) -> bool:
        return bool(self._detect_faq_intent(message))

    def _is_boundary_pause(self, message: str, profile) -> bool:
        """边界/顾虑输入检测，仅用于理解层打标。"""
        text = str(message or "").strip()
        if not text:
            return False
        if self._has_faq_priority_signal(text):
            return False
        if profile is not None and self._prefers_wechat_over_phone(text, profile):
            return False
        if profile is not None:
            contact_refusal_markers = [
                "不留电话", "不想留电话", "电话不方便",
                "不留微信", "不想留微信", "微信不方便",
            ]
            generic_contact_refusal_markers = [
                "不方便留", "不方便说", "先不留", "不想留", "不留呀", "不方便呀", "不方便呢",
            ]
            in_contact_stage = any(
                [
                    bool(getattr(profile, "phone_ask_count", 0) > 0),
                    bool(getattr(profile, "wechat_ask_count", 0) > 0),
                    bool(getattr(profile, "rejected_phone", False)),
                    bool(getattr(profile, "rejected_wechat", False)),
                ]
            )
            if in_contact_stage and (
                any(marker in text for marker in contact_refusal_markers)
                or any(marker in text for marker in generic_contact_refusal_markers)
            ):
                return False
        return self._matches_any_pattern(text, BOUNDARY_PAUSE_PATTERNS)

    def _prefers_wechat_over_phone(self, message: str, profile) -> bool:
        if not message or getattr(profile, "wechat_collected", False):
            return False
        wants_wechat = any(keyword in message for keyword in WECHAT_INTENT_KEYWORDS)
        explicit_contact_preference = any(keyword in message for keyword in CONTACT_PREFERENCE_KEYWORDS)
        refuses_phone = any(keyword in message for keyword in PHONE_REFUSAL_PREFERENCE_KEYWORDS)
        return wants_wechat and (refuses_phone or explicit_contact_preference)

    def _is_risk_guard(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        return any(
            [
                self._matches_any_pattern(text, SELF_HARM_GUARD_PATTERNS),
                self._matches_any_pattern(text, MEDICAL_GUARD_PATTERNS),
                self._matches_any_pattern(text, LEGAL_GUARD_PATTERNS),
                self._matches_any_pattern(text, OVERREACH_GUARD_PATTERNS),
                self._matches_any_pattern(text, AI_IDENTITY_GUARD_PATTERNS),
                self._matches_any_pattern(text, ABUSE_GUARD_PATTERNS),
            ]
        )

    def _classify_withdraw_intent(self, message: str) -> str | None:
        if not message or self._has_faq_priority_signal(message):
            return None
        if self._matches_any_pattern(message, WITHDRAW_STRONG_PATTERNS):
            return "strong"
        if self._matches_any_pattern(message, WITHDRAW_SOFT_PATTERNS):
            return "soft"
        return None

    def _is_complaint_message(self, message: str) -> bool:
        if not message:
            return False
        if self._matches_any_pattern(message, REPEAT_ASK_COMPLAINT_PATTERNS):
            return True
        if self._matches_any_pattern(message, COMPLAINT_PATTERNS):
            return True
        if self._has_faq_priority_signal(message):
            return False
        return False

    @staticmethod
    def _matches_any_pattern(message: str, patterns) -> bool:
        content = str(message or "")
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)

    def _extract_simple_partner_requirement(self, message: str) -> str | None:
        compact_message = re.sub(r"\s+", "", str(message or "").strip())
        if not compact_message:
            return None
        if any(token in compact_message for token in ("没有要求", "没要求", "没有别的", "没有其他", "没别的", "都可以", "都行", "无所谓")):
            return "无特别要求"
        if any(token in compact_message for token in ("随缘", "看感觉", "看眼缘", "看缘分", "顺其自然")):
            return "看感觉/随缘"
        numeric_height_preference = self._extract_numeric_height_preference(compact_message)
        if numeric_height_preference:
            return numeric_height_preference
        compact_message = re.sub(
            r"(^|[，,])我(?=(温柔|性格好|聊得来|合适|人好|高挑|高一点|同城优先|成熟稳重|三观合拍))",
            r"\1",
            compact_message,
        )
        patterns = [
            r"(温柔(?:一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?)",
            r"(温柔就行(?:了)?(?:吧|呀|呢)?)",
            r"(性格好就行(?:了)?(?:吧|呀|呢)?)",
            r"(聊得来就行(?:了)?(?:吧|呀|呢)?)",
            r"(合适就行(?:了)?(?:吧|呀|呢)?)",
            r"(人好就行(?:了)?(?:吧|呀|呢)?)",
            r"(高挑)",
            r"(高一点)",
            r"(同城优先)",
            r"(不要超过\d{2}岁)",
            r"(不超过\d{2}岁)",
            r"(成熟稳重)",
            r"(三观合拍)",
            r"(喜欢[^\s，,。]{0,10}(?:男朋友|女朋友|男生|女生|男孩子|女孩子|男的|女的|男|女))",
            r"(想找[^\s，,。]{0,10}(?:男朋友|女朋友|男生|女生|男孩子|女孩子|男的|女的|男|女))",
            r"(找[^\s，,。]{0,10}(?:男朋友|女朋友|男生|女生|男孩子|女孩子|男的|女的|男|女))",
        ]
        values = []
        for pattern in patterns:
            match = re.search(pattern, compact_message)
            if match:
                values.append(match.group(1).strip())
        if not values:
            return None
        normalized = []
        for value in dict.fromkeys(values):
            value = re.sub(r"(温柔)(一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?$", r"\1", value)
            value = re.sub(r"^(温柔)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(性格好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(聊得来)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(合适)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(人好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = self._normalize_partner_requirement_value(value)
            normalized.append(value)
        normalized = list(dict.fromkeys(normalized))
        if len(normalized) == 1 and normalized[0] in {"男生", "女生"}:
            return None
        return "，".join(normalized) if normalized else None

    @staticmethod
    def _extract_numeric_height_preference(message: str) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        compact = re.sub(r"\s+", "", text)
        short_meter_match = re.fullmatch(r"1米([5-9])", compact)
        if short_meter_match:
            return f"身高1米{short_meter_match.group(1)}"
        meter_match = re.fullmatch(r"1米([5-9]\d)", compact)
        if meter_match:
            return f"身高{meter_match.group(1)}cm"
        bare_match = re.fullmatch(r"(1[5-9]\d)(?:cm|CM)?(?:左右|以上|以下|以内|吧)?", compact)
        if bare_match:
            suffix = compact[bare_match.end(1):]
            normalized_suffix = suffix.replace("CM", "cm").replace("cm", "")
            normalized_suffix = re.sub(r"^吧$", "", normalized_suffix)
            return f"身高{bare_match.group(1)}cm{normalized_suffix}"
        return None

    @staticmethod
    def _normalize_partner_requirement_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return text
        if re.search(r"(男朋友|男生|男孩子|男的|找个男|想找男|喜欢男)", text):
            return "男生"
        if re.search(r"(女朋友|女生|女孩子|女的|找个女|想找女|喜欢女)", text):
            return "女生"
        return text

    @staticmethod
    def _extract_partner_gender_preference(message: str) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        if re.search(r"(?:我是|本人|我)\s*(?:男生|女生|男的|女的|男|女)", text):
            return None
        if re.search(
            r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找).{0,8}(?:男朋友|男生|男孩子|男的|男性|男)",
            text,
        ) or re.search(r"(?:男朋友)", text):
            return "男"
        if re.search(
            r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找).{0,8}(?:女朋友|女生|女孩子|女的|女性|女)",
            text,
        ) or re.search(r"(?:女朋友)", text):
            return "女"
        return None

    def _extract_profile_fields(self, message: str, *, last_response: str) -> Dict[str, str]:
        raw_fields = self._extract_deterministic_profile_fields(message)
        return self._apply_extraction_guards(raw_fields, message, last_response=last_response)

    def _extract_contact_candidate(self, message: str):
        """从用户原始消息中提取疑似联系方式，并携带字段提示。"""
        text = str(message or "")
        if not text:
            return None
        marker_pattern = re.compile(
            r'(?P<marker>电话|手机|手机号|号码|微信|vx|wx|weixin)[^\da-zA-Z_/-]*(?P<value>[a-zA-Z][a-zA-Z0-9_-]{2,19}|\+?86[\d\s-]{11,17}|[\d\s-]{8,17})',
            re.IGNORECASE,
        )
        matched = marker_pattern.search(text)
        if not matched:
            return None
        marker = matched.group("marker").lower()
        hinted_type = "wechat" if marker in {"微信", "vx", "wx", "weixin"} else "phone"
        raw_value = matched.group("value").strip()
        marker_end = matched.end("marker")
        value_start = matched.start("value")
        if hinted_type == "wechat" and marker in {"vx", "wx", "weixin"} and value_start == marker_end:
            # `wx23234242` 这类账号本身包含前缀，不能把前缀吞掉。
            raw_value = f"{marker}{raw_value}"
        contaminated = False
        if hinted_type == "phone":
            raw_value = re.sub(r"[\s-]", "", raw_value)
        else:
            value_end = matched.end("value")
            if value_end < len(text):
                trailing_char = text[value_end]
                if re.match(r"[A-Za-z0-9_\-\u4e00-\u9fff]", trailing_char):
                    contaminated = True
        return {"value": raw_value, "type": hinted_type, "contaminated": contaminated}

    @staticmethod
    def _extract_bare_contact_candidate(message: str):
        """识别用户直接裸发的联系方式，不依赖微信/电话前缀。"""
        text = str(message or "").strip()
        if not text:
            return None
        if re.fullmatch(r"\+?86?[\d\s-]{8,17}", text):
            digits = re.sub(r"\D", "", text)
            if digits.startswith("86") and len(digits) == 13 and digits[2] == "1":
                digits = digits[2:]
            if re.match(r"^1[3-9]\d{9}$", digits) or re.match(r"^[5-9]\d{7}$", digits):
                return {"value": digits, "type": "phone", "contaminated": False}
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{5,19}", text):
            return {"value": text, "type": "wechat", "contaminated": False}
        return None

    def _extract_deterministic_profile_fields(self, user_message: str) -> Dict[str, str]:
        message = str(user_message or "").strip()
        if not message:
            return {}

        extracted = self._extract_basic_fields_from_message(message)
        extracted = self._normalize_bucket_age_fields(extracted)

        sex_patterns = {
            "男": r"^\s*(男生|男的|男)\s*(呀|呢|哈|哦|啊)?\s*$",
            "女": r"^\s*(女生|女的|女)\s*(呀|呢|哈|哦|啊)?\s*$",
        }
        for value, pattern in sex_patterns.items():
            if re.search(pattern, message):
                extracted["sex"] = value
                break

        current_year = datetime.now().year
        if re.search(r"^\s*90后\s*$", message):
            extracted["age"] = str(current_year - 1990)
            extracted["age_label"] = "90后"
        elif re.search(r"^\s*95后\s*$", message):
            extracted["age"] = str(current_year - 1995)
            extracted["age_label"] = "95后"
        elif re.search(r"^\s*85后\s*$", message):
            extracted["age"] = str(current_year - 1985)
            extracted["age_label"] = "85后"

        compact_message = re.sub(r"[，,、。！？!?~～\s]+", "", message)
        location_text = self._extract_location_like_text(message, compact_message=compact_message)
        if location_text:
            extracted["location"] = location_text

        for edu in ["博士", "硕士", "研究生", "本科", "大专", "中专", "高中"]:
            if message == edu:
                extracted["education"] = edu
                break

        for marital in ["单身", "未婚", "离异", "已婚"]:
            if message == marital:
                extracted["marital_status"] = marital
                break

        occupation_match = re.search(
            r"(?:做|做的是|我是)\s*([A-Za-z]{1,12}|[\u4e00-\u9fa5]{2,8})\s*(?:的|呢|呀|吧|哈|哦|啊)?(?=$|[，,、。！？!?])",
            message,
        )
        if occupation_match:
            candidate = self._normalize_occupation_candidate(occupation_match.group(1))
            if candidate and candidate not in {"男", "女", "单身", "未婚", "离异", "已婚"}:
                extracted["occupation"] = candidate

        if not extracted.get("occupation"):
            normalized = self._normalize_occupation_candidate(message)
            if normalized in self._OCCUPATION_ALIASES.values():
                extracted["occupation"] = normalized

        if not extracted.get("partner_requirement"):
            pref = self._extract_simple_partner_requirement(message)
            if pref:
                extracted["partner_requirement"] = pref
        if not extracted.get("partner_gender_preference"):
            partner_gender = self._extract_partner_gender_preference(message)
            if partner_gender:
                extracted["partner_gender_preference"] = partner_gender
        if not extracted.get("monthly_income"):
            income = self._extract_simple_monthly_income(message)
            if income:
                extracted["monthly_income"] = income

        return extracted

    @classmethod
    def _normalize_occupation_candidate(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"[，,、。！？!?~～\s]+", "", text)
        text = re.sub(r"(吧|呀|呢|哈|哦|啊)+$", "", text)
        text = re.sub(r"^(做|做的|做的是|我是|从事)\s*", "", text)
        normalized = text.lower()
        if normalized in cls._OCCUPATION_ALIASES:
            return cls._OCCUPATION_ALIASES[normalized]
        if text and text[0] in cls._OCCUPATION_FALLBACK_CHARS and len(text) >= 2:
            trimmed = text[1:]
            trimmed_normalized = trimmed.lower()
            if trimmed_normalized in cls._OCCUPATION_ALIASES:
                return cls._OCCUPATION_ALIASES[trimmed_normalized]
            for stem in ("美容师", "美业", "医美", "美容", "程序员", "销售", "老师", "医生", "公务员", "产品", "运营", "设计", "开发"):
                if stem in trimmed:
                    residue = trimmed.replace(stem, "")
                    if not residue or set(residue) <= cls._OCCUPATION_FALLBACK_CHARS:
                        return stem
        return cls._OCCUPATION_ALIASES.get(normalized, text)

    @staticmethod
    def _normalize_bucket_age_fields(extracted: Dict[str, str]) -> Dict[str, str]:
        normalized = dict(extracted or {})
        age_label = str(normalized.get("age_label") or "").strip()
        if not age_label:
            return normalized

        label_match = re.search(r"(\d{2})后", age_label)
        if not label_match:
            return normalized

        year_suffix = int(label_match.group(1))
        current_year = datetime.now().year
        birth_year = 2000 + year_suffix if year_suffix <= current_year % 100 else 1900 + year_suffix
        normalized["age"] = str(current_year - birth_year)
        return normalized

    def _extract_basic_fields_from_message(self, user_message: str) -> Dict[str, str]:
        if not user_message:
            return {}

        extracted: Dict[str, str] = {}
        compact_message = re.sub(r"[，,、。！？!?~～\s]+", "", user_message)
        contact_like_message = bool(
            self._extract_contact_candidate(user_message)
            or self._extract_bare_contact_candidate(user_message)
        )

        if "我是女生" in user_message or "本人女" in user_message:
            extracted["sex"] = "女"
        elif "我是男生" in user_message or "本人男" in user_message:
            extracted["sex"] = "男"
        elif re.search(r"(上面|前面|之前).{0,8}(说过|说了|提过).{0,6}(?:是)?(男生|男的|男)", user_message):
            extracted["sex"] = "男"
        elif re.search(r"(上面|前面|之前).{0,8}(说过|说了|提过).{0,6}(?:是)?(女生|女的|女)", user_message):
            extracted["sex"] = "女"
        else:
            sex_match = re.search(r"(?:^|[，,、\s])(?:(?:我是)?(男生|男的|女生|女的))(?:呢|呀|哈|哦|啊)?(?=$|[，,、。！？!?])", user_message)
            if sex_match:
                extracted["sex"] = "男" if "男" in sex_match.group(1) else "女"

        if not contact_like_message:
            age_match = re.search(r"(\d{2})后", user_message)
            if age_match:
                suffix = int(age_match.group(1))
                birth_year = 2000 + suffix if suffix <= datetime.now().year % 100 else 1900 + suffix
                extracted["age"] = str(datetime.now().year - birth_year)
                extracted["age_label"] = f"{age_match.group(1)}后"
            else:
                birth_year_full = re.search(r"(19\d{2}|20\d{2})年(?:出生)?", user_message)
                birth_year_short = re.search(r"(?<!\d)(\d{2})年(?:的)?(?:出生)?", user_message)
                if birth_year_full:
                    birth_year = int(birth_year_full.group(1))
                    extracted["age"] = str(datetime.now().year - birth_year)
                    extracted["age_label"] = f"{birth_year}年"
                elif birth_year_short:
                    suffix = int(birth_year_short.group(1))
                    birth_year = 2000 + suffix if suffix <= datetime.now().year % 100 else 1900 + suffix
                    extracted["age"] = str(datetime.now().year - birth_year)
                    extracted["age_label"] = f"{birth_year_short.group(1)}年"
                else:
                    explicit_age = re.search(r"(?:我今年|今年|我现在|现在)?\s*(\d{2})岁?", user_message)
                    if explicit_age:
                        extracted["age"] = explicit_age.group(1)

        preference_context = bool(re.search(r"(喜欢|想找|找).*(?:在|来自|住在|深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|台湾|澳门)", user_message))
        if not preference_context:
            location_text = self._extract_location_like_text(user_message, compact_message=compact_message)
            if location_text:
                extracted["location"] = location_text

        for edu in ["博士", "硕士", "研究生", "本科", "大专", "中专", "高中"]:
            if edu in user_message:
                extracted["education"] = edu
                break

        for marital in ["单身", "离异", "未婚", "已婚"]:
            if marital in user_message:
                extracted["marital_status"] = marital
                break

        segments = re.split(r"[，,、\s]+", user_message)
        education_tokens = {"博士", "硕士", "研究生", "本科", "大专", "中专", "高中"}
        marital_tokens = {"单身", "离异", "未婚", "已婚"}
        ignored_tokens = {"我是女生", "我是男生", "女生", "男生"}
        for index, segment in enumerate(segments):
            token = segment.strip()
            if not token:
                continue
            if token in education_tokens and index + 1 < len(segments):
                candidate = segments[index + 1].strip()
                if (
                    candidate
                    and candidate not in marital_tokens
                    and candidate not in ignored_tokens
                    and not candidate.startswith("想找")
                    and not self._looks_like_income_token(candidate)
                ):
                    extracted["occupation"] = candidate
                    break

        return extracted

    @staticmethod
    def _looks_like_income_token(value: str) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return False
        return bool(
            re.fullmatch(r"(?:税前|税后)?\d+(?:\.\d+)?(?:k|w|万|千|元)?(?:左右|上下|出头|\+)?", text)
            or re.fullmatch(r"(?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千|元)(?:左右|上下|出头)?", text)
        )

    @staticmethod
    def _extract_location_like_text(message: str, *, compact_message: str | None = None) -> str | None:
        content = str(message or "").strip()
        if not content:
            return None
        compact = compact_message if compact_message is not None else re.sub(r"[，,、。！？!?~～\s]+", "", content)
        if not compact:
            return None
        if re.search(r"(喜欢|想找|找对象|找另一半|另一半|对象).{0,8}(?:在|来自|住在)", content):
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
        common_cities = (
            "深圳",
            "广州",
            "杭州",
            "上海",
            "北京",
            "成都",
            "武汉",
            "苏州",
            "南京",
            "天津",
            "重庆",
            "西安",
            "长沙",
            "郑州",
            "青岛",
            "厦门",
            "宁波",
            "无锡",
            "东莞",
            "佛山",
        )
        city_match = re.fullmatch(
            r"(?:我)?(?P<loc>" + "|".join(common_cities) + r")(?:的|人|呢|呀|哦|哈|啊|啦)?",
            compact,
        )
        if city_match:
            return str(city_match.group("loc") or "").strip()
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

    @staticmethod
    def _extract_confirmed_sex_candidate_from_context(text: str) -> str | None:
        content = str(text or "").strip()
        if not content:
            return None
        if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*男(?:生|的|孩子)?", content):
            return "男"
        if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*女(?:生|的|孩子)?", content):
            return "女"
        return None

    @staticmethod
    def _is_affirmative_confirmation_answer(text: str) -> bool:
        return bool(
            re.search(
                r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
                r"(?:[呀呢啊哦哈啦嘛]*)?"
                r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
                str(text or ""),
            )
        )

    @staticmethod
    def _is_birth_year_question(last_response: str) -> bool:
        text = str(last_response or "").strip()
        if not text:
            return False
        return bool(
            re.search(
                r"(哪一年出生|几几年(?:的)?|具体是\d{2}几年的|具体是哪一年的|[89]\d几年出生|九几年出生|98年出生)",
                text,
            )
        )

    @staticmethod
    def _extract_birth_year_from_context_answer(text: str) -> tuple[str, str] | None:
        content = str(text or "").strip()
        if not content:
            return None
        match = re.search(r"^\s*(?P<year>(?:19\d{2}|20\d{2}|\d{2}))(?:年)?(?:的)?(?:[呀呢哈哦啊啦]*)?(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$", content)
        if not match:
            return None
        raw_year = str(match.group("year") or "").strip()
        current_year = datetime.now().year
        if len(raw_year) == 2:
            suffix = int(raw_year)
            birth_year = 2000 + suffix if suffix <= current_year % 100 else 1900 + suffix
            return str(current_year - birth_year), f"{raw_year}年"
        birth_year = int(raw_year)
        return str(current_year - birth_year), f"{birth_year}年"

    def _apply_extraction_guards(
        self,
        extracted_data: Dict[str, str],
        user_message: str,
        *,
        last_response: str = "",
    ) -> Dict[str, str]:
        guarded = dict(extracted_data or {})
        message = str(user_message or "").strip()
        last_ai = str(last_response or "")
        asked_field = self._detect_which_field_is_asked(last_ai)

        if last_ai and self._looks_like_refusal(message):
            refused_fields = self._detect_asked_fields_from_context(last_ai)
            cleared_fields: list[str] = []
            for field in refused_fields:
                if self._message_explicitly_answers_field(field, message):
                    continue
                if field == "age":
                    if "age" in guarded:
                        guarded.pop("age", None)
                        cleared_fields.append("age")
                    if "age_label" in guarded:
                        guarded.pop("age_label", None)
                        if "age_label" not in cleared_fields:
                            cleared_fields.append("age_label")
                    continue
                if field in guarded:
                    guarded.pop(field, None)
                    cleared_fields.append(field)
            if cleared_fields:
                logger.info("[提取保护] 拒绝语命中，清除上一轮被问字段的污染提取: %s", ",".join(cleared_fields))

        confirmation_context_sex = self._extract_confirmed_sex_candidate_from_context(last_ai)
        sex_question_context = bool(
            re.search(r"(你是|是)(男生|女生|男的|女的|男|女)", last_ai)
            or "性别" in last_ai
            or confirmation_context_sex
        )
        short_sex_answer = re.search(
            r"^\s*(?:你们)?\s*(男生|女生|男的|女的|男|女)"
            r"(?:\s*[，,、 ]\s*(?:是的|对|嗯|好的|好))?"
            r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
            message,
        )
        trailing_punct_sex_answer = re.search(
            r"^\s*(?:你们)?\s*(男生|女生|男的|女的|男|女)\s*[，,、 ]+\s*$",
            message,
        )
        affirmative_prefixed_sex_answer = re.search(
            r"^\s*(?:是的|对|对的|嗯|嗯嗯|好的|好|没错)"
            r"(?:[呀呢啊哦哈啦嘛]*)?\s*(男生|女生|男的|女的|男|女)"
            r"(?:\s*[，,、 ]\s*(?:\d{2}年|\d{2}后|\d{2}岁|19\d{2}年|20\d{2}年).*)?$",
            message,
        )
        embedded_context_sex_answer = re.search(
            r"(?:^|[，,、 ]|是|就是)\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?(?:$|[，,。！？!? ])",
            message,
        )
        affirmative_confirmation = self._is_affirmative_confirmation_answer(message)
        marital_question_context = bool(
            re.search(r"(单身状态|现在是单身吗|现在单身吗|感情状态.*单身|婚况.*单身)", last_ai)
        )
        if sex_question_context and short_sex_answer:
            raw = short_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            partner_value = str(guarded.get("partner_requirement") or "")
            if partner_value and any(token in partner_value for token in ["男", "女"]):
                guarded.pop("partner_requirement", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_requirement 性别污染值")
            if guarded.get("partner_gender_preference"):
                guarded.pop("partner_gender_preference", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_gender_preference 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 short answer 强制写入 sex")
        elif sex_question_context and trailing_punct_sex_answer:
            raw = trailing_punct_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            if guarded.get("partner_gender_preference"):
                guarded.pop("partner_gender_preference", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_gender_preference 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 trailing short answer 强制写入 sex")
        elif sex_question_context and affirmative_prefixed_sex_answer:
            raw = affirmative_prefixed_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            if guarded.get("partner_gender_preference"):
                guarded.pop("partner_gender_preference", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_gender_preference 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 affirmative+sex 复合短答强制写入 sex")
        elif sex_question_context and embedded_context_sex_answer:
            raw = embedded_context_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            if guarded.get("partner_gender_preference"):
                guarded.pop("partner_gender_preference", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_gender_preference 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 embedded answer 强制写入 sex")
        elif confirmation_context_sex and affirmative_confirmation:
            guarded["sex"] = confirmation_context_sex
            if guarded.get("partner_gender_preference"):
                guarded.pop("partner_gender_preference", None)
                logger.info("[提取保护] 性别确认上下文命中，移除本轮 partner_gender_preference 性别污染值")
            logger.info("[提取保护] 性别确认上下文命中，按 affirmative answer 强制写入 sex")
        elif marital_question_context and affirmative_confirmation:
            guarded["marital_status"] = "单身"
            logger.info("[提取保护] 婚况问答上下文命中，按 affirmative answer 强制写入 marital_status")

        birth_year_question_context = self._is_birth_year_question(last_ai)
        if birth_year_question_context:
            if self._looks_like_refusal(message):
                guarded.pop("age", None)
                guarded.pop("age_label", None)
                logger.info("[提取保护] 出生年问答上下文命中，用户拒绝补充具体年份，本轮不提取 age/age_label")
            else:
                birth_year_answer = self._extract_birth_year_from_context_answer(message)
                if birth_year_answer:
                    age_value, age_label = birth_year_answer
                    guarded["age"] = age_value
                    guarded["age_label"] = age_label
                    logger.info("[提取保护] 出生年问答上下文命中，按 short answer 强制写入 age/age_label")

        numeric_height_preference = self._extract_numeric_height_preference(message)
        if numeric_height_preference and ("age" in guarded or "age_label" in guarded):
            guarded["partner_requirement"] = str(guarded.get("partner_requirement") or numeric_height_preference).strip()
            guarded.pop("age", None)
            guarded.pop("age_label", None)
            logger.info("[提取保护] 数字身高偏好命中，移除 age/age_label 数字污染")

        if asked_field == "partner_requirement":
            partner_preference = self._extract_simple_partner_requirement(message)
            if partner_preference:
                guarded["partner_requirement"] = partner_preference
            if partner_preference and ("age" in guarded or "age_label" in guarded):
                guarded.pop("age", None)
                guarded.pop("age_label", None)
                logger.info("[提取保护] 择偶要求问答上下文命中，移除 age/age_label 数字污染")
            elif self._extract_numeric_height_preference(message) and (
                "age" in guarded or "age_label" in guarded
            ):
                guarded.pop("age", None)
                guarded.pop("age_label", None)
                logger.info("[提取保护] 择偶身高上下文命中，移除 age/age_label 数字污染")

        if not guarded:
            return guarded

        explicit_self_sex = re.search(r"(我是|本人|我)\s*(男生|女生|男的|女的|男|女)", message)
        preference_sex_hint = re.search(r"(找|想找|喜欢|偏好).{0,4}(男生|女生|男的|女的|男|女)", message)
        if explicit_self_sex and "partner_gender_preference" in guarded and not preference_sex_hint:
            guarded.pop("partner_gender_preference", None)
            logger.info("[提取保护] 检测到明确自述性别，移除本轮 partner_gender_preference 污染值")
        if "sex" in guarded and not explicit_self_sex and preference_sex_hint:
            guarded.pop("sex", None)
            logger.info("[提取保护] 检测到择偶偏好语境，忽略 sex 提取，避免误写用户性别")

        explicit_self_location = re.search(
            r"(?:我在|来自|人在|目前在|现在在|住在)\s*([^\s，。！？!?]{2,8})",
            message,
        )
        preference_location_hint = re.search(
            r"(找|想找|喜欢|偏向|更想找).{0,6}(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)",
            message,
        )
        if "location" in guarded and not explicit_self_location and preference_location_hint:
            guarded.pop("location", None)
            logger.info("[提取保护] 检测到择偶偏好城市语境，忽略 location 提取，避免误写用户所在地")

        return guarded

    def _detect_asked_fields_from_context(self, response: str) -> set[str]:
        text = str(response or "").strip().lower()
        if not text:
            return set()

        asked_fields: set[str] = set()
        pattern_map = {
            "sex": (
                r"男生还是女生",
                r"男的还是女的",
                r"你是男",
                r"你是女",
                r"你应该是男",
                r"你应该是女",
                r"性别",
            ),
            "age": (
                r"多大",
                r"几岁",
                r"年龄",
                r"年纪",
                r"出生",
                r"几几年(?:的)?",
                r"哪一年出生",
                r"九几年",
                r"\d{2}几年",
            ),
            "location": (
                r"哪个城市",
                r"什么城市",
                r"在哪个城市",
                r"常住",
                r"在哪边",
                r"哪里生活",
            ),
            "education": (
                r"学历",
                r"什么学历",
                r"最高学历",
                r"毕业",
            ),
            "occupation": (
                r"做什么工作",
                r"做哪方面",
                r"什么工作",
                r"职业",
                r"做哪行",
            ),
            "marital_status": (
                r"感情状态",
                r"婚况",
                r"单身状态",
                r"单身吗",
                r"单身状态不",
            ),
            "monthly_income": (
                r"月收入",
                r"月薪",
                r"收入",
                r"工资",
                r"多少钱",
            ),
            "partner_requirement": (
                r"另一半",
                r"择偶",
                r"看重哪",
                r"更看重",
                r"看重对方哪一点",
                r"更看重对方哪一点",
                r"有什么要求",
                r"想找个什么样",
                r"希望对方的身高",
                r"身高大概在什么范围",
                r"身高.*范围",
            ),
        }
        for field, patterns in pattern_map.items():
            if any(re.search(pattern, text) for pattern in patterns):
                asked_fields.add(field)
        return asked_fields

    def _message_explicitly_answers_field(self, field: str, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if field == "sex":
            return bool(re.search(r"(男生|女生|男的|女的|^男$|^女$)", text))
        if field == "age":
            return bool(
                re.search(r"(\d{2})后", text)
                or re.search(r"(19\d{2}|20\d{2}|\d{2})年", text)
                or re.search(r"(我今年|今年|我现在|现在)?\s*\d{2}\s*岁", text)
            )
        if field == "location":
            return bool(self._extract_location_like_text(text, compact_message=re.sub(r"[，,、。！？!?~～\s]+", "", text)))
        if field == "education":
            return any(token in text for token in ("博士", "硕士", "研究生", "本科", "大专", "中专", "高中"))
        if field == "occupation":
            return bool(
                re.search(r"(?:^|[，,、\s])(?:做|做的是|我是)\s*([A-Za-z]{1,12}|[\u4e00-\u9fa5]{2,8})", text)
                or text.strip().lower() in {"it", "ui", "hr", "qa"}
            )
        if field == "marital_status":
            return any(token in text for token in ("单身", "未婚", "离异", "已婚", "分居"))
        if field == "monthly_income":
            return bool(self._extract_simple_monthly_income(text))
        if field == "partner_requirement":
            return bool(self._extract_simple_partner_requirement(text))
        return False

    @staticmethod
    def _extract_simple_monthly_income(user_message: str) -> str | None:
        message = str(user_message or "").strip().lower()
        if not message:
            return None

        sanitized_message = re.sub(r"\d+(?:\.\d+)?\s*kg\b", " ", message, flags=re.IGNORECASE)
        sanitized_message = re.sub(r"\d+(?:\.\d+)?\s*(?:公斤|斤)\b", " ", sanitized_message, flags=re.IGNORECASE)
        patterns = [
            r"((?:税前|税后)?\s*\d+(?:\.\d+)?\s*(?:k|w|万)(?:\+|左右|上下)?)",
            r"((?:月收入|月薪|收入|工资)[^，。；,\s]{0,6}\d+(?:\.\d+)?\s*(?:k|w|万|元)(?:\+|左右|上下)?)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)左右)",
            r"(年包\d+(?:\.\d+)?(?:w|万)?左右)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)出头)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)上下)",
        ]
        for pattern in patterns:
            match = re.search(pattern, sanitized_message, re.IGNORECASE)
            if match:
                return re.sub(r"\s+", "", match.group(1))
        return None

    def _render_preference_for_ack(self, preference: str) -> str:
        text = str(preference or "").strip()
        if not text:
            return text
        text = re.sub(r"^(喜欢|想找|想要|找)\s*", "", text)
        text = re.sub(r"^一个", "", text)
        text = text.strip("，,。 ")
        if text.endswith("的女生"):
            return text[:-3] + "女生"
        if text.endswith("的男生"):
            return text[:-3] + "男生"
        if text.endswith("的女孩子"):
            return text[:-4] + "女孩子"
        if text.endswith("的男孩子"):
            return text[:-4] + "男孩子"
        return text

    def _build_lightweight_field_ack(self, message: str, profile) -> str:
        text = str(message or "").strip()
        if not text:
            return ""
        extracted = self._extract_profile_fields(text, last_response="")
        if "sex" not in extracted:
            if re.match(r"^(男的|男生|我是男|男)\b", text):
                extracted["sex"] = "男"
            elif re.match(r"^(女的|女生|我是女|女)\b", text):
                extracted["sex"] = "女"
        preference = str(extracted.get("partner_requirement") or "").strip()
        if not preference:
            preference = self._extract_simple_partner_requirement(text) or ""
        if preference and not (profile and profile.is_active_ask_closed("partner_requirement")):
            natural_preference = self._render_preference_for_ack(preference)
            variants = tuple(v.format(preference=natural_preference) for v in FAST_PATH_PREFERENCE_ACK_VARIANTS)
            return random.choice(variants).strip()
        for field in ("sex", "age_label", "age", "location", "education", "occupation", "marital_status"):
            value = extracted.get(field)
            if not value:
                continue
            ack = self._build_contextual_short_ack(field, value)
            if ack:
                return ack
        return ""

    def _build_opening_profile_ack(self, message: str) -> str:
        text = str(message or "").strip()
        if not text:
            return ""
        extracted = self._extract_profile_fields(text, last_response="")
        preference = self._extract_simple_partner_requirement(text) or ""
        partner_gender = str(extracted.get("partner_gender_preference") or self._extract_partner_gender_preference(text) or "").strip()
        if extracted.get("sex"):
            return "你这边是男生。" if "男" in str(extracted["sex"]) else "你这边是女生。"
        if extracted.get("location"):
            return f"你现在主要在{str(extracted['location']).strip()}。"
        if extracted.get("education"):
            return f"{str(extracted['education']).strip()}是吧。"
        if extracted.get("occupation"):
            occupation = self._render_occupation_for_ack(str(extracted["occupation"]).strip())
            return f"你现在在做{occupation}。"
        if extracted.get("age_label") or extracted.get("age"):
            age_text = str(extracted.get("age_label") or extracted.get("age") or "").strip()
            return f"{self._render_age_value(age_text)}这个年龄段。"
        if partner_gender == "男":
            return "你是想找男生这类。"
        if partner_gender == "女":
            return "你是想找女生这类。"
        if preference:
            natural_preference = self._render_preference_for_ack(preference)
            return f"你更偏向{natural_preference}这类。"
        return ""

    def _should_treat_as_opening_service_confirmation(self, turn_input: TurnUnderstandingInput) -> bool:
        profile = turn_input.user_profile
        message = str(turn_input.user_message or "")
        if not self._is_service_confirmation_like(message):
            return False
        if int(turn_input.message_count or 0) > 1:
            return False
        if self._count_collected_profile_fields(profile) > 0:
            return False
        if self._extract_profile_fields(message, last_response=str(turn_input.last_response or "").strip()):
            return False
        if self._is_boundary_pause(message, profile):
            return False
        if self._is_risk_guard(message):
            return False
        if self._has_faq_priority_signal(message):
            return False
        last_response = str(turn_input.last_response or "").strip()
        if last_response and self._detect_which_field_is_asked(last_response):
            return False
        return True

    def _should_treat_as_mid_service_confirmation(self, turn_input: TurnUnderstandingInput) -> bool:
        profile = turn_input.user_profile
        message = str(turn_input.user_message or "")
        last_response = str(turn_input.last_response or "").strip()
        if not self._is_service_confirmation_like(message):
            return False
        if self._should_treat_as_opening_service_confirmation(turn_input):
            return False
        if self._is_boundary_pause(message, profile):
            return False
        if self._is_risk_guard(message):
            return False
        if self._count_collected_profile_fields(profile) > 0:
            return True
        return bool(last_response and self._detect_which_field_is_asked(last_response))

    @staticmethod
    def _is_service_confirmation_like(message: str) -> bool:
        text = str(message or "").strip().lower()
        if not text:
            return False
        compact = re.sub(r"[\s,，。！？!?~～、：:；;（）()\"'`]+", "", text)
        if not compact:
            return False
        if any(re.search(pattern, compact) for pattern in SERVICE_CONFIRMATION_DIRECT_PATTERNS):
            return True
        has_subject = any(token in compact for token in SERVICE_CONFIRMATION_SUBJECT_PATTERNS)
        has_service = any(token in compact for token in SERVICE_CONFIRMATION_SERVICE_PATTERNS)
        has_question = any(token in compact for token in SERVICE_CONFIRMATION_QUESTION_PATTERNS)
        return has_subject and has_service and has_question

    @staticmethod
    def _count_collected_profile_fields(profile) -> int:
        count = 0
        for field in ("sex", "age", "location", "education", "occupation", "marital_status", "monthly_income", "partner_requirement"):
            value = getattr(profile, field, None)
            if str(value or "").strip():
                count += 1
                continue
            if getattr(profile, "collection_progress", {}).get(field):
                count += 1
        return count

    def _detect_which_field_is_asked(self, response: str) -> str | None:
        text = str(response or "").lower()
        if not text:
            return None

        detection_text = text
        occupation_patterns = [
            r"做什么工作", r"职业", r"从事", r"做哪行", r"做哪方面工作", r"主要做哪方面工作",
        ]
        income_patterns = [
            r"月收入", r"收入", r"月薪", r"工资", r"赚", r"多少钱",
            r"收入.*[？?]", r"月薪.*[？?]",
        ]
        asks_occupation = any(re.search(pattern, detection_text) for pattern in occupation_patterns)
        asks_income = any(re.search(pattern, detection_text) for pattern in income_patterns)
        if asks_occupation and asks_income:
            return "occupation"

        for pattern in income_patterns:
            if re.search(pattern, detection_text):
                return "monthly_income"

        sex_patterns = [
            r"男生还是女生",
            r"男的还是女的",
            r"你是男",
            r"你是女",
            r"你应该是男",
            r"你应该是女",
            r"男孩子",
            r"女孩子",
            r"性别",
            r"你这边是男生",
            r"你这边是女生",
            r"男生对吧",
            r"女生对吧",
        ]
        for pattern in sex_patterns:
            if re.search(pattern, detection_text):
                return "sex"

        partner_requirement_patterns = [
            r"另一半",
            r"有什么要求",
            r"看重哪",
            r"更在意哪",
            r"看重对方哪一点",
            r"更看重对方哪一点",
            r"想找个什么样",
            r"择偶",
        ]
        for pattern in partner_requirement_patterns:
            if re.search(pattern, detection_text):
                return "partner_requirement"

        age_patterns = [
            r"多大", r"年龄", r"几岁", r"岁数", r"出生", r"多老",
            r"年纪", r"年龄.*[？?]",
            r"几几年(?:的)?", r"哪一年出生", r"九几年", r"\d{2}几年",
        ]
        for pattern in age_patterns:
            if re.search(pattern, detection_text):
                return "age"

        location_patterns = [
            r"哪个城市", r"在哪", r"在哪个城市", r"工作生活", r"生活.*城市",
            r"城市.*[？?]", r"哪里.*[？?]",
        ]
        for pattern in location_patterns:
            if re.search(pattern, detection_text):
                return "location"

        education_patterns = [
            r"学历", r"什么学历", r"毕业", r"大学", r"本科", r"研究生", r"博士",
            r"学历.*[？?]",
        ]
        for pattern in education_patterns:
            if re.search(pattern, detection_text):
                return "education"

        occupation_patterns = [
            r"做什么工作", r"职业", r"工作.*[？?]", r"从事", r"做哪行", r"做哪方面工作", r"主要做哪方面工作",
        ]
        for pattern in occupation_patterns:
            if re.search(pattern, detection_text):
                return "occupation"

        marital_patterns = [
            r"婚", r"单身", r"离异", r"未婚", r"结婚", r"婚姻",
        ]
        for pattern in marital_patterns:
            if re.search(pattern, detection_text):
                return "marital_status"

        return None

    @staticmethod
    def _render_occupation_for_ack(value: str) -> str:
        text = str(value or "").strip()
        if text.endswith("的") and len(text) >= 3:
            text = text[:-1]
        return text

    @staticmethod
    def _render_age_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return text
        if text.endswith(("岁", "后", "年")):
            return text
        if text.isdigit():
            return f"{text}岁"
        return text

    def _build_contextual_short_ack(self, field: str, value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if field == "sex":
            return ""
        if field in {"age", "age_label"}:
            return ""
        if field == "location":
            variants = (
                f"你现在在{text}。",
                f"现在主要在{text}。",
                f"在{text}这边。",
            )
            return random.choice(variants)
        if field == "education":
            variants = (
                f"{text}是吧。",
                f"学历这块是{text}。",
            )
            return random.choice(variants)
        if field == "occupation":
            rendered = self._render_occupation_for_ack(text)
            variants = (
                f"你现在在做{rendered}。",
                f"现在主要是做{rendered}。",
            )
            return random.choice(variants)
        if field == "marital_status":
            if "离异" in text:
                return "现在是这个状态。"
            if "单身" in text:
                return "现在是单身在了解。"
            return f"现在是{text}这个状态。"
        return ""

    @staticmethod
    def _is_explicit_matchmaking_intent_message(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        return bool(
            re.search(
                r"((?:想)?找(?:个)?(?:对象|另一半|男朋友|女朋友)|(?:帮(?:我|忙)?|给我)?(?:找|介绍|介绍下|牵线|安排)(?:个)?(?:对象|另一半|男朋友|女朋友)|介绍(?:个)?(?:对象|另一半|男朋友|女朋友)|相亲|脱单|认真聊聊)",
                text,
            )
        )

    def _normalize_opening_probe_text(self, message: str) -> str:
        normalized = re.sub(r"[\s,，。！？!?~～、]+", "", str(message or "").strip().lower())
        normalized = re.sub(r"(呀|啊|呢|嘛|呗|啦|喔|咯|哈)+$", "", normalized)
        normalized = re.sub(r"(呀|啊|呢|嘛|呗|啦|喔|咯|哈){2,}", r"\1", normalized)
        normalized = re.sub(r"(在吗){2,}", "在吗", normalized)
        normalized = re.sub(r"(在不){2,}", "在不", normalized)
        normalized = re.sub(r"(你好){2,}", "你好", normalized)
        normalized = re.sub(r"(hi){2,}", "hi", normalized)
        normalized = re.sub(r"(hello){2,}", "hello", normalized)
        return normalized

    def _is_stable_opening_greeting(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        greeting_service = getattr(self.chat_service, "greeting_service", None)
        if greeting_service is not None and greeting_service.is_greeting(text):  # noqa: SLF001
            return True
        normalized = self._normalize_opening_probe_text(text)
        if not normalized:
            return False
        greeting_tokens = ("你好", "您好", "hi", "hello", "哈喽", "嗨", "在吗", "在不", "早上好", "下午好", "晚上好")
        if any(token in normalized for token in greeting_tokens):
            remainder = normalized
            for token in greeting_tokens:
                remainder = remainder.replace(token, "")
            return remainder == ""
        return False

    def _has_opening_greeting_signal(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self._is_stable_opening_greeting(text):
            return True
        normalized = self._normalize_opening_probe_text(text)
        if not normalized:
            return False
        greeting_tokens = ("你好", "您好", "hi", "hello", "哈喽", "嗨", "在吗", "在不", "早上好", "下午好", "晚上好")
        return any(token in normalized for token in greeting_tokens)

    def _looks_like_greeting(self, message: str) -> bool:
        return self._has_opening_greeting_signal(message)

    def _is_opening_probe_followup_message(self, message: str, last_response: str) -> bool:
        text = str(message or "").strip()
        previous = str(last_response or "").strip()
        if not text or not previous:
            return False
        probe_markers = (
            "想找对象",
            "先了解下",
            "先问问情况",
            "先看看情况",
            "认真聊聊",
            "简单介绍下自己",
            "简单说说自己",
            "讲讲自己的情况",
            "顺着了解",
        )
        return any(marker in previous for marker in probe_markers)

    def _should_use_opening_clarify(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        normalized = re.sub(r"[\s,，。！？!?~～、]+", "", text)
        if not normalized:
            return False
        if "\ufffd" in text or "�" in text:
            return True
        input_fallback_service = getattr(self.chat_service, "input_fallback_service", None)
        if input_fallback_service is not None and input_fallback_service.is_nonsense_input(text):  # noqa: SLF001
            return True
        weird_char_count = len(re.findall(r"[^\w\s\u4e00-\u9fa5，。！？!?~～、]", text))
        if weird_char_count >= 2:
            return True
        if len(normalized) <= 3 and not re.search(r"[\u4e00-\u9fa5a-zA-Z]", normalized):
            return True
        return False

    def _is_noisy_opening_clarify_message(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self._should_use_opening_clarify(text):
            return True
        normalized = self._normalize_opening_probe_text(text)
        if not normalized:
            return False
        if any(token in normalized for token in ("你好", "您好", "在吗", "在不")):
            stripped = normalized
            for token in ("你好", "您好", "在吗", "在不"):
                stripped = stripped.replace(token, "")
            greeting_service = getattr(self.chat_service, "greeting_service", None)
            if greeting_service is not None:
                return bool(stripped) and not greeting_service.is_greeting(stripped)
            fallback_tokens = ("你好", "您好", "hi", "hello", "哈喽", "嗨", "在吗", "在不", "早上好", "下午好", "晚上好")
            return bool(stripped) and not any(token in stripped for token in fallback_tokens)
        return False

    def _looks_like_resume_profile_collection(self, turn_input: TurnUnderstandingInput) -> bool:
        message = str(turn_input.user_message or "").strip()
        return bool(message) and any(pattern in message for pattern in RESUME_PROFILE_COLLECTION_PATTERNS)

    def _looks_like_post_answer_reentry(self, turn_input: TurnUnderstandingInput) -> bool:
        message = str(turn_input.user_message or "").strip()
        previous_response = str(turn_input.last_response or "").strip()
        if not message or not previous_response:
            return False
        if not self._is_acknowledgement_only_message(message):
            return False
        if self._has_faq_priority_signal(previous_response):
            return True
        if (
            any(marker in previous_response for marker in ("保密", "严格保密", "精准", "更符合你预期"))
            and any(marker in previous_response for marker in ("匹配", "要求", "男生", "对象"))
        ):
            return True
        return any(marker in previous_response for marker in FAQ_ANSWER_MARKERS)

    @staticmethod
    def _is_acknowledgement_only_message(message: str) -> bool:
        normalized = re.sub(r"[，。！？!?~～、\s]+", "", str(message or "").strip())
        return normalized in ACKNOWLEDGEMENT_MESSAGES

    @staticmethod
    def _looks_like_refusal(message: str) -> bool:
        return bool(re.search(r"(不方便说|不想说|先不说|不太想说|这个不说)", message))

    @staticmethod
    def _looks_like_correction(message: str) -> bool:
        return bool(re.search(r"(不是.+是.+|不是这个|刚刚说的是|说错了|改成|改为)", message))

    @staticmethod
    def _looks_like_invalid_input(message: str) -> bool:
        compact = re.sub(r"\s+", "", message)
        if re.fullmatch(r"[?？!！,.，。~～、]+", compact):
            return True
        if re.search(r"(乱码|手滑|乱打|输错)", message):
            return True
        if re.search(r"[a-zA-Z][a-zA-Z0-9_-]{3,}[\u4e00-\u9fff]+[a-zA-Z0-9_-]+", message):
            return True
        return False

    def _looks_like_confirmation(self, message: str, turn_input: TurnUnderstandingInput) -> bool:
        if not re.fullmatch(r"\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好|行|可以)\s*[，,、 ]*\s*", message):
            return False
        return bool(turn_input.last_response or turn_input.pending_confirmation_field)

    @staticmethod
    def _looks_like_preference_only(message: str) -> bool:
        return bool(re.search(r"(找男生|找女生|喜欢男生|喜欢女生|想找男|想找女)", str(message or "")))

    @staticmethod
    def _looks_like_contaminated_contact(message: str, candidate_value: str) -> bool:
        dirty_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{5,19}[\u4e00-\u9fff]+[a-zA-Z0-9_-]+", str(message or ""))
        lower_candidate = str(candidate_value or "").lower()
        return any(token.lower().startswith(lower_candidate) for token in dirty_tokens)

    @staticmethod
    def _contact_subtype(message: str, resolved_slots: Dict[str, str]) -> str:
        if re.search(r"(电话不方便|不留电话|不给电话).*(微信可以|留微信|微信吧)", message):
            return "contact_preference_switch"
        if re.search(r"(不留电话|不给电话|不留微信|不给微信)", message):
            return "contact_refusal"
        if any(field in resolved_slots for field in {"phone", "wechat"}):
            return "contact_provided"
        return "contact_context_reply"

    @staticmethod
    def _profile_subtype(message: str, message_count: int, resolved_slots: Dict[str, str]) -> str:
        if len(resolved_slots) >= 2:
            return "multi_slot_compound"
        if message_count <= 1:
            return "proactive_profile_provide"
        return "single_slot_answer"

    def _opening_subtype(self, message: str) -> str:
        if self._is_stable_opening_greeting(message):
            return "greeting"
        if self._is_explicit_matchmaking_intent_message(message):
            return "matchmaking_intent"
        return "connective_opening"

    def _extract_opening_signals(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> Dict[str, bool]:
        message = str(turn_input.user_message or "").strip()
        message_count = int(turn_input.message_count or 0)
        if message_count > 1 or not message:
            return {}

        signals = {
            "greeting": self._has_opening_greeting_signal(message),
            "matchmaking_intent": self._is_explicit_matchmaking_intent_message(message),
            "service_confirmation": False,
            "low_pressure": False,
            "clarify": False,
            "profile_provided": bool(resolved_slots),
        }
        if not resolved_slots:
            signals["service_confirmation"] = self._looks_like_opening_service_confirmation(turn_input, resolved_slots)
            signals["low_pressure"] = self._looks_like_low_pressure_opening(turn_input, resolved_slots)
            signals["clarify"] = self._looks_like_opening_clarify(turn_input, resolved_slots)
        return signals

    def _looks_like_opening_clarify(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> bool:
        message = str(turn_input.user_message or "").strip()
        if int(turn_input.message_count or 0) != 0:
            return False
        if resolved_slots:
            return False
        if self._is_stable_opening_greeting(message):
            return False
        if self._is_explicit_matchmaking_intent_message(message):
            return False
        if self._detect_faq_intent(message):
            return False
        if self._is_boundary_pause(message, turn_input.user_profile):
            return False
        if self._is_risk_guard(message):
            return False
        return bool(
            self._should_use_opening_clarify(message)
            or self._is_noisy_opening_clarify_message(message)
        )

    def _build_context_ack_payload(
        self,
        turn_input: TurnUnderstandingInput,
        *,
        context_ack_type: str | None,
    ) -> Dict[str, str]:
        if not context_ack_type:
            return {}

        message = str(turn_input.user_message or "").strip()
        profile = turn_input.user_profile
        payload: Dict[str, str] = {}
        if context_ack_type == "work_busy":
            payload["occupation"] = str(getattr(profile, "occupation", "") or "").strip()
        elif context_ack_type == "location_reuse":
            payload["location"] = str(getattr(profile, "location", "") or "").strip()
        elif context_ack_type == "preference_reuse":
            preference = str(getattr(profile, "partner_requirement", "") or "").strip()
            if preference:
                payload["preference"] = self._render_preference_for_ack(preference)
        elif context_ack_type == "profile_partial_with_boundary":
            payload["field_ack"] = self._build_lightweight_field_ack(message, profile)
        elif context_ack_type == "opening_profile_ack":
            payload["field_ack"] = self._build_opening_profile_ack(message)
        elif context_ack_type == "field_soft_refusal_retry":
            previous_field = self._resolve_previous_asked_field(turn_input)
            if previous_field:
                payload["field"] = previous_field
        return payload

    def _looks_like_opening_service_confirmation(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> bool:
        if resolved_slots:
            return False
        return self._should_treat_as_opening_service_confirmation(turn_input)

    def _looks_like_mid_service_confirmation(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> bool:
        if resolved_slots:
            return False
        return self._should_treat_as_mid_service_confirmation(turn_input)

    def _looks_like_low_pressure_opening(
        self,
        turn_input: TurnUnderstandingInput,
        resolved_slots: Dict[str, str],
    ) -> bool:
        message = str(turn_input.user_message or "").strip()
        last_response = str(turn_input.last_response or "").strip()
        normalized_message = self._normalize_opening_probe_text(message)
        if int(turn_input.message_count or 0) > 2:
            return False
        if resolved_slots:
            return False
        if self._detect_faq_intent(message):
            return False
        if self._is_boundary_pause(message, turn_input.user_profile):
            return False
        if self._is_risk_guard(message):
            return False
        if not self._is_opening_probe_followup_message(message, last_response):
            return False
        return normalized_message in {
            "先了解下",
            "先了解一下",
            "了解下",
            "了解一下",
            "先看看",
            "看看情况",
            "问问情况",
            "先问问情况",
            "想了解下",
            "想了解一下",
            "先聊聊",
            "我先看看",
            "就是想先问问情况",
            "我问问你情况",
        }
