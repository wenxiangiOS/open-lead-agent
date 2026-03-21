"""
重构后的聊天服务 - 处理对话并隐晦地收集用户信息

这是一个重构版本，将原来 1113 行的单一服务拆分为多个专职服务：
- ExtractionService: 信息提取
- ValidationService: 数据验证
- DialogueManager: 对话状态管理
- ChatService: 主流程编排
"""

import asyncio
import logging
import os
import random
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.data.user_service import UserService
from src.services.collection.profile_collection_coordinator import ProfileCollectionCoordinator
from src.services.conversation.conversation_rule_service import ConversationRuleService
from src.services.application.process_chat_turn import ProcessChatTurnUseCase
from src.modules.contact_collection.domain.contact_collection_service import ContactCollectionService
from src.modules.contact_collection.domain.refusal_service import RefusalService
from src.modules.conversation.domain.dialogue_manager import DialogueManager
from src.modules.conversation.domain.conversation_ending_service import ConversationEndingService
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.conversation.domain.greeting_service import GreetingService
from src.modules.conversation.domain.input_fallback_service import InputFallbackService
from src.modules.conversation.domain.user_question_service import UserQuestionService
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.profile_collection.domain.ask_tracking_service import AskTrackingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.profile_collection.domain.validation_service import ValidationService
from src.modules.profile_collection.domain.field_skip_service import FieldSkipService
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.utils.validators import InputValidator, RefusalDetector
from src.core.exceptions import ValidationException, AIServiceException
from src.config.settings import settings, get_field_keywords

logger = logging.getLogger(__name__)

SELF_HARM_GUARD_PATTERNS = (
    r"不想活",
    r"活不下去",
    r"想自杀",
    r"结束自己",
    r"轻生",
)
MEDICAL_GUARD_PATTERNS = (
    r"抑郁",
    r"吃什么药",
    r"医疗",
    r"诊断",
)
LEGAL_GUARD_PATTERNS = (
    r"法律",
    r"起诉",
    r"合同",
    r"财产分割",
)
OVERREACH_GUARD_PATTERNS = (
    r"私人微信",
    r"内部名单",
    r"发我.*名单",
    r"绕过流程",
    r"直接给我资料",
)
AI_IDENTITY_GUARD_PATTERNS = (
    r"你是ai吗",
    r"你是AI吗",
    r"你是不是ai",
    r"你是真人还是机器人",
    r"你是不是机器人",
    r"你是机器人吗",
)
ABUSE_GUARD_PATTERNS = (
    r"傻",
    r"滚",
    r"闭嘴",
    r"烦不烦",
    r"有病",
    r"操",
    r"草",
    r"妈的",
    r"去死",
    r"智障",
)
BOUNDARY_PAUSE_PATTERNS = (
    r"不方便",
    r"不想留",
    r"不太想说",
    r"先不说",
    r"先不留",
    r"暂时不留",
)
ASK_GUARD_MANAGED_FIELDS = {"sex", "age", "education", "occupation", "location", "marital_status"}
ASK_GUARD_CORE_FIELDS = {"sex", "age", "education", "occupation", "location", "marital_status"}
ASK_GUARD_MEDIUM_FIELDS = {"monthly_income", "partner_requirement"}
ASK_GUARD_QUESTION_CUES = ("？", "?", "吗", "呢", "嘛", "方便", "请问", "能否", "可否", "多少", "多大", "哪里", "哪个")
ACK_STYLE_MARKERS = ("记下", "收到", "了解", "明白", "好哒", "好呀", "好的呀")
CONTACT_ASK_MARKERS = ("电话", "手机号", "号码", "微信", "联系方式", "留个")
CONTACT_TRANSITION_MARKERS = ("顺便", "资料差不多", "继续推进", "后续方便联系", "对接")
PARTNER_REQUIREMENT_ASK_MARKERS = ("择偶", "偏好", "看重对方", "另一半", "喜欢什么样", "想找什么类型")
LOW_PRIORITY_ASK_PATTERNS = (
    r"(身高|多高|体重|多重).*(\?|？|吗|呢|嘛)",
    r"(怎么称呼|叫什么|怎么叫你|称呼你).*(\?|？|吗|呢|嘛)",
)
CLARIFICATION_USER_PATTERNS = ("没看懂", "看不懂", "听不懂", "啥意思", "什么意思", "解释下", "解释一下")
CLARIFICATION_ASSISTANT_MARKERS = ("换个直白", "简单说", "意思是", "比如", "关键条件", "标准")
AFFIRMATIVE_WORDS = {"嗯", "好", "好的", "行", "可以", "ok", "是的", "对", "是", "恩", "嗯嗯", "好的呢", "好呀"}
PREFERENCE_ORIENTATION_MARKERS = ("les", "gay", "同性", "同性爱", "喜欢女生", "喜欢男生", "找女生", "找男生")
FAREWELL_MARKERS = ("先这样", "随时找我", "有需要再来", "祝你", "拜拜", "下次聊", "好消息")
EXTRACTION_CRITICAL_FIELDS = {"sex", "age", "age_label", "phone", "wechat", "contact"}
NORMAL_COMPLETE_ENDING_TEMPLATES = (
    "好的呀～那你等好消息啦，{timeline}，牵线同事联系前会提前约时间，不会打扰你的～",
    "收到啦～你的信息我这边都记好了，{timeline}，后续联系前我们会先跟你约时间～",
    "行呀，那我先帮你推进匹配，{timeline}，有合适的人选会提前和你确认沟通时间～",
    "没问题～这边就按你的情况去安排，{timeline}，后续联系都会提前打招呼，不会突然打扰你～",
)
PREFERENCE_ACK_VARIANTS = (
    "这个偏好我先记住啦，我会按这个方向优先筛选，后面有合适的第一时间跟你同步。",
    "收到，这个偏好我先记住并整理好，后面我按这个方向优先匹配，有进展就及时告诉你。",
    "好呀，这个条件我先记住收下，后面会按这个方向优先筛选，合适的我尽快同步你。",
)
NO_REPEAT_FIELD_VARIANTS = (
    "先不重复问同一个点了，你可以先说说最在意的匹配条件，我按这个优先筛。",
    "这个点我先不连着追问了，你先告诉我最看重的一项，我按你的优先级来。",
)
PARTNER_REQUIREMENT_ASK_VARIANTS = (
    "顺带聊聊你的偏好吧，你更看重对方哪几点呀？",
    "你这边如果方便，也可以先说一个最看重的匹配条件，我按这个优先筛。",
    "先聊下你的偏好吧，比如你最在意同城、年龄段还是相处感觉？",
)
LOW_PRIORITY_DEFLECT_VARIANTS = (
    "这轮先不问细枝末节资料，我先按你更在意的匹配条件推进。",
    "先不纠结这些次要信息，你先告诉我一个最看重的点，我好优先筛选。",
)
INCOME_ASK_VARIANTS = (
    "另外我轻问一句，你月收入大概在哪个区间呀？不方便说也没关系。",
    "如果你方便的话，我再补一个小问题：你月收入大概在哪个范围？不方便说也没关系。",
)


