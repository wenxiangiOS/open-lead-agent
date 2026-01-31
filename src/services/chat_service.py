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

            can_understand, error_response = self.info_collector.check_input_understandability(
                request.question, account_id
            )
            if not can_understand:
                self.info_collector.record_input_error(account_id)
                return self._success_response(error_response, request.dialogId)

            analysis = await self.ai_service.analyze_sentiment(request.question)
            context = self.user_service.get_conversation_context(account_id)

            # 检测用户输入是否为确认性回复（如"好"、"嗯"、"可以"等）
            is_confirmation = self.input_analyzer.is_confirmation_response(request.question)

            # 检查是否所有信息已收集完成
            is_collection_complete = user_profile.get_progress() >= 1.0

            # 检查联系方式是否已收集（包括phone/wechat标识类型）
            contact_collected = user_profile.collection_progress.get('contact', False)

            # 如果联系方式已收集且用户回复确认性内容，真人应该简短回应（结束话题）
            # 信息收集完成后，真人不会一直主动发起新话题
            if is_confirmation and (is_collection_complete or contact_collected):
                # 模拟真人行为：简短回应或不回复
                # 70%概率简短回应，30%概率不回复
                import random
                if random.random() < 0.3:
                    # 不回复或极简短
                    short_responses = ["[愉快]", "[爱心]", "嗯嗯", "好哒"]
                    enhanced_response = random.choice(short_responses)
                    self.user_service.record_interaction(
                        account_id,
                        request.question,
                        enhanced_response,
                        {
                            "intent": analysis.get("intent", "chat"),
                            "confidence": analysis.get("confidence", 0.0),
                            "collected_field": None,
                            "collection_progress": user_profile.get_progress(),
                            "is_confirmation": True
                        }
                    )
                    return self._success_response(enhanced_response, request.dialogId)
                else:
                    # 简短回应，不重复"已记下情况"这类话
                    short_responses = ["嗯嗯～", "好哒～", "收到啦～", "嗯嗯～[愉快]"]
                    enhanced_response = random.choice(short_responses)
                    self.user_service.record_interaction(
                        account_id,
                        request.question,
                        enhanced_response,
                        {
                            "intent": analysis.get("intent", "chat"),
                            "confidence": analysis.get("confidence", 0.0),
                            "collected_field": None,
                            "collection_progress": user_profile.get_progress(),
                            "is_confirmation": True
                        }
                    )
                    return self._success_response(enhanced_response, request.dialogId)

            # 先尝试收集信息
            collection_result = self._try_collect_user_info(
                account_id, user_profile, request.question, context
            )

            # 如果收集到性别，立即更新人设
            if collection_result["collected"] and collection_result["field"] == "sex":
                self._update_personality_with_user_sex(user_profile)

            # 重新获取最新的用户档案（可能已更新）
            user_profile = self.user_service.get_user_profile(account_id)

            user_greeting = self.user_service.get_user_greeting(account_id)
            # 获取已收集的用户信息摘要
            collected_info = self._get_collected_info_summary(user_profile)
            system_prompt = self.personality_profile.get_conversation_context_prompt(user_greeting, collected_info)

            ai_response = await self.ai_service.generate_response(
                request.question,
                system_prompt,
                temperature=0.8
            )

            enhanced_response = self.personality_profile.enhance_response(ai_response)

            if collection_result["collected"]:
                if collection_result["field"] == "contact":
                    # 检查收集到的联系方式类型
                    contact_value = collection_result["value"]
                    # 如果是标识类型（phone/wechat），不是实际号码，不需要验证
                    if contact_value in ['phone', 'wechat']:
                        # 标记为已收集，但不作为有效联系方式
                        pass
                    else:
                        # 是实际号码，需要验证
                        is_valid, phone_error = self.info_collector.is_valid_phone(contact_value)
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

            return self._success_response(enhanced_response, request.dialogId)

        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(str(e))

    def _get_collected_info_summary(self, user_profile: UserProfile) -> str:
        """获取已收集信息的摘要"""
        info_parts = []
        if user_profile.sex:
            info_parts.append(f"性别：{user_profile.sex}")
        if user_profile.last_name:
            # 姓氏信息已收集，但只用于知晓，不在称呼中使用，也不重复询问
            info_parts.append(f"用户已提供过姓氏信息（在称呼时只能用'小哥哥'或'小姐姐'，严禁加姓氏）")
        if user_profile.birth_year:
            info_parts.append(f"出生年：{user_profile.birth_year}年")
        if user_profile.height:
            info_parts.append(f"身高：{user_profile.height}")
        if user_profile.weight:
            info_parts.append(f"体重：{user_profile.weight}")
        if user_profile.location:
            info_parts.append(f"坐标：{user_profile.location}")
        if user_profile.education:
            info_parts.append(f"学历：{user_profile.education}")
        if user_profile.marital_status:
            info_parts.append(f"婚况：{user_profile.marital_status}")
        if user_profile.monthly_income:
            info_parts.append(f"月薪：{user_profile.monthly_income}")
        if user_profile.occupation:
            info_parts.append(f"职业：{user_profile.occupation}")
        if user_profile.contact:
            contact_info = user_profile.contact
            if contact_info in ['phone', 'wechat']:
                contact_info = 'phone' if contact_info == 'phone' else 'wechat'
            info_parts.append(f"联系方式：{contact_info}")

        if info_parts:
            return "【用户已知信息】" + "，".join(info_parts)
        return "【用户已知信息】暂无信息"

    def _try_collect_user_info(self, account_id: str, user_profile: UserProfile, user_message: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """尝试从用户消息中收集信息"""
        conversation_history = conversation_context.get("recent_messages", [])

        # 按收集优先级排序字段
        priority_order = [
            'sex',
            'last_name',
            'birth_year',
            'height',
            'weight',
            'location',
            'education',
            'marital_status',
            'monthly_income',
            'occupation',
            'contact'
        ]

        # 获取所有未收集的字段，并按优先级排序
        uncollected_fields = [
            field for field in priority_order
            if not user_profile.collection_progress.get(field, False)
        ]

        if not uncollected_fields:
            return {"collected": False, "field": None, "value": None, "progress": user_profile.get_progress(), "all_fields": []}

        # 尝试从用户消息中提取所有未收集的字段
        collected_fields = []
        for field_name in uncollected_fields:
            extractor = self._get_field_extractor(field_name)
            if extractor:
                extracted_value = extractor(user_message)
                if extracted_value is not None:
                    success = self.user_service.update_user_profile_field(account_id, field_name, extracted_value)
                    if success:
                        collected_fields.append({"field": field_name, "value": extracted_value})

        if collected_fields:
            # 更新profile以反映最新的收集进度
            user_profile = self.user_service.get_user_profile(account_id)
            return {
                "collected": True,
                "field": collected_fields[0]["field"],  # 返回第一个字段用于兼容
                "value": collected_fields[0]["value"],
                "progress": user_profile.get_progress(),
                "all_fields": collected_fields
            }

        return {"collected": False, "field": None, "value": None, "progress": user_profile.get_progress(), "all_fields": []}

    def _get_field_extractor(self, field_name: str):
        """获取字段提取器"""
        extractors = {
            "sex": self.info_collector.extract_sex,
            "last_name": self.info_collector.extract_last_name,
            "birth_year": self.info_collector.extract_birth_year,
            "height": self.info_collector.extract_height,
            "weight": self.info_collector.extract_weight,
            "location": self.info_collector.extract_location,
            "education": self.info_collector.extract_education,
            "marital_status": self.info_collector.extract_marital_status,
            "monthly_income": self.info_collector.extract_monthly_income,
            "occupation": self.info_collector.extract_occupation,
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
