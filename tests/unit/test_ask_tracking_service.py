from unittest.mock import AsyncMock

import pytest

from src.models.user_profile import UserProfile
from src.services.collection.ask_tracking_service import AskTrackingService


@pytest.mark.anyio
async def test_track_ai_asked_fields_treats_work_life_question_as_location():
    user_service = AsyncMock()
    profile = UserProfile(account_id="user_1")
    user_service.get_user_profile = AsyncMock(return_value=profile)
    user_service.save_user_profile = AsyncMock(return_value=True)
    service = AskTrackingService(user_service)

    await service.track_ai_asked_fields("user_1", "好哒，90后的情况我记下来啦～那你现在是在深圳工作生活嘛？")

    assert profile.get_ask_count("location") == 1
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
    assert profile.get_ask_count("location") == 0
