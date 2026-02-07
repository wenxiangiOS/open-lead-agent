"""
并发管理模块

统一管理所有并发相关的功能：
- 限流器
- 连接池
- 信号量
- 并发配置
"""

from .manager import ConcurrencyManager
from .rate_limiter import UnifiedRateLimiter, RateLimitResult
from .connection_pool import ConnectionPoolManager
from .config import ConcurrencyConfig

__all__ = [
    'ConcurrencyManager',
    'UnifiedRateLimiter',
    'RateLimitResult',
    'ConnectionPoolManager',
    'ConcurrencyConfig',
]

# 全局并发管理器实例
_concurrency_manager: ConcurrencyManager = None


def get_concurrency_manager() -> ConcurrencyManager:
    """获取全局并发管理器实例"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager
