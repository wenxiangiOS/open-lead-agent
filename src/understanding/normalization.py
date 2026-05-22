"""字段值标准化。

这里只做类型、枚举、常见格式标准化，不决定字段是否落库。
"""

import re
from typing import Any

from src.templates.config import ContactMethodConfig, FieldConfig
from src.understanding.validation import FieldValueValidator


class FieldNormalizer:
    def __init__(self):
        self.validator = FieldValueValidator()

    def normalize(
        self,
        config: FieldConfig | ContactMethodConfig,
        value: Any,
    ) -> str | int | float | bool | list[Any] | dict[str, Any] | None:
        if isinstance(config, ContactMethodConfig):
            return self.validator.normalize_contact(config, value)
        if config.type == "enum" and isinstance(config, FieldConfig) and config.options:
            return self._normalize_enum(config, value)
        if config.type == "number":
            if isinstance(config, FieldConfig) and self._should_preserve_number_text(config):
                return self._normalize_number_text(value)
            return self._normalize_number(value)
        return value

    def _normalize_enum(self, config: FieldConfig, value: Any) -> str | None:
        raw = str(value).strip()
        for option in config.options:
            if raw == option or raw.lower() == option.lower() or option in raw or raw in option:
                return option
        return None

    def _normalize_number(self, value: Any) -> int | float | str | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return value
        raw = str(value).strip()
        if not raw:
            return None
        if "后" in raw:
            return raw
        match = re.search(r"\d+(?:\.\d+)?", raw)
        if match:
            raw = match.group(0)
        try:
            number = float(raw)
        except ValueError:
            return None
        if number.is_integer():
            return int(number)
        return number

    def _should_preserve_number_text(self, config: FieldConfig) -> bool:
        validation = (config.validation or "").lower()
        return validation in {"preserve_raw", "raw_number", "number_text"}

    def _normalize_number_text(self, value: Any) -> str | None:
        if isinstance(value, bool):
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if not re.search(r"\d", raw):
            return None
        # A common typo in terminal tests is "50k9" for "50kg".
        raw = re.sub(r"(?<=\d)k9\b", "kg", raw, flags=re.I)
        raw = re.sub(r"\s+", "", raw)
        return raw
