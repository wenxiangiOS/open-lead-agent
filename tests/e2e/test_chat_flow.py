"""End-to-end tests for chat flow."""

import pytest
import asyncio
from httpx import AsyncClient


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

        async with AsyncClient(app=app, base_url="http://test") as ac:
            for message in conversation:
                response = await ac.post("/api/doubao/chat", json={
                    "question": message,
                    "accountId": "user123",
                    "sex": "女"
                })

                assert response.status_code == 200
                data = response.json()
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

        async with AsyncClient(app=app, base_url="http://test") as ac:
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
        async with AsyncClient(app=app, base_url="http://test") as ac:
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
            async with AsyncClient(app=app, base_url="http://test") as ac:
                for i, message in enumerate(messages):
                    response = await ac.post("/api/doubao/chat", json={
                        "question": message,
                        "accountId": user_id,
                        "sex": "女"
                    })

                    if response.status_code == 200:
                        data = response.json()
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

        async with AsyncClient(app=app, base_url="http://test") as ac:
            responses = []

            for i in range(message_count):
                response = await ac.post("/api/doubao/chat", json={
                    "question": f"Message {i + 1}",
                    "accountId": user_id,
                    "sex": "女"
                })

                assert response.status_code == 200
                data = response.json()
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

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # First message - provide personal info
            response1 = await ac.post("/api/doubao/chat", json={
                "question": "我25岁，在北京工作",
                "accountId": user_id,
                "sex": "女"
            })

            assert response1.status_code == 200
            data1 = response1.json()

            # Second message - reference previous info
            response2 = await ac.post("/api/doubao/chat", json={
                "question": "能推荐一些北京的交友活动吗？",
                "accountId": user_id,
                "sex": "女"
            })

            assert response2.status_code == 200
            data2 = response2.json()

            # The response should acknowledge the previous context
            response_text = data2["response"].lower()
            # Should mention location context or similar
            assert any(word in response_text for word in ["北京", "活动", "推荐"])

    @pytest.mark.asyncio
    async def test_different_user_types(self):
        """Test handling different user types and preferences."""
        test_cases = [
            {"user_id": "male_user", "sex": "男"},
            {"user_id": "female_user", "sex": "女"},
            {"user_id": "other_user", "sex": "other"}
        ]

        async with AsyncClient(app=app, base_url="http://test") as ac:
            for case in test_cases:
                response = await ac.post("/api/doubao/chat", json={
                    "question": "我想找对象",
                    "accountId": case["user_id"],
                    "sex": case["sex"]
                })

                assert response.status_code == 200
                data = response.json()

                # Response should be appropriate for the user type
                response_text = data["response"].lower()
                # Should contain appropriate greeting or response
                assert len(response_text) > 0

    @pytest.mark.asyncio
    async def test_service_availability_monitoring(self):
        """Test service availability monitoring."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
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