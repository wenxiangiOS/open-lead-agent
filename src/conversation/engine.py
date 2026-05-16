from typing import Any

from pydantic import BaseModel, Field

from src.collection import CollectionEngine
from src.contact import ContactEngine
from src.llm import OpenAICompatibleLLM
from src.rag import RAGEngine
from src.storage import MemoryStore
from src.templates import TemplateConfig


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

        next_field = self.collection.next_field(profile)
        if next_field is None and self.template.contact.ask_after_required_fields:
            next_contact = self.contact.next_contact_method(profile)
            if next_contact is not None:
                next_field = next_contact

        rag_results = self.rag.search(request.question)
        system_prompt = self._build_system_prompt(next_field, rag_results)
        response = await self.llm.generate(system_prompt, request.question)

        if next_field and not response.strip():
            response = next_field.ask or f"Could you share your {next_field.label}?"
        elif next_field and not self.llm.configured:
            response = next_field.ask or f"Could you share your {next_field.label}?"

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

    def _build_system_prompt(self, next_field: Any, rag_results: list[Any]) -> str:
        lines = [
            f"You are {self.template.agent.name}.",
            f"Tone: {self.template.agent.tone}",
            f"Business: {self.template.template.name}",
            "Answer the user naturally. If a next field is provided, ask for it conversationally.",
        ]
        if next_field is not None:
            lines.append(f"Next field to collect: {next_field.key} ({next_field.label}).")
        if rag_results:
            lines.append("Knowledge base context:")
            for result in rag_results:
                lines.append(f"- Source: {result.source}\n{result.content}")
        return "\n".join(lines)
