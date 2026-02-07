"""
插件系统

提供动态插件加载和管理功能
"""

from .base import (
    Plugin,
    PluginState,
    PluginMetadata,
    PluginConfig,
    PluginException,
    PluginNotFoundError,
    PluginLoadError,
    PluginDependencyError,
    PluginActivationError
)

from .manager import PluginManager

from .hooks import (
    HookManager,
    HookPriority,
    HookMetadata,
    HookResult,
    default_hook_manager,
    on_event,
    once_event,
    emit_event,
    emit_event_sync
)

__all__ = [
    # 插件基类
    'Plugin',
    'PluginState',
    'PluginMetadata',
    'PluginConfig',

    # 插件异常
    'PluginException',
    'PluginNotFoundError',
    'PluginLoadError',
    'PluginDependencyError',
    'PluginActivationError',

    # 插件管理器
    'PluginManager',

    # 钩子系统
    'HookManager',
    'HookPriority',
    'HookMetadata',
    'HookResult',

    # 全局钩子管理器
    'default_hook_manager',
    'on_event',
    'once_event',
    'emit_event',
    'emit_event_sync',
]
