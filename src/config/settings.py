"""
配置管理模块

采用分层配置架构，提高可维护性和可测试性
"""

import os
from pathlib import Path
from typing import Optional, Callable
from pydantic import BaseModel, ValidationError, Field
from dotenv import load_dotenv

from .components import (
    BaseConfig,
    AIConfig,
    RedisConfig,
    ServerConfig,
    SecurityConfig,
    LoggingConfig,
)

# 🔴 重要：在创建任何配置之前，先加载 .env 文件
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)


class Settings(BaseModel):
    """
    应用配置聚合器

    整合所有配置组件，提供统一的配置访问接口
    """

    # 配置组件 - 使用 default_factory 延迟创建，确保在 load_dotenv() 之后
    app: BaseConfig = Field(default_factory=BaseConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # 兼容旧版本的单层配置属性（逐步废弃）
    @property
    def api_key(self) -> str:
        """兼容属性：API 密钥"""
        return self.ai.api_key

    @property
    def model_name(self) -> str:
        """兼容属性：模型名称"""
        return self.ai.model_name

    @property
    def base_url(self) -> str:
        """兼容属性：API 基础 URL"""
        return self.ai.base_url

    @property
    def app_name(self) -> str:
        """兼容属性：应用名称"""
        return self.app.app_name

    @property
    def app_version(self) -> str:
        """兼容属性：应用版本"""
        return self.app.app_version

    @property
    def debug(self) -> bool:
        """兼容属性：调试模式"""
        return self.app.debug

    @property
    def log_level(self) -> str:
        """兼容属性：日志级别"""
        return self.logging.level

    @property
    def host(self) -> str:
        """兼容属性：监听地址"""
        return self.server.host

    @property
    def port(self) -> int:
        """兼容属性：监听端口"""
        return self.server.port

    @property
    def reload(self) -> bool:
        """兼容属性：自动重载"""
        return self.server.reload

    @property
    def rate_limit_enabled(self) -> bool:
        """兼容属性：限流启用"""
        return self.server.rate_limit_enabled

    @property
    def rate_limit_requests(self) -> int:
        """兼容属性：限流请求数"""
        return self.server.rate_limit_requests

    @property
    def rate_limit_window(self) -> int:
        """兼容属性：限流时间窗口"""
        return self.server.rate_limit_window

    @property
    def redis_enabled(self) -> bool:
        """兼容属性：Redis 启用"""
        return self.redis.enabled

    @property
    def redis_host(self) -> str:
        """兼容属性：Redis 主机"""
        return self.redis.host

    @property
    def redis_port(self) -> int:
        """兼容属性：Redis 端口"""
        return self.redis.port

    @property
    def redis_db(self) -> int:
        """兼容属性：Redis 数据库"""
        return self.redis.db

    @property
    def redis_password(self) -> Optional[str]:
        """兼容属性：Redis 密码"""
        return self.redis.password

    @property
    def redis_prefix(self) -> str:
        """兼容属性：Redis 键前缀"""
        return self.redis.key_prefix

    @property
    def redis_ttl(self) -> int:
        """兼容属性：Redis TTL"""
        return self.redis.default_ttl

    @property
    def http_connections(self) -> int:
        """兼容属性：HTTP 连接数"""
        return self.redis.max_connections

    @property
    def http_max_keepalive(self) -> int:
        """兼容属性：HTTP Keep-Alive 连接数"""
        return self.server.keepalive

    @property
    def volc_access_key(self) -> Optional[str]:
        """兼容属性：火山引擎 Access Key"""
        return self.ai.volc_access_key

    @property
    def volc_secret_key(self) -> Optional[str]:
        """兼容属性：火山引擎 Secret Key"""
        return self.ai.volc_secret_key

    class Config:
        """Pydantic 配置"""
        arbitrary_types_allowed = True
        validate_assignment = True


def load_settings(env_file: Optional[str] = None) -> Settings:
    """
    加载配置

    Args:
        env_file: 环境变量文件路径（可选）

    Returns:
        Settings: 配置实例

    Raises:
        ValidationError: 配置验证失败
    """
    # 加载 .env 文件
    if env_file is None:
        env_path = Path(__file__).parent.parent.parent / ".env"
    else:
        env_path = Path(env_file)

    if env_path.exists():
        load_dotenv(env_path, override=True)

    # 创建配置实例
    try:
        settings = Settings()
        return settings
    except ValidationError as e:
        print(f"❌ 配置验证失败: {e}")
        raise


# 全局配置实例
settings = load_settings()


def get_settings() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 全局配置实例
    """
    return settings


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """
    重新加载配置（用于测试或热更新）

    Args:
        env_file: 环境变量文件路径（可选）

    Returns:
        Settings: 新的配置实例
    """
    global settings
    settings = load_settings(env_file)
    return settings
