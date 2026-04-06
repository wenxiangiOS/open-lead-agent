from types import SimpleNamespace

import pytest

from src.models.user_profile import UserProfile
from src.services.core.first_generation_delivery_service import FirstGenerationDeliveryService
from src.services.core.chat_service_finalize_service import ChatServiceFinalizeService


class _RecordingHost:
    def __init__(self):
        self.calls: list[str] = []
        self.unified_response_draft_service = SimpleNamespace(build=lambda **kwargs: None)
        self.unified_response_validation_service = SimpleNamespace(validate=lambda **kwargs: None)
        self.unified_response_safe_cleanup_service = SimpleNamespace(cleanup=lambda *args, **kwargs: ("", False))
        self.unified_response_delivery_service = SimpleNamespace(deliver=lambda **kwargs: None)
        self.unified_response_observability_service = SimpleNamespace(
            build_record=lambda **kwargs: {},
            log=lambda **kwargs: None,
        )
        self.first_generation_delivery_service = FirstGenerationDeliveryService()
        self._last_unified_generation_record = None
        self._detect_asked_fields_in_response = lambda text: set()
        self._sanitize_forbidden_sales_phrases = lambda text: text
        self._sanitize_robotic_tone = lambda text: text
        self.contact_service = SimpleNamespace(
            get_next_action=lambda profile, user_message="": SimpleNamespace(value="none")
        )

    async def _call_ai(self, prompt, account_id, user_message):
        return ""


def _build_turn_decision():
    return SimpleNamespace(
        ask_field="occupation",
        response_channel="model",
        primary_move="ack_and_ask",
        followup_topic=None,
        allow_medium_target=True,
    )


@pytest.mark.anyio
async def test_chat_service_finalize_service_orchestrates_happy_path_in_order():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)
    steps: list[str] = []

    class _DraftService:
        def build(self, **kwargs):
            steps.append("draft")
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            steps.append("validate")
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            steps.append("deliver")
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    class _ObsService:
        def build_record(self, **kwargs):
            steps.append("build_record")
            return {"final_display_response": kwargs["delivery"].display_response}

        def log(self, **kwargs):
            steps.append("log")

    async def _record_delivered(*args, **kwargs):
        steps.append("record_delivered")
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host.unified_response_observability_service = _ObsService()
    host._record_delivered_contact_ask_if_needed = _record_delivered

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_happy",
        user_profile=UserProfile(account_id="u_finalize_happy"),
        user_message="你好",
        turn_decision=_build_turn_decision(),
        turn_understanding=SimpleNamespace(),
        collection_result={"all_fields": []},
        response_to_clean="seed",
        ai_response="seed",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert steps == ["draft", "validate", "deliver", "record_delivered", "build_record", "log"]
    assert delivery_ok is True
    assert profile.account_id == "u_finalize_happy"
    assert response == "seed"


@pytest.mark.anyio
async def test_chat_service_finalize_service_silences_failed_first_generation_without_fallback():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)
    steps: list[str] = []

    class _DraftService:
        def build(self, **kwargs):
            steps.append("draft")
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            steps.append("validate")
            return SimpleNamespace(
                delivery_status="fallback_required",
                violations=[],
                warnings=[],
                should_fallback=True,
                fallback_reason="forced_for_test",
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            steps.append("deliver")
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason="forced_for_test",
            )

    class _ObsService:
        def build_record(self, **kwargs):
            steps.append("build_record")
            return {"final_display_response": kwargs["delivery"].display_response}

        def log(self, **kwargs):
            steps.append("log")

    async def _record_delivered(*args, **kwargs):
        steps.append("record_delivered")
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host.unified_response_observability_service = _ObsService()
    host._record_delivered_contact_ask_if_needed = _record_delivered

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_fallback",
        user_profile=UserProfile(account_id="u_finalize_fallback"),
        user_message="你好",
        turn_decision=_build_turn_decision(),
        turn_understanding=SimpleNamespace(),
        collection_result={"all_fields": []},
        response_to_clean="seed",
        ai_response="",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert steps == ["draft", "validate", "deliver", "build_record", "log"]
    assert delivery_ok is False
    assert profile.account_id == "u_finalize_fallback"
    assert response == ""


