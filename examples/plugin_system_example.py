"""
插件系统使用示例

演示如何创建、加载和使用插件
"""

import asyncio
import logging
from typing import Dict, Any

from src.plugins import (
    Plugin,
    PluginManager,
    PluginMetadata,
    PluginConfig,
    on_event,
    once_event,
    emit_event
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 自定义插件示例
# ============================================================================

class GreetingPlugin(Plugin):
    """
    问候插件

    在用户登录时发送问候消息
    """

    metadata = PluginMetadata(
        name="greeting",
        version="1.0.0",
        description="用户登录问候功能",
        author="示例",
        dependencies=[],
        tags=["greeting", "user"],
        priority=50,
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        self._greeting_count = 0

    async def on_load(self) -> bool:
        """加载插件"""
        logger.info("🎁 问候插件加载成功")
        return True

    async def on_activate(self) -> bool:
        """激活插件"""
        # 注册事件监听器
        self.register_hook("user.login", self._on_user_login)
        self.register_hook("user.logout", self._on_user_logout)

        logger.info("✅ 问候插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """停用插件"""
        logger.info("问候插件停用")
        return True

    async def on_unload(self) -> bool:
        """卸载插件"""
        logger.info("问候插件卸载")
        return True

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def _on_user_login(self, user_id: str, username: str = None, **kwargs):
        """用户登录事件"""
        self._greeting_count += 1
        name = username or user_id
        logger.info(f"👋 你好，{name}！欢迎回来！(第 {self._greeting_count} 次问候)")

    async def _on_user_logout(self, user_id: str, **kwargs):
        """用户登出事件"""
        logger.info(f"👋 再见，{user_id}！期待下次相见！")

    # ========================================================================
    # 插件功能
    # ========================================================================

    def get_greeting_count(self) -> int:
        """获取问候次数"""
        return self._greeting_count


class NotificationPlugin(Plugin):
    """
    通知插件

    发送各种通知
    """

    metadata = PluginMetadata(
        name="notification",
        version="1.0.0",
        description="通知发送功能",
        author="示例",
        dependencies=[],
        tags=["notification", "messaging"],
        priority=60,
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        self._notification_count = 0
        self._channels = config.get("channels", ["email", "sms"]) if config else ["email", "sms"]

    async def on_load(self) -> bool:
        """加载插件"""
        logger.info(f"📢 通知插件加载成功 (渠道: {', '.join(self._channels)})")
        return True

    async def on_activate(self) -> bool:
        """激活插件"""
        self.register_hook("notification.send", self._on_send_notification)
        self.register_hook("user.login", self._on_user_login_notify)
        logger.info("✅ 通知插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """停用插件"""
        logger.info("通知插件停用")
        return True

    async def on_unload(self) -> bool:
        """卸载插件"""
        logger.info("通知插件卸载")
        return True

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def _on_send_notification(
        self,
        user_id: str,
        message: str,
        channels: list = None,
        **kwargs
    ):
        """发送通知事件"""
        channels = channels or self._channels
        self._notification_count += 1

        for channel in channels:
            logger.info(f"📨 通过 {channel} 发送通知给 {user_id}: {message}")

    async def _on_user_login_notify(self, user_id: str, **kwargs):
        """用户登录通知（低优先级）"""
        # 延迟通知
        await asyncio.sleep(0.1)
        logger.info(f"🔔 登录通知已发送给 {user_id}")

    # ========================================================================
    # 插件功能
    # ========================================================================

    async def send_notification(self, user_id: str, message: str):
        """发送通知"""
        await emit_event("notification.send", user_id=user_id, message=message)


# ============================================================================
# 使用钩子装饰器
# ============================================================================

@on_event("user.login", priority=10)
async def log_user_login(user_id: str, **kwargs):
    """使用装饰器监听用户登录事件"""
    logger.info(f"📝 记录登录: 用户 {user_id} 在 {asyncio.get_event_loop().time()} 登录")


@once_event("app.startup")
async def on_app_startup():
    """使用装饰器监听应用启动事件（只执行一次）"""
    logger.info("🚀 应用启动完成！")


# ============================================================================
# 主程序
# ============================================================================

async def main():
    """主程序"""

    print("\n" + "=" * 60)
    print("🔌 插件系统示例")
    print("=" * 60 + "\n")

    # 1. 创建插件管理器
    manager = PluginManager()

    # 2. 注册插件
    print("📦 注册插件...")
    from plugins.builtin import LoggingPlugin, CachePlugin, AnalyticsPlugin

    manager.register_plugin(LoggingPlugin)
    manager.register_plugin(CachePlugin)
    manager.register_plugin(AnalyticsPlugin)
    manager.register_plugin(GreetingPlugin)
    manager.register_plugin(NotificationPlugin)

    # 3. 加载所有插件
    print("\n⏳ 加载插件...")
    await manager.load_all()

    # 4. 激活所有插件
    print("\n▶️  激活插件...")
    await manager.activate_all()

    # 5. 打印插件状态
    manager.print_status()

    # 6. 触发应用启动事件
    print("\n🚀 触发应用启动事件...")
    await manager.emit("app.startup")

    # 7. 模拟用户登录
    print("\n👤 模拟用户登录...")
    await manager.emit(
        "user.login",
        user_id="user_123",
        username="张三"
    )

    # 8. 获取插件实例并调用功能
    print("\n📊 获取插件统计...")

    greeting_plugin = manager.get_plugin("greeting")
    if greeting_plugin:
        logger.info(f"问候插件已发送 {greeting_plugin.get_greeting_count()} 次问候")

    cache_plugin = manager.get_plugin("cache")
    if cache_plugin:
        stats = cache_plugin.get_stats()
        logger.info(f"缓存统计: 命中率 {stats['hit_rate']}%")

    analytics_plugin = manager.get_plugin("analytics")
    if analytics_plugin:
        summary = analytics_plugin.get_summary()
        logger.info(f"分析统计: {summary['total_events']} 事件, {summary['active_users']} 活跃用户")

    # 9. 模拟用户登出
    print("\n👋 模拟用户登出...")
    await manager.emit("user.logout", user_id="user_123")

    # 10. 触发应用关闭事件
    print("\n🛑 触发应用关闭事件...")
    await manager.emit("app.shutdown")

    # 11. 停用和卸载插件
    print("\n⏹️  停用插件...")
    await manager.deactivate_all()

    print("\n📦 卸载插件...")
    await manager.unload_all()

    # 12. 最终状态
    manager.print_status()

    print("\n✅ 示例完成！")


# ============================================================================
# 简化的使用示例
# ============================================================================

async def simple_example():
    """简化的使用示例"""

    # 创建插件管理器
    manager = PluginManager()

    # 注册自定义插件
    manager.register_plugin(GreetingPlugin)

    # 加载并激活
    await manager.load_all()
    await manager.activate_all()

    # 触发事件
    await manager.emit("user.login", user_id="user_456", username="李四")

    # 停用
    await manager.deactivate_all()
    await manager.unload_all()


if __name__ == "__main__":
    asyncio.run(main())
