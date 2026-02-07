"""
服务层单元测试

测试覆盖:
- ValidationService: 验证服务
- RefusalService: 拒绝检测服务
- FieldSkipService: 字段跳过服务
- Validators: 验证器工具
- UserProfile: 用户资料模型
- Repository: 仓储实现
- ErrorHandler: 错误处理
- Infrastructure: 缓存和队列
- RateLimiter: 分级限流
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# Import services to test
from src.services.validation_service import ValidationService, validation_service
from src.services.refusal_service import RefusalService, refusal_service
from src.services.field_skip_service import FieldSkipService, field_skip_service
from src.utils.validators import PhoneValidator, WeChatValidator, EmailValidator
from src.models.user_profile import UserProfile, Gender, MatchStatus
from src.repositories.user_profile_repository import MemoryUserProfileRepository
from src.core.error_handler import (
    ValidationError,
    AIServiceError,
    StorageError,
    error_handler,
    handle_errors
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_service():
    """Mock Redis 服务"""
    mock = AsyncMock()
    mock.is_enabled.return_value = True
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def sample_user_profile():
    """示例用户资料"""
    return UserProfile(
        account_id="user_123",
        phone="13800138000",
        gender=Gender.MALE,
        age=28,
        height=175,
        education="本科",
        income="20-30万",
        city="北京",
        match_status=MatchStatus.MATCHING
    )


@pytest.fixture
def sample_chat_request():
    """示例对话请求"""
    return {
        "accountId": "user_123",
        "content": "你好，我想找对象",
        "currentRound": 1
    }


# ============================================================================
# TestValidationService
# ============================================================================

class TestValidationService:
    """验证服务测试"""

    @pytest.fixture
    def validation_svc(self, mock_redis_service):
        """创建验证服务实例"""
        with patch('src.services.validation_service.redis_service', mock_redis_service):
            return ValidationService()

    @pytest.mark.asyncio
    async def test_validate_phone_valid(self, validation_svc):
        """测试有效手机号验证"""
        result = await validation_svc.validate_phone("13800138000")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_phone_invalid(self, validation_svc):
        """测试无效手机号验证"""
        result = await validation_svc.validate_phone("12345678901")
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_phone_with_cache(self, validation_svc, mock_redis_service):
        """测试带缓存的手机号验证"""
        # 模拟缓存命中
        mock_redis_service.get.return_value = "true"
        result = await validation_svc.validate_phone("13800138000")
        mock_redis_service.get.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_wechat_valid(self, validation_svc):
        """测试有效微信号验证"""
        result = await validation_svc.validate_wechat("wechat_id_123")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_wechat_invalid_too_long(self, validation_svc):
        """测试过长的微信号"""
        result = await validation_svc.validate_wechat("a" * 21)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_wechat_invalid_has_space(self, validation_svc):
        """测试包含空格的微信号"""
        result = await validation_svc.validate_wechat("wechat_123 456")
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_email_valid(self, validation_svc):
        """测试有效邮箱验证"""
        result = await validation_svc.validate_email("test@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_email_invalid(self, validation_svc):
        """测试无效邮箱验证"""
        result = await validation_svc.validate_email("invalid-email")
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_age_valid(self, validation_svc):
        """测试有效年龄验证"""
        result = await validation_svc.validate_age(25)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_age_too_young(self, validation_svc):
        """测试年龄过小"""
        result = await validation_svc.validate_age(17)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_age_too_old(self, validation_svc):
        """测试年龄过大"""
        result = await validation_svc.validate_age(61)
        assert result is False


# ============================================================================
# TestRefusalService
# ============================================================================

class TestRefusalService:
    """拒绝检测服务测试"""

    @pytest.fixture
    def refusal_svc(self):
        """创建拒绝检测服务实例"""
        return RefusalService()

    def test_is_refusal_clear_refusal(self, refusal_svc):
        """测试明确拒绝"""
        result = refusal_svc.is_refusal("我不想继续了")
        assert result is True

    def test_is_refusal_polite_refusal(self, refusal_svc):
        """测试礼貌拒绝"""
        result = refusal_svc.is_refusal("暂时不需要")
        assert result is True

    def test_is_refusal_negative_response(self, refusal_svc):
        """测试负面回应"""
        result = refusal_svc.is_refusal("不太感兴趣")
        assert result is True

    def test_is_refusal_positive_response(self, refusal_svc):
        """测试正面回应（非拒绝）"""
        result = refusal_svc.is_refusal("好的，请继续")
        assert result is False

    def test_is_refusal_question(self, refusal_svc):
        """测试问题（非拒绝）"""
        result = refusal_svc.is_refusal("你们有哪些服务？")
        assert result is False

    def test_is_refusal_neutral_response(self, refusal_svc):
        """测试中性回应"""
        result = refusal_svc.is_refusal("我在考虑一下")
        # "考虑一下"通常是拒绝
        assert result is True

    def test_is_refusal_empty(self, refusal_svc):
        """测试空输入"""
        result = refusal_svc.is_refusal("")
        assert result is False


# ============================================================================
# TestFieldSkipService
# ============================================================================

class TestFieldSkipService:
    """字段跳过服务测试"""

    @pytest.fixture
    def field_skip_svc(self):
        """创建字段跳过服务实例"""
        return FieldSkipService()

    def test_should_skip_phone_true(self, field_skip_svc):
        """测试应该跳过手机号"""
        result = field_skip_svc.should_skip_phone("我不想提供手机号")
        assert result is True

    def test_should_skip_phone_false(self, field_skip_svc):
        """测试不应跳过手机号"""
        result = field_skip_svc.should_skip_phone("我的手机号是13800138000")
        assert result is False

    def test_should_skip_wechat_true(self, field_skip_svc):
        """测试应该跳过微信号"""
        result = field_skip_svc.should_skip_wechat("不方便给微信号")
        assert result is True

    def test_should_skip_wechat_false(self, field_skip_svc):
        """测试不应跳过微信号"""
        result = field_skip_svc.should_skip_wechat("加我微信wechat123")
        assert result is False

    def test_should_skip_email_true(self, field_skip_svc):
        """测试应该跳过邮箱"""
        result = field_skip_svc.should_skip_email("不想留邮箱")
        assert result is True

    def test_should_skip_email_false(self, field_skip_svc):
        """测试不应跳过邮箱"""
        result = field_skip_svc.should_skip_email("邮箱是test@example.com")
        assert result is False

    def test_should_skip_income_true(self, field_skip_svc):
        """测试应该跳过收入"""
        result = field_skip_svc.should_skip_income("收入不太方便说")
        assert result is True

    def test_should_skip_income_false(self, field_skip_svc):
        """测试不应跳过收入"""
        result = field_skip_svc.should_skip_income("年收入20万左右")
        assert result is False


# ============================================================================
# TestValidators
# ============================================================================

class TestPhoneValidator:
    """手机号验证器测试"""

    def test_is_valid_valid_phone(self):
        """测试有效手机号"""
        assert PhoneValidator.is_valid("13800138000") is True
        assert PhoneValidator.is_valid("15912345678") is True
        assert PhoneValidator.is_valid("18888888888") is True

    def test_is_valid_invalid_length(self):
        """测试无效长度"""
        assert PhoneValidator.is_valid("1234567890") is False  # 10位
        assert PhoneValidator.is_valid("123456789012") is False  # 12位

    def test_is_valid_invalid_prefix(self):
        """测试无效前缀"""
        assert PhoneValidator.is_valid("10012345678") is False
        assert PhoneValidator.is_valid("12312345678") is False

    def test_is_valid_non_numeric(self):
        """测试非数字"""
        assert PhoneValidator.is_valid("1380013800a") is False
        assert PhoneValidator.is_valid("138-0013-8000") is False

    def test_normalize(self):
        """测试手机号标准化"""
        assert PhoneValidator.normalize(" 138 0013 8000 ") == "13800138000"
        assert PhoneValidator.normalize("+86-138-0013-8000") == "13800138000"
        assert PhoneValidator.normalize("") == ""

    def test_mask(self):
        """测试手机号脱敏"""
        assert PhoneValidator.mask("13800138000") == "138****8000"
        assert PhoneValidator.mask("") == ""


class TestWeChatValidator:
    """微信号验证器测试"""

    def test_is_valid_valid_wechat(self):
        """测试有效微信号"""
        assert WeChatValidator.is_valid("wechat_id") is True
        assert WeChatValidator.is_valid("wx123456") is True
        assert WeChatValidator.is_valid("user_123") is True
        assert WeChatValidator.is_valid("abc") is True  # 最短3个字符

    def test_is_valid_too_long(self):
        """测试过长"""
        assert WeChatValidator.is_valid("a" * 21) is False

    def test_is_valid_too_short(self):
        """测试过短"""
        assert WeChatValidator.is_valid("ab") is False

    def test_is_valid_invalid_characters(self):
        """测试无效字符"""
        assert WeChatValidator.is_valid("wechat 123") is False
        assert WeChatValidator.is_valid("微信123") is False

    def test_is_valid_empty(self):
        """测试空值"""
        assert WeChatValidator.is_valid("") is False


class TestEmailValidator:
    """邮箱验证器测试"""

    def test_is_valid_valid_email(self):
        """测试有效邮箱"""
        assert EmailValidator.is_valid("test@example.com") is True
        assert EmailValidator.is_valid("user.name@example.com") is True
        assert EmailValidator.is_valid("user+tag@example.co.uk") is True

    def test_is_valid_no_at(self):
        """测试缺少@"""
        assert EmailValidator.is_valid("invalid-email") is False

    def test_is_valid_no_domain(self):
        """测试缺少域名"""
        assert EmailValidator.is_valid("user@") is False

    def test_is_valid_no_local(self):
        """测试缺少本地部分"""
        assert EmailValidator.is_valid("@example.com") is False

    def test_is_valid_empty(self):
        """测试空值"""
        assert EmailValidator.is_valid("") is False


# ============================================================================
# TestUserProfile
# ============================================================================

class TestUserProfile:
    """用户资料模型测试"""

    def test_create_profile(self):
        """测试创建用户资料"""
        profile = UserProfile(
            account_id="user_123",
            phone="13800138000",
            gender=Gender.MALE,
            age=28
        )
        assert profile.account_id == "user_123"
        assert profile.phone == "13800138000"
        assert profile.gender == Gender.MALE
        assert profile.age == 28

    def test_profile_to_dict(self, sample_user_profile):
        """测试资料转字典"""
        data = sample_user_profile.to_dict()
        assert isinstance(data, dict)
        assert data["account_id"] == "user_123"
        assert data["phone"] == "13800138000"

    def test_profile_from_dict(self):
        """测试从字典创建资料"""
        data = {
            "account_id": "user_456",
            "phone": "13900139000",
            "gender": "female",
            "age": 25
        }
        profile = UserProfile.from_dict(data)
        assert profile.account_id == "user_456"
        assert profile.phone == "13900139000"
        assert profile.gender == Gender.FEMALE


# ============================================================================
# TestMemoryUserProfileRepository
# ============================================================================

class TestMemoryUserProfileRepository:
    """内存用户资料仓储测试"""

    @pytest.fixture
    def repository(self):
        """创建仓储实例"""
        return MemoryUserProfileRepository()

    @pytest.mark.asyncio
    async def test_save_and_get(self, repository, sample_user_profile):
        """测试保存和获取"""
        await repository.save(sample_user_profile)
        retrieved = await repository.get("user_123")
        assert retrieved is not None
        assert retrieved.account_id == "user_123"
        assert retrieved.phone == "13800138000"

    @pytest.mark.asyncio
    async def test_get_not_found(self, repository):
        """测试获取不存在的用户"""
        result = await repository.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repository, sample_user_profile):
        """测试更新用户资料"""
        await repository.save(sample_user_profile)
        sample_user_profile.age = 29
        await repository.update(sample_user_profile)
        retrieved = await repository.get("user_123")
        assert retrieved.age == 29

    @pytest.mark.asyncio
    async def test_delete(self, repository, sample_user_profile):
        """测试删除用户资料"""
        await repository.save(sample_user_profile)
        await repository.delete("user_123")
        result = await repository.get("user_123")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, repository, sample_user_profile):
        """测试检查用户是否存在"""
        await repository.save(sample_user_profile)
        assert await repository.exists("user_123") is True
        assert await repository.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_all(self, repository):
        """测试获取所有用户"""
        profile1 = UserProfile(account_id="user_1", phone="13800138001", gender=Gender.MALE)
        profile2 = UserProfile(account_id="user_2", phone="13800138002", gender=Gender.FEMALE)
        await repository.save(profile1)
        await repository.save(profile2)
        all_users = await repository.get_all()
        assert len(all_users) == 2


# ============================================================================
# TestErrorHandler
# ============================================================================

class TestErrorHandler:
    """错误处理器测试"""

    def test_validation_error_creation(self):
        """测试创建验证错误"""
        error = ValidationError("手机号格式错误", field="phone")
        assert error.message == "手机号格式错误"
        assert error.field == "phone"
        assert error.status_code == 400

    def test_ai_service_error_creation(self):
        """测试创建AI服务错误"""
        error = AIServiceError("AI调用失败", details={"timeout": True})
        assert error.message == "AI调用失败"
        assert error.details["timeout"] is True
        assert error.status_code == 502

    def test_storage_error_creation(self):
        """测试创建存储错误"""
        error = StorageError("Redis连接失败", operation="set")
        assert error.message == "Redis连接失败"
        assert error.operation == "set"
        assert error.status_code == 503

    @pytest.mark.asyncio
    async def test_handle_validation_error(self):
        """测试处理验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("测试错误")
        assert exc_info.value.message == "测试错误"

    @pytest.mark.asyncio
    async def test_handle_errors_decorator(self):
        """测试错误处理装饰器"""
        @handle_errors
        async def failing_function():
            raise ValidationError("装饰器测试")
        with pytest.raises(ValidationError):
            await failing_function()


