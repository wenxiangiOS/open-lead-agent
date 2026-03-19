import asyncio

from src.api.routes import chat as chat_routes
from src.config.settings import settings
from src.modules.conversation.domain.conversation_rule_service import ConversationRuleService
from src.modules.shared.models.chat_flow import RuleCheckResult
from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase
from src.modules.shared.models.use_case_models import ProcessChatTurnCommand, ProcessChatTurnResult


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


class _StubChatServiceWithProtocol(_StubChatService):
    def __init__(self):
        super().__init__()
        self.commands = []
        self.process_chat_turn_use_case = self

    async def execute_command(self, command):
        self.commands.append(command)
        return ProcessChatTurnResult(
            success=True,
            response="ok_from_protocol",
            dialog_id="d_protocol",
            payload={
                "success": True,
                "response": "ok_from_protocol",
                "dialogId": "d_protocol",
            },
        )


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


def test_chat_route_prefers_process_chat_turn_command_protocol():
    asyncio.run(_test_chat_route_prefers_process_chat_turn_command_protocol())


async def _test_chat_route_prefers_process_chat_turn_command_protocol():
    stub = _StubChatServiceWithProtocol()
    original_service = chat_routes.chat_service
    try:
        chat_routes.chat_service = stub
        resp = await chat_routes.chat({
            "question": "你好",
            "accountId": "u_protocol_1",
            "dialogId": "d_protocol",
            "sex": "女",
        })
        assert resp.success is True
        assert resp.response == "ok_from_protocol"
        assert len(stub.commands) == 1
        assert isinstance(stub.commands[0], ProcessChatTurnCommand)
        assert stub.commands[0].account_id == "u_protocol_1"
    finally:
        chat_routes.chat_service = original_service


def test_process_chat_turn_use_case_execute_command_wraps_payload():
    asyncio.run(_test_process_chat_turn_use_case_execute_command_wraps_payload())


async def _test_process_chat_turn_use_case_execute_command_wraps_payload():
    use_case = ProcessChatTurnUseCase(chat_service=object())

    async def fake_execute(_request):
        return {
            "success": True,
            "response": "ok",
            "dialogId": "d_cmd_chat",
        }

    use_case.execute = fake_execute  # type: ignore[method-assign]

    result = await use_case.execute_command(
        ProcessChatTurnCommand(
            question="你好",
            account_id="u_cmd_chat",
            dialog_id="d_cmd_chat",
            sex="女",
        )
    )

    assert result.success is True
    assert result.response == "ok"
    assert result.dialog_id == "d_cmd_chat"


def test_conversation_rule_service_uses_first_matching_rule():
    asyncio.run(_test_conversation_rule_service_uses_first_matching_rule())


async def _test_conversation_rule_service_uses_first_matching_rule():
    service = ConversationRuleService(chat_service=object())
    call_order = []

    class _RuleA:
        async def apply(self, _ctx):
            call_order.append("A")
            return RuleCheckResult(handled=False)

    class _RuleB:
        async def apply(self, _ctx):
            call_order.append("B")
            return RuleCheckResult(handled=True, response_payload={"success": True, "response": "b"})

    class _RuleC:
        async def apply(self, _ctx):
            call_order.append("C")
            return RuleCheckResult(handled=True, response_payload={"success": True, "response": "c"})

    service.rules = [_RuleA(), _RuleB(), _RuleC()]

    class _Req:
        accountId = "u"
        question = "你好"
        dialogId = "d"

    class _Profile:
        conversation_ended = False

    result = await service.try_handle(_Req(), _Profile(), is_first_user_turn=True, message_count=0)
    assert result.handled is True
    assert result.response_payload["response"] == "b"
    assert call_order == ["A", "B"]
