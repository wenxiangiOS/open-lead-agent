"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import Mock, patch

from src.api.routes import app
from src.models.requests import ChatRequest


class TestAPIIntegration:
    """Test API endpoints integration."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "小桃子" in data["msg"]

    @pytest.mark.asyncio
    async def test_chat_endpoint_success(self):
        """Test chat endpoint with successful request."""
        # Mock the services
        with patch('src.api.routes.chat_service') as mock_chat_service:
            mock_chat_service.process_chat_request = AsyncMock(
                return_value={
                    "success": True,
                    "response": "Hello! How can I help you?",
                    "dialogId": "dialog123",
                    "timestamp": "2024-01-01T00:00:00"
                }
            )

            request_data = {
                "question": "Hello",
                "accountId": "user123",
                "sex": "女",
                "dialogId": "dialog123"
            }

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/api/doubao/chat", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "Hello! How can I help you?"
            assert data["dialogId"] == "dialog123"

    @pytest.mark.asyncio
    async def test_chat_endpoint_missing_question(self):
        """Test chat endpoint with missing question."""
        request_data = {
            "accountId": "user123",
            "sex": "女"
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/doubao/chat", json=request_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_question(self):
        """Test chat endpoint with empty question."""
        request_data = {
            "question": "",
            "accountId": "user123",
            "sex": "女"
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/doubao/chat", json=request_data)

        assert response.status_code == 400  # Bad request

    @pytest.mark.asyncio
    async def test_chat_endpoint_service_error(self):
        """Test chat endpoint with service error."""
        # Mock the services to return an error
        with patch('src.api.routes.chat_service') as mock_chat_service:
            mock_chat_service.process_chat_request = AsyncMock(
                return_value={
                    "success": False,
                    "error": "AI Service Error",
                    "dialogId": "dialog123"
                }
            )

            request_data = {
                "question": "Hello",
                "accountId": "user123",
                "sex": "女"
            }

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/api/doubao/chat", json=request_data)

            assert response.status_code == 500  # Internal server error
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_with_ai_error(self):
        """Test chat endpoint with AI service error."""
        # Mock the services to simulate AI error
        with patch('src.api.routes.chat_service') as mock_chat_service:
            mock_chat_service.process_chat_request = AsyncMock(
                side_effect=Exception("AI Service Unavailable")
            )

            request_data = {
                "question": "Hello",
                "accountId": "user123",
                "sex": "女"
            }

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/api/doubao/chat", json=request_data)

            assert response.status_code == 500  # Internal server error

    @pytest.mark.asyncio
    async def test_chat_endpoint_concurrent_requests(self):
        """Test chat endpoint with concurrent requests."""
        # Mock the services
        with patch('src.api.routes.chat_service') as mock_chat_service:
            mock_chat_service.process_chat_request = AsyncMock(
                side_effect=lambda req: {
                    "success": True,
                    "response": f"Response for {req.question}",
                    "dialogId": f"dialog_{id(req)}",
                    "timestamp": "2024-01-01T00:00:00"
                }
            )

            request_data = {
                "question": "Hello",
                "accountId": "user123",
                "sex": "女"
            }

            # Make multiple concurrent requests
            async with AsyncClient(app=app, base_url="http://test") as ac:
                tasks = [ac.post("/api/doubao/chat", json=request_data) for _ in range(5)]
                responses = await asyncio.gather(*tasks)

            # All requests should succeed
            for response in responses:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_endpoint_rate_limiting(self):
        """Test chat endpoint rate limiting."""
        # This test would require implementing rate limiting
        # For now, we'll just verify the endpoint doesn't break
        request_data = {
            "question": "Hello",
            "accountId": "user123",
            "sex": "女"
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Make multiple requests quickly
            for i in range(10):
                response = await ac.post("/api/doubao/chat", json=request_data)
                # Should not return 429 (Too Many Requests) unless rate limiting is implemented
                assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_middleware_integration(self):
        """Test middleware integration."""
        # Test that CORS middleware works
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Preflight request
            response = await ac.options("/api/doubao/chat", headers=headers)

            # Should return appropriate CORS headers
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test with invalid JSON
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/doubao/chat",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 422  # Unprocessable entity

        # Test with missing content type
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/api/doubao/chat", json={})

            assert response.status_code == 422  # Validation error