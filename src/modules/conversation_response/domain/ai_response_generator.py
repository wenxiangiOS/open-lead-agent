from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from src.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


@dataclass
class AIResponseResult:
    content: str
    failure_reason: str | None = None


class AIResponseGenerator:
    """负责执行最终模型生成调用，承接已装配完成的 prompt。"""

    def __init__(self, *, ai_service: Any) -> None:
        self.ai_service = ai_service

    async def generate(
        self,
        *,
        prompt: str,
        account_id: str,
        user_message: str,
        model_name: str,
        max_tokens: int,
        system_prompt: str = "你是一个说中文的AI助手，请用中文回复用户。",
        soft_timeout: float | None = None,
        hard_timeout: float | None = None,
        temperature: float | None = None,
    ) -> AIResponseResult:
        ai_start_time = time.perf_counter()

        resolved_soft_timeout = soft_timeout
        resolved_hard_timeout = hard_timeout
        if resolved_soft_timeout is None or resolved_hard_timeout is None:
            if hasattr(self.ai_service, "resolve_timeout_settings"):
                timeout_settings = self.ai_service.resolve_timeout_settings()
                resolved_soft_timeout = max(0.5, float(timeout_settings["chat_ai_timeout"]))
                resolved_hard_timeout = float(timeout_settings["chat_ai_hard_timeout"])
            else:
                resolved_soft_timeout = max(0.5, float(os.getenv("CHAT_AI_TIMEOUT_SECONDS", "12")))
                resolved_hard_timeout = float(
                    os.getenv("CHAT_AI_HARD_TIMEOUT_SECONDS", str(max(resolved_soft_timeout + 0.5, 15.0)))
                )
        assert resolved_soft_timeout is not None
        assert resolved_hard_timeout is not None

        logger.info(
            f"[⏱️ 性能] 开始调用AI: account_id={account_id}, model={model_name}, prompt_chars={len(prompt) if prompt else 0}, max_tokens={max_tokens}, soft_timeout={resolved_soft_timeout:.1f}s, hard_timeout={resolved_hard_timeout:.1f}s"
        )

        try:
            request_kwargs: dict[str, Any] = {
                "message": prompt,
                "system_prompt": system_prompt,
                "max_tokens": max_tokens,
                "timeout": resolved_soft_timeout,
                "model_name": model_name,
            }
            if temperature is not None:
                request_kwargs["temperature"] = temperature
            response = await asyncio.wait_for(
                self.ai_service.generate_response(**request_kwargs),
                timeout=resolved_hard_timeout,
            )
            ai_end_time = time.perf_counter()
            ai_duration = ai_end_time - ai_start_time
            logger.info(f"[⏱️ 性能] AI调用完成: account_id={account_id}, 耗时={ai_duration:.3f}秒")
            return AIResponseResult(content=response or "", failure_reason=None)
        except asyncio.TimeoutError:
            logger.error(f"[AI调用] 总时长触发硬超时: account_id={account_id}, hard_timeout={resolved_hard_timeout:.1f}s，返回空响应")
            return AIResponseResult(content="", failure_reason="hard_timeout")
        except AIServiceException as e:
            logger.error(f"[AI调用] 失败: {e}，返回空响应")
            details = getattr(e, "details", {}) or {}
            status_code = details.get("status_code")
            reason = "ai_service_error"
            msg = str(e or "")
            if status_code == 403 or "AccountOverdueError" in msg:
                reason = "account_overdue_403"
            elif status_code and 400 <= int(status_code) < 500:
                reason = f"client_error_{int(status_code)}"
            return AIResponseResult(content="", failure_reason=reason)
        except Exception as e:
            logger.error(f"[AI调用] 未预期的错误: {e}，返回空响应")
            return AIResponseResult(content="", failure_reason="unexpected_error")
