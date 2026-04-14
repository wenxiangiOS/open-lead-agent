from __future__ import annotations

import re
from datetime import datetime
from types import SimpleNamespace

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService


class _StubChatService:
    def __init__(self):
        self.extraction_service = ExtractionService(SimpleNamespace())
        self.user_question_service = SimpleNamespace(
            detect_quick_faq_intent=lambda message: (
                "fee"
                if "收费" in str(message or "")
                else "info_collection_why"
                if "记下我的信息" in str(message or "")
                else None
            )
        )
        self.expectation_service = SimpleNamespace(
            is_matching_timeline_question=lambda message: "多久" in str(message or "")
        )

    def _extract_deterministic_profile_fields(self, message: str):
        text = str(message or "").strip()
        extracted = {}
        if re.search(r"(^|[，, ])男([，, ]|$)|男生|男的", text):
            extracted["sex"] = "男"
        if re.search(r"(^|[，, ])女([，, ]|$)|女生|女的", text):
            extracted["sex"] = "女"
        if "单身" in text:
            extracted["marital_status"] = "单身"
        if "离异" in text:
            extracted["marital_status"] = "离异"
        if "广州" in text:
            extracted["location"] = "广州"
        if "深圳" in text:
            extracted["location"] = "深圳"
        for edu in ("博士", "硕士", "研究生", "本科", "大专", "中专", "高中"):
            if edu in text:
                extracted["education"] = edu
                extracted.setdefault("partner_requirement", edu)
                break
        if "IT" in text or "it" in text:
            extracted["occupation"] = "IT"
        age_match = re.search(r"(\d{2})", text)
        if "今年" in text and age_match:
            extracted["age"] = int(age_match.group(1))
        if "160以上" in text:
            extracted["partner_requirement"] = "160以上"
        return extracted

    def _apply_extraction_guards(self, extracted, message: str, last_response: str = ""):
        return dict(extracted or {})

    def _extract_contact_candidate_from_message(self, message: str):
        text = str(message or "").strip()
        phone = re.search(r"1[3-9]\d{9}", text)
        if phone:
            return {"type": "phone", "value": phone.group(0)}
        wx = re.search(r"微信(?:是|号)?\s*([a-zA-Z][a-zA-Z0-9_-]{5,19})", text)
        if wx:
            return {"type": "wechat", "value": wx.group(1)}
        return None

    def _is_risk_guard_triggered(self, message: str) -> bool:
        return "自杀" in str(message or "")

    def _classify_withdraw_intent(self, message: str):
        if "先这样吧" in str(message or "") or "不聊了" in str(message or ""):
            return "soft_exit"
        return None

    def _matches_any_pattern(self, text: str, patterns):
        return any(re.search(pattern, str(text or "")) for pattern in patterns)

    def _is_boundary_pause_triggered(self, message: str, user_profile=None) -> bool:
        return any(token in str(message or "") for token in ("不想说", "问这么细", "不方便说"))

    def _is_complaint_message(self, message: str) -> bool:
        return any(token in str(message or "") for token in ("怎么一直问", "是不是问的次数太多了", "查户口"))

    def _is_stable_opening_greeting(self, message: str) -> bool:
        return str(message or "").strip() in {"你好", "hi", "在吗"}

    def _is_explicit_matchmaking_intent_message(self, message: str) -> bool:
        return "找对象" in str(message or "")

    def _normalize_opening_probe_text(self, user_message: str) -> str:
        message = str(user_message or "").strip().lower()
        message = re.sub(r"[\s,，。！？!?~～、:：;；\"'`()（）]+", "", message)
        message = re.sub(r"(呀|啊|呢|哈|啦|嘛|呐|喔|哦|噢)+", "", message)
        return message

    def _should_use_opening_clarify(self, message: str) -> bool:
        return "坏呼叫" in str(message or "") or "佃" in str(message or "")

    def _is_noisy_opening_clarify_message(self, message: str) -> bool:
        return self._should_use_opening_clarify(message)

    def _should_treat_as_opening_service_confirmation(
        self,
        user_profile,
        *,
        stage: str,
        message_count: int,
        user_message: str,
        last_response: str,
    ) -> bool:
        return stage == "opening" and "介绍对象" in str(user_message or "") and message_count <= 1

    def _should_treat_as_mid_service_confirmation(
        self,
        user_profile,
        *,
        stage: str,
        message_count: int,
        user_message: str,
        last_response: str,
    ) -> bool:
        return bool(last_response) and "介绍对象" in str(user_message or "")

    def _is_opening_probe_followup_message(self, user_message: str, last_response: str = "") -> bool:
        return "先了解下" in str(user_message or "") and "先了解下" in str(last_response or "")

    def _extract_simple_partner_requirement(self, message: str):
        text = str(message or "")
        if "160以上" in text:
            return "160以上"
        return None

    def _is_resume_profile_collection_message(self, user_message: str) -> bool:
        return "你不问其他了" in str(user_message or "")

    def _is_post_answer_reentry_turn(self, user_message: str, last_response: str = "") -> bool:
        return str(user_message or "").strip() in {"好", "知道了"} and "收费" in str(last_response or "")


def _make_input(
    message: str,
    *,
    last_response: str = "",
    message_count: int = 0,
    in_contact_flow: bool = False,
    user_profile=None,
    pending_confirmation_field=None,
):
    return TurnUnderstandingInput(
        user_message=message,
        last_response=last_response,
        message_count=message_count,
        user_profile=user_profile or SimpleNamespace(),
        conversation_context={"recent_responses": [last_response] if last_response else []},
        in_contact_flow=in_contact_flow,
        pending_confirmation_field=pending_confirmation_field,
    )


def test_multi_slot_profile_answer_resolves_sex_and_marital_status():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("男，单身"))
    assert result.primary_turn_type == "profile_answer"
    assert result.subtype == "multi_slot_compound"
    assert result.resolved_slots["sex"] == "男"
    assert result.resolved_slots["marital_status"] == "单身"


def test_faq_with_profile_signal_answers_first_and_resumes_mainline():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("我在广州，你们多久联系我"))
    assert result.primary_turn_type == "faq_concern"
    assert result.answer_first is True
    assert result.resume_hint == "profile_mainline"
    assert result.resolved_slots["location"] == "广州"


def test_contact_preference_switch_is_contact_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("电话不方便，微信可以", in_contact_flow=True))
    assert result.primary_turn_type == "contact_answer"
    assert result.subtype == "contact_preference_switch"
    assert "occupation" not in result.resolved_slots


