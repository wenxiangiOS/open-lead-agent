"""Compatibility exports for the legacy ``src.services`` package.

Keep this module side-effect light to avoid import cycles during the
services/modules migration. Import concrete symbols from their leaf modules
when possible instead of relying on package-level re-exports.
"""

__all__ = [
    "AIService",
    "UserService",
    "ChatService",
    "ExtractionService",
    "RedisService",
    "redis_service",
    "ValidationService",
    "DialogueManager",
    "RefusalService",
    "FieldSkipService",
]


def __getattr__(name: str):
    if name == "AIService":
        from src.services.ai_service import AIService
        return AIService
    if name == "UserService":
        from src.services.data.user_service import UserService
        return UserService
    if name == "ChatService":
        from src.services.core.chat_service import ChatService
        return ChatService
    if name == "ExtractionService":
        from src.services.data.extraction_service import ExtractionService
        return ExtractionService
    if name in {"RedisService", "redis_service"}:
        from src.services.data.redis_service import RedisService, redis_service
        return {"RedisService": RedisService, "redis_service": redis_service}[name]
    if name == "ValidationService":
        from src.services.data.validation_service import ValidationService
        return ValidationService
    if name == "DialogueManager":
        from src.services.core.dialogue_manager import DialogueManager
        return DialogueManager
    if name == "RefusalService":
        from src.services.refusal_service import RefusalService
        return RefusalService
    if name == "FieldSkipService":
        from src.services.field_skip_service import FieldSkipService
        return FieldSkipService
    raise AttributeError(name)
