"""
会话亲和性管理

支持多实例部署的会话路由机制
"""

import asyncio
import hashlib
import logging
from typing import Optional, Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionAffinityManager:
    """
    会话亲和性管理器

    确保同一用户的请求路由到同一个实例，提高缓存命中率
    """

    def __init__(
        self,
        instance_id: Optional[str] = None,
        redis_client=None,
        affinity_ttl: int = 3600
    ):
        """
        初始化会话亲和性管理器

        Args:
            instance_id: 当前实例ID
            redis_client: Redis 客户端
            affinity_ttl: 亲和性记录的过期时间
        """
        self.instance_id = instance_id or self._generate_instance_id()
        self.redis = redis_client
        self.affinity_ttl = affinity_ttl

        # 本地会话缓存（用于 Redis 不可用时）
        self._local_sessions: Dict[str, str] = {}
        self._session_timestamps: Dict[str, float] = {}

    def _generate_instance_id(self) -> str:
        """生成实例 ID"""
        import uuid
        import socket
        hostname = socket.gethostname()
        return f"{hostname}-{uuid.uuid4().hex[:8]}"

    def get_instance_for_session(self, session_id: str) -> str:
        """
        获取处理指定会话的实例 ID

        Args:
            session_id: 会话 ID

        Returns:
            实例 ID
        """
        # 优先从本地缓存获取
        if session_id in self._local_sessions:
            return self._local_sessions[session_id]

        # 从 Redis 获取
        if self.redis and self._is_redis_available():
            try:
                key = f"session_affinity:{session_id}"
                instance_id = self.redis.get(key)
                if instance_id:
                    # 更新本地缓存
                    self._local_sessions[session_id] = instance_id
                    self._session_timestamps[session_id] = asyncio.get_event_loop().time()
                    return instance_id.decode() if isinstance(instance_id, bytes) else instance_id
            except Exception as e:
                logger.warning(f"从 Redis 获取亲和性失败: {e}")

        # 默认路由到当前实例
        return self.instance_id

    async def set_session_affinity(
        self,
        session_id: str,
        instance_id: Optional[str] = None
    ):
        """
        设置会话亲和性

        Args:
            session_id: 会话 ID
            instance_id: 实例 ID（默认使用当前实例）
        """
        import time
        instance_id = instance_id or self.instance_id

        # 更新本地缓存
        self._local_sessions[session_id] = instance_id
        self._session_timestamps[session_id] = time.time()

        # 持久化到 Redis
        if self.redis and self._is_redis_available():
            try:
                key = f"session_affinity:{session_id}"
                await self.redis.setex(key, self.affinity_ttl, instance_id)
                logger.debug(f"设置会话亲和性: {session_id} -> {instance_id}")
            except Exception as e:
                logger.warning(f"设置亲和性到 Redis 失败: {e}")

    async def remove_session_affinity(self, session_id: str):
        """
        移除会话亲和性（会话结束时调用）

        Args:
            session_id: 会话 ID
        """
        # 从本地缓存移除
        self._local_sessions.pop(session_id, None)
        self._session_timestamps.pop(session_id, None)

        # 从 Redis 移除
        if self.redis and self._is_redis_available():
            try:
                key = f"session_affinity:{session_id}"
                await self.redis.delete(key)
                logger.debug(f"移除会话亲和性: {session_id}")
            except Exception as e:
                logger.warning(f"从 Redis 移除亲和性失败: {e}")

    def _is_redis_available(self) -> bool:
        """检查 Redis 是否可用"""
        try:
            if self.redis:
                self.redis.ping()
                return True
        except:
            pass
        return False

    def get_local_sessions(self) -> Dict[str, str]:
        """获取本地会话映射"""
        return self._local_sessions.copy()

    def cleanup_expired_sessions(self, ttl: int = 3600):
        """
        清理过期的本地会话记录

        Args:
            ttl: 过期时间（秒）
        """
        import time
        current_time = time.time()
        expired_sessions = []

        for session_id, timestamp in self._session_timestamps.items():
            if current_time - timestamp > ttl:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self._local_sessions.pop(session_id, None)
            self._session_timestamps.pop(session_id, None)

        if expired_sessions:
            logger.info(f"清理 {len(expired_sessions)} 个过期会话")