def test_contact_context_reply_maps_wechat_to_phone_when_user_says_same_number():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_same_as_phone")
    profile.phone = "17688987659"
    profile.phone_collected = True
    profile.pending_contact_field = "wechat"
    profile.last_contact_request_type = "wechat"

    result = service.analyze(_make_input("就是电话", in_contact_flow=True, user_profile=profile))

    assert result.primary_turn_type == "contact_answer"
    assert result.resolved_slots["wechat"] == "17688987659"
    assert "occupation" not in result.resolved_slots


def test_education_like_preference_is_blocked():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("本科"))
    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["education"] == "本科"
    assert "partner_requirement" in result.blocked_slots
    assert result.blocked_slots["partner_requirement"].reason == "looks_like_education_not_preference"


def test_closing_exit_has_high_priority():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("先这样吧"))
    assert result.primary_turn_type == "closing_exit"


def test_turn_understanding_extracts_age_from_natural_self_report():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("我今年36"))
    assert result.primary_turn_type == "profile_answer"


def test_turn_understanding_keeps_self_sex_in_mixed_self_intro_with_partner_preference():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("南山女生找男朋友，93年未婚，起码本科，自己也是做互联网的")
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["marital_status"] == "未婚"
    assert result.resolved_slots["age"] == "33"


def test_turn_understanding_keeps_self_location_in_mixed_intro_with_location_preference():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("深圳女生想找香港的男生，93年未婚，自己也是做互联网的")
    )

    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["partner_requirement"] == "香港"
    assert result.resolved_slots["partner_gender_preference"] == "男"


def test_turn_understanding_does_not_treat_hk_resource_question_as_self_location():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("女生 香港有不", last_response="行呀，那我先简单问下哦，你是男生还是女生呀？", message_count=2)
    )

    assert result.resolved_slots["sex"] == "女"
    assert "location" not in result.resolved_slots
    assert "occupation" not in result.resolved_slots
    assert "occupation" not in result.blocked_slots


def test_turn_understanding_blocks_low_quality_occupation_candidate_in_faq_like_opening():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("可以啊 机构是吗 资源怎么样啊"))

    assert "occupation" not in result.resolved_slots
    assert "occupation" not in result.blocked_slots


def test_turn_understanding_does_not_treat_faq_location_probe_as_self_location():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("香港的有吗"))

    assert "location" not in result.resolved_slots
    assert "location" not in result.blocked_slots
    assert "occupation" not in result.resolved_slots
    assert "occupation" not in result.blocked_slots


def test_turn_understanding_does_not_treat_faq_education_probe_as_self_education():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("本科以上的有吗"))

    assert "education" not in result.resolved_slots
    assert "education" not in result.blocked_slots
    assert "occupation" not in result.resolved_slots
    assert "occupation" not in result.blocked_slots


def test_turn_understanding_does_not_extract_age_from_income_typo_message():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("月搜入大概20k+", last_response="你现在月收入大概在哪个区间呀？", message_count=3)
    )

    assert result.resolved_slots["monthly_income"] == "20k+"
    assert "age" not in result.resolved_slots


def test_turn_understanding_opening_mixed_intro_blocks_relationship_and_income_age_pollution():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就"
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["marital_status"] == "单身"
    assert result.resolved_slots["monthly_income"] == "一年18左右"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "身高180cm以上"
    assert "occupation" not in result.resolved_slots
    assert "age" not in result.resolved_slots


def test_turn_understanding_opening_mixed_intro_with_trailing_question_text_does_not_pollute_occupation():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就 怎么多了"
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["marital_status"] == "单身"
    assert result.resolved_slots["monthly_income"] == "一年18左右"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "身高180cm以上"
    assert "occupation" not in result.resolved_slots
    assert "age" not in result.resolved_slots


def test_turn_understanding_keeps_rich_partner_requirement_in_mixed_self_intro():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("南山女生找男盆友，就是93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不")
    )

    assert result.resolved_slots["sex"] == "女"
    assert "education" not in result.resolved_slots
    assert result.resolved_slots["marital_status"] == "未婚"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "未婚，学历本科及以上，大厂程序员"


def test_turn_understanding_keeps_self_marital_status_and_education_in_mixed_intro():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("深圳女生，93年未婚，自己本科，想找未婚、本科及以上的男生")
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["marital_status"] == "未婚"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["partner_gender_preference"] == "男"


def test_turn_understanding_mixed_intro_with_contact_no_longer_collapses_to_contact_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("94年，深圳女生，港硕，外贸行业工作，想找90后男生，微信abc123456", in_contact_flow=True)
    )

    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["age_label"] == "94年"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["education"] == "硕士"
    assert result.resolved_slots["occupation"] == "外贸"
    assert result.resolved_slots["wechat"] == "abc123456"


def test_turn_understanding_hobby_phrase_no_longer_pollutes_occupation():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("喜欢做饭旅游，到时候可以微信联系我abc123456")  # noqa: SLF001

    assert "occupation" not in extracted
    assert extracted == {}


def test_turn_understanding_does_not_write_self_marital_status_from_partner_only_requirement():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("想找未婚的男生，本科及以上就行")
    )

    assert "marital_status" not in result.resolved_slots
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "未婚，学历本科及以上"


def test_turn_understanding_supports_colloquial_partner_requirement_variants():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("深圳女生，自己互联网，想找港男，本科起步，程序员最好")
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["occupation"] == "互联网"
    assert result.resolved_slots["partner_requirement"] == "香港，学历本科及以上，程序员"


