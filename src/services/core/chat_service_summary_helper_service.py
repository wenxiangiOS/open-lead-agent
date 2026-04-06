from typing import Dict, Optional

from src.models.user_profile import UserProfile


class ChatServiceSummaryHelperService:
    @staticmethod
    def extract_partner_requirement_hint(collection_result: Optional[Dict[str, object]] = None) -> str:
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

        partner_req = profile.partner_requirement or ""
        if partner_req:
            if "同城" in partner_req:
                summary_parts.append("偏同城")
            elif len(partner_req) <= 10:
                summary_parts.append(f"偏{partner_req}")

        if not summary_parts:
            return ""

        summary_text = "、".join(summary_parts[:3])
        return f"你这边大概是{summary_text}。"
