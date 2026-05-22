"""密集自我介绍识别。

Dense intro 指用户一轮里同时给出多个资料、需求、联系方式或 FAQ。
这里不做行业规则，只做通用标记，帮助后续流程避免重复追问已经观察到的字段。
"""

from __future__ import annotations

import re

from src.understanding.models import TurnSemanticFrame


class DenseIntroDetector:
    _DENSE_INTENTS = {"profile", "contact_intent", "faq", "concern"}

    def detect(self, frame: TurnSemanticFrame, *, user_message: str) -> TurnSemanticFrame:
        if frame.turn_mode and frame.turn_mode != "default":
            return frame
        if not self._looks_like_dense_intro(frame, user_message=user_message):
            return frame

        observed_fields = sorted(
            {
                str(observation.field or "").strip()
                for observation in frame.observations
                if str(observation.field or "").strip()
            }
        )
        return TurnSemanticFrame(
            intents=frame.intents,
            observations=frame.observations,
            turn_mode="dense_intro",
            no_reask_fields=observed_fields,
            faq_intent=frame.faq_intent,
            compliance_signals=frame.compliance_signals,
            reply_act=frame.reply_act,
            confidence=frame.confidence,
            raw_payload=frame.raw_payload,
        )

    def _looks_like_dense_intro(
        self,
        frame: TurnSemanticFrame,
        *,
        user_message: str,
    ) -> bool:
        observed_count = len({observation.field for observation in frame.observations})
        if observed_count >= 3:
            return True
        text = user_message.strip()
        if len(text) < 20:
            return False
        intent_count = len(
            {
                intent.strip().lower()
                for intent in frame.intents
                if intent.strip().lower() in self._DENSE_INTENTS
            }
        )
        clause_count = len([part for part in re.split(r"[，,。；;、\s]+", text) if part])
        return observed_count >= 2 and (intent_count >= 2 or clause_count >= 4)
