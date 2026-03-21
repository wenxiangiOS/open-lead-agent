"""System information routes"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException

from src.models.requests import ErrorResponse
from src.models.personality import PersonalityProfile
from src.services.data.user_service import UserService
from src.services.queue.queue_store import QueueStore
from src.services.ai_service import AIService
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["系统"])

# Service will be injected during app initialization
user_service: UserService = None
queue_store: QueueStore | None = None




def _safe_rate(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(float(num) / float(den), 4)

def init_service(service: UserService, mq_store: QueueStore | None = None):
    """Initialize user service"""
    global user_service, queue_store
    user_service = service
    queue_store = mq_store


@router.get(
    "/api/doubao/stats",
    summary="获取服务统计",
    description="获取服务运行统计数据，包括用户数量、消息数量等",
    responses={
        200: {
            "description": "成功返回统计数据",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "statistics": {
                            "total_users": 100,
                            "active_users": 50,
                            "total_messages": 1000,
                            "profiles_completed": 30
                        },
                        "timestamp": "2024-01-01T10:00:00"
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
async def get_statistics() -> Dict[str, Any]:
    """获取服务统计数据"""
    if user_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info("Getting service statistics")

        # Get user statistics (synchronous method)
        stats = user_service.get_user_statistics()
        if queue_store is not None:
            stats["message_queue"] = await queue_store.get_queue_metrics()

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Statistics retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息时出错")


@router.get(
    "/api/doubao/personality",
    summary="获取AI人设",
    description="获取AI红娘小缘的人格设定和对话风格配置",
    responses={
        200: {
            "description": "成功返回AI人设",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "personality": {
                            "name": "小缘",
                            "role": "AI红娘",
                            "style": "温柔可爱、专业热情",
                            "traits": [
                                "善于引导对话",
                                "情商高、说话委婉",
                                "自然流畅的对话风格"
                            ]
                        },
                        "timestamp": "2024-01-01T10:00:00"
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
async def get_personality_profile() -> Dict[str, Any]:
    """获取AI红娘人设配置"""
    try:
        # Get personality profile
        personality = PersonalityProfile()

        return {
            "success": True,
            "personality": personality.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Personality retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取人格设定时出错")


@router.get("/api/doubao/mq/dashboard", summary="消息队列看板")
async def get_message_queue_dashboard() -> Dict[str, Any]:
    if queue_store is None:
        raise HTTPException(status_code=500, detail="消息队列未初始化")

    try:
        mq = await queue_store.get_queue_metrics()
        ingest_total = int(mq.get("ingest_total", 0))
        ingest_accepted = int(mq.get("ingest_accepted", 0))
        outbox_created = int(mq.get("outbox_created", 0))
        outbox_success = int(mq.get("outbox_delivery_success", 0))

        return {
            "success": True,
            "dashboard": {
                "snapshot": mq,
                "ratios": {
                    "ingest_accept_rate": _safe_rate(ingest_accepted, ingest_total),
                    "delivery_success_rate": _safe_rate(outbox_success, outbox_created),
                    "turn_success_rate": _safe_rate(int(mq.get("turn_succeeded", 0)), int(mq.get("turn_started", 0))),
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"MQ dashboard retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取消息队列看板时出错")


@router.get(
    "/api/doubao/token-usage",
    summary="获取大模型 Token 用量",
    description="返回进程内累计的大模型 token 使用统计（输入/输出/总量/调用次数）",
)
async def get_token_usage() -> Dict[str, Any]:
    try:
        usage = await AIService.get_token_usage()
        return {
            "success": True,
            "token_usage": usage,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Token usage retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取 token 用量时出错")


@router.post(
    "/api/doubao/token-usage/reset",
    summary="重置大模型 Token 用量统计",
    description="将进程内累计的大模型 token 使用统计清零",
)
async def reset_token_usage() -> Dict[str, Any]:
    try:
        await AIService.reset_token_usage()
        return {
            "success": True,
            "message": "token usage reset",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Token usage reset error: {e}")
        raise HTTPException(status_code=500, detail="重置 token 用量时出错")


@router.get(
    "/api",
    summary="API信息",
    description="获取API基本信息和所有可用端点列表",
    responses={
        200: {
            "description": "成功返回API信息",
            "content": {
                "application/json": {
                    "example": {
                        "service": "小缘红娘服务",
                        "version": "1.0.0",
                        "endpoints": {
                            "chat": "/api/doubao/chat",
                            "welcome": "/api/doubao/welcome",
                            "feedback": "/api/doubao/feedback",
                            "history": "/api/doubao/history",
                            "profile": "/api/doubao/profile/{user_id}",
                            "reset": "/api/doubao/reset",
                            "stats": "/api/doubao/stats",
                            "personality": "/api/doubao/personality",
                            "health": "/health"
                        },
                        "timestamp": "2024-01-01T10:00:00"
                    }
                }
            }
        }
    }
)
async def api_info() -> Dict[str, Any]:
    """API信息端点，返回服务基本信息和端点列表"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "chat": "/api/doubao/chat",
            "welcome": "/api/doubao/welcome",
            "feedback": "/api/doubao/feedback",
            "history": "/api/doubao/history",
            "profile": "/api/doubao/profile/{user_id}",
            "reset": "/api/doubao/reset",
            "stats": "/api/doubao/stats",
            "personality": "/api/doubao/personality",
            "mq_dashboard": "/api/doubao/mq/dashboard",
            "token_usage": "/api/doubao/token-usage",
            "token_usage_reset": "/api/doubao/token-usage/reset",
            "health": "/health"
        },
        "timestamp": datetime.now().isoformat()
    }
