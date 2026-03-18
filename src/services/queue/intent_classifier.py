from __future__ import annotations


class QueueIntentClassifier:
    CANCEL_KEYWORDS = [
        "算了",
        "不用了",
        "下次再说",
        "不聊了",
        "不想看了",
        "先这样",
    ]

    FORCE_FLUSH_KEYWORDS = [
        "说完了",
        "你回复吧",
        "好了",
        "可以回我了",
    ]

    NEGATION_PREFIXES = ["不是", "不", "没", "别"]

    def _is_negated_cancel(self, text: str, keyword: str) -> bool:
        return any(f"{prefix}{keyword}" in text for prefix in self.NEGATION_PREFIXES)

    def classify(self, content: str) -> dict:
        text = (content or "").strip()
        cancel_like = any((k in text) and (not self._is_negated_cancel(text, k)) for k in self.CANCEL_KEYWORDS)
        return {
            "cancel_like": cancel_like,
            "force_flush": any(k in text for k in self.FORCE_FLUSH_KEYWORDS),
        }
