"""API routes for the application"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from src.models.requests import (
    ChatRequest,
    HealthCheckResponse,
    ChatResponse,
    ErrorResponse,
    UserProfileRequest,
    ConversationHistoryRequest,
    UserInsightsResponse
)
from src.models.personality import PersonalityProfile
from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.services.chat_service import ChatService
from src.config.settings import settings

# Set up logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize services
ai_service = AIService()
user_service = UserService()
chat_service = ChatService(ai_service, user_service)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="小缘（同城脱单联盟）AI红娘服务API"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint"""
    try:
        # Check AI service health
        ai_healthy = await ai_service.health_check()

        if ai_healthy:
            return HealthCheckResponse(
                status="ok",
                message="小缘红娘服务运行中🌸",
                version=settings.app_version
            )
        else:
            return HealthCheckResponse(
                status="degraded",
                message="服务运行中，但AI服务有问题",
                version=settings.app_version
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="服务健康检查失败")


@app.post("/api/doubao/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint"""
    try:
        logger.info(f"Processing chat request from user: {request.accountId}")

        # Process the chat request
        result = await chat_service.process_chat_request(request)

        # Convert to response model
        return ChatResponse(**result)

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="处理聊天请求时出错")


@app.post("/api/doubao/welcome")
async def welcome(user_id: str) -> Dict[str, Any]:
    """Welcome endpoint for new users"""
    try:
        logger.info(f"Generating welcome for user: {user_id}")

        # Generate welcome message
        result = await chat_service.generate_welcome_message(user_id)

        return result

    except Exception as e:
        logger.error(f"Welcome generation error: {e}")
        raise HTTPException(status_code=500, detail="生成欢迎消息时出错")


@app.post("/api/doubao/feedback")
async def feedback(
    user_id: str,
    message: str,
    rating: int,
    feedback_type: str = "response"
) -> Dict[str, Any]:
    """Feedback endpoint"""
    try:
        logger.info(f"Processing feedback from user: {user_id}")

        # Process feedback
        result = await chat_service.process_user_feedback(
            user_id, message, rating, feedback_type
        )

        return result

    except ValueError as e:
        logger.warning(f"Feedback validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Feedback processing error: {e}")
        raise HTTPException(status_code=500, detail="处理反馈时出错")


@app.get("/api/doubao/history")
async def get_conversation_history(
    user_id: str,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """Get conversation history endpoint"""
    try:
        logger.info(f"Getting history for user: {user_id}")

        # Get conversation history
        result = await chat_service.get_user_conversation_history(
            user_id, limit, offset
        )

        return result

    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取对话历史时出错")


@app.get("/api/doubao/profile/{user_id}")
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile endpoint"""
    try:
        logger.info(f"Getting profile for user: {user_id}")

        # Get user profile
        result = await chat_service.get_user_profile(user_id)

        return result

    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料时出错")


@app.post("/api/doubao/reset")
async def reset_conversation(user_id: str) -> Dict[str, Any]:
    """Reset conversation endpoint"""
    try:
        logger.info(f"Resetting conversation for user: {user_id}")

        # Reset conversation
        result = await chat_service.reset_user_conversation(user_id)

        return result

    except Exception as e:
        logger.error(f"Conversation reset error: {e}")
        raise HTTPException(status_code=500, detail="重置对话时出错")


@app.get("/api/doubao/stats")
async def get_statistics() -> Dict[str, Any]:
    """Get service statistics endpoint"""
    try:
        logger.info("Getting service statistics")

        # Get user statistics
        stats = user_service.get_user_statistics()

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Statistics retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息时出错")


@app.get("/api/doubao/personality")
async def get_personality_profile() -> Dict[str, Any]:
    """Get personality profile endpoint"""
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return ErrorResponse(
        success=False,
        error=exc.detail,
        error_code=f"HTTP_{exc.status_code}",
        details={"status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        success=False,
        error="内部服务器错误",
        error_code="INTERNAL_ERROR"
    )


# Root endpoint for basic info
@app.get("/api")
async def api_info() -> Dict[str, Any]:
    """API information endpoint"""
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
            "health": "/health"
        },
        "timestamp": datetime.now().isoformat()
    }