class ChatService:
    """
    聊天服务 - 处理对话并隐晦地收集用户信息

    核心功能：
    1. 拟人化对话 - 让用户察觉不到是AI
    2. 隐晦信息收集 - 自然地收集用户信息
    3. 智能容错 - 错误提醒有限制
    4. 性别自适应 - 根据性别调整称呼
    5. 目标对象反推 - 利用目标对象性别推断用户性别

    架构：
    - 使用 ExtractionService 处理信息提取
    - 使用 ValidationService 处理数据验证
    - 使用 DialogueManager 管理对话状态
    - 本类主要负责流程编排
    """

    # 核心字段定义（必须收集的字段）
    CORE_FIELDS = ['sex', 'age', 'education', 'occupation', 'location', 'contact']

    # 常见单字姓氏白名单（中国前100大姓）
    COMMON_SURNAMES = frozenset({
        '李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
        '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
        '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
        '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
        '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
        '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
        '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
        '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
        '顾', '侯', '邵', '孟', '龙', '万', '段', '雷', '钱', '汤',
        '尹', '黎', '易', '常', '武', '乔', '贺', '赖', '龚', '文',
        # 常见复姓
        '欧阳', '司马', '上官', '诸葛', '东方', '皇甫', '令狐', '夏侯',
    })
    FORBIDDEN_SALES_PATTERNS = (
        r"(通知|安排|约)(你)?(见面|线下见面)",
        r"(给你|发你|发送给你)(对方)?资料",
        r"(发|给)(你)?(对方)?资料",
        r"对方资料",
    )

    def __init__(
        self,
        ai_service: AIService,
        user_service: UserService
    ):
        """初始化聊天服务"""
        self.ai_service = ai_service
        self.user_service = user_service

        # 无意义输入计数器键名前缀
        self._nonsense_count_prefix = "nonsense_count:"

        # 确认词（用户回复"好的"但没留联系方式）计数器键名前缀
        self._confirm_count_prefix = "confirm_count:"

        # 初始化专职服务
        self.extraction_service = ExtractionService(user_service)
        self.ask_tracking_service = AskTrackingService(user_service)
        self.validation_service = ValidationService()
        self.dialogue_manager = DialogueManager(user_service)
        self.refusal_service = RefusalService()
        self.field_skip_service = FieldSkipService()
        self.contact_service = ContactCollectionService(user_service)
        self.ending_service = ConversationEndingService()
        self.expectation_service = ExpectationService()
        self.greeting_service = GreetingService()
        self.input_fallback_service = InputFallbackService(
            user_service=user_service,
            nonsense_prefix=self._nonsense_count_prefix,
            confirm_prefix=self._confirm_count_prefix,
        )
        self.user_question_service = UserQuestionService()
        self.collection_policy = ProfileCollectionPolicy()
        self.personality_profile = PersonalityProfile()
        self.profile_collection_coordinator = ProfileCollectionCoordinator(self)
        self.conversation_rule_service = ConversationRuleService(self)
        self.process_chat_turn_use_case = ProcessChatTurnUseCase(self)

        # 临时存储可能的拒绝字段
        self._temp_refused_fields = {}
        self._last_ai_failure_reason: Optional[str] = None

    async def process_chat_request(self, request: ChatRequest) -> Dict[str, Any]:
        """处理聊天请求 - 兼容入口，主流程已迁移到 use case。"""
        return await self.process_chat_turn_use_case.execute(request)

    async def _handle_refusal_detection(self, user_message: str, account_id: str, user_profile: UserProfile) -> None:
        """
        处理拒绝检测，包括提前拒绝联系方式

        使用 ContactCollectionService 统一处理联系方式相关的拒绝检测
        """
        # === 入口日志（INFO级别，便于调试）===
        logger.info(f"[拒绝检测-开始] account_id={account_id}, phone_ask_count={user_profile.phone_ask_count}, wechat_ask_count={user_profile.wechat_ask_count}, rejected_phone={user_profile.rejected_phone}, rejected_wechat={user_profile.rejected_wechat}")

        last_response = await self.dialogue_manager.get_last_response(account_id)

        # 检测用户是否拒绝（通用拒绝检测）
        is_refusing = self.refusal_service.is_refusing(user_message)
        if is_refusing and last_response:
            refused_fields = self.extraction_service.infer_refused_fields(last_response)
            self._temp_refused_fields[account_id] = refused_fields

        # === 使用 ContactCollectionService 检测联系方式拒绝 ===
        refusal_result = self.contact_service.detect_refusal(
            message=user_message,
            profile=user_profile,
            last_response=last_response
        )

        if refusal_result:
            contact_type_cn = "电话" if refusal_result.contact_type == 'phone' else "微信"

            if refusal_result.is_final:
                logger.info(f"[拒绝检测] 用户最终拒绝{contact_type_cn}")
            else:
                logger.info(f"[拒绝检测] 用户拒绝{contact_type_cn}，询问次数: {refusal_result.ask_count_after}")

            # 保存更新后的用户档案
            await self.user_service.save_user_profile(account_id, user_profile)

        # === 检查是否应该结束对话 ===
        if self.contact_service.should_end_conversation(user_profile):
            # 只标记联系方式状态，不在拒绝检测阶段强制结束会话。
            # 结束时机交由统一收尾逻辑判定，避免被回归闸门判定为 unexpected_conversation_end。
            user_profile.spam_user = True
            user_profile.contact = self.contact_service.get_status_display(user_profile)
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info("[无效用户] 用户拒绝了微信和电话，已标记状态，等待统一收尾逻辑处理")

    def _is_high_risk_turn(self, user_message: str, prompt: str) -> bool:
        """
        高风险轮次必须走主模型，避免质量回退。
        只做表达层路由，不改变业务规则。
        """
        message = (user_message or "").strip().lower()
        if not message:
            return False

        high_risk_markers = [
            "不留", "拒绝", "不方便", "隐私", "安全吗", "靠谱吗",
            "离异", "分居", "已婚", "帮朋友问", "家人", "代问",
            "电话", "微信", "联系方式",
        ]
        if any(marker in message for marker in high_risk_markers):
            return True

        # 提示词中出现联系方式强约束时，强制主模型
        prompt_markers = ["立即执行-询问电话", "立即执行-询问微信", "立即执行-争取微信", "收尾"]
        return any(marker in (prompt or "") for marker in prompt_markers)

    def _is_low_complexity_turn(self, user_message: str, prompt: str) -> bool:
        """
        低复杂度轮次可尝试快模型：
        - 用户消息较短
        - 提示词长度可控
        - 单意图（疑问符较少）
        """
        msg = (user_message or "").strip()
        prompt_len = len(prompt or "")
        question_marks = msg.count("?") + msg.count("？")
        quick_faq_intent = self.user_question_service.detect_quick_faq_intent(msg)
        deterministic_fields = self._extract_deterministic_profile_fields(msg)
        safe_profile_answer = self._should_use_rule_profile_fast_path(msg, deterministic_fields, "model")

        prompt_limit = 4500
        if quick_faq_intent or safe_profile_answer:
            prompt_limit = 6500

        if len(msg) > 48:
            return False
        if prompt_len > prompt_limit:
            return False
        if question_marks > 1:
            return False
        return True

    def _select_model_for_turn(self, user_message: str, prompt: str) -> str:
        """
        上下文长度 + 意图复杂度 + 风险等级路由。
        无快模型配置时自动回退主模型。
        """
        default_model = getattr(self.ai_service, "model_name", settings.model_name)
        fast_model = os.getenv("AI_FAST_MODEL_NAME", "").strip()
        routing_enabled = os.getenv("AI_ROUTING_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

        if not routing_enabled or not fast_model:
            return default_model

        if self._is_high_risk_turn(user_message, prompt):
            return default_model

        if self._is_low_complexity_turn(user_message, prompt):
            return fast_model

        return default_model

    def _select_max_tokens_for_turn(self, user_message: str, prompt: str) -> int:
        """
        按轮次复杂度动态控制输出长度，降低平均时延与成本。
        """
        default_max_tokens = self._env_int("CHAT_AI_MAX_TOKENS", 360)
        if default_max_tokens <= 0:
            default_max_tokens = 360

        high_risk_max_tokens = self._env_int("CHAT_AI_HIGH_RISK_MAX_TOKENS", default_max_tokens)
        low_complexity_max_tokens = self._env_int("CHAT_AI_LOW_COMPLEXITY_MAX_TOKENS", 220)
        long_prompt_threshold = self._env_int("CHAT_AI_LONG_PROMPT_CHAR_THRESHOLD", 5000)
        long_prompt_max_tokens = self._env_int("CHAT_AI_LONG_PROMPT_MAX_TOKENS", 180)

        if self._is_high_risk_turn(user_message, prompt):
            return max(80, min(default_max_tokens, high_risk_max_tokens))

        if self._is_low_complexity_turn(user_message, prompt):
            return max(80, min(default_max_tokens, low_complexity_max_tokens))

        prompt_len = len(prompt or "")
        if prompt_len >= max(1, long_prompt_threshold):
            return max(80, min(default_max_tokens, long_prompt_max_tokens))

        return default_max_tokens

    @staticmethod
    def _matches_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
        content = str(text or "")
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)

    def _get_risk_guard_response(self, user_message: str, user_profile: UserProfile) -> Optional[str]:
        """高风险输入走固定护栏，不再继续字段收集。"""
        message = (user_message or "").strip()
        if not message:
            return None

        if self._matches_any_pattern(message, SELF_HARM_GUARD_PATTERNS):
            return (
                "听起来你现在真的很难受，先保证安全很重要。"
                "如果你身边有人，先立刻联系家人或朋友陪着你；要是已经有伤害自己的想法，也请尽快联系当地紧急求助或心理热线。"
                "你并不孤单。"
            )

        if self._matches_any_pattern(message, MEDICAL_GUARD_PATTERNS):
            return (
                "这个我不适合直接给你诊疗或用药建议，最好尽快找专业医生或心理咨询渠道做评估。"
                "如果你现在状态很差，也建议先联系身边可信的人陪你一下。"
            )

        if self._matches_any_pattern(message, LEGAL_GUARD_PATTERNS):
            return "这类法律问题我不适合替你下结论，建议咨询专业律师或以当地官方渠道说明为准，会更稳妥。"

        if self._matches_any_pattern(message, OVERREACH_GUARD_PATTERNS):
            return "这个不方便直接给你，涉及隐私和合规，我们这边都要按流程保护双方信息。"

        if self._matches_any_pattern(message, AI_IDENTITY_GUARD_PATTERNS):
            return "我这边就是负责跟你对接了解情况的小缘呀，你要是担心流程、隐私或真实性，我可以直接跟你说清楚。"

        if self._matches_any_pattern(message, ABUSE_GUARD_PATTERNS):
            return "我理解你现在有点烦，没关系，我先不追问。你要是愿意聊，我们可以慢慢说。"

        return None

    def _get_boundary_pause_response(self, user_message: str) -> Optional[str]:
        """
        用户在边界/顾虑场景时，本轮只降温承接，不推进字段收集。
        """
        message = (user_message or "").strip()
        if not message:
            return None
        # FAQ/联系方式偏好优先于 boundary pause，避免把“靠谱吗/安全吗/留微信可以吗”
        # 这类明确答疑或切流程请求误拦成固定安抚话术。
        if self.user_question_service.detect_quick_faq_intent(message):
            return None
        if self.contact_service.prefers_wechat_over_phone(message, UserProfile(account_id="boundary_probe")):
            return None
        if not self._matches_any_pattern(message, BOUNDARY_PAUSE_PATTERNS):
            return None
        return "理解你的顾虑，这轮我先不追问资料。你要是想先确认流程、隐私或真实性，我可以先跟你讲清楚。"

    def _build_turn_decision(
        self,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any] | None = None,
    ) -> TurnDecision:
        """
        单轮统一决策器（结构化输出，供主流程/兜底/快答共用）。
        """
        context = conversation_context or {}
        message_count = int(context.get("message_count", 0))
        stage = self.dialogue_manager.detect_conversation_stage(user_profile, message_count)
        message = (user_message or "").strip()

        intent = self.user_question_service.detect_quick_faq_intent(message) or "general"
        risk = "none"
        next_action = "continue"
        response_channel = "model"

        if self._get_risk_guard_response(message, user_profile):
            risk = "high_risk"
            next_action = "risk_guard"
            response_channel = "fixed_template"
        elif self._get_boundary_pause_response(message):
            risk = "boundary"
            next_action = "boundary_pause"
            response_channel = "fixed_template"
        elif intent != "general":
            next_action = "quick_faq"
            response_channel = "quick_faq"

        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=message,
            message_count=message_count,
        )
        ask_field = policy_decision.main_target

        tone_policy = {
            "ack_budget_per_n_turns": 3,
            "max_question_per_turn": 1,
            "enforce_contact_transition": True,
            "core_streak_max": 2,
        }
        return TurnDecision(
            intent=intent,
            risk=risk,
            stage=stage,
            next_action=next_action,
            ask_field=ask_field,
            response_channel=response_channel,
            tone_policy=tone_policy,
        )

    @staticmethod
    def _pick_non_repeating_template(templates: tuple[str, ...], last_response: str) -> str:
        if not templates:
            return ""
        normalized_last = (last_response or "").strip()
        candidates = [tpl for tpl in templates if tpl.strip() != normalized_last]
        if not candidates:
            candidates = list(templates)
        return random.choice(candidates)

    def _build_rotating_ending_message(self, user_profile: UserProfile, last_response: str = "") -> str:
        timeline_text = self.expectation_service.get_closing_timeline_text(user_profile)
        rendered = tuple(
            template.format(timeline=timeline_text).replace("  ", " ").strip()
            for template in NORMAL_COMPLETE_ENDING_TEMPLATES
        )
        return self._pick_non_repeating_template(rendered, last_response)

    @staticmethod
    def _is_contact_ask_response(text: str) -> bool:
        content = str(text or "")
        return any(marker in content for marker in CONTACT_ASK_MARKERS)

    @staticmethod
    def _is_partner_requirement_ask_response(text: str) -> bool:
        content = str(text or "")
        if not content:
            return False
        if not any(cue in content for cue in ASK_GUARD_QUESTION_CUES):
            return False
        return any(marker in content for marker in PARTNER_REQUIREMENT_ASK_MARKERS)

    @staticmethod
    def _contains_ack_style(text: str) -> bool:
        content = str(text or "")
        return any(marker in content for marker in ACK_STYLE_MARKERS)

    @staticmethod
    def _strip_leading_ack_clause(response: str) -> str:
        content = str(response or "").strip()
        if not content:
            return content
        # 仅移除最前面的“收到/记下了”短从句，避免每轮机械复述。
        pattern = r"^(?:好(?:的)?(?:呀|哒)?|收到(?:啦)?|了解(?:啦)?|明白(?:啦)?)(?:[^。！？!?]{0,20})(?:[，,。！？!?~～]+)\s*"
        cleaned = re.sub(pattern, "", content)
        return cleaned or content

    def _ensure_contact_transition_natural(
        self,
        last_response: str,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        content = str(response or "").strip()
        if not content or not self._is_contact_ask_response(content):
            return content

        previous = str(last_response or "")
        prev_about_contact = self._is_contact_ask_response(previous)
        has_transition = any(marker in content for marker in CONTACT_TRANSITION_MARKERS)
        if prev_about_contact or has_transition:
            return content

        profile_ready = self.collection_policy.has_serviceable_profile(user_profile)
        user_mentions_contact = any(k in str(user_message or "") for k in ["电话", "手机号", "号码", "微信", "联系方式"])
        if user_mentions_contact:
            return content
        if profile_ready:
            return f"你这边资料我先整理好了，后续方便联系推进，{content}"
        return f"我先不急着推进联系方式，先按你刚说的继续聊会更自然。"

    def _apply_dialogue_style_guard(
        self,
        last_response: str,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
        tone_policy: Dict[str, Any] | None = None,
    ) -> str:
        """
        统一表达层防抖：
        1) 连续轮次避免机械“收到/记下”复述
        2) 联系方式提问必须有自然过渡
        """
        content = str(response or "").strip()
        if not content:
            return content

        previous = str(last_response or "")
        user_text = str(user_message or "").strip()
        prev_about_contact = self._is_contact_ask_response(previous)
        asks_contact_now = self._is_contact_ask_response(content)
        current_is_affirmative = user_text in AFFIRMATIVE_WORDS
        if current_is_affirmative and prev_about_contact and asks_contact_now:
            return "我先不重复催联系方式，你方便时再发就行。我们也可以先聊你更在意的匹配点。"
        if current_is_affirmative and (not prev_about_contact) and asks_contact_now:
            return "收到，你刚这句我先接住。我们先按你在意的点继续聊，不急着留联系方式。"

        if self._contains_ack_style(previous) and self._contains_ack_style(content):
            content = self._strip_leading_ack_clause(content)
        # 追问句前优先去掉“收到/了解/好哒”类前置复述，降低模板化复读率。
        if any(cue in content for cue in ASK_GUARD_QUESTION_CUES) and self._contains_ack_style(content):
            content = self._strip_leading_ack_clause(content)
        # 即使上一轮不是复述，也尽量去掉当前轮前置“收到/记下”从句，降低 ack_overuse。
        if self._contains_ack_style(content):
            content = self._strip_leading_ack_clause(content)

        content = self._ensure_contact_transition_natural(previous, content, user_profile, user_message=user_message)
        content = self._enforce_field_interleaving(
            previous,
            content,
            user_profile,
            tone_policy=tone_policy or {},
            user_message=user_message,
        )
        content = self._avoid_repeat_loop(previous, content, user_message=user_message)
        content = self._avoid_preference_hard_ending(user_text, content)
        return content

    def _avoid_repeat_loop(self, last_response: str, response: str, user_message: str = "") -> str:
        """避免同一句兜底回复连续出现，用户要解释时优先给解释。"""
        content = str(response or "").strip()
        previous = str(last_response or "").strip()
        if not content:
            return content

        if content != previous:
            return content

        message = str(user_message or "")
        wants_clarification = any(pattern in message for pattern in CLARIFICATION_USER_PATTERNS)
        if wants_clarification:
            return "我换个直白说法：我说的匹配点，就是你在意的几个条件，比如年龄范围、城市、工作节奏和相处感觉。"

        if "匹配点" in content:
            return "我换个说法：你可以先告诉我你最看重哪一点，比如同城、年龄段，还是工作节奏。"

        return "我先换个说法继续聊，避免重复问你同一个点。"

    @staticmethod
    def _pick_variant(options: tuple[str, ...], default: str) -> str:
        if not options:
            return default
        return random.choice(options)

    def _avoid_preference_hard_ending(self, user_message: str, response: str) -> str:
        """
        在用户表达择偶取向时，避免“祝福式结束语”导致会话被判定提前收尾。
        """
        message = str(user_message or "").lower()
        content = str(response or "").strip()
        if not content:
            return content
        if not any(marker in message for marker in PREFERENCE_ORIENTATION_MARKERS):
            return content
        if not any(marker in content for marker in FAREWELL_MARKERS):
            return content
        # 保留边界说明，去掉明显收尾语气。
        sanitized = re.sub(r"(祝你[^\n。！？!?]*[。！？!?]?)", "", content).strip()
        sanitized = re.sub(r"(有需要再来找我|先这样啦|拜拜[👋!]?)", "", sanitized).strip()
        if sanitized:
            return sanitized
        return "谢谢你坦诚说这个，我先把规则边界讲清楚：这边当前主要做异性匹配流程。"

    def _detect_asked_fields_from_response(self, response: str) -> set[str]:
        text = str(response or "")
        if not text:
            return set()
        if not any(cue in text for cue in ASK_GUARD_QUESTION_CUES):
            return set()

        asked_fields: set[str] = set()
        field_keywords = get_field_keywords()
        # 与回归脚本口径对齐：婚况问法常见表述并不总在关键词表里。
        if re.search(r"(单身状态|婚况|婚姻状态|离异|未婚|已婚)", text):
            asked_fields.add("marital_status")
        if re.search(r"(想找什么类型|择偶要求|期待另一半|喜欢什么类型|看重对方哪几点|另一半有没有|对方哪几点)", text):
            asked_fields.add("partner_requirement")
        for field, keywords in field_keywords.items():
            if field in {"height", "weight", "last_name", "contact"}:
                continue
            if any(keyword and keyword in text for keyword in keywords):
                asked_fields.add(field)
        return asked_fields

    def _enforce_field_interleaving(
        self,
        last_response: str,
        response: str,
        user_profile: UserProfile,
        tone_policy: Dict[str, Any] | None = None,
        user_message: str = "",
    ) -> str:
        """
        连续核心字段追问硬约束：
        - 最近3轮主追问都在核心字段时，当前轮不继续核心字段连问
        - 优先切入中等字段（择偶要求/月收入），否则给承接缓冲句
        """
        content = str(response or "").strip()
        if not content:
            return content
        if self._is_contact_ask_response(content):
            return content
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in LOW_PRIORITY_ASK_PATTERNS):
            return self._pick_variant(
                LOW_PRIORITY_DEFLECT_VARIANTS,
                "这轮先不问细枝末节资料，我先按你更在意的匹配条件推进。",
            )

        asked_fields = self._detect_asked_fields_from_response(content)
        asks_core = bool(asked_fields & ASK_GUARD_CORE_FIELDS)
        asks_medium = bool(asked_fields & ASK_GUARD_MEDIUM_FIELDS)
        prev_asked_fields = self._detect_asked_fields_from_response(last_response)
        repeated_managed = (prev_asked_fields & asked_fields) & (ASK_GUARD_CORE_FIELDS | ASK_GUARD_MEDIUM_FIELDS)
        if "partner_requirement" in repeated_managed:
            return self._pick_variant(PREFERENCE_ACK_VARIANTS, PREFERENCE_ACK_VARIANTS[0])
        if "monthly_income" in repeated_managed:
            return "收入这块我先按你前面说的来，不用这轮重复。你也可以先说说你更在意的匹配条件。"

        # 若用户本轮明确给出择偶偏好，不继续追核心字段，优先接住偏好信息。
        user_text = str(user_message or "")
        preference_cues = ["想找", "高挑", "高一点", "不超过", "年龄", "择偶", "偏好", "看重", "成熟稳重", "同城优先"]
        if asks_core and any(cue in user_text for cue in preference_cues):
            return self._pick_variant(PREFERENCE_ACK_VARIANTS, PREFERENCE_ACK_VARIANTS[0])

        if (not asks_core) or asks_medium:
            return content

        repeated_core = (prev_asked_fields & asked_fields) & ASK_GUARD_CORE_FIELDS
        if repeated_core:
            if (
                not user_profile.collection_progress.get("partner_requirement", False)
                and not self._is_partner_requirement_ask_response(last_response)
            ):
                return self._pick_variant(NO_REPEAT_FIELD_VARIANTS, NO_REPEAT_FIELD_VARIANTS[0])
            return self._pick_variant(NO_REPEAT_FIELD_VARIANTS, NO_REPEAT_FIELD_VARIANTS[0])

        recent = [f for f in (user_profile.recent_asked_fields or []) if f in ASK_GUARD_CORE_FIELDS]
        core_streak = 0
        for field in reversed(recent):
            if field in ASK_GUARD_CORE_FIELDS:
                core_streak += 1
            else:
                break

        core_streak_max = int((tone_policy or {}).get("core_streak_max", 2))
        # 兜底：若历史核心追问总量已较高，当前轮直接触发穿插，避免出现长核心连问。
        # 这里用 ask_count 累积而非 recent_asked_fields，防止追问追踪在边界轮次漏记。
        total_core_ask_count = 0
        for field in ASK_GUARD_CORE_FIELDS:
            total_core_ask_count += int(user_profile.get_ask_count(field) or 0)
        if total_core_ask_count >= max(3, core_streak_max):
            if (not user_profile.collection_progress.get("partner_requirement", False)) and (not self._is_partner_requirement_ask_response(last_response)):
                return self._pick_variant(PARTNER_REQUIREMENT_ASK_VARIANTS, PARTNER_REQUIREMENT_ASK_VARIANTS[0])
            if (
                not user_profile.collection_progress.get("monthly_income", False)
                and bool(user_profile.occupation)
                and ("月收入" not in last_response and "收入" not in last_response and "薪资" not in last_response)
            ):
                return self._pick_variant(INCOME_ASK_VARIANTS, INCOME_ASK_VARIANTS[0])

        if core_streak < max(1, core_streak_max):
            return content

        if (not user_profile.collection_progress.get("partner_requirement", False)) and (not self._is_partner_requirement_ask_response(last_response)):
            return self._pick_variant(PARTNER_REQUIREMENT_ASK_VARIANTS, PARTNER_REQUIREMENT_ASK_VARIANTS[0])

        if (
            not user_profile.collection_progress.get("monthly_income", False)
            and bool(user_profile.occupation)
            and ("月收入" not in last_response and "收入" not in last_response and "薪资" not in last_response)
        ):
            return self._pick_variant(INCOME_ASK_VARIANTS, INCOME_ASK_VARIANTS[0])

        return "我们先不连着问资料。这里说的匹配点，就是你在意的条件，比如同城、年龄段、工作节奏。你先说一个最看重的就行。"

    async def _call_ai(self, prompt: str, account_id: str, user_message: str = "") -> str:
        """
        调用 AI 服务（带超时控制）

        Args:
            prompt: 完整的对话提示词
            account_id: 用户ID

        Returns:
            str: AI 回复内容

        Raises:
            AIServiceException: AI 调用失败或超时
        """
        import time
        ai_start_time = time.perf_counter()
        chosen_model = self._select_model_for_turn(user_message, prompt)
        response_max_tokens = self._select_max_tokens_for_turn(user_message, prompt)
        soft_timeout = max(0.5, self._env_float("CHAT_AI_TIMEOUT_SECONDS", 20.0))
        hard_timeout = self._env_float("CHAT_AI_HARD_TIMEOUT_SECONDS", 25.0)
        if hard_timeout <= soft_timeout:
            hard_timeout = soft_timeout + 0.5
        logger.info(
            f"[⏱️ 性能] 开始调用AI: account_id={account_id}, model={chosen_model}, prompt_chars={len(prompt) if prompt else 0}, max_tokens={response_max_tokens}, soft_timeout={soft_timeout:.1f}s, hard_timeout={hard_timeout:.1f}s"
        )
        self._last_ai_failure_reason = None

        try:
            # 使用总时长硬超时兜底，避免 SDK/重试链路长尾卡死。
            response = await asyncio.wait_for(
                self.ai_service.generate_response(
                    message=prompt,
                    system_prompt="你是一个说中文的AI助手，请用中文回复用户。",
                    max_tokens=response_max_tokens,
                    timeout=soft_timeout,
                    model_name=chosen_model,
                ),
                timeout=hard_timeout,
            )
            ai_end_time = time.perf_counter()
            ai_duration = ai_end_time - ai_start_time
            logger.info(f"[⏱️ 性能] AI调用完成: account_id={account_id}, 耗时={ai_duration:.3f}秒")
            return response
        except asyncio.TimeoutError:
            logger.error(f"[AI调用] 总时长触发硬超时: account_id={account_id}, hard_timeout={hard_timeout:.1f}s，返回空响应")
            self._last_ai_failure_reason = "hard_timeout"
            return ""
        except AIServiceException as e:
            # AI 服务失败时返回空响应，不暴露 AI 身份
            logger.error(f"[AI调用] 失败: {e}，返回空响应")
            details = getattr(e, "details", {}) or {}
            status_code = details.get("status_code")
            reason = "ai_service_error"
            msg = str(e or "")
            if status_code == 403 or "AccountOverdueError" in msg:
                reason = "account_overdue_403"
            elif status_code and 400 <= int(status_code) < 500:
                reason = f"client_error_{int(status_code)}"
            self._last_ai_failure_reason = reason
            return ""
        except Exception as e:
            logger.error(f"[AI调用] 未预期的错误: {e}，返回空响应")
            self._last_ai_failure_reason = "unexpected_error"
            return ""

    async def _process_collection_result(
        self,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        user_message: str,
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
        turn_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """处理收集结果"""
        last_response = await self.dialogue_manager.get_last_response(account_id) or ""
        extracted_data = self._apply_extraction_guards(extracted_data, user_message, last_response=last_response)
        # 处理提取的数据
        collection_result = await self.extraction_service.process_extracted_data(
            account_id,
            user_profile,
            extracted_data,
            user_message=user_message,
            extraction_meta=extraction_meta,
            turn_id=turn_id,
        )

        # process_extracted_data 通过 user_service 持久化字段，刷新后再做收尾判断，
        # 否则同一轮新收集到的年龄/身高/联系方式会被旧 profile 漏掉。
        user_profile = await self.user_service.get_user_profile(account_id)

        # === 使用统一的收尾服务检测收尾场景 ===
        # 调用 check_and_get_ending，参数顺序：user_message, profile, collection_result
        # 返回结构：{'scenario': str, 'use_ai': bool, 'description': str, 'response': str, ...}
        # 内部已调用 update_profile_for_ending，无需单独调用
        ending_info = self.ending_service.check_and_get_ending(
            user_message,        # 第1个参数：用户消息
            user_profile,        # 第2个参数：用户档案
            collection_result    # 第3个参数：收集结果
        )

        if ending_info:
            scenario = ending_info['scenario']
            use_ai = ending_info['use_ai']
            logger.info(f"[收尾检测] 检测到收尾场景: {scenario}, AI生成: {use_ai}")

            # 保存已更新的用户状态（check_and_get_ending 内部已更新 profile）
            await self.user_service.save_user_profile(account_id, user_profile)

            # AI 生成场景：不返回预设话术，由外部流程处理
            if use_ai:
                # 将 extra_instructions 传递给外部流程（通过 collection_result）
                collection_result['ending_info'] = ending_info
                logger.info(f"[收尾检测] AI生成场景，传递给外部处理: {scenario}")
            else:
                # 预设话术场景：直接返回
                response = ending_info.get('response', '')
                is_silent = response == ""  # 空模板表示静默场景

                result = {
                    "success": True,
                    "response": response,
                    "dialogId": "",
                    "collected_info": {},
                    "collected": False
                }
                if is_silent:
                    result["silent"] = True

                logger.info(f"[收尾检测] 返回预设话术，场景: {scenario}, 静默: {is_silent}")
                return result

        # === 以下为保留的旧逻辑，逐步迁移到收尾服务 ===
        # 检测离异手续状态（已办妥的情况，不是收尾场景）
        divorce_complete_keywords = [
            '办妥了', '办好了', '已办妥', '已办好', '办完了', '已经办妥', '已经办好',
            '手续办了', '手续好了', '办妥', '办好', '离了', '办了'
        ]
        if user_profile.marital_status == '离异' or '离异' in str(user_profile.marital_status):
            if any(kw in user_message for kw in divorce_complete_keywords):
                # 用户确认手续已办妥，更新婚况状态
                user_profile.marital_status = "离异（手续已办妥）"
                user_profile.divorce_confirmed = True
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[离异手续已办妥] 用户说: {user_message}，更新 marital_status=离异（手续已办妥）")

        # 处理拒绝字段
        if account_id in self._temp_refused_fields:
            refused_fields = self._temp_refused_fields[account_id]
            collected_fields = [f['field'] for f in collection_result.get('all_fields', [])]

            # 标记被拒绝但未被提取的字段
            for field in refused_fields:
                if field not in collected_fields:
                    await self.user_service.skip_user_profile_field(account_id, field)
                    logger.info(f"[拒绝标记] 用户拒绝字段: {field}")

            del self._temp_refused_fields[account_id]

        return collection_result

    async def _handle_contact_validation(
        self,
        account_id: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        ai_response: str,
        user_message: str = "",
    ) -> str:
        """处理联系方式验证"""
        # 检查是否收集到联系方式（电话或微信）
        collected_contact = None
        collected_phone = None
        collected_wechat = None
        for field_info in collection_result.get('all_fields', []):
            if field_info.get('field') == 'contact':
                collected_contact = field_info.get('value')
            elif field_info.get('field') == 'phone':
                collected_phone = field_info.get('value')
            elif field_info.get('field') == 'wechat':
                collected_wechat = field_info.get('value')

        fallback_contacts = self._extract_contacts_from_message(user_message)
        fallback_contact = self._extract_contact_candidate_from_message(user_message)
        fallback_candidate = fallback_contact["value"] if fallback_contact else None
        fallback_hint = fallback_contact["type"] if fallback_contact else None
        fallback_contaminated = bool(fallback_contact.get("contaminated")) if fallback_contact else False
        next_action = self.contact_service.get_next_action(user_profile, user_message)
        contact_value = collected_phone or collected_contact
        invalid_contact_attempt = collection_result.get("invalid_contact_attempt") or fallback_candidate

        if contact_value is None and fallback_contacts.get("phone"):
            contact_value = fallback_contacts["phone"]
        if collected_wechat is None and fallback_contacts.get("wechat"):
            collected_wechat = fallback_contacts["wechat"]

        if contact_value is None and collected_wechat is None and fallback_candidate:
            from src.utils.validators import ContactValidator

            is_valid_fallback, fallback_type, _ = ContactValidator.is_valid_contact(fallback_candidate)
            if is_valid_fallback and not fallback_contaminated:
                if fallback_hint == "wechat":
                    collected_wechat = fallback_candidate
                else:
                    contact_value = fallback_candidate
                logger.info(f"[联系方式兜底] 从原始消息恢复联系方式: type={fallback_hint or fallback_type}, value={fallback_candidate}")
            elif is_valid_fallback and fallback_contaminated:
                logger.info(
                    f"[联系方式兜底] 检测到污染输入，拒绝自动收集: type={fallback_hint or fallback_type}, value={fallback_candidate}"
                )

        # 用户可能直接发了“看起来像联系方式”的内容，但提取器没识别到字段。
        # 在联系方式流程中启用上下文兜底，确保能走到“格式校验失败 -> 重新确认”。
        if contact_value is None and collected_wechat is None and not invalid_contact_attempt:
            hinted_attempt, hinted_type = self._infer_contact_attempt_from_context(user_message, next_action.value)
            if hinted_attempt:
                invalid_contact_attempt = hinted_attempt
                fallback_hint = fallback_hint or hinted_type

        contact_value = contact_value or collected_phone or collected_contact
        logger.info(f"[联系方式检查] collected_contact={contact_value}, collected_wechat={collected_wechat}, all_fields={collection_result.get('all_fields', [])}")

        # 如果收集到微信，设置 wechat_collected 标志
        if collected_wechat:
            user_profile.wechat = collected_wechat
            user_profile.wechat_collected = True
            # 非香港用户：微信也可以作为联系方式
            is_hong_user = self._is_hong_user(user_profile.location)
            if not is_hong_user:
                user_profile.collection_progress['contact'] = True
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[微信收集] 设置 wechat_collected=True, 香港用户={is_hong_user}")

        # 如果没有收集到任何联系方式，检查是否所有字段都已完成
        if contact_value is None and collected_wechat is None:
            if invalid_contact_attempt:
                logger.info(f"[联系方式检查] 检测到疑似无效联系方式输入: {invalid_contact_attempt}")
                if fallback_contaminated and (fallback_hint == "wechat" or "微信" in user_message):
                    return f"{user_profile.get_greeting()}，这个微信号里好像混了多余字符，麻烦你重新确认一下微信号哈～"
                if fallback_hint == "wechat" or "微信" in user_message:
                    is_valid, error_msg = self.validation_service.validate_wechat(invalid_contact_attempt)
                    if not is_valid and error_msg:
                        error_msg = f"{user_profile.get_greeting()}，{error_msg}"
                else:
                    is_valid, error_msg, _ = await self.validation_service.validate_contact(
                        invalid_contact_attempt,
                        user_profile,
                        account_id,
                        self.user_service
                    )
                if not is_valid:
                    return error_msg or ""

            # 检查核心字段是否全部收集
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 如果资料已足够服务，检查联系方式收集流程是否也结束
            if profile_ready_for_service and contact_collected:
                # 检查联系方式收集流程是否还有下一步动作
                from src.services.collection.contact_collection_service import NextAction
                next_action = self.contact_service.get_next_action(user_profile)
                if next_action not in [NextAction.NONE, NextAction.END_CONVERSATION]:
                    # 联系方式收集流程还没结束，返回 AI 原回复（包含争取话术）
                    logger.info(f"[收尾检查] 联系方式收集流程未结束，next_action={next_action.value}")
                    return ai_response

                logger.info(f"[收尾检查] 所有字段已完成，返回固定轮转收尾回复")
                last_response = await self.dialogue_manager.get_last_response(account_id) or ""
                return self._build_rotating_ending_message(user_profile, last_response)

            # 否则返回原回复
            return ai_response

        # 用户提供了联系方式（电话或微信），重置确认词计数器
        await self.input_fallback_service.reset_confirm_count(account_id)
        logger.info(f"[联系方式验证] 用户提供了联系方式，重置确认词计数器")

        # 如果只收集到微信（没有电话），尝试争取电话
        if contact_value is None and collected_wechat:
            has_phone_already = bool(user_profile.phone_collected and user_profile.phone)
            # 微信已在上面的代码中处理（设置 wechat_collected=True）
            # 检查是否可以收尾
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            # === 新增：争取电话号码 ===
            # 如果用户没有提供电话，且还没争取过电话，则再问一次电话
            # 注意：不在这里设置 phone_ask_count，让 _handle_refusal 在用户拒绝时递增
            # 这样用户第一次拒绝后还有一次争取机会
            if not has_phone_already and not user_profile.rejected_phone and user_profile.phone_ask_count < 1:
                logger.info(f"[微信收集] 尝试争取电话号码")
                call_name = user_profile.get_greeting()
                return "好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～"

            # 已经争取过电话，用户还是只留微信，检查是否可以收尾
            if profile_ready_for_service and contact_collected:
                logger.info(f"[微信收集] 核心字段全部收集完成，准备收尾")
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                self.ending_service.update_profile_for_ending('normal_complete', user_profile)
                await self.user_service.save_user_profile(account_id, user_profile)
                last_response = await self.dialogue_manager.get_last_response(account_id) or ""
                return self._build_rotating_ending_message(user_profile, last_response)
            else:
                # === 资料未达到可服务阈值，继续收集重要字段 ===
                decision = self.collection_policy.decide(
                    user_profile,
                    allow_contact_target=False,
                )
                logger.info(f"[微信收集] 资料未完成，继续推进字段: {decision.main_target}")

                call_name = user_profile.get_greeting()
                field_names = {
                    'sex': '是小哥哥还是小姐姐呀',
                    'age': '今年多大呢',
                    'education': '学历是什么呀',
                    'occupation': '做什么工作的呀',
                    'location': '在哪个城市呢',
                    'marital_status': '现在是单身状态在认真了解吗'
                }
                first_missing = decision.main_target
                if first_missing and first_missing in field_names:
                    question = field_names[first_missing]
                    return f"好的呀，我先记下啦。顺带问你一下，{question}"
                else:
                    return "好的呀，我先记下啦。你也可以再简单说说自己的情况～"

        # 验证电话号码
        logger.info(f"[联系方式验证] 开始验证电话: {contact_value}")

        is_valid, error_msg, success_msg = await self.validation_service.validate_contact(
            contact_value,
            user_profile,
            account_id,
            self.user_service  # 传入共享的 user_service
        )

        if is_valid:
            logger.info(f"[联系方式验证成功]")

            # === 设置电话号码和 phone_collected ===
            normalized_phone = re.sub(r'\D', '', contact_value or '')
            if normalized_phone.startswith('86') and len(normalized_phone) == 13 and normalized_phone[2] == '1':
                normalized_phone = normalized_phone[2:]

            user_profile.phone = normalized_phone or contact_value
            user_profile.phone_collected = True
            user_profile.contact = user_profile.get_contact_status()
            logger.info(f"[联系方式验证] 设置 phone={user_profile.phone}, phone_collected=True")

            # === 重置电话询问计数（用户已提供电话，无需再争取）===
            user_profile.phone_ask_count = 0
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[联系方式验证] 重置 phone_ask_count = 0 并保存")

            # === 检查是否需要询问微信 ===
            next_action = self.contact_service.get_next_action(user_profile)
            logger.info(f"[联系方式验证] 下一步动作: {next_action}")

            if next_action.value == "ask_wechat":
                # 需要询问微信
                logger.info(f"[联系方式验证] 电话已收集，需要询问微信，wechat_ask_count={user_profile.wechat_ask_count}")
                # 询问次数在用户明确拒绝时由拒绝检测统一递增，这里只发起询问，不提前计数。

                call_name = user_profile.get_greeting()
                wechat_ask_response = f"好的呀～{call_name}的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～"

                # === 重要：将微信询问回复添加到 recent_responses ===
                # 这样后续拒绝检测时 get_last_response 才能正确获取到这条微信询问
                await self.dialogue_manager.update_recent_responses(account_id, wechat_ask_response)
                logger.info(f"[联系方式验证] 已将微信询问添加到 recent_responses")

                return wechat_ask_response

            # === 核心字段完成度检查 ===
            # 检查核心字段是否全部收集（联系方式：电话或微信有一个即可）
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 核心字段检查（排除contact，因为上面单独检查了
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            if profile_ready_for_service and contact_collected:
                # === 核心字段全部收集完成，收尾 ===
                logger.info(f"[核心字段] 全部收集完成，准备收尾")

                # 标记剩余未收集字段为"跳过"
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                self.ending_service.update_profile_for_ending('normal_complete', user_profile)
                await self.user_service.save_user_profile(account_id, user_profile)

                # 返回固定轮转收尾回复（避免重复模板与自由发挥漂移）
                last_response = await self.dialogue_manager.get_last_response(account_id) or ""
                return self._build_rotating_ending_message(user_profile, last_response)
            else:
                # === 资料未达到可服务阈值，继续收集重要字段 ===
                decision = self.collection_policy.decide(
                    user_profile,
                    allow_contact_target=False,
                )
                logger.info(f"[核心字段] 资料未完成，继续推进字段: {decision.main_target}")

                call_name = user_profile.get_greeting()
                field_names = {
                    'sex': '是小哥哥还是小姐姐呀',
                    'age': '今年多大呢',
                    'education': '学历是什么呀',
                    'occupation': '做什么工作的呀',
                    'location': '在哪个城市呢',
                    'marital_status': '现在是单身状态在认真了解吗'
                }
                first_missing = decision.main_target
                if first_missing and first_missing in field_names:
                    question = field_names[first_missing]
                    return f"好的呀～{call_name}的电话我先记下啦。顺带问你一下，{question}"
                else:
                    return f"好的呀～{call_name}的电话我先记下啦。你也可以再简单说说自己的情况～"
        else:
            # 撤销保存 - 直接修改传入的 user_profile 对象
            user_profile.contact = None
            user_profile.collection_progress['contact'] = False
            await self.user_service.save_user_profile(account_id, user_profile)

            logger.info(f"[联系方式验证失败] 已撤销保存")
            # 如果 error_msg 为空，表示不回复（第3次及以上错误），返回空字符串
            if error_msg == "":
                return ""
            return error_msg

    def _clean_response(self, response: str) -> str:
        """清理回复（移除 XML 标签）"""
        import re
        return re.sub(r'<extract>.*?</extract>', '', response, flags=re.DOTALL).strip()

    def _strip_collection_prompts_for_faq(self, response: str) -> str:
        """
        FAQ/顾虑优先轮次下，移除资料收集追问，避免“先答疑又追问年龄”。
        """
        if not response:
            return response

        segments = [seg.strip() for seg in re.split(r'(?<=[。！？!?])\s*', response) if seg.strip()]
        if not segments:
            return response

        blocked_keywords = [
            "年龄", "多大", "年龄段",
            "学历", "职业", "工作",
            "哪个城市", "在哪个城市", "城市",
            "电话", "微信", "联系方式",
            "身高", "体重", "婚况", "月薪",
        ]

        kept = []
        for seg in segments:
            hit_positions = [seg.find(kw) for kw in blocked_keywords if kw in seg]
            if not hit_positions:
                kept.append(seg)
                continue

            # 若同一句里“先答疑后追问”，保留追问关键词前的答疑部分
            first_hit = min(hit_positions)
            prefix = seg[:first_hit].rstrip("，,；;。!！?？ ")
            if len(prefix) >= 6 and not any(kw in prefix for kw in blocked_keywords):
                kept.append(prefix + "。")

        if kept:
            return " ".join(kept).strip()

        # 兜底：避免把追问话术原样返回
        return "这个问题我先给你说明清楚。"

    def _ensure_conservative_empathy(self, user_message: str, response: str) -> str:
        """
        保守型用户场景补齐共情关键词，降低字面断言波动。
        """
        if not response:
            return response

        conservative_markers = ["不方便", "先不说", "不太想说", "这个也要", "不想聊", "算了"]
        if not any(marker in (user_message or "") for marker in conservative_markers):
            return response

        empathy_keywords = ["没关系", "理解", "方便"]
        if any(kw in response for kw in empathy_keywords):
            return response

        if "没事" in response:
            return response.replace("没事", "没关系", 1)
        return f"理解你的感受，{response}"

    def _apply_field_ask_guard(self, user_profile: UserProfile, response: str) -> str:
        """
        策略层硬约束：冷却字段和已问满字段不允许继续追问。
        """
        if not response:
            return response

        try:
            cooldown_turns = int(os.getenv("MQ_FIELD_ASK_COOLDOWN_TURNS", "2"))
        except (TypeError, ValueError):
            cooldown_turns = 2

        cooldown_fields = set(user_profile.get_cooldown_fields(cooldown_turns)) if cooldown_turns > 0 else set()
        blocked_fields = set()
        for field in ASK_GUARD_MANAGED_FIELDS | ASK_GUARD_MEDIUM_FIELDS:
            if user_profile.collection_progress.get(field, False):
                continue
            if user_profile.skipped_fields.get(field, False):
                continue
            limit = 2 if field in ASK_GUARD_MANAGED_FIELDS else 1
            if field in cooldown_fields or user_profile.get_ask_count(field) >= limit:
                blocked_fields.add(field)

        if not blocked_fields:
            return response

        field_keywords = get_field_keywords()
        blocked_keywords = {
            keyword
            for field in blocked_fields
            for keyword in field_keywords.get(field, [])
            if keyword
        }
        if not blocked_keywords:
            return response

        segments = [seg.strip() for seg in re.split(r"(?<=[。！？!?])\s*", response) if seg.strip()]
        if not segments:
            return response

        kept_segments = []
        removed_any = False
        for seg in segments:
            has_blocked_keyword = any(keyword in seg for keyword in blocked_keywords)
            looks_like_question = any(cue in seg for cue in ASK_GUARD_QUESTION_CUES)
            if has_blocked_keyword and looks_like_question:
                removed_any = True
                continue
            kept_segments.append(seg)

        if not removed_any:
            return response

        if kept_segments:
            return " ".join(kept_segments).strip()
        return "我们先按你刚说的继续聊，不急着重复问这个。"

    def _ensure_humanlike_memory_ack(self, user_message: str, user_profile: UserProfile, response: str) -> str:
        """
        轻量拟人化承接保护：
        当回复过早跳到“留电话”时，补一句与用户当轮/历史信息相关的承接。
        不改变业务流程，只增强表达层。
        """
        if not response:
            return response

        message = (user_message or "").strip()
        lower_message = message.lower()

        # 1) 调侃/玩笑型：先接住情绪，再回主线
        joke_markers = ["查户口", "问这么细", "盘问", "审我"]
        if any(marker in message for marker in joke_markers):
            if not any(kw in response for kw in ["了解", "认识", "匹配", "适合"]):
                return f"哈哈不是查户口啦，主要是想先多了解你，才能更匹配合适的人选～{response}"

        # 2) 位置记忆回用：用户问“那边资源”
        if any(marker in message for marker in ["那边", "深圳", "资源", "相亲资源"]):
            loc = (user_profile.location or "").strip()
            if loc and not any(kw in response for kw in [loc, "那边"]):
                return f"{loc}那边的资源我们这边一直在做筛选更新，我会优先按同城给你匹配～{response}"

        # 3) 职业/忙碌承接
        if any(marker in lower_message for marker in ["工作比较忙", "工作忙", "比较忙", "加班"]):
            occ = (user_profile.occupation or "").strip()
            if not any(kw in response for kw in ["运营", "工作", "忙"]):
                if occ:
                    return f"懂你，做{occ}很多时候节奏会比较快、也挺忙的～{response}"
                return f"懂你，工作忙确实会压缩认识新人的时间～{response}"

        # 4) 择偶偏好承接
        if any(marker in message for marker in ["推荐", "有什么推荐", "合适", "成熟", "稳重"]):
            pref = (user_profile.partner_requirement or "").strip()
            if pref and not any(kw in response for kw in ["成熟", "稳重", "合拍", "推荐"]):
                if "成熟" in pref or "稳重" in pref:
                    return f"你提到想找成熟稳重的类型，我会按这个方向给你推荐更合拍的人选～{response}"
                return f"我会结合你刚提到的偏好来推荐更合拍的人选～{response}"

        return response

    def _extract_contact_candidate_from_message(self, user_message: str) -> Optional[Dict[str, str]]:
        """从用户原始消息中提取疑似联系方式，并携带字段提示。"""
        if not user_message:
            return None

        import re

        marker_pattern = re.compile(
            r'(?P<marker>电话|手机|手机号|号码|微信|vx|wx|weixin)[^\da-zA-Z_/-]*(?P<value>[a-zA-Z][a-zA-Z0-9_-]{2,19}|\+?86[\d\s-]{11,17}|[\d\s-]{8,17})',
            re.IGNORECASE,
        )
        matched = marker_pattern.search(user_message)
        if matched:
            marker = matched.group("marker").lower()
            hinted_type = "wechat" if marker in {"微信", "vx", "wx", "weixin"} else "phone"
            raw_value = matched.group("value").strip()
            contaminated = False
            if hinted_type == "phone":
                raw_value = re.sub(r'[\s-]', '', raw_value)
            else:
                value_end = matched.end("value")
                if value_end < len(user_message):
                    trailing_char = user_message[value_end]
                    # 防止将 “wx12345让3” 这类混杂串误收集成合法微信
                    if re.match(r"[A-Za-z0-9_\-\u4e00-\u9fff]", trailing_char):
                        contaminated = True
            return {"value": raw_value, "type": hinted_type, "contaminated": contaminated}

        return None

    def _extract_contacts_from_message(self, user_message: str) -> Dict[str, str]:
        """从原始消息中分别提取电话和微信，兜底无 AI 提取场景。"""
        if not user_message:
            return {}

        contacts: Dict[str, str] = {}

        phone_match = re.search(r'(?:电话|手机|手机号|号码)[^\d]*(\+?86[\s-]*)?((?:1[\s-]*){1}(?:\d[\s-]*){10}|(?:[5-9][\s-]*){1}(?:\d[\s-]*){7})\b', user_message, re.IGNORECASE)
        if phone_match:
            phone_value = ''.join(c for c in phone_match.group(0) if c.isdigit())
            if phone_value.startswith('86') and len(phone_value) == 13 and phone_value[2] == '1':
                phone_value = phone_value[2:]
            if re.match(r'^1[3-9]\d{9}$', phone_value) or re.match(r'^[5-9]\d{7}$', phone_value):
                contacts["phone"] = phone_value

        wechat_match = re.search(
            r'(?:微信|vx|wx|weixin)[^a-zA-Z0-9_-]*(?:就是手机号)?([a-zA-Z][a-zA-Z0-9_-]{5,19}|1[3-9]\d{9}|[5-9]\d{7})\b',
            user_message,
            re.IGNORECASE,
        )
        if wechat_match:
            wechat_value = wechat_match.group(1)
            value_end = wechat_match.end(1)
            trailing_contaminated = False
            if value_end < len(user_message):
                trailing_char = user_message[value_end]
                trailing_contaminated = bool(re.match(r"[A-Za-z0-9_\-\u4e00-\u9fff]", trailing_char))
            if not trailing_contaminated:
                contacts["wechat"] = wechat_value

        return contacts

    def _infer_contact_attempt_from_context(self, user_message: str, next_action: str) -> tuple[Optional[str], Optional[str]]:
        """根据当前联系方式流程动作，推断用户是否在尝试提供联系方式（即便格式错误）。"""
        message = (user_message or "").strip()
        if not message:
            return None, None

        # 电话流程：只要出现较长数字串，就认为是电话尝试
        if next_action in {"ask_phone", "persuade_phone"}:
            digits = re.sub(r"\D", "", message)
            if digits.startswith("86") and len(digits) >= 12:
                digits = digits[2:]
            if len(digits) >= 7:
                return digits, "phone"
            return None, None

        # 微信流程：包含字母/数字组合或微信标识，视作微信尝试
        if next_action in {"ask_wechat", "persuade_wechat"}:
            lowered = message.lower()
            cleaned = re.sub(r"^(微信|微信号|weixin)[:：\s]*", "", lowered, flags=re.IGNORECASE).strip()
            if re.search(r"[a-z]", cleaned) and re.search(r"\d", cleaned):
                return cleaned, "wechat"
            explicit_id_match = re.search(r"\b(?:wx|vx|weixin)[:：\s]*([a-z][a-z0-9_-]{5,19})\b", lowered)
            if explicit_id_match:
                return explicit_id_match.group(1), "wechat"
            # 仅出现“微信”意向词（例如“用微信联系吧”）不应当作“已提供微信号”。
            if re.match(r"^[a-z][a-z0-9_-]{5,19}$", cleaned):
                return cleaned, "wechat"

        return None, None

    def _looks_like_fake_info(self, user_message: str) -> bool:
        """基于原始文本识别明显虚假年龄/身高。"""
        if not user_message:
            return False

        age_match = re.search(r'(\d{1,4})\s*岁', user_message)
        if age_match:
            age_value = int(age_match.group(1))
            if age_value >= 123 or age_value <= 10:
                return True

        height_meter_match = re.search(
            r'身高\s*(?:是|有|大概|差不多|约|在)?\s*(\d+(?:\.\d+)?)\s*米',
            user_message,
        )
        if height_meter_match:
            try:
                if float(height_meter_match.group(1)) >= 3.0:
                    return True
            except ValueError:
                pass

        height_cm_match = re.search(
            r'身高\s*(?:是|有|大概|差不多|约|在)?\s*(\d{2,3})(?:\s*(?:cm|CM|厘米))?(?!\s*岁)',
            user_message,
        )
        if height_cm_match:
            height_value = int(height_cm_match.group(1))
            if height_value >= 300 or height_value <= 50:
                return True

        return False

    def _extract_basic_fields_from_message(self, user_message: str) -> Dict[str, Any]:
        """AI 不可用时，用轻量规则兜底提取常见基础字段。"""
        if not user_message:
            return {}

        extracted: Dict[str, Any] = {}

        if '我是女生' in user_message or '本人女' in user_message:
            extracted['sex'] = '女'
        elif '我是男生' in user_message or '本人男' in user_message:
            extracted['sex'] = '男'

        age_match = re.search(r'(\d{2})后', user_message)
        if age_match:
            suffix = int(age_match.group(1))
            birth_year = 2000 + suffix if suffix <= datetime.now().year % 100 else 1900 + suffix
            extracted['age'] = datetime.now().year - birth_year
            extracted['age_label'] = f"{age_match.group(1)}后"
        else:
            explicit_age = re.search(r'(\d{2})岁', user_message)
            if explicit_age:
                extracted['age'] = int(explicit_age.group(1))

        location_match = re.search(r'在([\u4e00-\u9fa5]{2,10})', user_message)
        if location_match:
            extracted['location'] = location_match.group(1)
        else:
            # 支持“我是女生，90后，深圳，本科”这类紧凑输入中的城市片段。
            city_candidates = {"深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港"}
            preference_context = bool(re.search(r"(喜欢|想找|找).*(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", user_message))
            if not preference_context:
                for token in re.split(r'[，,、\s]+', user_message):
                    t = token.strip()
                    if t in city_candidates:
                        extracted["location"] = t
                        break

        for edu in ['博士', '硕士', '研究生', '本科', '大专', '中专', '高中']:
            if edu in user_message:
                extracted['education'] = edu
                break

        for marital in ['单身', '离异', '未婚', '已婚']:
            if marital in user_message:
                extracted['marital_status'] = marital
                break

        segments = re.split(r'[，,、\s]+', user_message)
        education_tokens = {'博士', '硕士', '研究生', '本科', '大专', '中专', '高中'}
        marital_tokens = {'单身', '离异', '未婚', '已婚'}
        ignored_tokens = {'我是女生', '我是男生', '女生', '男生'}
        for index, segment in enumerate(segments):
            token = segment.strip()
            if not token:
                continue
            if token in education_tokens and index + 1 < len(segments):
                candidate = segments[index + 1].strip()
                if candidate and candidate not in marital_tokens and candidate not in ignored_tokens and not candidate.startswith('想找'):
                    extracted['occupation'] = candidate
                    break

        return extracted

    def _extract_deterministic_profile_fields(self, user_message: str) -> Dict[str, Any]:
        """
        为“短答资料补充”准备的保守规则提取。
        仅覆盖确定性很强的字段，避免误伤复杂/拟人化轮次。
        """
        message = (user_message or "").strip()
        if not message:
            return {}

        extracted = self._extract_basic_fields_from_message(message)

        sex_patterns = {
            "男": r"^\s*(男生|男的|男)\s*(呀|呢|哈|哦|啊)?\s*$",
            "女": r"^\s*(女生|女的|女)\s*(呀|呢|哈|哦|啊)?\s*$",
        }
        for value, pattern in sex_patterns.items():
            if re.search(pattern, message):
                extracted["sex"] = value
                break

        if re.search(r"^\s*90后\s*$", message):
            current_year = datetime.now().year
            extracted["age"] = current_year - 1990
            extracted["age_label"] = "90后"
        elif re.search(r"^\s*95后\s*$", message):
            current_year = datetime.now().year
            extracted["age"] = current_year - 1995
            extracted["age_label"] = "95后"
        elif re.search(r"^\s*85后\s*$", message):
            current_year = datetime.now().year
            extracted["age"] = current_year - 1985
            extracted["age_label"] = "85后"

        location_candidates = {"深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港"}
        if message in location_candidates:
            extracted["location"] = message

        for edu in ["博士", "硕士", "研究生", "本科", "大专", "中专", "高中"]:
            if message == edu:
                extracted["education"] = edu
                break

        for marital in ["单身", "未婚", "离异", "已婚"]:
            if message == marital:
                extracted["marital_status"] = marital
                break

        occupation_match = re.search(r"^\s*(?:做|做?的是|我是)\s*([\u4e00-\u9fa5]{2,8})\s*(?:的|呢|呀)?\s*$", message)
        if occupation_match:
            candidate = occupation_match.group(1).strip()
            if candidate not in {"男", "女", "单身", "未婚", "离异", "已婚"}:
                extracted["occupation"] = candidate

        if not extracted.get("partner_requirement"):
            pref = self._extract_simple_partner_requirement(message)
            if pref:
                extracted["partner_requirement"] = pref

        return extracted

    @staticmethod
    def _extract_simple_partner_requirement(user_message: str) -> Optional[str]:
        """轻量提取明确的择偶偏好短答。"""
        message = (user_message or "").strip()
        if not message:
            return None

        patterns = [
            r"(高挑)",
            r"(高一点)",
            r"(同城优先)",
            r"(不要超过\d{2}岁)",
            r"(不超过\d{2}岁)",
            r"(成熟稳重)",
            r"(三观合拍)",
            r"(喜欢[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(想找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
        ]
        values = []
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                values.append(match.group(1).strip())
        if values:
            return "，".join(dict.fromkeys(values))
        return None

    def _should_use_rule_profile_fast_path(
        self,
        user_message: str,
        extracted_data: Dict[str, Any],
        response_channel: str,
    ) -> bool:
        """
        仅让低歧义、低风险、短答资料轮次走非 AI 快路径。
        """
        message = (user_message or "").strip()
        if not message or not extracted_data:
            return False
        if response_channel != "model":
            return False
        if len(message) > 20:
            return False
        if any(token in message for token in ["电话", "微信", "联系方式", "不方便", "不留", "为什么", "靠谱吗", "安全", "隐私"]):
            return False
        if any(ch in message for ch in ["?", "？"]):
            return False

        allowed_fields = {"sex", "age", "age_label", "location", "education", "occupation", "marital_status", "partner_requirement"}
        fields = set(extracted_data.keys())
        if not fields:
            return False
        if not fields.issubset(allowed_fields):
            return False

        substantive_fields = fields - {"age_label"}
        return len(substantive_fields) <= 2

    def _build_rule_profile_fast_response(self, user_profile: UserProfile, user_message: str = "") -> str:
        """
        规则短答入档后的自然追问模板。
        只覆盖资料收集主线，不处理复杂答疑/说服场景。
        """
        policy = self.collection_policy.decide(user_profile, user_message=user_message)
        next_field = policy.main_target
        if not next_field:
            return ""

        if next_field == "sex":
            return "我先记下来啦～顺带问下你是男生还是女生呀？"
        if next_field == "age":
            return "好哒～那想问下你今年多大呀？"
        if next_field == "location":
            return "收到啦～那你现在主要在哪个城市工作生活呀？"
        if next_field == "education":
            return "知道啦～那你这边是什么学历呀？"
        if next_field == "occupation":
            return "了解啦～那你现在是做什么工作的呀？"
        if next_field == "marital_status":
            return "我记下来啦～那你现在是单身状态，还是离异呢？"
        if next_field == "contact":
            return "资料我这边先了解得差不多啦～方便留个电话吗？后续有合适的人选时联系你～"

        if next_field == "partner_requirement":
            return "顺带聊聊你的偏好吧，你更看重对方哪几点呀？"
        if next_field == "monthly_income":
            return "另外我轻问一句，你月收入大概在哪个区间呀？不方便说也没关系。"
        return ""

    def _canonicalize_extracted_fields(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """将提取字段映射为统一字段名，清理空值。"""
        canonical: Dict[str, Any] = {}
        if not extracted_data:
            return canonical

        for raw_field, raw_value in extracted_data.items():
            if raw_value in (None, "", "null"):
                continue
            field_key = str(raw_field).strip()
            mapped = self.extraction_service.FIELD_MAPPING.get(field_key, field_key)
            if mapped.startswith("__"):
                continue
            canonical[mapped] = raw_value
        return canonical

    def _fuse_extracted_fields(
        self,
        ai_extracted: Dict[str, Any],
        rule_extracted: Dict[str, Any],
        user_message: str,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        多源提取融合（AI + 规则）并产出证据元信息。

        规则：
        1. 双源一致 -> 高置信
        2. 关键字段冲突 -> 优先规则值
        3. 非关键字段冲突 -> 优先 AI 值
        """
        ai_fields = self._canonicalize_extracted_fields(ai_extracted)
        rule_fields = self._canonicalize_extracted_fields(rule_extracted)
        fused: Dict[str, Any] = {}
        meta: Dict[str, Dict[str, Any]] = {}

        for field in set(ai_fields) | set(rule_fields):
            ai_value = ai_fields.get(field)
            rule_value = rule_fields.get(field)

            if ai_value is not None and rule_value is not None:
                if str(ai_value).strip() == str(rule_value).strip():
                    fused[field] = rule_value
                    meta[field] = {
                        "source": "ai+rule",
                        "confidence": 0.96,
                        "source_text": user_message,
                    }
                elif field in EXTRACTION_CRITICAL_FIELDS:
                    fused[field] = rule_value
                    meta[field] = {
                        "source": "rule_override",
                        "confidence": 0.9,
                        "source_text": user_message,
                    }
                else:
                    fused[field] = ai_value
                    meta[field] = {
                        "source": "ai_preferred",
                        "confidence": 0.74,
                        "source_text": str(ai_value),
                    }
                continue

            if rule_value is not None:
                fused[field] = rule_value
                meta[field] = {
                    "source": "rule",
                    "confidence": 0.88 if field in EXTRACTION_CRITICAL_FIELDS else 0.8,
                    "source_text": user_message,
                }
                continue

            if ai_value is not None:
                fused[field] = ai_value
                meta[field] = {
                    "source": "ai",
                    "confidence": 0.72,
                    "source_text": str(ai_value),
                }

        return fused, meta

    async def _build_no_ai_response(self, account_id: str, user_profile: UserProfile, user_message: str) -> str:
        """AI 不可用时的最小可用回复，优先兜住联系方式主线。"""
        message = (user_message or "").strip()
        last_response = await self.dialogue_manager.get_last_response(account_id) or ""

        if self.expectation_service.is_matching_timeline_question(message):
            return self.expectation_service.get_matching_timeline_response(user_profile)

        if any(keyword in message for keyword in ['为什么一定要电话', '为什么要电话', '为什么留电话', '电话干嘛', '电话做什么', '为什么要留手机号']):
            return "电话这边主要是留作登记和后面联系用的，不会私下打扰你，这点你可以放心～"

        if any(keyword in message for keyword in ['留微信可以吗', '微信可以吗', '电话不方便，留微信可以吗', '用微信联系吧', '微信吧', '加微信吧']):
            return "可以呀，那你直接发我微信号就行，我这边先记下来～"

        if any(keyword in message for keyword in ['联系方式都不留', '都不留', '不留任何联系方式']):
            if not user_profile.rejected_phone:
                return "如果电话不方便的话，微信也可以呀，留一个方便后面联系就行～"
            return "那微信或者电话留一个都可以，主要是方便后面联系你～"

        if message in {'好', '嗯', '嗯嗯', '好的', 'ok', '可以'}:
            # 仅在明确联系方式语境中，确认词才进入联系方式兜底。
            contact_context_markers = ["电话", "手机号", "号码", "微信", "联系方式", "留个", "联系你"]
            has_contact_stage_signal = any(
                [
                    bool(user_profile.phone_ask_count > 0),
                    bool(user_profile.wechat_ask_count > 0),
                    bool(user_profile.phone_collected),
                    bool(user_profile.wechat_collected),
                    bool(user_profile.rejected_phone),
                    bool(user_profile.rejected_wechat),
                ]
            )
            last_response_about_contact = any(marker in last_response for marker in contact_context_markers)
            if has_contact_stage_signal or last_response_about_contact:
                confirm_count = await self.input_fallback_service.increment_confirm_count(account_id)
                return self.input_fallback_service.get_confirm_word_response(user_profile, confirm_count) or ""

        next_action = self.contact_service.get_next_action(user_profile, message)
        if next_action.value == "ask_phone":
            if any(marker in last_response for marker in ["留个电话", "电话号码", "手机号", "号码"]):
                return "我先不重复追问电话啦，你也可以先说说你更在意的匹配条件。"
            return self._ensure_contact_transition_natural(
                last_response,
                "方便留个电话吗？后续有合适的人选时联系你～",
                user_profile,
            )
        if next_action.value == "persuade_phone":
            return self._ensure_contact_transition_natural(
                last_response,
                "这个电话只是留作登记和后面联系用的，不会私下打扰你。你方便的话发我一个号码就行～",
                user_profile,
            )
        if next_action.value == "ask_wechat":
            if any(marker in last_response for marker in ["留个微信", "微信号", "加微信", "发我微信"]):
                return "我先不重复追问微信啦，你要是愿意再告诉我就行。"
            response = self._ensure_contact_transition_natural(
                last_response,
                "可以呀，你方便的话直接发我微信号就行，后面联系会更顺手一点～",
                user_profile,
            )
            await self.dialogue_manager.update_recent_responses(account_id, response)
            return response
        if next_action.value == "persuade_wechat":
            response = self._ensure_contact_transition_natural(
                last_response,
                "如果电话不方便的话，留个微信也可以，后面沟通会方便一点～",
                user_profile,
            )
            await self.dialogue_manager.update_recent_responses(account_id, response)
            return response

        return ""

    async def _update_conversation_state(
        self,
        account_id: str,
        user_message: str,
        clean_response: str,
        raw_response: str,
        track_asked_fields: bool = True,
    ) -> None:
        """更新对话状态"""
        # 添加到历史
        await self.dialogue_manager.add_to_history(account_id, 'user', user_message)
        await self.dialogue_manager.add_to_history(account_id, 'assistant', clean_response)

        # 更新最近回复（使用清理后的回复，而不是原始回复）
        # 注意：_handle_contact_validation 可能已经添加了微信询问回复，这里不要覆盖
        # 检查 recent_responses 最后一条是否已经是当前回复
        last_response = await self.dialogue_manager.get_last_response(account_id)
        if last_response != clean_response:
            await self.dialogue_manager.update_recent_responses(account_id, clean_response)

        # 增加消息计数
        await self.dialogue_manager.increment_message_count(account_id)

        # 智能追问机制：追踪AI询问的字段
        if track_asked_fields:
            await self.ask_tracking_service.track_ai_asked_fields(account_id, clean_response)

    async def _build_chat_response(
        self,
        account_id: str,
        user_profile: UserProfile,
        response: str,
        collection_result: Dict[str, Any],
        dialog_id: Optional[str],
        field_ask_count_before: Dict[str, int] = None,
        response_route: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建聊天响应

        Args:
            field_ask_count_before: AI询问前的字段计数快照，用于正确显示"已跳过"时机
                                   （使用"增加前"的值，这样用户还有机会回答当前问题）
        """
        response = self._sanitize_forbidden_sales_phrases(response)
        if response_route:
            await self._simulate_non_ai_human_delay(response, route=response_route)

        # 检查是否拒绝
        is_refusal = RefusalDetector.is_refusing(response)

        # 获取消息计数
        message_count = await self.dialogue_manager.get_message_count(account_id)

        # 使用"增加前"的快照来判断"已跳过"显示（如果没有快照，使用当前值）
        ask_count_snapshot = field_ask_count_before if field_ask_count_before is not None else {}

        # 辅助函数：获取字段显示值（区分"未留"和"已跳过"）
        def get_field_display(field_name: str, value, default: str = "未留") -> str:
            if value:
                return str(value)
            # 检查是否被跳过（问了2次及以上未回答）
            # 使用"增加前"的快照值，这样用户还有机会回答当前问题
            ask_count = ask_count_snapshot.get(field_name, 0)
            if ask_count >= 2:
                return f"已跳过({ask_count}次未答)"
            return default

        # 构建联系方式显示值（简化版逻辑）
        def get_contact_display() -> str:
            parts = []
            # 微信号部分
            if user_profile.wechat:
                parts.append(f"微信:{user_profile.wechat}")
            elif user_profile.rejected_wechat:
                parts.append("不愿留微信")
            elif user_profile.wechat_ask_count >= 1 and not user_profile.rejected_wechat:
                parts.append("微信争取中")
            # 电话部分
            if user_profile.phone:
                parts.append(f"电话:{user_profile.phone}")
            elif user_profile.rejected_phone:
                parts.append("不愿留电话")
            elif user_profile.phone_ask_count >= 1 and not user_profile.rejected_phone:
                parts.append("电话争取中")
            # 组合结果
            if parts:
                return ", ".join(parts)
            return "未留"

        # 构建已收集信息（12 个字段，联系方式合并显示）
        collected_info = {
            "sex": get_field_display("sex", user_profile.sex),
            "last_name": get_field_display("last_name", user_profile.last_name, "未留称呼"),
            "age": get_field_display(
                "age",
                f"{user_profile.age_label}({user_profile.age}岁)" if user_profile.age_label and user_profile.age else user_profile.age_label or user_profile.age,
            ),
            "height": get_field_display("height", user_profile.height),
            "weight": get_field_display("weight", user_profile.weight),
            "location": get_field_display("location", user_profile.location),
            "education": get_field_display("education", user_profile.education),
            "marital_status": get_field_display("marital_status", user_profile.marital_status),
            "monthly_income": get_field_display("monthly_income", user_profile.monthly_income),
            "occupation": get_field_display("occupation", user_profile.occupation),
            "contact": get_contact_display(),
            "partner_requirement": get_field_display("partner_requirement", user_profile.partner_requirement)
        }

        # 返回响应
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id,
            "collected_info": collected_info,
            "collected": collection_result.get("collected", False) if collection_result else False,
            "field": collection_result.get("field") if collection_result else None,
            "value": collection_result.get("value") if collection_result else None
        }

    def _success_response(self, response: str, dialog_id: Optional[str]) -> Dict[str, Any]:
        """构建成功响应"""
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id
        }

    def _sanitize_forbidden_sales_phrases(self, response: str) -> str:
        """清理会暴露业务流程或违规承诺的固定话术。"""
        text = str(response or "")
        if not text:
            return text

        original = text
        for pattern in self.FORBIDDEN_SALES_PATTERNS:
            text = re.sub(pattern, "后续有合适人选我会第一时间联系你", text)

        # 去除重复替换导致的冗余表达
        text = re.sub(r"(后续有合适人选我会第一时间联系你){2,}", "后续有合适人选我会第一时间联系你", text)
        text = re.sub(r"\s+", " ", text).strip()

        if text != original:
            logger.info("[话术合规] 已替换禁语表达，避免出现见面/发资料承诺")
        return text

    def _apply_extraction_guards(
        self,
        extracted_data: Dict[str, Any],
        user_message: str,
        last_response: str = "",
    ) -> Dict[str, Any]:
        """对高风险提取结果做入库前保护，避免偏好信息污染用户主档。"""
        if not extracted_data:
            return extracted_data

        guarded = dict(extracted_data)
        message = (user_message or "").strip()
        last_ai = str(last_response or "")

        # 仅凭“找男的/找女生”这类择偶偏好，不允许反推用户自身 sex。
        explicit_self_sex = re.search(r"(我是|本人|我)\s*(男生|女生|男的|女的|男|女)", message)
        preference_sex_hint = re.search(r"(找|想找|喜欢|偏好).{0,4}(男生|女生|男的|女的|男|女)", message)
        if "sex" in guarded and not explicit_self_sex and preference_sex_hint:
            guarded.pop("sex", None)
            logger.info("[提取保护] 检测到择偶偏好语境，忽略 sex 提取，避免误写用户性别")

        # 性别问题上下文优先：上一轮明确在问性别时，短答“男的/女的/你们男的”优先按 sex 处理。
        sex_question_context = bool(
            re.search(r"(你是|是)(男生|女生|男的|女的|男|女)", last_ai)
            or "性别" in last_ai
        )
        short_sex_answer = re.search(r"(?:你们)?\s*(男生|女生|男的|女的|男|女)\s*$", message)
        if sex_question_context and short_sex_answer:
            raw = short_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            partner_value = str(guarded.get("partner_requirement") or "")
            if partner_value and any(token in partner_value for token in ["男", "女"]):
                guarded.pop("partner_requirement", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_requirement 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 short answer 强制写入 sex")

        return guarded

    def _error_response(self, error: str, dialog_id: Optional[str]) -> Dict[str, Any]:
        """构建错误响应"""
        # 检测是否是429配额错误，如果是则返回空响应（不显示错误消息）
        if '429' in error or 'SetLimitExceeded' in error or 'TooManyRequests' in error:
            return {
                "success": True,
                "response": "",
                "dialogId": dialog_id,
                "silent": True
            }

        return {
            "success": False,
            "error": error,
            "dialogId": dialog_id
        }

    # ============ 其他辅助方法 ============

    async def generate_welcome_message(self, user_id: str) -> Dict[str, Any]:
        """生成欢迎消息（已禁用）"""
        # 清除对话历史
        await self.dialogue_manager.clear_conversation(user_id)

        # 不再显示欢迎消息，直接开始对话
        return {
            "success": True,
            "message": "",
            "conversation_reset": True
        }

    async def process_user_feedback(
        self,
        user_id: str,
        message: str,
        rating: int,
        feedback_type: str = "response"
    ) -> Dict[str, Any]:
        """处理用户反馈"""
        logger.info(f"[用户反馈] user={user_id}, rating={rating}, type={feedback_type}")

        # TODO: 存储反馈到数据库
        return {
            "success": True,
            "message": "感谢您的反馈！",
            "feedback_recorded": True
        }

    async def get_user_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取对话历史"""
        history_payload = await self.user_service.get_conversation_history(user_id, limit, offset)
        conversations = history_payload.get("conversations", []) if isinstance(history_payload, dict) else []
        total_count = history_payload.get("total_count", len(conversations)) if isinstance(history_payload, dict) else len(conversations)

        return {
            "success": True,
            "history": conversations,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        profile = await self.user_service.get_user_profile(user_id)

        return {
            "success": True,
            "profile": profile.to_dict()
        }

    async def reset_user_conversation(self, user_id: str) -> Dict[str, Any]:
        """重置用户对话（包括清除用户资料）"""
        await self.dialogue_manager.clear_conversation(user_id)

        # 清除用户资料（重置为全新用户状态）
        await self.user_service.delete_user_profile(user_id)

        return {
            "success": True,
            "message": "对话已重置",
            "conversation_reset": True
        }

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        """读取浮点环境变量，异常时返回默认值。"""
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        """读取整型环境变量，异常时返回默认值。"""
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def _get_followup_greeting_ai_prob(self) -> float:
        """获取非首轮寒暄进入 AI 的概率。"""
        prob = self._env_float("MQ_FOLLOWUP_GREETING_AI_PROB", 0.30)
        return max(0.0, min(1.0, prob))

    def _should_route_followup_greeting_to_ai(self) -> bool:
        """决定非首轮寒暄是否进入 AI。"""
        return random.random() < self._get_followup_greeting_ai_prob()

    async def _simulate_human_reply_delay(self, first_turn: bool) -> None:
        """打招呼快捷路径也加入拟人随机延迟，避免机械秒回。"""
        # 测试环境跳过等待，避免回归测试变慢
        if os.getenv("PYTEST_CURRENT_TEST"):
            return

        if first_turn:
            min_s = self._env_float("MQ_GREETING_FIRST_TURN_DELAY_MIN", 0.8)
            max_s = self._env_float("MQ_GREETING_FIRST_TURN_DELAY_MAX", 2.2)
        else:
            min_s = self._env_float("MQ_GREETING_FOLLOWUP_DELAY_MIN", 0.9)
            max_s = self._env_float("MQ_GREETING_FOLLOWUP_DELAY_MAX", 2.6)

        if max_s < min_s:
            min_s, max_s = max_s, min_s

        min_s = max(0.0, min_s)
        max_s = max(min_s, max_s)
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _simulate_non_ai_human_delay(self, response_text: str, route: str = "rule") -> None:
        """给非 AI 直返路径加拟人延时，避免秒回暴露机器人。"""
        enabled = os.getenv("MQ_NON_AI_DELAY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        if not enabled:
            return
        if os.getenv("PYTEST_CURRENT_TEST"):
            return
        if not response_text or not response_text.strip():
            return

        base = self._env_float("MQ_NON_AI_DELAY_BASE", 0.7)
        per_char = self._env_float("MQ_NON_AI_DELAY_PER_CHAR", 0.018)
        jitter_min = self._env_float("MQ_NON_AI_DELAY_JITTER_MIN", 0.2)
        jitter_max = self._env_float("MQ_NON_AI_DELAY_JITTER_MAX", 0.9)
        cap = self._env_float("MQ_NON_AI_DELAY_MAX", 3.8)

        if route == "quick_faq":
            base = self._env_float("MQ_QUICK_FAQ_DELAY_BASE", base)
            per_char = self._env_float("MQ_QUICK_FAQ_DELAY_PER_CHAR", per_char)
            jitter_min = self._env_float("MQ_QUICK_FAQ_DELAY_JITTER_MIN", jitter_min)
            jitter_max = self._env_float("MQ_QUICK_FAQ_DELAY_JITTER_MAX", jitter_max)
            cap = self._env_float("MQ_QUICK_FAQ_DELAY_MAX", cap)

        if jitter_max < jitter_min:
            jitter_min, jitter_max = jitter_max, jitter_min

        delay = base + max(0, len(response_text)) * per_char + random.uniform(jitter_min, jitter_max)
        delay = max(0.0, min(delay, max(0.0, cap)))
        logger.info(f"[拟人延时] route={route}, delay={delay:.3f}s")
        await asyncio.sleep(delay)

    # ============ 打招呼检测 ============

    # ============ 无意义输入检测 ============

    def _is_nonsense_input(self, text: str) -> bool:
        """
        检测是否是无意义输入（乱码、表情符号堆砌、键盘乱敲等）

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否是无意义输入
        """
        import re
        import logging
        from src.services.data.redis_service import redis_service

        logger = logging.getLogger(__name__)
        text_stripped = text.strip()

        # 跳过纯中文输入（认为是有意义的）
        # 简化检查：如果主要是中文，认为是有意义的
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            logger.info(f"[无意义检测] 通过中文检查: {text_stripped}")
            return False

        # 1. 长度过短（1-2个字符且不是有意义的内容）
        if len(text_stripped) <= 2:
            # 如果是常见姓氏，认为是有意义的
            if text_stripped in self.COMMON_SURNAMES:
                logger.info(f"[无意义检测] 判定为有意义（常见姓氏）: {text_stripped}")
                return False

            # 检查是否是中文或英文单词
            pattern = r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}'
            match = re.search(pattern, text_stripped)
            logger.info(f"[无意义检测] 短输入 '{text_stripped}' (len={len(text_stripped)}) 正则匹配: {match}")
            if not match:
                # 额外检查：数字+单位格式（如"5万"、"3k"、"20k"）是有意义的
                income_pattern = r'^\d+[万千百kKwW]?$|^\d+[万千百kKwW]$'
                if re.match(income_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（收入格式）: {text_stripped}")
                    return False
                logger.info(f"[无意义检测] 判定为无意义: {text_stripped}")
                return True
            else:
                logger.info(f"[无意义检测] 判定为有意义: {text_stripped}，返回 False")
                return False  # 明确返回 False！

        # 2. 大量表情符号/特殊字符（超过内容的30%）
        # 注意：使用范围时必须精确，避免包含中文字符
        emoji_pattern = re.compile(
            '[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            '\U00002702-\U000027B0\U000024C2-\U000027BF'
            '\u2600-\u26FF]'
        )
        emoji_count = len(emoji_pattern.findall(text_stripped))
        if emoji_count > 0 and len(text_stripped) > 0:
            emoji_ratio = emoji_count / len(text_stripped)
            if emoji_ratio > 0.3:
                logger.info(f"[无意义检测] 表情符号过多: {text_stripped}")
                return True

        # 3. 纯数字或数字+符号（且不是手机号、年龄等有意义的数字）
        if re.match(r'^[\d\s\+\-\(\)\*#]{3,}$', text_stripped):
            # 排除手机号格式（中国大陆11位或香港8位）
            clean_num = re.sub(r'\s+', '', text_stripped)
            if re.match(r'^1[3-9]\d{9}$', clean_num) or re.match(r'^[5-9]\d{7}$', clean_num):
                logger.info(f"[无意义检测] 手机号格式，判定有意义: {text_stripped}")
                return False

            # 排除常见的有意义数字格式
            pure_num = re.sub(r'\s+', '', text_stripped)
            try:
                num = int(pure_num)
                # 身高范围：100-250（cm）
                if 100 <= num <= 250:
                    logger.info(f"[无意义检测] 可能是身高，判定有意义: {text_stripped}")
                    return False
                # 体重范围：30-300（斤/kg）
                if 30 <= num <= 300:
                    logger.info(f"[无意义检测] 可能是体重，判定有意义: {text_stripped}")
                    return False
                # 年龄范围：18-80
                if 18 <= num <= 80:
                    logger.info(f"[无意义检测] 可能是年龄，判定有意义: {text_stripped}")
                    return False
                # 收入：常见范围
                if num >= 1000:
                    logger.info(f"[无意义检测] 可能是收入等大数字，判定有意义: {text_stripped}")
                    return False
            except ValueError:
                pass

            # 其他纯数字才判定为无意义
            logger.info(f"[无意义检测] 纯数字但无法识别含义: {text_stripped}")
            return True

        # 4. 键盘乱敲检测 - 只检测字母键盘乱敲
        # 检测模式：连续键盘上相邻的字母（如 "rtyui", "asdfg", "qwerty"）
        # 不检测数字序列，因为手机号等正常数字可能包含连续数字
        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'qwer', 'asdf', 'zxcv', 'tyui', 'ghjk', 'bnm',
            'rtyu', 'fghj', 'cvbn', 'yuiop', 'hjkl'
        ]
        text_lower = text_stripped.lower()
        for seq in keyboard_sequences:
            if seq in text_lower or seq[::-1] in text_lower:
                logger.info(f"[无意义检测] 键盘乱敲: {text_stripped}")
                return True

        # 5. 字母数字混合乱码 - 新的检测方法！
        # 检测：数字和字母混合但没有形成有意义的内容
        if len(text_stripped) >= 6:
            # 检查是否是字母数字混合
            has_letter = bool(re.search(r'[a-zA-Z]', text_stripped))
            has_digit = bool(re.search(r'\d', text_stripped))
            logger.info(f"[无意义检测] 字母数字检查: has_letter={has_letter}, has_digit={has_digit}")

            if has_letter and has_digit:
                # 排除微信号格式：以字母开头，6-20字符，可含字母数字下划线减号
                wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'
                if re.match(wechat_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（微信号格式）: {text_stripped}")
                    return False
                # 新增：从输入中提取可能的微信号（不要求整个输入匹配）
                potential_wechat = re.search(r'[a-zA-Z][a-zA-Z0-9_-]{5,19}', text_stripped)
                if potential_wechat:
                    logger.info(f"[无意义检测] 包含可能的微信号格式: {potential_wechat.group()}")
                    return False
                # 方法1：检测是否有重复的短模式（2-4字符）
                # 排除常见的数字组合（如年龄、体重等）
                # 只有当重复模式占比很高时才认为是乱码
                for pattern_len in range(2, 5):
                    if len(text_stripped) >= pattern_len * 3:  # 提高阈值：至少出现3次
                        patterns = []
                        for i in range(len(text_stripped) - pattern_len + 1):
                            pattern = text_stripped[i:i + pattern_len].lower()
                            patterns.append(pattern)

                        # 检查是否有重复的模式
                        from collections import Counter
                        pattern_counts = Counter(patterns)
                        for pattern, count in pattern_counts.items():
                            # 重复至少3次且是字母数字混合才认为是乱码
                            if count >= 3 and pattern.isalnum() and any(c.isalpha() for c in pattern) and any(c.isdigit() for c in pattern):
                                logger.info(f"[无意义检测] 重复模式(字母数字混合): {pattern} count={count}")
                                return True

                # 方法2：检测字符分布是否均匀（乱码特征）
                # 但先排除常见的有意义格式（包含单位的数字）
                meaningful_patterns = [
                    r'\d+kg',      # 体重：90kg
                    r'\d+cm',      # 身高：180cm
                    r'\d+岁',      # 年龄：28岁
                    r'\d+年',      # 年份：90年
                    r'wx[a-zA-Z0-9]+',  # 微信号
                    r'\d+\.?\d*[wW万千百]',  # 收入格式（支持小数）：1.4w、1.4万、3w、3万
                ]
                for pattern in meaningful_patterns:
                    if re.search(pattern, text_stripped.lower()):
                        logger.info(f"[无意义检测] 包含有意义格式({pattern})，跳过乱码检测: {text_stripped}")
                        return False

                # 如果相邻字符总是频繁切换字母/数字类型
                type_switches = 0
                prev_was_digit = text_stripped[0].isdigit()
                for char in text_stripped[1:]:
                    current_is_digit = char.isdigit()
                    if current_is_digit != prev_was_digit and char.isalnum():
                        type_switches += 1
                    prev_was_digit = current_is_digit

                # 如果类型切换次数超过长度的一半，说明是乱码
                if type_switches > len(text_stripped) * 0.4:
                    logger.info(f"[无意义检测] 类型切换过多: type_switches={type_switches}, len={len(text_stripped)}")
                    return True

        # 6. 字符熵检测 - 唯一字符太少说明大量重复
        # 但排除手机号（手机号可能有重复数字）
        if len(text_stripped) >= 8:
            # 先检查是否是手机号格式（中国大陆11位或香港8位）
            if re.match(r'^1[3-9]\d{9}$', text_stripped) or re.match(r'^[5-9]\d{7}$', text_stripped):
                return False  # 手机号是有意义的
            unique_chars = set(text_stripped.lower())
            unique_ratio = len(unique_chars) / len(text_stripped)
            # 如果独特字符少于50%，说明大量重复
            if unique_ratio < 0.5:
                return True

        # 7. 重复字符过多（如 "啊啊啊啊啊啊" 或 "哈哈哈..."）
        if len(text_stripped) > 5:
            # 检查是否有单个字符重复超过4次
            if re.search(r'(.)\1{4,}', text_stripped):
                return True

        # 8. 纯字母乱码检测
        # 检测：纯字母但没有形成有意义的英文单词
        if re.match(r'^[a-zA-Z]{4,}$', text_stripped):
            # 检查是否包含元音字母（英文单词通常有元音）
            has_vowel = bool(re.search(r'[aeiou]', text_stripped.lower()))
            if not has_vowel:
                # 没有元音，很可能是乱码
                return True
            # 检查辅音连续过多（超过4个连续辅音很可能是乱码）
            if re.search(r'[^aeiou\s]{5,}', text_stripped.lower()):
                return True

        # 9. 乱码模式检测：大量随机字符+符号混合
        # 检测连续的特殊字符/数字/符号堆砌
        special_char_pattern = re.compile(r'[^\w\s\u4e00-\u9fa5]{8,}')
        if special_char_pattern.search(text_stripped):
            return True

        return False

    async def _mark_remaining_fields_as_skipped(self, account_id: str, user_profile: UserProfile) -> None:
        """
        收尾时，标记所有未收集字段为"跳过"

        这样用户下次进入时，不会重复询问这些字段
        """
        all_fields = [
            'sex', 'age', 'location', 'education', 'occupation',
            'marital_status', 'contact', 'monthly_income',
            'partner_requirement', 'last_name', 'height', 'weight'
        ]

        skipped_count = 0
        for field in all_fields:
            if not user_profile.collection_progress.get(field, False):
                user_profile.skipped_fields[field] = True
                skipped_count += 1

        if skipped_count > 0:
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[收尾] 已标记 {skipped_count} 个未收集字段为跳过")

    def _is_hong_user(self, location: Optional[str]) -> bool:
        """判断用户是否是香港用户"""
        if not location:
            return False
        location_lower = location.lower()
        return '香港' in location_lower or 'hk' in location_lower
