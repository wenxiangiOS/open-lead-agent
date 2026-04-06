from __future__ import annotations

import re


class ResponseSafeCleanupService:
    """Minimal safe cleanup only. No semantic rewrite."""

    def cleanup(self, text: str) -> tuple[str, bool]:
        original = str(text or "")
        cleaned = original
        cleaned = re.sub(r"<extract>.*?</extract>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<opening_intent>.*?</opening_intent>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"```(?:debug|json|text)?\s*(?:traceback|error|debug).*?```", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"^[ \t]+|[ \t]+$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = cleaned.strip()
        return cleaned, cleaned != original
