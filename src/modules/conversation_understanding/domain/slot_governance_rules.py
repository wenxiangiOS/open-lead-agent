from __future__ import annotations

import re


def message_has_explicit_age_semantics(message: str) -> bool:
    return bool(re.search(r"(岁|年龄|今年|出生|哪年|90后|95后|85后)", str(message or "")))


def is_sex_confirmation_context(
    *,
    last_response: str,
    pending_confirmation_field: str | None,
    confirmed_sex_candidate: str | None,
) -> bool:
    text = str(last_response or "")
    return bool(
        re.search(r"(你是|是)(男生|女生|男的|女的|男|女)", text)
        or "性别" in text
        or confirmed_sex_candidate
        or pending_confirmation_field == "sex"
    )


def extract_explicit_correction_fields(
    *,
    message: str,
    user_profile: object,
    deterministic_extractor,
    looks_like_correction,
) -> dict[str, str]:
    if not looks_like_correction(message):
        return {}

    detected = deterministic_extractor(message)
    correction_tail_match = re.search(
        r"(?:不是|不在|不做|不算|说错了|搞错了).{0,12}?(?:是|在|做|改成|改为)\s*(?P<tail>.+)$",
        str(message or "").strip(),
    )
    if correction_tail_match:
        correction_tail = str(correction_tail_match.group("tail") or "").strip("，,、。！？!? ")
        if correction_tail:
            detected.update(deterministic_extractor(correction_tail))

    correction_fields: dict[str, str] = {}
    allowed_fields = {
        "sex",
        "age",
        "age_label",
        "location",
        "education",
        "occupation",
        "marital_status",
        "monthly_income",
    }
    for field_name, value in detected.items():
        if field_name not in allowed_fields:
            continue
        normalized_value = str(value or "").strip()
        if not normalized_value:
            continue
        current_value = "" if user_profile is None else str(getattr(user_profile, field_name, "") or "").strip()
        if field_name == "age_label" or not current_value or current_value != normalized_value:
            correction_fields[field_name] = normalized_value
    return correction_fields
