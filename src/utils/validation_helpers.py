"""
验证工具

统一的验证逻辑，消除重复的验证代码
"""

import re
import logging
from typing import Any, Optional, Dict, List, Callable, Tuple
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# 验证结果
# ============================================================================

@dataclass
class ValidationResult:
    """
    验证结果

    Attributes:
        is_valid: 是否有效
        errors: 错误消息列表
        warnings: 警告消息列表
        sanitized_data: 清理后的数据
    """
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    sanitized_data: Any = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def add_error(self, message: str):
        """添加错误"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """合并另一个验证结果"""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "sanitized_data": self.sanitized_data
        }


# ============================================================================
# 手机号验证
# ============================================================================

def validate_phone_number(phone: str, country_code: str = "CN") -> ValidationResult:
    """
    验证手机号

    Args:
        phone: 手机号
        country_code: 国家代码（CN 中国）

    Returns:
        验证结果
    """
    result = ValidationResult(is_valid=True)

    if not phone:
        result.add_error("手机号不能为空")
        return result

    # 移除所有非数字字符
    sanitized = re.sub(r'[^\d]', '', phone)

    if country_code == "CN":
        # 中国手机号验证
        if len(sanitized) != 11:
            result.add_error(f"手机号长度不正确: {len(sanitized)}位，应为11位")
            return result

        if not sanitized.startswith(('13', '14', '15', '16', '17', '18', '19')):
            result.add_error(f"手机号前缀无效: {sanitized[:3]}")
            return result

        # 验证第二位
        if sanitized[0] == '1' and sanitized[1] not in '3456789':
            result.add_error("手机号格式无效")
            return result

        result.sanitized_data = sanitized
    else:
        # 其他国家的简单验证
        if len(sanitized) < 7 or len(sanitized) > 15:
            result.add_error("手机号长度无效")
            return result

        result.sanitized_data = sanitized

    return result


# ============================================================================
# 邮箱验证
# ============================================================================

def validate_email(email: str, check_domain: bool = False) -> ValidationResult:
    """
    验证邮箱地址

    Args:
        email: 邮箱地址
        check_domain: 是否检查域名（需要 DNS 查询）

    Returns:
        验证结果
    """
    result = ValidationResult(is_valid=True)

    if not email:
        result.add_error("邮箱地址不能为空")
        return result

    # 基本格式验证
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        result.add_error("邮箱地址格式无效")
        return result

    # 检查域名
    if check_domain:
        domain = email.split('@')[1]
        # 这里可以添加 DNS 检查
        # 暂时只做基本检查
        if '.' not in domain:
            result.add_warning("邮箱域名可能无效")

    result.sanitized_data = email
    return result


# ============================================================================
# 姓名验证
# ============================================================================

def validate_name(name: str, min_length: int = 2, max_length: int = 20) -> ValidationResult:
    """
    验证姓名

    Args:
        name: 姓名
        min_length: 最小长度
        max_length: 最大长度

    Returns:
        验证结果
    """
    result = ValidationResult(is_valid=True)

    if not name:
        result.add_error("姓名不能为空")
        return result

    name = name.strip()

    if len(name) < min_length:
        result.add_error(f"姓名长度不能少于{min_length}个字符")

    if len(name) > max_length:
        result.add_error(f"姓名长度不能超过{max_length}个字符")

    # 检查是否包含特殊字符
    if re.search(r'[<>"\'/\\]', name):
        result.add_error("姓名不能包含特殊字符")

    # 检查是否全是数字
    if name.isdigit():
        result.add_error("姓名不能全是数字")

    result.sanitized_data = name
    return result


# ============================================================================
# URL 验证
# ============================================================================

def validate_url(url: str, allowed_schemes: List[str] = None) -> ValidationResult:
    """
    验证 URL

    Args:
        url: URL 地址
        allowed_schemes: 允许的协议列表（默认: http, https）

    Returns:
        验证结果
    """
    result = ValidationResult(is_valid=True)

    if not url:
        result.add_error("URL 不能为空")
        return result

    allowed_schemes = allowed_schemes or ['http', 'https']

    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)

        if not parsed.scheme:
            result.add_error("URL 缺少协议（如 http://）")
            return result

        if parsed.scheme.lower() not in [s.lower() for s in allowed_schemes]:
            result.add_error(f"不支持的协议: {parsed.scheme}")

        if not parsed.netloc:
            result.add_error("URL 缺少域名")

        result.sanitized_data = url

    except Exception as e:
        result.add_error(f"URL 解析失败: {e}")

    return result


# ============================================================================
# JSON 验证
# ============================================================================

def validate_json(json_str: str, schema: Optional[Dict] = None) -> ValidationResult:
    """
    验证 JSON 字符串

    Args:
        json_str: JSON 字符串
        schema: JSON Schema（可选）

    Returns:
        验证结果
    """
    result = ValidationResult(is_valid=True)

    if not json_str:
        result.add_error("JSON 不能为空")
        return result

    try:
        import json
        data = json.loads(json_str)

        # 如果提供了 schema，进行验证
        if schema:
            # 这里可以集成 jsonschema 库
            # 暂时做基本验证
            if isinstance(schema, dict) and 'required' in schema:
                for field in schema['required']:
                    if field not in data:
                        result.add_error(f"缺少必填字段: {field}")

        result.sanitized_data = data

    except json.JSONDecodeError as e:
        result.add_error(f"JSON 格式错误: {e}")

    return result


# ============================================================================
# 敏感词过滤
# ============================================================================

class SensitiveWordFilter:
    """
    敏感词过滤器

    检测和过滤敏感内容
    """

    # 默认敏感词列表
    DEFAULT_WORDS = [
        # 政治敏感词（示例）
        # 暴力/色情词汇（示例）
        # 垃圾广告词汇（示例）
    ]

    def __init__(self, words: Optional[List[str]] = None):
        """
        初始化过滤器

        Args:
            words: 自定义敏感词列表
        """
        self.words = set(words or self.DEFAULT_WORDS)
        self._build_pattern()

    def _build_pattern(self):
        """构建正则表达式模式"""
        if self.words:
            pattern = '|'.join(re.escape(word) for word in self.words)
            self.pattern = re.compile(pattern, re.IGNORECASE)
        else:
            self.pattern = None

    def add_words(self, words: List[str]):
        """添加敏感词"""
        self.words.update(words)
        self._build_pattern()

    def contains_sensitive(self, text: str) -> bool:
        """
        检查文本是否包含敏感词

        Args:
            text: 要检查的文本

        Returns:
            是否包含敏感词
        """
        if not self.pattern:
            return False

        return bool(self.pattern.search(text))

    def filter(self, text: str, replacement: str = "***") -> Tuple[str, int]:
        """
        过滤敏感词

        Args:
            text: 要过滤的文本
            replacement: 替换文本

        Returns:
            (过滤后的文本, 替换数量)
        """
        if not self.pattern:
            return text, 0

        count = 0

        def replace_func(match):
            nonlocal count
            count += 1
            return replacement

        filtered = self.pattern.sub(replace_func, text)
        return filtered, count

    def validate(self, text: str) -> ValidationResult:
        """
        验证文本

        Args:
            text: 要验证的文本

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)

        if self.contains_sensitive(text):
            # 找出所有敏感词
            sensitive_words = []
            if self.pattern:
                sensitive_words = list(set(self.pattern.findall(text)))

            result.add_error(f"文本包含敏感词: {', '.join(sensitive_words)}")

        return result


