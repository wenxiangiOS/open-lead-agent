from src.models.user_profile import UserProfile
from src.services.core.chat_service_message_signal_service import (
    ChatServiceMessageSignalService,
)


class _Host:
    def __init__(self, intent: str | None):
        self.intent = intent

    def _classify_withdraw_intent(self, user_message: str):
        return self.intent


def test_chat_service_message_signal_service_uses_host_for_withdraw_detection():
    service = ChatServiceMessageSignalService(_Host("soft"))

    assert service.is_withdraw_or_stop_message("先不聊了") is True


def test_chat_service_message_signal_service_detects_resume_profile_collection_message():
    assert ChatServiceMessageSignalService.is_resume_profile_collection_message("继续聊资料") is True
    assert ChatServiceMessageSignalService.is_resume_profile_collection_message("你好呀") is False


def test_chat_service_message_signal_service_detects_acknowledgement_only_message():
    assert ChatServiceMessageSignalService.is_acknowledgement_only_message("好的") is True
    assert ChatServiceMessageSignalService.is_acknowledgement_only_message("我知道了，继续吧") is False


def test_chat_service_message_signal_service_detects_short_answer():
    assert ChatServiceMessageSignalService.is_short_answer("男的") is True
    assert ChatServiceMessageSignalService.is_short_answer("深圳") is True
    assert ChatServiceMessageSignalService.is_short_answer("我在深圳南山这边上班") is False


def test_chat_service_message_signal_service_detects_valid_contact():
    profile = UserProfile(account_id="u_contact_signal")
    assert ChatServiceMessageSignalService.has_any_valid_contact(profile) is False
    profile.wechat = "abc123"
    profile.wechat_collected = True
    assert ChatServiceMessageSignalService.has_any_valid_contact(profile) is True
