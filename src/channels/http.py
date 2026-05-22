"""HTTP 渠道接口，暴露聊天、模板配置和字段收集 API。HTTP channel adapter."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

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
    try:
        template = get_active_template()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Template configuration error") from exc
    return {"success": True, "template": template.public_dict()}


@router.post("/api/chat", tags=["conversation"])
async def chat(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = ChatRequest(**payload)
        response = await _engine().chat(request)
        return response.model_dump(by_alias=True)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Template configuration error") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI response generation failed") from exc


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