def test_turn_understanding_supports_numeric_colloquial_partner_requirement_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175往上，30左右，月入别太低")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_turn_understanding_supports_looser_numeric_colloquial_partner_requirement_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("一米七五以上，三十出头，收入别太拉垮")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_turn_understanding_supports_even_looser_numeric_colloquial_partner_requirement_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("一米七五朝上，三十来岁，收入别太低就行")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_turn_understanding_supports_nonstandard_numeric_colloquial_partner_requirement_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("一米七五打底，三十上下，收入过得去就行")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_turn_understanding_supports_even_more_scattered_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("一米七五左右，三十多点，收入差不多就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_spoken_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("身高差不多175，30出头，收入别太寒碜")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175差不多，三十郎当岁，收入别太难看")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_extra_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下，三十好几，收入看得过去就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下浮动，三十冒头，收入说得过去就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_soft_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("一米七五上下都行，三十左右都可，收入能看就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_soft_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("身高175左右都成，30上下都行，收入过得去就成")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_variant_more_soft_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175左右都可以，30左右都行，收入差不离就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_extra_variant_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175附近，30来岁也行，收入别太磕碜")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_latest_extra_variant_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下差不多，30来岁左右，收入别太埋汰")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_latest_slang_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175差不离，30左右上下，收入别太拉胯")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_extra_variant_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175前后，30来岁都成，收入别太埋汰")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都可，30来岁上下，收入过得去就好")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都成，30来岁上下都行，收入说得过去就好")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_latest_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都OK，30来岁上下都可，收入别太说不过去")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_latest_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都ok啦，30来岁上下都成，收入别太拿不出手")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_next_more_latest_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都ok的，30来岁上下也成，收入别太掉价")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_followup_latest_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下也行，30来岁也都行，收入别太上不了台面")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_latest_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下都还行，30来岁也可以，收入别太寒酸")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_next_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下差不太多，30来岁差不多，收入别太捉襟见肘")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下大差不差，30来岁上下差不多，收入别太拮据")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下凑合，30来岁还行，收入别太紧巴")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_more_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下过得去，30来岁还成，收入别太磕巴")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_next_more_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下说得过去，30来岁说得过去，收入别太寒碜吧")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下没毛病，30来岁问题不大，收入别太磕碜吧")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_post_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下没啥问题，30来岁没啥问题，收入别太掉面儿")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_after_post_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下还过得去，30来岁还过得去，收入别太上不得台面")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下马马虎虎，30来岁马马虎虎，收入别太寒掺")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_really_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下也还行，30来岁也还行，收入别太没法看")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_true_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下不赖，30来岁不赖，收入别太磕搀")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_actual_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下将就，30来岁将就，收入别太寒碜着")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_actual_real_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下还凑合，30来岁还凑合，收入别太跌份")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_next_actual_real_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("175上下也凑合，30来岁也凑合，收入别太寒伧")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_supports_structured_numeric_partner_preference_for_bare_height_plus():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("想找一个175+的，30左右，收入别太低")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_turn_understanding_supports_structured_numeric_partner_preference_for_bare_numeric_operands():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("想找175以上的，30+的，月入2w+的")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30以上，收入2万以上"


def test_turn_understanding_supports_structured_numeric_partner_preference_for_explicit_operand_phrases():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("想找175往上的，30左右的，收入过万的")  # noqa: SLF001

    assert extracted == "身高175cm以上，年龄30左右，收入1万以上"


def test_turn_understanding_supports_structured_numeric_partner_preference_for_explicit_around_and_income_bound_phrases():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("想找175左右的，30上下的，收入2万以上的")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入2万以上"


def test_turn_understanding_extracts_structured_numeric_partner_preference_semantics():
    semantics = TurnUnderstandingService._extract_structured_numeric_partner_preference_semantics(  # noqa: SLF001
        "想找175以上的，30+的，月入2w+的"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "lower_bound", "value": "175"},
        {"pos": 9, "field": "age", "operator": "lower_bound", "value": "30"},
        {"pos": 14, "field": "income", "operator": "lower_bound", "value": "2万"},
    ]


def test_turn_understanding_extracts_structured_numeric_partner_preference_semantics_from_colloquial_aliases():
    semantics = TurnUnderstandingService._extract_structured_numeric_partner_preference_semantics(  # noqa: SLF001
        "想找175差不多的，三十来岁的，收入过得去就行"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "around", "value": "175"},
        {"pos": 10, "field": "age", "operator": "around", "value": "30"},
        {"pos": 16, "field": "income", "operator": "not_too_low", "value": ""},
    ]


def test_turn_understanding_extracts_structured_numeric_partner_preference_semantics_with_conversational_tails():
    semantics = TurnUnderstandingService._extract_structured_numeric_partner_preference_semantics(  # noqa: SLF001
        "想找175左右都可以，30上下都行，收入过得去就好"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "around", "value": "175"},
        {"pos": 11, "field": "age", "operator": "around", "value": "30"},
        {"pos": 18, "field": "income", "operator": "not_too_low", "value": ""},
    ]


def test_turn_understanding_simple_partner_requirement_uses_structured_numeric_alias_bridge():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_simple_partner_requirement("175上下都OK，三十出头，收入过得去就行")  # noqa: SLF001

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_turn_understanding_treats_no_education_as_valid_education_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("没有学历"))
    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["education"] == "没学历"


def test_turn_understanding_treats_divorce_as_valid_marital_status_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("离婚"))
    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["marital_status"] == "离异"


def test_turn_understanding_extracts_sex_and_marital_status_from_affirmative_compound_answer():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_affirmative_compound")
    profile.pending_sex_confirmation = "女"

    result = service.analyze(
        _make_input(
            "是的，离婚",
            last_response="我顺嘴核对下哦，你是女生对吧？另外你现在的感情状态大概是什么样呀？",
            user_profile=profile,
            pending_confirmation_field="sex",
        )
    )

    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["marital_status"] == "离异"


def test_turn_understanding_opening_matchmaking_with_explicit_age_keeps_actual_age():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("我想找对象，我今年26岁", message_count=1))
    assert result.primary_turn_type == "opening"
    assert result.subtype == "matchmaking_intent"
    assert result.resolved_slots["age"] == "26"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_extracts_married_status_from_natural_phrase():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("我已经结婚了"))
    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["marital_status"] == "已婚"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_classifies_opening_service_confirmation():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("你们帮帮忙介绍对象吗？"))
    assert result.primary_turn_type == "opening"
    assert result.subtype == "matchmaking_intent"
    assert "service_confirmation_like" in result.secondary_signals


def test_turn_understanding_classifies_low_pressure_opening_after_probe():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "先了解下",
            last_response="你好呀，我在呢。你这边是想找对象，还是先了解下呀？",
            message_count=1,
        )
    )
    assert result.primary_turn_type == "opening"
    assert result.subtype == "low_pressure_opening"


def test_turn_understanding_marks_post_answer_reentry_signal():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "好",
            last_response="我们这边不收费，先顺着了解就行。",
            message_count=3,
        )
    )
    assert result.post_answer_reentry is True


def test_turn_understanding_marks_post_answer_reentry_for_info_collection_explanation():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "好的",
            last_response="这个我先说清楚，主要是怕后面把你的情况和择偶需求理解偏了，不会拿去乱登记乱用的。",
            message_count=4,
        )
    )
    assert result.post_answer_reentry is True
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_marks_post_answer_reentry_for_precise_matching_explanation():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "好的",
            last_response="我知道你会在意问得太细的问题，主要是为了后续给你匹配对象的时候更精准，不会给你推不符合你要求的男生哦。",
            message_count=4,
        )
    )
    assert result.post_answer_reentry is True
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_detects_contextual_info_collection_concern():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_ctx_concern")
    profile.last_asked_field = "monthly_income"

    result = service.analyze(
        _make_input(
            "这些信息干嘛",
            last_response="你方便说下每个月收入大概在什么区间吗？",
            message_count=4,
            user_profile=profile,
        )
    )

    assert result.primary_turn_type == "faq_concern"
    assert result.subtype == "info_collection_why"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_exposes_looks_like_greeting_helper():
    service = TurnUnderstandingService(_StubChatService())
    assert service._looks_like_greeting("你好呀") is True  # noqa: SLF001


