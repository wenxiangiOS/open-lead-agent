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
    async def get_message_count(self, account_id):
        return 3


class _EndedFallbackService:
    async def reset_nonsense_count(self, account_id):
        return None


class _EndedEndingService:
    def get_ending_response(self, scenario_name):
        assert scenario_name == "already_ended"
        return "行，那先聊到这儿。"


class _EndedChatService:
    def __init__(self):
        self.user_service = _EndedUserService()
        self.dialogue_manager = _EndedDialogueManager()
        self.input_fallback_service = _EndedFallbackService()
        self.ending_service = _EndedEndingService()
        self.updated = None

    @staticmethod
    def _sanitize_robotic_tone(response):
        return response

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

    assert payload["response"] == "行，那先聊到这儿。"
    assert payload["meta"]["route"] == "already_ended"
    assert chat_service.updated[-1] is False
