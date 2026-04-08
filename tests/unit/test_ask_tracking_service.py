from unittest.mock import AsyncMock

import pytest

from src.models.user_profile import UserProfile
from src.modules.profile_collection.domain.ask_tracking_service import AskTrackingService


@pytest.mark.anyio
async def test_track_ai_asked_fields_treats_work_life_question_as_location():
    user_service = AsyncMock()
    profile = UserProfile(account_id="user_1")
    user_service.get_user_profile = AsyncMock(return_value=profile)
    user_service.save_user_profile = AsyncMock(return_value=True)
    service = AskTrackingService(user_service)

    await service.track_ai_asked_fields("user_1", "好哒，90后的情况我记下来啦～那你现在是在深圳工作生活嘛？")

    assert profile.get_ask_count("location") == 1
    assert profile.get_effective_ask_count("location") == 1
    assert profile.get_ask_count("occupation") == 0


@pytest.mark.anyio
async def test_track_ai_asked_fields_treats_job_question_as_occupation():
    user_service = AsyncMock()
    profile = UserProfile(account_id="user_2")
    user_service.get_user_profile = AsyncMock(return_value=profile)
    user_service.save_user_profile = AsyncMock(return_value=True)
    service = AskTrackingService(user_service)

    await service.track_ai_asked_fields("user_2", "好哒，本科学历我记下来啦~对了想问下你平时是做哪方面工作的呀？")

    assert profile.get_ask_count("occupation") == 1
    assert profile.get_effective_ask_count("occupation") == 1
    assert profile.get_ask_count("location") == 0


@pytest.mark.anyio
async def test_track_ai_asked_fields_respects_cooldown_and_skip_guard(monkeypatch):
    user_service = AsyncMock()
    profile = UserProfile(account_id="user_3")
    profile.recent_asked_fields = ["age"]
    profile.field_ask_count = {"age": 1}
    user_service.get_user_profile = AsyncMock(return_value=profile)
    user_service.save_user_profile = AsyncMock(return_value=True)
    service = AskTrackingService(user_service)

    monkeypatch.setenv("MQ_FIELD_ASK_COOLDOWN_TURNS", "2")
    monkeypatch.setenv("MQ_SKIP_GUARD_ENABLED", "true")

    await service.track_ai_asked_fields("user_3", "你今年多大呀？")

    # 同字段在冷却窗口，不应继续累加
    assert profile.get_ask_count("age") == 1
    # 但用户真实看到了这一轮，仍应计入有效询问
    assert profile.get_effective_ask_count("age") == 1
    # 开启防抖，不应自动标记跳过
    assert profile.skipped_fields.get("age", False) is False


@pytest.mark.anyio
async def test_track_ai_asked_fields_does_not_close_partner_requirement_on_ask():
    user_service = AsyncMock()
    profile = UserProfile(account_id="user_partner_req")
    user_service.get_user_profile = AsyncMock(return_value=profile)
    user_service.save_user_profile = AsyncMock(return_value=True)
    service = AskTrackingService(user_service)

    await service.track_ai_asked_fields("user_partner_req", "你对另一半有什么大致的要求不？")

    assert profile.get_ask_count("partner_requirement") == 1
    assert profile.is_active_ask_closed("partner_requirement") is False
