from typing import Any

from fastapi import APIRouter, HTTPException

from src.collection import CollectionEngine
from src.conversation import ChatRequest, ConversationEngine
from src.llm import OpenAICompatibleLLM
from src.storage import MemoryStore
from src.templates import get_active_template


router = APIRouter()
store = MemoryStore()


def _engine() -> ConversationEngine:
    return ConversationEngine(get_active_template(), store, OpenAICompatibleLLM())


@router.get("/api/config/template", tags=["template"])
async def template_config() -> dict[str, Any]:
    template = get_active_template()
    return {"success": True, "template": template.public_dict()}


@router.post("/api/chat", tags=["conversation"])
async def chat(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = ChatRequest(**payload)
        response = await _engine().chat(request)
        return response.model_dump(by_alias=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/collection/next-field", tags=["collection"])
async def next_field(payload: dict[str, Any]) -> dict[str, Any]:
    template = get_active_template()
    profile = payload.get("profile") or {}
    if not isinstance(profile, dict):
        raise HTTPException(status_code=400, detail="profile must be an object")
    field = CollectionEngine(template).next_field(profile)
    return {
        "success": True,
        "template_id": template.template.id,
        "next_field": field.model_dump() if field else None,
    }
