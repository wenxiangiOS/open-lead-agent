"""
结构化日志模块

提供统一的日志记录接口，支持：
1. 结构化输出（JSON 格式）
2. 自动脱敏
3. 请求追踪
4. 性能指标
"""

import logging
import json
import time
import uuid
from typing import Any, Dict, Optional
from contextlib import contextmanager
from datetime import datetime

from src.config.settings import settings


class StructuredLogger:
    """
    结构化日志记录器

    特性：
    1. JSON 格式输出
    2. 自动脱敏
    3. 追踪ID关联
    4. 性能指标记录
    """

    # 需要脱敏的字段
    SENSITIVE_FIELDS = {
        'phone', 'mobile', 'telephone', 'contact', '联系方式',
        'password', 'passwd', 'pwd', 'token', 'api_key',
        'id_card', 'idcard', 'ssn', 'secret'
    }

    # 脱敏替换符
    MASK_CHAR = '*'

    def __init__(self, name: str):
        """初始化结构化日志记录器

        Args:
            name: 日志记录器名称
        """
        self.logger = logging.getLogger(name)
        self._context = {}

    def with_context(self, **kwargs) -> 'StructuredLogger':
        """添加日志上下文

        Args:
            **kwargs: 上下文字段

        Returns:
            Self for chaining
        """
        self._context.update(kwargs)
        return self

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏处理

        Args:
            data: 原始数据

        Returns:
            Dict[str, Any]: 脱敏后的数据
        """
        sanitized = {}
        for key, value in data.items():
            # 检查是否为敏感字段
            key_lower = key.lower()
            is_sensitive = any(
                field in key_lower
                for field in self.SENSITIVE_FIELDS
            )

            if is_sensitive and value:
                # 脱敏处理
                if isinstance(value, str):
                    if len(value) <= 4:
                        sanitized[key] = self.MASK_CHAR * len(value)
                    else:
                        sanitized[key] = value[:2] + self.MASK_CHAR * 4 + value[-2:]
                else:
                    sanitized[key] = self.MASK_CHAR * 8
            else:
                sanitized[key] = value

        return sanitized

    def _log(
        self,
        level: int,
        event: str,
        message: str = "",
        **kwargs
    ):
        """记录结构化日志

        Args:
            level: 日志级别
            event: 事件名称
            message: 日志消息
            **kwargs: 额外字段
        """
        # 合并上下文
        log_data = {**self._context, **kwargs}

        # 添加基础字段
        log_data.update({
            'event': event,
            'message': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': logging.getLevelName(level)
        })

        # 脱敏
        log_data = self._sanitize(log_data)

        # 输出
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False))

    # ============ 日志级别方法 ============

    def debug(self, event: str, message: str = "", **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, event, message, **kwargs)

    def info(self, event: str, message: str = "", **kwargs):
        """记录 INFO 级别日志"""
        self._log(logging.INFO, event, message, **kwargs)

    def warning(self, event: str, message: str = "", **kwargs):
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, event, message, **kwargs)

    def error(self, event: str, message: str = "", **kwargs):
        """记录 ERROR 级别日志"""
        self._log(logging.ERROR, event, message, **kwargs)

    def critical(self, event: str, message: str = "", **kwargs):
        """记录 CRITICAL 级别日志"""
        self._log(logging.CRITICAL, event, message, **kwargs)

    # ============ 性能记录方法 ============

    @contextmanager
    def measure(self, event: str, **kwargs):
        """测量操作执行时间

        Args:
            event: 事件名称
            **kwargs: 额外字段

        Usage:
            with logger.measure("ai_call", model="gpt-4"):
                result = await ai.generate()
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                event,
                message=f"操作完成，耗时 {duration_ms:.2f}ms",
                duration_ms=round(duration_ms, 2),
                **kwargs
            )

    # ============ 业务日志方法 ============

    def log_user_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """记录用户行为

        Args:
            action: 行为类型
            user_id: 用户ID
            **kwargs: 额外字段
        """
        self.info(
            "user_action",
            message=f"用户行为: {action}",
            action=action,
            user_id=user_id,
            **kwargs
        )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """记录 API 调用

        Args:
            endpoint: API 端点
            method: HTTP 方法
            user_id: 用户ID
            status_code: 状态码
            duration_ms: 执行时间
            **kwargs: 额外字段
        """
        self.info(
            "api_call",
            message=f"{method} {endpoint}",
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )

    def log_error(
        self,
        error: Exception,
        context: str = "",
        **kwargs
    ):
        """记录错误

        Args:
            error: 异常对象
            context: 错误上下文
            **kwargs: 额外字段
        """
        self.error(
            "error",
            message=str(error),
            context=context,
            error_type=type(error).__name__,
            **kwargs
        )


class RequestLogger:
    """请求日志记录器（带追踪ID）"""

    # 追踪ID 上下文变量
    _context = {}

    @classmethod
    def get_request_id(cls) -> str:
        """获取当前请求ID"""
        return cls._context.get('request_id', 'unknown')

    @classmethod
    def set_request_id(cls, request_id: str):
        """设置当前请求ID"""
        cls._context['request_id'] = request_id

    @classmethod
    def clear_request_id(cls):
        """清除当前请求ID"""
        cls._context.pop('request_id', None)

    @classmethod
    @contextmanager
    def request_context(cls, request_id: Optional[str] = None):
        """请求上下文管理器

        Usage:
            with RequestLogger.request_context():
                logger.info("event", message="...")
        """
        request_id = request_id or str(uuid.uuid4())
        cls.set_request_id(request_id)
        try:
            yield request_id
        finally:
            cls.clear_request_id()


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        StructuredLogger: 日志记录器实例
    """
    return StructuredLogger(name)


# ============ 预配置的日志记录器 ============

# API 日志
api_logger = get_logger('api')

# AI 服务日志
ai_logger = get_logger('ai_service')

# Redis 日志
redis_logger = get_logger('redis')

# 业务日志
business_logger = get_logger('business')
