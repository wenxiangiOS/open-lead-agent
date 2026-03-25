"""
统一错误处理中间件

提供更强大的错误处理能力：
1. 请求/响应验证错误
2. 业务逻辑错误
3. 服务层错误
4. 基础设施错误
5. 自动重试机制
"""

import logging
import traceback
import time
import uuid
from typing import Callable, Optional, Any, Dict
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.exceptions import AppException, AIServiceException, StorageException
from src.core.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    统一错误处理中间件

    功能：
    1. 捕获所有异常并统一处理
    2. 添加请求追踪 ID
    3. 记录请求耗时
    4. 自动重试特定错误
    5. 降级处理
    """

    # 可重试的错误类型
    RETRYABLE_ERRORS = (
        ConnectionError,
        TimeoutError,
    )

    # 最大重试次数
    MAX_RETRIES = 2

    def __init__(
        self,
        app: ASGIApp,
        enable_logging: bool = True,
        enable_tracing: bool = True,
        debug_mode: bool = False
    ):
        """
        初始化错误处理中间件

        Args:
            app: ASGI 应用
            enable_logging: 是否启用日志记录
            enable_tracing: 是否启用请求追踪
            debug_mode: 是否启用调试模式（返回详细错误信息）
        """
        super().__init__(app)
        self.enable_logging = enable_logging
        self.enable_tracing = enable_tracing
        self.debug_mode = debug_mode

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        处理请求并捕获所有异常

        Args:
            request: 传入的请求
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 生成请求追踪 ID
        trace_id = str(uuid.uuid4())[:8]
        request.state.trace_id = trace_id

        # 记录开始时间
        start_time = time.time()

        # 添加追踪 ID 到请求上下文
        if self.enable_tracing:
            logger.info(f"[{trace_id}] → {request.method} {request.url.path}")

        try:
            # 尝试处理请求（带重试机制）
            response = await self._process_with_retry(
                request,
                call_next,
                trace_id
            )

            # 添加追踪 ID 到响应头
            if self.enable_tracing:
                response.headers["X-Trace-ID"] = trace_id

            # 记录请求耗时
            duration = time.time() - start_time
            if self.enable_logging and duration > 1.0:  # 只记录超过1秒的请求
                logger.warning(
                    f"[{trace_id}] 慢请求: {request.method} {request.url.path} "
                    f"耗时 {duration:.2f}s"
                )

            return response

        except HTTPException as exc:
            # HTTP 异常直接返回
            return await self._handle_http_exception(exc, request, trace_id)

        except AppException as exc:
            # 应用自定义异常
            return await self._handle_app_exception(exc, request, trace_id)

        except Exception as exc:
            # 未捕获的异常
            return await self._handle_unexpected_exception(exc, request, trace_id)

    async def _process_with_retry(
        self,
        request: Request,
        call_next: Callable,
        trace_id: str,
        retry_count: int = 0
    ) -> Response:
        """
        带重试机制的请求处理

        Args:
            request: 传入的请求
            call_next: 下一个处理器
            trace_id: 追踪 ID
            retry_count: 当前重试次数

        Returns:
            响应对象
        """
        try:
            return await call_next(request)

        except self.RETRYABLE_ERRORS as exc:
            if retry_count < self.MAX_RETRIES:
                retry_count += 1
                logger.warning(
                    f"[{trace_id}] 可重试错误，第 {retry_count} 次重试: {type(exc).__name__}"
                )
                # 指数退避
                await self._backoff(retry_count)
                return await self._process_with_retry(
                    request,
                    call_next,
                    trace_id,
                    retry_count
                )
            else:
                # 超过最大重试次数
                logger.error(
                    f"[{trace_id}] 超过最大重试次数 ({self.MAX_RETRIES}): {type(exc).__name__}"
                )
                raise

    async def _backoff(self, retry_count: int) -> None:
        """指数退避等待"""
        import asyncio
        wait_time = 0.1 * (2 ** (retry_count - 1))  # 0.1s, 0.2s, 0.4s...
        await asyncio.sleep(wait_time)

    async def _handle_http_exception(
        self,
        exc: HTTPException,
        request: Request,
        trace_id: str
    ) -> JSONResponse:
        """处理 HTTP 异常"""
        status_code = exc.status_code

        # 使用已有的错误处理器
        error_response = ErrorHandler.handle(
            exc,
            context=f"{request.method} {request.url.path}",
            user_id=self._get_user_id(request)
        )

        # 添加追踪 ID
        error_response["trace_id"] = trace_id

        # 记录日志
        if status_code >= 500:
            logger.error(f"[{trace_id}] HTTP {status_code}: {exc.detail}")
        elif status_code >= 400:
            logger.warning(f"[{trace_id}] HTTP {status_code}: {exc.detail}")

        return JSONResponse(
            status_code=status_code,
            content=error_response
        )

    async def _handle_app_exception(
        self,
        exc: AppException,
        request: Request,
        trace_id: str
    ) -> JSONResponse:
        """处理应用自定义异常"""
        # 使用已有的错误处理器
        error_response = ErrorHandler.handle(
            exc,
            context=f"{request.method} {request.url.path}",
            user_id=self._get_user_id(request)
        )

        # 添加追踪 ID
        error_response["trace_id"] = trace_id

        # 记录日志
        logger.error(f"[{trace_id}] 应用异常: {exc.error_code} - {exc.message}")

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )

    async def _handle_unexpected_exception(
        self,
        exc: Exception,
        request: Request,
        trace_id: str
    ) -> JSONResponse:
        """处理未预期的异常"""
        # 记录完整的堆栈跟踪
        logger.error(
            f"[{trace_id}] 未捕获的异常: {type(exc).__name__}: {str(exc)}\n"
            f"堆栈: {traceback.format_exc()}"
        )

        error_response = ErrorHandler.handle(
            exc,
            context=f"{request.method} {request.url.path}",
            user_id=self._get_user_id(request)
        )
        error_response["trace_id"] = trace_id

        # 调试模式下返回详细错误信息
        if self.debug_mode:
            error_response["debug"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc().split("\n")
            }

        return JSONResponse(
            status_code=500,
            content=error_response
        )

    def _get_user_id(self, request: Request) -> Optional[str]:
        """从请求中获取用户 ID"""
        # 尝试从多个地方获取用户 ID
        # 1. 请求头
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        # 2. 查询参数
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id

        # 3. 请求体（仅限 POST/PUT）
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                # 注意：这里不能直接读取 body，因为它已经被读取了
                # 需要从其他地方获取
                pass
            except Exception:
                pass

        return None


class ValidationErrorHandler:
    """验证错误处理器"""

    @staticmethod
    def handle_validation_error(error: Exception) -> Dict[str, Any]:
        """
        处理验证错误

        Args:
            error: 验证异常

        Returns:
            错误响应字典
        """
        error_type = type(error).__name__
        error_message = str(error)

        details: Dict[str, Any] = {"type": error_type}

        # 尝试解析 Pydantic 验证错误
        if "validation error" in error_message.lower():
            try:
                errors = []
                for line in error_message.split("\n"):
                    if line.strip():
                        errors.append(line.strip())
                details["errors"] = errors
            except Exception:
                pass
        else:
            details["message"] = error_message

        return {
            "success": False,
            "error": "request_validation_failed",
            "error_code": "VALIDATION_ERROR",
            "details": details,
        }


def create_error_handling_middleware(
    enable_logging: bool = True,
    enable_tracing: bool = True,
    debug_mode: bool = False
) -> ErrorHandlingMiddleware:
    """
    创建错误处理中间件的工厂函数

    Args:
        enable_logging: 是否启用日志记录
        enable_tracing: 是否启用请求追踪
        debug_mode: 是否启用调试模式

    Returns:
        错误处理中间件实例
    """
    return lambda app: ErrorHandlingMiddleware(
        app,
        enable_logging=enable_logging,
        enable_tracing=enable_tracing,
        debug_mode=debug_mode
    )
