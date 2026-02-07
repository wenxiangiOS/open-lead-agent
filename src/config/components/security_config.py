"""
安全配置

包含 JWT、加密、密钥等安全相关配置
"""

import os
import secrets
from string import ascii_letters, digits
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SecurityConfig(BaseModel):
    """安全配置"""

    # JWT 配置
    jwt_enabled: bool = Field(default=False, description="启用 JWT 认证")
    jwt_secret_key: str = Field(default="", description="JWT 密钥")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256", description="JWT 算法"
    )
    jwt_expiration: int = Field(default=86400, ge=300, le=604800, description="JWT 过期时间（秒）")

    # 密码策略
    password_min_length: int = Field(default=8, ge=6, le=32, description="密码最小长度")
    password_require_uppercase: bool = Field(default=True, description="密码需要大写字母")
    password_require_digit: bool = Field(default=True, description="密码需要数字")
    password_require_special: bool = Field(default=True, description="密码需要特殊字符")

    # API 密钥
    api_key_header: str = Field(default="X-API-Key", description="API 密钥请求头")
    allowed_api_keys: list[str] = Field(default_factory=list, description="允许的 API 密钥列表")

    # 加密
    encryption_key: str | None = Field(default=None, description="加密密钥")
    hash_algorithm: Literal["sha256", "sha512"] = Field(default="sha256", description="哈希算法")

    # 限流
    ip_rate_limit: int = Field(default=1000, ge=100, le=10000, description="IP 级别限流")
    user_rate_limit: int = Field(default=100, ge=10, le=1000, description="用户级别限流")

    # 安全头
    enable_security_headers: bool = Field(default=True, description="启用安全 HTTP 头")
    strict_transport_security: bool = Field(default=True, description="HSTS")

    @field_validator('jwt_enabled')
    @classmethod
    def validate_jwt_enabled(cls, v: bool) -> bool:
        """从环境变量读取 JWT 启用状态"""
        env_enabled = os.getenv('JWT_ENABLED')
        if env_enabled:
            return env_enabled.lower() in ('true', '1', 'yes')
        return v

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """验证 JWT 密钥强度"""
        env_secret = os.getenv('JWT_SECRET_KEY')
        if env_secret:
            v = env_secret

        jwt_enabled = info.data.get('jwt_enabled', False)

        if jwt_enabled:
            if not v:
                # 生产环境启用 JWT 时必须有密钥
                environment = info.data.get('environment', 'development')
                if environment == 'production':
                    raise ValueError('生产环境启用 JWT 时必须设置 JWT_SECRET_KEY')

                # 开发环境生成随机密钥
                v = secrets.token_urlsafe(64)

            # 验证密钥强度
            if len(v) < 32:
                raise ValueError('JWT_SECRET_KEY 长度不能少于32个字符')

            has_upper = any(c.isupper() for c in v)
            has_lower = any(c.islower() for c in v)
            has_digit = any(c.isdigit() for c in v)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

            if not all([has_upper, has_lower, has_digit, has_special]):
                raise ValueError(
                    'JWT_SECRET_KEY 必须包含大小写字母、数字和特殊字符'
                )

        return v

    @staticmethod
    def generate_secret_key(length: int = 64) -> str:
        """生成安全的密钥"""
        alphabet = ascii_letters + digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @property
    def is_jwt_enabled(self) -> bool:
        """检查 JWT 是否已启用并配置"""
        return self.jwt_enabled and bool(self.jwt_secret_key)