def test_turn_understanding_result_to_dict_includes_soft_retry_field():
    from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult

    result = TurnUnderstandingResult(
        primary_turn_type="invalid_input",
        subtype="soft_refusal_current_field",
        context_ack_type="field_soft_refusal_retry",
        soft_retry_field="occupation",
    )

    payload = result.to_dict()

    assert payload["soft_retry_field"] == "occupation"


def test_turn_understanding_exposes_opening_field_ack_separately_from_payload():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("你好，我在深圳"))

    assert result.context_ack_type == "opening_profile_ack"
    assert result.context_ack_field_ack == "你现在主要在深圳。"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_context_ack_does_not_mark_opening_profile_ack_for_non_preference_short_trait():
    service = TurnUnderstandingService(_StubChatService())
    context_ack_type = service._derive_context_ack_type(  # noqa: SLF001
        _make_input("温柔吧", message_count=1),
        primary_turn_type="opening",
        subtype="connective_opening",
        resolved_slots={},
        secondary_signals=[],
    )

    assert context_ack_type is None


def test_turn_understanding_does_not_treat_self_education_phrase_as_occupation():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(_make_input("深圳女生，93年未婚，自己本科，想找未婚、本科及以上的男生"))

    assert result.resolved_slots["education"] == "本科"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_detects_asked_field_prefers_last_question_over_ack_text():
    service = TurnUnderstandingService(_StubChatService())
    asked_field = service._detect_which_field_is_asked(  # noqa: SLF001
        "好，现在单身状态我知道了。 这些我都先记下啦，姓文，180的个子挺不错的~你是男生还是女生呀？"
    )
    assert asked_field == "sex"


def test_turn_understanding_detects_asked_field_prefers_partner_requirement():
    service = TurnUnderstandingService(_StubChatService())
    asked_field = service._detect_which_field_is_asked(  # noqa: SLF001
        "那我再了解下，方便说下你今年多大吗？ 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更在意哪方面？"
    )
    assert asked_field == "partner_requirement"


def test_turn_understanding_detects_asked_field_prefers_occupation_over_income():
    service = TurnUnderstandingService(_StubChatService())
    asked_field = service._detect_which_field_is_asked(  # noqa: SLF001
        "那你现在在深圳主要做哪方面工作呀？ 收入这块大概在什么区间，也可以顺手说个大概。"
    )
    assert asked_field == "occupation"


def test_turn_understanding_detects_soft_gender_confirmation():
    service = TurnUnderstandingService(_StubChatService())
    asked_field = service._detect_which_field_is_asked(  # noqa: SLF001
        "我再确认下，你这边是男生在了解，对吧？"
    )
    assert asked_field == "sex"


def test_turn_understanding_detects_asked_field_prefers_sex_over_partner_requirement():
    service = TurnUnderstandingService(_StubChatService())
    asked_field = service._detect_which_field_is_asked(  # noqa: SLF001
        "你大概是什么学历呀？平时更看重另一半哪一点，也可以一起说说。对了，我还不知道你是男生还是女生呢？"
    )
    assert asked_field == "sex"


def test_turn_understanding_builds_opening_profile_ack():
    service = TurnUnderstandingService(_StubChatService())
    assert service._build_opening_profile_ack("我在深圳") == "你现在主要在深圳。"  # noqa: SLF001
    assert service._build_opening_profile_ack("本科") == "本科是吧。"  # noqa: SLF001
    assert service._build_opening_profile_ack("不要同财务行业，想找稳定行业男生") == "你是想找男生这类。"  # noqa: SLF001


def test_turn_understanding_builds_opening_profile_ack_does_not_preference_ack_trait_without_context():
    service = TurnUnderstandingService(_StubChatService())
    ack = service._build_opening_profile_ack("温柔吧")  # noqa: SLF001
    assert "偏向" not in ack


def test_turn_understanding_message_explicitly_answers_partner_requirement_requires_preference_context():
    service = TurnUnderstandingService(_StubChatService())
    assert service._message_explicitly_answers_field("partner_requirement", "温柔吧") is False  # noqa: SLF001
    assert service._message_explicitly_answers_field("partner_requirement", "想找温柔的") is True  # noqa: SLF001


def test_turn_understanding_resolves_partner_requirement_text_from_structured_subslots():
    service = TurnUnderstandingService(_StubChatService())
    preference = service._resolve_partner_requirement_text(  # noqa: SLF001
        {
            "partner_pref_age": "90后",
            "partner_pref_location": "深圳",
        },
        "90后都可以，最好深圳",
    )
    assert preference == "90后，深圳"


def test_turn_understanding_resolve_partner_requirement_text_disables_message_fallback_by_default():
    service = TurnUnderstandingService(_StubChatService())
    preference = service._resolve_partner_requirement_text(  # noqa: SLF001
        {},
        "温柔吧",
    )
    assert preference == ""


def test_turn_understanding_resolve_partner_requirement_text_allows_message_fallback_when_enabled():
    service = TurnUnderstandingService(_StubChatService())
    preference = service._resolve_partner_requirement_text(  # noqa: SLF001
        {},
        "温柔吧",
        allow_message_fallback=True,
    )
    assert preference == "温柔"


def test_turn_understanding_builds_opening_profile_ack_from_structured_partner_preference():
    service = TurnUnderstandingService(_StubChatService())
    service._extract_profile_fields = lambda text, last_response="": {  # noqa: SLF001
        "partner_pref_age": "90后",
        "partner_pref_location": "深圳",
    }
    ack = service._build_opening_profile_ack("90后都可以，最好深圳")  # noqa: SLF001
    assert ack == "你更偏向90后，深圳这类。"


def test_turn_understanding_builds_opening_profile_ack_ignores_partner_preference_education():
    service = TurnUnderstandingService(_StubChatService())
    ack = service._build_opening_profile_ack("93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员")  # noqa: SLF001
    assert "本科是吧" not in ack
    assert "学历这块是本科" not in ack


def test_turn_understanding_builds_lightweight_field_ack_for_location():
    service = TurnUnderstandingService(_StubChatService())
    response = service._build_lightweight_field_ack("深圳", None)  # noqa: SLF001
    assert "深圳" in response
    assert any(token in response for token in ["知道了", "是吧", "这边", "有数了", "现在主要在", "你现在在"])


def test_turn_understanding_builds_lightweight_field_ack_keeps_partner_requirement_short_answer_in_asked_context():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_pref_ack")
    profile.last_asked_field = "partner_requirement"
    response = service._build_lightweight_field_ack("温柔吧", profile)  # noqa: SLF001
    assert "温柔" in response


