from src.services.queue.intent_classifier import QueueIntentClassifier


def test_classify_cancel_like():
    c = QueueIntentClassifier()
    result = c.classify("算了，先这样")
    assert result["cancel_like"] is True


def test_classify_force_flush():
    c = QueueIntentClassifier()
    result = c.classify("好了，你回复吧")
    assert result["force_flush"] is True


def test_cancel_negation_guard():
    c = QueueIntentClassifier()
    result = c.classify("我不是算了，我是说继续")
    assert result["cancel_like"] is False
