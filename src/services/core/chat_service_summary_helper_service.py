import re
from typing import Dict, Optional

from src.models.user_profile import UserProfile
from src.modules.profile_collection.domain.extraction_service import ExtractionService


class ChatServiceSummaryHelperService:
    GENERIC_PARTNER_REQUIREMENT_VALUES = {
        "找对象",
        "想找对象",
        "找个对象",
        "找另一半",
        "想找另一半",
        "男生",
        "女生",
    }
    _PURE_GENDER_PARTNER_REQUIREMENT_PATTERN = re.compile(
        r"^(?:想找|找个|找|只找)?(?:男朋友|女朋友|男生|女生|男的|女的|男士|女士|男性|女性)$"
    )
    STRUCTURED_PARTNER_PREFERENCE_FIELDS = (
        "partner_pref_age",
        "partner_pref_age_relation",
        "partner_pref_location",
        "partner_pref_locality",
        "partner_pref_height",
        "partner_pref_education",
        "partner_pref_industry",
        "partner_pref_personality",
        "partner_pref_income",
        "partner_pref_other",
    )

    @classmethod
    def compose_structured_partner_preference_text(cls, profile: Optional[UserProfile]) -> str:
        if profile is None:
            return ""
        parts = []
        for field in cls.STRUCTURED_PARTNER_PREFERENCE_FIELDS:
            value = str(getattr(profile, field, "") or "").strip()
            if value and value not in parts:
                parts.append(value)
        return "，".join(parts)

    @staticmethod
    def _compose_structured_partner_preference_text_from_mapping(payload: Optional[Dict[str, object]] = None) -> str:
        if not isinstance(payload, dict):
            return ""
        parts = []
        for field in ChatServiceSummaryHelperService.STRUCTURED_PARTNER_PREFERENCE_FIELDS:
            value = str(payload.get(field) or "").strip()
            if value and value not in parts:
                parts.append(value)
        return "，".join(parts)

    @classmethod
    def _collect_structured_partner_preference_mapping_from_profile(
        cls,
        profile: Optional[UserProfile] = None,
    ) -> Dict[str, str]:
        if profile is None:
            return {}
        field_mapping: Dict[str, str] = {}
        for field in cls.STRUCTURED_PARTNER_PREFERENCE_FIELDS:
            value = str(getattr(profile, field, "") or "").strip()
            if value:
                field_mapping[field] = value
        return field_mapping

    @classmethod
    def _extract_structured_partner_preference_mapping_from_collection_result(
        cls,
        collection_result: Optional[Dict[str, object]] = None,
    ) -> Dict[str, str]:
        if not isinstance(collection_result, dict):
            return {}
        top_level_mapping = {
            field: str(collection_result.get(field) or "").strip()
            for field in cls.STRUCTURED_PARTNER_PREFERENCE_FIELDS
            if str(collection_result.get(field) or "").strip()
        }
        if top_level_mapping:
            return top_level_mapping

        field_mapping: Dict[str, str] = {}
        for item in collection_result.get("all_fields", []):
            if not isinstance(item, dict):
                continue
            field_name = str(item.get("field") or "").strip()
            if field_name not in cls.STRUCTURED_PARTNER_PREFERENCE_FIELDS:
                continue
            value = str(item.get("value") or "").strip()
            if value:
                field_mapping[field_name] = value
        return field_mapping

    @classmethod
    def _extract_structured_partner_requirement_from_collection_result(
        cls,
        collection_result: Optional[Dict[str, object]] = None,
    ) -> str:
        field_mapping = cls._extract_structured_partner_preference_mapping_from_collection_result(collection_result)
        return cls._compose_structured_partner_preference_text_from_mapping(field_mapping)

    @staticmethod
    def _extract_partner_requirement_from_collection_result(collection_result: Optional[Dict[str, object]] = None) -> str:
        if not isinstance(collection_result, dict):
            return ""
        for item in collection_result.get("all_fields", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("field") or "").strip() != "partner_requirement":
                continue
            value = str(item.get("value") or "").strip()
            if value:
                return value
        value = str(collection_result.get("value") or "").strip()
        if str(collection_result.get("field") or "").strip() == "partner_requirement" and value:
            return value
        return ""

    @classmethod
    def _resolve_partner_requirement_display(
        cls,
        *,
        raw_requirement: str = "",
        structured_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        structured_mapping = {
            str(field or "").strip(): str(value or "").strip()
            for field, value in dict(structured_mapping or {}).items()
            if str(field or "").strip() and str(value or "").strip()
        }
        raw_text = str(raw_requirement or "").strip()
        compact_raw_text = re.sub(r"\s+", "", raw_text)
        if (
            raw_text in cls.GENERIC_PARTNER_REQUIREMENT_VALUES
            or cls._PURE_GENDER_PARTNER_REQUIREMENT_PATTERN.fullmatch(compact_raw_text)
        ):
            raw_text = ""

        if structured_mapping and raw_text:
            composed = ExtractionService._compose_partner_requirement_from_subslots(structured_mapping, raw_text)  # noqa: SLF001
            if str(composed or "").strip():
                return str(composed).strip()
        if raw_text:
            return raw_text
        if structured_mapping:
            return cls._compose_structured_partner_preference_text_from_mapping(structured_mapping)
        return ""

    @classmethod
    def extract_partner_requirement_hint(
        cls,
        collection_result: Optional[Dict[str, object]] = None,
        profile: Optional[UserProfile] = None,
    ) -> str:
        collection_hint = cls._resolve_partner_requirement_display(
            raw_requirement=cls._extract_partner_requirement_from_collection_result(collection_result),
            structured_mapping=cls._extract_structured_partner_preference_mapping_from_collection_result(collection_result),
        )
        if collection_hint:
            return collection_hint

        profile_hint = cls._resolve_partner_requirement_display(
            raw_requirement=str(getattr(profile, "partner_requirement", "") or "").strip() if profile else "",
            structured_mapping=cls._collect_structured_partner_preference_mapping_from_profile(profile),
        )
        if profile_hint:
            return profile_hint
        return ""

    @staticmethod
    def build_profile_summary_line(profile: UserProfile) -> str:
        summary_parts = []

        location = profile.location or ""
        if location:
            summary_parts.append(f"在{location}")

        age = profile.age or profile.age_label or ""
        if age:
            if "后" in str(age) or "岁" in str(age):
                summary_parts.append(str(age))
            else:
                summary_parts.append(f"{age}岁")

        education = profile.education or ""
        if education:
            summary_parts.append(education)

        partner_req = ChatServiceSummaryHelperService.compose_structured_partner_preference_text(profile)
        if not partner_req:
            partner_req = str(profile.partner_requirement or "").strip()
        if partner_req:
            if "同城" in partner_req:
                summary_parts.append("偏同城")
            elif len(partner_req) <= 10:
                summary_parts.append(f"偏{partner_req}")

        if not summary_parts:
            return ""

        summary_text = "、".join(summary_parts[:3])
        return f"你这边大概是{summary_text}。"
