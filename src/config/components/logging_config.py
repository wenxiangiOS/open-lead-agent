"""
日志配置

包含日志级别、格式、输出等配置
"""

import os
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class LoggingConfig(BaseModel):
    """日志配置"""

    # 基础配置
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="日志级别"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="日期格式")

    # 输出配置
    console_enabled: bool = Field(default=True, description="启用控制台输出")
    file_enabled: bool = Field(default=False, description="启用文件输出")
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    max_bytes: int = Field(default=10485760, ge=1048576, le=104857600, description="日志文件最大大小（字节）")
    backup_count: int = Field(default=5, ge=1, le=20, description="日志文件备份数量")

    # 结构化日志
    json_enabled: bool = Field(default=True, description="启用 JSON 格式日志")
    sanitize_enabled: bool = Field(default=True, description="启用敏感信息脱敏")
    sanitize_fields: list[str] = Field(
        default=["phone", "token", "password", "api_key", "secret"],
        description="需要脱敏的字段"
    )

    # 采样配置（高并发时减少日志量）
    sampling_enabled: bool = Field(default=False, description="启用日志采样")
    sampling_rate: float = Field(default=0.1, ge=0.01, le=1.0, description="采样率")

    # 性能日志
    performance_logging: bool = Field(default=True, description="启用性能日志")
    slow_query_threshold: float = Field(default=1.0, ge=0.1, le=10.0, description="慢查询阈值（秒）")

    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """从环境变量读取日志级别"""
        env_level = os.getenv('LOG_LEVEL')
        if env_level:
            v = env_level.upper()
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v not in valid_levels:
                raise ValueError(f'LOG_LEVEL 必须是 {valid_levels} 之一')
        return v

    @property
    def effective_level(self) -> str:
        """获取有效的日志级别（开发环境默认 DEBUG）"""
        env = os.getenv('ENV', 'development')
        if env == 'development' and self.level == 'INFO':
            return 'DEBUG'
        return self.level

    @property
    def should_log_performance(self) -> bool:
        """是否应该记录性能日志"""
        return self.performance_logging and self.level in ['DEBUG', 'INFO']