# ============================================================================
# 验证装饰器
# ============================================================================

def validate_params(**validators):
    """
    参数验证装饰器

    Args:
        **validators: 参数名 -> 验证函数的映射

    Usage:
        @validate_params(
            phone=validate_phone_number,
            email=validate_email
        )
        async def register_user(phone, email):
            return await user_service.create(phone, email)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 验证所有参数
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    result = validator(value)

                    if not result.is_valid:
                        logger.error(
                            f"参数验证失败 [{param_name}]: {result.errors}"
                        )
                        raise ValueError(
                            f"参数 {param_name} 验证失败: {', '.join(result.errors)}"
                        )

                    # 使用清理后的数据
                    if result.sanitized_data is not None:
                        kwargs[param_name] = result.sanitized_data

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    result = validator(value)

                    if not result.is_valid:
                        logger.error(
                            f"参数验证失败 [{param_name}]: {result.errors}"
                        )
                        raise ValueError(
                            f"参数 {param_name} 验证失败: {', '.join(result.errors)}"
                        )

                    if result.sanitized_data is not None:
                        kwargs[param_name] = result.sanitized_data

            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 批量验证
# ============================================================================

def validate_batch(
    data: Dict[str, Any],
    rules: Dict[str, Callable]
) -> ValidationResult:
    """
    批量验证

    Args:
        data: 要验证的数据字典
        rules: 验证规则字典（字段名 -> 验证函数）

    Returns:
        综合验证结果

    Usage:
        rules = {
            "phone": lambda x: validate_phone_number(x),
            "email": lambda x: validate_email(x),
            "name": lambda x: validate_name(x)
        }
        result = validate_batch(user_data, rules)
    """
    overall_result = ValidationResult(is_valid=True)

    for field_name, validator in rules.items():
        value = data.get(field_name)

        if value is None:
            overall_result.add_warning(f"字段 {field_name} 不存在")
            continue

        result = validator(value)
        overall_result.merge(result)

        # 更新清理后的数据
        if result.sanitized_data is not None:
            data[field_name] = result.sanitized_data

    return overall_result


# ============================================================================
# 预配置的过滤器
# ============================================================================

# 全局敏感词过滤器
sensitive_filter = SensitiveWordFilter()
