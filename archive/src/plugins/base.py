"""
插件基类

定义插件接口和生命周期
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# 插件状态枚举
# ============================================================================

class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"       # 未加载
    LOADING = "loading"         # 加载中
    LOADED = "loaded"           # 已加载（未激活）
    ACTIVATING = "activating"   # 激活中
    ACTIVE = "active"           # 已激活
    DEACTIVATING = "deactivating"  # 停用中
    ERROR = "error"             # 错误状态
    DISABLED = "disabled"       # 已禁用


# ============================================================================
# 插件元数据
# ============================================================================

@dataclass
class PluginMetadata:
    """
    插件元数据

    Attributes:
        name: 插件名称（唯一标识符）
        version: 插件版本
        description: 插件描述
        author: 作者
        dependencies: 依赖的其他插件列表
        requires: 需要的最低系统版本
        tags: 标签（用于分类和搜索）
        priority: 优先级（影响加载顺序）
        enabled: 是否默认启用
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = None
    requires: str = "1.0.0"
    tags: List[str] = None
    priority: int = 100
    enabled: bool = True

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []

    @property
    def id(self) -> str:
        """插件唯一标识符"""
        return f"{self.name}@{self.version}"


# ============================================================================
# 插件配置
# ============================================================================

@dataclass
class PluginConfig:
    """
    插件配置

    Attributes:
        enabled: 是否启用
        settings: 插件设置
    """
    enabled: bool = True
    settings: Dict[str, Any] = None

    def __post_init__(self):
        if self.settings is None:
            self.settings = {}

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self.settings[key] = value

    def update(self, config: Dict[str, Any]):
        """更新配置"""
        self.settings.update(config)


# ============================================================================
# 插件基类
# ============================================================================

