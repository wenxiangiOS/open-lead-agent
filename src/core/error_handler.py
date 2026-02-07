"""
统一错误处理模块

提供统一的错误处理逻辑，包括日志记录、降级策略、用户友好的错误信息等
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from .exceptions import AppException, StorageException, AIServiceException

logger = logging.getLogger(__name__)


class ErrorHandler:
    """统一错误处理器"""

    # 敏感信息关键词（需要脱敏）
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'pwd',
        'token', 'api_key', 'apikey', 'api-key',
        'secret', 'access_key', 'secret_key',
        'phone', 'mobile', 'telephone',
        'id_card', 'idcard', 'ssn'
    ]

    # 用户友好的错误信息映射
    USER_FRIENDLY_MESSAGES = {
        'ConnectionError': '网络连接失败，请检查网络设置',
        'TimeoutError': '请求超时，请稍后重试',
        'RedisError': '缓存服务暂时不可用，正在使用备用存储',
        'ValidationError': '输入数据格式不正确',
        'KeyError': '数据处理异常，请重试',
        'ValueError': '数据值无效',
        'TypeError': '数据类型错误',
    }

    @classmethod
    def handle(
        cls,
        error: Exception,
        context: str = "",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        统一处理错误

        Args:
            error: 异常对象
            context: 错误发生的上下文信息
            user_id: 用户ID（用于日志追踪）

        Returns:
            错误响应字典
        """
        # 1. 记录错误日志
        cls._log_error(error, context, user_id)

        # 2. 尝试恢复（根据错误类型）
        recovery_result = cls._attempt_recovery(error)
        if recovery_result is not None:
            return recovery_result

        # 3. 构建错误响应
        return cls._build_error_response(error)

    @classmethod
    def _log_error(
        cls,
        error: Exception,
        context: str,
        user_id: Optional[str]
    ) -> None:
        """记录错误日志"""
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        # 脱敏处理
        safe_message = cls._sanitize_message(error_message)

        # 构建日志上下文
        log_context = f"[{context}]" if context else ""
        user_info = f"[用户: {user_id}]" if user_id else ""

        # 根据错误类型选择日志级别
        if isinstance(error, (ValueError, TypeError)):
            logger.warning(
                f"{log_context}{user_info} {error_type}: {safe_message}",
                exc_info=False
            )
        else:
            logger.error(
                f"{log_context}{user_info} {error_type}: {safe_message}\n{error_traceback}",
                exc_info=True
            )

    @classmethod
    def _sanitize_message(cls, message: str) -> str:
        """脱敏处理"""
        safe_message = message
        for keyword in cls.SENSITIVE_KEYWORDS:
            # 简单脱敏：将敏感关键词后面的内容替换为 ****
            import re
            pattern = rf'({keyword}["\']?\s*[:=]\s*["\']?)[^"\']+(["\']?)'
            safe_message = re.sub(pattern, rf'\1****\2', safe_message, flags=re.IGNORECASE)
        return safe_message

    @classmethod
    def _attempt_recovery(cls, error: Exception) -> Optional[Dict[str, Any]]:
        """尝试从错误中恢复"""
        # Redis 错误：自动降级到内存存储
        if 'redis' in str(error).lower() or 'Redis' in str(type(error)):
            from src.repositories import get_storage_factory
            factory = get_storage_factory()
            factory.switch_to_memory_only()
            logger.info("已自动切换到内存存储模式")

            # 返回降级提示（不影响用户体验）
            return {
                "success": True,
                "warning": "缓存服务暂时不可用，已切换到备用存储"
            }

        # 其他错误不尝试恢复
        return None

    @classmethod
    def _build_error_response(cls, error: Exception) -> Dict[str, Any]:
        """构建错误响应"""
        # 如果是自定义异常，直接使用其信息
        if isinstance(error, AppException):
            return {
                "success": False,
                "error": error.message,
                "error_code": error.error_code,
                "details": error.details
            }

        # 如果是 HTTPException
        if isinstance(error, HTTPException):
            return {
                "success": False,
                "error": error.detail,
                "error_code": f"HTTP_{error.status_code}",
                "details": {}
            }

        # 其他异常：使用友好的错误信息
        error_type = type(error).__name__
        friendly_message = cls.USER_FRIENDLY_MESSAGES.get(
            error_type,
            "服务暂时不可用，请稍后重试"
        )

        return {
            "success": False,
            "error": friendly_message,
            "error_code": "INTERNAL_ERROR",
            "details": {
                "type": error_type,
                "message": str(error) if logger.level <= logging.DEBUG else None
            }
        }


def handle_error(
    error: Exception,
    context: str = "",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    便捷的错误处理函数

    Args:
        error: 异常对象
        context: 错误上下文
        user_id: 用户ID

    Returns:
        错误响应字典
    """
    return ErrorHandler.handle(error, context, user_id)


# FastAPI 全局异常处理器
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI 全局异常处理器"""
    error_response = handle_error(
        exc,
        context=f"{request.method} {request.url.path}",
        user_id=request.headers.get("X-User-ID")
    )

    # 确定状态码
    status_code = 500
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
    elif isinstance(exc, AppException):
        status_code = exc.status_code

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )
