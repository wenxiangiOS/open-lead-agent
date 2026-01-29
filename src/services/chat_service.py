"""Chat service for processing conversations with info collection"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.services.info_collector import InfoCollector
from src.utils.input_analyzer import InputAnalyzer
from src.utils.text_generator import TextGenerator
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ChatService:
    """
    聊天服务 - 处理对话并隐晦地收集用户信息

    核心功能：
    1. 拟人化对话 - 让用户察觉不到是AI
    2. 隐晦信息收集 - 自然地收集用户信息
    3. 智能容错 - 错误提醒有限制
    4. 性别自适应 - 根据性别调整称呼
    5. 目标对象反推 - 利用目标对象性别推断用户性别
    """

    def __init__(
        self,
        ai_service: AIService,
        user_service: UserService
    ):
        """Initialize chat service"""
        self.ai_service = ai_service
        self.user_service = user_service
        self.input_analyzer = InputAnalyzer()
        self.text_generator = TextGenerator()
        self.info_collector = InfoCollector()
        self.personality_profile = PersonalityProfile()

    async def process_chat_request(self, request: ChatRequest) -> Dict[str, Any]:
        """
        处理聊天请求 - 核心业务逻辑
        """
        try:
            account_id = request.accountId
            user_profile = self.user_service.get_user_profile(account_id)

            # 检测目标对象性别并反推用户性别
            target_gender = self.personality_profile.detect_target_gender(request.question)
            if target_gender and not user_profile.sex:
                # 如果检测到目标对象性别且用户性别未知，设置目标性别
                self.personality_profile.set_target_gender(target_gender)
                logger.info(f"Detected target gender: {target_gender}, inferred user as: {self.personality_profile.user_sex}")

            self._update_personality_with_user_sex(user_profile)

            can_understand, error_response = self.info_collector.check_input_understandability(
                request.question, account_id
            )
            if not can_understand:
                self.info_collector.record_input_error(account_id)
                return self._success_response(error_response, request.dialogId)

            analysis = await self.ai_service.analyze_sentiment(request.question)
            context = self.user_service.get_conversation_context(account_id)

            user_greeting = self.user_service.get_user_greeting(account_id)
            system_prompt = self.personality_profile.get_conversation_context_prompt(user_greeting)

            ai_response = await self.ai_service.generate_response(
                request.question,
                system_prompt,
                temperature=0.8
            )

            enhanced_response = self.personality_profile.enhance_response(ai_response)

            collection_result = self._try_collect_user_info(
                account_id, user_profile, request.question, context
            )

            if collection_result["collected"]:
                if collection_result["field"] == "contact":
                    is_valid, phone_error = self.info_collector.is_valid_phone(collection_result["value"])
                    if not is_valid:
                        field_state = self.info_collector._get_field_state(account_id, "contact")
                        if field_state["error_count"] < 2:
                            enhanced_response = phone_error
                        else:
                            enhanced_response = "嗯嗯，咱们聊点别的吧～😊"

            self.user_service.record_interaction(
                account_id,
                request.question,
                enhanced_response,
                {
                    "intent": analysis.get("intent", "chat"),
                    "confidence": analysis.get("confidence", 0.0),
                    "collected_field": collection_result.get("field"),
                    "collection_progress": user_profile.get_progress()
                }
            )

            if collection_result["field"] == "sex" and collection_result["collected"]:
                self._update_personality_with_user_sex(user_profile)

            return self._success_response(enhanced_response, request.dialogId)

        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(str(e))

    def _try_collect_user_info(self, account_id: str, user_profile: UserProfile, user_message: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """尝试从用户消息中收集信息"""
        conversation_history = conversation_context.get("recent_messages", [])
        next_field = user_profile.get_next_field_to_collect()

        if next_field:
            extractor = self._get_field_extractor(next_field)
            if extractor:
                extracted_value = extractor(user_message)
                if extracted_value is not None:
                    success = self.user_service.update_user_profile_field(account_id, next_field, extracted_value)
                    if success:
                        return {"collected": True, "field": next_field, "value": extracted_value, "progress": user_profile.get_progress()}

        return {"collected": False, "field": None, "value": None, "progress": user_profile.get_progress()}

    def _get_field_extractor(self, field_name: str):
        """获取字段提取器"""
        extractors = {
            "sex": self.info_collector.extract_sex,
            "birth_year": self.info_collector.extract_birth_year,
            "height": self.info_collector.extract_height,
            "weight": self.info_collector.extract_weight,
            "location": self.info_collector.extract_location,
            "education": self.info_collector.extract_education,
            "marital_status": self.info_collector.extract_marital_status,
            "monthly_income": self.info_collector.extract_monthly_income,
            "occupation": self.info_collector.extract_occupation,
            "preferred_call": self.info_collector.extract_preferred_call,
            "contact": self.info_collector.extract_contact
        }
        return extractors.get(field_name)

    def _update_personality_with_user_sex(self, user_profile: UserProfile) -> None:
        """根据用户档案更新人设中的性别"""
        if user_profile.sex:
            self.personality_profile.set_user_sex(user_profile.sex)

    def _success_response(self, response: str, dialog_id: Optional[str] = None, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成成功响应"""
        result = {"success": True, "response": response, "timestamp": datetime.now().isoformat()}
        if dialog_id:
            result["dialogId"] = dialog_id
        if additional_data:
            result.update(additional_data)
        return result

    def _error_response(self, error: str, dialog_id: Optional[str] = None) -> Dict[str, Any]:
        """生成错误响应"""
        result = {"success": False, "error": error, "timestamp": datetime.now().isoformat()}
        if dialog_id:
            result["dialogId"] = dialog_id
        return result

    async def generate_welcome_message(self, user_id: str) -> Dict[str, Any]:
        """生成新用户欢迎消息"""
        try:
            user_state = self.user_service.get_user_state(user_id)
            is_new = user_state.is_new_user()
            user_profile = self.user_service.get_user_profile(user_id)
            self._update_personality_with_user_sex(user_profile)

            if is_new:
                welcome = self.personality_profile.get_greeting()
                self.user_service.record_interaction(user_id, "welcome", welcome, {"type": "welcome"})
                return self._success_response(welcome, None, {"is_new_user": True, "user_insights": self.user_service.get_user_insights(user_id)})
            else:
                greeting = self.personality_profile.get_greeting()
                return self._success_response(greeting, user_state.active_dialog_id, {"is_new_user": False, "user_insights": self.user_service.get_user_insights(user_id)})
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            return self._error_response(str(e))

    async def get_user_profile_info(self, account_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            profile = self.user_service.get_user_profile_dict(account_id)
            return self._success_response({"profile": profile})
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return self._error_response(str(e))

    async def reset_user_collection(self, account_id: str) -> Dict[str, Any]:
        """重置用户信息收集状态"""
        try:
            self.info_collector.reset_errors(account_id)
            return self._success_response("已重置信息收集状态～")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return self._error_response(str(e))

    async def get_all_user_profiles(self) -> Dict[str, Any]:
        """获取所有用户档案信息"""
        try:
            profile_ids = self.user_service.get_all_profile_ids()
            profiles = {}
            for profile_id in profile_ids:
                profile_dict = self.user_service.get_user_profile_dict(profile_id)
                profiles[profile_id] = profile_dict
            return self._success_response({"profiles": profiles, "total_count": len(profiles), "statistics": self.user_service.get_user_statistics()})
        except Exception as e:
            logger.error(f"Error getting all profiles: {e}")
            return self._error_response(str(e))

    async def handle_no_response(self, user_id: str) -> Dict[str, Any]:
        """处理用户无响应情况"""
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            response = self.personality_profile.handle_no_response(user_profile.sex)
            return self._success_response(response)
        except Exception as e:
            logger.error(f"Error handling no response: {e}")
            return self._error_response(str(e))

    async def handle_skepticism(self, user_id: str) -> Dict[str, Any]:
        """处理用户质疑真假情况"""
        try:
            response = self.personality_profile.handle_skepticism()
            return self._success_response(response)
        except Exception as e:
            logger.error(f"Error handling skepticism: {e}")
            return self._error_response(str(e))
