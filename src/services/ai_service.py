"""AI service for Doubao integration"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from openai import OpenAI
from src.config.settings import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI model interactions"""

    def __init__(self, client: Optional[OpenAI] = None):
        """Initialize AI service"""
        # Import httpx and create a client without proxy
        import httpx

        # Disable proxy by setting NO_PROXY environment variable
        import os
        os.environ['NO_PROXY'] = '*'
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''

        # Create httpx client with no proxy transport
        http_client = httpx.Client()

        self.client = client or OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            http_client=http_client
        )
        self.model_name = settings.model_name

    async def generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate response from AI model"""
        try:
            # Create messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]

            # Make API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise Exception(f"AI服务错误: {str(e)}")

    async def generate_response_with_messages(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate response from AI model with full message history"""
        try:
            # Make API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise Exception(f"AI服务错误: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding"""
        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model_name,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise Exception(f"嵌入生成错误: {str(e)}")

    async def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text"""
        try:
            # Simple sentiment analysis using AI
            prompt = f"""
            请分析以下文本的情感倾向，返回JSON格式：
            - positive: 积极情感程度 (0-1)
            - negative: 消极情感程度 (0-1)
            - neutral: 中性情感程度 (0-1)

            文本："{text}"

            请只返回JSON，不要其他内容。
            """

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"positive": 0.3, "negative": 0.3, "neutral": 0.4}

    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        try:
            prompt = f"""
            请从以下文本中提取关键词，返回JSON数组：
            - 只提取重要的名词和短语
            - 去除重复项
            - 返回最多10个关键词

            文本："{text}"

            请只返回JSON数组，不要其他内容。
            """

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []

    async def classify_intent(self, text: str) -> Dict[str, Any]:
        """Classify user intent"""
        try:
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

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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
        system_prompt = f"""
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

        return system_prompt.strip()

    async def health_check(self) -> bool:
        """Check AI service health"""
        try:
            # Simple health check with a minimal request
            await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return False