"""Compatibility exports for legacy data services.

Avoid eager imports here so importing one adapter does not pull the whole
services tree and create circular-import chains.
"""

__all__ = [
    "ExtractionService",
    "RedisService",
    "redis_service",
    "UserService",
    "ValidationService",
]


def __getattr__(name: str):
    if name == "ExtractionService":
        from src.services.data.extraction_service import ExtractionService
        return ExtractionService
    if name in {"RedisService", "redis_service"}:
        from src.services.data.redis_service import RedisService, redis_service
        return {"RedisService": RedisService, "redis_service": redis_service}[name]
    if name == "UserService":
        from src.services.data.user_service import UserService
        return UserService
    if name == "ValidationService":
        from src.services.data.validation_service import ValidationService
        return ValidationService
    raise AttributeError(name)
