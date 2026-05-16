import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class TemplateMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str = ""


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = "AI Agent"
    language: str = "zh-CN"
    tone: str = "友好、简洁、专业。"
    welcome_message: str = "你好，请问有什么可以帮你？"


class ConversationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_questions_per_turn: int = 1
    answer_question_before_collection: bool = True
    response_max_chars: int = 240
    allow_handoff: bool = True


class FieldConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    type: str = "text"
    required: bool = False
    priority: int = 100
    ask_limit: int = 1
    options: list[str] = Field(default_factory=list)
    ask: str = ""


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
    fields: list[FieldConfig] = Field(default_factory=list)
    contact: ContactConfig = Field(default_factory=ContactConfig)
    faq: list[FAQConfig] = Field(default_factory=list)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    source_path: str = ""

    def public_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["summary"] = {
            "field_count": len(self.fields),
            "required_field_count": len([field for field in self.fields if field.required]),
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
