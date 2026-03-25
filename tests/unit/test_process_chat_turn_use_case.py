from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase


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
