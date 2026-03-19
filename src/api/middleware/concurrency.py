"""
并发限流中间件 - 使用新的并发管理器

整合了原本分散的限流中间件：
- src/api/middleware/rate_limit.py
- src/api/middleware/redis_rate_limit.py
- src/api/middleware/tiered_rate_limit.py
"""

import logging
import os
import json
from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.concurrency import get_concurrency_manager

logger = logging.getLogger(__name__)


class ConcurrencyMiddleware(BaseHTTPMiddleware):
    """
    并发限流中间件

    使用新的并发管理器进行限流检查：
    1. 检查用户级限流
    2. 检查 IP 级限流
    3. 添加限流响应头
    """

    def __init__(self, app, enabled: bool = True):
        """
        初始化中间件

        Args:
            app: FastAPI 应用
            enabled: 是否启用限流
        """
        super().__init__(app)
        self.enabled = enabled
        self.manager = get_concurrency_manager()
        trusted_proxies = os.getenv("TRUSTED_PROXY_IPS", "")
        self.trusted_proxy_ips = {ip.strip() for ip in trusted_proxies.split(",") if ip.strip()}

        if not self.enabled:
            logger.warning("ConcurrencyMiddleware is disabled")
        else:
            logger.info("ConcurrencyMiddleware initialized")

    async def dispatch(self, request: Request, call_next):
        """
        处理请求

        Args:
            request: FastAPI 请求
            call_next: 下一个中间件/路由

        Returns:
            Response: HTTP 响应
        """
        if not self.enabled:
            return await call_next(request)

        # 获取客户端标识
        user_id = await self._get_user_id(request)
        client_ip = self._get_client_ip(request)

        # 检查 IP 限流
        ip_result = await self.manager.check_rate_limit(
            f"ip:{client_ip}",
            limit=self.manager.config.ip_rate_limit
        )

        if not ip_result.allowed:
            logger.warning(f"IP rate limit exceeded: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "IP rate limit exceeded",
                    "limit": ip_result.limit,
                    "retry_after": int(ip_result.reset_time - __import__('time').time())
                }
            )

        # 检查用户限流（如果有用户ID）
        if user_id:
            user_result = await self.manager.check_user_rate_limit(user_id)

            if not user_result.allowed:
                logger.warning(f"User rate limit exceeded: {user_id}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "User rate limit exceeded",
                        "limit": user_result.limit,
                        "tier": user_result.tier,
                        "retry_after": int(user_result.reset_time - __import__('time').time())
                    }
                )

            # 保存限流结果到 request.state（供后续使用）
            request.state.rate_limit_result = user_result

        # 处理请求
        response = await call_next(request)

        # 添加限流响应头
        if user_id:
            user_result = getattr(request.state, "rate_limit_result", None)
            if user_result is not None:
                response.headers["X-RateLimit-Limit"] = str(user_result.limit)
                response.headers["X-RateLimit-Remaining"] = str(user_result.remaining)
                response.headers["X-RateLimit-Reset"] = str(int(user_result.reset_time))
            else:
                response.headers["X-RateLimit-Reset"] = str(int(ip_result.reset_time))
        else:
            response.headers["X-RateLimit-Reset"] = str(int(ip_result.reset_time))

        return response

    async def _get_user_id(self, request: Request) -> str:
        """
        从请求中获取用户ID

        Args:
            request: FastAPI 请求

        Returns:
            str: 用户ID
        """
        # 尝试从查询参数获取
        user_id = request.query_params.get("userId")
        if user_id:
            return user_id

        # 回退：从常见 Header 获取
        header_user_id = request.headers.get("X-User-Id")
        if header_user_id:
            return header_user_id

        # 尝试从 JSON body 获取 accountId/userId。
        # Starlette 会缓存 body，不会影响后续路由读取。
        if request.method in {"POST", "PUT", "PATCH"} and request.url.path in self.BODY_USER_ID_PATHS:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        payload = json.loads(body)
                        if isinstance(payload, dict):
                            body_user_id = payload.get("accountId") or payload.get("userId")
                            if isinstance(body_user_id, str) and body_user_id.strip():
                                return body_user_id.strip()
                except Exception:
                    # 限流识别失败时保持降级，不阻塞请求
                    pass

        return None

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端 IP

        Args:
            request: FastAPI 请求

        Returns:
            str: 客户端 IP
        """
        client_host = request.client.host if request.client else None

        # 仅信任受信代理转发的 X-Forwarded-For，避免任意伪造请求头绕过限流
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for and client_host in self.trusted_proxy_ips:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip and client_host in self.trusted_proxy_ips:
            return real_ip

        # 从客户端地址获取
        if client_host:
            return client_host

        return "unknown"
    BODY_USER_ID_PATHS = frozenset({
        "/api/doubao/chat",
        "/api/v1/chat",
        "/api/xiaohongshu/messages/ingest",
    })
