"""Xiaohongshu async ingest route."""

import asyncio
import json
import logging
import hashlib
import hmac
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from src.modules.message_queue.application.message_orchestrator import MessageOrchestrator
from src.modules.shared.models.use_case_models import IngestMessageCommand

logger = logging.getLogger(__name__)

router = APIRouter(tags=["小红书入站"])

orchestrator: MessageOrchestrator | None = None


def init_service(service: MessageOrchestrator) -> None:
    global orchestrator
    orchestrator = service


def _http_detail(error_code: str, error: str, **details: Any) -> Dict[str, Any]:
    return {
        "error": error,
        "error_code": error_code,
        "details": details,
    }


def _build_ingest_command(payload: Dict[str, Any]) -> IngestMessageCommand:
    return IngestMessageCommand(
        account_id=str(payload.get("accountId") or "").strip(),
        dialog_id=payload.get("dialogId"),
        message=str(payload.get("message") or "").strip(),
        platform_msg_id=str(payload.get("platformMsgId") or "").strip(),
        timestamp=payload.get("timestamp"),
        sex=payload.get("sex"),
    )


@router.post("/api/xiaohongshu/messages/ingest")
async def ingest_message(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("INGEST_SERVICE_NOT_INITIALIZED", "ingest_service_not_initialized", route="xhs_ingest"),
        )

    try:
        # Optional API key guard.
        expected_api_key = os.getenv("XHS_INGEST_API_KEY", "").strip()
        if expected_api_key:
            provided_api_key = (request.headers.get("X-API-Key") or "").strip()
            if not hmac.compare_digest(provided_api_key, expected_api_key):
                raise HTTPException(
                    status_code=401,
                    detail=_http_detail("XHS_INGEST_UNAUTHORIZED", "unauthorized", route="xhs_ingest"),
                )

        # Optional signature guard: HMAC_SHA256(secret, "<timestamp>.<raw_body>")
        signing_secret = os.getenv("XHS_INGEST_SIGNING_SECRET", "").strip()
        if signing_secret:
            ts = (request.headers.get("X-Timestamp") or "").strip()
            sig = (request.headers.get("X-Signature") or "").strip()
            if not ts or not sig:
                raise HTTPException(
                    status_code=401,
                    detail=_http_detail("XHS_INGEST_MISSING_SIGNATURE", "missing_signature", route="xhs_ingest"),
                )
            try:
                ts_int = int(ts)
            except ValueError:
                raise HTTPException(
                    status_code=401,
                    detail=_http_detail("XHS_INGEST_INVALID_TIMESTAMP", "invalid_timestamp", route="xhs_ingest"),
                )

            now = int(time.time())
            max_skew = int(os.getenv("XHS_INGEST_MAX_SKEW_SECONDS", "300"))
            if abs(now - ts_int) > max_skew:
                raise HTTPException(
                    status_code=401,
                    detail=_http_detail("XHS_INGEST_STALE_SIGNATURE", "stale_signature", route="xhs_ingest"),
                )

            raw_body = (await request.body()) or b""
            signed = f"{ts}.".encode("utf-8") + raw_body
            expected_sig = hmac.new(
                signing_secret.encode("utf-8"),
                signed,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                raise HTTPException(
                    status_code=401,
                    detail=_http_detail("XHS_INGEST_INVALID_SIGNATURE", "invalid_signature", route="xhs_ingest"),
                )

        result = await orchestrator.ingest_command(_build_ingest_command(payload))
        return result.payload
    except HTTPException:
        raise
    except Exception:
        logger.exception("[ingest] failed")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("XHS_INGEST_FAILED", "ingest_failed", route="xhs_ingest"),
        )


@router.get("/api/xiaohongshu/messages/replies")
async def poll_replies(
    request: Request,
    accountId: str = Query(..., min_length=1),
    after: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("INGEST_SERVICE_NOT_INITIALIZED", "ingest_service_not_initialized", route="xhs_replies"),
        )

    # Reuse optional API key guard for polling.
    expected_api_key = os.getenv("XHS_INGEST_API_KEY", "").strip()
    if expected_api_key:
        provided_api_key = (request.headers.get("X-API-Key") or "").strip()
        if not hmac.compare_digest(provided_api_key, expected_api_key):
            raise HTTPException(
                status_code=401,
                detail=_http_detail("XHS_REPLIES_UNAUTHORIZED", "unauthorized", route="xhs_replies"),
            )

    replies = await orchestrator.queue_store.fetch_delivered_replies(
        account_id=accountId,
        after_id=after,
        limit=limit,
    )
    next_after = after
    if replies:
        next_after = max(int(item.get("id", 0)) for item in replies)

    return {
        "success": True,
        "accountId": accountId,
        "after": after,
        "nextAfter": next_after,
        "replies": replies,
    }


@router.get("/api/xiaohongshu/messages/replies/stream")
async def stream_replies(
    request: Request,
    accountId: str = Query(..., min_length=1),
    after: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> StreamingResponse:
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("INGEST_SERVICE_NOT_INITIALIZED", "ingest_service_not_initialized", route="xhs_replies_stream"),
        )

    expected_api_key = os.getenv("XHS_INGEST_API_KEY", "").strip()
    if expected_api_key:
        provided_api_key = (request.headers.get("X-API-Key") or "").strip()
        if not hmac.compare_digest(provided_api_key, expected_api_key):
            raise HTTPException(
                status_code=401,
                detail=_http_detail("XHS_REPLIES_UNAUTHORIZED", "unauthorized", route="xhs_replies_stream"),
            )

    async def event_generator():
        current_after = after
        heartbeat_interval = 15.0
        last_heartbeat = time.monotonic()

        while True:
            if await request.is_disconnected():
                break

            replies = await orchestrator.queue_store.fetch_delivered_replies(
                account_id=accountId,
                after_id=current_after,
                limit=limit,
            )

            if replies:
                current_after = max(int(item.get("id", 0)) for item in replies)
                payload = {
                    "success": True,
                    "accountId": accountId,
                    "nextAfter": current_after,
                    "replies": replies,
                }
                yield f"event: replies\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_heartbeat = time.monotonic()
            else:
                now = time.monotonic()
                if now - last_heartbeat >= heartbeat_interval:
                    yield "event: ping\ndata: {}\n\n"
                    last_heartbeat = now

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
