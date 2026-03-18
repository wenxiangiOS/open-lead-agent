"""Xiaohongshu async ingest route."""

import logging
import hashlib
import hmac
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from src.services.queue.message_orchestrator import MessageOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["小红书入站"])

orchestrator: MessageOrchestrator | None = None


def init_service(service: MessageOrchestrator) -> None:
    global orchestrator
    orchestrator = service


@router.post("/api/xiaohongshu/messages/ingest")
async def ingest_message(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="ingest service not initialized")

    try:
        # Optional API key guard.
        expected_api_key = os.getenv("XHS_INGEST_API_KEY", "").strip()
        if expected_api_key:
            provided_api_key = (request.headers.get("X-API-Key") or "").strip()
            if not hmac.compare_digest(provided_api_key, expected_api_key):
                raise HTTPException(status_code=401, detail="unauthorized")

        # Optional signature guard: HMAC_SHA256(secret, "<timestamp>.<raw_body>")
        signing_secret = os.getenv("XHS_INGEST_SIGNING_SECRET", "").strip()
        if signing_secret:
            ts = (request.headers.get("X-Timestamp") or "").strip()
            sig = (request.headers.get("X-Signature") or "").strip()
            if not ts or not sig:
                raise HTTPException(status_code=401, detail="missing signature")
            try:
                ts_int = int(ts)
            except ValueError:
                raise HTTPException(status_code=401, detail="invalid timestamp")

            now = int(time.time())
            max_skew = int(os.getenv("XHS_INGEST_MAX_SKEW_SECONDS", "300"))
            if abs(now - ts_int) > max_skew:
                raise HTTPException(status_code=401, detail="stale signature")

            raw_body = (await request.body()) or b""
            signed = f"{ts}.".encode("utf-8") + raw_body
            expected_sig = hmac.new(
                signing_secret.encode("utf-8"),
                signed,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                raise HTTPException(status_code=401, detail="invalid signature")

        result = await orchestrator.ingest(payload)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("[ingest] failed")
        raise HTTPException(status_code=500, detail="ingest failed")


@router.get("/api/xiaohongshu/messages/replies")
async def poll_replies(
    request: Request,
    accountId: str = Query(..., min_length=1),
    after: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="ingest service not initialized")

    # Reuse optional API key guard for polling.
    expected_api_key = os.getenv("XHS_INGEST_API_KEY", "").strip()
    if expected_api_key:
        provided_api_key = (request.headers.get("X-API-Key") or "").strip()
        if not hmac.compare_digest(provided_api_key, expected_api_key):
            raise HTTPException(status_code=401, detail="unauthorized")

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
