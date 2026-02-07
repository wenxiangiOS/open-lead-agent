"""User state management model"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class UserState:
    """Manages conversation state and preferences for each user"""

    def __init__(self, user_id: str):
        """Initialize user state"""
        self.user_id = user_id
        self.dialog_count = 0
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_interaction: Optional[datetime] = None
        self.preferences: Dict[str, Any] = {}
        self.session_start: datetime = datetime.now()
        self.active_dialog_id: Optional[str] = None
        # 联系方式错误次数跟踪
        self.contact_error_count: int = 0
        self.last_contact_error_time: Optional[datetime] = None
        # 用户连续回确认词但没有提供信息的次数跟踪
        self.non_response_count: int = 0
        self.last_non_response_time: Optional[datetime] = None

    def record_interaction(
        self,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a conversation interaction"""
        timestamp = datetime.now()

        # Create interaction record
        interaction = {
            "timestamp": timestamp.isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "metadata": metadata or {}
        }

        # Add to conversation history
        self.conversation_history.append(interaction)

        # Update counters
        self.dialog_count += 1
        self.last_interaction = timestamp

        # Limit history size (keep last 50 interactions)
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

    def update_preference(self, key: str, value: Any) -> None:
        """Update user preference"""
        self.preferences[key] = value
        # Also record the update time
        self.preferences[f"{key}_updated"] = datetime.now().isoformat()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self.preferences.get(key, default)

    def get_conversation_context(self, lookback: int = 5) -> Dict[str, Any]:
        """Get conversation context for AI"""
        recent_messages = self.conversation_history[-lookback:]

        # Extract recent user messages
        user_messages = [
            msg["user_message"] for msg in recent_messages
        ]

        # Extract recent assistant responses
        assistant_responses = [
            msg["assistant_response"] for msg in recent_messages
        ]

        return {
            "user_id": self.user_id,
            "dialog_count": self.dialog_count,
            "recent_messages": user_messages,
            "recent_responses": assistant_responses,
            "preferences": self.preferences,
            "session_duration": (datetime.now() - self.session_start).total_seconds()
        }

    def get_user_profile(self) -> Dict[str, Any]:
        """Get comprehensive user profile"""
        return {
            "user_id": self.user_id,
            "session_info": {
                "start_time": self.session_start.isoformat(),
                "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
                "dialog_count": self.dialog_count,
                "session_duration": (datetime.now() - self.session_start).total_seconds()
            },
            "preferences": self.preferences,
            "conversation_summary": self.get_conversation_summary()
        }

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Generate conversation summary"""
        if not self.conversation_history:
            return {"total_messages": 0, "topics": []}

        # Extract topics (keywords from messages)
        topics = set()
        for msg in self.conversation_history:
            # Simple keyword extraction (in production, use NLP)
            text = msg["user_message"] + " " + msg["assistant_response"]
            words = text.split()
            for word in words:
                if len(word) > 2:  # Skip short words
                    topics.add(word)

        # Calculate sentiment trends (simplified)
        recent_sentiment = "neutral"
        recent_messages = self.conversation_history[-3:]
        if len(recent_messages) >= 2:
            # Simple heuristic: look for positive/negative words
            positive_words = ["好", "棒", "开心", "满意", "喜欢"]
            negative_words = ["不好", "差", "难过", "失望", "讨厌"]

            positive_count = sum(
                1 for msg in recent_messages
                if any(word in msg["user_message"] for word in positive_words)
            )
            negative_count = sum(
                1 for msg in recent_messages
                if any(word in msg["user_message"] for word in negative_words)
            )

            if positive_count > negative_count:
                recent_sentiment = "positive"
            elif negative_count > positive_count:
                recent_sentiment = "negative"

        return {
            "total_messages": len(self.conversation_history),
            "topics": list(topics)[:10],  # Top 10 topics
            "recent_sentiment": recent_sentiment,
            "last_message": self.conversation_history[-1]["user_message"] if self.conversation_history else None
        }

    def get_interaction_frequency(self, days: int = 7) -> float:
        """Get interaction frequency per day"""
        if not self.last_interaction:
            return 0.0

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_interactions = [
            msg for msg in self.conversation_history
            if datetime.fromisoformat(msg["timestamp"]) > cutoff_date
        ]

        return len(recent_interactions) / days if days > 0 else 0.0

    def is_new_user(self, threshold_hours: int = 24) -> bool:
        """Check if user is new"""
        if not self.last_interaction:
            return True

        time_diff = datetime.now() - self.last_interaction
        return time_diff.total_seconds() > threshold_hours * 3600

    def is_active_user(self, threshold_hours: int = 168) -> bool:
        """Check if user is active (within last week)"""
        if not self.last_interaction:
            return False

        time_diff = datetime.now() - self.last_interaction
        return time_diff.total_seconds() < threshold_hours * 3600

    def get_user_insights(self) -> Dict[str, Any]:
        """Get user insights for personalized responses"""
        insights = {
            "is_new_user": self.is_new_user(),
            "is_active_user": self.is_active_user(),
            "interaction_frequency": self.get_interaction_frequency(),
            "has_preferences": bool(self.preferences),
            "preference_keys": list(self.preferences.keys()),
            "conversation_depth": len(self.conversation_history)
        }

        # Add insights based on conversation content
        if self.conversation_history:
            # Check for specific interests mentioned
            interests = []
            for msg in self.conversation_history:
                text = msg["user_message"].lower()
                if any(keyword in text for keyword in ["电影", "音乐", "运动", "旅行", "阅读", "美食"]):
                    interests.append("general_interests")
                if any(keyword in text for keyword in ["工作", "职业", "事业"]):
                    interests.append("career")
                if any(keyword in text for keyword in ["学习", "教育", "课程"]):
                    interests.append("education")

            insights["interests"] = list(set(interests))

        return insights

    def reset_conversation(self) -> None:
        """Reset conversation history but keep preferences"""
        self.conversation_history = []
        self.dialog_count = 0
        self.last_interaction = None
        self.active_dialog_id = None

    def increment_contact_error(self) -> int:
        """增加联系方式错误次数，返回当前错误次数"""
        self.contact_error_count += 1
        self.last_contact_error_time = datetime.now()
        return self.contact_error_count

    def get_contact_error_count(self) -> int:
        """获取联系方式错误次数"""
        return self.contact_error_count

    def reset_contact_error_count(self) -> None:
        """重置联系方式错误次数（当用户成功提供联系方式后）"""
        self.contact_error_count = 0
        self.last_contact_error_time = None

    def increment_non_response(self) -> int:
        """增加用户连续回确认词的次数，返回当前次数"""
        self.non_response_count += 1
        self.last_non_response_time = datetime.now()
        return self.non_response_count

    def reset_non_response_count(self) -> None:
        """重置用户连续回确认词的次数（当用户提供了有效信息后）"""
        self.non_response_count = 0
        self.last_non_response_time = None

    def get_non_response_count(self) -> int:
        """获取用户连续回确认词的次数"""
        return self.non_response_count

    def export_state(self) -> Dict[str, Any]:
        """Export user state for persistence"""
        return {
            "user_id": self.user_id,
            "dialog_count": self.dialog_count,
            "conversation_history": self.conversation_history,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "preferences": self.preferences,
            "session_start": self.session_start.isoformat(),
            "active_dialog_id": self.active_dialog_id,
            "contact_error_count": self.contact_error_count,
            "last_contact_error_time": self.last_contact_error_time.isoformat() if self.last_contact_error_time else None,
            "non_response_count": self.non_response_count,
            "last_non_response_time": self.last_non_response_time.isoformat() if self.last_non_response_time else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Alias for export_state"""
        return self.export_state()

    @classmethod
    def from_dict(cls, data: Dict[str, Any], user_id: Optional[str] = None) -> "UserState":
        """Create user state from dictionary"""
        uid = user_id or data.get("user_id")
        if not uid:
            raise ValueError("user_id is required")
        state = cls(uid)
        state.dialog_count = data.get("dialog_count", 0)
        state.conversation_history = data.get("conversation_history", [])

        if data.get("last_interaction"):
            state.last_interaction = datetime.fromisoformat(data["last_interaction"])

        state.preferences = data.get("preferences", {})
        state.session_start = datetime.fromisoformat(data["session_start"]) if data.get("session_start") else datetime.now()
        state.active_dialog_id = data.get("active_dialog_id")
        state.contact_error_count = data.get("contact_error_count", 0)
        if data.get("last_contact_error_time"):
            state.last_contact_error_time = datetime.fromisoformat(data["last_contact_error_time"])
        state.non_response_count = data.get("non_response_count", 0)
        if data.get("last_non_response_time"):
            state.last_non_response_time = datetime.fromisoformat(data["last_non_response_time"])

        return state