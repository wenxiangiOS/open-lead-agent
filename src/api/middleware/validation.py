"""
请求验证层

提供统一的请求验证功能：
1. Pydantic 模型验证
2. 自定义验证规则
3. 验证装饰器
4. 验证错误处理
"""

import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Optional, Dict, List
from fastapi import Request, HTTPException
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def _validation_detail(errors: List[str], source: str) -> Dict[str, Any]:
    return {
        "success": False,
        "error": "request_validation_failed",
        "error_code": "VALIDATION_ERROR",
        "details": {
            "source": source,
            "errors": errors,
        }
    }


class ValidationRule:
    """验证规则基类"""

    def __init__(self, field_name: str, error_message: Optional[str] = None):
        self.field_name = field_name
        self.error_message = error_message or f"{field_name} 验证失败"

    def validate(self, value: Any) -> bool:
        """验证值是否有效"""
        raise NotImplementedError

    def get_error_message(self) -> str:
        """获取错误消息"""
        return self.error_message


class RequiredFieldRule(ValidationRule):
    """必填字段验证"""

    def validate(self, value: Any) -> bool:
        return value is not None and value != ""


class MinLengthRule(ValidationRule):
    """最小长度验证"""

    def __init__(self, field_name: str, min_length: int):
        super().__init__(field_name, f"{field_name} 长度不能少于 {min_length} 个字符")
        self.min_length = min_length

    def validate(self, value: Any) -> bool:
        if value is None:
            return False
        return len(str(value)) >= self.min_length


class MaxLengthRule(ValidationRule):
    """最大长度验证"""

    def __init__(self, field_name: str, max_length: int):
        super().__init__(field_name, f"{field_name} 长度不能超过 {max_length} 个字符")
        self.max_length = max_length

    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        return len(str(value)) <= self.max_length


class PatternRule(ValidationRule):
    """正则表达式验证"""

    def __init__(self, field_name: str, pattern: str, error_message: Optional[str] = None):
        super().__init__(field_name, error_message)
        import re
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        return bool(self.pattern.match(str(value)))


class RangeRule(ValidationRule):
    """数值范围验证"""

    def __init__(self, field_name: str, min_value: Optional[float] = None, max_value: Optional[float] = None):
        super().__init__(field_name, f"{field_name} 必须在 {min_value} 到 {max_value} 之间")
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        try:
            num_value = float(value)
            if self.min_value is not None and num_value < self.min_value:
                return False
            if self.max_value is not None and num_value > self.max_value:
                return False
            return True
        except (ValueError, TypeError):
            return False


