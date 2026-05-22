"""单轮理解上下文构建。

这里把上一轮目标字段、已知档案和模板字段整理成理解层可消费的信息。
"""

import json
from dataclasses import dataclass
from typing import Any

from src.templates.config import ContactMethodConfig, FieldConfig, TemplateConfig


@dataclass(frozen=True)
class UnderstandingContext:
    known_profile: dict[str, Any]
    expected_field: str = ""
    last_question: str = ""

    def known_profile_json(self) -> str:
        values = {
            key: value
            for key, value in self.known_profile.items()
            if value not in (None, "", [])
        }
        return json.dumps(values, ensure_ascii=False, sort_keys=True)


def configured_items(template: TemplateConfig) -> list[FieldConfig | ContactMethodConfig]:
    return [
        *[field for field in template.fields if field.extract],
        *[method for method in template.contact.methods if method.extract],
    ]


def configured_item_map(
    template: TemplateConfig,
) -> dict[str, FieldConfig | ContactMethodConfig]:
    return {item.key: item for item in configured_items(template)}
