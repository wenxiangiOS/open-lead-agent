"""
分析插件

数据收集和分析功能
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.plugins import Plugin, PluginMetadata, PluginConfig

logger = logging.getLogger(__name__)


class AnalyticsPlugin(Plugin):
    """
    分析插件

    提供数据收集和分析功能：
    - 事件跟踪
    - 用户行为分析
    - 性能指标收集
    """

    metadata = PluginMetadata(
        name="analytics",
        version="1.0.0",
        description="数据收集和分析功能",
        author="系统",
        dependencies=[],
        tags=["analytics", "monitoring", "metrics"],
        priority=30,
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        self._events: List[Dict[str, Any]] = []
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._user_sessions: Dict[str, Dict[str, Any]] = {}

    async def on_load(self) -> bool:
        """加载插件"""
        logger.info("分析插件加载成功")
        return True

    async def on_activate(self) -> bool:
        """激活插件"""
        # 注册事件监听器
        self.register_hook("request.completed", self._on_request_completed)
        self.register_hook("error.occurred", self._on_error_occurred)
        self.register_hook("user.action", self._on_user_action)
        self.register_hook("metric.recorded", self._on_metric_recorded)
        self.register_hook("app.shutdown", self._on_shutdown)

        logger.info("✅ 分析插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """停用插件"""
        # 保存数据
        await self._flush_data()
        logger.info("分析插件停用")
        return True

    async def on_unload(self) -> bool:
        """卸载插件"""
        logger.info("分析插件卸载")
        return True

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def _on_request_completed(
        self,
        request_id: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """请求完成事件"""
        self.track_event("request_completed", {
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms
        })

        # 记录性能指标
        self.record_metric(f"request.duration.{path}", duration_ms)
        self.record_metric(f"request.status.{status_code}", 1)

    async def _on_error_occurred(self, error: Exception, context: Dict[str, Any], **kwargs):
        """错误发生事件"""
        self.track_event("error_occurred", {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        })

        self.record_metric(f"error.{type(error).__name__}", 1)

    async def _on_user_action(self, user_id: str, action: str, **kwargs):
        """用户操作事件"""
        # 记录用户会话
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = {
                "start_time": datetime.now(),
                "actions": []
            }

        self._user_sessions[user_id]["actions"].append({
            "action": action,
            "timestamp": datetime.now()
        })

        self.track_event("user_action", {
            "user_id": user_id,
            "action": action
        })

    async def _on_metric_recorded(self, name: str, value: float, **kwargs):
        """指标记录事件"""
        self._metrics[name].append(value)

    async def _on_shutdown(self, **kwargs):
        """应用关闭事件"""
        await self._flush_data()

    # ========================================================================
    # 插件功能
    # ========================================================================

    def track_event(self, event_name: str, properties: Dict[str, Any] = None):
        """
        跟踪事件

        Args:
            event_name: 事件名称
            properties: 事件属性
        """
        event = {
            "name": event_name,
            "timestamp": datetime.now(),
            "properties": properties or {}
        }
        self._events.append(event)

        # 限制内存使用
        if len(self._events) > 10000:
            self._events = self._events[-5000:]

    def record_metric(self, name: str, value: float):
        """
        记录指标

        Args:
            name: 指标名称
            value: 指标值
        """
        self._metrics[name].append(value)

        # 限制内存使用
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-500:]

    def get_events(
        self,
        event_name: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取事件列表

        Args:
            event_name: 事件名称（None 表示所有事件）
            limit: 返回数量限制

        Returns:
            事件列表
        """
        events = self._events

        if event_name:
            events = [e for e in events if e["name"] == event_name]

        return events[-limit:]

    def get_metric_stats(
        self,
        metric_name: str,
        period: timedelta = None
    ) -> Dict[str, float]:
        """
        获取指标统计

        Args:
            metric_name: 指标名称
            period: 时间周期（None 表示全部）

        Returns:
            统计信息字典
        """
        values = self._metrics.get(metric_name, [])

        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values)
        }

    def get_user_session(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户会话信息

        Args:
            user_id: 用户 ID

        Returns:
            会话信息字典
        """
        return self._user_sessions.get(user_id, {})

    def get_active_users(self, minutes: int = 30) -> List[str]:
        """
        获取活跃用户列表

        Args:
            minutes: 活跃时间窗口（分钟）

        Returns:
            用户 ID 列表
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        active_users = []

        for user_id, session in self._user_sessions.items():
            if session.get("start_time", datetime.min) > cutoff:
                active_users.append(user_id)

        return active_users

    async def _flush_data(self):
        """刷新数据到存储"""
        logger.info(f"刷新分析数据: {len(self._events)} 事件, {len(self._metrics)} 指标")

    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        total_events = len(self._events)
        total_metrics = sum(len(v) for v in self._metrics.values())
        active_users = len(self._user_sessions)

        return {
            "total_events": total_events,
            "total_metrics": total_metrics,
            "active_users": active_users,
            "event_types": len(set(e["name"] for e in self._events)),
            "metric_types": len(self._metrics)
        }
