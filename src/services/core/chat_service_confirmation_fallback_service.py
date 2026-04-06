import logging
import re
from typing import Any, Dict

from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class ChatServiceConfirmationFallbackService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def _extract_confirmed_sex_candidate_from_context(text: str) -> str | None:
        content = str(text or "").strip()
        if not content:
            return None
        if re.search(r"(你这边是|你是|我理解你是)\s*男(?:生|的)?", content):
            return "男"
        if re.search(r"(你这边是|你是|我理解你是)\s*女(?:生|的)?", content):
            return "女"
        return None

    @staticmethod
    def _is_affirmative_confirmation_answer(text: str) -> bool:
        return bool(
            re.search(
                r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
                r"(?:[呀呢啊哦哈啦嘛]*)?"
                r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
                str(text or ""),
            )
        )

    @staticmethod
    def extract_pending_confirmation_targets(last_response: str, user_profile: UserProfile) -> Dict[str, str]:
        targets: Dict[str, str] = {}
        sex_candidate = getattr(user_profile, "pending_sex_confirmation", None) or ChatServiceConfirmationFallbackService._extract_confirmed_sex_candidate_from_context(last_response)
        if sex_candidate:
            targets["sex"] = sex_candidate
        if re.search(r"(单身状态|现在是单身吗|现在单身吗|感情状态.*单身|婚况.*单身)", str(last_response or "")):
            targets["marital_status"] = "单身"
        return targets

    @staticmethod
    def should_use_confirmation_ai_fallback(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        if len(text) > 12:
            return False
        if re.search(r"(我是|我就是|本人|男生|女生|男的|女的|单身|未婚|离异|已婚)", text):
            return False
        if ChatServiceConfirmationFallbackService._is_affirmative_confirmation_answer(text):
            return False
        if re.search(r"(不是|不对|并不是|没有)", text):
            return False
        return True

    async def apply_confirmation_ai_fallback(
        self,
        extracted_data: Dict[str, Any],
        extraction_meta: Dict[str, Dict[str, Any]],
        *,
        user_message: str,
        last_response: str,
        user_profile: UserProfile,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        if not self.should_use_confirmation_ai_fallback(user_message):
            return extracted_data, extraction_meta

        pending_targets = self.extract_pending_confirmation_targets(last_response, user_profile)
        unresolved_targets = {
            field: value
            for field, value in pending_targets.items()
            if not extracted_data.get(field)
        }
        if not unresolved_targets:
            return extracted_data, extraction_meta

        decision = await self.host.confirmation_ai_fallback_classifier.classify(
            last_response=last_response,
            user_message=user_message,
            unresolved_targets=unresolved_targets,
        )
        if decision is None:
            return extracted_data, extraction_meta
        if decision.result != "confirmed" or decision.field not in unresolved_targets:
            return extracted_data, extraction_meta

        extracted_data[decision.field] = unresolved_targets[decision.field]
        extraction_meta[decision.field] = {
            "source": "confirmation_ai_fallback",
            "confidence": 0.72,
            "source_text": user_message,
        }
        logger.info(
            "[confirmation_ai_fallback] field=%s value=%s",
            decision.field,
            unresolved_targets[decision.field],
        )
        return extracted_data, extraction_meta
