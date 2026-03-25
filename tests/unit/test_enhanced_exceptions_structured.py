from src.core.enhanced_exceptions import (
    AIServiceException,
    AuthenticationException,
    ValidationException,
)


def test_enhanced_exception_to_dict_uses_structured_error_key():
    payload = AIServiceException().to_dict()

    assert payload["error"] == "ai_service_unavailable"
    assert payload["error_code"] == "AI_SERVICE_ERROR"


def test_validation_exception_to_dict_uses_structured_error_key():
    payload = ValidationException(field="question").to_dict()

    assert payload["error"] == "validation_error"
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert payload["details"]["field"] == "question"


def test_authentication_exception_to_dict_uses_structured_error_key():
    payload = AuthenticationException().to_dict()

    assert payload["error"] == "authentication_failed"
    assert payload["error_code"] == "AUTH_ERROR"
