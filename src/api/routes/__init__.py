"""API routes package"""

from .health import router as health_router
from .chat import router as chat_router
from .conversation import router as conversation_router
from .user import router as user_router
from .system import router as system_router
from .xiaohongshu_ingest import router as xiaohongshu_ingest_router

__all__ = [
    'health_router',
    'chat_router',
    'conversation_router',
    'user_router',
    'system_router',
    'xiaohongshu_ingest_router',
]
