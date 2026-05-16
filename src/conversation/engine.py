from typing import Any

from pydantic import BaseModel, Field

from src.collection import CollectionEngine
from src.contact import ContactEngine
from src.llm import OpenAICompatibleLLM
from src.rag import RAGEngine
from src.storage import MemoryStore
from src.templates import TemplateConfig
from src.templates.config import DialogueExampleConfig, DialoguePolicySectionConfig, FAQConfig


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1, alias="accountId")
    dialog_id: str | None = Field(default=None, alias="dialogId")
    profile: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    success: bool = True
    response: str
    account_id: str
    dialog_id: str | None = None
    collected: dict[str, Any] = Field(default_factory=dict)
    next_field: dict[str, Any] | None = None
    template_id: str
    rag_sources: list[str] = Field(default_factory=list)


class ConversationEngine:
    def __init__(self, template: TemplateConfig, store: MemoryStore, llm: OpenAICompatibleLLM):
        self.template = template
        self.store = store
        self.llm = llm
        self.collection = CollectionEngine(template)
        self.contact = ContactEngine(template)
        self.rag = RAGEngine(template.rag)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        profile = self.store.update_profile(request.account_id, request.profile)
        collected = self.collection.extract_configured_fields(request.profile)
        self.store.append_message(request.account_id, "user", request.question)

        ask_counts = self.store.get_ask_counts(request.account_id)
        next_field = self._next_field_to_collect(profile, ask_counts)

        rag_results = self.rag.search(request.question)
        faq_match = self._match_faq(request.question)
        if faq_match is not None:
            response = self._faq_response(faq_match, next_field)
        else:
            system_prompt = self._build_system_prompt(next_field, rag_results)
            response = await self.llm.generate(system_prompt, request.question)

        if next_field and not response.strip():
            response = next_field.ask or f"请补充一下{next_field.label}可以吗？"
        elif next_field and not self.llm.configured and faq_match is None:
            response = next_field.ask or f"请补充一下{next_field.label}可以吗？"

        response = self._enforce_response_limit(response)
        if next_field:
            self.store.increment_ask_count(request.account_id, next_field.key)
        self.store.append_message(request.account_id, "assistant", response)
        return ChatResponse(
            response=response,
            account_id=request.account_id,
            dialog_id=request.dialog_id,
            collected=collected,
            next_field=next_field.model_dump() if next_field else None,
            template_id=self.template.template.id,
            rag_sources=[result.source for result in rag_results],
        )

    def _next_field_to_collect(self, profile: dict[str, Any], ask_counts: dict[str, int]) -> Any:
        required_field = self.collection.next_required_field(profile, ask_counts)
        if required_field is not None:
            return required_field

        if self.template.contact.ask_after_required_fields:
            contact_method = self.contact.next_contact_method(profile, ask_counts)
            if contact_method is not None:
                return contact_method
            return self.collection.next_optional_field(profile, ask_counts)

        optional_field = self.collection.next_optional_field(profile, ask_counts)
        if optional_field is not None:
            return optional_field
        return self.contact.next_contact_method(profile, ask_counts)

    def _build_system_prompt(self, next_field: Any, rag_results: list[Any]) -> str:
        lines = [
            f"You are {self.template.agent.name}.",
            f"Role: {self.template.agent.role}.",
            f"Reply language: {self.template.agent.language}.",
            f"Tone: {self.template.agent.tone}",
            f"Business: {self.template.template.name}",
            "Always respond in the configured reply language unless the user explicitly "
            "requests another language.",
            "Answer the user naturally. If a next field is provided, ask for it conversationally.",
        ]
        if self.template.agent.persona:
            lines.append(f"Persona:\n{self.template.agent.persona}")
        if self.template.agent.goals:
            lines.append("Goals:")
            lines.extend(f"- {goal}" for goal in self.template.agent.goals)
        if self.template.agent.behavior_rules:
            lines.append("Behavior rules:")
            lines.extend(f"- {rule}" for rule in self.template.agent.behavior_rules)
        if self.template.agent.boundaries:
            lines.append("Boundaries:")
            lines.extend(f"- {boundary}" for boundary in self.template.agent.boundaries)
        lines.extend(self._format_dialogue_policy())
        if next_field is not None:
            lines.append(f"Next field to collect: {next_field.key} ({next_field.label}).")
        if rag_results:
            lines.append("Knowledge base context:")
            for result in rag_results:
                lines.append(f"- Source: {result.source}\n{result.content}")
        return "\n".join(lines)

    def _format_dialogue_policy(self) -> list[str]:
        policy = self.template.dialogue_policy
        lines: list[str] = []
        if policy.turn_goal:
            lines.append(f"Turn goal:\n{policy.turn_goal}")
        for section in policy.sections:
            self._append_policy_section(lines, section)
        if policy.examples:
            lines.append("Dialogue examples:")
            lines.extend(self._format_dialogue_example(example) for example in policy.examples)
        return lines

    def _append_policy_section(
        self, lines: list[str], section: DialoguePolicySectionConfig
    ) -> None:
        if not section.rules:
            return
        lines.append(f"{section.title}:")
        lines.extend(f"- {rule}" for rule in section.rules)

    def _format_dialogue_example(self, example: DialogueExampleConfig) -> str:
        parts = [f"- User: {example.user}", f"  Better: {example.better}"]
        if example.worse:
            parts.append(f"  Worse: {example.worse}")
        return "\n".join(parts)

    def _match_faq(self, question: str) -> FAQConfig | None:
        normalized = question.lower()
        for item in self.template.faq:
            if any(keyword.lower() in normalized for keyword in item.keywords):
                return item
        return None

    def _faq_response(self, faq: FAQConfig, next_field: Any) -> str:
        if not faq.continue_collection or next_field is None:
            return faq.answer
        ask = next_field.ask or f"请补充一下{next_field.label}可以吗？"
        return f"{faq.answer}\n\n{ask}"

    def _enforce_response_limit(self, response: str) -> str:
        max_chars = self.template.conversation.response_max_chars
        if max_chars <= 0 or len(response) <= max_chars:
            return response
        if max_chars <= 3:
            return response[:max_chars]
        return response[: max_chars - 3].rstrip() + "..."
