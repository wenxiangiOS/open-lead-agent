"""
配置验证模块

在应用启动时验证配置的有效性，防止运行时错误
"""

import logging
from typing import List, Tuple
from .settings import Settings

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigValidator:
    """配置验证器"""

    # 必需配置项
    REQUIRED_CONFIGS = {
        'api_key': 'ARK_API_KEY 是必需的，请设置环境变量 ARK_API_KEY',
        'model_name': 'MODEL_NAME 是必需的，请设置环境变量 MODEL_NAME',
    }

    # 推荐配置项
    RECOMMENDED_CONFIGS = {
        'redis_enabled': '建议启用 Redis 以支持高并发和持久化存储',
    }

    # 数值范围验证
    RANGE_VALIDATIONS = {
        'port': (1, 65535, '端口号必须在 1-65535 之间'),
        'rate_limit_requests': (1, 10000, '限流请求数必须在 1-10000 之间'),
        'rate_limit_window': (1, 3600, '限流时间窗口必须在 1-3600 秒之间'),
        'redis_port': (1, 65535, 'Redis 端口号必须在 1-65535 之间'),
        'redis_ttl': (60, 604800, 'Redis TTL 必须在 60秒-7天 之间'),
        'http_connections': (1, 1000, 'HTTP 连接池大小必须在 1-1000 之间'),
        'http_max_keepalive': (1, 100, 'HTTP keep-alive 连接数必须在 1-100 之间'),
    }

    # 日志级别验证
    VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}

    @classmethod
    def validate(cls, settings: Settings, raise_on_error: bool = True) -> Tuple[bool, List[str]]:
        """
        验证配置

        Args:
            settings: 配置对象
            raise_on_error: 是否在验证失败时抛出异常

        Returns:
            (是否有效, 错误/警告信息列表)
        """
        errors = []
        warnings = []

        # 1. 验证必需配置
        for field, message in cls.REQUIRED_CONFIGS.items():
            value = getattr(settings, field, None)
            if not value:
                errors.append(f"❌ 配置缺失: {message}")

        # 2. 验证推荐配置
        for field, message in cls.RECOMMENDED_CONFIGS.items():
            value = getattr(settings, field, None)
            if not value:
                warnings.append(f"⚠️  配置建议: {message}")

        # 3. 验证数值范围
        for field, (min_val, max_val, message) in cls.RANGE_VALIDATIONS.items():
            value = getattr(settings, field, None)
            if value is not None:
                if not (min_val <= value <= max_val):
                    errors.append(f"❌ 配置错误: {field}={value}, {message}")

        # 4. 验证日志级别
        if settings.log_level not in cls.VALID_LOG_LEVELS:
            errors.append(f"❌ 配置错误: log_level='{settings.log_level}', 必须是 {cls.VALID_LOG_LEVELS} 之一")

        # 5. 验证 Redis 配置
        if settings.redis_enabled:
            if not settings.redis_host:
                errors.append("❌ Redis 已启用但 redis_host 未配置")
            if settings.redis_password == '':
                # 空字符串会被视为未设置密码（与 None 不同）
                warnings.append("⚠️  Redis 未设置密码，生产环境建议设置密码")

        # 6. 验证 API 端点
        if not settings.base_url.startswith(('http://', 'https://')):
            errors.append(f"❌ 配置错误: base_url 必须以 http:// 或 https:// 开头")

        # 7. 验证模型名称
        if settings.model_name and not settings.model_name.startswith('doubao-'):
            warnings.append(f"⚠️  模型名称 '{settings.model_name}' 可能不是有效的豆包模型")

        # 输出验证结果
        cls._log_validation_results(errors, warnings)

        # 决定是否抛出异常
        is_valid = len(errors) == 0
        if not is_valid and raise_on_error:
            raise ConfigValidationError(
                f"配置验证失败:\n" + "\n".join(errors)
            )

        return is_valid, errors + warnings

    @classmethod
    def _log_validation_results(cls, errors: List[str], warnings: List[str]) -> None:
        """记录验证结果"""
        if errors:
            logger.error("=== 配置验证失败 ===")
            for error in errors:
                logger.error(error)
        else:
            logger.info("✅ 配置验证通过")

        if warnings:
            logger.warning("=== 配置警告 ===")
            for warning in warnings:
                logger.warning(warning)

        if not errors and not warnings:
            logger.info("✅ 所有配置项正确")


def validate_config_on_startup(settings: Settings) -> None:
    """
    应用启动时的配置验证

    应该在 FastAPI 的 startup 事件中调用

    Args:
        settings: 配置对象

    Raises:
        ConfigValidationError: 配置验证失败
    """
    logger.info("=" * 50)
    logger.info("开始配置验证...")
    logger.info("=" * 50)

    try:
        is_valid, messages = ConfigValidator.validate(settings, raise_on_error=True)

        # 输出关键配置信息（脱敏）
        logger.info("=== 关键配置信息 ===")
        logger.info(f"应用名称: {settings.app_name}")
        logger.info(f"应用版本: {settings.app_version}")
        logger.info(f"调试模式: {settings.debug}")
        logger.info(f"监听地址: {settings.host}:{settings.port}")
        logger.info(f"AI 模型: {settings.model_name}")
        logger.info(f"API Key: {'*' * 20}{settings.api_key[-4:] if settings.api_key else 'None'}")
        logger.info(f"Redis: {'启用 (' + settings.redis_host + ':' + str(settings.redis_port) + ')' if settings.redis_enabled else '未启用'}")
        logger.info(f"限流: {'启用 (' + str(settings.rate_limit_requests) + '次/' + str(settings.rate_limit_window) + '秒)' if settings.rate_limit_enabled else '未启用'}")
        logger.info(f"日志级别: {settings.log_level}")
        logger.info("=" * 50)

    except ConfigValidationError as e:
        logger.error(str(e))
        raise
