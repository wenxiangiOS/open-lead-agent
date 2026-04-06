from src.models.user_profile import UserProfile
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService


def test_render_field_question_uses_profile_location_for_bridged_occupation_prompt():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_bridge_location")
    profile.location = "深圳"

    response = service.render_field_question("occupation", profile=profile, stage="opening", user_message="嗯")

    assert "深圳" in response
    assert any(token in response for token in ("工作", "做什么"))


def test_render_field_question_does_not_bridge_age_when_age_already_collected():
    expr = DialogueExpressionService()
    profile = UserProfile(account_id="u_age_bridge_guard")
    profile.education = "本科"
    profile.age = 29
    profile.collection_progress["education"] = True
    profile.collection_progress["age"] = True

    rendered = expr.render_field_question("age", profile=profile, user_message="本科")

    assert "本科" not in rendered
    assert "29岁" not in rendered
    assert "婚况" in rendered or "感情状态" in rendered


def test_render_field_question_uses_mid_conversation_sex_prompt_without_opening_phrase():
    service = DialogueExpressionService()

    response = service.render_field_question("sex", stage="completing", user_message="本科")

    assert "男生还是女生" in response
    assert "我先简单了解下" not in response
    assert "我先认识你一下" not in response


def test_dialogue_expression_service_avoids_duplicate_location_prefix():
    service = DialogueExpressionService()

    response = service.render_field_question("location", user_message="90后")

    assert "你现在，你现在" not in response
    assert "平时的话" not in response