def test_turn_understanding_extracts_compound_sex_and_location_reply():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_deterministic_profile_fields("男的呢，在深圳")  # noqa: SLF001
    assert extracted["sex"] == "男"
    assert extracted["location"] == "深圳"


def test_turn_understanding_extracts_short_profile_answers():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("男的")  # noqa: SLF001
    assert extracted["sex"] == "男"

    extracted = service._extract_deterministic_profile_fields("深圳")  # noqa: SLF001
    assert extracted["location"] == "深圳"

    extracted = service._extract_deterministic_profile_fields("90后")  # noqa: SLF001
    assert extracted["age_label"] == "90后"
    assert int(extracted["age"]) >= 30

    extracted = service._extract_deterministic_profile_fields("我深圳的")  # noqa: SLF001
    assert extracted["location"] == "深圳"

    extracted = service._extract_deterministic_profile_fields("it")  # noqa: SLF001
    assert extracted["occupation"] == "IT"

    extracted = service._extract_deterministic_profile_fields("admin")  # noqa: SLF001
    assert extracted["occupation"] == "行政"

    extracted = service._extract_deterministic_profile_fields("本可")  # noqa: SLF001
    assert extracted["education"] == "本科"

    extracted = service._extract_deterministic_profile_fields("硕土")  # noqa: SLF001
    assert extracted["education"] == "硕士"

    extracted = service._extract_deterministic_profile_fields("专科")  # noqa: SLF001
    assert extracted["education"] == "大专"

    extracted = service._extract_deterministic_profile_fields("研一")  # noqa: SLF001
    assert extracted["education"] == "研究生"

    extracted = service._extract_deterministic_profile_fields("研二")  # noqa: SLF001
    assert extracted["education"] == "研究生"

    extracted = service._extract_deterministic_profile_fields("在读硕士")  # noqa: SLF001
    assert extracted["education"] == "硕士"

    extracted = service._extract_deterministic_profile_fields("博后")  # noqa: SLF001
    assert extracted["education"] == "博士"

    extracted = service._extract_deterministic_profile_fields("博士后")  # noqa: SLF001
    assert extracted["education"] == "博士"

    extracted = service._extract_deterministic_profile_fields("在读博")  # noqa: SLF001
    assert extracted["education"] == "博士"

    extracted = service._extract_deterministic_profile_fields("专升本")  # noqa: SLF001
    assert extracted["education"] == "本科"


def test_turn_understanding_extracts_occupation_and_preference_from_compound_reply():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("做it，看中对方温柔")  # noqa: SLF001

    assert extracted["occupation"] == "IT"
    assert extracted["partner_requirement"] == "温柔"


def test_turn_understanding_deterministic_partner_requirement_fallback_requires_preference_context():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("温柔吧")  # noqa: SLF001

    assert "partner_requirement" not in extracted


def test_turn_understanding_normalizes_beauty_occupation_with_trailing_particle():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("做美容吧，7万左右")  # noqa: SLF001

    assert extracted["occupation"] == "美容"
    assert extracted["monthly_income"] == "7万左右"


def test_turn_understanding_normalizes_noisy_beauty_occupation_prefix():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("做恶美容吧，7万左右")  # noqa: SLF001

    assert extracted["occupation"] == "美容"
    assert extracted["monthly_income"] == "7万左右"


def test_turn_understanding_normalizes_occupation_suffix_variants():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("做it的")  # noqa: SLF001
    assert extracted["occupation"] == "IT"

    extracted = service._extract_deterministic_profile_fields("产品这块")  # noqa: SLF001
    assert extracted["occupation"] == "产品"

    extracted = service._extract_deterministic_profile_fields("搞运营的")  # noqa: SLF001
    assert extracted["occupation"] == "运营"

    extracted = service._extract_deterministic_profile_fields("做医美这行")  # noqa: SLF001
    assert extracted["occupation"] == "医美"

    extracted = service._extract_deterministic_profile_fields("干hr")  # noqa: SLF001
    assert extracted["occupation"] == "HR"

    extracted = service._extract_deterministic_profile_fields("做qa测试")  # noqa: SLF001
    assert extracted["occupation"] == "QA"

    extracted = service._extract_deterministic_profile_fields("行政前台")  # noqa: SLF001
    assert extracted["occupation"] == "行政"

    extracted = service._extract_deterministic_profile_fields("hrbp")  # noqa: SLF001
    assert extracted["occupation"] == "HR"

    extracted = service._extract_deterministic_profile_fields("产品运营")  # noqa: SLF001
    assert extracted["occupation"] == "产品运营"

    extracted = service._extract_deterministic_profile_fields("电商运营")  # noqa: SLF001
    assert extracted["occupation"] == "电商运营"

    extracted = service._extract_deterministic_profile_fields("做ui设计")  # noqa: SLF001
    assert extracted["occupation"] == "UI"

    extracted = service._extract_deterministic_profile_fields("UI设计师")  # noqa: SLF001
    assert extracted["occupation"] == "UI"

    extracted = service._extract_deterministic_profile_fields("做qa测试工程师")  # noqa: SLF001
    assert extracted["occupation"] == "QA"

    extracted = service._extract_deterministic_profile_fields("行政人事")  # noqa: SLF001
    assert extracted["occupation"] == "行政"

    extracted = service._extract_deterministic_profile_fields("产品经理")  # noqa: SLF001
    assert extracted["occupation"] == "产品"

    extracted = service._extract_deterministic_profile_fields("运营助理")  # noqa: SLF001
    assert extracted["occupation"] == "运营"

    extracted = service._extract_deterministic_profile_fields("前端开发")  # noqa: SLF001
    assert extracted["occupation"] == "前端开发"

    extracted = service._extract_deterministic_profile_fields("前端工程师")  # noqa: SLF001
    assert extracted["occupation"] == "前端开发"

    extracted = service._extract_deterministic_profile_fields("后端开发")  # noqa: SLF001
    assert extracted["occupation"] == "后端开发"

    extracted = service._extract_deterministic_profile_fields("后端工程师")  # noqa: SLF001
    assert extracted["occupation"] == "后端开发"

    extracted = service._extract_deterministic_profile_fields("财会")  # noqa: SLF001
    assert extracted["occupation"] == "财务"

    extracted = service._extract_deterministic_profile_fields("医护")  # noqa: SLF001
    assert extracted["occupation"] == "医护"


def test_turn_understanding_extracts_short_occupation_answer_in_occupation_context():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_short_occupation")
    profile.last_asked_field = "occupation"

    result = service.analyze(_make_input("客服", last_response="你现在是做什么工作的呀？", user_profile=profile))

    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["occupation"] == "客服"


def test_turn_understanding_extracts_generic_location_short_reply():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("在南京呢")  # noqa: SLF001

    assert extracted["location"] == "南京"


