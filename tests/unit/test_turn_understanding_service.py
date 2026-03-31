from __future__ import annotations

import re
from types import SimpleNamespace

from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingInput
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService


class _StubChatService:
    def __init__(self):
        self.user_question_service = SimpleNamespace(
            detect_quick_faq_intent=lambda message: "fee" if "收费" in str(message or "") else None
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
        if "本科" in text:
            extracted["education"] = "本科"
            extracted.setdefault("partner_requirement", "本科")
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


def _make_input(message: str, *, last_response: str = "", message_count: int = 0, in_contact_flow: bool = False):
    return TurnUnderstandingInput(
        user_message=message,
        last_response=last_response,
        message_count=message_count,
        user_profile=SimpleNamespace(),
        conversation_context={"recent_responses": [last_response] if last_response else []},
        in_contact_flow=in_contact_flow,
        pending_confirmation_field=None,
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
    assert result.resolved_slots["age"] == "36"


def test_turn_understanding_extracts_married_status_from_natural_phrase():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("我已经结婚了"))
    assert result.primary_turn_type == "profile_answer"
    assert result.resolved_slots["marital_status"] == "已婚"


def test_turn_understanding_classifies_opening_service_confirmation():
    service = TurnUnderstandingService(_StubChatService())
    result = service.analyze(_make_input("你们帮帮忙介绍对象吗？"))
    assert result.primary_turn_type == "opening"
    assert result.subtype == "service_confirmation_opening"


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
    assert service._build_opening_profile_ack("本科") == "学历是本科。"  # noqa: SLF001


def test_turn_understanding_builds_lightweight_field_ack_for_location():
    service = TurnUnderstandingService(_StubChatService())
    response = service._build_lightweight_field_ack("深圳", None)  # noqa: SLF001
    assert "深圳" in response
    assert any(token in response for token in ["知道了", "是吧", "这边", "有数了", "现在主要在"])


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


def test_turn_understanding_extracts_occupation_and_preference_from_compound_reply():
    service = TurnUnderstandingService(_StubChatService())

    extracted = service._extract_deterministic_profile_fields("做it，看中对方温柔")  # noqa: SLF001

    assert extracted["occupation"] == "IT"
    assert extracted["partner_requirement"] == "温柔"


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


def test_turn_understanding_extracts_monthly_income():
    service = TurnUnderstandingService(_StubChatService())
    extracted = service._extract_deterministic_profile_fields("收入大概1w左右")  # noqa: SLF001
    assert extracted["monthly_income"] == "1w左右"


def test_turn_understanding_preserves_wx_prefixed_wechat_id_candidate():
    service = TurnUnderstandingService(_StubChatService())
    candidate = service._extract_contact_candidate("wx23234242")  # noqa: SLF001
    assert candidate["type"] == "wechat"
    assert candidate["value"] == "wx23234242"


def test_turn_understanding_extracts_simple_monthly_income_variants():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_monthly_income("我现在税前15k左右") == "税前15k左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("月薪 1.2w+") == "1.2w+"  # noqa: SLF001
    assert service._extract_simple_monthly_income("年包30左右") == "年包30左右"  # noqa: SLF001
    assert service._extract_simple_monthly_income("一万出头") == "一万出头"  # noqa: SLF001
    assert service._extract_simple_monthly_income("两万上下") == "两万上下"  # noqa: SLF001


def test_turn_understanding_extracts_simple_monthly_income_without_weight_pollution():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_monthly_income("单身，90kg，身高198") is None  # noqa: SLF001
    assert service._extract_simple_monthly_income("体重90kg，月薪3万") == "3万"  # noqa: SLF001


def test_turn_understanding_extracts_simple_partner_requirement_from_oral_reply():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("温柔就行了") == "温柔"  # noqa: SLF001


def test_turn_understanding_extracts_simple_partner_requirement_from_modal_particle_reply():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("温柔吧") == "温柔"  # noqa: SLF001


def test_turn_understanding_extracts_simple_partner_requirement_from_polluted_short_answer():
    service = TurnUnderstandingService(_StubChatService())
    assert service._extract_simple_partner_requirement("本科，我温柔 点") == "温柔"  # noqa: SLF001


def test_turn_understanding_guard_prioritizes_sex_answer_in_sex_question_context():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"partner_requirement": "找男性"},
        "你们男的",
        last_response="你是男生还是女生呀？",
    )
    assert guarded.get("sex") == "男"
    assert "partner_requirement" not in guarded


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


def test_turn_understanding_guard_binds_affirmative_prefix_to_confirmed_sex_with_marital_answer():
    service = TurnUnderstandingService(_StubChatService())
    guarded = service._apply_extraction_guards(  # noqa: SLF001
        {"marital_status": "单身"},
        "是的，单身",
        last_response="我这边确认一下，你这边是男生？ 感情状态这边我也顺手确认一下，你现在是单身状态吗？",
    )
    assert guarded["sex"] == "男"
    assert guarded["marital_status"] == "单身"
