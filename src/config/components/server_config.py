"""
服务器配置

包含服务器启动、端口、CORS 等配置
"""

import os
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """服务器配置"""

    # 监听配置
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="监听端口")
    reload: bool = Field(default=False, description="自动重载（开发模式）")

    # 工作进程
    workers: int = Field(default=1, ge=1, le=16, description="工作进程数")
    worker_class: str = Field(default="uvicorn.workers.UvicornWorker", description="Worker 类")

    # 超时配置
    timeout: int = Field(default=120, ge=30, le=600, description="请求超时（秒）")
    keepalive: int = Field(default=5, ge=2, le=75, description="Keep-alive 超时（秒）")

    # 限流配置
    rate_limit_enabled: bool = Field(default=True, description="启用限流")
    rate_limit_requests: int = Field(default=100, ge=1, le=10000, description="限流请求数")
    rate_limit_window: int = Field(default=60, ge=1, le=3600, description="限流时间窗口（秒）")

    # CORS 配置
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="允许的 CORS 源"
    )
    cors_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE"], description="允许的 HTTP 方法")
    cors_headers: list[str] = Field(
        default=["Content-Type", "Authorization", "X-User-ID"],
        description="允许的 HTTP 头"
    )

    @property
    def bind_address(self) -> str:
        """获取绑定地址"""
        return f"{self.host}:{self.port}"

    @property
    def max_requests(self) -> int:
        """最大请求数（用于 Gunicorn）"""
        return self.workers * 1000
