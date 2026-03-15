from src.services.conversation.user_question_service import UserQuestionService


def test_priority_question_detection_matches_business_questions():
    service = UserQuestionService()

    assert service.is_priority_question("你是中介吗")
    assert service.is_priority_question("怎么收费")
    assert not service.is_priority_question("深圳呢")
