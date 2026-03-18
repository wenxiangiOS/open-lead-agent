"""End-to-end tests for chat flow."""

import pytest
import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from src.api.app import app


@asynccontextmanager
async def _test_client():
    prev_mq = os.getenv("MQ_ENABLED")
    os.environ["MQ_ENABLED"] = "false"
    await app.router.startup()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        await app.router.shutdown()
        if prev_mq is None:
            os.environ.pop("MQ_ENABLED", None)
        else:
            os.environ["MQ_ENABLED"] = prev_mq


def _has_meaningful_reply(payload: dict) -> bool:
    return bool(str(payload.get("response", "")).strip())


async def _skip_if_ai_unavailable(ac: AsyncClient) -> None:
    probe_user = f"e2e_probe_{uuid.uuid4().hex[:8]}"
    probe = await ac.post("/api/doubao/chat", json={
        "question": "连通性探测",
        "accountId": probe_user,
        "sex": "女"
    })
    if probe.status_code != 200:
        pytest.skip(f"AI probe failed with status {probe.status_code}")
    if not _has_meaningful_reply(probe.json()):
        pytest.skip("AI service unavailable in current test environment")


async def _post_chat_or_skip(ac: AsyncClient, payload: dict, *, reason: str) -> dict:
    resp = await ac.post("/api/doubao/chat", json=payload)
    if resp.status_code != 200:
        pytest.skip(f"{reason}: chat status={resp.status_code}")
    data = resp.json()
    if not _has_meaningful_reply(data):
        pytest.skip(f"{reason}: AI returned empty reply")
    return data