def test_turn_understanding_extracts_non_whitelist_location_terms():
    service = TurnUnderstandingService(_StubChatService())

    assert service._extract_deterministic_profile_fields("在台湾呢")["location"] == "台湾"  # noqa: SLF001
    assert service._extract_deterministic_profile_fields("在老家呢")["location"] == "老家"  # noqa: SLF001


def test_turn_understanding_extracts_colloquial_divorce_variant():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(_make_input("离过"))

    assert result.resolved_slots["marital_status"] == "离异"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_does_not_treat_income_token_after_education_as_occupation():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("本科，8万")  # noqa: SLF001

    assert extracted["education"] == "本科"
    assert extracted["monthly_income"] == "8万"
    assert extracted.get("occupation") in (None, "")


def test_turn_understanding_does_not_parse_post_90_bucket_as_ninety_years_old():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("我90后，")  # noqa: SLF001

    assert extracted["age_label"] == "90后"
    assert int(extracted["age"]) < 60
    assert int(extracted["age"]) != 90


def test_turn_understanding_treats_bare_two_digit_age_token_as_specific_birth_year():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("90")  # noqa: SLF001

    assert extracted["age_label"] == "90年"
    assert int(extracted["age"]) < 60
    assert int(extracted["age"]) != 90


def test_turn_understanding_extracts_monthly_income():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_deterministic_profile_fields("收入大概1w左右")  # noqa: SLF001
    assert extracted["monthly_income"] == "1w左右"


def test_turn_understanding_preserves_wx_prefixed_wechat_id_candidate():
    service = TurnUnderstandingService(_StubChatService())
    candidate = service._extract_contact_candidate("wx23234242")  # noqa: SLF001
    assert candidate["type"] == "wechat"
    assert candidate["value"] == "wx23234242"


def test_turn_understanding_does_not_extract_age_from_wechat_id_message():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("wx235345345")  # noqa: SLF001

    assert "age" not in extracted
    assert "age_label" not in extracted


def test_turn_understanding_extracts_sex_and_occupation_from_confirmation_context_compound_reply():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input(
            "是女生，做it吧",
            last_response="想找男生的话我顺嘴确认下，你是女生对吧？在深圳发展的话，你目前是做什么工作的呀？",
            message_count=1,
        )
    )

    assert result.primary_turn_type == "profile_answer"
    assert result.subtype == "multi_slot_compound"
    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["occupation"] == "IT"


def test_turn_understanding_extracts_embedded_occupation_after_location_phrase():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input(
            "是女生呢，目前在深圳做it",
            last_response="你是女生对吧？在深圳发展的话，你目前是做什么工作的呀？",
            message_count=1,
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["occupation"] == "IT"


def test_turn_understanding_contact_flow_numeric_candidate_does_not_pollute_age():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input(
            "1879987654",
            last_response="在深圳做IT能有这个收入挺不错的呀，你方便给下你的电话号码不？",
            message_count=5,
            in_contact_flow=True,
        )
    )

    assert result.primary_turn_type == "contact_answer"
    assert "age" not in result.resolved_slots
    assert "age_label" not in result.resolved_slots


def test_turn_understanding_blocks_marital_status_like_occupation_in_compound_reply():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(_make_input("本科，单身呢"))

    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["marital_status"] == "单身"
    assert "occupation" not in result.resolved_slots
    assert "occupation" not in result.blocked_slots


def test_turn_understanding_explicit_correction_overrides_contact_context():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input(
            "不是本科，是大专",
            last_response="在深圳做IT能有这个收入挺不错的呀，你方便给下你的电话号码不？",
            message_count=5,
            in_contact_flow=True,
            user_profile=SimpleNamespace(education="本科"),
        )
    )

    assert result.primary_turn_type == "correction"
    assert result.resolved_slots["education"] == "大专"
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_blocks_partner_gender_preference_in_sex_confirmation_context():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input(
            "是女生",
            last_response="你是女生对吧？",
            message_count=2,
            pending_confirmation_field="sex",
        )
    )

    assert result.resolved_slots["sex"] == "女"
    assert "partner_gender_preference" not in result.resolved_slots
    assert "occupation" not in result.resolved_slots


def test_turn_understanding_extracts_simple_monthly_income_variants():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_monthly_income("我现在税前15k左右") == "税前15k左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("月薪 1.2w+") == "1.2w+"  # noqa: SLF001
    assert service._extract_simple_monthly_income("年包30左右") == "年包30左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("现在年薪税后大概20左右") == "年薪税后大概20左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("大概收入8k-12k") == "大概收入8k-12k"  # noqa: SLF001
    assert service._extract_simple_monthly_income("收入区间2万到3万") == "收入区间2万到3万"  # noqa: SLF001
    assert service._extract_simple_monthly_income("一年18-25左右") == "一年18-25左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("我自己收入不高一年18左右") == "一年18左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("一万出头") == "一万出头"  # noqa: SLF001
    assert service._extract_simple_monthly_income("两万上下") == "两万上下"  # noqa: SLF001


def test_turn_understanding_extracts_simple_monthly_income_without_weight_pollution():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_monthly_income("单身，90kg，身高198") is None  # noqa: SLF001
    assert service._extract_simple_monthly_income("体重90kg，月薪3万") == "3万"  # noqa: SLF001


def test_turn_understanding_prefers_monthly_income_context_over_age_like_number():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_income_ctx")
    profile.last_asked_field = "monthly_income"

    result = service.analyze(
        _make_input(
            "深圳南山呢，现在年薪税后大概20左右",
            last_response="那你现在常住在哪座城市呀？方便的话也可以说下大概的月收入哦。",
            user_profile=profile,
        )
    )

    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["monthly_income"] == "年薪税后大概20左右"
    assert "age" not in result.resolved_slots
    assert "partner_requirement" not in result.resolved_slots


def test_turn_understanding_binds_short_compound_reply_to_location_and_income_when_both_were_asked():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_location_income_ctx")
    profile.last_asked_field = "location"
    profile.last_asked_side_field = "monthly_income"

    result = service.analyze(
        _make_input(
            "深圳，20k+",
            last_response="那你现在常住在哪座城市呀？方便的话也可以说下大概的月收入哦。",
            user_profile=profile,
            message_count=3,
        )
    )

    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["monthly_income"] == "20k+"


def test_turn_understanding_extracts_contextual_income_short_answer_with_particle():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_income_short_particle")
    profile.last_asked_field = "monthly_income"

    result = service.analyze(
        _make_input(
            "20+啊",
            last_response="看你之前说做IT行业的，那你目前薪资大概是什么范围呀？",
            user_profile=profile,
            message_count=4,
        )
    )

    assert result.resolved_slots["monthly_income"] == "20+"
    assert "age" not in result.resolved_slots


