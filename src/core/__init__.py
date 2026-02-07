"""
核心模块

提供错误处理、日志、断路器、分布式锁等核心功能
"""

# 错误严重性
from .error_severity import ErrorSeverity

# 异常定义（新版）
from .enhanced_exceptions import (
    EnhancedException,
    CriticalException,
    HighSeverityException,
    MediumSeverityException,
    LowSeverityException,
    StorageException as EnhancedStorageException,
    RedisException,
    AIServiceException as EnhancedAIServiceException,
    AITimeoutException,
    ValidationException as EnhancedValidationException,
    AuthenticationException as EnhancedAuthenticationException,
    RateLimitException as EnhancedRateLimitException,
    ConfigurationException as EnhancedConfigurationException,
    CircuitBreakerOpenException,
    RefusalException,
)

# 异常定义（旧版 - 兼容）
from .exceptions import (
    AppException,
    StorageException,
    AIServiceException,
    ValidationException,
    AuthenticationException,
    RateLimitException,
    ConfigurationException,
)

# 错误处理器
from .error_handler import ErrorHandler, handle_error
from .enhanced_error_handler import (
    ErrorHandler as EnhancedErrorHandler,
    error_handler,
    handle_errors,
    retry_on_error,
)

# 日志
from .logging import (
    StructuredLogger,
    RequestLogger,
    get_logger,
    api_logger,
    ai_logger,
    redis_logger,
    business_logger
)

# 断路器
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitState,
    circuit_breaker_manager,
    with_circuit_breaker,
)

# 分布式锁
from .distributed_lock import (
    DistributedLock,
    LockManager,
    distributed_lock,
)

__all__ = [
    # 错误严重性
    'ErrorSeverity',

    # 异常类（新版）
    'EnhancedException',
    'CriticalException',
    'HighSeverityException',
    'MediumSeverityException',
    'LowSeverityException',
    'RedisException',
    'AITimeoutException',
    'CircuitBreakerOpenException',

    # 异常类（旧版 - 兼容）
    'AppException',
    'StorageException',
    'AIServiceException',
    'ValidationException',
    'AuthenticationException',
    'RateLimitException',
    'ConfigurationException',

    # 错误处理器
    'ErrorHandler',
    'error_handler',
    'handle_error',
    'handle_errors',
    'retry_on_error',

    # 日志
    'StructuredLogger',
    'RequestLogger',
    'get_logger',
    'api_logger',
    'ai_logger',
    'redis_logger',
    'business_logger',

    # 断路器
    'CircuitBreaker',
    'CircuitBreakerManager',
    'CircuitState',
    'circuit_breaker_manager',
    'with_circuit_breaker',

    # 分布式锁
    'DistributedLock',
    'LockManager',
    'distributed_lock',
]
