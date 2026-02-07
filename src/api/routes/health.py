"""Health check routes"""

import logging
from fastapi import APIRouter, HTTPException

from src.models.requests import HealthCheckResponse, ErrorResponse
from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.services.chat_service import ChatService
from src.services.redis_service import redis_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])

# Services will be injected during app initialization
ai_service: AIService = None
user_service: UserService = None
chat_service: ChatService = None


def init_services(ai: AIService, user: UserService, chat: ChatService):
    """Initialize services for health check routes"""
    global ai_service, user_service, chat_service
    ai_service = ai
    user_service = user
    chat_service = chat


@router.get(
    "/health",
    summary="服务健康检查",
    description="检查服务整体健康状态，包括AI服务和Redis",
    responses={
        200: {
            "description": "健康检查成功",
            "model": HealthCheckResponse
        },
        500: {
            "description": "健康检查失败",
            "model": ErrorResponse
        }
    }
)
async def health_check() -> HealthCheckResponse:
    """健康检查端点，返回服务状态"""
    if ai_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        # Check AI service health
        ai_healthy = await ai_service.health_check()

        # Check Redis health (if enabled)
        redis_healthy = True
        redis_status = "disabled"
        if redis_service.is_enabled():
            redis_healthy = await redis_service.health_check()
            redis_status = "ok" if redis_healthy else "error"

        # Determine overall status
        if ai_healthy and (redis_healthy or not redis_service.is_enabled()):
            return HealthCheckResponse(
                status="ok",
                message=f"小缘红娘服务运行中🌸 (Redis: {redis_status})",
                version=settings.app_version
            )
        else:
            return HealthCheckResponse(
                status="degraded",
                message=f"服务运行中，但AI或Redis有问题 (Redis: {redis_status})",
                version=settings.app_version
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="服务健康检查失败")


@router.get(
    "/health/concurrency",
    summary="并发健康检查",
    description="检查并发相关组件的健康状态",
    responses={
        200: {
            "description": "成功返回并发健康状态",
            "content": {
                "application/json": {
                    "example": {
                        "config": {
                            "rate_limit_enabled": True,
                            "user_rate_limit": 100,
                            "max_concurrent_requests": 50
                        },
                        "components": {
                            "http_client": True,
                            "redis_async": True,
                            "redis_sync": True
                        }
                    }
                }
            }
        }
    }
)
async def concurrency_health_check():
    """并发健康检查端点"""
    try:
        from src.infrastructure.concurrency import get_concurrency_manager

        manager = get_concurrency_manager()
        health = await manager.health_check()

        return health

    except Exception as e:
        logger.error(f"Concurrency health check failed: {e}")
        raise HTTPException(status_code=500, detail="并发健康检查失败")