class RequestValidator:
    """请求验证器"""

    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}

    def add_rule(self, field_name: str, rule: ValidationRule) -> 'RequestValidator':
        """添加验证规则"""
        if field_name not in self.rules:
            self.rules[field_name] = []
        self.rules[field_name].append(rule)
        return self

    def add_required(self, *field_names: str) -> 'RequestValidator':
        """添加必填字段验证"""
        for field_name in field_names:
            self.add_rule(field_name, RequiredFieldRule(field_name))
        return self

    def add_min_length(self, field_name: str, min_length: int) -> 'RequestValidator':
        """添加最小长度验证"""
        self.add_rule(field_name, MinLengthRule(field_name, min_length))
        return self

    def add_max_length(self, field_name: str, max_length: int) -> 'RequestValidator':
        """添加最大长度验证"""
        self.add_rule(field_name, MaxLengthRule(field_name, max_length))
        return self

    def add_pattern(self, field_name: str, pattern: str, error_message: Optional[str] = None) -> 'RequestValidator':
        """添加正则表达式验证"""
        self.add_rule(field_name, PatternRule(field_name, pattern, error_message))
        return self

    def add_range(self, field_name: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> 'RequestValidator':
        """添加数值范围验证"""
        self.add_rule(field_name, RangeRule(field_name, min_value, max_value))
        return self

    def validate(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证数据

        Args:
            data: 要验证的数据字典

        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []

        for field_name, rules in self.rules.items():
            value = data.get(field_name)

            for rule in rules:
                if not rule.validate(value):
                    errors.append(rule.get_error_message())

        return len(errors) == 0, errors


def validate_request(validator: RequestValidator):
    """
    请求验证装饰器

    Usage:
        @validate_request(
            RequestValidator()
            .add_required("account_id", "question")
            .add_min_length("question", 1)
            .add_max_length("question", 1000)
        )
        async def my_endpoint(request: Dict[str, Any]):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 尝试从参数中获取请求数据
            request_data = None

            # 从位置参数中查找
            for arg in args:
                if isinstance(arg, dict):
                    request_data = arg
                    break
                elif isinstance(arg, BaseModel):
                    request_data = arg.model_dump()
                    break

            # 如果没找到，从关键字参数中查找
            if request_data is None:
                for key, value in kwargs.items():
                    if 'request' in key.lower() and isinstance(value, dict):
                        request_data = value
                        break
                    elif isinstance(value, BaseModel):
                        request_data = value.model_dump()
                        break

            # 执行验证
            if request_data is not None:
                is_valid, errors = validator.validate(request_data)
                if not is_valid:
                    error_message = "; ".join(errors)
                    logger.warning(f"请求验证失败: {error_message}")
                    raise HTTPException(
                        status_code=400,
                        detail=_validation_detail(errors, source="request_validator")
                    )

            # 调用原始函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def validate_pydantic(model: type[BaseModel]):
    """
    Pydantic 模型验证装饰器

    Usage:
        @validate_pydantic(ChatRequest)
        async def my_endpoint(request: Dict[str, Any]):
            # request 已经是验证过的 ChatRequest 对象
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找请求数据
            request_data = None
            request_arg_name = None

            # 从位置参数中查找
            for i, arg in enumerate(args):
                if isinstance(arg, dict):
                    request_data = arg
                    request_arg_name = f"arg_{i}"
                    break
                elif isinstance(arg, BaseModel):
                    # 已经是 Pydantic 模型，直接使用
                    return await func(*args, **kwargs)

            # 如果没找到，从关键字参数中查找
            if request_data is None:
                for key, value in kwargs.items():
                    if 'request' in key.lower() and isinstance(value, dict):
                        request_data = value
                        request_arg_name = key
                        break

            # 验证数据
            if request_data is not None:
                try:
                    validated = model(**request_data)
                    # 替换原始参数为验证后的对象
                    if request_arg_name:
                        if request_arg_name.startswith("arg_"):
                            # 位置参数，需要重新构建参数列表
                            arg_index = int(request_arg_name.split("_")[1])
                            new_args = list(args)
                            new_args[arg_index] = validated
                            args = tuple(new_args)
                        else:
                            # 关键字参数
                            kwargs[request_arg_name] = validated
                except ValidationError as e:
                    errors = []
                    for error in e.errors():
                        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
                        errors.append(f"{field}: {error['msg']}")

                    logger.warning(f"Pydantic 验证失败: {errors}")
                    raise HTTPException(
                        status_code=400,
                        detail=_validation_detail(errors, source="pydantic")
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


class CommonValidators:
    """常用验证器集合"""

    @staticmethod
    def user_id() -> RequestValidator:
        """用户 ID 验证"""
        return (
            RequestValidator()
            .add_required("user_id")
            .add_pattern("user_id", r"^[\w\-\.]{1,50}$", "用户 ID 格式不正确")
        )

    @staticmethod
    def chat_message() -> RequestValidator:
        """聊天消息验证"""
        return (
            RequestValidator()
            .add_required("question")
            .add_min_length("question", 1)
            .add_max_length("question", 5000)
        )

    @staticmethod
    def pagination() -> RequestValidator:
        """分页参数验证"""
        return (
            RequestValidator()
            .add_range("limit", min_value=1, max_value=100)
            .add_range("offset", min_value=0, max_value=10000)
        )

    @staticmethod
    def rating() -> RequestValidator:
        """评分验证"""
        return (
            RequestValidator()
            .add_required("rating")
            .add_range("rating", min_value=1, max_value=5)
        )