def test_turn_understanding_extracts_contextual_income_range_short_answer():
    service = TurnUnderstandingService(_StubChatService())
    profile = UserProfile(account_id="u_income_range_short")
    profile.last_asked_field = "monthly_income"

    result = service.analyze(
        _make_input(
            "2万到3万",
            last_response="我再轻问一句，你收入大概在哪个区间？",
            user_profile=profile,
            message_count=4,
        )
    )

    assert result.resolved_slots["monthly_income"] == "2万到3万"
    assert "age" not in result.resolved_slots


def test_turn_understanding_does_not_write_partner_income_requirement_to_self_income():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input("想找月入2w+的男生", message_count=2)
    )

    assert "monthly_income" not in result.resolved_slots
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "收入2万以上"


def test_turn_understanding_keeps_self_income_in_mixed_intro_with_partner_income_preference():
    service = TurnUnderstandingService(_StubChatService())

    result = service.analyze(
        _make_input("我月入20k+，想找月入2w+的男生", message_count=2)
    )

    assert result.resolved_slots["monthly_income"] == "20k+"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["partner_requirement"] == "收入2万以上"


def test_turn_understanding_extracts_simple_partner_requirement_from_oral_reply():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("温柔就行了") == "温柔"  # noqa: SLF001


def test_turn_understanding_extracts_simple_partner_requirement_from_modal_particle_reply():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("温柔吧") == "温柔"  # noqa: SLF001


def test_turn_understanding_extracts_rich_partner_requirement_with_age_bucket():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement("90后，看重稳重，成熟，身高要180以上，然后多金")  # noqa: SLF001

    assert extracted is not None
    assert "90后" in extracted
    assert ("身高180cm以上" in extracted) or ("身高至少180" in extracted)
    assert "多金" in extracted
    assert "成熟稳重" in extracted


def test_turn_understanding_extracts_numeric_height_preference_from_short_reply():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("180吧") == "身高180cm"  # noqa: SLF001
    assert service._extract_simple_partner_requirement("175以上") == "身高175cm以上"  # noqa: SLF001


def test_turn_understanding_extracts_simple_partner_requirement_from_polluted_short_answer():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("本科，我温柔 点") == "温柔"  # noqa: SLF001


def test_turn_understanding_extracts_composite_partner_requirement_from_matchmaking_opening():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_simple_partner_requirement(
        "深圳有不 想了解看看96年能接受4岁上下年龄差，喜欢笑就更好了卡身高174+最好不要同财务行业 自己跟跟倾向于稳定行业男生可以匹配不"
    )  # noqa: SLF001

    assert extracted == "年龄上下4岁，爱笑，身高至少174，不要同财务行业，稳定行业"


def test_turn_understanding_guard_blocks_age_pollution_in_partner_requirement_height_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"age": "18"},
        "180吧",
        last_response="嗯呐，那你希望对方的身高大概在什么范围呀？",
    )
    assert guarded["partner_requirement"] == "身高180cm"
    assert "age" not in guarded
    assert "age_label" not in guarded


def test_turn_understanding_guard_blocks_age_pollution_in_income_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"age": "20"},
        "我月薪20万",
        last_response="你现在月收入大概在哪个区间呀？",
    )
    assert "age" not in guarded


def test_turn_understanding_guard_keeps_income_in_income_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"monthly_income": "2万"},
        "我月薪2万",
        last_response="你现在月收入大概在哪个区间呀？",
    )
    assert guarded["monthly_income"] == "2万"


def test_turn_understanding_analyze_treats_numeric_height_reply_as_partner_requirement_not_age():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "180吧",
            last_response="嗯呐，那你希望对方的身高大概在什么范围呀？",
            message_count=8,
        )
    )
    assert result.resolved_slots["partner_requirement"] == "身高180cm"
    assert "age" not in result.resolved_slots
    assert "age_label" not in result.resolved_slots


def test_turn_understanding_guard_prioritizes_sex_answer_in_sex_question_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"partner_gender_preference": "男"},
        "你们男的",
        last_response="你是男生还是女生呀？",
    )
    assert guarded.get("sex") == "男"
    assert "partner_gender_preference" not in guarded


def test_turn_understanding_guard_allows_composite_sex_short_answer_in_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"sex": "男", "marital_status": "单身"},
        "男的，是的，单身",
        last_response="你这边是男生还是女生呀？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？",
    )
    assert guarded["sex"] == "男"


def test_turn_understanding_guard_allows_trailing_punct_sex_short_answer_in_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"sex": "男"},
        "男的，",
        last_response="我顺手确认下，你这边是男生还是女生呀？",
    )
    assert guarded["sex"] == "男"


def test_turn_understanding_guard_allows_affirmative_confirmation_to_confirm_sex():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"sex": "男"},
        "是的",
        last_response="我再确认下，你这边是男生对吧？",
    )
    assert guarded["sex"] == "男"


def test_turn_understanding_guard_treats_soft_gender_guess_as_sex_confirmation_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"age": "37", "age_label": "89年", "partner_gender_preference": "女"},
        "是的呢女生，89年的",
        last_response="想找合适的男生对吧，我先记下来啦~你应该是女孩子吧？对啦你具体是80几年出生的呀？",
    )
    assert guarded["sex"] == "女"
    assert guarded["age_label"] == "89年"
    assert "partner_gender_preference" not in guarded


def test_turn_understanding_extract_partner_gender_preference_ignores_self_sex_statement():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_partner_gender_preference("是的呢女生，89年的") is None  # noqa: SLF001
    assert service._extract_partner_gender_preference("前面不是说了是女生吗？") is None  # noqa: SLF001
    assert service._extract_partner_gender_preference("找男朋友，我80后呢") == "男"  # noqa: SLF001


def test_turn_understanding_guard_resolves_birth_year_short_answer_in_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {},
        "98的",
        last_response="90后跨度还挺大的呢，具体是九几年出生的呀？",
    )
    assert guarded["age_label"] == "98年"
    assert guarded["age"].isdigit()


def test_turn_understanding_guard_resolves_birth_year_and_marital_status_compound_answer_in_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"marital_status": "离异"},
        "98的，离异",
        last_response="哈哈我知道是90后，具体是90几年出生的呀？",
    )
    assert guarded["age_label"] == "98年"
    assert guarded["marital_status"] == "离异"


def test_turn_understanding_prefers_self_birth_year_and_partner_age_preference_in_same_message():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("95想找90后都可以有不", message_count=3))

    assert result.resolved_slots["age_label"] == "95年"
    assert result.resolved_slots["age"].isdigit()
    assert "90后" in str(result.resolved_slots.get("partner_requirement") or "")


