"""API v1 模块"""

from fastapi import APIRouter
from .chat import router as chat_router

__all__ = ['chat_router']
