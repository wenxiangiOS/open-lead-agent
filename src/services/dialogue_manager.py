"""
对话管理器

负责管理对话状态和上下文
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.models.user_profile import UserProfile
from src.models.personality import PersonalityProfile
from src.services.prompts import get_main_dialogue, get_extraction, build_gender_instruction, build_contact_instruction, build_skipped_fields_instruction, build_ask_count_instruction
from src.services.user_service import UserService

logger = logging.getLogger(__name__)


class DialogueManager:
    """
    对话管理器

    职责：
    1. 管理对话状态
    2. 构建对话上下文
    3. 生成 AI 提示词
    4. 追踪对话历史
    5. 检测对话阶段
    """

    def __init__(self, user_service: UserService):
        """
        初始化对话管理器

        Args:
            user_service: 用户服务
        """
        self.user_service = user_service
        self.personality_profile = PersonalityProfile()

    async def get_conversation_context(self, account_id: str) -> Dict[str, Any]:
        """
        获取对话上下文

        Args:
            account_id: 用户 ID

        Returns:
            Dict[str, Any]: 对话上下文
        """
        context = await self.user_service.get_conversation_context(account_id)

        # 确保必要字段存在
        if 'recent_responses' not in context:
            context['recent_responses'] = []
        if 'message_count' not in context:
            context['message_count'] = 0
        if 'conversation_stage' not in context:
            context['conversation_stage'] = 'opening'

        return context

    def update_user_sex(self, user_profile: UserProfile) -> None:
        """
        更新人设中的用户性别

        Args:
            user_profile: 用户档案
        """
        if user_profile.sex:
            self.personality_profile.set_user_sex(user_profile.sex)

    def build_main_dialogue_prompt(
        self,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any]
    ) -> str:
        """
        构建主对话提示词

        Args:
            user_message: 用户消息
            user_profile: 用户档案
            conversation_context: 对话上下文

        Returns:
            str: 完整的对话提示词
        """
        from src.services.extraction_service import ExtractionService

        # 获取已收集信息摘要
        extraction_service = ExtractionService(self.user_service)
        collected_info = extraction_service.get_collected_info_summary(user_profile)

        # 获取性别指令
        gender_instruction = build_gender_instruction(user_profile.sex)

        # 获取联系方式指令
        contact_instruction = build_contact_instruction(
            user_profile.collection_progress.get('contact', False)
        )

        # 获取跳过字段指令（从 user_profile.skipped_fields 获取）
        skipped_fields = set(user_profile.skipped_fields.keys()) if user_profile.skipped_fields else set()
        skipped_fields_instruction = build_skipped_fields_instruction(skipped_fields)

        # 获取追问次数指令（智能追问机制）
        ask_count_instruction = build_ask_count_instruction(user_profile.field_ask_count)

        # 构建主提示词
        # 判断是否为首次对话：基于用户资料的收集进度
        # 如果已经收集了称呼和性别，就不再显示开场白
        has_name = user_profile.last_name is not None and user_profile.last_name != ""
        has_sex = user_profile.sex is not None
        is_first_chat = not (has_name or has_sex)

        # 调试日志
        logger.info(f"[is_first_chat检查] has_name={has_name}(value={user_profile.last_name}), has_sex={has_sex}(value={user_profile.sex}), is_first_chat={is_first_chat}")
        logger.info(f"[已收集摘要] {collected_info}")
        if skipped_fields:
            logger.info(f"[跳过字段] {skipped_fields}")

        main_prompt = get_main_dialogue(
            collected_info=collected_info,
            gender_instruction=gender_instruction,
            contact_instruction=contact_instruction,
            skipped_fields_instruction=skipped_fields_instruction,
            ask_count_instruction=ask_count_instruction,
            is_first_chat=is_first_chat
        )

        # 获取上一轮 AI 回复（用于上下文感知提取）
        last_ai_response = conversation_context.get('recent_responses', [])
        last_question = last_ai_response[-1] if last_ai_response else ""
        if last_question:
            logger.info(f"[上下文提取] 上一轮AI回复: {last_question[:100]}...")

        # 添加信息提取提示词（传递 last_question 用于上下文感知）
        extraction_prompt = get_extraction(
            user_message=user_message,
            last_question=last_question
        )

        # 组合完整提示词
        full_prompt = f"{main_prompt}\n\n{extraction_prompt}"

        return full_prompt

    def build_extraction_prompt(
        self,
        ai_response: str,
        user_message: str
    ) -> str:
        """
        构建信息提取提示词

        Args:
            ai_response: AI 回复
            user_message: 用户消息

        Returns:
            str: 提取提示词
        """
        return get_extraction(ai_response, user_message)

    async def add_to_history(
        self,
        account_id: str,
        role: str,
        content: str
    ) -> None:
        """
        添加消息到对话历史

        Args:
            account_id: 用户 ID
            role: 角色 (user/assistant)
            content: 消息内容
        """
        await self.user_service.add_message_to_history(account_id, {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })

    async def update_recent_responses(
        self,
        account_id: str,
        response: str,
        max_length: int = 3
    ) -> None:
        """
        更新最近的回复列表

        Args:
            account_id: 用户 ID
            response: AI 回复
            max_length: 最大保留数量
        """
        context = await self.get_conversation_context(account_id)
        recent_responses = context.get('recent_responses', [])

        # 清理旧的回复（移除 <extract> 标签）
        import re
        clean_response = re.sub(r'<extract>.*?</extract>', '', response, flags=re.DOTALL).strip()

        recent_responses.append(clean_response)

        # 只保留最近的几条
        if len(recent_responses) > max_length:
            recent_responses = recent_responses[-max_length:]

        context['recent_responses'] = recent_responses
        await self.user_service.save_conversation_context(account_id, context)

    async def increment_message_count(self, account_id: str) -> int:
        """
        增加消息计数

        Args:
            account_id: 用户 ID

        Returns:
            int: 当前消息总数
        """
        context = await self.get_conversation_context(account_id)
        message_count = context.get('message_count', 0) + 1
        context['message_count'] = message_count
        await self.user_service.save_conversation_context(account_id, context)
        return message_count

    async def get_message_count(self, account_id: str) -> int:
        """
        获取消息计数

        Args:
            account_id: 用户 ID

        Returns:
            int: 消息总数
        """
        context = await self.get_conversation_context(account_id)
        return context.get('message_count', 0)

    async def get_last_response(self, account_id: str) -> Optional[str]:
        """
        获取最后一次 AI 回复

        Args:
            account_id: 用户 ID

        Returns:
            Optional[str]: 最后一次回复
        """
        context = await self.get_conversation_context(account_id)
        recent_responses = context.get('recent_responses', [])
        return recent_responses[-1] if recent_responses else None

    def detect_conversation_stage(
        self,
        user_profile: UserProfile,
        message_count: int
    ) -> str:
        """
        检测对话阶段

        Args:
            user_profile: 用户档案
            message_count: 消息数量

        Returns:
            str: 对话阶段 (opening/understanding/trust/completing/complete)
        """
        # 计算已收集字段数量
        collected_count = sum(user_profile.collection_progress.values())

        # 判断阶段
        if message_count <= 2:
            return 'opening'
        elif collected_count == 0:
            return 'opening'
        elif collected_count < 3:
            return 'understanding'
        elif collected_count < 6:
            return 'trust'
        elif not user_profile.collection_progress.get('contact'):
            return 'completing'
        else:
            return 'complete'

    def should_continue_after_complete(
        self,
        user_message: str,
        conversation_stage: str
    ) -> bool:
        """
        判断任务完成后是否应该继续对话

        Args:
            user_message: 用户消息
            conversation_stage: 对话阶段

        Returns:
            bool: 是否应该继续
        """
        if conversation_stage != 'complete':
            return True

        # 任务完成后，只对确认性内容回复
        affirmative_keywords = ['好的', '嗯', '可以', '行', '谢谢', '感谢', 'ok', 'ok的']
        return any(keyword in user_message.lower() for keyword in affirmative_keywords)

    async def clear_conversation(self, account_id: str) -> None:
        """
        清除对话历史

        Args:
            account_id: 用户 ID
        """
        await self.user_service.clear_conversation_history(account_id)
        context = {
            'recent_responses': [],
            'message_count': 0,
            'conversation_stage': 'opening'
        }
        await self.user_service.save_conversation_context(account_id, context)
        logger.info(f"[对话清除] 已清除用户 {account_id} 的对话历史")