def test_turn_understanding_splits_self_birth_year_and_partner_age_bucket_in_opening_intro():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("96年女生找男朋友，目前在深圳单身未婚，本科学历，与收入1万左右，找90后", message_count=1)
    )

    assert result.resolved_slots["sex"] == "女"
    assert result.resolved_slots["location"] == "深圳"
    assert result.resolved_slots["education"] == "本科"
    assert result.resolved_slots["marital_status"] in {"单身", "未婚", "单身未婚"}
    assert result.resolved_slots["monthly_income"] == "1万左右"
    assert result.resolved_slots["partner_gender_preference"] == "男"
    assert result.resolved_slots["age_label"] == "96年"
    assert result.resolved_slots["age"] == str(datetime.now().year - 1996)
    assert "90后" in str(result.resolved_slots.get("partner_requirement") or "")


def test_turn_understanding_occupation_short_answer_under_context_accepts_clean_industry_token():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {},
        "新能源",
        last_response="原来是本科呀，那你现在做什么工作的呀？",
    )

    assert guarded["occupation"] == "新能源"


def test_turn_understanding_extracts_occupation_and_income_from_compound_followup_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "新能源，年薪大概20+",
            message_count=3,
            last_response="有的哦，我们平台也有不少在香港工作生活的优质单身资源~ 对啦，你现在是做哪方面工作的呀，大概收入在什么区间呢？",
        )
    )

    assert result.resolved_slots["occupation"] == "新能源"
    assert "20" in str(result.resolved_slots["monthly_income"])
    assert result.subtype == "multi_slot_compound"


def test_turn_understanding_normalizes_asr_noisy_occupation_prefix_in_compound_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "是u做新能源，年薪大概20+",
            message_count=3,
            last_response="挺好的呀，那你现在是做什么工作的，月收入大概在什么区间呢？",
        )
    )

    assert result.resolved_slots["occupation"] == "新能源"
    assert "20" in str(result.resolved_slots["monthly_income"])


def test_turn_understanding_does_not_treat_medical_industry_intro_as_risk_guard():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input("90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地", message_count=1)
    )

    assert result.primary_turn_type == "profile_answer"
    assert result.subtype in {"multi_slot_compound", "single_slot_answer"}


def test_turn_understanding_extracts_nurse_as_occupation_in_compact_self_intro():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_deterministic_profile_fields(  # noqa: SLF001
        "90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地"
    )

    assert extracted["occupation"] == "护士"
    assert extracted["age_label"] == "90年"
    assert extracted["partner_requirement"] == "同医疗体系，同在深圳发展，本地优先，比自己大"


def test_turn_understanding_generalizes_compact_self_intro_with_preference_variants():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_deterministic_profile_fields(  # noqa: SLF001
        "91 老师 硕士 想找体制内本地 年纪大点也行"
    )

    assert extracted["occupation"] == "老师"
    assert extracted["age_label"] == "91年"


def test_turn_understanding_guard_skips_birth_year_extraction_when_user_refuses_specific_year():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"age": "90", "age_label": "90年"},
        "不方便说",
        last_response="好哒，那你是几几年的呀？",
    )
    assert "age" not in guarded
    assert "age_label" not in guarded


def test_turn_understanding_analyze_treats_birth_year_refusal_as_soft_refusal_not_age_answer():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "不方便说",
            last_response="好哒，那你是几几年的呀？",
            message_count=2,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert "age" not in result.resolved_slots
    assert "age_label" not in result.resolved_slots
    assert result.soft_retry_field == "age"


def test_turn_understanding_analyze_treats_dual_field_refusal_as_core_soft_refusal_without_pollution():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(
        _make_input(
            "不方便说",
            last_response="你最高学历是什么呀，现在是单身状态不？",
            message_count=5,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "education"
    assert "education" not in result.resolved_slots
    assert "marital_status" not in result.resolved_slots


def test_turn_understanding_prefers_last_asked_field_for_core_soft_refusal():
    service = TurnUnderstandingService(_StubChatService())
    profile = SimpleNamespace(last_asked_field="education")
    result = service.analyze(
        TurnUnderstandingInput(
            user_message="不方便说",
            last_response="做IT还挺厉害的，这个收入很不错呀，你是什么学历呀？",
            message_count=6,
            user_profile=profile,
            conversation_context={},
            in_contact_flow=False,
            pending_confirmation_field=None,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "education"


def test_turn_understanding_uses_recent_response_fallback_for_location_soft_refusal():
    service = TurnUnderstandingService(_StubChatService())
    profile = SimpleNamespace(last_asked_field=None)
    result = service.analyze(
        TurnUnderstandingInput(
            user_message="不方便说",
            last_response="",
            message_count=7,
            user_profile=profile,
            conversation_context={"recent_responses": ["好的，那你现在常住在哪座城市呀？"]},
            in_contact_flow=False,
            pending_confirmation_field=None,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "location"


def test_turn_understanding_uses_recent_response_fallback_for_monthly_income_soft_refusal():
    service = TurnUnderstandingService(_StubChatService())
    profile = SimpleNamespace(last_asked_field=None)
    result = service.analyze(
        TurnUnderstandingInput(
            user_message="不方便说",
            last_response="",
            message_count=7,
            user_profile=profile,
            conversation_context={"recent_responses": ["你现在月收入大概在什么区间呢？"]},
            in_contact_flow=False,
            pending_confirmation_field=None,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "monthly_income"


def test_turn_understanding_uses_recent_response_fallback_for_partner_requirement_soft_refusal():
    service = TurnUnderstandingService(_StubChatService())
    profile = SimpleNamespace(last_asked_field=None)
    result = service.analyze(
        TurnUnderstandingInput(
            user_message="不方便说",
            last_response="",
            message_count=7,
            user_profile=profile,
            conversation_context={"recent_responses": ["那你找对象的时候更看重对方哪一点呀？"]},
            in_contact_flow=False,
            pending_confirmation_field=None,
        )
    )
    assert result.primary_turn_type == "invalid_input"
    assert result.subtype == "soft_refusal_current_field"
    assert result.soft_retry_field == "partner_requirement"


def test_user_profile_serialization_preserves_last_asked_and_pending_retry_state():
    profile = UserProfile(account_id="u_persist_last_asked")
    profile.set_last_asked_field("education", 6, side_field="marital_status")
    profile.set_pending_retry_field("education")

    restored = UserProfile.from_dict(profile.to_dict())

    assert restored.last_asked_field == "education"
    assert restored.last_asked_side_field == "marital_status"
    assert restored.last_asked_turn_index == 6
    assert restored.pending_retry_field == "education"


def test_turn_understanding_guard_binds_affirmative_prefix_to_confirmed_sex_with_marital_answer():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"marital_status": "单身"},
        "是的，单身",
        last_response="我这边确认一下，你这边是男生？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？",
    )
    assert guarded["sex"] == "男"
    assert guarded["marital_status"] == "单身"
