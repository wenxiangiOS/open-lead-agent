"""
AI 服务配置

包含 AI 模型、API 密钥、超时等配置
"""

import os
from pydantic import BaseModel, Field, field_validator, model_validator


class AIConfig(BaseModel):
    """AI 服务配置"""

    # API 配置
    api_key: str = Field(default="", description="Doubao API 密钥")
    model_name: str = Field(default="doubao-seed-1-8-251228", description="模型名称")
    base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        description="API 基础 URL"
    )

    # 火山引擎配置（可选）
    volc_access_key: str | None = Field(default=None, description="火山引擎 Access Key")
    volc_secret_key: str | None = Field(default=None, description="火山引擎 Secret Key")

    # 超时和重试
    timeout: int = Field(default=30, ge=5, le=120, description="API 调用超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, le=5, description="最大重试次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="重试延迟（秒）")

    # 模型参数
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2000, ge=100, le=32000, description="最大 token 数")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p 采样")

    # 限流
    rate_limit: int = Field(default=100, ge=1, le=1000, description="每分钟最大请求数")

    @model_validator(mode='before')
    @classmethod
    def load_from_env(cls, data):
        """初始化前从环境变量读取配置"""
        if isinstance(data, dict):
            if 'ARK_API_KEY' in os.environ and 'api_key' not in data:
                data['api_key'] = os.environ['ARK_API_KEY']
            if 'MODEL_NAME' in os.environ and 'model_name' not in data:
                data['model_name'] = os.environ['MODEL_NAME']
            if 'BASE_URL' in os.environ and 'base_url' not in data:
                data['base_url'] = os.environ['BASE_URL']
        return data

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """验证 API 密钥"""
        if not v:
            raise ValueError('ARK_API_KEY 环境变量不能为空')

        if len(v) < 20:
            raise ValueError('ARK_API_KEY 长度不能少于20个字符')

        return v

    @field_validator('model_name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称"""
        # 支持豆包和 GLM 模型
        valid_prefixes = ('doubao-', 'glm-', 'gpt-')
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f'MODEL_NAME 必须以 doubao-、glm- 或 gpt- 开头，当前值: {v}')

        return v

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """验证 API 基础 URL"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('BASE_URL 必须以 http:// 或 https:// 开头')

        return v

    @property
    def is_configured(self) -> bool:
        """检查 AI 服务是否已正确配置"""
        return bool(self.api_key and self.model_name)
