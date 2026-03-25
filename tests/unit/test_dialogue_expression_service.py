from src.models.user_profile import UserProfile
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService


def test_render_field_question_for_education_is_natural():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_edu")

    response = service.render_field_question("education", profile=profile, stage="trust")

    assert "学历" in response
    assert "平时你是什么学历背景" not in response


def test_render_field_question_for_contact_is_short_and_natural():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_contact")

    response = service.render_field_question("contact", profile=profile, stage="completing")

    assert "手机号" in response
    assert "方便联系" in response
    assert "资料差不多" not in response
    assert "及时联系" not in response


def test_render_field_question_for_education_can_follow_short_answer_naturally():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_followup")

    response = service.render_field_question(
        "education",
        profile=profile,
        stage="trust",
        user_message="深圳",
    )

    assert "学历" in response
    assert response.startswith(("那，", "对了，", "顺着聊到这儿，", "方便的话，"))


def test_render_contact_question_can_follow_short_answer_naturally():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_follow_contact")

    response = service.render_contact_question(
        profile=profile,
        stage="completing",
        user_message="it",
    )

    assert "手机号" in response
    assert "方便联系" in response
