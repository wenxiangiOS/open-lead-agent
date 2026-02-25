"""AI service for Doubao integration"""
"""调用豆包 API，生成回复、情感分析、关键词提取、意图分类"""

import logging
import asyncio
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

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        """Initialize AI service"""
        # 注意：代理配置已在 main.py 中统一设置，此处不再重复

        # 创建带合理超时配置的异步 OpenAI 客户端
        # 使用异步客户端 AsyncOpenAI 而非同步客户端，避免资源泄漏
        # 添加连接池配置支持高并发
        import httpx

        # 配置连接池
        limits = httpx.Limits(
            max_connections=settings.http_connections,
            max_keepalive_connections=settings.http_max_keepalive
        )

        # 配置超时 - 增加读取超时时间
        timeout = httpx.Timeout(
            connect=self.CONNECT_TIMEOUT,
            read=60.0,  # 增加到60秒
            write=10.0,
            pool=5.0
        )

        self.client = client or AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=timeout,
            max_retries=0,  # 禁用重试，加快失败响应
            http_client=httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                verify=True,  # 启用SSL验证
                proxy=None    # 禁用代理，直连豆包API
            )
        )
        self.model_name = settings.model_name

    async def generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: Optional[float] = None
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
        timeout = timeout or self.DEFAULT_TIMEOUT
        max_retries = 3  # 最大重试次数
        retry_delay = 1  # 重试间隔（秒）

        last_error = None
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(timeout):
                    return await self._do_generate_response(
                        message, system_prompt, temperature, max_tokens
                    )
            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"AI 调用超时（{timeout}秒），第 {attempt + 1} 次重试...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"AI 调用超时（{timeout}秒），已重试 {max_retries} 次")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"AI 调用失败: {e}，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"AI 调用失败: {e}")

        raise AIServiceException(f"AI 服务响应超时（{timeout}秒），已重试 {max_retries} 次")

    async def _do_generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
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

        # Extract response
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from AI model")
            return "抱歉，我暂时无法回答这个问题。"

        # 记录token使用情况（使用锁保护并发访问）
        if hasattr(response, 'usage') and response.usage:
            async with AIService._token_lock:
                AIService.total_prompt_tokens += response.usage.prompt_tokens
                AIService.total_completion_tokens += response.usage.completion_tokens
                AIService.total_tokens += response.usage.total_tokens
                AIService.call_count += 1
            logger.info(
                f"Token使用: 输入={response.usage.prompt_tokens}, "
                f"输出={response.usage.completion_tokens}, "
                f"总计={response.usage.total_tokens}"
            )

        return content.strip()
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
        timeout = timeout or self.DEFAULT_TIMEOUT

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

                # Extract response
                content = response.choices[0].message.content
                if not content:
                    logger.warning("Empty response from AI model")
                    return "抱歉，我暂时无法回答这个问题。"

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

                content = response.choices[0].message.content
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

                content = response.choices[0].message.content
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

                content = response.choices[0].message.content
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
        personality_desc = f"""
        你是{personality_profile.get('name', '小桃子')}，{personality_profile.get('age', 28)}岁，
        拥有{personality_profile.get('experience_years', 3)}年经验的专业红娘。

        性格特点：
        - 外向程度：{personality_profile.get('personality', {}).get('extroversion', 0.75)}
        - 耐心程度：{personality_profile.get('personality', {}).get('patience', 0.7)}
        - 专业程度：{personality_profile.get('personality', {}).get('professionalism', 0.85)}
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

        请以小桃子的身份与用户交流，要求：
        1. 保持专业、友好的态度
        2. 适当展现个性特征

        3. 根据对话上下文调整回应风格
        4. 提供有价值的情感建议
        5. 适当使用口头禅和表情符号

        当前时间：{user_context.get('session_start', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
        """

        return system.strip()
              #健康检查
    async def health_check(self) -> bool:
        """Check AI service health"""
        try:
            # Simple health check with a minimal request
            await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
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
