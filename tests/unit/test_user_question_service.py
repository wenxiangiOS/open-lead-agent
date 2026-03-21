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
