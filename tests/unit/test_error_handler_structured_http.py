from fastapi import HTTPException

from src.core.error_handler import ErrorHandler


def test_http_exception_with_structured_detail_preserves_error_code_and_details():
    response = ErrorHandler.handle(
        HTTPException(
            status_code=500,
            detail={
                "error": "chat_processing_failed",
                "error_code": "CHAT_PROCESSING_ERROR",
                "details": {"route": "chat"},
            },
        )
    )

    assert response["success"] is False
    assert response["error"] == "chat_processing_failed"
    assert response["error_code"] == "CHAT_PROCESSING_ERROR"
    assert response["details"] == {"route": "chat"}


def test_error_handler_uses_structured_internal_error_key_for_generic_exception():
    response = ErrorHandler.handle(ValueError("bad value"))

    assert response["success"] is False
    assert response["error"] == "value_error"
    assert response["error_code"] == "INTERNAL_ERROR"
    assert response["details"]["type"] == "ValueError"
