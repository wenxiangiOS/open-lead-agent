from src.services.conversation.user_question_service import UserQuestionService


def test_priority_question_detection_matches_business_questions():
    service = UserQuestionService()

    assert service.is_priority_question("你是中介吗")
    assert service.is_priority_question("怎么收费")
    assert service.is_priority_question("你们成功率怎么样")
    assert not service.is_priority_question("深圳呢")


def test_quick_faq_response_hits_known_intents():
    service = UserQuestionService()

    fee = service.get_quick_faq_response("怎么收费")
    assert fee is not None
    assert "免费" in fee

    match = service.get_quick_faq_response("你们怎么匹配")
    assert match is not None
    assert "线上" in match

    safety = service.get_quick_faq_response("你们平台安全吗")
    assert safety is not None
    assert "安全" in safety
