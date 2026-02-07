"""
安全中间件

提供 JWT 认证、CORS、安全头等安全相关中间件
"""

import secrets
import logging
from typing import Optional, List, Callable
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# JWT 认证
# ============================================================================

class JWTAuth(HTTPBearer):
    """
    JWT 认证处理器

    验证请求中的 JWT token
    """

    def __init__(
        self,
        auto_error: bool = True,
        realm: str = "protected"
    ):
        super().__init__(auto_error=auto_error, realm=realm)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        验证 JWT token

        Args:
            request: FastAPI 请求

        Returns:
            认证凭据

        Raises:
            HTTPException: 认证失败
        """
        # 检查是否启用 JWT
        if not settings.security.is_jwt_enabled:
            return None

        return await super().__call__(request)


class JWTMiddleware:
    """
    JWT 认证中间件
    """

    def __init__(
        self,
        public_paths: Optional[List[str]] = None,
        exempt_paths: Optional[List[str]] = None
    ):
        """
        初始化 JWT 中间件

        Args:
            public_paths: 公开路径列表（无需认证）
            exempt_paths: 豁免路径列表（无需认证）
        """
        self.public_paths = set(public_paths or [])
        self.exempt_paths = set(exempt_paths or [])

        # 添加默认公开路径
        self.public_paths.update([
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api",
            "/metrics"
        ])

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        path = request.url.path

        # 检查是否是公开路径
        if self._is_public_path(path):
            return await call_next(request)

        # 检查 JWT 认证
        if settings.security.is_jwt_enabled:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "未授权访问",
                        "error_code": "AUTH_REQUIRED",
                        "details": {
                            "message": "需要提供有效的 JWT token"
                        }
                    }
                )

            token = auth_header.split(" ")[1]

            # 验证 token
            try:
                payload = self._verify_token(token)
                # 将用户信息添加到请求状态
                request.state.user = payload
                request.state.user_id = payload.get("sub")
            except Exception as e:
                logger.warning(f"JWT 验证失败: {e}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "认证失败",
                        "error_code": "INVALID_TOKEN",
                        "details": {
                            "message": "Token 无效或已过期"
                        }
                    }
                )

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        # 精确匹配
        if path in self.public_paths:
            return True

        # 前缀匹配
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True

        return False

    def _verify_token(self, token: str) -> dict:
        """
        验证 JWT token

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            Exception: 验证失败
        """
        import jwt

        try:
            payload = jwt.decode(
                token,
                settings.security.jwt_secret_key,
                algorithms=[settings.security.jwt_algorithm]
            )

            # 检查过期时间
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                raise ValueError("Token 已过期")

            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Token 已过期")
        except jwt.InvalidTokenError:
            raise ValueError("Token 无效")
        except Exception as e:
            raise ValueError(f"Token 验证失败: {e}")


# ============================================================================
# 安全头中间件
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全 HTTP 头中间件

    添加各种安全相关的 HTTP 头
    """

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        response = await call_next(request)

        # 添加安全头
        if settings.security.enable_security_headers:
            # HSTS (HTTP Strict Transport Security)
            if settings.security.strict_transport_security:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            # 防止点击劫持
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"

            # XSS 保护
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # 内容安全策略
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

            # 推荐策略
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # 权限策略
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"

        return response


# ============================================================================
# CORS 中间件
# ============================================================================

