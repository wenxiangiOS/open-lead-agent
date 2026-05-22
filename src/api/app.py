"""FastAPI 应用创建与顶层路由注册。FastAPI app factory and top-level routes."""

from fastapi import FastAPI

from src.channels.http import router
from src.ops.health import health_payload


def create_app() -> FastAPI:
    app = FastAPI(
        title="open-lead-agent",
        description="Configurable AI customer agent for lead collection, RAG, and multi-LLM chat.",
        version="0.1.0",
    )
    app.include_router(router)

    @app.get("/health", tags=["ops"])
    async def health():
        return health_payload()

    return app


app = create_app()
