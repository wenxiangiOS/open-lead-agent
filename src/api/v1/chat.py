"""API v1 路由 - 对话相关接口"""

from fastapi import APIRouter, Request
from typing import Dict, Any

from src.models.requests import ChatRequest, ChatResponse
from src.modules.shared.models.use_case_models import ProcessChatTurnCommand
from src.services.core.chat_service import ChatService
from src.core.logging import api_logger, RequestLogger
from src.core.exceptions import AppException

router = APIRouter(prefix="/api/v1", tags=["v1-对话"])

# 由应用启动流程注入，避免 v1 与主路由使用不同服务实例
chat_service: ChatService | None = None


def init_service(service: ChatService) -> None:
    global chat_service
    chat_service = service


async def _process_chat_via_protocol(request_model: ChatRequest) -> Dict[str, Any]:
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)

    use_case = getattr(chat_service, "process_chat_turn_use_case", None)
    if use_case is not None and hasattr(use_case, "execute_command"):
        result = await use_case.execute_command(
            ProcessChatTurnCommand(
                question=request_model.question,
                account_id=request_model.accountId,
                dialog_id=request_model.dialogId,
                sex=request_model.sex,
                timestamp=request_model.timestamp,
            )
        )
        return result.payload or {
            "success": result.success,
            "response": result.response,
            "dialogId": result.dialog_id,
        }
    return await chat_service.process_chat_request(request_model)


@router.post("/chat", response_model=ChatResponse, summary="AI红娘对话 v1")
async def chat_v1(request: ChatRequest, http_request: Request) -> Dict[str, Any]:
    """
    与AI红娘小缘进行对话，收集用户信息并提供匹配服务

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
    """
    # 生成请求ID
    with RequestLogger.request_context() as request_id:
        # 记录开始时间
        import time
        start_time = time.time()

        try:
            # 记录API调用
            api_logger.log_api_call(
                endpoint="/api/v1/chat",
                method="POST",
                user_id=request.accountId
            )

            # 处理聊天请求
            result = await _process_chat_via_protocol(request)

            # 记录成功
            duration_ms = (time.time() - start_time) * 1000
            api_logger.log_api_call(
                endpoint="/api/v1/chat",
                method="POST",
                user_id=request.accountId,
                status_code=200,
                duration_ms=duration_ms,
                success=True
            )

            return result

        except AppException as e:
            # 记录业务错误
            duration_ms = (time.time() - start_time) * 1000
            api_logger.log_error(
                error=e,
                context="chat_v1",
                user_id=request.accountId
            )
            api_logger.log_api_call(
                endpoint="/api/v1/chat",
                method="POST",
                user_id=request.accountId,
                status_code=e.status_code,
                duration_ms=duration_ms,
                success=False
            )
            raise
        except Exception as e:
            # 记录未预期的错误
            duration_ms = (time.time() - start_time) * 1000
            api_logger.log_error(
                error=e,
                context="chat_v1",
                user_id=request.accountId
            )
            raise


@router.post("/welcome", summary="生成欢迎消息 v1")
async def welcome_v1(user_id: str) -> Dict[str, Any]:
    """为新用户生成欢迎消息，重置对话状态并开始新的信息收集流程"""
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)
    with RequestLogger.request_context() as request_id:
        api_logger.log_user_action(
            action="welcome",
            user_id=user_id
        )

        return await chat_service.generate_welcome_message(user_id)


@router.post("/feedback", summary="用户反馈 v1")
async def feedback_v1(
    user_id: str,
    message: str,
    rating: int,
    feedback_type: str = "response"
) -> Dict[str, Any]:
    """收集用户对AI回复的反馈，用于改进服务质量"""
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)
    with RequestLogger.request_context() as request_id:
        api_logger.log_user_action(
            action="feedback",
            user_id=user_id,
            rating=rating,
            feedback_type=feedback_type
        )

        return await chat_service.process_user_feedback(
            user_id, message, rating, feedback_type
        )


@router.get("/history", summary="获取对话历史 v1")
async def get_conversation_history_v1(
    user_id: str,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """获取指定用户的对话历史记录，支持分页查询"""
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)
    with RequestLogger.request_context() as request_id:
        return await chat_service.get_user_conversation_history(
            user_id, limit, offset
        )


@router.get("/profile/{user_id}", summary="获取用户资料 v1")
async def get_user_profile_v1(user_id: str) -> Dict[str, Any]:
    """获取指定用户的完整档案信息，包括已收集的所有个人信息"""
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)
    with RequestLogger.request_context() as request_id:
        return await chat_service.get_user_profile(user_id)


@router.post("/reset", summary="重置对话 v1")
async def reset_conversation_v1(user_id: str) -> Dict[str, Any]:
    """重置指定用户的对话状态和档案信息，清除所有已收集的数据"""
    if chat_service is None:
        raise AppException("服务未初始化", status_code=500)
    with RequestLogger.request_context() as request_id:
        api_logger.log_user_action(
            action="reset_conversation",
            user_id=user_id
        )

        return await chat_service.reset_user_conversation(user_id)
