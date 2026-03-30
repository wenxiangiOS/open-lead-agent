from src.models.user_profile import UserProfile
from src.services.core.chat_service import ChatService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), object())


def test_build_interleaving_followup_combines_main_and_income_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_income")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    for field in ["sex", "age", "location", "education"]:
        profile.collection_progress[field] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "本科",
        main_target="occupation",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "工作" in response or "做什么" in response
    assert "月收入" in response or "收入" in response


def test_build_interleaving_followup_prefers_bridge_mode_over_generic_income_fusion():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_bridge_income")

    response = chat_service._build_interleaving_followup(
        profile,
        "我目前在深圳呢，目前单身",
        main_target="occupation",
        preferred_side_target="monthly_income",
        allow_medium_target=True,
    )

    assert "工作" in response or "做什么" in response
    assert "收入" in response or "月薪" in response


def test_build_interleaving_followup_combines_main_and_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_partner")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    for field in ["sex", "age", "location"]:
        profile.collection_progress[field] = True

    response = chat_service._build_interleaving_followup(
        profile,
        "深圳",
        main_target="education",
        preferred_side_target="partner_requirement",
        allow_medium_target=True,
    )

    assert "学历" in response
    assert "找对象" in response or "看重" in response or "在意" in response


def test_build_interleaving_followup_does_not_use_collected_age_as_host_for_partner_requirement():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_interleave_partner_requirement")
    profile.education = "本科"
    profile.age = 29
    profile.sex = "男"
    profile.marital_status = "单身"
    profile.collection_progress["education"] = True
    profile.collection_progress["age"] = True
    profile.collection_progress["sex"] = True
    profile.collection_progress["marital_status"] = True

    rendered = chat_service._build_interleaving_followup(
        profile,
        "男的，单身",
        main_target="age",
        preferred_side_target="partner_requirement",
    )

    assert "年龄段" not in rendered
    assert "多大" not in rendered
    assert any(token in rendered for token in ("另一半", "想找", "看重", "在意"))


def test_ensure_short_answer_ack_transition_prefixes_ack_before_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_short_answer_bridge")

    response = chat_service._ensure_short_answer_ack_transition(
        "你大概是什么学历呀？",
        user_message="深圳",
        user_profile=profile,
    )

    assert response.startswith(("深圳呀", "在深圳", "深圳我"))
    assert "学历" in response


def test_ensure_short_answer_ack_transition_does_not_double_ack_when_model_already_confirmed_field():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_short_answer_bridge_existing_ack")

    response = chat_service._ensure_short_answer_ack_transition(
        "好的，你是男生啦。 你今年多大呀？",
        user_message="男的",
        user_profile=profile,
    )

    assert response == "好的，你是男生啦。 你今年多大呀？"


def test_append_safe_short_answer_followup_continues_to_next_core_field_after_sex_answer():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_safe_short_followup")
    profile.sex = "男"
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.monthly_income = "6万"
    profile.collection_progress.update(
        {
            "sex": True,
            "location": True,
            "education": True,
            "occupation": True,
            "monthly_income": True,
        }
    )

    response = chat_service._append_safe_short_answer_followup(
        "好，你是男生啦。",
        profile,
        {"all_fields": [{"field": "sex", "value": "男"}]},
        previous_asked_field="sex",
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        ask_field=None,
        followup_topic=None,
    )

    assert "男生" in response
    assert "多大" in response or "年龄" in response


def test_append_safe_short_answer_followup_skips_special_scenarios():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_safe_short_followup_guard")
    profile.sex = "男"
    profile.collection_progress["sex"] = True
    profile.marital_status = "离异"
    profile.divorce_confirmation_pending = True

    response = chat_service._append_safe_short_answer_followup(
        "好，你是男生啦。",
        profile,
        {"all_fields": [{"field": "sex", "value": "男"}]},
        previous_asked_field="sex",
        user_message="男的",
        response_channel="model",
        primary_move="light_followup",
        ask_field=None,
        followup_topic=None,
    )

    assert response == "好，你是男生啦。"


def test_prepend_multi_field_ack_transition_bridges_before_next_core_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_multi_field_ack")
    profile.location = "深圳"
    profile.occupation = "IT"
    profile.marital_status = "单身"
    profile.collection_progress.update({"location": True, "occupation": True, "marital_status": True})

    response = chat_service._prepend_multi_field_ack_transition(
        "你今年大概多大呀？ 这样我心里会更有数一点。",
        profile,
        {
            "all_fields": [
                {"field": "location", "value": "深圳"},
                {"field": "occupation", "value": "IT"},
                {"field": "marital_status", "value": "单身"},
            ]
        },
        user_message="目前在深圳，单身，做it",
        response_channel="model",
        primary_move="ack_and_ask",
        ask_field="age",
        followup_topic=None,
    )

    assert "多大" in response
    assert response.startswith(("做IT", "好，IT这块", "IT方向", "IT这行我接住了", "IT这行我有数了", "现在主要做IT这块", "你现在主要做IT", "在深圳", "深圳呀", "好，现在单身状态"))
    assert "更有数一点" not in response


def test_build_contextual_short_ack_avoids_recent_opening_repeat_for_occupation():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_recent_opening_ack")
    profile.recent_response_openings = ["做IT是吧"]

    ack = chat_service._build_contextual_short_ack("occupation", "IT", profile)

    assert ack != "做IT是吧。"


def test_prepend_single_field_ack_transition_bridges_short_answer_before_next_question():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_single_field_ack")
    profile.education = "本科"
    profile.collection_progress["education"] = True

    response = chat_service._prepend_single_field_ack_transition(
        "我先简单了解下，你这边是男生还是女生呀？",
        profile,
        {"all_fields": [{"field": "education", "value": "本科"}]},
        user_message="本科",
        response_channel="model",
        primary_move="light_followup",
        ask_field="sex",
        followup_topic=None,
    )

    assert "男生还是女生" in response
    assert response == "我先简单了解下，你这边是男生还是女生呀？"


def test_prepend_single_field_ack_transition_skips_when_model_already_acked_location():
    chat_service = _build_chat_service()
    profile = UserProfile(account_id="u_single_field_ack_existing_location")
    profile.location = "深圳"
    profile.collection_progress["location"] = True

    response = chat_service._prepend_single_field_ack_transition(
        "在深圳这边是吧。 你目前是做哪方面工作的？",
        profile,
        {"all_fields": [{"field": "location", "value": "深圳"}]},
        user_message="深圳",
        response_channel="model",
        primary_move="light_followup",
        ask_field="occupation",
        followup_topic=None,
    )

    assert response == "在深圳这边是吧。 你目前是做哪方面工作的？"
