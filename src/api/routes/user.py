"""User management routes"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from src.models.requests import ErrorResponse
from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["用户数据"])

# Service will be injected during app initialization
chat_service: ChatService = None


def init_service(service: ChatService):
    """Initialize chat service"""
    global chat_service
    chat_service = service


@router.get(
    "/api/doubao/profile/{user_id}",
    summary="获取用户资料",
    description="获取指定用户的完整档案信息，包括已收集的所有个人信息",
    responses={
        200: {
            "description": "成功返回用户资料",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "profile": {
                            "account_id": "user_123",
                            "name": "青青",
                            "gender": "女",
                            "age": "25岁",
                            "height": "165cm",
                            "location": "北京",
                            "marital_status": "单身",
                            "contact": "138****5678",
                            "collection_progress": {
                                "name": True,
                                "gender": True,
                                "age": True,
                                "height": True,
                                "location": True,
                                "marital_status": True,
                                "contact": True
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "用户不存在",
            "model": ErrorResponse
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """获取用户资料"""
    if chat_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"Getting profile for user: {user_id}")

        # Get user profile
        result = await chat_service.get_user_profile(user_id)

        return result

    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料时出错")
