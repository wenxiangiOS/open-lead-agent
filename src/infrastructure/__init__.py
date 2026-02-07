"""
基础设施模块

提供底层基础设施服务：
- 消息队列
- 缓存策略
- 负载均衡（会话亲和性）
- 并发管理（推荐使用）

注意：旧的 redis_rate_limit 模块已被 concurrency 模块替代
"""

from .queue import MemoryQueue, Task, TaskStatus, task_queue
from .cache import (
    MemoryCache,
    RedisCache,
    HybridCache,
    cached,
    prompt_cache,
    user_cache,
    hybrid_cache
)
from .load_balancer import (
    SessionAffinityManager,
    ConsistentHashRouter,
    LoadBalancer,
    session_affinity_manager,
    consistent_hash_router,
    load_balancer,
    initialize_load_balancing,
    get_load_balancer,
)

# 并发管理模块（推荐使用）
from .concurrency import (
    ConcurrencyManager,
    UnifiedRateLimiter,
    RateLimitResult as ConcurrencyRateLimitResult,
    ConnectionPoolManager,
    ConcurrencyConfig,
    get_concurrency_manager,
)

__all__ = [
    # 消息队列
    'MemoryQueue',
    'Task',
    'TaskStatus',
    'task_queue',
    # 缓存
    'MemoryCache',
    'RedisCache',
    'HybridCache',
    'cached',
    'prompt_cache',
    'user_cache',
    'hybrid_cache',
    # 负载均衡
    'SessionAffinityManager',
    'ConsistentHashRouter',
    'LoadBalancer',
    'session_affinity_manager',
    'consistent_hash_router',
    'load_balancer',
    'initialize_load_balancing',
    'get_load_balancer',
    # 并发管理（推荐使用）
    'ConcurrencyManager',
    'UnifiedRateLimiter',
    'ConcurrencyRateLimitResult',
    'ConnectionPoolManager',
    'ConcurrencyConfig',
    'get_concurrency_manager',
]