class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS 中间件

    处理跨域资源共享
    """

    def __init__(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 3600
    ):
        """
        初始化 CORS 中间件

        Args:
            allow_origins: 允许的源
            allow_methods: 允许的 HTTP 方法
            allow_headers: 允许的请求头
            allow_credentials: 是否允许携带凭证
            max_age: 预检请求缓存时间（秒）
        """
        self.allow_origins = allow_origins or settings.server.cors_origins
        self.allow_methods = allow_methods or settings.server.cors_methods
        self.allow_headers = allow_headers or settings.server.cors_headers
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        origin = request.headers.get("origin")

        # 检查源是否允许
        if origin and self._is_allowed_origin(origin):
            response = await call_next(request)

            # 设置 CORS 头
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Max-Age"] = str(self.max_age)

            # 处理预检请求
            if request.method == "OPTIONS":
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "OK"
                    },
                    headers=response.headers
                )

            return response

        # 源不允许，正常处理（由其他中间件处理）
        return await call_next(request)

    def _is_allowed_origin(self, origin: str) -> bool:
        """检查源是否允许"""
        # 允许所有（开发环境）
        if settings.app.is_development and "*" in self.allow_origins:
            return True

        # 精确匹配
        if origin in self.allow_origins:
            return True

        return False


# ============================================================================
# API 密钥认证
# ============================================================================

class APIKeyAuth:
    """
    API 密钥认证

    通过 X-API-Key 头进行认证
    """

    def __init__(self, allowed_keys: Optional[List[str]] = None):
        """
        初始化 API 密钥认证

        Args:
            allowed_keys: 允许的 API 密钥列表
        """
        self.allowed_keys = set(allowed_keys or settings.security.allowed_api_keys)

    async def authenticate(self, request: Request) -> Optional[str]:
        """
        验证 API 密钥

        Args:
            request: FastAPI 请求

        Returns:
            API 密钥标识符，验证失败返回 None

        Raises:
            HTTPException: 认证失败
        """
        api_key = request.headers.get(settings.security.api_key_header)

        if not api_key:
            return None

        # 检查密钥是否允许
        if not self.allowed_keys:
            return None

        # 验证密钥
        if api_key in self.allowed_keys:
            # 返回密钥标识符（可选，用于识别密钥所有者）
            return api_key[:8] + "..."

        return None


# ============================================================================
# 密钥管理工具
# ============================================================================

class KeyManager:
    """
    密钥管理工具

    生成、验证、旋转各种密钥
    """

    @staticmethod
    def generate_jwt_secret(length: int = 64) -> str:
        """
        生成 JWT 密钥

        Args:
            length: 密钥长度

        Returns:
            JWT 密钥
        """
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_api_key(prefix: str = "sk") -> str:
        """
        生成 API 密钥

        Args:
            prefix: 密钥前缀

        Returns:
            API 密钥
        """
        # 生成 32 字节随机数据
        random_bytes = secrets.token_bytes(32)
        # 转换为 base64（去掉填充）
        import base64
        key_data = base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')
        return f"{prefix}_{key_data}"

    @staticmethod
    def validate_jwt_secret(secret: str) -> tuple[bool, List[str]]:
        """
        验证 JWT 密钥强度

        Args:
            secret: JWT 密钥

        Returns:
            (是否有效, 问题列表)
        """
        issues = []

        # 长度检查
        if len(secret) < 32:
            issues.append("密钥长度不能少于32个字符")

        # 复杂度检查
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

        if not (has_upper and has_lower and has_digit and has_special):
            issues.append("密钥必须包含大小写字母、数字和特殊字符")

        # 常见弱密钥检查
        weak_patterns = ["password", "12345678", "secret", "key"]
        lower_secret = secret.lower()
        for pattern in weak_patterns:
            if pattern in lower_secret:
                issues.append(f"密钥不能包含常见词汇: {pattern}")

        return (len(issues) == 0, issues)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        哈希密码

        Args:
            password: 明文密码

        Returns:
            哈希后的密码
        """
        import hashlib
        import base64

        # 使用 PBKDF2
        salt = secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000  # 迭代次数
        )

        # 返回 salt + hash
        return base64.b64encode(salt + pwd_hash).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        验证密码

        Args:
            password: 明文密码
            hashed: 哈希后的密码

        Returns:
            是否匹配
        """
        import hashlib
        import base64

        try:
            # 解码
            data = base64.b64decode(hashed)
            salt = data[:16]
            stored_hash = data[16:]

            # 计算哈希
            pwd_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt,
                100000
            )

            # 比较哈希
            import hmac
            return hmac.compare_digest(pwd_hash, stored_hash)

        except Exception:
            return False


# ============================================================================
# 输入验证中间件
# ============================================================================

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    输入清理中间件

    防止 XSS、SQL 注入等攻击
    """

    def __init__(self):
        """初始化中间件"""
        self.dangerous_patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"javascript:",
            r"on\w+\s*=",  # 事件处理器
            r"(union|select|insert|update|delete|drop|create)\s+",  # SQL 注入
            r"<\?php",  # PHP 标签
            r"\.\./",  # 路径遍历
        ]

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 清理查询参数
        if request.query_params:
            request.state._original_query_params = dict(request.query_params)
            request._query_params = self._sanitize_dict(request.query_params)

        # 清理路径参数
        if request.path_params:
            request.state._original_path_params = dict(request.path_params)
            request._path_params = self._sanitize_dict(request.path_params)

        return await call_next(request)

    def _sanitize_dict(self, data: dict) -> dict:
        """清理字典数据"""
        import re

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # 移除危险字符
                for pattern in self.dangerous_patterns:
                    value = re.sub(pattern, "", value, flags=re.IGNORECASE)
                sanitized[key] = value.strip()
            else:
                sanitized[key] = value

        return sanitized


# ============================================================================
# 全局实例
# ============================================================================

jwt_auth = JWTAuth()
jwt_middleware = JWTMiddleware()
security_headers_middleware = SecurityHeadersMiddleware()
cors_middleware = CORSMiddleware()
input_sanitization_middleware = InputSanitizationMiddleware()
key_manager = KeyManager()