@pytest.mark.anyio
async def test_chat_service_finalize_service_keeps_first_generation_text_without_post_rewrite():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)
    steps: list[str] = []

    class _DraftService:
        def build(self, **kwargs):
            steps.append("draft")
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            steps.append("validate")
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            steps.append("deliver")
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    class _ObsService:
        def build_record(self, **kwargs):
            steps.append("build_record")
            return {"final_display_response": kwargs["delivery"].display_response}

        def log(self, **kwargs):
            steps.append("log")

    async def _record_delivered(*args, **kwargs):
        steps.append("record_delivered")
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host.unified_response_observability_service = _ObsService()
    host._record_delivered_contact_ask_if_needed = _record_delivered

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_guards",
        user_profile=UserProfile(account_id="u_finalize_guards"),
        user_message="你好",
        turn_decision=_build_turn_decision(),
        turn_understanding=SimpleNamespace(),
        collection_result={"all_fields": []},
        response_to_clean="seed",
        ai_response="seed",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=1,
    )

    assert steps == ["draft", "validate", "deliver", "record_delivered", "build_record", "log"]
    assert delivery_ok is True
    assert profile.account_id == "u_finalize_guards"
    assert response == "seed"


@pytest.mark.anyio
async def test_chat_service_finalize_service_strips_technical_blocks_and_keeps_first_generation_only():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)

    class _DraftService:
        def build(self, **kwargs):
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    async def _record_delivered(*args, **kwargs):
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host._record_delivered_contact_ask_if_needed = _record_delivered

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_soft_refusal",
        user_profile=UserProfile(account_id="u_finalize_soft_refusal"),
        user_message="不方便说",
        turn_decision=SimpleNamespace(ask_field="education"),
        turn_understanding=SimpleNamespace(subtype="soft_refusal_current_field"),
        collection_result={"all_fields": []},
        response_to_clean="",
        ai_response=(
            '<opening_intent>{"intent":"opening_profile_provided"}</opening_intent>\n'
            "好哦，那我再大概了解下你的学历呀？\n"
            "<extract>\n学历:null\n</extract>"
        ),
        bridge_prefix="",
        contact_gate_before=False,
        message_count=5,
    )

    assert delivery_ok is True
    assert profile.account_id == "u_finalize_soft_refusal"
    assert response == "好哦，那我再大概了解下你的学历呀？"
    assert host._last_unified_generation_record["technical_blocks_removed"] == ["opening_intent", "extract"]


@pytest.mark.anyio
async def test_chat_service_finalize_service_never_calls_ai_regen_for_core_followup():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)

    class _DraftService:
        def build(self, **kwargs):
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    async def _record_delivered(*args, **kwargs):
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    async def _regen(prompt, account_id, user_message):
        raise AssertionError("finalize stage must not call AI again")

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host._record_delivered_contact_ask_if_needed = _record_delivered
    host._call_ai = _regen

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_soft_refusal_retry_twice",
        user_profile=UserProfile(account_id="u_finalize_soft_refusal_retry_twice"),
        user_message="不方便说",
        turn_decision=SimpleNamespace(ask_field="education"),
        turn_understanding=SimpleNamespace(subtype="soft_refusal_current_field"),
        collection_result={"all_fields": []},
        response_to_clean="",
        ai_response="没事的，这块你要是不方便说也没关系，咱们慢慢聊就好。",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=5,
    )

    assert delivery_ok is True
    assert profile.account_id == "u_finalize_soft_refusal_retry_twice"
    assert response == "没事的，这块你要是不方便说也没关系，咱们慢慢聊就好。"


