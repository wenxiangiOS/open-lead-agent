"""
安全配置验证器

在应用启动时验证安全配置
"""

import logging
from typing import List, Tuple
from fastapi import Request

from src.config import settings

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    安全配置验证器

    验证各种安全相关的配置是否正确
    """

    def __init__(self):
        """初始化验证器"""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        验证所有安全配置

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        self.errors = []
        self.warnings = []

        # JWT 配置验证
        self._validate_jwt_config()

        # 生产环境安全检查
        if settings.app.is_production:
            self._validate_production_security()

        # CORS 配置验证
        self._validate_cors_config()

        # API 密钥验证
        self._validate_api_keys()

        # 密码策略验证
        self._validate_password_policy()

        return (len(self.errors) == 0, self.errors, self.warnings)

    def _validate_jwt_config(self):
        """验证 JWT 配置"""
        if not settings.security.is_jwt_enabled:
            if settings.app.is_production:
                self.errors.append(
                    "❌ 生产环境必须启用 JWT 认证 (JWT_ENABLED=true)"
                )
            else:
                self.warnings.append(
                    "⚠️ JWT 认证未启用，建议在生产环境启用"
                )
            return

        # 验证密钥强度
        from src.api.middleware.security import key_manager
        is_valid, issues = key_manager.validate_jwt_secret(settings.security.jwt_secret_key)

        if not is_valid:
            for issue in issues:
                self.errors.append(f"❌ JWT 密钥不安全: {issue}")

    def _validate_production_security(self):
        """验证生产环境安全配置"""
        # 检查调试模式
        if settings.app.debug:
            self.errors.append(
                "❌ 生产环境不能启用调试模式 (DEBUG=false)"
            )

        # 检查 TLS/SSL
        # 这里可以添加 SSL 证书检查
        if settings.app.is_production and not settings.app.is_development:
            # 假设使用 HTTPS，可以检查证书
            pass

        # 检查 CORS 配置
        if "*" in settings.server.cors_origins:
            self.errors.append(
                "❌ 生产环境不能使用允许所有源的 CORS 配置 (CORS_ORIGINS=*)"
            )

    def _validate_cors_config(self):
        """验证 CORS 配置"""
        allowed_origins = settings.server.cors_origins

        # 检查是否允许所有源
        if "*" in allowed_origins:
            if settings.app.is_production:
                self.errors.append(
                    "❌ 生产环境不应允许所有源的 CORS (CORS_ORIGINS=*)"
                )
            else:
                self.warnings.append(
                    "⚠️ CORS 配置允许所有源，仅适用于开发环境"
                )

        # 检查允许的方法
        dangerous_methods = ["DELETE", "PUT", "PATCH"]
        allowed_methods = settings.server.cors_methods

        for method in dangerous_methods:
            if method in allowed_methods and settings.app.is_production:
                self.warnings.append(
                    f"⚠️ CORS 允许 {method} 方法，确保前端需要此功能"
                )

    def _validate_api_keys(self):
        """验证 API 密钥配置"""
        if not settings.security.allowed_api_keys:
            if not settings.security.is_jwt_enabled:
                self.warnings.append(
                    "⚠️ 未配置 API 密钥且未启用 JWT，服务将无认证保护"
                )
            return

        # 检查密钥格式
        for api_key in settings.security.allowed_api_keys:
            if not api_key.startswith(("sk_", "pk_")):
                self.warnings.append(
                    f"⚠️ API 密钥格式不规范: {api_key[:8]}..."
                )

            if len(api_key) < 20:
                self.errors.append(
                    f"❌ API 密钥长度不足: {api_key[:8]}..."
                )

    def _validate_password_policy(self):
        """验证密码策略"""
        policy = settings.security

        # 检查密码最小长度
        if policy.password_min_length < 8:
            self.warnings.append(
                "⚠️ 密码最小长度建议至少 8 位"
            )

        # 检查密码复杂度要求
        if not policy.password_require_uppercase:
            self.warnings.append(
                "⚠️ 建议要求密码包含大写字母"
            )

        if not policy.password_require_digit:
            self.warnings.append(
                "⚠️ 建议要求密码包含数字"
            )

        if not policy.password_require_special:
            self.warnings.append(
                "⚠️ 建议要求密码包含特殊字符"
            )

    def print_report(self):
        """打印验证报告"""
        print("\n" + "=" * 70)
        print("🔒 安全配置验证报告")
        print("=" * 70)

        if not self.errors and not self.warnings:
            print("✅ 所有安全配置检查通过！")
        else:
            if self.errors:
                print(f"\n❌ 发现 {len(self.errors)} 个错误:")
                for error in self.errors:
                    print(f"  {error}")

            if self.warnings:
                print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
                for warning in self.warnings:
                    print(f"  {warning}")

        print("=" * 70 + "\n")


def validate_security_on_startup() -> bool:
    """
    应用启动时验证安全配置

    Returns:
        验证是否通过
    """
    validator = SecurityValidator()
    is_valid, errors, warnings = validator.validate_all()
    validator.print_report()

    if not is_valid:
        raise ValueError(
            "安全配置验证失败，请修复上述错误后再启动服务"
        )

    return is_valid


# ============================================================================
# 安全工具函数
# ============================================================================

def check_rate_limit_by_ip(request: Request, limit: int = 1000) -> bool:
    """
    基于 IP 的限流检查

    Args:
        request: FastAPI 请求
        limit: 限制数量

    Returns:
        是否允许请求
    """
    # 获取客户端 IP
    client_ip = request.client.host
    # TODO: 实现 IP 限流逻辑
    return True


def sanitize_html(html: str) -> str:
    """
    清理 HTML 内容

    Args:
        html: HTML 内容

    Returns:
        清理后的 HTML
    """
    import re

    # 移除 script 标签
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)

    # 移除事件处理器
    html = re.sub(r'on\w+\s*=', '', html, flags=re.IGNORECASE)

    # 移除 javascript: 协议
    html = re.sub(r'javascript:', '', html, flags=re.IGNORECASE)

    return html


def validate_phone_number(phone: str) -> bool:
    """
    验证手机号格式

    Args:
        phone: 手机号

    Returns:
        是否有效
    """
    import re

    # 移除所有非数字字符
    phone = re.sub(r'[^\d]', '', phone)

    # 验证长度和前缀
    if len(phone) != 11:
        return False

    if not phone.startswith(('13', '14', '15', '16', '17', '18', '19')):
        return False

    # 验证第二位（1开头时第二位必须是3-9）
    if phone[0] == '1':
        if phone[1] not in '3456789':
            return False

    return True


def validate_email(email: str) -> bool:
    """
    验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        是否有效
    """
    import re

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
