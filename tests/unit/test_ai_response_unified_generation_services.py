from src.modules.ai_response_unified_generation.domain import (
    ResponseDeliveryService,
    ResponseDraftService,
    ResponseObservabilityService,
    ResponseSafeCleanupService,
    ResponseValidationService,
)


def test_response_validation_service_marks_empty_as_fallback_required():
    service = ResponseValidationService()

    result = service.validate(raw_ai_response="")

    assert result.delivery_status == "fallback_required"
    assert result.should_fallback is True
    assert result.fallback_reason == "ai_empty_response"


def test_response_validation_service_marks_debug_payload_as_hard_block():
    service = ResponseValidationService()

    result = service.validate(raw_ai_response="Traceback (most recent call last): ...")

    assert result.delivery_status == "hard_block"
    assert result.should_fallback is True
    assert result.fallback_reason == "invalid_ai_payload"


def test_response_safe_cleanup_service_keeps_semantic_tail():
    service = ResponseSafeCleanupService()

    cleaned, changed = service.cleanup("  你是在深圳对吧？如果合适的话也可以顺带说下职业。  ")

    assert cleaned == "你是在深圳对吧？如果合适的话也可以顺带说下职业。"
    assert changed is True


def test_response_safe_cleanup_service_keeps_short_colloquial_reply():
    service = ResponseSafeCleanupService()

    cleaned, changed = service.cleanup("做it呢")

    assert cleaned == "做it呢"
    assert changed is False


def test_response_safe_cleanup_service_keeps_status_confirmation_chain():
    service = ResponseSafeCleanupService()

    cleaned, changed = service.cleanup("98年呢？我离异过呢，手续办理好呢。")

    assert cleaned == "98年呢？我离异过呢，手续办理好呢。"
    assert changed is False


def test_response_safe_cleanup_service_keeps_colloquial_income_expression():
    service = ResponseSafeCleanupService()

    cleaned, changed = service.cleanup("我自己收入不高一年18左右。")

    assert cleaned == "我自己收入不高一年18左右。"
    assert changed is False


def test_response_delivery_service_uses_fallback_only_when_required():
    draft = ResponseDraftService().build(raw_ai_response="AI原文")
    validation = ResponseValidationService().validate(raw_ai_response="")
    delivery = ResponseDeliveryService().deliver(
        draft=draft,
        validation_result=validation,
        cleaned_response="AI原文",
        safe_cleaned=False,
        fallback_response="兜底文案",
    )

    assert delivery.display_response == "兜底文案"
    assert delivery.fallback_used is True


def test_response_observability_service_populates_diff_reason_for_safe_cleanup():
    draft = ResponseDraftService().build(raw_ai_response="原文  ")
    validation = ResponseValidationService().validate(raw_ai_response="原文  ")
    delivery = ResponseDeliveryService().deliver(
        draft=draft,
        validation_result=validation,
        cleaned_response="原文",
        safe_cleaned=True,
        fallback_response="",
    )

    record = ResponseObservabilityService().build_record(
        draft=draft,
        validation_result=validation,
        cleaned_response="原文",
        delivery=delivery,
    )

    assert record["raw_display_diff"] is True
    assert record["raw_display_diff_reason"] == "safe_cleanup"
    assert record["display_frozen_at"]
