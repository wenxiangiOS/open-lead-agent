from src.modules.conversation.domain.user_question_service import UserQuestionService


def test_detect_quick_faq_intent_clarification():
    service = UserQuestionService()
    intent = service.detect_quick_faq_intent("匹配点是啥意思，解释下")
    assert intent == "clarification"


def test_get_quick_faq_response_clarification_returns_explanatory_text():
    service = UserQuestionService()
    response = service.get_quick_faq_response("没看懂你刚说的匹配点是啥意思")
    assert response is not None
    assert any(marker in response for marker in ["匹配点", "比如", "条件", "标准"])


def test_get_quick_faq_response_store_location_keeps_store_rule_without_overpromising():
    service = UserQuestionService()
    response = service.get_quick_faq_response("你们有实体店吗，门店地址在哪")

    assert response is not None
    assert any(marker in response for marker in ["门店", "线下", "深圳"])
    assert "定位" not in response
    assert "马上发" not in response
    assert "第一时间" not in response


def test_get_quick_faq_response_how_match_stays_on_process_not_sales_pitch():
    service = UserQuestionService()
    response = service.get_quick_faq_response("你们怎么匹配，怎么牵线")

    assert response is not None
    assert any(marker in response for marker in ["情况", "要求", "偏好", "推进", "继续"])
    assert "电话联系你介绍对方情况" not in response
    assert "精准匹配" not in response


def test_get_quick_faq_response_contact_exchange_avoids_direct_exchange_promise():
    service = UserQuestionService()
    response = service.get_quick_faq_response("可以直接加男生微信吗")

    assert response is not None
    assert any(marker in response for marker in ["不会", "不", "直接", "互加", "确认"])
    assert "直接给你微信" not in response


def test_get_quick_faq_response_photo_avoids_sending_photo_promise():
    service = UserQuestionService()
    response = service.get_quick_faq_response("能先看对方照片吗")

    assert response is not None
    assert any(marker in response for marker in ["照片", "隐私", "不会", "当前阶段"])
    assert "直接发" not in response


def test_get_quick_faq_response_fee_avoids_hard_push():
    service = UserQuestionService()
    response = service.get_quick_faq_response("怎么收费")

    assert response is not None
    assert "免费" in response or "不收费" in response
    assert "强推" not in response


def test_get_quick_faq_response_specific_target_keeps_bidirectional_boundary():
    service = UserQuestionService()
    response = service.get_quick_faq_response("我就想要这个男生")

    assert response is not None
    assert any(marker in response for marker in ["这个人", "这个男生", "双方", "不合适"])
    assert "100%" not in response
    assert "保证" not in response


def test_get_quick_faq_response_marriage_pace_respects_user_preference():
    service = UserQuestionService()
    response = service.get_quick_faq_response("我暂时不想结婚，着急结婚的不要")

    assert response is not None
    assert any(marker in response for marker in ["节奏", "慢慢", "相处", "了解"])
    assert "催着定下来" in response or "节奏一致" in response


def test_get_quick_faq_response_contact_why_avoids_collection_tone():
    service = UserQuestionService()
    response = service.get_quick_faq_response("为什么要留微信")

    assert response is not None
    assert "顺着联系到你" not in response
    assert "登记" not in response
    assert "流程" not in response


def test_detect_quick_faq_intent_timeline_question():
    service = UserQuestionService()
    intent = service.detect_quick_faq_intent("多久联系我呢？")

    assert intent == "timeline"
