"""
分布式锁实现

支持多实例部署的分布式锁机制
"""

import asyncio
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DistributedLock:
    """
    分布式锁

    基于 Redis 实现分布式锁，支持多实例部署
    """

    def __init__(
        self,
        redis_client,
        key: str,
        ttl: int = 10,
        auto_extend: bool = False
    ):
        """
        初始化分布式锁

        Args:
            redis_client: Redis 客户端
            key: 锁的键名
            ttl: 锁的过期时间（秒）
            auto_extend: 是否自动延长锁
        """
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.auto_extend = auto_extend
        self.identifier = str(uuid.uuid4())
        self._locked = False
        self._extend_task: Optional[asyncio.Task] = None

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        获取锁

        Args:
            timeout: 等待超时时间（秒），None 表示不等待

        Returns:
            是否成功获取锁
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # 尝试获取锁（使用 SET NX EX 命令）
            acquired = await self.redis.set(
                self.key,
                self.identifier,
                nx=True,
                ex=self.ttl
            )

            if acquired:
                self._locked = True
                logger.debug(f"获取锁成功: {self.key}")

                # 自动延长锁
                if self.auto_extend:
                    self._extend_task = asyncio.create_task(self._extend_lock())

                return True

            # 检查超时
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.debug(f"获取锁超时: {self.key}")
                    return False

            # 短暂等待后重试
            await asyncio.sleep(0.01)

    async def release(self) -> bool:
        """
        释放锁

        Returns:
            是否成功释放锁
        """
        if not self._locked:
            return False

        # 停止自动延长任务
        if self._extend_task:
            self._extend_task.cancel()
            try:
                await self._extend_task
            except asyncio.CancelledError:
                pass

        # 使用 Lua 脚本确保只释放自己持有的锁
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await self.redis.eval(script, 1, self.key, self.identifier)

        if result:
            self._locked = False
            logger.debug(f"释放锁成功: {self.key}")
            return True

        logger.warning(f"释放锁失败: 锁已过期或被其他客户端持有: {self.key}")
        return False

    async def _extend_lock(self):
        """
        自动延长锁

        定期延长锁的过期时间，防止长时间操作导致锁过期
        """
        try:
            while self._locked:
                await asyncio.sleep(self.ttl / 2)

                # 延长锁
                script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("expire", KEYS[1], ARGV[2])
                else
                    return 0
                end
                """

                result = await self.redis.eval(script, 1, self.key, self.identifier, self.ttl)

                if not result:
                    logger.warning(f"延长锁失败: {self.key}")
                    break

                logger.debug(f"延长锁成功: {self.key}")

        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.release()

    @property
    def is_locked(self) -> bool:
        """是否持有锁"""
        return self._locked


class LockManager:
    """锁管理器"""

    def __init__(self, redis_client):
        """
        初始化锁管理器

        Args:
            redis_client: Redis 客户端
        """
        self.redis = redis_client

    async def acquire_lock(
        self,
        key: str,
        ttl: int = 10,
        timeout: Optional[float] = None
    ) -> Optional[DistributedLock]:
        """
        获取锁

        Args:
            key: 锁的键名
            ttl: 锁的过期时间
            timeout: 等待超时时间

        Returns:
            锁对象，获取失败返回 None
        """
        lock = DistributedLock(self.redis, key, ttl)

        if await lock.acquire(timeout):
            return lock

        return None

    async def run_with_lock(
        self,
        key: str,
        func,
        *args,
        ttl: int = 10,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """
        在锁保护下执行函数

        Args:
            key: 锁的键名
            func: 要执行的函数
            *args: 位置参数
            ttl: 锁的过期时间
            timeout: 等待超时时间
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 函数执行异常
            TimeoutError: 获取锁超时
        """
        async with DistributedLock(self.redis, key, ttl) as lock:
            # 等待获取锁
            if not await lock.acquire(timeout):
                raise TimeoutError(f"获取锁超时: {key}")

            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            finally:
                await lock.release()


# ============================================================================
# 装饰器
# ============================================================================

def distributed_lock(
    key_func: Optional[callable] = None,
    ttl: int = 10,
    timeout: Optional[float] = None
):
    """
    分布式锁装饰器

    Args:
        key_func: 生成锁键名的函数，接收被装饰函数的参数
        ttl: 锁的过期时间
        timeout: 等待超时时间

    Usage:
        @distributed_lock(key_func=lambda user_id: f"user:{user_id}")
        async def process_user_data(user_id):
            ...

        @distributed_lock(key_func=lambda args: f"chat:{args[0]}")
        async def process_chat(user_id, message):
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成锁键名
            if key_func:
                lock_key = key_func(args, kwargs)
            else:
                lock_key = f"{func.__name__}:{str(args)}"

            # 获取 Redis 客户端
            from src.services.redis_service import redis_service
            if not redis_service.is_enabled():
                # Redis 未启用，直接执行
                return await func(*args, **kwargs)

            # 获取锁并执行
            lock_manager = LockManager(redis_service.client)
            return await lock_manager.run_with_lock(
                lock_key,
                func,
                *args,
                ttl=ttl,
                timeout=timeout,
                **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数暂不支持
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
