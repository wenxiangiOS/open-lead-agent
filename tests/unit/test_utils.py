"""Tests for utils module."""

import pytest
from unittest.mock import Mock, patch

from src.utils.input_analyzer import InputAnalyzer
from src.utils.text_generator import TextGenerator


class TestInputAnalyzer:
    """Test InputAnalyzer class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = InputAnalyzer()

    def test_analyze_greeting(self):
        """Test greeting analysis."""
        test_cases = [
            ("你好", {"intent": "greeting", "confidence": 0.95}),
            ("hello", {"intent": "greeting", "confidence": 0.9}),
            ("hi", {"intent": "greeting", "confidence": 0.85}),
            ("嗨", {"intent": "greeting", "confidence": 0.9}),
        ]

        for text, expected in test_cases:
            result = self.analyzer.analyze(text)
            assert result["intent"] == expected["intent"]
            assert result["confidence"] >= expected["confidence"]

    def test_analyze_question_about_relationship(self):
        """Test relationship question analysis."""
        test_cases = [
            ("我想找对象", {"intent": "relationship_seeking", "confidence": 0.9}),
            ("怎么脱单", {"intent": "relationship_seeking", "confidence": 0.95}),
            ("如何交友", {"intent": "relationship_seeking", "confidence": 0.85}),
            ("想谈恋爱", {"intent": "relationship_seeking", "confidence": 0.9}),
        ]

        for text, expected in test_cases:
            result = self.analyzer.analyze(text)
            assert result["intent"] == expected["intent"]
            assert result["confidence"] >= expected["confidence"]

    def test_analyze_personal_info_request(self):
        """Test personal info request analysis."""
        test_cases = [
            ("多大了", {"intent": "personal_info_request", "confidence": 0.9}),
            ("你是做什么的", {"intent": "personal_info_request", "confidence": 0.85}),
            ("身高多少", {"intent": "personal_info_request", "confidence": 0.8}),
        ]

        for text, expected in test_cases:
            result = self.analyzer.analyze(text)
            assert result["intent"] == expected["intent"]
            assert result["confidence"] >= expected["confidence"]

    def test_analyze_complaint(self):
        """Test complaint analysis."""
        test_cases = [
            ("你不懂", {"intent": "complaint", "confidence": 0.9}),
            ("太差了", {"intent": "complaint", "confidence": 0.85}),
            ("不满意", {"intent": "complaint", "confidence": 0.8}),
        ]

        for text, expected in test_cases:
            result = self.analyzer.analyze(text)
            assert result["intent"] == expected["intent"]
            assert result["confidence"] >= expected["confidence"]

    def test_analyze_unknown_intent(self):
        """Test unknown intent analysis."""
        test_cases = [
            ("随机文本", {"intent": "unknown", "confidence": 0.1}),
            ("123456", {"intent": "unknown", "confidence": 0.05}),
            ("", {"intent": "unknown", "confidence": 0.0}),
        ]

        for text, expected in test_cases:
            result = self.analyzer.analyze(text)
            assert result["intent"] == expected["intent"]
            assert result["confidence"] <= expected["confidence"]

    def test_extract_keywords(self):
        """Test keyword extraction."""
        test_cases = [
            (
                "我想找一个25-30岁的男朋友",
                {"keywords": ["男朋友", "25", "30", "岁"], "age_range": "25-30"}
            ),
            (
                "在北京工作，喜欢旅游",
                {"keywords": ["北京", "工作", "旅游"], "location": "北京"}
            ),
            (
                "身高175以上",
                {"keywords": ["身高", "175"], "height_requirement": "175+"}
            ),
        ]

        for text, expected in test_cases:
            result = self.analyzer.extract_keywords(text)
            for keyword in expected["keywords"]:
                assert keyword in result["keywords"]

            # Check specific extracted info
            if "age_range" in expected:
                assert result.get("age_range") == expected["age_range"]
            if "location" in expected:
                assert result.get("location") == expected["location"]
            if "height_requirement" in expected:
                assert result.get("height_requirement") == expected["height_requirement"]

    def test_detect_emotion(self):
        """Test emotion detection."""
        test_cases = [
            ("我很开心", "happy"),
            ("我很难过", "sad"),
            ("我很生气", "angry"),
            ("我很焦虑", "anxious"),
            ("随便吧", "neutral"),
        ]

        for text, expected_emotion in test_cases:
            emotion = self.analyzer.detect_emotion(text)
            assert emotion == expected_emotion

    def test_analyze_comprehensive(self):
        """Test comprehensive analysis."""
        text = "我想找一个25-30岁的男朋友，在北京工作"
        result = self.analyzer.analyze_comprehensive(text)

        assert "intent" in result
        assert "keywords" in result
        assert "emotion" in result
        assert "confidence" in result
        assert result["intent"] == "relationship_seeking"
        assert "男朋友" in result["keywords"]
        assert "北京" in result["keywords"]
        assert result["emotion"] == "neutral"


class TestTextGenerator:
    """Test TextGenerator class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = TextGenerator()
        self.mock_personality = Mock()
        self.mock_personality.name = "小桃子"
        self.mock_personality.catchphrases = ["说起来", "那个啥", "对了"]
        self.mock_personality.get_speech_pattern = Mock(return_value=["嗯", "诶", "噢"])
        self.mock_personality.generate_emotion_emoji = Mock(return_value="😊")

    def test_generate_greeting_with_personality(self):
        """Test greeting generation with personality."""
        greeting = self.generator.generate_greeting(
            self.mock_personality,
            user_name="用户"
        )

        assert "小桃子" in greeting
        assert "用户" in greeting
        assert any(phrase in greeting for phrase in ["说起来", "那个啥", "对了"])
        assert any(emoji in greeting for emoji in ["😊", "😂", "😅"])

    def test_generate_response_with_context(self):
        """Test response generation with conversation context."""
        context = {
            "recent_messages": [
                {"user": "我想找对象"},
                {"assistant": "我可以帮你"}
            ]
        }

        response = self.generator.generate_response_with_context(
            self.mock_personality,
            "有什么建议吗？",
            context
        )

        assert isinstance(response, str)
        assert len(response) > 0

    def test_add_personality_filler_words(self):
        """Test adding personality filler words."""
        text = "我想找个男朋友"
        enhanced = self.generator.add_personality_filler_words(
            self.mock_personality,
            text
        )

        # Should contain filler words
        assert any(filler in enhanced for filler in ["嗯", "诶", "噢"])

    def test_add_emotion_emoji(self):
        """Test adding emotion emoji."""
        text = "我很开心"
        enhanced = self.generator.add_emotion_emoji(
            self.mock_personality,
            text,
            emotion="happy"
        )

        assert "😊" in enhanced or "😂" in enhanced or "😆" in enhanced

    def test_generate_catchphrase_response(self):
        """Test response with catchphrase."""
        response = self.generator.generate_catchphrase_response(
            self.mock_personality,
            "那个啥",
            "用户的问题"
        )

        assert "那个啥" in response

    def test_generate_professional_advice(self):
        """Test professional advice generation."""
        advice = self.generator.generate_professional_advice(
            "如何交友",
            "user123"
        )

        assert isinstance(advice, str)
        assert len(advice) > 0
        assert "建议" in advice or "方法" in advice or "可以" in advice

    def test_generate_light_hearted_response(self):
        """Test light-hearted response generation."""
        response = self.generator.generate_light_hearted_response(
            self.mock_personality,
            "今天天气真好"
        )

        assert isinstance(response, str)
        assert len(response) > 0
        # Should contain some personality traits

    def test_generate_follow_up_question(self):
        """Test follow-up question generation."""
        question = self.generator.generate_follow_up_question(
            self.mock_personality,
            "用户说喜欢旅游"
        )

        assert isinstance(question, str)
        assert len(question) > 0
        assert "？" in question or "呢" in question or "吗" in question