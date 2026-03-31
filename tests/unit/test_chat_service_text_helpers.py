import pytest

from src.services.core.chat_service import ChatService


class _FakeAIService:
    async def generate_response(self, *args, **kwargs):
        return ""


def _build_chat_service() -> ChatService:
    return ChatService(_FakeAIService(), object())


def test_collapse_duplicate_ack_segments_removes_double_confirmation():
    response = ChatService._collapse_duplicate_ack_segments(
        "男生，明白了。 好嘞，你是男生啦。 你今年多大呀？"
    )

    assert "你今年多大呀？" in response
    assert response.count("男生") <= 1


def test_collapse_duplicate_ack_segments_prefers_compound_ack_question_segment():
    response = ChatService._collapse_duplicate_ack_segments(
        "男生，明白了。 好的，你是男生啦。 你今年多大呀？"
    )

    assert response == "好的，你是男生啦。 你今年多大呀？"


def test_collapse_duplicate_ack_segments_removes_generic_followup_ack_after_specific_ack():
    response = ChatService._collapse_duplicate_ack_segments(
        "好，你这边是男生。 嗯嗯我知道啦。 你现在主要在哪个城市生活呀？"
    )

    assert response == "好，你这边是男生。 你现在主要在哪个城市生活呀？"


def test_sanitize_robotic_tone_removes_sex_confirmation_prefix():
    cleaned = ChatService._sanitize_robotic_tone("好，你是男生啦。 方便说下你今年多大吗？")
    assert "男生啦" not in cleaned
    assert "多大" in cleaned


def test_sanitize_robotic_tone_keeps_unknown_you_are_phrase_intact():
    cleaned = ChatService._sanitize_robotic_tone(
        "好，你说的这些择偶要求我都记下来啦。对了，我还不知道你是男生还是女生呢？"
    )

    assert "我还不知道你是男生还是女生呢" in cleaned
    assert "我还不你是" not in cleaned


def test_sanitize_robotic_tone_removes_business_identity_and_registration_tone():
    response = ChatService._sanitize_robotic_tone(
        "你好呀~我是帮大家做交友匹配的小缘，顺口问下你是男生还是女生呀？"
    )

    assert "交友匹配" not in response
    assert "顺口问下" not in response
    assert "我是小缘" in response


def test_sanitize_robotic_tone_softens_registration_and_contact_push_tone():
    response = ChatService._sanitize_robotic_tone(
        "我记下你是男生啦。后面给你匹配到合适的人选时好及时联系到你。"
    )

    assert "我记下" not in response
    assert "合适的人选" not in response
    assert "及时联系到你" not in response


def test_sanitize_robotic_tone_does_not_create_broken_sentence_fragments():
    response = ChatService._sanitize_robotic_tone("好的，我记下你是男生啦。")

    assert "来你是" not in response
    assert "你是男生" in response


def test_sanitize_robotic_tone_removes_meta_tone_adjustment_copy():
    response = ChatService._sanitize_robotic_tone(
        "哈哈好的，我语气放轻松些。之后有合适的匹配进展也方便及时通知到你，你方便留个联系电话不？"
    )

    assert "语气放轻松" not in response
    assert "及时通知到你" not in response
    assert "联系电话吗" in response or "联系你会更方便" in response


def test_sanitize_robotic_tone_removes_repetitive_location_ack_prefix():
    cleaned = ChatService._sanitize_robotic_tone("在深圳这边是吧。 你平时也是在深圳工作吗，主要做什么呀？")
    assert "在深圳这边是吧" not in cleaned
    assert "主要做什么" in cleaned


def test_sanitize_robotic_tone_removes_repetitive_profile_ack_prefixes():
    cleaned = ChatService._sanitize_robotic_tone("本科是吧。 好呀，你今年大概多大呀？")
    assert "本科是吧" not in cleaned
    assert "多大" in cleaned

    cleaned = ChatService._sanitize_robotic_tone("做美容是吧。 你大概是什么学历呀？")
    assert "做美容是吧" not in cleaned
    assert "学历" in cleaned


