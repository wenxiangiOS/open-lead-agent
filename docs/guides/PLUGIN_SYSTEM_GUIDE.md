# 插件系统使用指南

本文档介绍 Doubao MCP Server 的插件系统，包括如何创建、加载和使用插件。

## 目录

- [概述](#概述)
- [插件基础](#插件基础)
- [创建插件](#创建插件)
- [插件生命周期](#插件生命周期)
- [钩子系统](#钩子系统)
- [插件管理](#插件管理)
- [最佳实践](#最佳实践)

---

## 概述

插件系统提供了一个灵活的架构，允许你：

1. **动态加载** - 在运行时加载和卸载功能模块
2. **事件驱动** - 通过钩子系统响应各种事件
3. **依赖管理** - 自动处理插件之间的依赖关系
4. **配置管理** - 灵活的插件配置系统

### 核心组件

```
src/plugins/
├── base.py       # 插件基类和元数据
├── manager.py    # 插件管理器
├── hooks.py      # 钩子管理器
└── __init__.py   # 模块导出

plugins/builtin/  # 内置插件
├── logging_plugin.py
├── cache_plugin.py
└── analytics_plugin.py
```

---

## 插件基础

### Plugin 类

所有插件都必须继承 `Plugin` 基类：

```python
from src.plugins import Plugin, PluginMetadata, PluginConfig

class MyPlugin(Plugin):
    metadata = PluginMetadata(
        name="my_plugin",
        version="1.0.0",
        description="我的插件",
        author="作者名",
        dependencies=[],  # 依赖的其他插件
        tags=["category"],
        priority=100,     # 加载优先级
        enabled=True      # 是否默认启用
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
```

### PluginMetadata

插件元数据定义了插件的基本信息：

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | str | 插件名称（唯一标识符） |
| `version` | str | 插件版本 |
| `description` | str | 插件描述 |
| `author` | str | 作者 |
| `dependencies` | List[str] | 依赖的插件列表 |
| `requires` | str | 最低系统版本 |
| `tags` | List[str] | 标签（用于分类） |
| `priority` | int | 加载优先级（数值越小越优先） |
| `enabled` | bool | 是否默认启用 |

---

## 创建插件

### 基本插件

```python
from src.plugins import Plugin, PluginMetadata, PluginConfig
import logging

logger = logging.getLogger(__name__)

class HelloPlugin(Plugin):
    """简单的问候插件"""

    metadata = PluginMetadata(
        name="hello",
        version="1.0.0",
        description="问候功能",
        author="系统",
        dependencies=[],
        tags=["greeting"],
        priority=100,
        enabled=True
    )

    async def on_load(self) -> bool:
        """插件加载时调用"""
        logger.info("问候插件加载成功")
        return True

    async def on_activate(self) -> bool:
        """插件激活时调用"""
        # 注册事件监听器
        self.register_hook("user.login", self._on_user_login)
        logger.info("✅ 问候插件激活成功")
        return True

    async def on_deactivate(self) -> bool:
        """插件停用时调用"""
        logger.info("问候插件停用")
        return True

    async def on_unload(self) -> bool:
        """插件卸载时调用"""
        logger.info("问候插件卸载")
        return True

    async def _on_user_login(self, user_id: str, **kwargs):
        """用户登录事件处理"""
        logger.info(f"👋 你好，{user_id}！欢迎回来！")
```

### 带配置的插件

```python
class ConfigurablePlugin(Plugin):
    """可配置的插件"""

    metadata = PluginMetadata(
        name="configurable",
        version="1.0.0",
        description="可配置插件示例",
        enabled=True
    )

    def __init__(self, config: PluginConfig = None):
        super().__init__(config)
        # 从配置获取参数
        self.max_items = self.config.get("max_items", 100)
        self.timeout = self.config.get("timeout", 30)

    async def on_load(self) -> bool:
        logger.info(f"配置: max_items={self.max_items}, timeout={self.timeout}")
        return True

    # ... 其他方法
```

---

## 插件生命周期

插件有以下几个状态：

```
UNLOADED → LOADING → LOADED → ACTIVATING → ACTIVE
                   ↓                 ↓
                  ERROR            DEACTIVATING → LOADED
```

### 生命周期方法

| 方法 | 调用时机 | 用途 |
|------|----------|------|
| `on_load()` | 插件加载时 | 初始化资源 |
| `on_activate()` | 插件激活时 | 注册钩子、启动服务 |
| `on_deactivate()` | 插件停用时 | 清理资源 |
| `on_unload()` | 插件卸载时 | 释放所有资源 |

---

## 钩子系统

钩子系统实现了事件驱动架构。

### 注册钩子

```python
# 在插件中注册
async def on_activate(self) -> bool:
    self.register_hook("event.name", self._handler)
    return True

async def _handler(self, arg1, arg2, **kwargs):
    # 处理事件
    pass
```

### 触发事件

```python
# 异步触发
await manager.emit("event.name", arg1="value1", arg2="value2")

# 同步触发
manager.emit_sync("event.name", arg1="value1")
```

### 使用装饰器

```python
from src.plugins import on_event, once_event

@on_event("user.login")
async def handle_login(user_id: str, **kwargs):
    print(f"用户 {user_id} 登录")

@once_event("app.startup")
async def handle_startup():
    print("应用启动（只执行一次）")
```

### 钩子优先级

```python
from src.plugins import HookPriority

self.register_hook(
    "event.name",
    self._handler,
    priority=HookPriority.HIGH.value  # 优先执行
)
```

---

## 插件管理

### PluginManager

```python
from src.plugins import PluginManager

# 创建插件管理器
manager = PluginManager()

# 注册插件
manager.register_plugin(MyPlugin)

# 加载所有插件
await manager.load_all()

# 激活所有插件
await manager.activate_all()

# 获取插件实例
plugin = manager.get_plugin("my_plugin")

# 触发事件
await manager.emit("event.name", data="value")

# 停用所有插件
await manager.deactivate_all()

# 卸载所有插件
await manager.unload_all()
```

### 查询插件

```python
# 获取所有插件
all_plugins = manager.get_all_plugins()

# 获取已激活的插件
active_plugins = manager.get_active_plugins()

# 按状态查询
loaded_plugins = manager.get_plugins_by_state(PluginState.LOADED)

# 按标签查询
cache_plugins = manager.get_plugins_by_tag("cache")

# 打印状态
manager.print_status()
```

### 插件配置

```python
# 创建配置
config = PluginConfig(
    enabled=True,
    settings={"max_items": 100, "timeout": 30}
)

# 注册时传入配置
manager.register_plugin(MyPlugin, config)

# 运行时更新配置
plugin_config = manager.get_plugin_config("my_plugin")
plugin_config.set("max_items", 200)
```

---

## 最佳实践

### 1. 插件命名

使用描述性的名称，使用下划线分隔：

```python
# ✅ 推荐
metadata = PluginMetadata(name="user_analytics")

# ❌ 不推荐
metadata = PluginMetadata(name="plugin1")
```

### 2. 错误处理

在生命周期方法中处理异常：

```python
async def on_load(self) -> bool:
    try:
        # 初始化代码
        return True
    except Exception as e:
        logger.error(f"插件加载失败: {e}")
        return False
```

### 3. 资源清理

确保在 `on_deactivate` 或 `on_unload` 中清理资源：

```python
async def on_deactivate(self) -> bool:
    # 取消定时任务
    if self._timer_task:
        self._timer_task.cancel()
    return True
```

### 4. 依赖管理

正确声明依赖关系：

```python
metadata = PluginMetadata(
    name="my_plugin",
    dependencies=["logging", "cache"]  # 依赖的插件
)
```

### 5. 配置验证

验证配置参数：

```python
def __init__(self, config: PluginConfig = None):
    super().__init__(config)
    self.timeout = self.config.get("timeout", 30)
    
    # 验证
    if self.timeout < 1 or self.timeout > 300:
        raise ValueError("timeout 必须在 1-300 秒之间")
```

---

## 内置插件

系统提供了以下内置插件：

### LoggingPlugin

日志插件，记录请求、错误和性能数据。

```python
from plugins.builtin import LoggingPlugin

manager.register_plugin(LoggingPlugin)
```

### CachePlugin

缓存插件，提供增强的缓存功能。

```python
from plugins.builtin import CachePlugin

config = PluginConfig(settings={"default_ttl": 3600})
manager.register_plugin(CachePlugin, config)
```

### AnalyticsPlugin

分析插件，收集和分析用户行为数据。

```python
from plugins.builtin import AnalyticsPlugin

manager.register_plugin(AnalyticsPlugin)
```

---

## 完整示例

```python
import asyncio
from src.plugins import PluginManager, PluginMetadata, PluginConfig
from plugins.builtin import LoggingPlugin, CachePlugin, AnalyticsPlugin

async def main():
    # 创建插件管理器
    manager = PluginManager()

    # 注册内置插件
    manager.register_plugin(LoggingPlugin)
    manager.register_plugin(CachePlugin)
    manager.register_plugin(AnalyticsPlugin)

    # 加载并激活
    await manager.load_all()
    await manager.activate_all()

    # 触发事件
    await manager.emit("user.login", user_id="user_123")

    # 查看状态
    manager.print_status()

    # 清理
    await manager.deactivate_all()
    await manager.unload_all()

if __name__ == "__main__":
    asyncio.run(main())
```

更多示例请参考 `examples/plugin_system_example.py`。