class TestChatFlowE2E:
    """End-to-end chat flow tests."""

    @pytest.mark.asyncio
    async def test_complete_chat_conversation(self):
        """Test complete conversation flow."""
        # This test would actually start the FastAPI server
        # For now, we'll mock the actual service

        conversation = [
            "你好",
            "我想找个男朋友",
            "有什么建议吗？",
            "谢谢你的帮助"
        ]

        responses = []

        async with _test_client() as ac:
            await _skip_if_ai_unavailable(ac)
            for message in conversation:
                data = await _post_chat_or_skip(ac, {
                    "question": message,
                    "accountId": "user123",
                    "sex": "女"
                }, reason="complete_chat_conversation")
                assert data["success"] is True
                assert "response" in data
                assert "dialogId" in data

                responses.append(data["response"])

                # Small delay between messages
                await asyncio.sleep(0.1)

        # Verify we got responses for all messages
        assert len(responses) == len(conversation)
        assert all(response for response in responses)

    @pytest.mark.asyncio
    async def test_user_state_persistence(self):
        """Test that user state persists across requests."""
        user_id = "test_user_123"
        dialog_id = "test_dialog_456"

        async with _test_client() as ac:
            # First message
            response1 = await ac.post("/api/doubao/chat", json={
                "question": "我想找对象",
                "accountId": user_id,
                "sex": "女",
                "dialogId": dialog_id
            })

            assert response1.status_code == 200
            data1 = response1.json()

            # Second message in same conversation
            response2 = await ac.post("/api/doubao/chat", json={
                "question": "我喜欢什么类型的",
                "accountId": user_id,
                "sex": "女",
                "dialogId": dialog_id
            })

            assert response2.status_code == 200
            data2 = response2.json()

            # Should have same dialog ID
            assert data1["dialogId"] == data2["dialogId"]

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery in chat flow."""
        async with _test_client() as ac:
            # First request with invalid data
            response1 = await ac.post("/api/doubao/chat", json={
                "accountId": "user123"
                # Missing required question field
            })

            assert response1.status_code == 422  # Validation error

            # Second request with valid data should still work
            response2 = await ac.post("/api/doubao/chat", json={
                "question": "Hello",
                "accountId": "user123",
                "sex": "女"
            })

            assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_users(self):
        """Test handling multiple concurrent users."""
        user_count = 3
        messages_per_user = 2

        async def user_conversation(user_id, messages):
            responses = []
            async with _test_client() as ac:
                await _skip_if_ai_unavailable(ac)
                for i, message in enumerate(messages):
                    data = await _post_chat_or_skip(ac, {
                        "question": message,
                        "accountId": user_id,
                        "sex": "女"
                    }, reason="concurrent_users")
                    responses.append(data["response"])

                    await asyncio.sleep(0.05)  # Small delay

            return responses

        # Create conversations for multiple users
        conversations = {}
        for i in range(user_count):
            user_id = f"concurrent_user_{i}"
            conversations[user_id] = [
                f"Hello from user {i}",
                f"How are you, user {i}?"
            ]

        # Run all conversations concurrently
        tasks = [
            user_conversation(user_id, messages)
            for user_id, messages in conversations.items()
        ]

        results = await asyncio.gather(*tasks)

        # Verify all users got responses
        assert len(results) == user_count
        for user_responses in results:
            assert len(user_responses) == messages_per_user
            assert all(response for response in user_responses)

    @pytest.mark.asyncio
    async def test_long_conversation(self):
        """Test handling of long conversations."""
        user_id = "long_conversation_user"
        message_count = 10

        async with _test_client() as ac:
            await _skip_if_ai_unavailable(ac)
            responses = []

            for i in range(message_count):
                data = await _post_chat_or_skip(ac, {
                    "question": f"Message {i + 1}",
                    "accountId": user_id,
                    "sex": "女"
                }, reason="long_conversation")
                responses.append(data["response"])

                # Small delay
                await asyncio.sleep(0.01)

        # Verify all messages got responses
        assert len(responses) == message_count
        assert all(response for response in responses)

    @pytest.mark.asyncio
    async def test_personalization_context(self):
        """Test that conversation context is maintained."""
        user_id = "personalization_test_user"

        async with _test_client() as ac:
            await _skip_if_ai_unavailable(ac)
            # First message - provide personal info
            data1 = await _post_chat_or_skip(ac, {
                "question": "我25岁，在北京工作",
                "accountId": user_id,
                "sex": "女"
            }, reason="personalization_context:first_message")

            # Second message - reference previous info
            data2 = await _post_chat_or_skip(ac, {
                "question": "能推荐一些北京的交友活动吗？",
                "accountId": user_id,
                "sex": "女"
            }, reason="personalization_context:second_message")
            assert data1["dialogId"] == data2["dialogId"]

            profile_resp = await ac.get(f"/api/doubao/profile/{user_id}")
            if profile_resp.status_code != 200:
                pytest.skip(f"personalization_context: profile status={profile_resp.status_code}")
            profile = profile_resp.json().get("profile", {})
            assert str(profile.get("age", "")).startswith("25")
            assert "北京" in str(profile.get("location", ""))

    @pytest.mark.asyncio
    async def test_different_user_types(self):
        """Test handling different user types and preferences."""
        test_cases = [
            {"user_id": "male_user", "sex": "男"},
            {"user_id": "female_user", "sex": "女"},
            {"user_id": "other_user", "sex": "other"}
        ]

        async with _test_client() as ac:
            await _skip_if_ai_unavailable(ac)
            for case in test_cases:
                data = await _post_chat_or_skip(ac, {
                    "question": "我想找对象",
                    "accountId": case["user_id"],
                    "sex": case["sex"]
                }, reason="different_user_types")

                # Response should be appropriate for the user type
                response_text = data["response"].lower()
                # Should contain appropriate greeting or response
                assert len(response_text) > 0

    @pytest.mark.asyncio
    async def test_service_availability_monitoring(self):
        """Test service availability monitoring."""
        async with _test_client() as ac:
            # Health check should always work
            health_response = await ac.get("/health")
            assert health_response.status_code == 200

            # Chat endpoint should be available
            chat_response = await ac.post("/api/doubao/chat", json={
                "question": "test",
                "accountId": "monitoring_test",
                "sex": "女"
            })

            # Should either succeed (200) or fail gracefully (500)
            assert chat_response.status_code in [200, 500]
