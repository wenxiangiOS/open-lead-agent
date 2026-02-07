"""CORS Configuration Component"""

import os
from typing import List
from pydantic import Field, BaseModel


class CORSConfig(BaseModel):
    """
    CORS 跨域配置

    统一管理所有 CORS 相关配置，避免在多个文件中分散配置
    """

    # 允许的源地址（逗号分隔）
    allowed_origins: str = Field(
        default="",
        description="允许的跨域源地址，逗号分隔 (例: http://localhost:3000,https://example.com)"
    )

    # 是否允许携带凭证
    allow_credentials: bool = Field(
        default=False,
        description="是否允许跨域请求携带凭证（Cookies）"
    )

    # 允许的 HTTP 方法
    allow_methods: str = Field(
        default="GET,POST,OPTIONS",
        description="允许的 HTTP 方法，逗号分隔"
    )

    # 允许的请求头
    allow_headers: str = Field(
        default="Content-Type,Authorization",
        description="允许的请求头，逗号分隔"
    )

    # 预检请求缓存时间（秒）
    max_age: int = Field(
        default=3600,
        ge=0,
        le=86400,
        description="预检请求的缓存时间（秒），默认 1 小时"
    )

    @classmethod
    def from_env(cls) -> "CORSConfig":
        """从环境变量加载 CORS 配置"""
        return cls(
            allowed_origins=os.getenv("ALLOWED_ORIGINS", ""),
            allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "False").lower() in ("true", "1", "yes"),
            allow_methods=os.getenv("CORS_ALLOW_METHODS", "GET,POST,OPTIONS"),
            allow_headers=os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization"),
            max_age=int(os.getenv("CORS_MAX_AGE", "3600"))
        )

    def get_origins_list(self) -> List[str]:
        """获取源地址列表"""
        origins = self.allowed_origins.split(',') if self.allowed_origins else []
        # 过滤空字符串并去除空白
        return [origin.strip() for origin in origins if origin.strip()]

    def get_methods_list(self) -> List[str]:
        """获取 HTTP 方法列表"""
        methods = self.allow_methods.split(',') if self.allow_methods else []
        return [method.strip() for method in methods if method.strip()]

    def get_headers_list(self) -> List[str]:
        """获取请求头列表"""
        headers = self.allow_headers.split(',') if self.allow_headers else []
        return [header.strip() for header in headers if header.strip()]

    def get_origins_with_fallback(self) -> List[str]:
        """
        获取源地址列表，如果为空则返回默认的 localhost 开发环境配置
        """
        origins = self.get_origins_list()
        if not origins:
            # 开发环境默认配置
            return [
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:8000',
                'http://127.0.0.1:8000',
            ]
        return origins

    def to_middleware_kwargs(self) -> dict:
        """
        转换为 FastAPI CORS 中间件的参数

        Returns:
            dict: 可直接传给 CORSMiddleware 的参数字典
        """
        return {
            "allow_origins": self.get_origins_with_fallback(),
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.get_methods_list(),
            "allow_headers": self.get_headers_list(),
            "max_age": self.max_age
        }
