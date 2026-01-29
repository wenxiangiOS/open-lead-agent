"""Tests for services module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.services.ai_service import AIService
from src.services.chat_service import ChatService
from src.services.user_service import UserService


class TestAIService:
    """Test AIService class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_client = Mock()
        self.ai_service = AIService(self.mock_client)

    def test_ai_service_initialization(self):
        """Test AIService initializes correctly."""
        assert self.ai_service.client == self.mock_client
        assert self.ai_service.model_name == "doubao-seed-1-6-251015"

    @patch('src.services.ai_service.generate_embedding')
    async def test_generate_response_success(self, mock_generate_embedding):
        """Test successful response generation."""
        # Mock the embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock the OpenAI client response
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Hello! How can I help you today?"
                }
            }]
        }
        self.mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test response generation
        response = await self.ai_service.generate_response(
            "Hello",
            system_prompt="You are a helpful assistant"
        )

        assert response == "Hello! How can I help you today?"
        self.mock_client.chat.completions.create.assert_called_once()

    @patch('src.services.ai_service.generate_embedding')
    async def test_generate_response_with_error(self, mock_generate_embedding):
        """Test response generation with error."""
        # Mock the embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock the OpenAI client to raise an error
        self.mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Test error handling
        with pytest.raises(Exception, match="API Error"):
            await self.ai_service.generate_response(
                "Hello",
                system_prompt="You are a helpful assistant"
            )

    @patch('src.services.ai_service.generate_embedding')
    async def test_generate_response_with_empty_content(self, mock_generate_embedding):
        """Test response generation with empty content."""
        # Mock the embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock the OpenAI client response with empty content
        mock_response = {
            "choices": [{
                "message": {
                    "content": ""
                }
            }]
        }
        self.mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test response generation
        response = await self.ai_service.generate_response(
            "Hello",
            system_prompt="You are a helpful assistant"
        )

        assert response == ""

    async def test_generate_embedding_success(self):
        """Test successful embedding generation."""
        mock_response = {
            "data": [{
                "embedding": [0.1, 0.2, 0.3, 0.4]
            }]
        }

        with patch('openai.Embedding.create', return_value=mock_response):
            embedding = await self.ai_service.generate_embedding("test text")

            assert embedding == [0.1, 0.2, 0.3, 0.4]

    async def test_generate_embedding_error(self):
        """Test embedding generation with error."""
        with patch('openai.Embedding.create', side_effect=Exception("Embedding error")):
            with pytest.raises(Exception, match="Embedding error"):
                await self.ai_service.generate_embedding("test text")


class TestChatService:
    """Test ChatService class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_ai_service = Mock(spec=AIService)
        self.mock_user_service = Mock()
        self.chat_service = ChatService(
            ai_service=self.mock_ai_service,
            user_service=self.mock_user_service
        )

    @pytest.mark.asyncio
    async def test_process_chat_request_success(self):
        """Test successful chat request processing."""
        # Mock request
        request = Mock()
        request.question = "Hello"
        request.accountId = "user123"
        request.sex = "女"
        request.dialogId = "dialog456"

        # Mock user state
        mock_user_state = Mock()
        mock_user_state.get_conversation_context.return_value = {
            "recent_messages": [],
            "dialog_count": 0
        }
        self.mock_user_service.get_user_state.return_value = mock_user_state

        # Mock AI response
        self.mock_ai_service.generate_response = AsyncMock(
            return_value="Hi there! How can I help you?"
        )

        # Process chat request
        result = await self.chat_service.process_chat_request(request)

        # Verify results
        assert result["success"] is True
        assert result["response"] == "Hi there! How can I help you?"
        assert result["dialogId"] == "dialog456"
        assert "timestamp" in result

        # Verify calls
        self.mock_user_service.get_user_state.assert_called_once_with("user123")
        self.mock_ai_service.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_request_with_error(self):
        """Test chat request processing with error."""
        # Mock request
        request = Mock()
        request.question = "Hello"
        request.accountId = "user123"

        # Mock AI service to raise error
        self.mock_ai_service.generate_response = AsyncMock(
            side_effect=Exception("AI Service Error")
        )

        # Process chat request
        result = await self.chat_service.process_chat_request(request)

        # Verify error handling
        assert result["success"] is False
        assert "error" in result
        assert "AI Service Error" in result["error"]

    @pytest.mark.asyncio
    async def test_process_chat_request_empty_question(self):
        """Test chat request with empty question."""
        # Mock request with empty question
        request = Mock()
        request.question = ""
        request.accountId = "user123"

        # Process chat request
        result = await self.chat_service.process_chat_request(request)

        # Verify validation error
        assert result["success"] is False
        assert "error" in result
        assert "Empty question" in result["error"]


class TestUserService:
    """Test UserService class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.user_service = UserService()

    def test_get_user_state_new_user(self):
        """Test getting user state for new user."""
        user_state = self.user_service.get_user_state("new_user")

        assert user_state.user_id == "new_user"
        assert user_state.dialog_count == 0
        assert len(user_state.conversation_history) == 0

    def test_get_user_state_existing_user(self):
        """Test getting user state for existing user."""
        # Pre-populate user state
        self.user_service.get_user_state("existing_user")

        # Get existing user state
        user_state = self.user_service.get_user_state("existing_user")

        assert user_state.user_id == "existing_user"
        assert user_state.dialog_count == 0  # Should still be 0 since we haven't recorded interactions

    def test_update_user_preference(self):
        """Test updating user preference."""
        user_state = self.user_service.get_user_state("user123")

        self.user_service.update_user_preference("user123", "location", "Beijing")

        assert user_state.get_preference("location") == "Beijing"

    def test_get_user_preference(self):
        """Test getting user preference."""
        user_state = self.user_service.get_user_state("user123")

        # Update preference
        self.user_service.update_user_preference("user123", "location", "Beijing")

        # Get preference
        preference = self.user_service.get_user_preference("user123", "location")
        assert preference == "Beijing"

        # Get non-existent preference
        preference = self.user_service.get_user_preference("user123", "non_existent", "default")
        assert preference == "default"