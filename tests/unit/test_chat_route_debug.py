import asyncio

from src.api.routes import chat as chat_routes
from src.config.settings import settings


class _StubChatService:
    def __init__(self):
        self.profile_calls = 0

    async def process_chat_request(self, _chat_request):
        return {
            "success": True,
            "response": "ok",
            "dialogId": "d1",
        }

    async def get_user_profile(self, _account_id):
        self.profile_calls += 1
        return {
            "profile": {
                "field_ask_count": {},
                "skipped_fields": {},
            }
        }


def test_chat_debug_payload_ignored_when_not_in_debug_mode():
    asyncio.run(_test_chat_debug_payload_ignored_when_not_in_debug_mode())


async def _test_chat_debug_payload_ignored_when_not_in_debug_mode():
    stub = _StubChatService()
    original_service = chat_routes.chat_service
    original_debug = settings.app.debug
    try:
        chat_routes.chat_service = stub
        settings.app.debug = False
        resp = await chat_routes.chat({
            "question": "你好",
            "accountId": "u_debug_1",
            "sex": "女",
            "debug": True,
        })
        assert resp.success is True
        assert resp.debug_info is None
        assert stub.profile_calls == 0
    finally:
        chat_routes.chat_service = original_service
        settings.app.debug = original_debug


def test_chat_debug_payload_enabled_in_debug_mode():
    asyncio.run(_test_chat_debug_payload_enabled_in_debug_mode())


async def _test_chat_debug_payload_enabled_in_debug_mode():
    stub = _StubChatService()
    original_service = chat_routes.chat_service
    original_debug = settings.app.debug
    try:
        chat_routes.chat_service = stub
        settings.app.debug = True
        resp = await chat_routes.chat({
            "question": "你好",
            "accountId": "u_debug_2",
            "sex": "女",
            "debug": True,
        })
        assert resp.success is True
        assert resp.debug_info is not None
        assert stub.profile_calls >= 2
    finally:
        chat_routes.chat_service = original_service
        settings.app.debug = original_debug
