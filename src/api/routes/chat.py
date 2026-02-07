"""Chat routes"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from src.models.requests import ChatResponse, ErrorResponse
from src.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["对话"])

# Service will be injected during app initialization
chat_service: ChatService = None


def init_service(service: ChatService):
    """Initialize chat service"""
    global chat_service
    chat_service = service


@router.post(
    "/api/doubao/chat",
    summary="AI红娘对话",
    description="""
与AI红娘小缘进行对话，收集用户信息并提供匹配服务。

**功能特性：**
- 智能信息收集：称呼、性别、年龄、身高、地区、婚况、联系方式
- 自然对话流程：根据已收集信息智能调整问题
- 联系方式验证：自动验证手机号格式
- 拒绝检测：识别用户拒绝并切换话题
- 对话历史维护：保持上下文连贯性

**对话流程：**
1. 开场打招呼并询问称呼
2. 询问性别、年龄等基本信息
3. 收集地区、婚况等详细信息
4. 最后询问联系方式（手机号/微信）
5. 完成收集后提示等待匹配
""",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "成功返回AI回复",
        },
        400: {
            "description": "请求参数错误",
            "model": ErrorResponse
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def chat(request: Dict[str, Any]) -> ChatResponse:
    """AI红娘对话端点，处理用户消息并返回AI回复"""
    if chat_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"Processing chat request from user: {request.get('accountId')}")

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


@router.post(
    "/api/doubao/welcome",
    summary="生成欢迎消息",
    description="为新用户生成欢迎消息，重置对话状态并开始新的信息收集流程",
    responses={
        200: {
            "description": "成功生成欢迎消息",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "你好呀～我是同城脱单联盟的小缘，帮男生女生脱单牵线的～方便告诉我怎么称呼你呢，称呼你小哥哥还是小姐姐呀哒~",
                        "conversation_reset": True
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
async def welcome(user_id: str) -> Dict[str, Any]:
    """为新用户生成欢迎消息"""
    if chat_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"Generating welcome for user: {user_id}")

        # Generate welcome message
        result = await chat_service.generate_welcome_message(user_id)

        return result

    except Exception as e:
        logger.error(f"Welcome generation error: {e}")
        raise HTTPException(status_code=500, detail="生成欢迎消息时出错")


@router.post(
    "/api/doubao/feedback",
    summary="用户反馈",
    description="收集用户对AI回复的反馈，用于改进服务质量",
    responses={
        200: {
            "description": "成功处理反馈",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "感谢您的反馈！",
                        "feedback_recorded": True
                    }
                }
            }
        },
        400: {
            "description": "反馈参数错误",
            "model": ErrorResponse
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def feedback(
    user_id: str,
    message: str,
    rating: int,
    feedback_type: str = "response"
) -> Dict[str, Any]:
    """处理用户反馈"""
    if chat_service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"Processing feedback from user: {user_id}")

        # Process feedback
        result = await chat_service.process_user_feedback(
            user_id, message, rating, feedback_type
        )

        return result

    except Exception as e:
        logger.error(f"Feedback processing error: {e}")
        raise HTTPException(status_code=500, detail="处理反馈时出错")
