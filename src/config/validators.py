"""Validation utilities"""

import re
from typing import Any


def validate_api_key(api_key: str) -> None:
    """Validate API key format"""
    if not api_key:
        raise ValueError("API key cannot be empty")
    if not re.match(r'^[a-zA-Z0-9\-]+$', api_key):
        raise ValueError("Invalid API key format")


def validate_model_name(model_name: str) -> None:
    """Validate model name format"""
    if not model_name:
        raise ValueError("Model name cannot be empty")
    if not re.match(r'^doubao-[a-zA-Z0-9\-]+$', model_name):
        raise ValueError("Invalid model name format")


def validate_user_id(user_id: str) -> None:
    """Validate user ID format"""
    if not user_id:
        raise ValueError("User ID cannot be empty")
    if not re.match(r'^[a-zA-Z0-9_\-]+$', user_id):
        raise ValueError("Invalid user ID format")


def validate_dialog_id(dialog_id: str) -> None:
    """Validate dialog ID format"""
    if not dialog_id:
        raise ValueError("Dialog ID cannot be empty")
    if not re.match(r'^[a-zA-Z0-9_\-]+$', dialog_id):
        raise ValueError("Invalid dialog ID format")


def validate_question(question: str) -> None:
    """Validate question format"""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    if len(question.strip()) > 1000:
        raise ValueError("Question too long (max 1000 characters)")


def validate_sex(sex: str) -> None:
    """Validate sex field"""
    valid_sexes = ["男", "女", "other", "unknown"]
    if sex not in valid_sexes:
        raise ValueError(f"Invalid sex value. Must be one of: {valid_sexes}")


def validate_age_range(age_range: str) -> None:
    """Validate age range format"""
    if not age_range:
        return  # Optional field

    # Pattern: "25-35", "18+", "30-40"
    if not re.match(r'^(\d{1,3}\+|\d{1,3}-\d{1,3})$', age_range):
        raise ValueError("Invalid age range format. Use format like '25-35' or '18+'")


def validate_location(location: str) -> None:
    """Validate location format"""
    if not location:
        return  # Optional field

    # Basic validation - allow Chinese characters and common location formats
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9\s\-\.]+$', location):
        raise ValueError("Invalid location format")


def validate_height_requirement(height: str) -> None:
    """Validate height requirement"""
    if not height:
        return  # Optional field

    # Pattern: "175+", "170-180", "165cm"
    if not re.match(r'^(\d{1,3}\+|\d{1,3}-\d{1,3}|)$', height):
        raise ValueError("Invalid height requirement format")


def validate_email(email: str) -> None:
    """Validate email format"""
    if not email:
        return  # Optional field

    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")


def validate_phone(phone: str) -> None:
    """Validate phone number format"""
    if not phone:
        return  # Optional field

    # Support Chinese mobile numbers and international formats
    if not re.match(r'^(\+?86?1[3-9]\d{9}|\+?[1-9]\d{1,14})$', phone):
        raise ValueError("Invalid phone number format")


def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\'\x00-\x1F]', '', text)

    # Trim whitespace
    text = text.strip()

    return text


def validate_preference_value(value: Any) -> bool:
    """Validate preference value type"""
    allowed_types = (str, int, float, bool, list, dict)
    return isinstance(value, allowed_types)