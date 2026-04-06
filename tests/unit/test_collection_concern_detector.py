from src.modules.conversation.domain.collection_concern_detector import CollectionConcernDetector


def test_collection_concern_detector_matches_direct_phrase_without_context():
    detector = CollectionConcernDetector()

    match = detector.detect(message="为什么要记下我的信息")

    assert match is not None
    assert match.intent == "info_collection_why"
    assert "direct_pattern" in match.reasons


def test_collection_concern_detector_matches_semantic_combination_without_context():
    detector = CollectionConcernDetector()

    match = detector.detect(message="你们了解我这些情况干嘛")

    assert match is not None
    assert match.intent == "info_collection_why"
    assert "question_cue" in match.reasons
    assert "collection_object_pair" in match.reasons


def test_collection_concern_detector_uses_context_for_followup_pressure_question():
    detector = CollectionConcernDetector()

    match = detector.detect(
        message="为啥要问这么清晰呢",
        last_asked_field="monthly_income",
        last_response="本科学历挺好的~你现在的月收入大概在什么范围呀？",
    )

    assert match is not None
    assert match.intent == "info_collection_why"
    assert match.context_field == "monthly_income"
    assert "context_field" in match.reasons
