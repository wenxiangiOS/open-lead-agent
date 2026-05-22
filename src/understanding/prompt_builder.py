"""单轮理解提示词构建。

提示词由模板字段动态生成，开源用户只需要配置字段，不需要写死行业字段。
"""

import json

from src.templates.config import ContactMethodConfig, FieldConfig, TemplateConfig
from src.understanding.context import UnderstandingContext, configured_items


class UnderstandingPromptBuilder:
    def __init__(self, template: TemplateConfig):
        self.template = template

    def build(self, user_message: str, context: UnderstandingContext) -> str:
        configured_fields = self._format_configured_fields()
        custom_prompt = self._render_custom_prompt(
            user_message=user_message,
            known_profile=context.known_profile_json(),
            configured_fields=configured_fields,
        )
        lines = [
            "Extract lead profile fields from the user message.",
            "You are the single turn understanding layer for a configurable lead agent.",
            "Return only one JSON object. Do not include markdown or explanations.",
            "Return {} if the message does not contain any configured field values.",
            "Only use the configured keys below. Never invent extra keys.",
            "Do not include fields that already have a value in the known profile.",
            "If the user gives a dense introduction with multiple facts, extract all "
            "configured fields in the same JSON instead of choosing only one.",
            "If the same message includes a question and profile facts, keep both: "
            "set faq_intent/intents and also include field observations.",
            f"Reply JSON values in the field's natural language: {self.template.agent.language}.",
            "",
            "Preferred JSON shape:",
            json.dumps(
                {
                    "intents": ["profile"],
                    "observations": [
                        {
                            "field": "configured_key",
                            "value": "value from user",
                            "scope": "self",
                            "confidence": 0.9,
                            "write_mode": "direct_write",
                        }
                    ],
                    "faq_intent": None,
                    "reply_act": "continue",
                },
                ensure_ascii=False,
            ),
            "Allowed intent examples: profile, faq, concern, contact_intent, "
            "refusal, conversation_end.",
            "Allowed reply_act examples: continue, answer_only, answer_then_ask, "
            "refuse_collection, stop.",
            "Compliance signal examples: underage, pending_divorce, unsupported_region. "
            "Only emit a compliance signal when the user's message clearly indicates it.",
            "",
            "Backward-compatible shape is also accepted:",
            json.dumps({"configured_key": "value"}, ensure_ascii=False),
        ]
        if context.expected_field:
            lines.extend(
                [
                    "",
                    "Short-answer binding:",
                    f"The previous assistant turn was collecting key={context.expected_field}.",
                    "If the current user message is a short answer, prefer binding it to this key.",
                ]
            )
        if context.last_question:
            lines.extend(["", "Previous assistant question:", context.last_question])
        if custom_prompt:
            lines.extend(["", "Template-specific extraction instructions:", custom_prompt])
        lines.extend(
            [
                "",
                "Known profile:",
                context.known_profile_json(),
                "",
                "Configured fields:",
                configured_fields,
            ]
        )
        return "\n".join(lines)

    def _render_custom_prompt(
        self,
        *,
        user_message: str,
        known_profile: str,
        configured_fields: str,
    ) -> str:
        prompt = self.template.extraction.prompt.strip()
        if not prompt:
            return ""
        replacements = {
            "{user_message}": user_message,
            "{known_profile}": known_profile,
            "{configured_fields}": configured_fields,
            "{reply_language}": self.template.agent.language,
        }
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)
        return prompt

    def _format_configured_fields(self) -> str:
        return "\n".join(self._format_item(item) for item in configured_items(self.template))

    def _format_item(self, item: FieldConfig | ContactMethodConfig) -> str:
        parts: list[str] = [
            f"- key={item.key}",
            f"label={item.label}",
            f"type={item.type}",
            f"scope={item.scope}",
        ]
        if isinstance(item, FieldConfig):
            parts.append(f"tier={item.tier}")
            if item.options:
                parts.append(f"options={json.dumps(item.options, ensure_ascii=False)}")
        else:
            parts.append("kind=contact")
        if item.description:
            parts.append(f"description={item.description}")
        if item.examples:
            parts.append(f"examples={json.dumps(item.examples, ensure_ascii=False)}")
        return "; ".join(parts)
