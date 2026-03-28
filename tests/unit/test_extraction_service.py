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


def test_parse_age_handles_birth_year_with_suffix():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("1998年") == 28


def test_extract_partner_requirement_from_user_message_preserves_negation():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "不超过30岁，身高至少160，温柔的"
    )

    assert extracted == "年龄不超过30岁，身高至少160，温柔"


def test_extract_partner_requirement_from_user_message_captures_qizhi_preference():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "本科，看中对方气质吧"
    )

    assert extracted == "气质"


def test_extract_partner_requirement_from_user_message_keeps_height_and_looks_preferences():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "温柔，不要低于160，漂亮点的，其他没有了"
    )

    assert extracted == "温柔，身高不低于160，漂亮点"


@pytest.mark.anyio
async def test_process_extracted_data_allows_trailing_punct_sex_self_intro():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_trailing_punct_sex")

    await service.process_extracted_data(
        "user_trailing_punct_sex",
        profile,
        {"sex": "男"},
        user_message="男的，",
    )

    refreshed = await user_service.get_user_profile("user_trailing_punct_sex")
    assert refreshed.sex == "男"


@pytest.mark.anyio
async def test_process_extracted_data_allows_affirmative_sex_confirmation_with_last_response():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_affirmative_confirm_sex")

    await service.process_extracted_data(
        "user_affirmative_confirm_sex",
        profile,
        {"sex": "男"},
        user_message="是的",
        last_response="我再确认下，你这边是男生对吧？",
    )

    refreshed = await user_service.get_user_profile("user_affirmative_confirm_sex")
    assert refreshed.sex == "男"


@pytest.mark.anyio
async def test_process_extracted_data_allows_affirmative_sex_confirmation_with_pending_state():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_affirmative_pending_sex")
    profile.pending_sex_confirmation = "男"
    await user_service.save_user_profile("user_affirmative_pending_sex", profile)

    await service.process_extracted_data(
        "user_affirmative_pending_sex",
        profile,
        {"sex": "男"},
        user_message="是的",
    )

    refreshed = await user_service.get_user_profile("user_affirmative_pending_sex")
    assert refreshed.sex == "男"
    assert refreshed.pending_sex_confirmation is None


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


@pytest.mark.anyio
async def test_process_extracted_data_does_not_pollute_occupation_with_partner_requirement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_preference")

    await service.process_extracted_data(
        "user_preference",
        profile,
        {
            "education": "本科",
            "occupation": "看对方气质吧",
            "partner_requirement": "看重对方气质",
        },
        user_message="本科，看中对方气质吧",
    )

    refreshed = await user_service.get_user_profile("user_preference")
    assert refreshed.education == "本科"
    assert refreshed.partner_requirement == "气质"
    assert refreshed.occupation is None


@pytest.mark.anyio
async def test_process_extracted_data_merges_partner_requirement_without_overwriting_longer_model_value():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_partner_merge")

    await service.process_extracted_data(
        "user_partner_merge",
        profile,
        {"partner_requirement": "温柔，身高不低于160，长相漂亮，无其他要求"},
        user_message="温柔，不要低于160，漂亮点的，其他没有了",
    )

    refreshed = await user_service.get_user_profile("user_partner_merge")
    assert refreshed.partner_requirement == "温柔，身高不低于160，长相漂亮，无其他要求，漂亮点"
