"""
自定义异常类

定义应用中使用的各种异常类型，便于统一错误处理
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class StorageException(AppException):
    """存储相关异常"""

    def __init__(
        self,
        message: str = "存储操作失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            status_code=500,
            details=details
        )


class AIServiceException(AppException):
    """AI 服务相关异常"""

    def __init__(
        self,
        message: str = "AI 服务调用失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            status_code=500,
            details=details
        )


class ValidationException(AppException):
    """数据验证相关异常"""

    def __init__(
        self,
        message: str = "数据验证失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationException(AppException):
    """认证相关异常"""

    def __init__(
        self,
        message: str = "认证失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=401,
            details=details
        )


class RateLimitException(AppException):
    """限流相关异常"""

    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if details is None:
            details = {}
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class ConfigurationException(AppException):
    """配置相关异常"""

    def __init__(
        self,
        message: str = "配置错误",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            status_code=500,
            details=details
        )


class RefusalException(AppException):
    """用户拒绝相关异常（用于业务逻辑）"""

    def __init__(
        self,
        message: str = "用户拒绝继续",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="REFUSAL_DETECTED",
            status_code=200,  # 不是错误，正常返回
            details=details
        )
