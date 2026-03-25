import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from src.api.middleware.validation import (
    RequestValidator,
    validate_request,
    validate_pydantic,
)


@pytest.mark.anyio
async def test_validate_request_returns_structured_validation_error():
    @validate_request(RequestValidator().add_required("question"))
    async def handler(request):
        return request

    with pytest.raises(HTTPException) as exc_info:
        await handler({})

    detail = exc_info.value.detail
    assert detail["error"] == "request_validation_failed"
    assert detail["error_code"] == "VALIDATION_ERROR"
    assert detail["details"]["source"] == "request_validator"
    assert detail["details"]["errors"]


@pytest.mark.anyio
async def test_validate_pydantic_returns_structured_validation_error():
    class Payload(BaseModel):
        question: str

    @validate_pydantic(Payload)
    async def handler(request):
        return request

    with pytest.raises(HTTPException) as exc_info:
        await handler({})

    detail = exc_info.value.detail
    assert detail["error"] == "request_validation_failed"
    assert detail["error_code"] == "VALIDATION_ERROR"
    assert detail["details"]["source"] == "pydantic"
    assert detail["details"]["errors"]