@pytest.mark.anyio
async def test_chat_service_finalize_service_never_calls_ai_regen_for_contact_followup():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)

    class _DraftService:
        def build(self, **kwargs):
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    async def _record_delivered(*args, **kwargs):
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    async def _regen(prompt, account_id, user_message):
        raise AssertionError("contact followup must not trigger finalize regeneration")

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host._record_delivered_contact_ask_if_needed = _record_delivered
    host._call_ai = _regen

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_contact_regen",
        user_profile=UserProfile(account_id="u_finalize_contact_regen"),
        user_message="不方便",
        turn_decision=SimpleNamespace(ask_field="contact"),
        turn_understanding=SimpleNamespace(subtype="contact_context_reply"),
        collection_result={"all_fields": []},
        response_to_clean="",
        ai_response="没关系呀，那你方便留个微信吗，后续有合适的方向能更顺畅对接上。",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=8,
    )

    assert delivery_ok is True
    assert profile.account_id == "u_finalize_contact_regen"
    assert response == "没关系呀，那你方便留个微信吗，后续有合适的方向能更顺畅对接上。"


@pytest.mark.anyio
async def test_chat_service_finalize_service_keeps_first_generation_wechat_followup_without_regen():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)

    class _DraftService:
        def build(self, **kwargs):
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    async def _record_delivered(*args, **kwargs):
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    async def _regen(prompt, account_id, user_message):
        raise AssertionError("valid first generation should be delivered directly")

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host._record_delivered_contact_ask_if_needed = _record_delivered
    host._call_ai = _regen

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_contact_material_cleanup",
        user_profile=UserProfile(account_id="u_finalize_contact_material_cleanup"),
        user_message="不方便呢",
        turn_decision=SimpleNamespace(ask_field="contact"),
        turn_understanding=SimpleNamespace(subtype="contact_context_reply"),
        collection_result={"all_fields": []},
        response_to_clean="",
        ai_response="我懂，那你方便说下电话不？",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=9,
    )

    assert delivery_ok is True
    assert profile.account_id == "u_finalize_contact_material_cleanup"
    assert response == "我懂，那你方便说下电话不？"


@pytest.mark.anyio
async def test_chat_service_finalize_service_keeps_valid_wechat_followup_that_only_acknowledges_phone_refusal():
    host = _RecordingHost()
    service = ChatServiceFinalizeService(host)

    class _DraftService:
        def build(self, **kwargs):
            return SimpleNamespace(raw_ai_response=kwargs["raw_ai_response"])

    class _ValidationService:
        def validate(self, **kwargs):
            return SimpleNamespace(
                delivery_status="deliverable",
                violations=[],
                warnings=[],
                should_fallback=False,
                fallback_reason=None,
            )

    class _DeliveryService:
        def deliver(self, **kwargs):
            return SimpleNamespace(
                display_response=kwargs["cleaned_response"],
                raw_ai_response=kwargs["draft"].raw_ai_response,
                safe_cleaned=True,
                fallback_used=False,
                fallback_reason=None,
            )

    async def _record_delivered(*args, **kwargs):
        return kwargs["user_profile"] if "user_profile" in kwargs else args[1]

    async def _regen(prompt, account_id, user_message):
        raise AssertionError("valid ask_wechat response should not trigger contact regeneration")

    host.unified_response_draft_service = _DraftService()
    host.unified_response_validation_service = _ValidationService()
    host.unified_response_delivery_service = _DeliveryService()
    host._record_delivered_contact_ask_if_needed = _record_delivered
    host._call_ai = _regen

    response, delivery_ok, profile = await service.finalize_generated_response(
        account_id="u_finalize_contact_no_false_regen",
        user_profile=UserProfile(account_id="u_finalize_contact_no_false_regen"),
        user_message="不方便呢",
        turn_decision=SimpleNamespace(ask_field="contact"),
        turn_understanding=SimpleNamespace(subtype="contact_context_reply"),
        collection_result={"all_fields": []},
        response_to_clean="",
        ai_response="没事呀，不愿留电话没关系，你方便说下微信不，后续联系起来也更顺畅。",
        bridge_prefix="",
        contact_gate_before=False,
        message_count=9,
    )

    assert delivery_ok is True
    assert profile.account_id == "u_finalize_contact_no_false_regen"
    assert response == "没事呀，不愿留电话没关系，你方便说下微信不，后续联系起来也更顺畅。"
