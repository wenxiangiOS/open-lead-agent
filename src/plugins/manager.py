"""
插件管理器

负责插件的加载、卸载、激活、停用和生命周期管理
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable

from .base import Plugin, PluginState, PluginMetadata, PluginConfig, PluginException
from .hooks import HookManager

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器

    职责：
    1. 插件发现和加载
    2. 插件生命周期管理
    3. 插件依赖管理
    4. 插件配置管理
    5. 插件状态监控
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        初始化插件管理器

        Args:
            plugin_dirs: 插件目录列表
        """
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_configs: Dict[str, PluginConfig] = {}
        self._plugin_dirs = plugin_dirs or []
        self._hook_manager = HookManager()

        logger.info("插件管理器初始化完成")

    # ========================================================================
    # 插件发现
    # ========================================================================

    def add_plugin_dir(self, directory: str):
        """
        添加插件目录

        Args:
            directory: 插件目录路径
        """
        if os.path.isdir(directory) and directory not in self._plugin_dirs:
            self._plugin_dirs.append(directory)
            logger.info(f"添加插件目录: {directory}")

    async def discover_plugins(self) -> List[str]:
        """
        发现所有可用的插件

        Returns:
            发现的插件类列表
        """
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                logger.warning(f"插件目录不存在: {plugin_dir}")
                continue

            for file_path in Path(plugin_dir).rglob("*.py"):
                if file_path.name.startswith("_"):
                    continue

                try:
                    plugin_classes = await self._load_plugin_classes_from_file(file_path)
                    discovered.extend(plugin_classes)
                except Exception as e:
                    logger.warning(f"加载插件文件失败 {file_path}: {e}")

        logger.info(f"发现 {len(discovered)} 个插件类")
        return discovered

    async def _load_plugin_classes_from_file(self, file_path: Path) -> List[Type[Plugin]]:
        """
        从文件中加载插件类

        Args:
            file_path: 文件路径

        Returns:
            插件类列表
        """
        # 构建模块路径
        rel_path = file_path.relative_to(file_path.parents[-1] if file_path.parents else Path("."))
        module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")

        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return []

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Plugin) and
                    obj is not Plugin and
                    hasattr(obj, 'metadata') and
                    isinstance(obj.metadata, PluginMetadata)
                ):
                    plugin_classes.append(obj)

            return plugin_classes

        except Exception as e:
            logger.warning(f"导入模块失败 {module_name}: {e}")
            return []

    # ========================================================================
    # 插件注册
    # ========================================================================

    def register_plugin(
        self,
        plugin_class: Type[Plugin],
        config: Optional[PluginConfig] = None
    ) -> Plugin:
        """
        注册插件

        Args:
            plugin_class: 插件类
            config: 插件配置

        Returns:
            插件实例

        Raises:
            PluginException: 注册失败
        """
        if plugin_class.metadata.name in self._plugins:
            raise PluginException(f"插件已存在: {plugin_class.metadata.name}")

        try:
            plugin = plugin_class(config)
            self._plugins[plugin_class.metadata.name] = plugin
            self._plugin_configs[plugin_class.metadata.name] = config or PluginConfig()

            logger.info(f"注册插件: {plugin.name} v{plugin.version}")
            return plugin

        except Exception as e:
            raise PluginException(f"插件注册失败 {plugin_class.metadata.name}: {e}")

    async def auto_register(self) -> int:
        """
        自动发现并注册所有插件

        Returns:
            注册的插件数量
        """
        plugin_classes = await self.discover_plugins()
        registered_count = 0

        # 按优先级排序
        plugin_classes.sort(key=lambda cls: cls.metadata.priority)

        for plugin_class in plugin_classes:
            try:
                # 检查依赖
                if await self._check_dependencies(plugin_class):
                    self.register_plugin(plugin_class)
                    registered_count += 1
                else:
                    logger.warning(f"插件依赖不满足，跳过: {plugin_class.metadata.name}")

            except PluginException as e:
                logger.error(f"插件注册失败: {e}")

        logger.info(f"自动注册完成，共注册 {registered_count} 个插件")
        return registered_count

    # ========================================================================
    # 插件加载
    # ========================================================================

    async def load_plugin(self, name: str) -> bool:
        """
        加载指定插件

        Args:
            name: 插件名称

        Returns:
            是否加载成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"插件未找到: {name}")
            return False

        try:
            success = await plugin.load()
            if success:
                # 注册插件的钩子
                self._register_plugin_hooks(plugin)
            return success

        except Exception as e:
            logger.error(f"加载插件失败 {name}: {e}")
            return False

    async def load_all(self) -> int:
        """
        加载所有已注册的插件

        Returns:
            成功加载的插件数量
        """
        loaded_count = 0

        # 按依赖顺序加载
        load_order = self._get_load_order()

        for name in load_order:
            plugin = self._plugins[name]
            if plugin.config.enabled:
                if await self.load_plugin(name):
                    loaded_count += 1

        logger.info(f"批量加载完成，成功加载 {loaded_count}/{len(self._plugins)} 个插件")
        return loaded_count

    def _get_load_order(self) -> List[str]:
        """
        根据依赖关系获取加载顺序

        Returns:
            插件名称列表（按加载顺序）
        """
        order = []
        visited = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            plugin = self._plugins.get(name)
            if not plugin:
                return

            # 先加载依赖
            for dep in plugin.metadata.dependencies:
                visit(dep)

            order.append(name)

        for name in self._plugins:
            visit(name)

        return order

    async def _check_dependencies(self, plugin_class: Type[Plugin]) -> bool:
        """
        检查插件依赖是否满足

        Args:
            plugin_class: 插件类

        Returns:
            依赖是否满足
        """
        for dep_name in plugin_class.metadata.dependencies:
            if dep_name not in self._plugins:
                logger.warning(f"插件依赖缺失: {plugin_class.metadata.name} 需要 {dep_name}")
                return False

        return True

    # ========================================================================
    # 插件激活/停用
    # ========================================================================

    async def activate_plugin(self, name: str) -> bool:
        """
        激活指定插件

        Args:
            name: 插件名称

        Returns:
            是否激活成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"插件未找到: {name}")
            return False

        try:
            return await plugin.activate()
        except Exception as e:
            logger.error(f"激活插件失败 {name}: {e}")
            return False

    async def deactivate_plugin(self, name: str) -> bool:
        """
        停用指定插件

        Args:
            name: 插件名称

        Returns:
            是否停用成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"插件未找到: {name}")
            return False

        try:
            return await plugin.deactivate()
        except Exception as e:
            logger.error(f"停用插件失败 {name}: {e}")
            return False

    async def activate_all(self) -> int:
        """
        激活所有已加载的插件

        Returns:
            成功激活的插件数量
        """
        activated_count = 0

        for name, plugin in self._plugins.items():
            if plugin.state == PluginState.LOADED and plugin.config.enabled:
                if await self.activate_plugin(name):
                    activated_count += 1

        logger.info(f"批量激活完成，成功激活 {activated_count} 个插件")
        return activated_count

    async def deactivate_all(self) -> int:
        """
        停用所有已激活的插件

        Returns:
            成功停用的插件数量
        """
        deactivated_count = 0

        # 按相反顺序停用
        for name in reversed(list(self._plugins.keys())):
            plugin = self._plugins[name]
            if plugin.state == PluginState.ACTIVE:
                if await self.deactivate_plugin(name):
                    deactivated_count += 1

        logger.info(f"批量停用完成，成功停用 {deactivated_count} 个插件")
        return deactivated_count

    # ========================================================================
    # 插件卸载
    # ========================================================================

    async def unload_plugin(self, name: str) -> bool:
        """
        卸载指定插件

        Args:
            name: 插件名称

        Returns:
            是否卸载成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"插件未找到: {name}")
            return False

        try:
            # 取消注册钩子
            self._unregister_plugin_hooks(plugin)
            return await plugin.unload()

        except Exception as e:
            logger.error(f"卸载插件失败 {name}: {e}")
            return False

    async def unload_all(self) -> int:
        """
        卸载所有插件

        Returns:
            成功卸载的插件数量
        """
        unloaded_count = 0

        # 先停用所有插件
        await self.deactivate_all()

        # 按相反顺序卸载
        for name in reversed(list(self._plugins.keys())):
            if await self.unload_plugin(name):
                unloaded_count += 1

        logger.info(f"批量卸载完成，成功卸载 {unloaded_count} 个插件")
        return unloaded_count

    # ========================================================================
    # 钩子管理
    # ========================================================================

    def _register_plugin_hooks(self, plugin: Plugin):
        """注册插件的所有钩子"""
        for event in dir(plugin):
            if event.startswith("on_"):
                callback = getattr(plugin, event)
                if callable(callback):
                    self._hook_manager.register(event, callback)

    def _unregister_plugin_hooks(self, plugin: Plugin):
        """取消注册插件的所有钩子"""
        self._hook_manager.unregister_plugin(plugin)

    async def emit(self, event: str, *args, **kwargs) -> List[Any]:
        """
        触发事件

        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            所有回调的返回值列表
        """
        return await self._hook_manager.emit(event, *args, **kwargs)

    def register_hook(self, event: str, callback: Callable):
        """注册钩子"""
        self._hook_manager.register(event, callback)

    # ========================================================================
    # 插件查询
    # ========================================================================

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取指定插件"""
        return self._plugins.get(name)

    def get_all_plugins(self) -> Dict[str, Plugin]:
        """获取所有插件"""
        return self._plugins.copy()

    def get_active_plugins(self) -> List[Plugin]:
        """获取所有已激活的插件"""
        return [
            p for p in self._plugins.values()
            if p.state == PluginState.ACTIVE
        ]

    def get_plugins_by_state(self, state: PluginState) -> List[Plugin]:
        """获取指定状态的插件"""
        return [
            p for p in self._plugins.values()
            if p.state == state
        ]

    def get_plugins_by_tag(self, tag: str) -> List[Plugin]:
        """获取指定标签的插件"""
        return [
            p for p in self._plugins.values()
            if tag in p.metadata.tags
        ]

    # ========================================================================
    # 插件配置
    # ========================================================================

    def get_plugin_config(self, name: str) -> Optional[PluginConfig]:
        """获取插件配置"""
        return self._plugin_configs.get(name)

    def update_plugin_config(self, name: str, config: PluginConfig):
        """更新插件配置"""
        if name in self._plugins:
            self._plugin_configs[name] = config
            self._plugins[name]._config = config

    def set_plugin_enabled(self, name: str, enabled: bool):
        """设置插件是否启用"""
        if name in self._plugin_configs:
            self._plugin_configs[name].enabled = enabled
            if name in self._plugins:
                self._plugins[name]._config.enabled = enabled

    # ========================================================================
    # 状态监控
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        获取插件系统状态

        Returns:
            状态信息字典
        """
        status = {
            "total_plugins": len(self._plugins),
            "active_plugins": len(self.get_active_plugins()),
            "plugins": {}
        }

        for name, plugin in self._plugins.items():
            status["plugins"][name] = plugin.to_dict()

        return status

    def print_status(self):
        """打印插件状态"""
        print("\n" + "=" * 60)
        print("🔌 插件系统状态")
        print("=" * 60)

        status = self.get_status()
        print(f"总插件数: {status['total_plugins']}")
        print(f"已激活: {status['active_plugins']}")

        for name, info in status["plugins"].items():
            status_emoji = {
                PluginState.ACTIVE: "✅",
                PluginState.LOADED: "📦",
                PluginState.ERROR: "❌",
                PluginState.UNLOADED: "⚪",
            }.get(PluginState(info["state"]), "❓")

            enabled_mark = "🔓" if info["enabled"] else "🔒"
            print(f"  {status_emoji} {enabled_mark} {name} v{info['version']} - {info['state']}")

        print("=" * 60 + "\n")
