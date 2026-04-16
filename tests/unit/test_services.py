"""
服务层单元测试

测试覆盖:
- Validators: 验证器工具
- UserProfile: 用户资料模型
- Infrastructure: 缓存和队列
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime

# Import actual classes that exist
from src.utils.validators import (
    PhoneValidator,
    WechatValidator,
    ContactValidator,
    AgeValidator,
    HeightValidator,
    InputValidator,
    RefusalDetector
)
from src.models.user_profile import UserProfile


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_user_profile():
    """示例用户资料"""
    return UserProfile(
        account_id="user_123",
        contact="13800138000",
        sex="男",
        age=28,
        height="175cm",
        education="本科",
        monthly_income="20-30万",
        location="北京"
    )


# ============================================================================
# TestPhoneValidator
# ============================================================================

class TestPhoneValidator:
    """手机号验证器测试"""

    def test_is_valid_valid_phone(self):
        """测试有效手机号"""
        assert PhoneValidator.is_valid("13800138000")[0] is True
        assert PhoneValidator.is_valid("15912345678")[0] is True
        assert PhoneValidator.is_valid("18888888888")[0] is True

    def test_is_valid_invalid_length(self):
        """测试无效长度"""
        assert PhoneValidator.is_valid("1234567890")[0] is False  # 10位
        assert PhoneValidator.is_valid("123456789012")[0] is False  # 12位

    def test_is_valid_invalid_prefix(self):
        """测试无效前缀"""
        assert PhoneValidator.is_valid("10012345678")[0] is False
        assert PhoneValidator.is_valid("12312345678")[0] is False

    def test_is_valid_non_numeric(self):
        """测试非数字"""
        assert PhoneValidator.is_valid("1380013800a")[0] is False
        # 带横杠的号码会被自动清理后验证
        result = PhoneValidator.is_valid("138-0013-8000")
        assert result[0] is True  # 清理后应该是有效的

    def test_is_valid_hongkong_phone(self):
        """测试香港手机号"""
        assert PhoneValidator.is_valid("51234567")[0] is True
        assert PhoneValidator.is_valid("61234567")[0] is True
        assert PhoneValidator.is_valid("91234567")[0] is True


# ============================================================================
# TestWechatValidator
# ============================================================================

class TestWechatValidator:
    """微信号验证器测试"""

    def test_is_valid_valid_wechat(self):
        """测试有效微信号"""
        assert WechatValidator.is_valid("wechat_id")[0] is True
        assert WechatValidator.is_valid("wx123456")[0] is True
        assert WechatValidator.is_valid("user_123")[0] is True

    def test_is_valid_too_long(self):
        """测试过长"""
        assert WechatValidator.is_valid("a" * 21)[0] is False

    def test_is_valid_too_short(self):
        """测试过短"""
        assert WechatValidator.is_valid("ab")[0] is False

    def test_is_valid_invalid_characters(self):
        """测试无效字符"""
        assert WechatValidator.is_valid("wechat 123")[0] is False
        assert WechatValidator.is_valid("微信123")[0] is False

    def test_is_valid_empty(self):
        """测试空值"""
        assert WechatValidator.is_valid("")[0] is False


# ============================================================================
# TestContactValidator
# ============================================================================

class TestContactValidator:
    """联系方式验证器测试"""

    def test_is_valid_phone(self):
        """测试手机号"""
        is_valid, contact_type, _ = ContactValidator.is_valid_contact("13800138000")
        assert is_valid is True
        assert contact_type == "phone"

    def test_is_valid_wechat(self):
        """测试微信号"""
        is_valid, contact_type, _ = ContactValidator.is_valid_contact("wechat123")
        assert is_valid is True
        assert contact_type == "wechat"

    def test_is_valid_invalid(self):
        """测试无效联系方式"""
        # "invalid" 实际上匹配微信号规则（字母开头，5-20位），所以是有效的
        # 需要使用真正无效的输入
        is_valid, contact_type, _ = ContactValidator.is_valid_contact("123")  # 纯数字，不是手机号也不是微信号
        assert is_valid is False


# ============================================================================
# TestAgeValidator
# ============================================================================

class TestAgeValidator:
    """年龄验证器测试"""

    def test_is_valid_valid_age(self):
        """测试有效年龄"""
        assert AgeValidator.is_valid(25)[0] is True
        assert AgeValidator.is_valid(30)[0] is True
        assert AgeValidator.is_valid("28")[0] is True

    def test_is_valid_too_young(self):
        """测试年龄过小"""
        assert AgeValidator.is_valid(17)[0] is False

    def test_is_valid_too_old(self):
        """测试年龄过大"""
        assert AgeValidator.is_valid(101)[0] is False

    def test_is_valid_invalid(self):
        """测试无效年龄"""
        assert AgeValidator.is_valid("abc")[0] is False


# ============================================================================
# TestHeightValidator
# ============================================================================

class TestHeightValidator:
    """身高验证器测试"""

    def test_is_valid_valid_height(self):
        """测试有效身高"""
        assert HeightValidator.is_valid(175)[0] is True
        assert HeightValidator.is_valid("175")[0] is True
        assert HeightValidator.is_valid("175cm")[0] is True

    def test_is_valid_too_short(self):
        """测试身高过矮"""
        assert HeightValidator.is_valid(139)[0] is False

    def test_is_valid_too_tall(self):
        """测试身高过高"""
        assert HeightValidator.is_valid(221)[0] is False


# ============================================================================
# TestInputValidator
# ============================================================================

class TestInputValidator:
    """输入验证器测试"""

    def test_is_understandable_valid(self):
        """测试可理解的输入"""
        assert InputValidator.is_understandable("你好") is True
        assert InputValidator.is_understandable("hello") is True
        assert InputValidator.is_understandable("123") is True

    def test_is_understandable_empty(self):
        """测试空输入"""
        assert InputValidator.is_understandable("") is False
        assert InputValidator.is_understandable(None) is False

    def test_is_understandable_too_long(self):
        """测试过长输入"""
        assert InputValidator.is_understandable("a" * 501) is False

    def test_is_understandable_pure_symbols(self):
        """测试纯符号"""
        assert InputValidator.is_understandable("!!!") is False
        assert InputValidator.is_understandable("...") is False


# ============================================================================
# TestRefusalDetector
# ============================================================================

class TestRefusalDetector:
    """拒绝检测器测试"""

    def test_is_refusing_clear_refusal(self):
        """测试明确拒绝"""
        # 使用实际关键词列表中的词
        assert RefusalDetector.is_refusing("我不想说") is True
        assert RefusalDetector.is_refusing("不方便提供") is True
        assert RefusalDetector.is_refusing("拒绝") is True

    def test_is_refusing_negative_response(self):
        """测试负面回应"""
        assert RefusalDetector.is_refusing("不太感兴趣") is False  # 不在关键词列表中
        assert RefusalDetector.is_refusing("不方便提供") is True

    def test_is_refusing_positive_response(self):
        """测试正面回应（非拒绝）"""
        assert RefusalDetector.is_refusing("好的，请继续") is False

    def test_is_refusing_empty(self):
        """测试空输入"""
        assert RefusalDetector.is_refusing("") is False


# ============================================================================
# TestUserProfile
# ============================================================================

class TestUserProfile:
    """用户资料模型测试"""

    def test_create_profile(self):
        """测试创建用户资料"""
        profile = UserProfile(
            account_id="user_123",
            contact="13800138000",
            sex="男",
            age=28
        )
        assert profile.account_id == "user_123"
        assert profile.contact == "13800138000"
        assert profile.sex == "男"
        assert profile.age == 28

    def test_profile_to_dict(self, sample_user_profile):
        """测试资料转字典"""
        data = sample_user_profile.to_dict()
        assert isinstance(data, dict)
        assert data["account_id"] == "user_123"
        assert data["contact"] == "13800138000"

    def test_profile_from_dict(self):
        """测试从字典创建资料"""
        data = {
            "account_id": "user_456",
            "contact": "13900139000",
            "sex": "女",
            "age": 25
        }
        profile = UserProfile.from_dict(data)
        assert profile.account_id == "user_456"
        assert profile.contact == "13900139000"
        assert profile.sex == "女"

    def test_get_greeting_male(self):
        """测试男性称呼"""
        profile = UserProfile(account_id="test", sex="男")
        assert profile.get_greeting() == "小哥哥"

    def test_get_greeting_female(self):
        """测试女性称呼"""
        profile = UserProfile(account_id="test", sex="女")
        assert profile.get_greeting() == "小姐姐"

    def test_get_greeting_unknown(self):
        """测试未知性别称呼"""
        profile = UserProfile(account_id="test")
        assert profile.get_greeting() == "你"

    def test_get_progress(self):
        """测试收集进度"""
        profile = UserProfile(account_id="test")
        assert profile.get_progress() == 0.0

        profile.collection_progress["sex"] = True
        assert profile.get_progress() > 0

    def test_get_missing_fields(self):
        """测试获取未收集字段"""
        profile = UserProfile(account_id="test")
        missing = profile.get_missing_fields()
        assert "sex" in missing
        assert "contact" in missing
        assert "age_label" not in missing
        assert "height" not in missing
        assert "weight" not in missing
        assert "last_name" not in missing

    def test_get_progress_ignores_age_label_and_low_priority_fields(self):
        """测试公共进度只统计业务关键字段"""
        profile = UserProfile(account_id="test")
        for field in ["sex", "age", "location", "education", "occupation", "marital_status", "contact"]:
            profile.collection_progress[field] = True

        assert profile.get_progress() == 1.0
        assert profile.is_collection_complete() is True

    def test_get_missing_fields_for_serviceable_profile_stays_empty(self):
        """测试达到业务服务阈值后，不再把派生/低优字段显示为缺口"""
        profile = UserProfile(account_id="test")
        profile.collection_progress.update({
            "sex": True,
            "age": True,
            "location": True,
            "education": True,
            "occupation": True,
            "marital_status": True,
            "contact": True,
        })
        profile.sex = "男"
        profile.age = 30
        profile.location = "深圳"
        profile.education = "本科"
        profile.occupation = "IT"
        profile.marital_status = "单身"
        profile.contact = "电话:13800138000"

        assert profile.get_missing_fields() == []
        assert profile.get_progress() == 1.0
        assert profile.is_collection_complete() is True

    def test_update_field(self):
        """测试更新字段"""
        profile = UserProfile(account_id="test")
        result = profile.update_field("sex", "男")
        assert result is True
        assert profile.sex == "男"
        assert profile.collection_progress["sex"] is True


# ============================================================================
# TestStructuredLogging
# ============================================================================

class TestStructuredLogging:
    """结构化日志测试"""

    def test_logger_creation(self):
        """测试创建日志器"""
        from src.core.logging import get_logger
        logger = get_logger("test")
        assert logger is not None
        assert logger.logger.name == "test"  # 实际的 name 在 logger 属性中

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
        # 脱敏格式是 value[:2] + '*' * 4 + value[-2:]
        assert sanitized["phone"] == "13****00"
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
# Test Configuration
# ============================================================================

def test_pytest_config():
    """测试pytest配置"""
    # 确保pytest可以正确发现和运行测试
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
