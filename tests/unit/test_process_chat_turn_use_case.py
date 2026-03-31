from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile


class _EndedUserService:
    def __init__(self):
        self.profile = UserProfile(account_id="u_ended")
        self.profile.conversation_ended = True

    async def get_user_profile(self, account_id):
        return self.profile

    async def save_user_profile(self, account_id, profile):
        self.profile = profile


class _EndedDialogueManager:
    def __init__(self, recent_responses=None):
        self.recent_responses = list(recent_responses or [])

    async def get_message_count(self, account_id):
        return 3

    async def get_conversation_context(self, account_id):
        return {"recent_responses": list(self.recent_responses), "message_count": 3}


class _EndedFallbackService:
    async def reset_nonsense_count(self, account_id):
        return None


class _EndedEndingService:
    def get_ending_response(self, scenario_name):
        assert scenario_name == "already_ended"
        return "行，那先聊到这儿。"


class _EndedChatService:
    def __init__(self, recent_responses=None):
        self.user_service = _EndedUserService()
        self.dialogue_manager = _EndedDialogueManager(recent_responses=recent_responses)
        self.input_fallback_service = _EndedFallbackService()
        self.ending_service = _EndedEndingService()
        self.updated = None

    @staticmethod
    def _sanitize_robotic_tone(response):
        return response

    async def _build_chat_response(
        self,
        account_id,
        user_profile,
        response,
        collection_result,
        dialog_id,
        field_ask_count_before=None,
        response_route=None,
    ):
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id,
            "collected_info": {"contact": "未留"},
            "meta": {"ending": collection_result.get("ending_info", {})},
        }

    async def _update_conversation_state(self, account_id, question, final_response, raw_response, track_asked_fields=False):
        self.updated = (account_id, question, final_response, raw_response, track_asked_fields)


def test_sync_payload_response_keeps_matching_response_unchanged():
    use_case = ProcessChatTurnUseCase(chat_service=object())

    payload = {
        "success": True,
        "response": "完整回复",
        "dialogId": "dlg_sync_same",
        "meta": {},
    }

    synced = use_case._sync_payload_response(payload, "完整回复")

    assert synced["response"] == "完整回复"
    assert "response_synced" not in synced["meta"]


def test_sync_payload_response_overrides_payload_with_final_response():
    use_case = ProcessChatTurnUseCase(chat_service=object())

    payload = {
        "success": True,
        "response": "半句",
        "dialogId": "dlg_sync_fix",
        "meta": {},
    }

    synced = use_case._sync_payload_response(payload, "完整回复")

    assert synced["response"] == "完整回复"
    assert synced["meta"]["response_synced"] is True


def test_execute_returns_already_ended_response_without_reopening_conversation():
    import asyncio

    chat_service = _EndedChatService()
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好",
                accountId="u_ended",
                dialogId="dlg_ended",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] == "行，那先聊到这儿。"
    assert payload["dialogId"] == "dlg_ended"
    assert "collected_info" in payload
    assert payload["meta"]["route"] == "already_ended"
    assert chat_service.updated[-1] is False


def test_execute_uses_short_ack_for_repeated_low_info_confirmation_after_end():
    import asyncio

    chat_service = _EndedChatService(recent_responses=["行，那先聊到这儿。"])
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好的",
                accountId="u_ended",
                dialogId="dlg_ended_repeat",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] in ProcessChatTurnUseCase.ALREADY_ENDED_LOW_INFO_ACKS
    assert payload["meta"]["route"] == "already_ended"


def test_execute_turns_silent_after_repeated_low_info_confirmation_after_end():
    import asyncio

    chat_service = _EndedChatService(recent_responses=["行，那先聊到这儿。", "嗯嗯"])
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好的",
                accountId="u_ended",
                dialogId="dlg_ended_silent",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] == ""
    assert payload["meta"]["route"] == "already_ended"