# ============================================================================
# TestStructuredLogging
# ============================================================================

class TestStructuredLogging:
    """结构化日志测试"""

    def test_logger_creation(self):
        """测试创建日志器"""
        from src.core.logging import StructuredLogger, get_logger
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_log_sanitization(self):
        """测试日志脱敏"""
        from src.core.logging import StructuredLogger
        logger = StructuredLogger("test")
        data = {
            "phone": "13800138000",
            "token": "secret_token_123",
            "normal_field": "normal_value"
        }
        sanitized = logger._sanitize(data)
        assert sanitized["phone"] == "138****8000"
        assert "token" in sanitized
        assert sanitized["normal_field"] == "normal_value"


# ============================================================================
# TestInfrastructure
# ============================================================================

class TestMemoryCache:
    """内存缓存测试"""

    @pytest.fixture
    def cache(self):
        from src.infrastructure.cache import MemoryCache
        return MemoryCache(max_size=100, ttl=60)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """测试设置和获取"""
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_not_found(self, cache):
        """测试获取不存在的键"""
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """测试删除"""
        await cache.set("key1", "value1")
        await cache.delete("key1")
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """测试清空"""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None


class TestMemoryQueue:
    """内存队列测试"""

    @pytest.fixture
    def queue(self):
        from src.infrastructure.queue import MemoryQueue
        return MemoryQueue(max_workers=2)

    @pytest.mark.asyncio
    async def test_submit_task(self, queue):
        """测试提交任务"""
        async def dummy_task():
            return "result"
        task_id = await queue.submit("test_task", dummy_task)
        assert task_id is not None
        assert isinstance(task_id, str)

    @pytest.mark.asyncio
    async def test_get_task_result(self, queue):
        """测试获取任务结果"""
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "result"
        await queue.start()
        task_id = await queue.submit("test_task", dummy_task)
        # 等待任务完成
        await asyncio.sleep(0.2)
        result = await queue.get_task_result(task_id, timeout=1)
        assert result == "result"
        await queue.stop()


