from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.config.settings import settings
from src.models.requests import ChatRequest
from src.modules.shared.models.use_case_models import (
    IngestMessageCommand,
    IngestMessageResult,
    ProcessChatTurnCommand,
    ProcessChatTurnResult,
)
from src.services.core.chat_service import ChatService
from src.services.queue.intent_classifier import QueueIntentClassifier
from src.services.queue.message_models import IncomingMessage, OutboxJob
from src.services.queue.queue_store import QueueStore
from src.services.queue.turn_commit_service import TurnCommitService
from src.services.queue.turn_draft_models import TurnMutationSet
from src.services.queue.turn_sandbox import TurnSandbox

logger = logging.getLogger(__name__)


class MessageOrchestrator:
    def __init__(
        self,
        chat_service: ChatService,
        queue_store: Optional[QueueStore] = None,
        classifier: Optional[QueueIntentClassifier] = None,
        commit_service: Optional[TurnCommitService] = None,
    ) -> None:
        self.chat_service = chat_service
        self.queue_store = queue_store or QueueStore()
        self.classifier = classifier or QueueIntentClassifier()
        self.commit_service = commit_service
        if self.commit_service is None and hasattr(chat_service, "user_service"):
            self.commit_service = TurnCommitService(chat_service.user_service, self.queue_store)

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _normalize_timestamp(raw: Any) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None

        if text.isdigit():
            try:
                value = int(text)
                # 13位通常是毫秒时间戳，10位通常是秒级时间戳。
                if value >= 10**12:
                    dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
                else:
                    dt = datetime.fromtimestamp(value, tz=timezone.utc)
                return dt.isoformat()
            except Exception:
                return None

        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
            return text
        except Exception:
            return None

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _mq_force_flush_enabled(self) -> bool:
        value = getattr(settings, "mq_force_flush_enabled", None)
        if value is not None:
            return bool(value)
        return self._env_bool("MQ_FORCE_FLUSH_ENABLED", False)

    def _mq_pre_send_silence_ms(self) -> int:
        value = getattr(settings, "mq_pre_send_silence_ms", None)
        if value is not None:
            try:
                return max(0, int(value))
            except Exception:
                return 400
        raw = os.getenv("MQ_PRE_SEND_SILENCE_MS")
        if raw is None:
            return 400
        try:
            return max(0, int(raw.strip()))
        except Exception:
            return 400


    async def _incr_metric(self, name: str, value: int = 1) -> None:
        try:
            await self.queue_store.incr_metric(name, value)
        except Exception:
            logger.debug("[mq.metrics] incr failed", extra={"metric": name})

    async def _record_validation_metrics(self, result: ProcessChatTurnResult) -> None:
        payload = result.payload if isinstance(result.payload, dict) else {}
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        validation = meta.get("validation") if isinstance(meta.get("validation"), dict) else {}
        error_code = str(validation.get("error_code") or "").strip()
        if not error_code:
            return

        if error_code in {"CONTACT_INVALID_FORMAT", "WECHAT_INVALID_FORMAT"}:
            if validation.get("silent"):
                await self._incr_metric("contact_validation_silent")
            else:
                await self._incr_metric("contact_validation_retry")

    @staticmethod
    def _conversation_key(account_id: str, dialog_id: Optional[str]) -> str:
        return QueueStore.conversation_key(account_id, dialog_id)

    @staticmethod
    def _to_ingest_command(payload: dict | IngestMessageCommand) -> IngestMessageCommand:
        if isinstance(payload, IngestMessageCommand):
            return payload
        return IngestMessageCommand(
            account_id=str(payload.get("accountId") or "").strip(),
            dialog_id=payload.get("dialogId"),
            message=str(payload.get("message") or "").strip(),
            platform_msg_id=str(payload.get("platformMsgId") or "").strip(),
            timestamp=payload.get("timestamp"),
            sex=payload.get("sex"),
        )

    async def ingest_command(self, payload: dict | IngestMessageCommand) -> IngestMessageResult:
        result_payload = await self.ingest(payload)
        return IngestMessageResult(
            success=bool(result_payload.get("success", False)),
            accepted=bool(result_payload.get("accepted", False)),
            status=str(result_payload.get("status") or ""),
            session_state=result_payload.get("sessionState"),
            seq=int(result_payload.get("seq") or 0),
            pending=int(result_payload.get("pending") or 0),
            max_pending=int(result_payload.get("maxPending") or 0),
            cancel_like=bool(result_payload.get("cancelLike", False)),
            force_flush=bool(result_payload.get("forceFlush", False)),
            payload=result_payload,
        )

    async def ingest(self, payload: dict | IngestMessageCommand) -> dict:
        command = self._to_ingest_command(payload)
        await self._incr_metric("ingest_total")
        account_id = command.account_id
        content = command.message
        platform_msg_id = command.platform_msg_id

        if not account_id or not platform_msg_id:
            await self._incr_metric("ingest_invalid_payload")
            return {"success": True, "accepted": False, "status": "invalid_payload"}

        if not content:
            await self._incr_metric("ingest_ignored_empty")
            return {"success": True, "accepted": False, "status": "ignored_empty"}

        now_ms = self._now_ms()
        intent = self.classifier.classify(content)
        conversation_key = self._conversation_key(account_id, command.dialog_id)
        normalized_timestamp = self._normalize_timestamp(command.timestamp)
        if command.timestamp is not None and normalized_timestamp is None:
            logger.warning(
                "[mq.ingest] invalid timestamp ignored",
                extra={"account_id": account_id, "platform_msg_id": platform_msg_id},
            )
            await self._incr_metric("invalid_timestamp_count")

        incoming = IncomingMessage(
            account_id=account_id,
            conversation_key=conversation_key,
            dialog_id=command.dialog_id,
            content=content,
            platform_msg_id=platform_msg_id,
            timestamp=normalized_timestamp,
            sex=command.sex,
            cancel_like=bool(intent.get("cancel_like", False)),
            force_flush=bool(intent.get("force_flush", False))
            and self._mq_force_flush_enabled(),
        )

        result = await self.queue_store.enqueue_message(incoming, now_ms)
        status = result.status
        if status == "queued":
            await self._incr_metric("ingest_accepted")
        elif status == "duplicate":
            await self._incr_metric("ingest_duplicate")
        elif status == "queue_full":
            await self._incr_metric("ingest_queue_full")
        max_pending = int(getattr(settings, "mq_max_pending_messages", 20))

        return {
            "success": True,
            "accepted": bool(result.accepted),
            "status": status,
            "conversationKey": conversation_key,
            "sessionState": result.session_state,
            "seq": result.seq,
            "pending": result.pending,
            "maxPending": max_pending,
            "cancelLike": incoming.cancel_like,
            "forceFlush": incoming.force_flush,
        }

    async def run_user_turn(self, account_id: str) -> None:
        conversation_key = await self.queue_store.resolve_conversation_key(account_id)
        now_ms = self._now_ms()
        lock_token = uuid.uuid4().hex
        locked = await self.queue_store.acquire_user_lock(
            conversation_key,
            lock_token,
            ttl_seconds=180,
        )
        if not locked:
            return

        try:
            turn = await self.queue_store.start_turn(conversation_key, now_ms)
            if turn is None:
                return
            await self._incr_metric("turn_started")

            messages = await self.queue_store.get_turn_messages(conversation_key, turn.start_seq, turn.end_seq)
            combined_message = self.combine_messages(
                messages,
                max_chars=int(getattr(settings, "mq_max_combined_chars", 4000)),
                keep_last_message=True,
                compact_middle=bool(getattr(settings, "mq_context_compaction_enabled", False)),
            )

            if not combined_message:
                await self.queue_store.finish_turn_success(conversation_key, turn, self._now_ms(), has_more=False)
                await self._incr_metric("turn_succeeded")
                return

            latest_dialog = self._last_non_empty(messages, "dialog_id")
            latest_sex = self._last_non_empty(messages, "sex")
            latest_ts = self._last_non_empty(messages, "timestamp")

            if hasattr(self.chat_service, "user_service"):
                async with TurnSandbox(self.chat_service.user_service, turn.profile_key) as sandbox:
                    result = await self._process_turn_command(
                        ProcessChatTurnCommand(
                            question=combined_message,
                            account_id=turn.profile_key,
                            dialog_id=latest_dialog,
                            sex=latest_sex,
                            timestamp=latest_ts,
                        )
                    )
                    mutation_set = sandbox.collect_mutation_set()
            else:
                result = await self._process_turn_command(
                    ProcessChatTurnCommand(
                        question=combined_message,
                        account_id=turn.profile_key,
                        dialog_id=latest_dialog,
                        sex=latest_sex,
                        timestamp=latest_ts,
                    )
                )
                mutation_set = TurnMutationSet()

            await self._record_validation_metrics(result)
            response = result.response.strip()
            now_ms = self._now_ms()

            if await self.queue_store.is_turn_stale(turn):
                logger.info(
                    "[mq.turn] stale dropped",
                    extra={"conversation_key": conversation_key, "turn_id": turn.turn_id, "generation": turn.generation},
                )
                await self.queue_store.mark_turn_stale(conversation_key, turn, now_ms)
                await self._incr_metric("turn_stale")
                return

            if response:
                pre_send_silence_ms = self._mq_pre_send_silence_ms()
                job = OutboxJob(
                    job_id=uuid.uuid4().hex,
                    account_id=turn.profile_key,
                    conversation_key=conversation_key,
                    turn_id=turn.turn_id,
                    generation=turn.generation,
                    covered_end_seq=turn.end_seq,
                    reply_text=response,
                    dialog_id=result.dialog_id or latest_dialog,
                    retry_count=0,
                    next_retry_at_ms=now_ms + max(0, pre_send_silence_ms),
                    mutation_set=TurnSandbox.serialize_mutation_set(mutation_set),
                )
                await self.queue_store.write_outbox(job)
                await self._incr_metric("outbox_created")
                session = await self.queue_store.get_session(conversation_key)
                has_more = int(session.max_enqueued_seq) > int(turn.end_seq) or bool(session.dirty)
                await self.queue_store.finish_turn_success(conversation_key, turn, now_ms, has_more=has_more)
                await self._incr_metric("turn_succeeded")
                return

            if result.success:
                # silent 分支没有 sender 二次闸门，提交前必须再次做 latest-wins 复核，
                # 避免该轮在“首检通过后”被新输入覆盖却仍提交业务状态。
                if await self.queue_store.is_turn_stale(turn):
                    await self.queue_store.mark_turn_stale(conversation_key, turn, now_ms)
                    await self._incr_metric("turn_stale")
                    return

                if self.commit_service is not None:
                    committed = await self.commit_service.commit_turn(turn.turn_id, turn.profile_key, mutation_set)
                    if not committed:
                        await self.queue_store.mark_turn_failed(conversation_key, turn, now_ms)
                        await self._incr_metric("turn_failed")
                        return

                silent_job = OutboxJob(
                    job_id=f"silent:{turn.turn_id}",
                    account_id=turn.profile_key,
                    conversation_key=conversation_key,
                    turn_id=turn.turn_id,
                    generation=turn.generation,
                    covered_end_seq=turn.end_seq,
                    reply_text="",
                    dialog_id=result.dialog_id or latest_dialog,
                    retry_count=0,
                    next_retry_at_ms=now_ms,
                    mutation_set=TurnSandbox.serialize_mutation_set(mutation_set),
                )
                finalized = await self.queue_store.finalize_turn_commit(silent_job, now_ms)
                if not finalized:
                    await self.queue_store.mark_turn_stale(conversation_key, turn, now_ms)
                    await self._incr_metric("turn_stale")
                    return

                await self._incr_metric("empty_response_business_silent")
                session = await self.queue_store.get_session(conversation_key)
                ack_seq = int(session.last_ack_seq)
                has_more = int(session.max_enqueued_seq) > ack_seq or bool(session.dirty)
                await self.queue_store.finish_turn_success(conversation_key, turn, now_ms, has_more=has_more)
                await self._incr_metric("turn_succeeded")
                return

            await self._incr_metric("empty_response_error")
            await self.queue_store.mark_turn_failed(conversation_key, turn, now_ms)
            await self._incr_metric("turn_failed")
            return

        except Exception:
            logger.exception("[mq.turn] run_user_turn failed", extra={"conversation_key": conversation_key})
            now_ms = self._now_ms()
            try:
                if "turn" in locals() and turn is not None:
                    await self.queue_store.mark_turn_failed(conversation_key, turn, now_ms)
                    await self._incr_metric("turn_failed")
            except Exception:
                logger.exception("[mq.turn] mark_turn_failed failed", extra={"conversation_key": conversation_key})
        finally:
            await self.queue_store.release_user_lock(conversation_key, lock_token)

    @staticmethod
    def _last_non_empty(messages: List[dict], field: str) -> Optional[str]:
        for item in reversed(messages):
            value = item.get(field)
            if value:
                return value
        return None

    async def _process_turn_command(self, command: ProcessChatTurnCommand):
        normalized_timestamp = self._normalize_timestamp(command.timestamp)
        use_case = getattr(self.chat_service, "process_chat_turn_use_case", None)
        if use_case is not None and hasattr(use_case, "execute_command"):
            safe_command = ProcessChatTurnCommand(
                question=command.question,
                account_id=command.account_id,
                dialog_id=command.dialog_id,
                sex=command.sex,
                timestamp=normalized_timestamp,
            )
            return await use_case.execute_command(safe_command)

        chat_request = ChatRequest(
            question=command.question,
            accountId=command.account_id,
            dialogId=command.dialog_id,
            sex=command.sex,
            timestamp=normalized_timestamp,
        )
        payload = await self.chat_service.process_chat_request(chat_request)
        return ProcessChatTurnResult(
            success=bool(payload.get("success", False)),
            response=str(payload.get("response") or ""),
            dialog_id=payload.get("dialogId"),
            payload=payload,
        )

    @staticmethod
    def combine_messages(
        messages: List[dict],
        max_chars: int,
        keep_last_message: bool = True,
        compact_middle: bool = False,
    ) -> str:
        contents = [((m.get("content") or "").strip()) for m in messages]
        contents = [c for c in contents if c]
        if not contents:
            return ""

        parts: List[str] = []
        total = 0
        for content in contents:
            candidate = total + (1 if parts else 0) + len(content)
            if candidate > max_chars:
                break
            parts.append(content)
            total = candidate

        if keep_last_message and contents:
            last = contents[-1]
            joined = "\n".join(parts)
            if last not in parts:
                if len(last) >= max_chars:
                    return last[-max_chars:]

                if compact_middle and len(contents) >= 3:
                    head = contents[0]
                    omitted = max(0, len(contents) - 2)
                    compact_text = f"{head}\n[省略{omitted}条历史消息]\n{last}"
                    if len(compact_text) <= max_chars:
                        return compact_text

                remaining = max_chars - len(last)
                prefix = joined[: max(0, remaining - 1)].rstrip()
                if prefix:
                    return f"{prefix}\n{last}"
                return last

        return "\n".join(parts)
