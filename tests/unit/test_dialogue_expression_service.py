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


def test_render_field_question_for_marital_status_only_confirms_single_status():
    service = DialogueExpressionService()

    response = service.render_field_question("marital_status")

    assert "单身状态" in response
    assert "未婚" not in response
    assert "离异" not in response


def test_main_prompt_allows_low_frequency_reason_for_sensitive_fields():
    from src.services.prompts.prompts import get_main_dialogue

    prompt = get_main_dialogue(
        collected_info="性别:男",
        missing_fields="学历、收入、婚况",
        gender_instruction="正常称呼即可",
        is_first_chat=False,
        current_main_target="学历",
        current_side_target="无",
        can_enter_contact=False,
    )

    assert "稍敏感的问题" in prompt
    assert "偶尔补半句简短解释" in prompt
