"""
钩子管理器

实现事件驱动的插件系统
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


# ============================================================================
# 钩子优先级
# ============================================================================

class HookPriority(Enum):
    """钩子优先级"""
    HIGHEST = 0    # 最高优先级
    HIGH = 10      # 高优先级
    NORMAL = 50    # 正常优先级
    LOW = 90       # 低优先级
    LOWEST = 100   # 最低优先级


# ============================================================================
# 钩子元数据
# ============================================================================

@dataclass
class HookMetadata:
    """
    钩子元数据

    Attributes:
        callback: 回调函数
        priority: 优先级
        plugin: 所属插件（可选）
        once: 是否只执行一次
        condition: 执行条件（可选）
    """
    callback: Callable
    priority: int = HookPriority.NORMAL.value
    plugin: Optional[Any] = None
    once: bool = False
    condition: Optional[Callable] = None

    def __post_init__(self):
        self._call_count = 0

    @property
    def should_execute(self) -> bool:
        """是否应该执行"""
        if self.once and self._call_count > 0:
            return False
        if self.condition and not self.condition():
            return False
        return True

    def mark_called(self):
        """标记已调用"""
        self._call_count += 1


# ============================================================================
# 钩子执行结果
# ============================================================================

@dataclass
class HookResult:
    """
    钩子执行结果

    Attributes:
        callback: 回调函数
        success: 是否成功
        result: 返回值
        error: 异常（如果有）
        execution_time: 执行时间（毫秒）
    """
    callback: Callable
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0


# ============================================================================
# 钩子管理器
# ============================================================================

class HookManager:
    """
    钩子管理器

    负责管理所有插件钩子的注册和触发
    """

    def __init__(self):
        """初始化钩子管理器"""
        self._hooks: Dict[str, List[HookMetadata]] = defaultdict(list)
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 1000

        logger.info("钩子管理器初始化完成")

    # ========================================================================
    # 钩子注册
    # ========================================================================

    def register(
        self,
        event: str,
        callback: Callable,
        priority: int = HookPriority.NORMAL.value,
        plugin: Optional[Any] = None,
        once: bool = False,
        condition: Optional[Callable] = None
    ):
        """
        注册钩子

        Args:
            event: 事件名称
            callback: 回调函数
            priority: 优先级（数值越小优先级越高）
            plugin: 所属插件
            once: 是否只执行一次
            condition: 执行条件函数

        Usage:
            def on_user_login(user_id):
                print(f"用户登录: {user_id}")

            hook_manager.register("user.login", on_user_login)
        """
        metadata = HookMetadata(
            callback=callback,
            priority=priority,
            plugin=plugin,
            once=once,
            condition=condition
        )

        self._hooks[event].append(metadata)

        # 按优先级排序
        self._hooks[event].sort(key=lambda h: h.priority)

        logger.debug(f"注册钩子: {event} -> {callback.__name__}")

    def unregister(self, event: str, callback: Callable):
        """
        取消注册钩子

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self._hooks:
            self._hooks[event] = [
                h for h in self._hooks[event]
                if h.callback != callback
            ]
            logger.debug(f"取消注册钩子: {event} -> {callback.__name__}")

    def unregister_plugin(self, plugin: Any):
        """
        取消注册插件的所有钩子

        Args:
            plugin: 插件实例
        """
        for event in list(self._hooks.keys()):
            self._hooks[event] = [
                h for h in self._hooks[event]
                if h.plugin is not plugin
            ]

            if not self._hooks[event]:
                del self._hooks[event]

        logger.debug(f"取消注册插件的所有钩子: {plugin}")

    # ========================================================================
    # 事件触发
    # ========================================================================

    async def emit(self, event: str, *args, **kwargs) -> List[HookResult]:
        """
        触发事件（异步）

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            所有钩子的执行结果列表

        Usage:
            await hook_manager.emit("user.login", user_id="123")
        """
        if event not in self._hooks:
            return []

        start_time = time.time()
        results = []
        hooks_to_remove = []

        # 复制钩子列表，避免在执行过程中修改
        hooks = self._hooks[event][:]

        for hook in hooks:
            if not hook.should_execute:
                continue

            try:
                hook_start = time.time()

                # 判断回调是否是协程函数
                if asyncio.iscoroutinefunction(hook.callback):
                    result = await hook.callback(*args, **kwargs)
                else:
                    result = hook.callback(*args, **kwargs)

                execution_time = (time.time() - hook_start) * 1000

                results.append(HookResult(
                    callback=hook.callback,
                    success=True,
                    result=result,
                    execution_time=execution_time
                ))

                hook.mark_called()

                # 标记一次性钩子待删除
                if hook.once:
                    hooks_to_remove.append(hook)

            except Exception as e:
                logger.error(f"钩子执行失败 {event} -> {hook.callback.__name__}: {e}")

                results.append(HookResult(
                    callback=hook.callback,
                    success=False,
                    error=e
                ))

        # 移除一次性钩子
        for hook in hooks_to_remove:
            self._hooks[event].remove(hook)

        # 记录事件历史
        total_time = (time.time() - start_time) * 1000
        self._record_event(event, results, total_time)

        return results

    def emit_sync(self, event: str, *args, **kwargs) -> List[HookResult]:
        """
        触发事件（同步）

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            所有钩子的执行结果列表
        """
        if event not in self._hooks:
            return []

        start_time = time.time()
        results = []
        hooks_to_remove = []

        hooks = self._hooks[event][:]

        for hook in hooks:
            if not hook.should_execute:
                continue

            try:
                hook_start = time.time()
                result = hook.callback(*args, **kwargs)
                execution_time = (time.time() - hook_start) * 1000

                results.append(HookResult(
                    callback=hook.callback,
                    success=True,
                    result=result,
                    execution_time=execution_time
                ))

                hook.mark_called()

                if hook.once:
                    hooks_to_remove.append(hook)

            except Exception as e:
                logger.error(f"钩子执行失败 {event} -> {hook.callback.__name__}: {e}")

                results.append(HookResult(
                    callback=hook.callback,
                    success=False,
                    error=e
                ))

        for hook in hooks_to_remove:
            self._hooks[event].remove(hook)

        total_time = (time.time() - start_time) * 1000
        self._record_event(event, results, total_time)

        return results

    # ========================================================================
    # 事件监听
    # ========================================================================

    def listen(self, event: str):
        """
        事件监听装饰器

        Args:
            event: 事件名称

        Usage:
            @hook_manager.listen("user.login")
            def on_user_login(user_id):
                print(f"用户登录: {user_id}")
        """
        def decorator(callback: Callable):
            self.register(event, callback)
            return callback
        return decorator

    def listen_once(self, event: str):
        """
        一次性事件监听装饰器

        Args:
            event: 事件名称

        Usage:
            @hook_manager.listen_once("app.shutdown")
            def on_shutdown():
                print("应用关闭")
        """
        def decorator(callback: Callable):
            self.register(event, callback, once=True)
            return callback
        return decorator

    def listen_with_priority(self, event: str, priority: int):
        """
        带优先级的事件监听装饰器

        Args:
            event: 事件名称
            priority: 优先级

        Usage:
            @hook_manager.listen_with_priority("user.login", priority=10)
            def on_user_login_high(user_id):
                print("高优先级处理")
        """
        def decorator(callback: Callable):
            self.register(event, callback, priority=priority)
            return callback
        return decorator

    # ========================================================================
    # 事件过滤
    # ========================================================================

    def filter(self, event: str, condition: Callable):
        """
        条件事件监听装饰器

        Args:
            event: 事件名称
            condition: 条件函数

        Usage:
            @hook_manager.filter("user.login", condition=lambda: user_id != "admin")
            def on_user_login(user_id):
                print(f"普通用户登录: {user_id}")
        """
        def decorator(callback: Callable):
            self.register(event, callback, condition=condition)
            return callback
        return decorator

    # ========================================================================
    # 钩子查询
    # ========================================================================

    def get_hooks(self, event: str) -> List[HookMetadata]:
        """获取指定事件的所有钩子"""
        return self._hooks.get(event, [])[:]

    def has_hooks(self, event: str) -> bool:
        """检查事件是否有钩子"""
        return event in self._hooks and len(self._hooks[event]) > 0

    def get_all_events(self) -> Set[str]:
        """获取所有已注册的事件"""
        return set(self._hooks.keys())

    def get_hook_count(self, event: str) -> int:
        """获取指定事件的钩子数量"""
        return len(self._hooks.get(event, []))

    # ========================================================================
    # 事件历史
    # ========================================================================

    def _record_event(self, event: str, results: List[HookResult], total_time: float):
        """记录事件历史"""
        self._event_history.append({
            "event": event,
            "timestamp": time.time(),
            "hook_count": len(results),
            "success_count": sum(1 for r in results if r.success),
            "failure_count": sum(1 for r in results if not r.success),
            "total_time_ms": round(total_time, 2),
        })

        # 限制历史记录大小
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取事件历史"""
        return self._event_history[-limit:]

    def get_event_stats(self, event: Optional[str] = None) -> Dict[str, Any]:
        """
        获取事件统计

        Args:
            event: 指定事件（None 表示全部）

        Returns:
            统计信息字典
        """
        history = self._event_history

        if event:
            history = [h for h in history if h["event"] == event]

        if not history:
            return {}

        return {
            "total_events": len(history),
            "total_hooks": sum(h["hook_count"] for h in history),
            "success_rate": sum(h["success_count"] for h in history) / max(1, sum(h["hook_count"] for h in history)),
            "average_time_ms": sum(h["total_time_ms"] for h in history) / len(history),
        }


# ============================================================================
# 全局钩子管理器实例
# ============================================================================

# 默认钩子管理器
default_hook_manager = HookManager()


# ============================================================================
# 便捷函数
# ============================================================================

def on_event(event: str, priority: int = HookPriority.NORMAL.value):
    """
    监听事件的便捷装饰器

    Usage:
        @on_event("user.login")
        async def handle_login(user_id):
            print(f"用户 {user_id} 登录")
    """
    return default_hook_manager.listen_with_priority(event, priority)


def once_event(event: str):
    """
    一次性监听事件的便捷装饰器

    Usage:
        @once_event("app.startup")
        async def handle_startup():
            print("应用启动")
    """
    return default_hook_manager.listen_once(event)


async def emit_event(event: str, *args, **kwargs) -> List[HookResult]:
    """
    触发事件的便捷函数

    Usage:
        await emit_event("user.login", user_id="123")
    """
    return await default_hook_manager.emit(event, *args, **kwargs)


def emit_event_sync(event: str, *args, **kwargs) -> List[HookResult]:
    """
    触发事件的便捷函数（同步）

    Usage:
        emit_event_sync("user.login", user_id="123")
    """
    return default_hook_manager.emit_sync(event, *args, **kwargs)
