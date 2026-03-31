from src.models.user_profile import UserProfile
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService


def test_render_field_question_for_education_is_natural():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_edu")

    response = service.render_field_question("education", profile=profile, stage="trust")

    assert "学历" in response
    assert "平时你是什么学历背景" not in response


def test_render_field_question_for_sex_is_not_overly_hard_on_opening():
    service = DialogueExpressionService()

    response = service.render_field_question("sex", user_message="你好")

    assert "男生还是女生" in response
    assert all(token not in response for token in ["最基础", "先简单认识下"])
    assert "先随便聊聊" not in response
    assert any(token in response for token in ["在呢", "你好呀", "在的"])


def test_render_field_question_for_sex_can_offer_open_self_intro_after_matchmaking_intent():
    service = DialogueExpressionService()

    response = service.render_field_question("sex", user_message="找对象")

    assert "介绍下自己" in response or "简单说说自己" in response
    assert "男生还是女生" in response


def test_render_field_question_for_contact_is_short_and_natural():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_contact")

    response = service.render_field_question("contact", profile=profile, stage="completing")

    assert "手机号" in response
    assert any(token in response for token in ["继续联系上你", "联系你会顺一点", "再跟你接着聊"])
    assert "资料差不多" not in response
    assert "及时联系" not in response


def test_render_field_question_for_contact_can_reuse_location_and_occupation_context():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_contact_context")
    profile.location = "深圳"
    profile.occupation = "IT"

    response = service.render_field_question("contact", profile=profile, stage="completing")

    assert "手机号" in response
    assert "深圳" in response
    assert "IT" in response
    assert "资料差不多" not in response


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
    assert response.startswith(("好呀，", "那我再了解下，", "顺着聊到这儿，"))


def test_render_field_question_for_occupation_can_follow_location_context_naturally():
    service = DialogueExpressionService()

    response = service.render_field_question("occupation", user_message="在深圳")

    assert "深圳" in response
    assert "工作" in response or "做什么" in response


def test_render_field_question_for_age_can_optionally_add_light_reason():
    service = DialogueExpressionService()

    first = service.render_field_question("age")

    assert "多大" in first or "年龄段" in first
    assert any(token in first for token in ["接话会更顺", "顺着往下聊"])


def test_render_field_question_for_age_bridge_avoids_flat_i_know_wording():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_bridge_age")
    profile.education = "博士"

    response = service.render_field_question("age", profile=profile, stage="trust")

    assert "博士" in response
    assert "什么年龄段" in response or "多大" in response
    assert "这边我知道了" not in response
    assert "年龄这块" not in response


def test_render_field_question_for_age_bridge_avoids_recent_opening_repeat():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_bridge_age_recent")
    profile.education = "博士"
    profile.recent_response_openings = ["博士是吧那你现在大概"]

    response = service.render_field_question("age", profile=profile, stage="trust")

    assert not response.startswith("博士是吧")


def test_render_field_question_for_location_can_optionally_add_same_city_reason():
    service = DialogueExpressionService()

    first = service.render_field_question("location")

    assert "城市" in first or "哪边生活" in first
    assert any(token in first for token in ["同城", "先看同城"])


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
    assert "我大概了解得差不多了" not in response
    assert "这样的话" not in response


def test_render_field_question_for_partner_requirement_uses_more_natural_preference_wording():
    service = DialogueExpressionService()

    response = service.render_field_question("partner_requirement")

    assert "看重" in response
    assert "哪方面" in response


def test_render_field_question_for_sex_uses_soft_confirmation_when_preference_strongly_implies_gender():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_sex_soft_confirm")
    profile.partner_requirement = "温柔，文静，身材苗条，身高不低于160，漂亮点"

    response = service.render_field_question("sex", profile=profile, stage="trust", user_message="温柔点")

    assert "男生还是女生" not in response
    assert "男生" in response
    assert any(token in response for token in ("对吧", "是吧"))
    assert "我理解得没偏" not in response


def test_render_field_question_for_sex_keeps_neutral_question_when_only_single_weak_height_cue():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_sex_weak_height")
    profile.partner_requirement = "至少180"

    response = service.render_field_question("sex", profile=profile, stage="trust", user_message="至少180")

    assert "男生还是女生" in response


def test_render_field_question_for_sex_handles_user_challenge_with_text_chat_style():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_sex_challenge")
    profile.partner_requirement = "温柔，文静，苗条"

    response = service.render_field_question(
        "sex",
        profile=profile,
        stage="trust",
        user_message="我这要求你还看不出来吗？",
    )

    assert "看出来" in response
    assert "听出来" not in response
    assert "男生" in response
    assert "男生还是女生" not in response
    assert "我理解得没偏" not in response


def test_render_field_question_for_marital_status_only_confirms_single_status():
    service = DialogueExpressionService()

    response = service.render_field_question("marital_status")

    assert "单身状态" in response
    assert "未婚" not in response
    assert "离异" not in response


def test_render_field_question_for_marital_status_bridge_avoids_awkward_status_inquire_copy():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_bridge_marital")
    profile.age_label = "90后"

    response = service.render_field_question("marital_status", profile=profile, stage="trust")

    assert "单身状态在了解吗" not in response
    assert "我先记下了" not in response
    assert "单身吗" in response


def test_render_field_question_for_partner_requirement_bridge_avoids_status_broadcast_copy():
    service = DialogueExpressionService()
    profile = UserProfile(account_id="u_expr_bridge_partner_requirement")
    profile.marital_status = "单身"

    response = service.render_field_question("partner_requirement", profile=profile, stage="trust")

    assert any(token in response for token in ("看重", "要求", "在意"))
    assert "状态是吧" not in response
    assert "这个状态" not in response


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


def test_main_prompt_mentions_low_frequency_reason_for_age_and_location():
    from src.services.prompts.prompts import get_main_dialogue

    prompt = get_main_dialogue(
        collected_info="性别:男",
        missing_fields="年龄、所在地",
        gender_instruction="正常称呼即可",
        is_first_chat=False,
        current_main_target="年龄",
        current_side_target="无",
        can_enter_contact=False,
    )

    assert "年龄、城市这类基础信息也可以低频补半句自然解释" in prompt
    assert "优先留意同城" in prompt


def test_main_prompt_mentions_light_praise_and_contact_rephrase():
    from src.services.prompts.prompts import get_main_dialogue

    prompt = get_main_dialogue(
        collected_info="职业:IT",
        missing_fields="月收入、联系方式",
        gender_instruction="正常称呼即可",
        is_first_chat=False,
        current_main_target="月收入",
        current_side_target="无",
        can_enter_contact=False,
    )

    assert "可以顺手轻轻认可半句" in prompt
    assert "不要重复“我再轻问一次”这类固定句式" in prompt


def test_main_prompt_mentions_opening_clarify_before_field_collection():
    from src.services.prompts.prompts import get_main_dialogue

    prompt = get_main_dialogue(
        collected_info="无",
        missing_fields="性别、年龄、所在地",
        gender_instruction="正常称呼即可",
        is_first_chat=True,
        current_main_target="性别",
        current_side_target="无",
        can_enter_contact=False,
    )

    assert "首轮，且用户输入像错字、乱码、打字异常" in prompt
    assert "不要直接切 `sex / age / location`" in prompt
