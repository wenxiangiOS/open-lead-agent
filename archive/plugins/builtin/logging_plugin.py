"""
日志插件

增强的日志记录功能
"""

import logging
from typing import Dict, Any
from datetime import datetime

from src.plugins import Plugin, PluginMetadata, PluginConfig

logger = logging.getLogger(__name__)


class LoggingPlugin(Plugin):
    """
    日志插件

    提供增强的日志记录功能：
    - 请求日志
    - 错误日志
    - 性能日志
    """

    metadata = PluginMetadata(
        name="logging",
        version="1.0.0",
        description="增强的日志记录功能",
        author="系统",
        dependencies=[],
        tags=["logging", "monitoring"],
        priority=10,
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        self._request_count = 0
        self._error_count = 0

    async def on_load(self) -> bool:
        """加载插件"""
        logger.info("日志插件加载成功")
        return True

    async def on_activate(self) -> bool:
        """激活插件"""
        # 注册事件监听器
        self.register_hook("request.received", self._on_request_received)
        self.register_hook("request.completed", self._on_request_completed)
        self.register_hook("error.occurred", self._on_error_occurred)
        self.register_hook("app.shutdown", self._on_shutdown)

        logger.info("✅ 日志插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """停用插件"""
        logger.info("日志插件停用")
        return True

    async def on_unload(self) -> bool:
        """卸载插件"""
        logger.info("日志插件卸载")
        return True

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def _on_request_received(self, request_id: str, path: str, method: str, **kwargs):
        """请求接收事件"""
        self._request_count += 1
        logger.info(f"📥 请求 #{self._request_count}: {method} {path} [ID: {request_id}]")

        self.set_context(request_id, {
            "start_time": datetime.now(),
            "path": path,
            "method": method
        })

    async def _on_request_completed(self, request_id: str, status_code: int, **kwargs):
        """请求完成事件"""
        context = self.get_context(request_id, {})
        if context:
            start_time = context.get("start_time")
            if start_time:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"📤 响应: {status_code} - {duration:.2f}ms [ID: {request_id}]")

    async def _on_error_occurred(self, error: Exception, context: Dict[str, Any], **kwargs):
        """错误发生事件"""
        self._error_count += 1
        logger.error(f"❌ 错误 #{self._error_count}: {type(error).__name__}: {error}")

    async def _on_shutdown(self, **kwargs):
        """应用关闭事件"""
        logger.info("=" * 50)
        logger.info("📊 日志插件统计:")
        logger.info(f"  总请求数: {self._request_count}")
        logger.info(f"  总错误数: {self._error_count}")
        logger.info("=" * 50)

    # ========================================================================
    # 插件功能
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "request_count": self._request_count,
            "error_count": self._error_count
        }