def test_sanitize_robotic_tone_removes_new_ack_skeletons_before_followup():
    cleaned = ChatService._sanitize_robotic_tone("IT这行我接住了。 你大概是什么学历呀？")
    assert "IT这行我接住了" not in cleaned
    assert "学历" in cleaned

    cleaned = ChatService._sanitize_robotic_tone("学历这块是本科。 那你现在大概多大呀？")
    assert "学历这块是本科" not in cleaned
    assert "多大" in cleaned

    cleaned = ChatService._sanitize_robotic_tone("现在主要做IT这块，是吧。 你月收入大概在哪个区间呀？")
    assert "现在主要做IT这块，是吧" not in cleaned
    assert "月收入" in cleaned

    cleaned = ChatService._sanitize_robotic_tone("学历这块是本科。 另外我也确认下，你现在是单身吗？")
    assert "学历这块是本科" not in cleaned
    assert "单身吗" in cleaned


def test_clean_response_removes_dangling_particles_and_truncated_tail():
    chat_service = _build_chat_service()
    assert chat_service._clean_response("啦。 你今年多大呀？") == "你今年多大呀？"
    assert chat_service._clean_response("了。 你是哪年的呀？") == "你是哪年的呀？"
    assert chat_service._clean_response("你这边更偏向温柔，对吧。 哈哈，原来") == "你这边更偏向温柔，对吧。"


def test_clean_response_compresses_low_information_explanatory_tail_after_question():
    chat_service = _build_chat_service()

    cleaned = chat_service._clean_response("你今年大概多大呀？ 这样我心里会更有数一点。")

    assert cleaned == "你今年大概多大呀？"


def test_clean_response_keeps_single_clear_question_without_explanatory_tail():
    chat_service = _build_chat_service()

    cleaned = chat_service._clean_response("你现在主要做哪方面工作呀？")

    assert cleaned == "你现在主要做哪方面工作呀？"


def test_is_delivery_viable_rejects_empty_and_truncated_responses():
    chat_service = _build_chat_service()

    assert chat_service._is_delivery_viable("") is False
    assert chat_service._is_delivery_viable("没事哈，我懂你担心隐私问题～要是手机号不方便的话，留个常用微信也行，我们平时") is False
    assert chat_service._is_delivery_viable("你这边更偏向温柔，对吧。 哈哈，原来") is False
    assert chat_service._is_delivery_viable("你现在主要在哪个城市生活？") is True


def test_format_fast_path_ack_skips_sex_confirmation():
    chat_service = _build_chat_service()
    response = chat_service._format_fast_path_ack("sex", "男")
    assert response == ""


def test_format_fast_path_ack_avoids_remembering_tone_for_occupation():
    chat_service = _build_chat_service()

    response = chat_service._format_fast_path_ack("occupation", "产品")

    assert "记着" not in response
    assert "记成" not in response
    assert "产品" in response


def test_format_fast_path_ack_avoids_remembering_tone_for_marital_status():
    chat_service = _build_chat_service()

    response = chat_service._format_fast_path_ack("marital_status", "单身")

    assert "记着" not in response
    assert "记成" not in response
    assert "单身" in response


def test_needs_style_retry_for_fixed_template_phrases():
    chat_service = _build_chat_service()

    assert chat_service._needs_style_retry("你好呀～对了，想问下你是男生还是女生呀？")
    assert chat_service._needs_style_retry("好，你是男生啦。 对了，你方便说下自己的年龄吗？")


@pytest.mark.parametrize(
    "input_text,should_not_contain",
    [
        ("好，那我们就按90后来聊。", "按90后来聊"),
        ("我们先不连着问资料。", "先不连着问资料"),
        ("这轮我先不把资料问得太密。", "不把资料问得太密"),
        ("按这个优先推进", "按这个优先推进"),
        ("按这个优先筛", "按这个优先筛"),
    ],
)
def test_meta_strategy_phrases_are_cleaned(input_text, should_not_contain):
    chat_service = _build_chat_service()
    cleaned = chat_service._sanitize_robotic_tone(input_text)
    assert should_not_contain not in cleaned


def test_short_confirmation_replaces_strategy_phrase():
    chat_service = _build_chat_service()
    cleaned = chat_service._sanitize_robotic_tone("好，那我们就按90后来聊。")
    assert "按90后来聊" not in cleaned
