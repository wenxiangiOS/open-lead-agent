from unittest.mock import AsyncMock

from src.models.user_profile import UserProfile
from src.services.core.dialogue_manager import DialogueManager


def test_build_main_dialogue_prompt_respects_primary_move_light_followup():
    user_service = AsyncMock()
    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_move")

    prompt = manager.build_main_dialogue_prompt(
        "男的",
        profile,
        {"message_count": 1, "recent_responses": []},
        primary_move="light_followup",
    )

    assert "这轮用轻量承接推进一小步" in prompt
    assert "句子尽量短，别像登记表" in prompt


def test_build_main_dialogue_prompt_blocks_contact_instruction_when_contact_target_disallowed():
    user_service = AsyncMock()
    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_no_contact")
    profile.sex = "男"
    profile.age = 36
    profile.location = "深圳"
    profile.education = "本科"
    profile.occupation = "IT"
    profile.marital_status = "离异（手续已办妥）"
    for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
        profile.collection_progress[field] = True

    prompt = manager.build_main_dialogue_prompt(
        "你不问其他了？",
        profile,
        {"message_count": 8, "recent_responses": []},
        primary_move="light_followup",
        allow_contact_target=False,
    )

    assert "不要索要电话或微信" not in prompt
    assert "当前不要主动切到电话或微信" in prompt
    assert "主目标=联系方式" not in prompt


def test_build_main_dialogue_prompt_includes_recent_style_avoidance():
    user_service = AsyncMock()
    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_style")
    context = {
        "message_count": 1,
        "recent_responses": ["你好呀～对了，想问下你是男生还是女生呀？"],
        "preferences": {"recent_prompt_signatures": ["你好呀|对了|想问下|sex"]},
    }

    prompt = manager.build_main_dialogue_prompt(
        "男的",
        profile,
        context,
        primary_move="light_followup",
        allow_contact_target=False,
        allow_medium_target=False,
    )

    assert "最近两轮你说过" in prompt
    assert "不要沿用同样开头" in prompt
    assert "不要并列枚举未婚和离异" in prompt


def test_build_main_dialogue_prompt_can_skip_generation_extract():
    user_service = AsyncMock()
    manager = DialogueManager(user_service)
    profile = UserProfile(account_id="u_prompt_no_extract")

    prompt = manager.build_main_dialogue_prompt(
        "怎么收费",
        profile,
        {"message_count": 1, "recent_responses": []},
        prioritize_user_question=True,
        include_extraction_prompt=False,
    )

    assert "<extract>" not in prompt
    assert "回复后必须附加" not in prompt
