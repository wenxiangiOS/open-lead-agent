"""
基础配置

包含应用的基础信息和环境配置
"""

import os
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class BaseConfig(BaseModel):
    """基础配置类"""

    # 应用信息
    app_name: str = Field(default="小缘AI红娘服务", description="应用名称")
    app_version: str = Field(default="2.0.0", description="应用版本")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="运行环境"
    )

    # 调试模式
    debug: bool = Field(default=False, description="调试模式")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """从环境变量读取并验证环境"""
        env_from_os = os.getenv('ENV', 'development')
        if env_from_os in ['development', 'staging', 'production']:
            return env_from_os
        return v

    @field_validator('debug')
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        """生产环境强制关闭调试模式"""
        environment = info.data.get('environment', 'development')
        if environment == 'production' and v:
            raise ValueError('生产环境必须关闭调试模式 (DEBUG=false)')
        return v

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
