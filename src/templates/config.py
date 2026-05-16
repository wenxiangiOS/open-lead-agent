import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemplateMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str = ""


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = "AI Agent"
    language: str = "zh-CN"
    role: str = "AI 客服"
    tone: str = "友好、简洁、专业。"
    persona: str = ""
    goals: list[str] = Field(default_factory=list)
    behavior_rules: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    welcome_message: str = "你好，请问有什么可以帮你？"


class ConversationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_questions_per_turn: int = 1
    answer_question_before_collection: bool = True
    response_max_chars: int = 240
    allow_handoff: bool = True


class DialogueExampleConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    user: str
    better: str
    worse: str = ""


class DialoguePolicySectionConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    rules: list[str] = Field(default_factory=list)


class DialoguePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    turn_goal: str = ""
    sections: list[DialoguePolicySectionConfig] = Field(default_factory=list)
    examples: list[DialogueExampleConfig] = Field(default_factory=list)


class FieldConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    tier: str = "custom"
    type: str = "text"
    required: bool = False
    priority: int = 100
    ask_limit: int = 1
    options: list[str] = Field(default_factory=list)
    ask: str = ""


class FieldGroupsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    core: list[FieldConfig] = Field(default_factory=list)
    medium: list[FieldConfig] = Field(default_factory=list)
    low: list[FieldConfig] = Field(default_factory=list)

    def flattened_fields(self) -> list[FieldConfig]:
        fields: list[FieldConfig] = []
        fields.extend(self._normalize_group("core", self.core, required=True, ask_limit=2, base=10))
        fields.extend(
            self._normalize_group("medium", self.medium, required=False, ask_limit=1, base=110)
        )
        fields.extend(self._normalize_group("low", self.low, required=False, ask_limit=0, base=210))
        return fields

    def _normalize_group(
        self,
        tier: str,
        fields: list[FieldConfig],
        *,
        required: bool,
        ask_limit: int,
        base: int,
    ) -> list[FieldConfig]:
        normalized = []
        for index, field in enumerate(fields):
            data = field.model_dump()
            if field.tier == "custom":
                data["tier"] = tier
            if "required" not in field.model_fields_set:
                data["required"] = required
            if "ask_limit" not in field.model_fields_set:
                data["ask_limit"] = ask_limit
            if "priority" not in field.model_fields_set:
                data["priority"] = base + index * 10
            normalized.append(FieldConfig(**data))
        return normalized


class ContactMethodConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    type: str = "text"
    required: bool = False
    ask_limit: int = 1
    ask: str = ""


class ContactConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    ask_after_required_fields: bool = True
    privacy_message: str = ""
    methods: list[ContactMethodConfig] = Field(default_factory=list)


class FAQConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    intent: str
    keywords: list[str] = Field(default_factory=list)
    answer: str
    continue_collection: bool = True


class RAGConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    knowledge_base_path: str = ""
    top_k: int = 5
    score_threshold: float = 0.65
    require_citation: bool = True


class TemplateConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    template: TemplateMeta
    agent: AgentConfig = Field(default_factory=AgentConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    dialogue_policy: DialoguePolicyConfig = Field(default_factory=DialoguePolicyConfig)
    field_groups: FieldGroupsConfig = Field(default_factory=FieldGroupsConfig)
    fields: list[FieldConfig] = Field(default_factory=list)
    contact: ContactConfig = Field(default_factory=ContactConfig)
    faq: list[FAQConfig] = Field(default_factory=list)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    source_path: str = ""

    @model_validator(mode="after")
    def hydrate_grouped_fields(self) -> "TemplateConfig":
        if not self.fields:
            self.fields = self.field_groups.flattened_fields()
        return self

    def public_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["summary"] = {
            "field_count": len(self.fields),
            "required_field_count": len([field for field in self.fields if field.required]),
            "core_field_count": len([field for field in self.fields if field.tier == "core"]),
            "medium_field_count": len([field for field in self.fields if field.tier == "medium"]),
            "low_field_count": len([field for field in self.fields if field.tier == "low"]),
            "contact_method_count": len(self.contact.methods),
            "faq_count": len(self.faq),
            "rag_enabled": self.rag.enabled,
        }
        return data


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _templates_dir() -> Path:
    raw = os.getenv("TEMPLATES_DIR", "./templates")
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    return path


@lru_cache(maxsize=16)
def get_active_template(template_id: str | None = None) -> TemplateConfig:
    active_id = template_id or os.getenv("ACTIVE_TEMPLATE", "matchmaking")
    path = _templates_dir() / active_id / "template.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw["source_path"] = str(path)
    return TemplateConfig(**raw)


def reset_template_cache() -> None:
    get_active_template.cache_clear()
