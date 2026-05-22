"""模板配置模型与 YAML 加载。

这个文件维护公开模板结构，并安全加载模板目录内的提示词和配置文件。
"""

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
    persona_file: str = ""
    goals: list[str] = Field(default_factory=list)
    goals_file: str = ""
    behavior_rules: list[str] = Field(default_factory=list)
    behavior_rules_file: str = ""
    boundaries: list[str] = Field(default_factory=list)
    boundaries_file: str = ""
    welcome_message: str = "你好，请问有什么可以帮你？"


class ConversationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_questions_per_turn: int = 1
    answer_question_before_collection: bool = True
    response_max_chars: int = 240
    allow_handoff: bool = True
    stop_message: str = "好的，那这边先不继续追问了。你后面想了解的话再来聊就行。"


class OpeningConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    message: str = ""
    quick_replies: list[str] = Field(default_factory=list)
    greeting_response: str = ""


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

    file: str = ""
    turn_goal: str = ""
    sections: list[DialoguePolicySectionConfig] = Field(default_factory=list)
    examples: list[DialogueExampleConfig] = Field(default_factory=list)


class FieldConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    tier: str = "custom"
    type: str = "text"
    scope: str = "self"
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    extract: bool = True
    validation: str = ""
    risk: str = "normal"
    min_confidence: float = 0.6
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
    scope: str = "contact"
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    extract: bool = True
    validation: str = ""
    risk: str = "high"
    min_confidence: float = 0.8
    required: bool = False
    ask_limit: int = 1
    ask: str = ""


class ContactTriggerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: str = "after_required_fields"
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    min_required_collected: int = 0
    require_all_core_covered: bool = False
    require_all_optional_covered: bool = False


class ContactConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    ask_after_required_fields: bool = True
    trigger: ContactTriggerConfig = Field(default_factory=ContactTriggerConfig)
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


class ExtractionConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    prompt: str = ""
    prompt_file: str = ""


class FieldPermissionRuleConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    intents: list[str] = Field(default_factory=list)
    reply_acts: list[str] = Field(default_factory=list)
    expected_fields: list[str] = Field(default_factory=list)
    allow_fields: list[str] = Field(default_factory=list)
    block_fields: list[str] = Field(default_factory=list)
    allow_mixed_answer: bool = True
    reason: str = ""


class FieldPermissionsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    faq_blocks_fields_by_default: bool = True
    contact_context_blocks_profile_fields: bool = True
    short_answer_binds_to_expected_field: bool = True
    rules: list[FieldPermissionRuleConfig] = Field(default_factory=list)


class FieldRoutingOverrideConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_field: str = Field(default="", alias="from")
    to: str
    weight: int = 50
    hint: str = ""


class FieldRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    mode: str = "auto"
    prefer_contextual_followup: bool = True
    overrides: list[FieldRoutingOverrideConfig] = Field(default_factory=list)


class ComplianceConditionConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: str = ""
    operator: str = "equals"
    value: Any = None
    in_values: list[Any] = Field(default_factory=list, alias="in")


class ComplianceRuleConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    description: str = ""
    when: ComplianceConditionConfig = Field(default_factory=ComplianceConditionConfig)
    semantic_signals: list[str] = Field(default_factory=list)
    semantic_min_confidence: float = 0.7
    action: str = "end"
    message: str = ""


class ComplianceConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    rules: list[ComplianceRuleConfig] = Field(default_factory=list)


class ClosingTriggerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    after_contact_collected: bool = False
    after_contact_covered: bool = False
    when_no_next_action: bool = True


class ClosingConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    trigger: ClosingTriggerConfig = Field(default_factory=ClosingTriggerConfig)
    message: str = "好的，我这边先帮你记下了，后续有合适进展会再跟你沟通。"


class HumanizationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    enforce_target_consistency: bool = True
    avoid_repeated_openings: bool = True
    max_active_questions_per_turn: int = 1
    prefer_contextual_followup: bool = True
    avoid_script_like_questions: bool = True
    recent_phrase_window: int = 5


class TemplateConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    template: TemplateMeta
    agent: AgentConfig = Field(default_factory=AgentConfig)
    opening: OpeningConfig = Field(default_factory=OpeningConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    dialogue_policy: DialoguePolicyConfig = Field(default_factory=DialoguePolicyConfig)
    field_groups: FieldGroupsConfig = Field(default_factory=FieldGroupsConfig)
    fields: list[FieldConfig] = Field(default_factory=list)
    field_routing: FieldRoutingConfig = Field(default_factory=FieldRoutingConfig)
    contact: ContactConfig = Field(default_factory=ContactConfig)
    faq: list[FAQConfig] = Field(default_factory=list)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    field_permissions: FieldPermissionsConfig = Field(default_factory=FieldPermissionsConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    closing: ClosingConfig = Field(default_factory=ClosingConfig)
    humanization: HumanizationConfig = Field(default_factory=HumanizationConfig)
    source_path: str = ""

    @model_validator(mode="after")
    def hydrate_grouped_fields(self) -> "TemplateConfig":
        if not self.fields:
            self.fields = self.field_groups.flattened_fields()
        if not self.opening.message and self.agent.welcome_message:
            self.opening.message = self.agent.welcome_message
        return self

    def public_dict(self) -> dict[str, Any]:
        return {
            "template": self.template.model_dump(),
            "agent": {
                "name": self.agent.name,
                "language": self.agent.language,
                "role": self.agent.role,
                "tone": self.agent.tone,
                "welcome_message": self.agent.welcome_message,
            },
            "opening": self.opening.model_dump(),
            "conversation": self.conversation.model_dump(),
            "field_groups": self.field_groups.model_dump(),
            "fields": [field.model_dump() for field in self.fields],
            "field_routing": self.field_routing.model_dump(by_alias=True),
            "contact": self.contact.model_dump(),
            "faq": [item.model_dump() for item in self.faq],
            "rag": {
                "enabled": self.rag.enabled,
                "top_k": self.rag.top_k,
                "score_threshold": self.rag.score_threshold,
                "require_citation": self.rag.require_citation,
            },
            "extraction": {
                "enabled": self.extraction.enabled,
                "custom_prompt": bool(self.extraction.prompt),
            },
            "field_permissions": self.field_permissions.model_dump(),
            "compliance": self.compliance.model_dump(by_alias=True),
            "closing": self.closing.model_dump(),
            "humanization": self.humanization.model_dump(),
            "summary": self.public_summary(),
        }

    def public_summary(self) -> dict[str, Any]:
        return {
            "field_count": len(self.fields),
            "required_field_count": len([field for field in self.fields if field.required]),
            "core_field_count": len([field for field in self.fields if field.tier == "core"]),
            "medium_field_count": len([field for field in self.fields if field.tier == "medium"]),
            "low_field_count": len([field for field in self.fields if field.tier == "low"]),
            "contact_method_count": len(self.contact.methods),
            "faq_count": len(self.faq),
            "rag_enabled": self.rag.enabled,
        }


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_templates_dir() -> Path:
    raw = os.getenv("TEMPLATES_DIR", "./templates")
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _templates_dir() -> Path:
    return get_templates_dir()


def _read_relative_text(base_dir: Path, relative_path: str) -> str:
    path = _resolve_template_reference(base_dir, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"Referenced template file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _resolve_template_reference(base_dir: Path, relative_path: str) -> Path:
    raw_path = Path(relative_path)
    if raw_path.is_absolute():
        raise ValueError(f"Template references must be relative paths: {relative_path}")

    safe_base = base_dir.resolve()
    path = (base_dir / raw_path).resolve()
    if not path.is_relative_to(safe_base):
        raise ValueError(
            f"Template reference must stay inside the template directory: {relative_path}"
        )
    return path


def _read_relative_prompt_text(base_dir: Path, relative_path: str) -> str:
    text = _read_relative_text(base_dir, relative_path)
    lines = text.splitlines()
    first_content_index = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_content_index = index
        break
    return "\n".join(lines[first_content_index:]).strip()


def _read_relative_yaml(base_dir: Path, relative_path: str) -> Any:
    text = _read_relative_text(base_dir, relative_path)
    return yaml.safe_load(text) or []


def _load_template_references(raw: dict[str, Any], base_dir: Path) -> None:
    agent = raw.get("agent") or {}
    if not isinstance(agent, dict):
        return

    if agent.get("persona_file") and not agent.get("persona"):
        agent["persona"] = _read_relative_prompt_text(base_dir, agent["persona_file"])
    if agent.get("goals_file") and not agent.get("goals"):
        agent["goals"] = _read_relative_yaml(base_dir, agent["goals_file"])
    if agent.get("behavior_rules_file") and not agent.get("behavior_rules"):
        agent["behavior_rules"] = _read_relative_yaml(base_dir, agent["behavior_rules_file"])
    if agent.get("boundaries_file") and not agent.get("boundaries"):
        agent["boundaries"] = _read_relative_yaml(base_dir, agent["boundaries_file"])
    raw["agent"] = agent

    dialogue_policy = raw.get("dialogue_policy") or {}
    if not isinstance(dialogue_policy, dict):
        return

    policy_file = dialogue_policy.get("file")
    if policy_file:
        loaded_policy = _read_relative_yaml(base_dir, policy_file)
        if not isinstance(loaded_policy, dict):
            raise ValueError(
                f"Dialogue policy file must be a YAML object: {base_dir / policy_file}"
            )
        merged_policy = {**loaded_policy, **dialogue_policy}
        raw["dialogue_policy"] = merged_policy

    extraction = raw.get("extraction") or {}
    if not isinstance(extraction, dict):
        return
    if extraction.get("prompt_file") and not extraction.get("prompt"):
        extraction["prompt"] = _read_relative_prompt_text(base_dir, extraction["prompt_file"])
    raw["extraction"] = extraction


@lru_cache(maxsize=16)
def get_active_template(template_id: str | None = None) -> TemplateConfig:
    active_id = template_id or os.getenv("ACTIVE_TEMPLATE", "matchmaking")
    path = _templates_dir() / active_id / "template.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _load_template_references(raw, path.parent)
    raw["source_path"] = str(path)
    return TemplateConfig(**raw)


def reset_template_cache() -> None:
    get_active_template.cache_clear()
