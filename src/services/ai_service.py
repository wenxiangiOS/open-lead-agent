"""AI service for Doubao integration"""
"""调用豆包 API，生成回复、情感分析、关键词提取、意图分类"""

import logging
import asyncio
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from src.config.settings import settings
from src.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


class AIService:
    """
    AI 服务 - 豆包模型调用

    特性：
    1. 超时控制 - 所有操作都有超时保护
    2. 自动重试 - 网络错误时自动重试
    3. 连接池管理 - 支持高并发
    4. Token 统计 - 记录使用情况（线程安全）
    """

    # 类级别的token统计
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    call_count = 0

    # 保护 token 统计的锁
    _token_lock = asyncio.Lock()

    # 超时配置（秒）
    DEFAULT_TIMEOUT = 30
    CONNECT_TIMEOUT = 10

    @staticmethod
    def _env_flag(name: str, default: bool = False) -> bool:
        raw = str(os.getenv(name, str(default))).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(str(os.getenv(name, default)).strip())
        except (TypeError, ValueError):
            return default

    @classmethod
    def resolve_timeout_settings(cls) -> Dict[str, float]:
        """统一解析 AI 相关超时，允许主配置驱动、其余自动推导。"""
        base_timeout = float(os.getenv("CHAT_AI_TIMEOUT_SECONDS", "45"))
        if base_timeout <= 0:
            base_timeout = 45.0

        http_total_timeout = float(
            os.getenv("AI_HTTP_TOTAL_TIMEOUT_SECONDS", str(base_timeout + 5.0))
        )
        if http_total_timeout < base_timeout:
            http_total_timeout = base_timeout + 5.0

        hard_timeout = float(
            os.getenv("CHAT_AI_HARD_TIMEOUT_SECONDS", str(base_timeout + 10.0))
        )
        if hard_timeout <= http_total_timeout:
            hard_timeout = http_total_timeout + 5.0

        request_timeout = float(
            os.getenv("CONCURRENCY_REQUEST_TIMEOUT", str(hard_timeout + 10.0))
        )
        if request_timeout <= hard_timeout:
            request_timeout = hard_timeout + 10.0

        return {
            "chat_ai_timeout": base_timeout,
            "http_total_timeout": http_total_timeout,
            "chat_ai_hard_timeout": hard_timeout,
            "request_timeout": request_timeout,
        }

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        """Initialize AI service"""
        self._owns_client = client is None
        self.client = client or self._create_async_openai_client()
        self.model_name = settings.model_name

    def _create_async_openai_client(self) -> AsyncOpenAI:
        """创建新的异步 OpenAI 客户端，用于初始化和超时后重建。"""
        timeout = self.resolve_timeout_settings()["http_total_timeout"]
        return AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=timeout,
            max_retries=0,
        )

    async def _reset_client(self, reason: str) -> None:
        """
        超时/连接异常后重建底层客户端，避免复用坏掉的 keep-alive 连接。
        仅对本服务自行创建的客户端生效。
        """
        if not self._owns_client:
            return
        old_client = self.client
        self.client = self._create_async_openai_client()
        try:
            await old_client.close()
        except Exception as exc:
            logger.warning(f"关闭旧 AI 客户端失败({reason}): {exc}")
        logger.warning(f"AI 客户端已重建，原因: {reason}")

    async def generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: Optional[float] = None,
        model_name: Optional[str] = None,
        disable_retry: bool = False,
        use_max_completion_tokens: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        """
        生成 AI 回复（带超时控制）

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒），默认使用 DEFAULT_TIMEOUT

        Returns:
            str: AI 回复内容

        Raises:
            AIServiceException: AI 服务调用失败
            asyncio.TimeoutError: 调用超时
        """
        timeout = timeout or self.resolve_timeout_settings()["chat_ai_timeout"]
        # 在线对话链路默认快失败：减少长尾阻塞
        max_retries = int(os.getenv("AI_CHAT_MAX_RETRIES", "1"))
        if max_retries < 1:
            max_retries = 1
        if disable_retry:
            max_retries = 1
        retry_delay = float(os.getenv("AI_CHAT_RETRY_DELAY_SECONDS", "0.5"))
        effective_retry_count = max(0, max_retries - 1)

        last_error = None
        for attempt in range(max_retries):
            try:
                attempt_started_at = time.monotonic()
                async with asyncio.timeout(timeout):
                    return await self._do_generate_response(
                        message,
                        system_prompt,
                        temperature,
                        max_tokens,
                        model_name,
                        use_max_completion_tokens=use_max_completion_tokens,
                        reasoning_effort=reasoning_effort,
                        attempt_timeout_seconds=timeout,
                        attempt_started_at=attempt_started_at,
                    )
            except asyncio.TimeoutError as e:
                last_error = e
                await self._reset_client("generate_response_timeout")
                if attempt < max_retries - 1:
                    logger.warning(f"AI 调用超时（{timeout}秒），第 {attempt + 1} 次重试...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    if effective_retry_count > 0:
                        logger.error(f"AI 调用超时（{timeout}秒），已重试 {effective_retry_count} 次")
                    else:
                        logger.error(f"AI 调用超时（{timeout}秒），未重试")
            except Exception as e:
                last_error = e
                status_code = self._extract_status_code(e)
                cause = getattr(e, "__cause__", None)
                context = getattr(e, "__context__", None)
                logger.warning(
                    "AI 调用异常详情: type=%s repr=%r cause_type=%s cause=%r context_type=%s context=%r",
                    type(e).__name__,
                    e,
                    type(cause).__name__ if cause else "-",
                    cause,
                    type(context).__name__ if context else "-",
                    context,
                )
                if self._is_non_retryable_client_error(e):
                    logger.error(
                        "AI 调用失败(非重试错误): %s (status=%s)",
                        e,
                        status_code if status_code is not None else "unknown",
                    )
                    break

                if self._is_empty_response_exception(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"AI 调用返回空响应，第 {attempt + 1} 次重试...")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.error(f"AI 调用失败: {e}")
                    continue

                await self._reset_client(f"generate_response_error:{type(e).__name__}")
                if attempt < max_retries - 1:
                    logger.warning(f"AI 调用失败: {e}，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"AI 调用失败: {e}")

        if isinstance(last_error, asyncio.TimeoutError):
            if effective_retry_count > 0:
                raise AIServiceException(f"AI 服务响应超时（{timeout}秒），已重试 {effective_retry_count} 次")
            raise AIServiceException(f"AI 服务响应超时（{timeout}秒），未重试")
        if last_error is not None:
            raise AIServiceException(
                f"AI 服务错误: {str(last_error)}",
                details={
                    "status_code": self._extract_status_code(last_error),
                    "retryable": not self._is_non_retryable_client_error(last_error),
                },
            )
        raise AIServiceException("AI 服务调用失败")

    @staticmethod
    def _extract_status_code(exc: Exception) -> Optional[int]:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            return response_status
        return None

    def _is_non_retryable_client_error(self, exc: Exception) -> bool:
        status_code = self._extract_status_code(exc)
        if status_code is not None:
            return 400 <= status_code < 500

        text = str(exc or "").lower()
        if "error code: 4" in text:
            return True
        if "forbidden" in text or "unauthorized" in text:
            return True
        if "accountoverdueerror" in text:
            return True
        return False

    @staticmethod
    def _is_empty_response_exception(exc: Exception) -> bool:
        if not isinstance(exc, AIServiceException):
            return False
        details = getattr(exc, "details", {}) or {}
        return str(details.get("reason") or "").strip() == "empty_response"

    async def _do_generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        model_name: Optional[str] = None,
        use_max_completion_tokens: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        attempt_timeout_seconds: Optional[float] = None,
        attempt_started_at: Optional[float] = None,
    ) -> str:
        """实际执行 AI 调用"""
        # Create messages
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": message
            }
        ]

        request_kwargs: Dict[str, Any] = {
            "model": model_name or self.model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        requested_token_param = "max_tokens"
        if use_max_completion_tokens:
            request_kwargs["max_completion_tokens"] = max_tokens
            requested_token_param = "max_completion_tokens"
        else:
            request_kwargs["max_tokens"] = max_tokens
        normalized_reasoning_effort = str(reasoning_effort or "").strip().lower()
        if normalized_reasoning_effort:
            request_kwargs["reasoning_effort"] = normalized_reasoning_effort

        response = await self._create_chat_completion_with_compat_fallback(
            request_kwargs=request_kwargs,
            requested_token_param=requested_token_param,
        )

        content = self._extract_response_text(response)
        if not content and self._should_retry_empty_response_with_token_fallback(
            response=response,
            requested_token_param=requested_token_param,
        ):
            remaining_budget = self._remaining_attempt_budget(
                timeout_seconds=attempt_timeout_seconds,
                started_at=attempt_started_at,
            )
            fallback_timeout = self._resolve_empty_response_fallback_timeout(remaining_budget)
            if fallback_timeout is None:
                logger.warning(
                    "[AI空响应兼容降级] skipped: insufficient_budget remaining=%.2fs requested_token_param=%s",
                    remaining_budget,
                    requested_token_param,
                )
            else:
                logger.warning(
                    "[AI空响应兼容降级] finish_reason=length requested_token_param=%s retry_with=max_tokens timeout=%.2fs",
                    requested_token_param,
                    fallback_timeout,
                )
                try:
                    async with asyncio.timeout(fallback_timeout):
                        response = await self.client.chat.completions.create(
                            **self._build_visible_output_fallback_kwargs(request_kwargs)
                        )
                    requested_token_param = "max_tokens"
                    content = self._extract_response_text(response)
                except asyncio.TimeoutError:
                    logger.warning(
                        "[AI空响应兼容降级] fallback_timeout requested_token_param=%s timeout=%.2fs",
                        requested_token_param,
                        fallback_timeout,
                    )

        if not content:
            self._log_empty_response_debug(
                response=response,
                model_name=model_name or self.model_name,
                requested_max_tokens=max_tokens,
                requested_token_param=requested_token_param,
            )
            raise AIServiceException(
                "AI 模型返回空响应",
                details={"reason": "empty_response"},
            )

        self._log_raw_response_debug(
            response=response,
            content=content,
            requested_max_tokens=max_tokens,
            model_name=model_name or self.model_name,
            requested_token_param=requested_token_param,
        )

        await self._record_token_usage(response)

        return content.strip()

    async def _create_chat_completion_with_compat_fallback(
        self,
        *,
        request_kwargs: Dict[str, Any],
        requested_token_param: str,
    ) -> Any:
        advanced_fields: list[str] = []
        if "max_completion_tokens" in request_kwargs:
            advanced_fields.append("max_completion_tokens")
        if request_kwargs.get("reasoning_effort"):
            advanced_fields.append("reasoning_effort")

        try:
            return await self.client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            status_code = self._extract_status_code(exc)
            if not advanced_fields or status_code != 400:
                raise

            fallback_kwargs = dict(request_kwargs)
            if "max_completion_tokens" in fallback_kwargs and "max_tokens" not in fallback_kwargs:
                fallback_kwargs["max_tokens"] = fallback_kwargs.pop("max_completion_tokens")
            fallback_kwargs.pop("reasoning_effort", None)

            logger.warning(
                "[AI请求兼容降级] status=%s requested_token_param=%s removed=%s",
                status_code,
                requested_token_param,
                ",".join(advanced_fields),
            )
            return await self.client.chat.completions.create(**fallback_kwargs)

    @staticmethod
    def _build_visible_output_fallback_kwargs(request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        fallback_kwargs = dict(request_kwargs)
        if "max_completion_tokens" in fallback_kwargs and "max_tokens" not in fallback_kwargs:
            fallback_kwargs["max_tokens"] = fallback_kwargs.pop("max_completion_tokens")
        fallback_kwargs.pop("reasoning_effort", None)
        return fallback_kwargs

    @staticmethod
    def _should_retry_empty_response_with_token_fallback(
        *,
        response: Any,
        requested_token_param: str,
    ) -> bool:
        if requested_token_param != "max_completion_tokens":
            return False
        choices = list(getattr(response, "choices", []) or [])
        if not choices:
            return False
        finish_reason = str(getattr(choices[0], "finish_reason", "") or "").strip().lower()
        return finish_reason == "length"

    @staticmethod
    def _remaining_attempt_budget(
        *,
        timeout_seconds: Optional[float],
        started_at: Optional[float],
    ) -> float:
        if timeout_seconds is None or started_at is None:
            return 0.0
        return max(0.0, float(timeout_seconds) - (time.monotonic() - float(started_at)))

    @classmethod
    def _resolve_empty_response_fallback_timeout(cls, remaining_budget: float) -> Optional[float]:
        cap = float(os.getenv("AI_EMPTY_RESPONSE_FALLBACK_TIMEOUT_SECONDS", "5"))
        safety_margin = float(os.getenv("AI_EMPTY_RESPONSE_FALLBACK_SAFETY_MARGIN_SECONDS", "0.5"))
        min_timeout = float(os.getenv("AI_EMPTY_RESPONSE_FALLBACK_MIN_TIMEOUT_SECONDS", "1"))
        fallback_timeout = min(cap, max(0.0, remaining_budget - safety_margin))
        if fallback_timeout < min_timeout:
            return None
        return fallback_timeout

    def _extract_response_text(self, response: Any) -> str:
        for choice in list(getattr(response, "choices", []) or []):
            direct_text = self._normalize_response_content(getattr(choice, "text", None))
            if direct_text:
                return direct_text

            message = getattr(choice, "message", None)
            if message is None:
                continue

            normalized = self._normalize_response_content(getattr(message, "content", None))
            if normalized:
                return normalized

        return ""

    def _normalize_response_content(self, payload: Any, *, _depth: int = 0) -> str:
        if _depth > 6 or payload is None:
            return ""
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, (list, tuple)):
            fragments = [
                self._normalize_response_content(item, _depth=_depth + 1)
                for item in payload
            ]
            return "\n".join(fragment for fragment in fragments if fragment).strip()
        if isinstance(payload, dict):
            payload_type = str(payload.get("type", "") or "").strip().lower()
            if payload_type in {"reasoning", "refusal", "tool_call", "function_call"}:
                return ""
            for key in ("text", "output_text", "content", "value"):
                normalized = self._normalize_response_content(payload.get(key), _depth=_depth + 1)
                if normalized:
                    return normalized
            return ""

        payload_type = str(getattr(payload, "type", "") or "").strip().lower()
        if payload_type in {"reasoning", "refusal", "tool_call", "function_call"}:
            return ""
        for attr in ("text", "output_text", "content", "value"):
            if hasattr(payload, attr):
                normalized = self._normalize_response_content(getattr(payload, attr), _depth=_depth + 1)
                if normalized:
                    return normalized
        return ""

    def _log_raw_response_debug(
        self,
        *,
        response: Any,
        content: str,
        requested_max_tokens: int,
        model_name: str,
        requested_token_param: str = "max_tokens",
    ) -> None:
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        completion_details = getattr(usage, "completion_tokens_details", None)
        reasoning_tokens = int(getattr(completion_details, "reasoning_tokens", 0) or 0)

        choice = response.choices[0] if getattr(response, "choices", None) else None
        finish_reason = getattr(choice, "finish_reason", None) or "-"
        response_id = getattr(response, "id", None) or "-"
        raw_text = str(content or "")
        raw_chars = len(raw_text)

        logger.info(
            "[AI原始响应] model=%s response_id=%s finish_reason=%s requested_token_param=%s requested_max_tokens=%s raw_chars=%s usage_prompt=%s usage_completion=%s usage_reasoning=%s usage_total=%s",
            model_name,
            response_id,
            finish_reason,
            requested_token_param,
            requested_max_tokens,
            raw_chars,
            prompt_tokens,
            completion_tokens,
            reasoning_tokens,
            total_tokens,
        )

        if completion_tokens > max(0, requested_max_tokens):
            logger.warning(
                "[AI原始响应] usage_completion_tokens 超过 requested_max_tokens: completion=%s requested=%s finish_reason=%s response_id=%s",
                completion_tokens,
                requested_max_tokens,
                finish_reason,
                response_id,
            )

        if not self._env_flag("AI_RAW_RESPONSE_LOG_ENABLED", False):
            return

        preview_chars = max(0, self._env_int("AI_RAW_RESPONSE_PREVIEW_CHARS", 800))
        if preview_chars == 0:
            return

        preview = raw_text[:preview_chars]
        logger.debug(
            "[AI原始响应预览] response_id=%s preview_chars=%s content=%r",
            response_id,
            min(preview_chars, raw_chars),
            preview,
        )

    def _log_empty_response_debug(
        self,
        *,
        response: Any,
        model_name: str,
        requested_max_tokens: int,
        requested_token_param: str = "max_tokens",
    ) -> None:
        choices = list(getattr(response, "choices", []) or [])
        choice = choices[0] if choices else None
        message = getattr(choice, "message", None) if choice is not None else None
        raw_content = getattr(message, "content", None) if message is not None else None
        finish_reason = getattr(choice, "finish_reason", None) or "-"
        response_id = getattr(response, "id", None) or "-"
        tool_calls = getattr(message, "tool_calls", None) if message is not None else None
        refusal = getattr(message, "refusal", None) if message is not None else None

        logger.warning(
            "[AI空响应] model=%s response_id=%s finish_reason=%s requested_token_param=%s requested_max_tokens=%s choices=%s message_role=%s content_type=%s content_preview=%r tool_calls=%s refusal=%r",
            model_name,
            response_id,
            finish_reason,
            requested_token_param,
            requested_max_tokens,
            len(choices),
            getattr(message, "role", None) or "-",
            type(raw_content).__name__ if raw_content is not None else "NoneType",
            str(raw_content)[:200] if raw_content is not None else None,
            len(tool_calls) if isinstance(tool_calls, list) else (1 if tool_calls else 0),
            refusal,
        )

    async def _record_token_usage(self, response: Any) -> None:
        """从响应中提取并累计 token 使用量。"""
        usage = getattr(response, "usage", None)
        if not usage:
            return

        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)

        async with AIService._token_lock:
            AIService.total_prompt_tokens += prompt_tokens
            AIService.total_completion_tokens += completion_tokens
            AIService.total_tokens += total_tokens
            AIService.call_count += 1

        logger.debug(
            "Token使用: 输入=%s, 输出=%s, 总计=%s",
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )
    async def generate_response_with_messages(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: Optional[float] = None
    ) -> str:
        """
        使用完整消息历史生成 AI 回复（带超时控制）

        Args:
            messages: 消息历史列表
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）

        Returns:
            str: AI 回复内容

        Raises:
            AIServiceException: AI 服务调用失败
            asyncio.TimeoutError: 调用超时
        """
        timeout = timeout or self.resolve_timeout_settings()["chat_ai_timeout"]

        try:
            async with asyncio.timeout(timeout):
                # Make API call using async client
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.9,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )

                content = self._extract_response_text(response)
                if not content:
                    self._log_empty_response_debug(
                        response=response,
                        model_name=self.model_name,
                        requested_max_tokens=max_tokens,
                    )
                    raise AIServiceException(
                        "AI 模型返回空响应",
                        details={"reason": "empty_response"},
                    )

                await self._record_token_usage(response)
                return content.strip()

        except asyncio.TimeoutError:
            logger.error(f"AI 调用超时（{timeout}秒）")
            raise AIServiceException(f"AI 服务响应超时（{timeout}秒）")
        except Exception as e:
            logger.error(f"AI 调用失败: {e}")
            raise AIServiceException(f"AI 服务错误: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding"""
        try:
            async with asyncio.timeout(15.0):
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=text,
                    encoding_format="float"
                )

                embedding = response.data[0].embedding
                return embedding

        except asyncio.TimeoutError:
            logger.error("Timeout generating embedding")
            raise AIServiceException("嵌入生成超时")
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise AIServiceException(f"嵌入生成错误: {str(e)}")
              #情感分析
    async def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text"""
        try:
            async with asyncio.timeout(15.0):
                # Simple sentiment analysis using AI
                prompt = f"""
                请分析以下文本以下情感倾向，返回JSON格式：
                - positive: 积极情感程度 (0-1)
                - negative: 消极情感程度 (0-1)
                - neutral: 中性情感程度 (0-1)

                文本："{text}"

                请只返回JSON，不要其他内容。
                """

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                await self._record_token_usage(response)

                content = self._extract_response_text(response)
                if not content:
                    return {"positive": 0.3, "negative": 0.3, "neutral": 0.4}

                import json
                try:
                    sentiment = json.loads(content)
                    return {
                        "positive": float(sentiment.get("positive", 0.3)),
                        "negative": float(sentiment.get("negative", 0.3)),
                        "neutral": float(sentiment.get("neutral", 0.4))
                    }
                except json.JSONDecodeError:
                    return {"positive": 0.3, "negative": 0.3, "neutral": 0.4}

        except asyncio.TimeoutError:
            logger.error("Timeout analyzing sentiment")
            return {"positive": 0.3, "negative": 0.3, "neutral": 0.4}
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"positive": 0.3, "negative": 0.3, "neutral": 0.4}
              #关键词提取
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        try:
            async with asyncio.timeout(15.0):
                prompt = f"""
                请从以下文本中提取关键词，返回JSON数组：
                - 只提取重要的名词和短语
                - 去除重复项
                - 返回最多10个关键词

                文本："{text}"

                请只返回JSON数组，不要其他内容。
                """

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                await self._record_token_usage(response)

                content = self._extract_response_text(response)
                if not content:
                    return []

                import json
                try:
                    keywords = json.loads(content)
                    return keywords if isinstance(keywords, list) else []
                except json.JSONDecodeError:
                    return []

        except asyncio.TimeoutError:
            logger.error("Timeout extracting keywords")
            return []
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
              #意图分类
    async def classify_intent(self, text: str) -> Dict[str, Any]:
        """Classify user intent"""
        try:
            async with asyncio.timeout(15.0):
                prompt = f"""
                请分类以下用户的意图，返回JSON格式：
                - intent: 意图类别 (greeting, question, request, complaint, other)
                - confidence: 置信度 (0-1)
                - category: 具体分类

                可能的意图：
                - greeting: 问候类
                - question: 询问类
                - request: 请求/需求类
                - complaint: 抱怨类
                - other: 其他

                文本："{text}"

                请只返回JSON，不要其他内容。
                """

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                await self._record_token_usage(response)

                content = self._extract_response_text(response)
                if not content:
                    return {"intent": "other", "confidence": 0.1, "category": "未知"}

                import json
                try:
                    intent = json.loads(content)
                    return {
                        "intent": intent.get("intent", "other"),
                        "confidence": float(intent.get("confidence", 0.1)),
                        "category": intent.get("category", "未知")
                    }
                except json.JSONDecodeError:
                    return {"intent": "other", "confidence": 0.1, "category": "未知"}

        except asyncio.TimeoutError:
            logger.error("Timeout classifying intent")
            return {"intent": "other", "confidence": 0.1, "category": "未知"}
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return {"intent": "other", "confidence": 0.1, "category": "未知"}

    async def generate_system_prompt(
        self,
        personality_profile: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> str:
        """Generate system prompt with personality and context"""
        # Build personality description
        persona_name = personality_profile.get('name', '小缘')
        personality_desc = f"""
        你是{persona_name}，用自然、真诚、像真人聊天的方式和用户交流。
        不要虚构你的年龄、从业年限、所在城市或其他个人履历。

        性格特点：
        - 外向程度：{personality_profile.get('personality', {}).get('extroversion', 0.75)}
        - 耐心程度：{personality_profile.get('personality', {}).get('patience', 0.7)}
        - 稳定程度：{personality_profile.get('personality', {}).get('professionalism', 0.85)}
        - 幽默感：{personality_profile.get('personality', {}).get('humor', 0.7)}
        """

        # Add conversation context
        context_desc = ""
        if user_context:
            context_desc = f"""

        用户背景：
        - 对话次数：{user_context.get('dialog_count', 0)}
        - 用户偏好：{user_context.get('preferences', {})}
        - 最近对话：{user_context.get('recent_messages', [])[-2:] if user_context.get('recent_messages') else []}
        """

        # Build complete system prompt
        system = f"""
        {personality_desc}
        {context_desc}

        请以{persona_name}的口吻与用户交流，要求：
        1. 保持自然、友好、稳定的态度
        2. 先接住用户当下的话，再决定要不要继续推进
        3. 根据对话上下文调整回应风格
        4. 不要写成客服公告、销售话术或固定模板
        5. 少量口语化即可，不要堆口头禅和表情符号

        当前时间：{user_context.get('session_start', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
        """

        return system.strip()
              #健康检查
    async def health_check(self) -> bool:
        """Check AI service health

        注意：不调用外部 API 以避免：
        1. 浪费 API 配额
        2. 健康检查响应慢
        只检查服务是否已初始化
        """
        try:
            # 只检查客户端是否已初始化，不调用外部 API
            return self.client is not None and self.model_name is not None
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return False

    @classmethod
    async def get_token_usage(cls) -> Dict[str, int]:
        """获取token使用统计（使用锁保护）"""
        async with cls._token_lock:
            return {
                "prompt_tokens": cls.total_prompt_tokens,
                "completion_tokens": cls.total_completion_tokens,
                "total_tokens": cls.total_tokens,
                "call_count": cls.call_count
            }

    @classmethod
    async def reset_token_usage(cls):
        """重置token使用统计（使用锁保护）"""
        async with cls._token_lock:
            cls.total_prompt_tokens = 0
            cls.total_completion_tokens = 0
            cls.total_tokens = 0
            cls.call_count = 0
        logger.info("Token usage statistics reset")

    #关闭客户端资源
    async def close(self):
        """Close the async client and cleanup resources"""
        await self.client.close()
        logger.info("AI service client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