# ============================================================================
# TestTieredRateLimiter
# ============================================================================

class TestTieredRateLimiter:
    """分级限流测试"""

    @pytest.fixture
    def limiter(self):
        from src.api.middleware.tiered_rate_limit import TieredRateLimiter
        return TieredRateLimiter()

    def test_get_user_tier_default(self, limiter):
        """测试获取默认用户级别"""
        tier = limiter.get_user_tier("new_user")
        assert tier == "free"

    def test_set_user_tier(self, limiter):
        """测试设置用户级别"""
        limiter.set_user_tier("user_123", "vip")
        tier = limiter.get_user_tier("user_123")
        assert tier == "vip"

    def test_get_limit_free(self, limiter):
        """测试免费用户限制"""
        limit = limiter.get_limit("free_user")
        assert limit["requests"] == 10
        assert limit["window"] == 60

    def test_get_limit_vip(self, limiter):
        """测试VIP用户限制"""
        limiter.set_user_tier("vip_user", "vip")
        limit = limiter.get_limit("vip_user")
        assert limit["requests"] == 100
        assert limit["window"] == 60

    def test_get_limit_enterprise(self, limiter):
        """测试企业用户限制"""
        limiter.set_user_tier("ent_user", "enterprise")
        limit = limiter.get_limit("ent_user")
        assert limit["requests"] == 1000
        assert limit["window"] == 60


# ============================================================================
# Test Configuration
# ============================================================================

def test_pytest_config():
    """测试pytest配置"""
    # 确保pytest可以正确发现和运行测试
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
