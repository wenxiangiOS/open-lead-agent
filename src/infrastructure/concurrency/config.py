"""
并发配置 - 统一管理所有并发相关的配置
"""

from pydantic import BaseModel, Field
from typing import Optional


class ConcurrencyConfig(BaseModel):
    """
    并发配置 - 统一管理所有并发相关的配置

    整合了：
    - RedisConfig.max_connections
    - ServerConfig.rate_limit_*
    - AIConfig.rate_limit
    - SecurityConfig.*_rate_limit
    """

    # ========== 连接池配置 ==========
    # Redis 连接池
    redis_pool_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Redis 连接池大小"
    )
    redis_pool_timeout: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Redis 连接超时（秒）"
    )

    # HTTP 连接池（AI API）
    http_pool_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="HTTP 连接池大小"
    )
    http_max_keepalive: int = Field(
        default=10,
        ge=2,
        le=50,
        description="HTTP Keep-Alive 连接数"
    )
    http_timeout: int = Field(
        default=60,
        ge=10,
        le=120,
        description="HTTP 请求超时（秒）"
    )

    # ========== 限流配置 ==========
    # 是否启用限流
    rate_limit_enabled: bool = Field(
        default=True,
        description="是否启用限流"
    )

    # 全局限流
    global_rate_limit: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="全局每分钟请求数限制"
    )
    global_rate_window: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="全局限流时间窗口（秒）"
    )

    # 用户级限流
    user_rate_limit: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="每个用户每分钟请求数限制"
    )
    user_rate_window: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="用户限流时间窗口（秒）"
    )

    # IP 级限流
    ip_rate_limit: int = Field(
        default=200,
        ge=50,
        le=2000,
        description="每个 IP 每分钟请求数限制"
    )

    # ========== 并发控制配置 ==========
    # 最大并发请求数
    max_concurrent_requests: int = Field(
        default=50,
        ge=10,
        le=500,
        description="最大并发请求数"
    )

    # 请求队列大小
    request_queue_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="请求队列大小"
    )

    # 请求超时
    request_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="请求处理超时（秒）"
    )

    # ========== 分级限流配置 ==========
    # 用户等级限流配置
    tier_limits: dict = Field(
        default={
            "free": {"limit": 10, "window": 60},
            "basic": {"limit": 50, "window": 60},
            "pro": {"limit": 100, "window": 60},
            "enterprise": {"limit": 1000, "window": 60},
        },
        description="用户等级限流配置"
    )

    class Config:
        env_prefix = "CONCURRENCY"
        extra = "ignore"
