import pytest

from src.models.user_profile import UserProfile
from src.services.data.extraction_service import ExtractionService


class _FakeUserService:
    def __init__(self):
        self.profiles = {}

    async def get_user_profile(self, account_id):
        return self.profiles.setdefault(account_id, UserProfile(account_id=account_id))

    async def save_user_profile(self, account_id, profile):
        self.profiles[account_id] = profile
        return True

    async def update_user_profile_field(self, account_id, field_name, value):
        profile = await self.get_user_profile(account_id)
        success = profile.update_field(field_name, value)
        if success:
            self.profiles[account_id] = profile
        return success


def test_normalize_extracted_value_filters_placeholder_values():
    assert ExtractionService._normalize_extracted_value("值") is None
    assert ExtractionService._normalize_extracted_value("值/null") is None
    assert ExtractionService._normalize_extracted_value("null（电话号码）") is None
    assert ExtractionService._normalize_extracted_value("程序员") == "程序员"


def test_normalize_extracted_value_filters_valuenull_variant():
    """测试 '值null' 占位符变体（无斜杠）被正确过滤"""
    # AI 可能误抄模板内容，返回 "值null" 而不是 "值/null"
    assert ExtractionService._normalize_extracted_value("值null") is None
    assert ExtractionService._normalize_extracted_value("值Null") is None
    assert ExtractionService._normalize_extracted_value("值NULL") is None
    # 其他"值"开头的短占位符也应该被过滤
    assert ExtractionService._normalize_extracted_value("值xxx") is None
    assert ExtractionService._normalize_extracted_value("值示例") is None
    # 正常的职业名称应该保留
    assert ExtractionService._normalize_extracted_value("工程师") == "工程师"
    assert ExtractionService._normalize_extracted_value("教师") == "教师"


def test_extract_age_label_keeps_post_90s_bucket():
    assert ExtractionService._extract_age_label("90后") == "90后"
    assert ExtractionService._extract_age_label("我是95后") == "95后"
    assert ExtractionService._extract_age_label("28岁") is None


def test_parse_age_handles_post_2000_bucket():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("00后") == 26


def test_parse_age_handles_post_90s_bucket():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("90后") == 36


@pytest.mark.anyio
async def test_process_extracted_data_clears_stale_age_label_when_user_provides_exact_age():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_age")
    profile.age = 36
    profile.age_label = "90后"
    profile.collection_progress["age"] = True
    profile.collection_progress["age_label"] = True
    await user_service.save_user_profile("user_age", profile)

    await service.process_extracted_data("user_age", profile, {"age": "28岁"}, user_message="我28岁")

    refreshed = await user_service.get_user_profile("user_age")
    assert refreshed.age == 28
    assert refreshed.age_label is None
