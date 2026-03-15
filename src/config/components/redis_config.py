"""
Redis 配置

包含 Redis 连接、缓存策略、连接池等配置
"""

import os
import re
from pydantic import BaseModel, Field, field_validator, model_validator


def parse_ttl(ttl_value: str | int) -> int:
    """
    解析 TTL 值，支持多种格式

    支持格式：
    - 纯数字：86400 = 86400 秒
    - 时间单位：24h = 24 小时，7d = 7 天，1w = 1 周，1M = 1 月，1y = 1 年

    Args:
        ttl_value: TTL 值（字符串或整数）

    Returns:
        int: TTL 秒数

    Examples:
        >>> parse_ttl(86400)
        86400
        >>> parse_ttl("24h")
        86400
        >>> parse_ttl("7d")
        604800
        >>> parse_ttl("1w")
        604800
        >>> parse_ttl("1M")
        2592000
        >>> parse_ttl("1y")
        31536000
    """
    # 如果是整数，直接返回
    if isinstance(ttl_value, int):
        return ttl_value

    # 如果是字符串，保留原始大小写
    ttl_str = str(ttl_value).strip()
    ttl_lower = ttl_str.lower()

    # 纯数字
    if ttl_lower.isdigit():
        return int(ttl_str)

    # 解析时间单位
    # 格式：数字 + 单位
    pattern = r'^(\d+)\s*([a-zA-Z]+)$'
    match = re.match(pattern, ttl_str)

    if not match:
        raise ValueError(f"Invalid TTL format: {ttl_value}")

    value = int(match.group(1))
    unit = match.group(2)  # 保留原始大小写

    # 时间单位转换（大小写敏感）
    time_units = {
        # 秒
        's': 1, 'sec': 1, 'second': 1,
        # 分钟（小写 m）
        'm': 60, 'min': 60, 'minute': 60,
        # 小时
        'h': 3600, 'hr': 3600, 'hour': 3600,
        # 天
        'd': 86400, 'day': 86400,
        # 周
        'w': 604800, 'week': 604800,
        # 月（大写 M）
        'M': 2592000, 'Month': 2592000, 'MONTH': 2592000,
        # 年
        'y': 31536000, 'year': 31536000,
    }

    if unit not in time_units:
        raise ValueError(f"Unknown time unit: {unit}. Supported: s/m/h/d/w/M/y")

    return value * time_units[unit]


class RedisConfig(BaseModel):
    """Redis 配置"""

    # 连接配置
    enabled: bool = Field(default=False, description="是否启用 Redis")
    host: str = Field(default="localhost", description="Redis 主机")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis 端口")
    db: int = Field(default=0, ge=0, le=15, description="Redis 数据库编号")
    password: str | None = Field(default=None, description="Redis 密码")

    # 缓存配置
    key_prefix: str = Field(default="doubao:", description="Redis 键前缀")
    default_ttl: int = Field(default=86400, ge=60, le=604800, description="默认 TTL（秒）")
    max_connections: int = Field(default=50, ge=1, le=100, description="最大连接数")

    # 健康检查
    health_check_interval: int = Field(default=30, ge=5, le=300, description="健康检查间隔（秒）")
    reconnect_attempts: int = Field(default=3, ge=1, le=10, description="重连尝试次数")

    # 序列化
    use_json: bool = Field(default=True, description="使用 JSON 序列化")

    @model_validator(mode='after')
    def validate_from_env(self) -> 'RedisConfig':
        """从环境变量读取配置值"""
        # 读取 REDIS_ENABLED
        env_enabled = os.getenv('REDIS_ENABLED')
        if env_enabled:
            self.enabled = env_enabled.lower() in ('true', '1', 'yes')

        # 读取 REDIS_HOST
        env_host = os.getenv('REDIS_HOST')
        if env_host:
            self.host = env_host

        # 读取 REDIS_PORT
        env_port = os.getenv('REDIS_PORT')
        if env_port:
            try:
                self.port = int(env_port)
            except ValueError:
                pass

        # 读取 REDIS_PASSWORD
        env_password = os.getenv('REDIS_PASSWORD')
        if env_password:
            self.password = env_password

        # 读取 REDIS_TTL
        env_ttl = os.getenv('REDIS_TTL')
        if env_ttl:
            try:
                self.default_ttl = parse_ttl(env_ttl)
            except ValueError:
                pass

        return self

    @property
    def redis_url(self) -> str:
        """生成 Redis 连接 URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self.enabled and self.host
