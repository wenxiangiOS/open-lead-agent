from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.api.middleware.security import JWTMiddleware


class _DummyRequest:
    def __init__(self, path="/private", headers=None):
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}
        self.state = SimpleNamespace()


@pytest.mark.anyio
async def test_jwt_middleware_returns_structured_auth_required_error():
    middleware = JWTMiddleware()
    request = _DummyRequest(headers={})

    with patch("src.api.middleware.security.settings.security.jwt_enabled", True):
        with patch("src.api.middleware.security.settings.security.jwt_secret_key", "Abcd1234!Abcd1234!Abcd1234!Abcd12"):
            response = await middleware.dispatch(request, lambda _request: None)

    assert response.status_code == 401
    assert response.body
    body = response.body.decode("utf-8")
    assert '"error":"auth_required"' in body
    assert '"error_code":"AUTH_REQUIRED"' in body


@pytest.mark.anyio
async def test_jwt_middleware_returns_structured_invalid_token_error():
    middleware = JWTMiddleware()
    request = _DummyRequest(headers={"Authorization": "Bearer bad-token"})

    with patch("src.api.middleware.security.settings.security.jwt_enabled", True):
        with patch("src.api.middleware.security.settings.security.jwt_secret_key", "Abcd1234!Abcd1234!Abcd1234!Abcd12"):
            with patch.object(JWTMiddleware, "_verify_token", side_effect=ValueError("bad token")):
                response = await middleware.dispatch(request, lambda _request: None)

    assert response.status_code == 401
    body = response.body.decode("utf-8")
    assert '"error":"invalid_token"' in body
    assert '"error_code":"INVALID_TOKEN"' in body
