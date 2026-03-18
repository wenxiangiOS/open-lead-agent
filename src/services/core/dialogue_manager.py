"""
对话管理器

负责管理对话状态和上下文
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.models.user_profile import UserProfile
from src.models.personality import PersonalityProfile
from src.services.prompts import (
    get_main_dialogue,
    get_question_priority_dialogue,
    get_extraction,
    build_gender_instruction,
    build_skipped_fields_instruction,
    build_ask_count_instruction,
)
from src.services.data.user_service import UserService
from src.services.collection.contact_collection_service import ContactCollectionService
from src.services.collection.profile_collection_policy import ProfileCollectionPolicy
from src.config.settings import get_all_field_names

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
        self.contact_service = ContactCollectionService(user_service)
        self.collection_policy = ProfileCollectionPolicy()

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

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
        conversation_context: Dict[str, Any],
        prioritize_user_question: bool = False,
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
        from src.services.data.extraction_service import ExtractionService

        # 获取已收集信息摘要
        extraction_service = ExtractionService(self.user_service)
        collected_info = extraction_service.get_collected_info_summary(user_profile)

        # 获取性别指令
        gender_instruction = build_gender_instruction(user_profile.sex)

        # 使用联系方式收集服务
        is_hong_user = self.contact_service.is_hongkong_user(user_profile)

        # 调试日志：香港用户场景
        logger.info(f"[联系方式状态] 香港用户={is_hong_user}({user_profile.location}), 电话={user_profile.phone}(已收集={user_profile.phone_collected}), 微信={user_profile.wechat}(已收集={user_profile.wechat_collected})")

        # 获取联系方式指令（使用新的服务）
        contact_instruction, next_action_enum = self.contact_service.build_instruction(user_profile, user_message)
        next_action = self.contact_service.get_action_dict(next_action_enum)

        # 调试日志：显示下一步动作
        logger.info(f"[联系方式指令] 下一步动作: {next_action_enum.value}, phone_ask_count={user_profile.phone_ask_count}, wechat_ask_count={user_profile.wechat_ask_count}")

        # 调试日志：只显示指令类型，不显示完整内容
        if contact_instruction:
            instruction_type = contact_instruction.strip().split('\n')[0][:50]
            logger.debug(f"[联系方式指令] {instruction_type}...")

        # 简化日志：合并状态信息
        logger.debug(f"[联系方式状态] 拒(微信={user_profile.rejected_wechat},电话={user_profile.rejected_phone}), 询问次数(微信={user_profile.wechat_ask_count},电话={user_profile.phone_ask_count})")

        # 获取跳过字段指令（从 user_profile.skipped_fields 获取）
        skipped_fields = set(user_profile.skipped_fields.keys()) if user_profile.skipped_fields else set()
        skipped_fields_instruction = build_skipped_fields_instruction(skipped_fields)

        # 获取追问次数指令（智能追问机制）
        ask_count_instruction = build_ask_count_instruction(
            user_profile.field_ask_count,
            user_profile.collection_progress
        )

        cooldown_turns = self._env_int("MQ_FIELD_ASK_COOLDOWN_TURNS", 2)
        cooldown_fields = user_profile.get_cooldown_fields(cooldown_turns)
        if cooldown_fields:
            field_name_map = get_all_field_names()
            cooldown_cn = [field_name_map.get(f, f) for f in cooldown_fields]
            ask_count_instruction += f"""

【追问冷却约束】
上一轮刚问过：{'、'.join(cooldown_cn)}。
这一轮禁止继续追问这些字段，优先承接用户新信息或改问其他未收集字段。
"""

        # 资料收集策略决策
        message_count = conversation_context.get('message_count', 0)
        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            message_count=message_count,
        )

        # 未到联系方式进入时机时，压制联系方式主动提示，避免旧逻辑抢跑
        if not self.collection_policy.should_allow_contact_instruction(user_profile, next_action_enum.name):
            contact_instruction = ""
            logger.info("[联系方式指令] 当前资料不足，暂不进入联系方式逻辑")

        question_priority_instruction = ""
        if prioritize_user_question:
            contact_instruction = ""
            ask_count_instruction = ""
            question_priority_instruction = """
【本轮优先级最高】
用户这句话是在提疑问或表达顾虑，这一轮先把问题讲清楚。
- 先完整回答用户当前的问题
- 不要追问资料
- 不要索要电话或微信
- 回答后最多轻轻确认一句“如果你还有顾虑也可以继续问我”
- 只有用户疑虑放下后，下一轮再回到资料收集
"""
            logger.info("[答疑优先] 已压制联系方式和字段追问提示")

        # 构建主提示词
        # 首轮判定以用户消息轮次为准，避免因预填sex导致首轮承接被跳过
        is_first_chat = message_count == 0

        # 调试日志
        logger.debug(f"[对话状态] 首次={is_first_chat}, 已收集={collected_info[:80]}...")
        if skipped_fields:
            logger.debug(f"[跳过字段] {skipped_fields}")

        # 获取缺失字段列表（使用新的资料收集策略，而不是旧的统一缺失字段）
        missing_fields_list = policy_decision.missing_fields
        # 从配置获取字段名映射（英文 -> 中文）
        field_name_map = get_all_field_names()
        missing_fields_cn = [field_name_map.get(f, f) for f in missing_fields_list if f in field_name_map]
        missing_fields_str = "、".join(missing_fields_cn) if missing_fields_cn else "无"

        if prioritize_user_question:
            # 答疑优先轮次使用轻量提示词，减少 token 与推理耗时
            main_prompt = get_question_priority_dialogue(
                collected_info=collected_info,
                gender_instruction=gender_instruction,
            )
        else:
            main_prompt = get_main_dialogue(
                collected_info=collected_info,
                gender_instruction=gender_instruction,
                contact_instruction=contact_instruction,
                skipped_fields_instruction=skipped_fields_instruction,
                ask_count_instruction=ask_count_instruction,
                question_priority_instruction=question_priority_instruction,
                is_first_chat=is_first_chat,
                missing_fields=missing_fields_str,
                current_main_target=field_name_map.get(policy_decision.main_target, policy_decision.main_target or "无"),
                current_side_target=field_name_map.get(policy_decision.side_target, policy_decision.side_target or "无"),
                user_type=policy_decision.user_type,
                can_enter_contact=policy_decision.can_enter_contact,
            )

        # 获取上一轮 AI 回复（用于上下文感知提取）
        last_ai_response = conversation_context.get('recent_responses', [])
        last_question = last_ai_response[-1] if last_ai_response else ""
        if last_question:
            logger.debug(f"[上下文] 上一轮AI: {last_question[:50]}...")

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
