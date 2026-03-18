from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid
from dataclasses import asdict
from typing import Dict, List, Optional

from src.config.settings import settings
from src.services.data.redis_service import redis_service
from src.services.queue.message_models import (
    EnqueueResult,
    IncomingMessage,
    OutboxJob,
    QueueSession,
    TurnContext,
    SESSION_DEBOUNCING,
    SESSION_IDLE,
    SESSION_RUNNING,
)

logger = logging.getLogger(__name__)

FUNNEL_METRICS = [
    "ingest_total",
    "ingest_invalid_payload",
    "ingest_ignored_empty",
    "ingest_accepted",
    "ingest_duplicate",
    "ingest_queue_full",
    "turn_started",
    "turn_succeeded",
    "turn_failed",
    "turn_stale",
    "empty_response_business_silent",
    "empty_response_error",
    "outbox_created",
    "outbox_delivery_success",
    "outbox_delivery_retry",
    "outbox_delivery_drop",
]


class QueueStore:
    def __init__(self):
        self._memory_sessions: Dict[str, QueueSession] = {}
        self._memory_seq: Dict[str, int] = {}
        self._memory_msgs: Dict[str, Dict[int, dict]] = {}
        self._memory_ready: Dict[str, int] = {}
        self._memory_outbox: Dict[str, OutboxJob] = {}
        self._memory_outbox_ready: Dict[str, int] = {}
        self._memory_dedupe: Dict[str, int] = {}
        self._memory_metrics: Dict[str, int] = {}
        self._memory_delivered: Dict[str, List[dict]] = {}

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _cfg(name: str, default):
        value = getattr(settings, name, None)
        if value is not None:
            return value

        env_name = name.upper()
        raw = os.getenv(env_name)
        if raw is None:
            return default

        if isinstance(default, bool):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(default, int):
            try:
                return int(raw.strip())
            except ValueError:
                return default
        if isinstance(default, float):
            try:
                return float(raw.strip())
            except ValueError:
                return default
        return raw

    def _session_ttl(self) -> int:
        return int(self._cfg("mq_session_ttl_seconds", 604800))

    def _dedupe_ttl(self) -> int:
        return int(self._cfg("mq_dedupe_ttl_seconds", 86400))

    @staticmethod
    def _metric_key(name: str) -> str:
        return f"mq:metrics:{name}"

    async def incr_metric(self, name: str, value: int = 1) -> None:
        client = await self._get_client()
        if client is None:
            self._memory_metrics[name] = self._memory_metrics.get(name, 0) + value
            return
        key = self._key(self._metric_key(name))
        await client.incrby(key, value)
        await client.expire(key, self._session_ttl())

    async def _get_client(self):
        if not redis_service.is_enabled():
            return None
        try:
            if not redis_service.is_healthy():
                ok = await redis_service.ensure_connection()
                if not ok:
                    return None
            await redis_service._ensure_initialized()  # noqa: SLF001
            if not redis_service.is_healthy():
                return None
            return redis_service.client
        except Exception:
            logger.warning("queue store redis unavailable, fallback to memory", exc_info=True)
            return None

    def _key(self, key: str) -> str:
        return redis_service._key(key)  # noqa: SLF001

    def _default_session(self, account_id: str, now_ms: Optional[int] = None) -> QueueSession:
        return QueueSession(account_id=account_id, updated_at_ms=now_ms or self._now_ms())

    def _to_session(self, account_id: str, raw: Optional[dict], now_ms: Optional[int] = None) -> QueueSession:
        if not raw:
            return self._default_session(account_id, now_ms)
        return QueueSession(
            account_id=account_id,
            version=int(raw.get("version", 1)),
            state=raw.get("state", SESSION_IDLE),
            generation=int(raw.get("generation", 0)),
            debounce_until_ms=int(raw.get("debounce_until_ms", 0)),
            first_enqueue_at_ms=int(raw.get("first_enqueue_at_ms", 0)),
            last_consumed_seq=int(raw.get("last_consumed_seq", 0)),
            max_enqueued_seq=int(raw.get("max_enqueued_seq", 0)),
            active_turn_id=raw.get("active_turn_id", ""),
            dirty=bool(raw.get("dirty", False)),
            fail_streak=int(raw.get("fail_streak", 0)),
            updated_at_ms=int(raw.get("updated_at_ms", now_ms or self._now_ms())),
        )

    async def enqueue_message(self, msg: IncomingMessage, now_ms: int) -> EnqueueResult:
        client = await self._get_client()
        if client is None:
            return self._enqueue_memory(msg, now_ms)

        dedupe_key = self._key(f"mq:dedupe:{msg.account_id}:{msg.platform_msg_id}")
        seq_key = self._key(f"mq:seq:{msg.account_id}")
        msg_prefix = self._key(f"mq:msg:{msg.account_id}:")
        session_key = self._key(f"mq:session:{msg.account_id}")
        ready_key = self._key("mq:ready_users")

        payload = {
            "content": msg.content,
            "dialog_id": msg.dialog_id,
            "timestamp": msg.timestamp,
            "sex": msg.sex,
            "platform_msg_id": msg.platform_msg_id,
            "cancel_like": msg.cancel_like,
            "force_flush": msg.force_flush,
            "arrived_at_ms": now_ms,
        }

        script = """
        local dedupe_key = KEYS[1]
        local seq_key = KEYS[2]
        local msg_prefix = KEYS[3]
        local session_key = KEYS[4]
        local ready_key = KEYS[5]

        local now_ms = tonumber(ARGV[1])
        local msg_json = ARGV[2]
        local dedupe_ttl = tonumber(ARGV[3])
        local session_ttl = tonumber(ARGV[4])
        local debounce_ms = tonumber(ARGV[5])
        local append_ms = tonumber(ARGV[6])
        local max_ms = tonumber(ARGV[7])
        local recheck_ms = tonumber(ARGV[8])
        local cancel_like = tonumber(ARGV[9])
        local force_flush = tonumber(ARGV[10])
        local account_id = ARGV[11]
        local max_pending = tonumber(ARGV[12])
        local priority_boost = tonumber(ARGV[13])
        local adaptive_enabled = tonumber(ARGV[14])

        if redis.call('EXISTS', dedupe_key) == 1 then
            local session_raw = redis.call('GET', session_key)
            local state = 'IDLE'
            if session_raw then
                local s = cjson.decode(session_raw)
                state = s['state'] or 'IDLE'
            end
            return {0, state, 0, 0}
        end

        local raw = redis.call('GET', session_key)
        local s
        if raw then
            s = cjson.decode(raw)
        else
            s = {
                account_id = account_id,
                version = 1,
                state = 'IDLE',
                generation = 0,
                debounce_until_ms = 0,
                first_enqueue_at_ms = 0,
                last_consumed_seq = 0,
                max_enqueued_seq = 0,
                active_turn_id = '',
                dirty = false,
                fail_streak = 0,
                updated_at_ms = now_ms
            }
        end

        local pending = (tonumber(s['max_enqueued_seq']) or 0) - (tonumber(s['last_consumed_seq']) or 0)
        if pending < 0 then
            pending = 0
        end
        if pending >= max_pending then
            return {2, s['state'] or 'IDLE', 0, pending}
        end

        redis.call('SETEX', dedupe_key, dedupe_ttl, '1')
        local seq = redis.call('INCR', seq_key)
        redis.call('EXPIRE', seq_key, session_ttl)

        local msg_key = msg_prefix .. tostring(seq)
        redis.call('SETEX', msg_key, session_ttl, msg_json)

        if cancel_like == 1 then
            s['generation'] = (tonumber(s['generation']) or 0) + 1
        end

        local state = s['state'] or 'IDLE'
        if state == 'IDLE' then
            s['state'] = 'DEBOUNCING'
            s['first_enqueue_at_ms'] = now_ms
            if force_flush == 1 then
                s['debounce_until_ms'] = now_ms
            else
                local debounce_ms_eff = debounce_ms
                if adaptive_enabled == 1 then
                    local last_updated = tonumber(s['updated_at_ms']) or now_ms
                    local gap = now_ms - last_updated
                    if gap > 0 and gap < 2000 then
                        debounce_ms_eff = math.max(300, math.floor(gap * 0.6))
                        if debounce_ms_eff > debounce_ms then
                            debounce_ms_eff = debounce_ms
                        end
                    end
                end
                s['debounce_until_ms'] = now_ms + debounce_ms_eff
            end
        elseif state == 'DEBOUNCING' then
            local first_at = tonumber(s['first_enqueue_at_ms']) or 0
            if first_at <= 0 then
                first_at = now_ms
                s['first_enqueue_at_ms'] = first_at
            end
            if force_flush == 1 then
                s['debounce_until_ms'] = now_ms
            else
                local current_deadline = tonumber(s['debounce_until_ms']) or 0
                local candidate = now_ms + append_ms
                local new_deadline = current_deadline
                if candidate > new_deadline then
                    new_deadline = candidate
                end
                local max_deadline = first_at + max_ms
                if new_deadline > max_deadline then
                    new_deadline = max_deadline
                end
                s['debounce_until_ms'] = new_deadline
            end
        elseif state == 'RUNNING' then
            s['dirty'] = true
            local running_score = now_ms + recheck_ms
            if cancel_like == 1 or force_flush == 1 then
                running_score = running_score - priority_boost
            end
            redis.call('ZADD', ready_key, running_score, account_id)
        end

        s['max_enqueued_seq'] = seq
        s['updated_at_ms'] = now_ms

        redis.call('SETEX', session_key, session_ttl, cjson.encode(s))

        if s['state'] == 'DEBOUNCING' then
            local schedule_score = tonumber(s['debounce_until_ms']) or now_ms
            if cancel_like == 1 or force_flush == 1 then
                schedule_score = schedule_score - priority_boost
            end
            redis.call('ZADD', ready_key, schedule_score, account_id)
        end

        local new_pending = (tonumber(s['max_enqueued_seq']) or 0) - (tonumber(s['last_consumed_seq']) or 0)
        if new_pending < 0 then
            new_pending = 0
        end
        return {1, s['state'], seq, new_pending}
        """

        ret = await client.eval(
            script,
            5,
            dedupe_key,
            seq_key,
            msg_prefix,
            session_key,
            ready_key,
            now_ms,
            json.dumps(payload, ensure_ascii=False),
            self._dedupe_ttl(),
            self._session_ttl(),
            int(self._cfg("mq_debounce_ms", 300)),
            int(self._cfg("mq_debounce_append_ms", 200)),
            int(self._cfg("mq_debounce_max_ms", 1200)),
            int(self._cfg("mq_running_recheck_ms", 300)),
            1 if msg.cancel_like else 0,
            1 if msg.force_flush else 0,
            msg.account_id,
            int(self._cfg("mq_max_pending_messages", 20)),
            int(self._cfg("mq_priority_boost_ms", 200)),
            1 if bool(self._cfg("mq_adaptive_debounce_enabled", False)) else 0,
        )

        code = int(ret[0])
        accepted = code == 1
        state = str(ret[1])
        seq = int(ret[2])
        pending = int(ret[3]) if len(ret) > 3 else 0
        status = "queued" if code == 1 else ("duplicate" if code == 0 else "queue_full")
        if code == 2:
            await self.incr_metric("queue_full_count")

        return EnqueueResult(
            accepted=accepted,
            duplicate=code == 0,
            session_state=state,
            seq=seq,
            status=status,
            pending=pending,
        )

    def _enqueue_memory(self, msg: IncomingMessage, now_ms: int) -> EnqueueResult:
        dedupe_expire = now_ms + self._dedupe_ttl() * 1000
        dedupe_key = f"{msg.account_id}:{msg.platform_msg_id}"
        if self._memory_dedupe.get(dedupe_key, 0) > now_ms:
            session = self._memory_sessions.get(msg.account_id, self._default_session(msg.account_id, now_ms))
            return EnqueueResult(False, True, session.state, 0, status="duplicate", pending=0)
        self._memory_dedupe[dedupe_key] = dedupe_expire

        session = self._memory_sessions.get(msg.account_id, self._default_session(msg.account_id, now_ms))
        pending = max(0, session.max_enqueued_seq - session.last_consumed_seq)
        max_pending = int(self._cfg("mq_max_pending_messages", 20))
        if pending >= max_pending:
            self._memory_metrics["queue_full_count"] = self._memory_metrics.get("queue_full_count", 0) + 1
            return EnqueueResult(False, False, session.state, 0, status="queue_full", pending=pending)

        seq = self._memory_seq.get(msg.account_id, 0) + 1
        self._memory_seq[msg.account_id] = seq

        self._memory_msgs.setdefault(msg.account_id, {})[seq] = {
            "content": msg.content,
            "dialog_id": msg.dialog_id,
            "timestamp": msg.timestamp,
            "sex": msg.sex,
            "platform_msg_id": msg.platform_msg_id,
            "cancel_like": msg.cancel_like,
            "force_flush": msg.force_flush,
            "arrived_at_ms": now_ms,
        }

        prev_updated_at_ms = int(session.updated_at_ms or 0)
        if msg.cancel_like:
            session.generation += 1
        session.max_enqueued_seq = seq

        if session.state == SESSION_IDLE:
            session.state = SESSION_DEBOUNCING
            session.first_enqueue_at_ms = now_ms
            if msg.force_flush:
                session.debounce_until_ms = now_ms
            else:
                debounce_ms = int(self._cfg("mq_debounce_ms", 300))
                if bool(self._cfg("mq_adaptive_debounce_enabled", False)):
                    base_ts = prev_updated_at_ms if prev_updated_at_ms > 0 else now_ms
                    gap = max(0, now_ms - base_ts)
                    if 0 < gap < 2000:
                        debounce_ms = max(300, min(debounce_ms, int(gap * 0.6)))
                session.debounce_until_ms = now_ms + debounce_ms
        elif session.state == SESSION_DEBOUNCING:
            if msg.force_flush:
                session.debounce_until_ms = now_ms
            else:
                candidate = now_ms + int(self._cfg("mq_debounce_append_ms", 200))
                max_deadline = session.first_enqueue_at_ms + int(self._cfg("mq_debounce_max_ms", 1200))
                session.debounce_until_ms = min(max(session.debounce_until_ms, candidate), max_deadline)
        elif session.state == SESSION_RUNNING:
            session.dirty = True

        session.updated_at_ms = now_ms
        self._memory_sessions[msg.account_id] = session
        score = session.debounce_until_ms if session.state == SESSION_DEBOUNCING else now_ms
        if msg.cancel_like or msg.force_flush:
            score -= int(self._cfg("mq_priority_boost_ms", 200))
        self._memory_ready[msg.account_id] = score

        pending = max(0, session.max_enqueued_seq - session.last_consumed_seq)
        return EnqueueResult(True, False, session.state, seq, status="queued", pending=pending)

    async def get_queue_metrics(self) -> Dict[str, int]:
        client = await self._get_client()
        if client is None:
            total_pending = 0
            running = 0
            debouncing = 0
            for session in self._memory_sessions.values():
                total_pending += max(0, session.max_enqueued_seq - session.last_consumed_seq)
                if session.state == SESSION_RUNNING:
                    running += 1
                elif session.state == SESSION_DEBOUNCING:
                    debouncing += 1
            metrics = {
                "pending_depth": total_pending,
                "running_sessions": running,
                "debouncing_sessions": debouncing,
                "ready_users": len(self._memory_ready),
                "outbox_ready": len(self._memory_outbox_ready),
                "invalid_timestamp_count": self._memory_metrics.get("invalid_timestamp_count", 0),
                "queue_full_count": self._memory_metrics.get("queue_full_count", 0),
                "stale_drop_count": self._memory_metrics.get("stale_drop_count", 0),
            }
            for name in FUNNEL_METRICS:
                metrics[name] = self._memory_metrics.get(name, 0)
            return metrics

        ready_users = await client.zcard(self._key("mq:ready_users"))
        outbox_ready = await client.zcard(self._key("mq:outbox:ready"))
        pending_depth = 0
        running = 0
        debouncing = 0
        pattern = self._key("mq:session:*")
        async for key in client.scan_iter(match=pattern, count=200):
            raw = await client.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            pending_depth += max(
                0,
                int(data.get("max_enqueued_seq", 0)) - int(data.get("last_consumed_seq", 0)),
            )
            state = data.get("state")
            if state == SESSION_RUNNING:
                running += 1
            elif state == SESSION_DEBOUNCING:
                debouncing += 1

        invalid_timestamp_count = int((await client.get(self._key(self._metric_key("invalid_timestamp_count")))) or 0)
        queue_full_count = int((await client.get(self._key(self._metric_key("queue_full_count")))) or 0)
        stale_drop_count = int((await client.get(self._key(self._metric_key("stale_drop_count")))) or 0)

        metrics = {
            "pending_depth": pending_depth,
            "running_sessions": running,
            "debouncing_sessions": debouncing,
            "ready_users": int(ready_users),
            "outbox_ready": int(outbox_ready),
            "invalid_timestamp_count": invalid_timestamp_count,
            "queue_full_count": queue_full_count,
            "stale_drop_count": stale_drop_count,
        }
        for name in FUNNEL_METRICS:
            metrics[name] = int((await client.get(self._key(self._metric_key(name)))) or 0)
        return metrics

    async def get_session(self, account_id: str) -> QueueSession:
        client = await self._get_client()
        now_ms = self._now_ms()
        if client is None:
            return self._memory_sessions.get(account_id, self._default_session(account_id, now_ms))

        raw = await client.get(self._key(f"mq:session:{account_id}"))
        session_dict = json.loads(raw) if raw else None
        return self._to_session(account_id, session_dict, now_ms)

    async def save_session(self, session: QueueSession) -> None:
        client = await self._get_client()
        if client is None:
            self._memory_sessions[session.account_id] = session
            return
        await client.setex(
            self._key(f"mq:session:{session.account_id}"),
            self._session_ttl(),
            json.dumps(asdict(session), ensure_ascii=False),
        )

    def _with_jitter(self, run_at_ms: int) -> int:
        jitter_ms = int(self._cfg("mq_schedule_jitter_ms", 0))
        if jitter_ms <= 0:
            return run_at_ms
        now_ms = self._now_ms()
        if run_at_ms <= now_ms:
            return run_at_ms
        return run_at_ms + random.randint(0, jitter_ms)

    async def schedule_user(self, account_id: str, run_at_ms: int) -> None:
        run_at_ms = self._with_jitter(run_at_ms)
        client = await self._get_client()
        if client is None:
            self._memory_ready[account_id] = run_at_ms
            return
        await client.zadd(self._key("mq:ready_users"), {account_id: run_at_ms})

    async def fetch_ready_users(self, now_ms: int, limit: int = 100) -> List[str]:
        client = await self._get_client()
        if client is None:
            ready = [uid for uid, score in self._memory_ready.items() if score <= now_ms]
            ready.sort(key=lambda uid: self._memory_ready[uid])
            selected = ready[:limit]
            for uid in selected:
                self._memory_ready.pop(uid, None)
            return selected

        key = self._key("mq:ready_users")
        script = """
        local key = KEYS[1]
        local now_ms = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local users = redis.call('ZRANGEBYSCORE', key, '-inf', now_ms, 'LIMIT', 0, limit)
        if #users > 0 then
            redis.call('ZREM', key, unpack(users))
        end
        return users
        """
        users = await client.eval(script, 1, key, now_ms, limit)
        return users or []

    async def acquire_user_lock(self, account_id: str, token: str, ttl_seconds: int) -> bool:
        client = await self._get_client()
        if client is None:
            return True
        key = self._key(f"lock:mq:user:{account_id}")
        return bool(await client.set(key, token, ex=ttl_seconds, nx=True))

    async def release_user_lock(self, account_id: str, token: str) -> None:
        client = await self._get_client()
        if client is None:
            return
        key = self._key(f"lock:mq:user:{account_id}")
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
        """
        await client.eval(script, 1, key, token)

    async def start_turn(self, account_id: str, now_ms: int) -> Optional[TurnContext]:
        session = await self.get_session(account_id)

        if session.state != SESSION_DEBOUNCING:
            return None

        if session.debounce_until_ms > now_ms:
            await self.schedule_user(account_id, session.debounce_until_ms)
            return None

        start_seq = session.last_consumed_seq + 1
        end_seq = session.max_enqueued_seq

        if start_seq > end_seq:
            session.state = SESSION_IDLE
            session.active_turn_id = ""
            session.debounce_until_ms = 0
            session.first_enqueue_at_ms = 0
            session.updated_at_ms = now_ms
            await self.save_session(session)
            return None

        turn_id = uuid.uuid4().hex
        session.state = SESSION_RUNNING
        session.active_turn_id = turn_id
        session.dirty = False
        session.fail_streak = 0
        session.updated_at_ms = now_ms
        await self.save_session(session)

        return TurnContext(
            turn_id=turn_id,
            account_id=account_id,
            generation=session.generation,
            start_seq=start_seq,
            end_seq=end_seq,
        )

    async def get_turn_messages(self, account_id: str, start_seq: int, end_seq: int) -> List[dict]:
        client = await self._get_client()
        out: List[dict] = []
        if client is None:
            msg_map = self._memory_msgs.get(account_id, {})
            for seq in range(start_seq, end_seq + 1):
                item = msg_map.get(seq)
                if item:
                    out.append(item)
            return out

        keys = [self._key(f"mq:msg:{account_id}:{seq}") for seq in range(start_seq, end_seq + 1)]
        values = await client.mget(keys)
        for raw in values:
            if raw:
                try:
                    out.append(json.loads(raw))
                except Exception:
                    logger.exception("invalid queue message payload", extra={"account_id": account_id})
        return out

    async def is_turn_stale(self, turn: TurnContext) -> bool:
        session = await self.get_session(turn.account_id)
        if session.generation != turn.generation:
            return True
        if session.active_turn_id != turn.turn_id:
            return True
        return False

    async def mark_turn_stale(self, account_id: str, turn: TurnContext, now_ms: int) -> None:
        await self.incr_metric("stale_drop_count")
        session = await self.get_session(account_id)
        session.last_consumed_seq = max(session.last_consumed_seq, turn.end_seq)
        session.active_turn_id = ""
        session.dirty = False
        session.fail_streak = 0
        session.updated_at_ms = now_ms

        if session.last_consumed_seq < session.max_enqueued_seq:
            session.state = SESSION_DEBOUNCING
            session.debounce_until_ms = now_ms + int(self._cfg("mq_running_recheck_ms", 300))
            session.first_enqueue_at_ms = now_ms
            await self.schedule_user(account_id, session.debounce_until_ms)
        else:
            session.state = SESSION_IDLE
            session.debounce_until_ms = 0
            session.first_enqueue_at_ms = 0

        await self.save_session(session)

    async def finish_turn_success(self, account_id: str, turn: TurnContext, now_ms: int, has_more: bool) -> None:
        session = await self.get_session(account_id)
        session.last_consumed_seq = max(session.last_consumed_seq, turn.end_seq)
        session.active_turn_id = ""
        session.dirty = False
        session.fail_streak = 0
        session.updated_at_ms = now_ms

        if has_more or session.last_consumed_seq < session.max_enqueued_seq:
            session.state = SESSION_DEBOUNCING
            session.debounce_until_ms = now_ms + int(self._cfg("mq_running_recheck_ms", 300))
            session.first_enqueue_at_ms = now_ms
            await self.schedule_user(account_id, session.debounce_until_ms)
        else:
            session.state = SESSION_IDLE
            session.debounce_until_ms = 0
            session.first_enqueue_at_ms = 0

        await self.save_session(session)

    async def mark_turn_failed(self, account_id: str, turn: TurnContext, now_ms: int) -> None:
        session = await self.get_session(account_id)
        session.active_turn_id = ""
        session.state = SESSION_DEBOUNCING
        session.dirty = True
        session.fail_streak = max(0, int(session.fail_streak)) + 1

        recheck_ms = int(self._cfg("mq_running_recheck_ms", 300))
        fail_threshold = int(self._cfg("mq_fail_streak_threshold", 3))
        cool_down_ms = int(self._cfg("mq_fail_streak_cooldown_ms", 5000))

        if session.fail_streak >= fail_threshold:
            delay_ms = cool_down_ms * min(6, session.fail_streak - fail_threshold + 1)
        else:
            delay_ms = recheck_ms

        session.debounce_until_ms = now_ms + max(recheck_ms, delay_ms)
        session.first_enqueue_at_ms = now_ms
        session.updated_at_ms = now_ms
        await self.save_session(session)
        await self.schedule_user(account_id, session.debounce_until_ms)

    async def write_outbox(self, job: OutboxJob) -> None:
        client = await self._get_client()
        if client is None:
            self._memory_outbox[job.job_id] = job
            self._memory_outbox_ready[job.job_id] = job.next_retry_at_ms
            return

        await client.setex(
            self._key(f"mq:outbox:{job.job_id}"),
            self._session_ttl(),
            json.dumps(asdict(job), ensure_ascii=False),
        )
        await client.zadd(self._key("mq:outbox:ready"), {job.job_id: job.next_retry_at_ms})

    async def fetch_due_outbox_jobs(self, now_ms: int, limit: int = 100) -> List[OutboxJob]:
        client = await self._get_client()
        if client is None:
            due_ids = [job_id for job_id, score in self._memory_outbox_ready.items() if score <= now_ms]
            due_ids.sort(key=lambda job_id: self._memory_outbox_ready[job_id])
            selected = due_ids[:limit]
            jobs = []
            for job_id in selected:
                self._memory_outbox_ready.pop(job_id, None)
                job = self._memory_outbox.get(job_id)
                if job:
                    jobs.append(job)
            return jobs

        ready_key = self._key("mq:outbox:ready")
        claim_script = """
        local key = KEYS[1]
        local now_ms = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local ids = redis.call('ZRANGEBYSCORE', key, '-inf', now_ms, 'LIMIT', 0, limit)
        if #ids > 0 then
            redis.call('ZREM', key, unpack(ids))
        end
        return ids
        """
        ids = await client.eval(claim_script, 1, ready_key, now_ms, limit)
        if not ids:
            return []

        jobs: List[OutboxJob] = []
        values = await client.mget([self._key(f"mq:outbox:{job_id}") for job_id in ids])
        for raw in values:
            if not raw:
                continue
            try:
                item = json.loads(raw)
                jobs.append(OutboxJob(**item))
            except Exception:
                logger.exception("invalid outbox payload")
        return jobs

    async def mark_outbox_done(self, job_id: str) -> None:
        client = await self._get_client()
        if client is None:
            self._memory_outbox.pop(job_id, None)
            self._memory_outbox_ready.pop(job_id, None)
            return
        await client.delete(self._key(f"mq:outbox:{job_id}"))
        await client.zrem(self._key("mq:outbox:ready"), job_id)

    async def retry_outbox(self, job_id: str, retry_count: int, next_retry_at_ms: int, error: str) -> None:
        client = await self._get_client()
        if client is None:
            job = self._memory_outbox.get(job_id)
            if not job:
                return
            job.retry_count = retry_count
            job.next_retry_at_ms = next_retry_at_ms
            self._memory_outbox_ready[job_id] = next_retry_at_ms
            return

        key = self._key(f"mq:outbox:{job_id}")
        raw = await client.get(key)
        if not raw:
            return
        item = json.loads(raw)
        item["retry_count"] = retry_count
        item["next_retry_at_ms"] = next_retry_at_ms
        item["last_error"] = error
        await client.setex(key, self._session_ttl(), json.dumps(item, ensure_ascii=False))
        await client.zadd(self._key("mq:outbox:ready"), {job_id: next_retry_at_ms})

    async def append_delivered_reply(
        self,
        account_id: str,
        reply_text: str,
        dialog_id: Optional[str],
        turn_id: Optional[str],
        now_ms: int,
    ) -> int:
        client = await self._get_client()
        keep_max = int(self._cfg("mq_delivered_keep_max", 200))

        if client is None:
            bucket = self._memory_delivered.setdefault(account_id, [])
            last_id = int(bucket[-1]["id"]) if bucket else 0
            next_id = last_id + 1
            bucket.append(
                {
                    "id": next_id,
                    "accountId": account_id,
                    "message": reply_text,
                    "dialogId": dialog_id,
                    "turnId": turn_id,
                    "createdAtMs": now_ms,
                }
            )
            if len(bucket) > keep_max:
                self._memory_delivered[account_id] = bucket[-keep_max:]
            return next_id

        seq_key = self._key(f"mq:delivered:seq:{account_id}")
        idx_key = self._key(f"mq:delivered:idx:{account_id}")
        ttl = self._session_ttl()

        next_id = int(await client.incr(seq_key))
        await client.expire(seq_key, ttl)

        payload = {
            "id": next_id,
            "accountId": account_id,
            "message": reply_text,
            "dialogId": dialog_id,
            "turnId": turn_id,
            "createdAtMs": now_ms,
        }
        msg_key = self._key(f"mq:delivered:{account_id}:{next_id}")
        await client.setex(msg_key, ttl, json.dumps(payload, ensure_ascii=False))
        await client.zadd(idx_key, {str(next_id): next_id})
        await client.expire(idx_key, ttl)

        # Keep only newest keep_max receipts.
        over = await client.zcard(idx_key) - keep_max
        if over > 0:
            old_ids = await client.zrange(idx_key, 0, over - 1)
            if old_ids:
                old_keys = [self._key(f"mq:delivered:{account_id}:{oid}") for oid in old_ids]
                await client.delete(*old_keys)
                await client.zrem(idx_key, *old_ids)

        return next_id

    async def fetch_delivered_replies(self, account_id: str, after_id: int = 0, limit: int = 20) -> List[dict]:
        client = await self._get_client()
        safe_limit = max(1, min(limit, 100))
        if client is None:
            bucket = self._memory_delivered.get(account_id, [])
            return [item for item in bucket if int(item.get("id", 0)) > after_id][:safe_limit]

        idx_key = self._key(f"mq:delivered:idx:{account_id}")
        ids = await client.zrangebyscore(idx_key, min=after_id + 1, max="+inf", start=0, num=safe_limit)
        if not ids:
            return []
        keys = [self._key(f"mq:delivered:{account_id}:{oid}") for oid in ids]
        values = await client.mget(keys)

        replies: List[dict] = []
        for raw in values:
            if not raw:
                continue
            try:
                replies.append(json.loads(raw))
            except Exception:
                logger.exception("invalid delivered reply payload")
        return replies

    async def recover_stale_running_sessions(self, now_ms: int, stale_after_ms: int, limit: int = 200) -> int:
        client = await self._get_client()
        recovered = 0
        if client is None:
            for account_id, session in self._memory_sessions.items():
                if recovered >= limit:
                    break
                if session.state == SESSION_RUNNING and (now_ms - session.updated_at_ms) > stale_after_ms:
                    session.state = SESSION_DEBOUNCING
                    session.active_turn_id = ""
                    session.debounce_until_ms = now_ms + int(self._cfg("mq_running_recheck_ms", 300))
                    session.first_enqueue_at_ms = now_ms
                    recovered += 1
                    self._memory_ready[account_id] = session.debounce_until_ms
            return recovered

        pattern = self._key("mq:session:*")
        async for key in client.scan_iter(match=pattern, count=200):
            raw = await client.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("state") != SESSION_RUNNING:
                continue
            updated_at_ms = int(data.get("updated_at_ms", 0))
            if now_ms - updated_at_ms <= stale_after_ms:
                continue
            data["state"] = SESSION_DEBOUNCING
            data["active_turn_id"] = ""
            data["debounce_until_ms"] = now_ms + int(self._cfg("mq_running_recheck_ms", 300))
            data["first_enqueue_at_ms"] = now_ms
            data["updated_at_ms"] = now_ms
            await client.setex(key, self._session_ttl(), json.dumps(data, ensure_ascii=False))
            prefix = self._key("mq:session:")
            account_id = key[len(prefix):] if key.startswith(prefix) else key.rsplit(":", 1)[-1]
            await client.zadd(self._key("mq:ready_users"), {account_id: data["debounce_until_ms"]})
            recovered += 1

        return recovered
