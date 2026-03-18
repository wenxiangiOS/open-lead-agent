from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ReplyDeliveryService:
    """Deliver replies to external platforms (Xiaohongshu)."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("XHS_REPLY_API", "").strip()
        self.backup_endpoint = os.getenv("XHS_REPLY_API_BACKUP", "").strip()
        self.timeout_seconds = float(os.getenv("XHS_REPLY_TIMEOUT_SECONDS", "8"))
        max_connections = int(os.getenv("XHS_REPLY_MAX_CONNECTIONS", "100"))
        max_keepalive = int(os.getenv("XHS_REPLY_MAX_KEEPALIVE", "20"))
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        )
        self._client = httpx.AsyncClient(timeout=self.timeout_seconds, limits=limits)

    async def _deliver_to_endpoint(self, endpoint: str, payload: dict) -> None:
        resp = await self._client.post(endpoint, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"delivery failed: status={resp.status_code} body={resp.text[:200]}")

    async def send_reply(
        self,
        account_id: str,
        reply_text: str,
        dialog_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        if not reply_text:
            return

        if not self.endpoint and not self.backup_endpoint:
            logger.info(
                "[mq.sender] XHS_REPLY_API not configured, skip delivery",
                extra={"account_id": account_id, "dialog_id": dialog_id},
            )
            return

        payload = {
            "accountId": account_id,
            "dialogId": dialog_id,
            "message": reply_text,
            "clientMsgId": idempotency_key,
        }

        if self.endpoint:
            try:
                await self._deliver_to_endpoint(self.endpoint, payload)
                return
            except Exception:
                logger.exception("[mq.sender] primary endpoint delivery failed")
                if not self.backup_endpoint:
                    raise

        await self._deliver_to_endpoint(self.backup_endpoint, payload)

    async def close(self) -> None:
        await self._client.aclose()
