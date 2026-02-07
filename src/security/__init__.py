"""
安全模块

提供安全相关的功能：
- 配置验证
- 密钥管理
- 输入验证
"""

from .validator import (
    SecurityValidator,
    validate_security_on_startup,
    check_rate_limit_by_ip,
    sanitize_html,
    validate_phone_number,
    validate_email
)

__all__ = [
    'SecurityValidator',
    'validate_security_on_startup',
    'check_rate_limit_by_ip',
    'sanitize_html',
    'validate_phone_number',
    'validate_email',
]
