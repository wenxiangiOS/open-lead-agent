"""Tests for models module."""

import pytest
from datetime import datetime

from src.models.personality import PersonalityProfile
from src.models.user_state import UserState
from src.models.requests import ChatRequest


class TestPersonalityProfile:
    """Test PersonalityProfile class."""

    def test_personality_profile_initialization(self):
        """Test PersonalityProfile initializes with default values."""
        personality = PersonalityProfile()

        assert personality.name == "小桃子"
        assert personality.age == 28
        assert personality.profession == "红娘"
        assert personality.experience_years == 3

    def test_personality_profile_custom_initialization(self):
        """Test PersonalityProfile initializes with custom values."""
        personality = PersonalityProfile(
            name="CustomName",
            age=25,
            profession="Consultant",
            experience_years=2
        )

        assert personality.name == "CustomName"
        assert personality.age == 25
        assert personality.profession == "Consultant"
        assert personality.experience_years == 2

    def test_get_personality_trait(self):
        """Test getting personality traits."""
        personality = PersonalityProfile()

        # Test default traits
        assert personality.get_trait("extroversion") == 0.75
        assert personality.get_trait("talkativeness") == 0.8
        assert personality.get_trait("patience") == 0.7

    def test_get_personality_trait_with_custom_trait(self):
        """Test getting personality trait with custom value."""
        personality = PersonalityProfile()
        personality.personality["custom_trait"] = 0.9

        assert personality.get_trait("custom_trait") == 0.9

    def test_get_speech_pattern(self):
        """Test getting speech patterns."""
        personality = PersonalityProfile()

        # Test default patterns
        fillers = personality.get_speech_pattern("fillers")
        assert "嗯" in fillers
        assert "诶" in fillers
        assert "那个" in fillers

    def test_get_catchphrase(self):
        """Test getting random catchphrase."""
        personality = PersonalityProfile()

        # Should return one of the catchphrases
        catchphrase = personality.get_random_catchphrase()
        assert catchphrase in personality.catchphrases

    def test_generate_emotion_emoji(self):
        """Test emotion emoji generation."""
        personality = PersonalityProfile()

        emoji = personality.generate_emotion_emoji()
        assert emoji in personality.speech_patterns["emotions"]


class TestUserState:
    """Test UserState class."""

    def test_user_state_initialization(self):
        """Test UserState initializes correctly."""
        user_state = UserState("user123")

        assert user_state.user_id == "user123"
        assert user_state.dialog_count == 0
        assert user_state.conversation_history == []
        assert user_state.last_interaction is None
        assert user_state.preferences == {}

    def test_record_interaction(self):
        """Test recording user interactions."""
        user_state = UserState("user123")

        # Record first interaction
        user_state.record_interaction("Hello", "Hi there!")

        assert user_state.dialog_count == 1
        assert len(user_state.conversation_history) == 1
        assert user_state.conversation_history[0]["user_message"] == "Hello"
        assert user_state.last_interaction is not None

    def test_record_interaction_multiple(self):
        """Test recording multiple interactions."""
        user_state = UserState("user123")

        # Record multiple interactions
        user_state.record_interaction("Hello", "Hi there!")
        user_state.record_interaction("How are you?", "I'm good!")

        assert user_state.dialog_count == 2
        assert len(user_state.conversation_history) == 2

    def test_get_conversation_context(self):
        """Test getting conversation context."""
        user_state = UserState("user123")

        # Add some interactions
        user_state.record_interaction("Hello", "Hi there!")
        user_state.record_interaction("How are you?", "I'm good!")

        context = user_state.get_conversation_context()

        assert "recent_messages" in context
        assert "dialog_count" in context
        assert "user_id" in context
        assert len(context["recent_messages"]) == 2

    def test_update_preference(self):
        """Test updating user preferences."""
        user_state = UserState("user123")

        user_state.update_preference("age_range", "25-35")
        user_state.update_preference("location", "Beijing")

        assert user_state.preferences["age_range"] == "25-35"
        assert user_state.preferences["location"] == "Beijing"

    def test_get_preference(self):
        """Test getting user preferences."""
        user_state = UserState("user123")

        # Set preference
        user_state.update_preference("age_range", "25-35")

        # Get preference
        assert user_state.get_preference("age_range") == "25-35"

        # Get non-existent preference with default
        assert user_state.get_preference("non_existent", "default") == "default"


class TestChatRequest:
    """Test ChatRequest model."""

    def test_chat_request_required_fields(self):
        """Test ChatRequest with required fields."""
        request = ChatRequest(question="Hello", accountId="user123")

        assert request.question == "Hello"
        assert request.accountId == "user123"
        assert request.sex == "女"  # Default value
        assert request.dialogId is None
        assert request.timestamp is None

    def test_chat_request_with_all_fields(self):
        """Test ChatRequest with all fields."""
        timestamp = datetime.now().isoformat()
        request = ChatRequest(
            question="Hello world",
            accountId="user456",
            dialogId="dialog789",
            sex="男",
            timestamp=timestamp
        )

        assert request.question == "Hello world"
        assert request.accountId == "user456"
        assert request.dialogId == "dialog789"
        assert request.sex == "男"
        assert request.timestamp == timestamp

    def test_chat_request_validation(self):
        """Test ChatRequest validation."""
        # Should raise error for missing required fields
        with pytest.raises(ValueError):
            ChatRequest(question="", accountId="user123")

        with pytest.raises(ValueError):
            ChatRequest(question="Hello", accountId="")

    def test_chat_request_sex_validation(self):
        """Test ChatRequest sex field validation."""
        # Valid sex values
        valid_sexes = ["男", "女", "other"]
        for sex in valid_sexes:
            request = ChatRequest(question="Hello", accountId="user123", sex=sex)
            assert request.sex == sex

        # Default sex when not provided
        request = ChatRequest(question="Hello", accountId="user123")
        assert request.sex == "女"