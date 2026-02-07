"""
工具模块

提供统一的工具函数和装饰器，消除重复代码
"""

# 错误处理工具
from .error_helpers import (
    safe_execute,
    retry_on_failure,
    ignore_errors,
    with_error_handling,
    ErrorContext,
    execute_safely,
    execute_safely_async
)

# Redis 工具
from .redis_helpers import (
    RedisOperation,
    redis_op,
    redis_get,
    redis_set,
    redis_get_json,
    redis_set_json,
    redis_delete,
    redis_exists,
    redis_fallback,
    sync_redis_fallback
)

# 日志工具
from .logging_helpers import (
    StructuredLogger,
    log_execution_time,
    log_api_call,
    log_performance,
    get_logger,
    api_logger,
    service_logger,
    db_logger,
    cache_logger
)

# 验证工具
from .validation_helpers import (
    ValidationResult,
    validate_phone_number,
    validate_email,
    validate_name,
    validate_url,
    validate_json,
    SensitiveWordFilter,
    sensitive_filter,
    validate_params,
    validate_batch
)

__all__ = [
    # 错误处理
    'safe_execute',
    'retry_on_failure',
    'ignore_errors',
    'with_error_handling',
    'ErrorContext',
    'execute_safely',
    'execute_safely_async',

    # Redis
    'RedisOperation',
    'redis_op',
    'redis_get',
    'redis_set',
    'redis_get_json',
    'redis_set_json',
    'redis_delete',
    'redis_exists',
    'redis_fallback',
    'sync_redis_fallback',

    # 日志
    'StructuredLogger',
    'log_execution_time',
    'log_api_call',
    'log_performance',
    'get_logger',
    'api_logger',
    'service_logger',
    'db_logger',
    'cache_logger',

    # 验证
    'ValidationResult',
    'validate_phone_number',
    'validate_email',
    'validate_name',
    'validate_url',
    'validate_json',
    'SensitiveWordFilter',
    'sensitive_filter',
    'validate_params',
    'validate_batch',
]
