"""API routes initialization - Refactored for better maintainability"""

import logging
import os
import atexit
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.services.chat_service import ChatService
from src.services.redis_service import redis_service
from src.config.settings import settings
from src.config.components.cors_config import CORSConfig
from src.config.validator import validate_config_on_startup, ConfigValidationError
from src.core.error_handler import global_exception_handler

# Import route modules
from src.api.routes import (
    health_router,
    chat_router,
    conversation_router,
    user_router,
    system_router
)

# Import v1 routes (keep for compatibility)
from src.api.v1 import chat as chat_v1
from src.api.middleware.auth import verify_jwt_token

# Import middleware
from src.api.middleware.concurrency import ConcurrencyMiddleware
from src.api.middleware.error_handling import ErrorHandlingMiddleware

# Set up logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# ============================================================================
# CORS Configuration (统一配置管理)
# ============================================================================

# 从环境变量加载 CORS 配置
cors_config = CORSConfig.from_env()

# 如果没有配置源地址，记录警告
if not cors_config.get_origins_list():
    logger.warning("No ALLOWED_ORIGINS configured. Using localhost only. Set ALLOWED_ORIGINS in .env for production.")

# ============================================================================
# Application Initialization
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    description="AI红娘小缘 - 帮助单身男女脱单的智能服务",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS middleware (使用统一配置)
app.add_middleware(CORSMiddleware, **cors_config.to_middleware_kwargs())

# Error handling middleware (统一错误处理)
app.add_middleware(
    ErrorHandlingMiddleware,
    enable_logging=True,
    enable_tracing=True,
    debug_mode=settings.debug_mode if hasattr(settings, 'debug_mode') else False
)

# Concurrency middleware (rate limiting)
app.add_middleware(ConcurrencyMiddleware, enabled=settings.rate_limit_enabled)

# ============================================================================
# Service Initialization
# ============================================================================

ai_service = AIService()
user_service = UserService()
chat_service = ChatService(ai_service, user_service)

# ============================================================================
# Route Registration
# ============================================================================

# Include all route modules
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(user_router)
app.include_router(system_router)

# Include v1 routes for backward compatibility
app.include_router(chat_v1.router, prefix="/api/v1")

# ============================================================================
# Error Handlers
# ============================================================================

# Global exception handlers
app.add_exception_handler(Exception, global_exception_handler)

# ============================================================================
# Lifecycle Events
# ============================================================================

async def async_cleanup_resources():
    """Async cleanup function to close all service connections"""
    try:
        # Close AI service client
        await ai_service.close()
        logger.info("AI service client closed successfully")
    except Exception as e:
        logger.error(f"Error closing AI service client: {e}")

    # Close Redis connection
    if redis_service.is_enabled():
        try:
            await redis_service.close()
            logger.info("Redis connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


def cleanup_resources():
    """Cleanup function to close AI service client"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a task
            loop.create_task(async_cleanup_resources())
        else:
            # If loop is not running, run directly
            loop.run_until_complete(async_cleanup_resources())
    except Exception as e:
        logger.error(f"Error in cleanup_resources: {e}")


# Register cleanup function
atexit.register(cleanup_resources)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    try:
        # Validate configuration
        validate_config_on_startup(settings)

        # Initialize route modules with services
        from src.api.routes.health import init_services as init_health
        from src.api.routes.chat import init_service as init_chat
        from src.api.routes.conversation import init_service as init_conversation
        from src.api.routes.user import init_service as init_user
        from src.api.routes.system import init_service as init_system

        init_health(ai_service, user_service, chat_service)
        init_chat(chat_service)
        init_conversation(chat_service)
        init_user(chat_service)
        init_system(user_service)

        logger.info(f"{settings.app_name} v{settings.app_version} started successfully")
        logger.info(f"Health check available at: http://localhost:8000/health")
        logger.info(f"API documentation available at: http://localhost:8000/docs")

    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down application...")
    await async_cleanup_resources()
    logger.info("Application shutdown complete")


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["根路径"])
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# Export
# ============================================================================

__all__ = ["app"]