class Plugin(ABC):
    """
    插件基类

    所有插件都必须继承此类并实现相应方法
    """

    # 插件元数据（子类必须覆盖）
    metadata: PluginMetadata = None

    def __init__(self, config: Optional[PluginConfig] = None):
        """
        初始化插件

        Args:
            config: 插件配置
        """
        if self.metadata is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 metadata 属性")

        self._state = PluginState.UNLOADED
        self._config = config or PluginConfig(enabled=self.metadata.enabled)
        self._context: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}

        logger.info(f"初始化插件: {self.metadata.name}")

    @property
    def state(self) -> PluginState:
        """获取插件状态"""
        return self._state

    @property
    def config(self) -> PluginConfig:
        """获取插件配置"""
        return self._config

    @property
    def name(self) -> str:
        """获取插件名称"""
        return self.metadata.name

    @property
    def version(self) -> str:
        """获取插件版本"""
        return self.metadata.version

    @property
    def is_active(self) -> bool:
        """是否已激活"""
        return self._state == PluginState.ACTIVE

    @property
    def is_enabled(self) -> bool:
        """是否已启用"""
        return self._config.enabled

    @abstractmethod
    async def on_load(self) -> bool:
        """
        插件加载时调用

        Returns:
            bool: 是否加载成功
        """
        pass

    @abstractmethod
    async def on_activate(self) -> bool:
        """
        插件激活时调用

        Returns:
            bool: 是否激活成功
        """
        pass

    @abstractmethod
    async def on_deactivate(self) -> bool:
        """
        插件停用时调用

        Returns:
            bool: 是否停用成功
        """
        pass

    @abstractmethod
    async def on_unload(self) -> bool:
        """
        插件卸载时调用

        Returns:
            bool: 是否卸载成功
        """
        pass

    def on_error(self, error: Exception):
        """
        插件出错时调用

        Args:
            error: 异常对象
        """
        logger.error(f"插件 {self.name} 出错: {error}")

    async def load(self) -> bool:
        """加载插件"""
        if self._state != PluginState.UNLOADED:
            logger.warning(f"插件 {self.name} 已经加载，状态: {self._state.value}")
            return True

        try:
            self._state = PluginState.LOADING
            logger.info(f"正在加载插件: {self.name}")

            success = await self.on_load()

            if success:
                self._state = PluginState.LOADED
                logger.info(f"✅ 插件加载成功: {self.name}")
                return True
            else:
                self._state = PluginState.ERROR
                logger.error(f"❌ 插件加载失败: {self.name}")
                return False

        except Exception as e:
            self._state = PluginState.ERROR
            self.on_error(e)
            return False

    async def activate(self) -> bool:
        """激活插件"""
        if not self._config.enabled:
            logger.warning(f"插件 {self.name} 未启用，无法激活")
            return False

        if self._state == PluginState.ACTIVE:
            logger.warning(f"插件 {self.name} 已经激活")
            return True

        try:
            self._state = PluginState.ACTIVATING
            logger.info(f"正在激活插件: {self.name}")

            success = await self.on_activate()

            if success:
                self._state = PluginState.ACTIVE
                logger.info(f"✅ 插件激活成功: {self.name}")
                return True
            else:
                self._state = PluginState.LOADED
                logger.error(f"❌ 插件激活失败: {self.name}")
                return False

        except Exception as e:
            self._state = PluginState.ERROR
            self.on_error(e)
            return False

    async def deactivate(self) -> bool:
        """停用插件"""
        if self._state != PluginState.ACTIVE:
            logger.warning(f"插件 {self.name} 未激活")
            return True

        try:
            self._state = PluginState.DEACTIVATING
            logger.info(f"正在停用插件: {self.name}")

            success = await self.on_deactivate()

            if success:
                self._state = PluginState.LOADED
                logger.info(f"✅ 插件停用成功: {self.name}")
                return True
            else:
                self._state = PluginState.ERROR
                logger.error(f"❌ 插件停用失败: {self.name}")
                return False

        except Exception as e:
            self._state = PluginState.ERROR
            self.on_error(e)
            return False

    async def unload(self) -> bool:
        """卸载插件"""
        if self._state == PluginState.ACTIVE:
            await self.deactivate()

        if self._state == PluginState.UNLOADED:
            logger.warning(f"插件 {self.name} 已经卸载")
            return True

        try:
            success = await self.on_unload()

            if success:
                self._state = PluginState.UNLOADED
                logger.info(f"✅ 插件卸载成功: {self.name}")
                return True
            else:
                self._state = PluginState.ERROR
                logger.error(f"❌ 插件卸载失败: {self.name}")
                return False

        except Exception as e:
            self._state = PluginState.ERROR
            self.on_error(e)
            return False

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self._context.get(key, default)

    def set_context(self, key: str, value: Any):
        """设置上下文数据"""
        self._context[key] = value

    def register_hook(self, event: str, callback: Callable):
        """注册钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def get_hooks(self, event: str) -> List[Callable]:
        """获取事件的所有钩子"""
        return self._hooks.get(event, [])

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "state": self._state.value,
            "enabled": self._config.enabled,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "tags": self.metadata.tags,
            "priority": self.metadata.priority
        }


# ============================================================================
# 插件异常
# ============================================================================

class PluginException(Exception):
    """插件基础异常"""
    pass


class PluginNotFoundError(PluginException):
    """插件未找到异常"""

    def __init__(self, plugin_name: str):
        super().__init__(f"插件未找到: {plugin_name}")
        self.plugin_name = plugin_name


class PluginLoadError(PluginException):
    """插件加载异常"""

    def __init__(self, plugin_name: str, reason: str):
        super().__init__(f"插件加载失败: {plugin_name} - {reason}")
        self.plugin_name = plugin_name
        self.reason = reason


class PluginDependencyError(PluginException):
    """插件依赖异常"""

    def __init__(self, plugin_name: str, missing_dependency: str):
        super().__init__(f"插件依赖缺失: {plugin_name} 需要 {missing_dependency}")
        self.plugin_name = plugin_name
        self.missing_dependency = missing_dependency


class PluginActivationError(PluginException):
    """插件激活异常"""

    def __init__(self, plugin_name: str, reason: str):
        super().__init__(f"插件激活失败: {plugin_name} - {reason}")
        self.plugin_name = plugin_name
        self.reason = reason