class ConsistentHashRouter:
    """
    一致性哈希路由器

    使用一致性哈希算法将请求路由到不同的实例
    """

    def __init__(self, replicas: int = 150):
        """
        初始化一致性哈希路由器

        Args:
            replicas: 虚拟节点数量（用于更均匀的分布）
        """
        self.replicas = replicas
        self._ring: Dict[int, str] = {}
        self._sorted_keys: List[int] = []
        self._instances: Dict[str, Dict[str, Any]] = {}

    def add_instance(self, instance_id: str, weight: int = 1, metadata: Optional[Dict[str, Any]] = None):
        """
        添加实例到哈希环

        Args:
            instance_id: 实例 ID
            weight: 实例权重（处理能力）
            metadata: 实例元数据（地址、端口等）
        """
        # 移除旧实例（如果存在）
        self.remove_instance(instance_id)

        # 添加虚拟节点
        for i in range(self.replicas * weight):
            key = self._hash(f"{instance_id}:{i}")
            self._ring[key] = instance_id
            self._sorted_keys.append(key)

        # 排序
        self._sorted_keys.sort()

        # 记录实例信息
        import time
        self._instances[instance_id] = {
            "weight": weight,
            "metadata": metadata or {},
            "added_at": time.time()
        }

        logger.info(f"添加实例到哈希环: {instance_id} (权重: {weight})")

    def remove_instance(self, instance_id: str):
        """
        从哈希环移除实例

        Args:
            instance_id: 实例 ID
        """
        keys_to_remove = [
            key for key, inst in self._ring.items()
            if inst == instance_id
        ]

        for key in keys_to_remove:
            del self._ring[key]
            self._sorted_keys.remove(key)

        if instance_id in self._instances:
            del self._instances[instance_id]
            logger.info(f"从哈希环移除实例: {instance_id}")

    def get_instance(self, key: str) -> Optional[str]:
        """
        根据键获取路由的实例

        Args:
            key: 路由键（如用户ID、会话ID）

        Returns:
            实例 ID
        """
        if not self._sorted_keys:
            return None

        # 计算键的哈希值
        hash_value = self._hash(key)

        # 二分查找顺时针第一个节点
        idx = self._bisect_right(self._sorted_keys, hash_value)

        # 如果超出范围，从第一个开始
        if idx == len(self._sorted_keys):
            idx = 0

        ring_key = self._sorted_keys[idx]
        return self._ring[ring_key]

    def get_all_instances(self) -> List[str]:
        """获取所有实例 ID"""
        return list(self._instances.keys())

    def get_instance_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """获取实例信息"""
        return self._instances.get(instance_id)

    def _hash(self, key: str) -> int:
        """计算哈希值"""
        hash_func = hashlib.md5()
        hash_func.update(key.encode())
        hash_hex = hash_func.hexdigest()
        return int(hash_hex[:8], 16)

    def _bisect_right(self, arr: List[int], value: int) -> int:
        """二分查找（找到第一个大于 value 的位置）"""
        left, right = 0, len(arr)
        while left < right:
            mid = (left + right) // 2
            if arr[mid] <= value:
                left = mid + 1
            else:
                right = mid
        return left


class LoadBalancer:
    """
    负载均衡器

    结合会话亲和性和一致性哈希的智能路由
    """

    def __init__(
        self,
        affinity_manager: SessionAffinityManager,
        hash_router: ConsistentHashRouter
    ):
        """
        初始化负载均衡器

        Args:
            affinity_manager: 会话亲和性管理器
            hash_router: 一致性哈希路由器
        """
        self.affinity = affinity_manager
        self.router = hash_router

    async def route_request(
        self,
        session_id: str,
        force_new_instance: bool = False
    ) -> str:
        """
        路由请求到合适的实例

        Args:
            session_id: 会话 ID
            force_new_instance: 是否强制使用新实例

        Returns:
            实例 ID
        """
        # 如果有亲和性且不强制新实例
        if not force_new_instance:
            instance = self.affinity.get_instance_for_session(session_id)
            if instance:
                # 检查实例是否仍然存在
                if instance in self.router.get_all_instances():
                    return instance

        # 使用一致性哈希选择实例
        instance = self.router.get_instance(session_id)
        if instance:
            # 设置亲和性
            await self.affinity.set_session_affinity(session_id, instance)

        return instance or self.affinity.instance_id

    def get_instance_stats(self) -> Dict[str, Any]:
        """
        获取实例统计信息

        Returns:
            统计信息字典
        """
        instances = self.router.get_all_instances()
        local_sessions = self.affinity.get_local_sessions()

        # 统计每个实例的会话数
        session_count = defaultdict(int)
        for instance_id in local_sessions.values():
            session_count[instance_id] += 1

        return {
            "total_instances": len(instances),
            "local_sessions": len(local_sessions),
            "sessions_per_instance": dict(session_count),
            "current_instance": self.affinity.instance_id
        }


# ============================================================================
# 全局实例
# ============================================================================

# 全局会话亲和性管理器
session_affinity_manager: Optional[SessionAffinityManager] = None

# 全局一致性哈希路由器
consistent_hash_router: Optional[ConsistentHashRouter] = None

# 全局负载均衡器
load_balancer: Optional[LoadBalancer] = None


def initialize_load_balancing(redis_client=None, instances: Optional[List[str]] = None):
    """
    初始化负载均衡组件

    Args:
        redis_client: Redis 客户端
        instances: 可用实例列表
    """
    global session_affinity_manager, consistent_hash_router, load_balancer

    # 创建会话亲和性管理器
    session_affinity_manager = SessionAffinityManager(redis_client=redis_client)

    # 创建一致性哈希路由器
    consistent_hash_router = ConsistentHashRouter()

    # 添加实例
    if instances:
        for instance_id in instances:
            consistent_hash_router.add_instance(instance_id)

    # 创建负载均衡器
    load_balancer = LoadBalancer(session_affinity_manager, consistent_hash_router)

    logger.info("负载均衡组件初始化完成")


def get_load_balancer() -> Optional[LoadBalancer]:
    """获取负载均衡器实例"""
    return load_balancer
