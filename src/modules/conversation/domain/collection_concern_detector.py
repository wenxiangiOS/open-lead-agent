"""Detect concern about ongoing profile/contact information collection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class CollectionConcernMatch:
    intent: str
    confidence: float
    reasons: tuple[str, ...]
    context_field: str | None = None


class CollectionConcernDetector:
    CONTACT_REPEAT_PATTERNS = (
        r"上面不是已经留(?:给)?过电话",
        r"不是已经留(?:给)?过电话",
        r"都已经留(?:给)?过电话",
        r"电话不是已经留(?:给)?过",
        r"上面不是已经给(?:过)?电话",
        r"不是已经给(?:过)?电话",
        r"(?:留过|给过)电话.*(?:为什么|为啥).*(?:还要问|还问|又问)",
    )
    DIRECT_PATTERNS = (
        r"为什么要记(?:下)?我(?:的)?(?:信息|资料|情况)",
        r"为啥要记(?:下)?我(?:的)?(?:信息|资料|情况)",
        r"收集(?:这些|这些个|我)?(?:信息|资料|情况).*(?:干嘛|做什么|有什么用)",
        r"记(?:这些|这个|我(?:的)?)?(?:信息|资料|情况).*(?:干嘛|做什么|有什么用)",
        r"为什么一直问(?:这些|我)?(?:信息|资料|情况)",
        r"问(?:这些|这么多|这么细|这么清楚|这么清晰).*(?:干嘛|做什么|有什么用|呢)",
        r"为啥要问这么(?:细|清楚|清晰)",
        r"为什么要问这么(?:细|清楚|清晰)",
    )
    QUESTION_CUES = ("为什么", "为啥", "干嘛", "做什么", "什么意思", "有必要", "一定要", "吗", "么", "？", "?")
    PRESSURE_CUES = ("这么细", "这么清楚", "这么清晰", "这么多", "一直问", "老问", "问这么多", "问这么细")
    ACTION_HINTS = ("记", "记下", "记录", "收集", "留", "问", "了解", "确认")
    OBJECT_HINTS = ("信息", "资料", "情况", "这些", "这个", "内容")
    CONTEXT_FIELDS = {
        "sex",
        "age",
        "education",
        "occupation",
        "location",
        "marital_status",
        "monthly_income",
        "partner_requirement",
        "contact",
        "phone",
        "wechat",
    }

    def detect(
        self,
        *,
        message: str,
        last_asked_field: str = "",
        last_response: str = "",
        recent_responses: Iterable[str] | None = None,
        in_contact_flow: bool = False,
    ) -> CollectionConcernMatch | None:
        text = str(message or "").strip()
        if not text:
            return None

        if any(re.search(pattern, text) for pattern in self.CONTACT_REPEAT_PATTERNS):
            return CollectionConcernMatch(
                intent="contact_repeat_why",
                confidence=0.96,
                reasons=("contact_repeat_pattern", "context_field"),
                context_field="contact",
            )

        if any(re.search(pattern, text) for pattern in self.DIRECT_PATTERNS):
            context_field = self._normalize_context_field(last_asked_field)
            reasons = ["direct_pattern"]
            if context_field:
                reasons.append("context_field")
            return CollectionConcernMatch(
                intent="info_collection_why",
                confidence=0.95,
                reasons=tuple(reasons),
                context_field=context_field,
            )

        has_question_cue = any(cue in text for cue in self.QUESTION_CUES)
        has_pressure_cue = any(cue in text for cue in self.PRESSURE_CUES)
        has_action_hint = any(hint in text for hint in self.ACTION_HINTS)
        has_object_hint = any(hint in text for hint in self.OBJECT_HINTS)
        context_field = self._resolve_context_field(
            last_asked_field=last_asked_field,
            last_response=last_response,
            recent_responses=recent_responses or (),
        )

        score = 0.0
        reasons: list[str] = []

        if has_question_cue:
            score += 0.8
            reasons.append("question_cue")
        if has_pressure_cue:
            score += 1.0
            reasons.append("pressure_cue")
        if has_action_hint and has_object_hint:
            score += 1.0
            reasons.append("collection_object_pair")
        elif has_action_hint or has_object_hint:
            score += 0.4
            reasons.append("collection_hint")
        if context_field:
            score += 1.2
            reasons.append("context_field")
        if in_contact_flow and has_question_cue:
            score += 0.4
            reasons.append("contact_context")

        if has_question_cue and has_pressure_cue and context_field:
            return CollectionConcernMatch(
                intent="info_collection_why",
                confidence=0.94,
                reasons=tuple(reasons),
                context_field=context_field,
            )

        if has_question_cue and has_action_hint and has_object_hint:
            return CollectionConcernMatch(
                intent="info_collection_why",
                confidence=0.88 if context_field else 0.84,
                reasons=tuple(reasons),
                context_field=context_field,
            )

        if has_question_cue and has_object_hint and context_field:
            return CollectionConcernMatch(
                intent="info_collection_why",
                confidence=0.86,
                reasons=tuple(reasons),
                context_field=context_field,
            )

        if score >= 2.6:
            confidence = 0.9 if context_field else 0.82
            return CollectionConcernMatch(
                intent="info_collection_why",
                confidence=confidence,
                reasons=tuple(reasons),
                context_field=context_field,
            )
        return None

    def _resolve_context_field(
        self,
        *,
        last_asked_field: str,
        last_response: str,
        recent_responses: Iterable[str],
    ) -> str | None:
        normalized = self._normalize_context_field(last_asked_field)
        if normalized:
            return normalized

        for candidate in (last_response, *recent_responses):
            detected = self._detect_field_from_response(candidate)
            if detected:
                return detected
        return None

    def _normalize_context_field(self, field_name: str) -> str | None:
        field = str(field_name or "").strip()
        if field in self.CONTEXT_FIELDS:
            return field
        return None

    @staticmethod
    def _detect_field_from_response(response: str) -> str | None:
        text = str(response or "").strip()
        if not text:
            return None

        field_patterns = (
            ("monthly_income", (r"月收入", r"收入大概在什么", r"收入大概在哪个区间")),
            ("marital_status", (r"感情状态", r"婚况", r"现在是不是单身", r"现在的状态")),
            ("education", (r"什么学历", r"学历大概是什么", r"学历这块")),
            ("occupation", (r"做什么工作", r"主要做什么", r"现在做哪方面")),
            ("location", (r"哪个城市", r"主要在哪", r"在哪里工作生活")),
            ("age", (r"几几年", r"哪一年出生", r"今年多大")),
            ("sex", (r"男生还是女生", r"你是女生对吧", r"你是男生对吧")),
            ("partner_requirement", (r"喜欢什么类型", r"想找什么样", r"择偶要求")),
            ("contact", (r"留个电话", r"留个微信", r"联系方式")),
        )
        for field_name, patterns in field_patterns:
            if any(re.search(pattern, text) for pattern in patterns):
                return field_name
        return None
