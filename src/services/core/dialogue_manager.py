"""
对话管理器

负责管理对话状态和上下文
"""

import logging
import os
import re
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
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
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

    @staticmethod
    def _compact_prompt_text(text: str, max_chars: int) -> str:
        content = str(text or "").strip()
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."

    @staticmethod
    def normalize_assistant_response(response: str) -> str:
        """统一 assistant 回复在 history / recent_responses 中的存储口径。"""
        import re

        clean_response = re.sub(r'<extract>.*?</extract>', '', str(response or ""), flags=re.DOTALL).strip()
        clean_response = re.sub(r"\s+", " ", clean_response).strip()
        return clean_response

    @staticmethod
    def build_prompt_signature(response: str) -> str:
        text = DialogueManager.normalize_assistant_response(response)
        if not text:
            return ""

        markers = []
        opening_patterns = (
            "你好呀",
            "对了",
            "想问下",
            "方便说下",
            "我再确认一下",
            "顺带问一句",
            "学历这块",
            "婚况这块",
        )
        for pattern in opening_patterns:
            if pattern in text:
                markers.append(pattern)

        field_patterns = (
            ("sex", ("男生还是女生", "男生吗还是女生", "性别")),
            ("age", ("多大", "年龄段", "年龄")),
            ("location", ("哪个城市", "什么城市", "在哪边", "在哪个城市")),
            ("education", ("学历",)),
            ("occupation", ("工作", "职业", "哪方面工作")),
            ("marital", ("单身状态", "婚况", "离异")),
            ("contact", ("手机号", "微信", "联系方式")),
        )
        for label, patterns in field_patterns:
            if any(pattern in text for pattern in patterns):
                markers.append(label)
                break

        if not markers:
            return text[:24]
        return "|".join(dict.fromkeys(markers))

    @staticmethod
    def build_recent_style_instruction(
        recent_responses: List[str],
        recent_prompt_signatures: List[str],
    ) -> str:
        snippets = [
            DialogueManager._compact_prompt_text(item, 28)
            for item in (recent_responses or [])[-2:]
            if str(item or "").strip()
        ]
        signatures = [str(item or "").strip() for item in (recent_prompt_signatures or [])[-3:] if str(item or "").strip()]

        lines: List[str] = []
        if snippets:
            lines.append(f"最近两轮你说过：{' / '.join(snippets)}")
            lines.append("这一轮不要沿用同样开头，也不要照着上一轮句式改两个词继续问。")
        if signatures:
            lines.append(f"近期高频骨架：{'；'.join(signatures)}")
        lines.append("优先换开头、换句式、换提问落点，但核心意图不要跑偏。")
        lines.append("如果要问婚况，只确认现在是不是单身状态，不要并列枚举未婚和离异。")
        return "\n".join(f"- {line}" for line in lines)

    async def update_prompt_style_memory(self, account_id: str, response: str, max_length: int = 5) -> None:
        signature = self.build_prompt_signature(response)
        if not signature:
            return

        context = await self.get_conversation_context(account_id)
        if not isinstance(context, dict):
            return
        preferences = context.get("preferences") or {}
        if not isinstance(preferences, dict):
            return
        recent = list(preferences.get("recent_prompt_signatures") or [])
        recent.append(signature)
        if len(recent) > max_length:
            recent = recent[-max_length:]
        await self.user_service.update_user_preference(account_id, "recent_prompt_signatures", recent)

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
        primary_move: str = "ack_and_ask",
        allow_contact_target: bool = True,
        allow_medium_target: bool = True,
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
        collected_info_prompt = self._compact_prompt_text(
            collected_info,
            self._env_int("MQ_PROMPT_COLLECTED_INFO_MAX_CHARS", 260),
        )

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
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
        )
        prompt_can_enter_contact = policy_decision.allow_contact_push

        # 显式禁止切联系方式时，直接压制联系方式提示，避免主线轮次被旧提示带偏。
        if not allow_contact_target:
            contact_instruction = ""
            logger.info("[联系方式指令] 当前轮次禁止切联系方式，已压制联系方式提示")
        # 未到联系方式进入时机时，压制联系方式主动提示，避免旧逻辑抢跑
        elif not self.collection_policy.should_allow_contact_instruction(user_profile, next_action_enum.name):
            contact_instruction = ""
            logger.info(
                "[联系方式指令] 暂不进入联系方式逻辑: "
                f"reason={policy_decision.reason}, "
                f"unresolved_core={policy_decision.unresolved_core_fields}, "
                f"unresolved_medium={policy_decision.unresolved_medium_fields}, "
                f"profile_sufficient={policy_decision.profile_sufficient}, "
                f"engagement_mode={policy_decision.engagement_mode}"
            )

        question_priority_instruction = ""
        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            contact_instruction = ""
            ask_count_instruction = ""
            question_priority_instruction = """
【离异手续确认优先】
用户当前处于“离异待确认手续”状态，这一轮只做这一件事：确认离婚手续是否已经办妥。
- 先承接用户刚刚关于离异/婚况的表达
- 只问手续是否已经办妥
- 不要追问学历、职业、城市、年龄、联系方式或其他资料
- 如果用户回答“还在办/没办完/分居中”，礼貌收尾，不再继续收集
- 如果用户回答“已经办妥/办好了/现在是单身”，下一轮再回到正常资料收集
"""
            logger.info("[离异确认] 已锁定本轮只确认手续状态")

        if prioritize_user_question:
            contact_instruction = ""
            ask_count_instruction = ""
            question_priority_instruction = """
【本轮优先级最高】
用户这句话是在提疑问或表达顾虑，这一轮先把问题讲清楚。
- 先完整回答用户当前的问题
- 不要追问资料
- 不要索要电话或微信
- 回答后不要固定重复同一句收尾，只有在自然顺口时才轻轻补一句继续交流的话
- 只有用户疑虑放下后，下一轮再回到资料收集
"""
            logger.info("[答疑优先] 已压制联系方式和字段追问提示")

        move_instruction = ""
        if primary_move == "answer_then_pause":
            move_instruction = """
【本轮动作】
这轮先答清楚用户当前的问题或顾虑，再决定是否轻轻收住。
- 先答，不要急着追问字段
- 回答尽量像真人解释，不像业务说明书
- 若回答完已完整，就停在这里，不强行补问
"""
        elif primary_move == "confirm_status_only":
            move_instruction = """
【本轮动作】
这轮只做状态确认。
- 先承接用户刚刚提到的婚况/手续
- 只确认当前状态，不并列追问别的资料
- 用更像真人确认的语气，不要像系统复核
"""
        elif primary_move == "soft_hold":
            move_instruction = """
【本轮动作】
这轮先接住用户边界或顾虑，不往前顶。
- 先让用户感觉你听到了
- 不急着推进资料或联系方式
- 允许轻轻收一下，不必硬问
"""
        elif primary_move == "light_followup":
            move_instruction = """
【本轮动作】
这轮用轻量承接推进一小步。
- 先接住用户刚给的短答
- 追问只问一个点
- 句子尽量短，别像登记表
"""

        if policy_decision.next_mode == "open_profile_repair":
            contact_instruction = ""
            ask_count_instruction = ""
            move_instruction += """

【开放式补画像】
当前已完成字段覆盖，但核心画像仍偏薄。
- 这轮不要按字段表单式追问
- 不要索要联系方式
- 用一个开放式、自然的问题让用户自由展开近况或生活状态
- 目标是顺手补到更多画像信息，而不是逐项盘问
"""
        elif policy_decision.next_mode in {"low_pressure_chat", "terminate_conversion"}:
            contact_instruction = ""
            ask_count_instruction = ""
            move_instruction += """

【低压收住】
当前不再主动推进资料或联系方式。
- 先自然承接用户这句话
- 回复保持简短
- 不主动追问资料
- 不主动索要联系方式
- 更像轻聊天或礼貌收住
"""
        elif policy_decision.next_mode == "contact_hold":
            contact_instruction = ""
            move_instruction += """

【联系方式缓一轮】
当前资料和画像已基本足够，但这一轮不适合直接切联系方式。
- 先顺着用户当前表达接一句
- 不要这轮马上索要电话或微信
- 允许轻轻收一下，下一轮再判断是否进入联系方式
"""

        # 构建主提示词
        # 首轮判定以用户消息轮次为准，避免因预填sex导致首轮承接被跳过
        is_first_chat = message_count == 0

        # 调试日志
        logger.debug(f"[对话状态] 首次={is_first_chat}, 已收集={collected_info[:80]}...")
        if skipped_fields:
            logger.debug(f"[跳过字段] {skipped_fields}")

        # 获取缺失字段列表（使用新的资料收集策略，而不是旧的统一缺失字段）
        missing_fields_list = policy_decision.missing_fields
        missing_fields_max = self._env_int("MQ_PROMPT_MISSING_FIELDS_MAX", 6)
        if missing_fields_max > 0:
            missing_fields_list = missing_fields_list[:missing_fields_max]
        # 从配置获取字段名映射（英文 -> 中文）
        field_name_map = get_all_field_names()
        missing_fields_cn = [field_name_map.get(f, f) for f in missing_fields_list if f in field_name_map]
        missing_fields_str = "、".join(missing_fields_cn) if missing_fields_cn else "无"

        # Phase 2: repair_mode 修复态约束（最高优先级）
        in_repair_mode = user_profile.repair_mode and user_profile.ask_cooldown_turns > 0
        if in_repair_mode:
            # 修复态：只允许确认问题 + 复述已记录信息 + 停止追问
            repair_reason = user_profile.repair_reason or "repeat_ask"
            reason_text = {
                "repeat_ask": "用户表示我们在重复追问",
                "over_questioning": "用户表示我们问得太多",
            }.get(repair_reason, "用户有不满")
            main_prompt = f"""【修复态约束】
当前处于修复模式，原因：{reason_text}
剩余冷却轮数：{user_profile.ask_cooldown_turns}

【严格约束】
- 先承认用户的不满，简短道歉
- 用1-2句话复述我们已经记录的关于用户的信息（不要展开追问）
- 停止追问任何新资料
- 不要索要联系方式
- 不要问"最看重什么/更在意什么"等偏好问题
- 回复要简短自然，像朋友聊天

【已记录的关于你的信息】
{collected_info_prompt}

请简短回复（1-2句），确认问题后自然收住，不要再追问。
"""
            logger.info(f"[repair_mode] 进入修复模式，原因={repair_reason}, 冷却剩余={user_profile.ask_cooldown_turns}")
            return main_prompt

        if prioritize_user_question:
            # 答疑优先轮次使用轻量提示词，减少 token 与推理耗时
            main_prompt = get_question_priority_dialogue(
                collected_info=collected_info_prompt,
                gender_instruction=gender_instruction,
            )
        else:
            recent_prompt_signatures = (
                (conversation_context.get("preferences") or {}).get("recent_prompt_signatures")
                or []
            )
            recent_style_instruction = self.build_recent_style_instruction(
                conversation_context.get("recent_responses") or [],
                recent_prompt_signatures,
            )
            turn_plan_instruction = (
                "\n【本轮计划】\n"
                f"- 主目标：{field_name_map.get(policy_decision.main_target, policy_decision.main_target or '无')}\n"
                f"- 顺带目标：{field_name_map.get(policy_decision.side_target, policy_decision.side_target or '无')}\n"
                f"- 用户类型：{policy_decision.user_type or '未知'}\n"
                f"- 可进联系方式：{'是' if prompt_can_enter_contact else '否'}"
            )
            main_prompt = get_main_dialogue(
                collected_info=collected_info_prompt,
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
                can_enter_contact=prompt_can_enter_contact,
                turn_plan_instruction=turn_plan_instruction,
                move_instruction=move_instruction,
                recent_style_instruction=recent_style_instruction,
            )

        # 获取上一轮 AI 回复（用于上下文感知提取）
        last_ai_response = conversation_context.get('recent_responses', [])
        last_question = last_ai_response[-1] if last_ai_response else ""
        if last_question:
            logger.debug(f"[上下文] 上一轮AI: {last_question[:50]}...")

        # Phase 2: 获取期望提取字段（短答槽位绑定）
        message_count = conversation_context.get('message_count', 0)
        expected_field = user_profile.get_expected_field_for_short_answer(message_count)
        if expected_field:
            logger.debug(f"[短答槽位绑定] 期望字段: {expected_field}, 当前轮次: {message_count}")

        # 添加信息提取提示词（传递 last_question 和 expected_field 用于上下文感知）
        extraction_prompt = get_extraction(
            user_message=user_message,
            last_question=last_question,
            expected_field=expected_field or ""
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
        return get_extraction(user_message=user_message, last_question=ai_response)

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

        clean_response = self.normalize_assistant_response(response)

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
