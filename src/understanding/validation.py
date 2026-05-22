"""字段格式校验与联系方式标准化。

这里提供模板通用的轻量校验，避免联系方式等高风险字段被随意写入档案。
复杂业务可以后续通过配置或插件扩展。
"""

import re
from typing import Any

from src.templates.config import ContactMethodConfig, FieldConfig


class FieldValueValidator:
    def normalize_contact(
        self,
        config: ContactMethodConfig,
        value: Any,
    ) -> str | None:
        raw = str(value).strip()
        if not raw:
            return None
        validation_type = (config.validation or config.type or "text").lower()
        if validation_type in {"phone", "mobile", "whatsapp"}:
            return self._normalize_phone(raw)
        if validation_type == "email":
            return self._normalize_email(raw)
        if validation_type == "qq":
            return self._normalize_qq(raw)
        if validation_type == "wechat":
            return self._normalize_wechat(raw)
        if validation_type == "telegram":
            return self._normalize_telegram(raw)
        return raw

    def is_high_risk(self, config: FieldConfig | ContactMethodConfig) -> bool:
        if isinstance(config, ContactMethodConfig):
            return True
        risk = (config.risk or "normal").lower()
        if risk in {"high", "strict"}:
            return True
        key_text = f"{config.key} {config.label} {config.type}".lower()
        return any(token in key_text for token in ("age", "income", "salary", "年龄", "收入"))

    def min_confidence(self, config: FieldConfig | ContactMethodConfig) -> float:
        if config.min_confidence > 0:
            return config.min_confidence
        return 0.8 if self.is_high_risk(config) else 0.6

    def _normalize_phone(self, raw: str) -> str | None:
        compact = re.sub(r"[\s\-\(\)]", "", raw)
        if compact.startswith("+"):
            digits = "+" + re.sub(r"\D", "", compact[1:])
        else:
            digits = re.sub(r"\D", "", compact)
        digit_count = len(digits.lstrip("+"))
        if 7 <= digit_count <= 15:
            return digits
        return None

    def _normalize_email(self, raw: str) -> str | None:
        email = raw.strip().lower()
        if re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", email, re.I):
            return email
        return None

    def _normalize_qq(self, raw: str) -> str | None:
        digits = re.sub(r"\D", "", raw)
        if re.fullmatch(r"\d{5,12}", digits):
            return digits
        return None

    def _normalize_wechat(self, raw: str) -> str | None:
        handle = raw.strip()
        if re.fullmatch(r"[A-Za-z0-9_\-]{5,20}", handle):
            return handle
        return None

    def _normalize_telegram(self, raw: str) -> str | None:
        handle = raw.strip()
        if handle.startswith("@"):
            handle = handle[1:]
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", handle):
            return f"@{handle}"
        return None
