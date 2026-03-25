"""Conversation management routes"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from src.models.requests import ErrorResponse
from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["对话管理"])

# Service will be injected during app initialization
chat_service: ChatService = None


def init_service(service: ChatService):
    """Initialize chat service"""
    global chat_service
    chat_service = service


def _http_detail(error_code: str, error: str, **details: Any) -> Dict[str, Any]:
    return {
        "error": error,
        "error_code": error_code,
        "details": details,
    }


@router.get(
    "/api/doubao/history",
    summary="获取对话历史",
    description="获取指定用户的对话历史记录，支持分页查询",
    responses={
        200: {
            "description": "成功返回对话历史",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "history": [
                            {
                                "role": "user",
                                "content": "你好",
                                "timestamp": "2024-01-01T10:00:00"
                            },
                            {
                                "role": "assistant",
                                "content": "你好呀～我是同城脱单联盟的小缘",
                                "timestamp": "2024-01-01T10:00:01"
                            }
                        ],
                        "total": 10,
                        "limit": 10,
                        "offset": 0
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def get_conversation_history(
    user_id: str,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """获取用户对话历史"""
    if chat_service is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("SERVICE_NOT_INITIALIZED", "service_not_initialized", route="conversation_history"),
        )

    try:
        logger.info(f"Getting history for user: {user_id}")

        # Get conversation history
        result = await chat_service.get_user_conversation_history(
            user_id, limit, offset
        )

        return result

    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("CONVERSATION_HISTORY_ERROR", "conversation_history_failed", route="conversation_history"),
        )


@router.post(
    "/api/doubao/reset",
    summary="重置对话",
    description="重置指定用户的对话状态和档案信息，清除所有已收集的数据",
    responses={
        200: {
            "description": "成功重置对话",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "对话已重置",
                        "conversation_reset": True,
                        "profile_cleared": True
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def reset_conversation(user_id: str) -> Dict[str, Any]:
    """重置用户对话"""
    if chat_service is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("SERVICE_NOT_INITIALIZED", "service_not_initialized", route="conversation_reset"),
        )

    try:
        logger.info(f"Resetting conversation for user: {user_id}")

        # Reset conversation
        result = await chat_service.reset_user_conversation(user_id)

        return result

    except Exception as e:
        logger.error(f"Conversation reset error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("CONVERSATION_RESET_ERROR", "conversation_reset_failed", route="conversation_reset"),
        )
