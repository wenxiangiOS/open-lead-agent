"""
内置插件

系统提供的默认插件
"""

from .logging_plugin import LoggingPlugin
from .cache_plugin import CachePlugin
from .analytics_plugin import AnalyticsPlugin

__all__ = [
    'LoggingPlugin',
    'CachePlugin',
    'AnalyticsPlugin',
]
