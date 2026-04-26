"""
重构后的聊天服务 - 处理对话并隐晦地收集用户信息

这是一个重构版本，将原来 1113 行的单一服务拆分为多个专职服务：
- ExtractionService: 信息提取
- ValidationService: 数据验证
- DialogueManager: 对话状态管理
- ChatService: 主流程编排
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, Any, Optional, List

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.data.user_service import UserService
from src.modules.profile_collection.application.profile_collection_coordinator import (
    ProfileCollectionCoordinator,
)
from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase
from src.services.core.chat_service_models import (
    AlreadyEndedPreparation,
    CollectionPhaseOutcome,
    GenerationCollectionPhaseOutcome,
    OpeningIntentSignal,
    TurnExecutionPreparation,
)
from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService
from src.services.core.chat_service_ack_render_service import ChatServiceAckRenderService
from src.services.core.chat_service_bridge_text_service import ChatServiceBridgeTextService
from src.services.core.chat_service_contact_validation_text_service import (
    ChatServiceContactValidationTextService,
)
from src.services.core.chat_service_ending_state_service import ChatServiceEndingStateService
from src.services.core.chat_service_response_cleanup_service import ChatServiceResponseCleanupService
from src.services.core.chat_service_contact_context_service import ChatServiceContactContextService
from src.services.core.chat_service_contact_resume_service import ChatServiceContactResumeService
from src.services.core.chat_service_contact_validation_flow_service import (
    ChatServiceContactValidationFlowService,
)
from src.services.core.chat_service_collection_postprocess_service import (
    ChatServiceCollectionPostprocessService,
)
from src.services.core.chat_service_validation_recovery_service import (
    ChatServiceValidationRecoveryService,
)
from src.services.core.chat_service_confirmation_fallback_service import (
    ChatServiceConfirmationFallbackService,
)
from src.services.core.chat_service_collection_extraction_service import (
    ChatServiceCollectionExtractionService,
)
from src.services.core.chat_service_ending_generation_service import (
    ChatServiceEndingGenerationService,
)
from src.services.core.chat_service_generation_prompt_service import (
    ChatServiceGenerationPromptService,
)
from src.services.core.chat_service_preset_response_service import (
    ChatServicePresetResponseService,
)
from src.services.core.chat_service_text_cleanup_service import (
    ChatServiceTextCleanupService,
)
from src.services.core.chat_service_followup_prompt_service import (
    ChatServiceFollowupPromptService,
)
from src.services.core.chat_service_turn_text_policy_service import (
    ChatServiceTurnTextPolicyService,
)
from src.services.core.chat_service_summary_helper_service import ChatServiceSummaryHelperService
from src.services.core.chat_service_generation_service import ChatServiceGenerationService
from src.services.core.chat_service_delivery_service import ChatServiceDeliveryService
from src.services.core.chat_service_finalize_service import ChatServiceFinalizeService
from src.services.core.chat_service_message_signal_service import ChatServiceMessageSignalService
from src.services.core.chat_service_preparation_service import ChatServicePreparationService
from src.services.core.chat_service_resume_guard_service import ChatServiceResumeGuardService
from src.services.core.chat_service_text_policy_service import ChatServiceTextPolicyService
from src.services.core.first_generation_delivery_service import FirstGenerationDeliveryService
from src.services.collection.contact_collection_service import ContactCollectionService
from src.services.refusal_service import RefusalService
from src.services.core.dialogue_manager import DialogueManager
from src.modules.conversation.domain.conversation_ending_service import ConversationEndingService
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.conversation.domain.greeting_service import GreetingService
from src.modules.conversation.domain.input_fallback_service import InputFallbackService
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService
from src.modules.conversation.domain.user_question_service import UserQuestionService
from src.modules.conversation.domain.conversation_rule_service import ConversationRuleService
from src.modules.conversation.domain.turn_intent_classifier import TurnIntentClassifier
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import (
    TurnUnderstandingInput,
    TurnUnderstandingResult,
)
from src.modules.conversation.domain.turn_understanding_service import TurnUnderstandingService
from src.modules.conversation_understanding.domain.unified_turn_understanding_service import UnifiedTurnUnderstandingService
from src.modules.conversation_understanding.domain.confirmation_ai_fallback_classifier import (
    ConfirmationAIFallbackClassifier,
)
from src.modules.conversation_response.domain.response_plan_builder import ResponsePlanBuilder
from src.modules.conversation_response.domain.response_plan_prompt_formatter import ResponsePlanPromptFormatter
from src.modules.conversation_response.domain.profile_bridge_prompt_formatter import ProfileBridgePromptFormatter
from src.modules.conversation_response.domain.opening_intent_prompt_formatter import OpeningIntentPromptFormatter
from src.modules.conversation_response.domain.prompt_assembly_service import PromptAssemblyService
from src.modules.conversation_response.domain.ai_response_generator import AIResponseGenerator
from src.modules.ai_response_unified_generation.domain import (
    ResponseDeliveryService,
    ResponseDraftService,
    ResponseObservabilityService,
    ResponseSafeCleanupService,
    ResponseValidationService,
)
from src.modules.profile_collection.domain.ask_tracking_service import AskTrackingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.profile_collection.domain.validation_service import ValidationService
from src.modules.profile_collection.domain.field_skip_service import FieldSkipService
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.utils.validators import RefusalDetector
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
    r"诊断",
    r"怎么用药",
    r"开什么药",
    r"药怎么吃",
    r"是不是.*病",
    r"要不要看医生",
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
SERVICE_CONFIRMATION_OPENING_ACK_VARIANTS = (
    "可以呀，你可以先简单介绍下自己，我顺着了解会更自然一点。",
    "可以的，你先说说自己的情况，我这边顺着了解就行。",
    "是的，我们这边就是帮忙牵线介绍的。你先简单讲讲自己，我顺着往下了解。",
)
SERVICE_CONFIRMATION_MID_ACK_VARIANTS = (
    "是的，我们这边就是帮忙牵线介绍的。",
    "对，我们这边就是顺着了解情况再帮你往合适方向看。",
    "嗯，我们这边就是先把情况聊清楚，再帮你留意合适方向的。",
)


def _extract_confirmed_sex_candidate_from_context(text: str) -> Optional[str]:
    content = str(text or "").strip()
    if not content:
        return None
    if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*男(?:生|的|孩子)?", content):
        return "男"
    if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*女(?:生|的|孩子)?", content):
        return "女"
    return None


def _is_affirmative_confirmation_answer(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
            r"(?:[呀呢啊哦哈啦嘛]*)?"
            r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
            str(text or ""),
        )
    )


BOUNDARY_PAUSE_PATTERNS = (
    r"不给电话",
    r"不方便",
    r"不想留",
    r"不太想说",
    r"不太想展开",
    r"先不说",
    r"先不留",
    r"暂时不留",
    r"先别问我这些",
    r"先别问这些",
    r"问得太细",
    r"问这么细",
    r"先不聊资料",
    r"先别聊资料",
    r"先不聊这个",
    r"先聊这个",
    r"换个话题",
    r"先聊别的",
)
WITHDRAW_STRONG_PATTERNS = (
    r"(先)?不聊了",
    r"不想(再)?聊了",
    r"不想(再)?说了",
    r"(先)?不说了",
    r"不想继续(聊|说|了解)?了",
    r"算了(吧)?",
    r"(就)?先这样(吧)?",
    r"(先)?到这(儿)?吧",
    r"(今天)?先到这(儿)?吧",
    r"(改天|回头|下次)(再|再来)?说",
    r"(暂时)?不考虑了",
    r"没必要继续了",
    r"别问了",
    r"不想回答了",
)
WITHDRAW_SOFT_PATTERNS = (
    r"先这样",
    r"先停一下",
    r"先暂停吧",
    r"晚点再聊",
    r"有空再聊",
    r"我先忙",
    r"现在不方便聊",
    r"我先去忙了",
    r"之后再说",
    r"我再想想",
    r"我考虑考虑",
    r"先不往下说了",
    r"先不往下聊了",
    r"这个先不展开了",
)
TOPIC_SHIFT_PATTERNS = (
    r"先不聊资料",
    r"先别聊资料",
    r"先别问我这些",
    r"先别问这些",
    r"先聊这个",
    r"先聊收费",
    r"先说收费",
    r"先说门店",
    r"先聊门店",
    r"先说这个",
    r"换个话题",
)
WORK_BUSY_PATTERNS = (
    r"工作比较忙",
    r"工作很忙",
    r"工作忙",
    r"平时比较忙",
    r"平时很忙",
    r"上班比较忙",
    r"最近比较忙",
)
LOCATION_REUSE_PATTERNS = (
    r"那边",
    r"同城",
    r"本地",
    r"附近",
    r"相亲资源",
    r"那边有什么",
)
PREFERENCE_REUSE_PATTERNS = (
    r"有什么推荐",
    r"有啥推荐",
    r"有推荐吗",
    r"推荐",
    r"成熟稳重",
    r"合拍",
    r"更偏",
    r"偏向",
)
COMPLAINT_PATTERNS = (
    r"问这么多",
    r"怎么问这么多",
    r"怎么问这么多信息",
    r"问这么多信息",
    r"信息问这么多",
    r"问太多",
    r"问的太多",
    r"问太多了",
    r"问的次数太多",
    r"次数太多",
    r"一直问",
    r"老问",
    r"怎么一直问",
    r"怎么老问",
    r"问了一遍又一遍",
    r"问一遍又一遍",
    r"别一直问",
    r"别老问",
    r"有点烦",
    r"太烦了",
    r"有点啰嗦",
    r"太啰嗦",
    r"查户口",
    r"问这么细",
    r"问这么详细",
    r"问得太细",
    r"问得太详细",
    r"重复问",
    r"重复了",
    r"又问这个",
    r"怎么又问",
    r"刚不是问过",
    r"刚不是问了",
    r"前面不是说了",
)

# Phase 2: 重复追问投诉模式（用于检测 "不是说了吗 / 别再问了" 类投诉）
REPEAT_ASK_COMPLAINT_PATTERNS = (
    r"不是说了[吗嘛]",
    r"不是说[了过]",
    r"不是回答[了过]",
    r"不是告诉你[了过]",
    r"不是跟你说[了过]",
    r"刚才不是[说讲]",
    r"刚不是[说讲]",
    r"前面不是[说讲]",
    r"上轮不是[说讲]",
    r"别再问",
    r"不要再问",
    r"不用再问",
    r"怎么还问",
    r"怎么又来问",
    r"你怎么还问",
    r"你怎么又问",
    r"你还问",
    r"又来这套",
    r"换个话题",
    r"换个方向",
    r"别问这个",
    r"不问这个",
    r"不用问这个",
    r"说过了",
    r"讲过了",
    r"都说了",
    r"都讲过了",
    r"已经说[了过]",
    r"已经回答[了过]",
    r"我前面说",
    r"我刚才说",
    r"我之前说",
)
ASK_GUARD_MANAGED_FIELDS = {"sex", "age", "education", "occupation", "location", "marital_status"}
ASK_GUARD_CORE_FIELDS = {"sex", "age", "education", "occupation", "location", "marital_status"}
ASK_GUARD_MEDIUM_FIELDS = {"monthly_income", "partner_requirement"}
ASK_GUARD_LOW_PRIORITY_FIELDS = {"height", "weight", "last_name"}
ASK_GUARD_QUESTION_CUES = ("？", "?", "吗", "呢", "嘛", "方便", "请问", "能否", "可否", "多少", "多大", "哪里", "哪个")
ACK_STYLE_MARKERS = ("记下", "收到", "了解", "明白", "好哒", "好呀", "好的呀")
CONTACT_ASK_MARKERS = ("电话", "手机号", "号码", "微信", "联系方式", "留个")
CONTACT_TRANSITION_MARKERS = ("顺便", "后面方便联系", "继续联系", "保持联系")
PARTNER_REQUIREMENT_ASK_MARKERS = (
    "择偶",
    "偏好",
    "看重对方",
    "另一半",
    "喜欢什么样",
    "想找什么类型",
    "更看重哪一点",
    "更在意哪方面",
    "更看重什么",
    "特别在意",
)
LOW_PRIORITY_ASK_PATTERNS = (
    r"(身高|多高|体重|多重).*(\?|？|吗|呢|嘛)",
    r"(怎么称呼|叫什么|怎么叫你|称呼你).*(\?|？|吗|呢|嘛)",
)
CLARIFICATION_USER_PATTERNS = ("没看懂", "看不懂", "听不懂", "啥意思", "什么意思", "解释下", "解释一下")
RESUME_PROFILE_COLLECTION_PATTERNS = (
    "你不问其他了",
    "你倒是问",
    "继续问",
    "继续聊资料",
    "继续问我",
    "接着问",
    "往下问",
)
CLARIFICATION_ASSISTANT_MARKERS = ("换个直白", "简单说", "意思是", "比如", "关键条件", "标准")
AFFIRMATIVE_WORDS = {"嗯", "好", "好的", "行", "可以", "ok", "是的", "对", "是", "恩", "嗯嗯", "好的呢", "好呀"}
PREFERENCE_ORIENTATION_MARKERS = ("les", "gay", "同性", "同性爱", "喜欢女生", "喜欢男生", "找女生", "找男生")
FAREWELL_MARKERS = ("先这样", "随时找我", "有需要再来", "祝你", "拜拜", "下次聊", "好消息")
EXTRACTION_CRITICAL_FIELDS = {"sex", "age", "age_label", "phone", "wechat", "contact"}
OPENING_INTENT_PRIORITY = {
    "opening_spam_or_promo": 0,
    "opening_boundary_or_contact_refusal": 1,
    "opening_clarify": 2,
    "opening_faq": 3,
    "opening_profile_provided": 4,
    "explicit_matchmaking_opening": 5,
    "low_pressure_opening": 6,
    "opening_light_consult": 7,
    "opening_greeting": 8,
}
PREFERENCE_ACK_VARIANTS = (
    "这个偏好我有数了，后面就顺着你这个感觉聊。",
    "这个点我听进去了。",
    "明白，你更在意的这个点我大概清楚了。",
)
LOCATION_MEMORY_ACK_VARIANTS = (
    "你现在主要在{location}这边。",
    "你现在主要在{location}。",
    "{location}这边我有数了。",
)
NO_REPEAT_FIELD_VARIANTS = (
    "这个点我不重复绕了，你想聊别的就顺着说。",
    "这个我大概清楚了，咱们不在这上面打转。",
)
NEUTRAL_HOLD_VARIANTS = (
    "这个点我有数了，我们接着往下聊。",
    "这个我先放这儿，咱们继续往下说。",
)
WORK_BUSY_ACK_VARIANTS = (
    "工作忙这点我有数了。",
    "平时工作节奏比较满，我能理解。",
    "忙一点我能理解。",
)
WORK_BUSY_OCCUPATION_ACK_VARIANTS = (
    "做{occupation}的话，忙一点也挺正常。",
    "像{occupation}这种工作，节奏忙我能理解。",
    "你平时做{occupation}，忙起来也正常。",
)
LOCATION_REUSE_ACK_VARIANTS = (
    "{location}这边我有数。",
    "你现在主要在{location}这边。",
    "同城这个感觉我有数了。",
)
PREFERENCE_REUSE_ACK_VARIANTS = (
    "你前面提过更偏向{preference}这一类，这个我记着。",
    "你会更看重{preference}这个点。",
    "像{preference}这种感觉，你是比较在意的。",
)
BOUNDARY_ACK_VARIANTS = (
    "好，这块我先不追问。",
    "行，这个点我先收住，先不追问。",
    "没关系，这块我先不追问，我们先按你舒服的节奏来。",
)
TOPIC_SHIFT_ACK_VARIANTS = (
    "好，那先顺着你现在更想聊的这个说，资料这块我先不追问。",
    "可以，资料这块我们先不追问。",
    "行，那就先聊你现在更在意的。",
)
PROFILE_PARTIAL_BOUNDARY_ACK_VARIANTS = (
    "{field_ack} 这块你要是现在不想展开，我们就先不追问。",
    "{field_ack} 我先接住，这一轮先不往这上面压。",
    "{field_ack} 这个我先放这儿，我们先按你舒服的节奏来。",
)
FIELD_SOFT_REFUSAL_RETRY_ACK_VARIANTS = {
    "location": (
        "没事，我不是想问得很细，就是想大概了解下你常住哪个城市，后面聊起来会更顺一点。",
        "这个我理解，我主要是想知道你现在大概在哪个城市生活，方便我顺着你的情况往下聊。",
        "没关系，不用说得太细，我就是想先知道你现在主要在哪个城市。",
    ),
    "education": (
        "这个我理解，我不是想问得很细，就是想大概了解下你的学历背景，后面沟通会更顺一点。",
        "没事，这里不用展开说很多，你告诉我大概是什么学历就行。",
        "这个我能理解，我主要是想先知道你学历大概在哪个范围。",
    ),
    "occupation": (
        "没事，我不是想问得太细，就是想大概了解下你现在做什么方向，后面聊起来更顺一点。",
        "这个我理解，你说个大概的工作方向就行，不用讲得很细。",
        "没关系，我主要是想先知道你现在大概做哪方面工作。",
    ),
    "sex": (
        "这个我理解，我就是先确认下基本情况，后面沟通会更顺一点。",
        "没事，这里我只是想先确认下你的基本信息。",
    ),
    "age": (
        "这个我理解，我主要是想先知道你大概是哪个年龄段，后面聊起来会更顺一点。",
        "没事，不用说得特别细，我就是想先确认下你大概多大。",
    ),
    "marital_status": (
        "这个我理解，我只是想先确认下你现在大概是什么感情状态，后面沟通会更顺一点。",
        "没事，这里不用说得很细，你大概说下现在的婚况或感情状态就行。",
    ),
}
OPENING_PROFILE_ACK_VARIANTS = (
    "{field_ack} 这个我有数了。",
    "{field_ack}。",
    "{field_ack} 我先记下了。",
)
WITHDRAW_RETAIN_VARIANTS = (
    "怎么啦，是哪块让你有点担心，或者不想继续聊呀？",
    "没关系，我先不往下问了。你要是有顾虑，也可以直接告诉我。",
    "是我刚才问得有点快了，还是你对这件事本身还有点担心呀？",
)
WITHDRAW_SOFT_CLOSE_VARIANTS = (
    "好，那我先不打扰你了，咱们先这样。后面你想继续聊了再来找我就行。",
    "没关系，那这轮我先收住，后面你要是想继续再来找我。",
)
NO_REPEAT_PARTNER_REQUIREMENT_STATEMENT = "这个条件我有数了，后面我会顺着这个方向聊，不重复追问。"
PARTNER_REQUIREMENT_ASK_VARIANTS = (
    "你对另一半大概有什么要求呀？",
    "你要是方便，也可以说说你想找个什么样的。",
    "你对另一半大概有什么要求呀？比如年龄、城市、性格这些，你会更看重哪方面？",
    "说到这儿，你会更看重对方哪方面？",
    "你要是愿意，也可以顺手说说你比较在意对方什么。",
)
LOW_PRIORITY_DEFLECT_VARIANTS = (
    "先不聊太细的，你更在意哪一点可以先说。",
    "次要的先放放，你更看重哪个点就先聊哪个。",
)
INCOME_ASK_VARIANTS = (
    "另外我轻问一句，你月收入大概在哪个区间呀？不方便说也没关系。",
    "如果你方便的话，我再补一个小问题：你月收入大概在哪个范围？不方便说也没关系。",
    "顺带问个不那么细的，你月收入大概在什么范围呀？不方便说也没关系。",
    "我再轻轻补一句，你现在月收入大概在哪一档？不方便说也没关系。",
    "收入这块你方便的话说个大概就行，月收入一般在哪个区间呀？",
    "要是你不介意的话，也可以顺手说下月收入大概在哪个范围，不方便说也没关系。",
)
INTERLEAVING_BUFFER_VARIANTS = (
    "你继续说，我顺着往下了解。",
    "这个我先放这儿，我们接着往下聊。",
)
ROTATING_ENDING_VARIANTS = (
    "那今天先聊到这儿，后面如果继续往下走，会先提前约时间再联系你。",
    "我们先聊到这儿，后面真要继续推进，也会在联系前先和你约个合适时间。",
    "先到这儿吧，后面如果还有需要继续沟通的地方，也会在联系前先跟你约时间。",
)

FAST_PATH_ACK_VARIANTS = {
    "sex": (
        "",
        "",
    ),
    "age": (
        "{value}我有数了。",
        "行，那我大概清楚了，{value}。",
    ),
    "location": (
        "那你现在主要在{value}。",
        "你现在主要在{value}这边。",
    ),
    "education": (
        "{value}是吧。",
        "学历这块是{value}。",
    ),
    "occupation": (
        "你现在做{value}呀。",
        "现在主要是做{value}。",
    ),
    "marital_status": (
        "那你现在是{value}这个状态。",
        "行，现在是{value}这个状态。",
    ),
}
DIVORCE_CONFIRMATION_PROMPT_VARIANTS = (
    "我先确认一个点，你这边离婚手续已经办妥了吗？",
    "那我确认一下，你这边离婚手续现在已经办妥了吗？",
    "离婚手续这块我确认下，现在是不是已经办妥了？",
    "我先问清楚一个点，离婚手续这边现在已经办妥了吗？",
)
DIVORCE_CONFIRMED_ACK_VARIANTS = {
    "location": (
        "那你现在主要在哪个城市生活？",
        "你现在是在哪个城市生活？",
    ),
    "education": (
        "那你现在是什么学历？",
        "你这边是什么学历？",
    ),
    "occupation": (
        "那你现在是做什么工作的？",
        "你现在主要做什么工作？",
    ),
    "marital_status": (
        "好，这个我清楚了。",
        "嗯，这个我知道了。",
    ),
    "contact": (
        "要是你愿意，留个电话也行。",
        "你这边要是方便的话，留个电话也行。",
    ),
}
DELIVERY_DANGLING_ENDINGS = (
    "我们平时",
    "后续要是",
    "留个常用微信也行，我们",
    "方便的话，留个常用微信也行，我们",
    "哈哈，原来",
    "原来",
    "这样的话",
    "所以说",
)

class ChatService:
    _ALLOWED_MAIN_SIDE_PAIRS: dict[str, set[str]] = {
        "education": {"marital_status"},
        "occupation": {"monthly_income", "marital_status"},
        "location": {"monthly_income", "marital_status", "partner_requirement"},
        "age": {"marital_status", "partner_requirement"},
        "marital_status": {"partner_requirement"},
    }

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
    - 本类主要负责流程编排、状态副作用和兼容入口

    维护约束：
    - 单轮理解统一收口到 TurnUnderstandingService
    - 动作边界统一收口到 ProfileCollectionPolicy
    - 本类不再新增第二套用户意图识别逻辑
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
        r"(互换|交换)(照片|联系方式)",
        r"(再)?(给你)?介绍(男生|女生|对方)的具体情况",
        r"发(你)?具体(定位|地址)",
        r"具体(定位|地址)",
        r"(和)?地址",
        r"第一时间联系你",
        r"\d+\s*(到|-)\s*\d+\s*(小时|天)内",
        r"\d+\s*(小时|天)内",
    )
    SALESY_CLAUSE_PATTERNS = (
        r"[，,]?绝对不会[^，。！？!?]*(?:广告|骚扰|打扰)[^，。！？!?]*",
        r"[，,]?不会[^，。！？!?]*(?:广告|骚扰|打扰)[^，。！？!?]*",
        r"[，,]?平时[^，。！？!?]*(?:广告|骚扰|打扰)[^，。！？!?]*",
        r"[，,]?手里好多[^，。！？!?]*资源[^，。！？!?]*",
        r"[，,]?(?:本地)?优质的?单身资源[^，。！？!?]*",
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
        self.dialogue_expression_service = DialogueExpressionService()
        self.turn_intent_classifier = TurnIntentClassifier()
        self.input_fallback_service = InputFallbackService(
            user_service=user_service,
            nonsense_prefix=self._nonsense_count_prefix,
            confirm_prefix=self._confirm_count_prefix,
        )
        self.conversation_rule_service = ConversationRuleService(chat_service=self)
        self.user_question_service = UserQuestionService()
        self.collection_policy = ProfileCollectionPolicy()
        self.turn_understanding_service = TurnUnderstandingService(self)
        self.unified_turn_understanding_service = UnifiedTurnUnderstandingService(
            semantic_service=self.turn_understanding_service,
            ai_service=self.ai_service,
        )
        self.confirmation_ai_fallback_classifier = ConfirmationAIFallbackClassifier(
            ai_service=self.ai_service,
        )
        self.personality_profile = PersonalityProfile()
        self.response_plan_builder = ResponsePlanBuilder(
            collection_policy=self.collection_policy,
            turn_understanding_service=self.turn_understanding_service,
        )
        self.response_plan_prompt_formatter = ResponsePlanPromptFormatter()
        self.profile_bridge_prompt_formatter = ProfileBridgePromptFormatter()
        self.opening_intent_prompt_formatter = OpeningIntentPromptFormatter()
        self.prompt_assembly_service = PromptAssemblyService(
            profile_bridge_prompt_formatter=self.profile_bridge_prompt_formatter,
            response_plan_prompt_formatter=self.response_plan_prompt_formatter,
            opening_intent_prompt_formatter=self.opening_intent_prompt_formatter,
        )
        self.ai_response_generator = AIResponseGenerator(ai_service=self.ai_service)
        self.unified_response_draft_service = ResponseDraftService()
        self.unified_response_validation_service = ResponseValidationService()
        self.unified_response_safe_cleanup_service = ResponseSafeCleanupService()
        self.unified_response_delivery_service = ResponseDeliveryService()
        self.unified_response_observability_service = ResponseObservabilityService()
        self.first_generation_delivery_service = FirstGenerationDeliveryService()
        self.preparation_service = ChatServicePreparationService(self)
        self.generation_service = ChatServiceGenerationService(self)
        self.delivery_service = ChatServiceDeliveryService(self)
        self.finalize_service = ChatServiceFinalizeService(self)
        self.message_signal_service = ChatServiceMessageSignalService(self)
        self._resume_guard_service: ChatServiceResumeGuardService | None = None
        self._contact_context_service: ChatServiceContactContextService | None = None
        self._contact_resume_service: ChatServiceContactResumeService | None = None
        self._contact_validation_flow_service: ChatServiceContactValidationFlowService | None = None
        self._collection_postprocess_service: ChatServiceCollectionPostprocessService | None = None
        self._validation_recovery_service: ChatServiceValidationRecoveryService | None = None
        self._confirmation_fallback_service: ChatServiceConfirmationFallbackService | None = None
        self._collection_extraction_service: ChatServiceCollectionExtractionService | None = None
        self._ending_generation_service: ChatServiceEndingGenerationService | None = None
        self._generation_prompt_service: ChatServiceGenerationPromptService | None = None
        self._preset_response_service: ChatServicePresetResponseService | None = None
        self._text_cleanup_service: ChatServiceTextCleanupService | None = None
        self._followup_prompt_service: ChatServiceFollowupPromptService | None = None
        self._turn_text_policy_service: ChatServiceTurnTextPolicyService | None = None
        self.text_policy_service = ChatServiceTextPolicyService()
        self._ending_state_service: ChatServiceEndingStateService | None = None
        self.profile_collection_coordinator = ProfileCollectionCoordinator(self)
        self.process_chat_turn_use_case = ProcessChatTurnUseCase(self)

        # 临时存储可能的拒绝字段
        self._temp_refused_fields = {}
        self._last_ai_failure_reason: Optional[str] = None
        self._last_validation_feedback_meta: Optional[Dict[str, Any]] = None
        self._last_opening_intent_signal: Optional[OpeningIntentSignal] = None
        self._last_unified_generation_record: Optional[Dict[str, Any]] = None
        self._last_turn_alignment_obs: Optional[Dict[str, Any]] = None

    async def process_chat_request(self, request: ChatRequest) -> Dict[str, Any]:
        """处理聊天请求 - 兼容入口，主流程已迁移到 use case。"""
        return await self.process_chat_turn_use_case.execute(request)

    @property
    def resume_guard_service(self) -> ChatServiceResumeGuardService:
        if self._resume_guard_service is None:
            self._resume_guard_service = ChatServiceResumeGuardService(self)
        return self._resume_guard_service

    @property
    def ending_state_service(self) -> ChatServiceEndingStateService:
        if self._ending_state_service is None:
            self._ending_state_service = ChatServiceEndingStateService(self)
        return self._ending_state_service

    @property
    def contact_context_service(self) -> ChatServiceContactContextService:
        if self._contact_context_service is None:
            self._contact_context_service = ChatServiceContactContextService(self)
        return self._contact_context_service

    @property
    def contact_resume_service(self) -> ChatServiceContactResumeService:
        if self._contact_resume_service is None:
            self._contact_resume_service = ChatServiceContactResumeService(self)
        return self._contact_resume_service

    @property
    def contact_validation_flow_service(self) -> ChatServiceContactValidationFlowService:
        if self._contact_validation_flow_service is None:
            self._contact_validation_flow_service = ChatServiceContactValidationFlowService(self)
        return self._contact_validation_flow_service

    @property
    def collection_postprocess_service(self) -> ChatServiceCollectionPostprocessService:
        if self._collection_postprocess_service is None:
            self._collection_postprocess_service = ChatServiceCollectionPostprocessService(self)
        return self._collection_postprocess_service

    @property
    def validation_recovery_service(self) -> ChatServiceValidationRecoveryService:
        if self._validation_recovery_service is None:
            self._validation_recovery_service = ChatServiceValidationRecoveryService(self)
        return self._validation_recovery_service

    @property
    def confirmation_fallback_service(self) -> ChatServiceConfirmationFallbackService:
        if self._confirmation_fallback_service is None:
            self._confirmation_fallback_service = ChatServiceConfirmationFallbackService(self)
        return self._confirmation_fallback_service

    @property
    def collection_extraction_service(self) -> ChatServiceCollectionExtractionService:
        if self._collection_extraction_service is None:
            self._collection_extraction_service = ChatServiceCollectionExtractionService(self)
        return self._collection_extraction_service

    @property
    def ending_generation_service(self) -> ChatServiceEndingGenerationService:
        if self._ending_generation_service is None:
            self._ending_generation_service = ChatServiceEndingGenerationService(self)
        return self._ending_generation_service

    @property
    def generation_prompt_service(self) -> ChatServiceGenerationPromptService:
        if self._generation_prompt_service is None:
            self._generation_prompt_service = ChatServiceGenerationPromptService(self)
        return self._generation_prompt_service

    @property
    def preset_response_service(self) -> ChatServicePresetResponseService:
        if self._preset_response_service is None:
            self._preset_response_service = ChatServicePresetResponseService(self)
        return self._preset_response_service

    @property
    def text_cleanup_service(self) -> ChatServiceTextCleanupService:
        if self._text_cleanup_service is None:
            self._text_cleanup_service = ChatServiceTextCleanupService(self)
        return self._text_cleanup_service

    @property
    def followup_prompt_service(self) -> ChatServiceFollowupPromptService:
        if self._followup_prompt_service is None:
            self._followup_prompt_service = ChatServiceFollowupPromptService(self)
        return self._followup_prompt_service

    @property
    def turn_text_policy_service(self) -> ChatServiceTurnTextPolicyService:
        if self._turn_text_policy_service is None:
            self._turn_text_policy_service = ChatServiceTurnTextPolicyService(self)
        return self._turn_text_policy_service

    async def _handle_refusal_detection(
        self,
        user_message: str,
        account_id: str,
        user_profile: UserProfile,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> None:
        """
        处理拒绝检测，包括提前拒绝联系方式

        使用 ContactCollectionService 统一处理联系方式相关的拒绝检测
        """
        # === 入口日志（INFO级别，便于调试）===
        logger.info(f"[拒绝检测-开始] account_id={account_id}, phone_ask_count={user_profile.phone_ask_count}, wechat_ask_count={user_profile.wechat_ask_count}, rejected_phone={user_profile.rejected_phone}, rejected_wechat={user_profile.rejected_wechat}")

        last_response = await self.dialogue_manager.get_last_response(account_id)
        faq_intent = self._extract_priority_question_intent_from_understanding(understanding_result)
        if faq_intent is None:
            faq_intent = self.user_question_service.detect_quick_faq_intent(user_message)
        last_contact_request_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()

        if (
            faq_intent
            and last_contact_request_type in {"phone", "wechat"}
            and hasattr(self.contact_service, "rollback_pending_request_state")
        ):
            already_collected = bool(getattr(user_profile, f"{last_contact_request_type}_collected", False))
            already_rejected = bool(getattr(user_profile, f"rejected_{last_contact_request_type}", False))
            if not already_collected and not already_rejected:
                self.contact_service.rollback_pending_request_state(user_profile, last_contact_request_type)
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(
                    "[联系方式打断] FAQ 打断了 %s 追问，回滚未兑现的有效询问次数",
                    last_contact_request_type,
                )

        # 检测用户是否拒绝（通用拒绝检测）
        is_refusing = self.refusal_service.is_refusing(user_message)
        if (
            is_refusing
            and getattr(user_profile, "pending_birth_year_bucket", None)
            and self._is_birth_year_bucket_question(last_response)
        ):
            user_profile.birth_year_confirmation_closed = True
            user_profile.close_active_ask("age")
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info("[年龄年份确认] 用户拒绝补充具体年份，保留年龄桶并继续主线")
            is_refusing = False
        if is_refusing and last_response:
            refused_fields = self._infer_effective_refused_fields(user_profile, last_response)
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

    async def handle_refusal_detection(
        self,
        user_message: str,
        account_id: str,
        user_profile: UserProfile,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> None:
        await self._handle_refusal_detection(
            user_message,
            account_id,
            user_profile,
            understanding_result=understanding_result,
        )

    def _infer_effective_refused_fields(self, user_profile: UserProfile, last_response: str) -> list[str]:
        refused_fields: list[str] = []
        primary_field = str(getattr(user_profile, "last_asked_field", "") or "").strip()
        side_field = str(getattr(user_profile, "last_asked_side_field", "") or "").strip()
        for field in (primary_field, side_field):
            if field and field not in refused_fields:
                refused_fields.append(field)
        if refused_fields:
            return refused_fields
        detected = sorted(self._detect_asked_fields_in_response(last_response))
        return detected or self.extraction_service.infer_refused_fields(last_response)

    @staticmethod
    def _is_birth_year_bucket_question(last_response: str) -> bool:
        text = str(last_response or "")
        return bool(
            re.search(r"(具体是\d{2}几年的|具体是哪一年的|哪一年出生)", text)
        )

    def _select_model_for_turn(self, user_message: str, prompt: str) -> str:
        """
        拟人化优先：统一走主模型，避免快模型路由带来的表达质量波动。
        """
        return getattr(self.ai_service, "model_name", settings.model_name)

    def _maybe_build_model_free_followup_response(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision | None = None,
    ) -> str:
        decision = turn_decision
        if decision is None:
            return ""
        if str(getattr(decision, "response_channel", "") or "").strip() != "model":
            return ""
        if str(getattr(decision, "primary_move", "") or "").strip() not in {"ack_and_ask", "light_followup"}:
            return ""
        if str(getattr(decision, "followup_topic", "") or "").strip() not in {"profile_ack", "opening_profile_ack"}:
            return ""
        if bool(getattr(decision, "prioritize_user_question", False)):
            return ""
        if bool(getattr(decision, "allow_medium_target", False)):
            return ""
        if str(getattr(decision, "risk", "none") or "").strip() not in {"", "none"}:
            return ""

        ask_field = str(getattr(decision, "ask_field", "") or "").strip()
        if not ask_field or ask_field == "contact":
            return ""

        followup = self._build_followup_seed_for_model_rewrite(
            ask_field,
            user_profile,
            user_message=user_message,
        ).strip()
        if not followup:
            return ""

        ack = (
            self.turn_understanding_service._build_opening_profile_ack(user_message)  # noqa: SLF001
            or self.turn_understanding_service._build_lightweight_field_ack(user_message, user_profile)  # noqa: SLF001
        )
        return self._sanitize_robotic_tone(" ".join(part for part in (ack, followup) if part).strip())

    @staticmethod
    def _normalize_reasoning_effort(value: str) -> str | None:
        normalized = str(value or "").strip().lower()
        if normalized in {"minimal", "low", "medium", "high"}:
            return normalized
        return None

    def _select_reasoning_effort_for_turn(self, *, turn_decision: TurnDecision | None = None) -> str | None:
        if turn_decision is not None and str(getattr(turn_decision, "response_channel", "") or "").strip() != "model":
            return None
        env_value = os.getenv("CHAT_REPLY_REASONING_EFFORT", "minimal")
        return self._normalize_reasoning_effort(env_value)

    def _should_use_max_completion_tokens_for_turn(
        self,
        *,
        turn_decision: TurnDecision | None = None,
    ) -> bool:
        if turn_decision is not None and str(getattr(turn_decision, "response_channel", "") or "").strip() != "model":
            return False
        return self._env_flag("CHAT_REPLY_USE_MAX_COMPLETION_TOKENS", True)

    def _select_max_tokens_for_turn(self, user_message: str, prompt: str) -> int:
        """
        拟人化优先：不再按低复杂度或长 prompt 压缩输出长度。
        """
        default_max_tokens = self._env_int("CHAT_AI_MAX_TOKENS", 360)
        if default_max_tokens <= 0:
            default_max_tokens = 360
        return default_max_tokens

    @staticmethod
    def _matches_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
        content = str(text or "")
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)

    def _should_keep_contact_refusal_in_contact_flow(
        self,
        user_message: str,
        user_profile: Optional[UserProfile],
        *,
        understanding: Optional[TurnUnderstandingResult] = None,
    ) -> bool:
        """联系方式场景中的委婉拒绝继续走现有联系方式追问链路，不被边界收口吞掉。"""
        if user_profile is None:
            return False
        if understanding is not None and not (
            understanding.primary_turn_type == "refusal_boundary_complaint"
            and (understanding.subtype or "") == "contact_refusal"
        ):
            return False

        message = (user_message or "").strip()
        if not message:
            return False
        if not any(token in message for token in ("不方便", "不想留", "不留", "不给", "算了")):
            return False

        last_contact_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
        has_real_contact_flow = bool(
            last_contact_type in {"phone", "wechat"}
            or getattr(user_profile, "phone_ask_count", 0) > 0
            or getattr(user_profile, "wechat_ask_count", 0) > 0
            or getattr(user_profile, "phone_collected", False)
            or getattr(user_profile, "wechat_collected", False)
        )
        if not has_real_contact_flow:
            return False

        if last_contact_type in {"phone", "wechat"}:
            return True

        try:
            next_action = self.contact_service.get_next_action(user_profile, message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return False

        return action_value in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}

    def _looks_like_fake_info_message(self, user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False

        extraction_service = getattr(self, "extraction_service", None)
        analysis = {}
        stable_self_age = None
        if extraction_service is not None:
            analysis = extraction_service.analyze_numeric_semantics(message)
            stable_self_age, _ = extraction_service.resolve_stable_self_age(
                user_message=message,
                resolved_age=None,
            )
        if stable_self_age is not None and (stable_self_age <= 10 or stable_self_age >= 120):
            return True

        age_match = re.search(r"(?:今年|我今年|年龄|岁数)?\s*(\d{1,4})\s*岁", message)
        if age_match and not bool((analysis or {}).get("partner_age_gap_candidates")):
            age_value = int(age_match.group(1))
            if age_value <= 10 or age_value >= 120:
                return True

        for raw_height in list((analysis or {}).get("height_candidates") or []):
            digits = re.sub(r"[^\d.]", "", str(raw_height or ""))
            if not digits:
                continue
            if "." in digits:
                try:
                    meter_value = float(digits)
                except ValueError:
                    meter_value = 0.0
                if meter_value >= 2.6 or meter_value <= 0.8:
                    return True
                continue
            try:
                height_value = int(digits)
            except ValueError:
                height_value = 0
            if height_value <= 80 or height_value >= 260:
                return True

        height_meter_match = re.search(r"(?:身高|高)\s*(\d(?:\.\d+)?)\s*米", message)
        if height_meter_match:
            try:
                meter_value = float(height_meter_match.group(1))
            except ValueError:
                meter_value = 0.0
            if meter_value >= 2.6 or meter_value <= 0.8:
                return True

        return False

    def _is_complaint_message(self, user_message: str) -> bool:
        """
        检测用户抱怨问太多/重复问的输入。

        触发场景：
        - "是不是问太多了"
        - "怎么一直问"
        - "问了一遍又一遍"
        - "有点烦"
        - "查户口"
        """
        message = (user_message or "").strip()
        if not message:
            return False
        if self._matches_any_pattern(message, REPEAT_ASK_COMPLAINT_PATTERNS):
            return True
        if self._matches_any_pattern(message, COMPLAINT_PATTERNS):
            return True
        # FAQ 意图优先，避免把答疑请求误判为抱怨
        if self._has_faq_priority_signal(message):
            return False
        return False

    def _classify_withdraw_intent(self, user_message: str) -> Optional[str]:
        message = (user_message or "").strip()
        if not message:
            return None
        if self._has_faq_priority_signal(message):
            return None
        if self._matches_any_pattern(message, WITHDRAW_STRONG_PATTERNS):
            return "strong"
        if self._matches_any_pattern(message, WITHDRAW_SOFT_PATTERNS):
            return "soft"
        return None

    def _is_withdraw_or_stop_message(self, user_message: str) -> bool:
        return self.message_signal_service.is_withdraw_or_stop_message(user_message)

    @staticmethod
    def _has_any_valid_contact(user_profile: Optional[UserProfile]) -> bool:
        return ChatServiceMessageSignalService.has_any_valid_contact(user_profile)

    def _reached_question_ceiling(self, user_profile: UserProfile) -> bool:
        core_ready = all(
            self.collection_policy.is_collected(user_profile, field)
            or user_profile.get_ask_count(field) >= 2
            for field in ASK_GUARD_CORE_FIELDS
        )
        medium_ready = all(
            self.collection_policy.is_collected(user_profile, field)
            or user_profile.get_ask_count(field) >= 1
            for field in ASK_GUARD_MEDIUM_FIELDS
        )
        return core_ready and medium_ready

    def _build_withdraw_response(self, user_profile: UserProfile, *, user_message: str = "") -> tuple[str, bool]:
        if self._can_close_on_withdraw_after_contact(user_profile):
            return self.expectation_service.get_contact_completion_response(user_profile), True

        withdraw_count = user_profile.get_ask_count("conversation_end_intent")
        if self._reached_question_ceiling(user_profile) or withdraw_count >= 2:
            return random.choice(WITHDRAW_SOFT_CLOSE_VARIANTS), True

        return random.choice(WITHDRAW_RETAIN_VARIANTS), False

    def _can_close_on_withdraw_after_contact(self, user_profile: UserProfile) -> bool:
        if not self._has_any_valid_contact(user_profile):
            return False
        return not self.collection_policy.get_uncovered_core_fields(user_profile)

    def _has_remaining_profile_fields(self, user_profile: UserProfile) -> bool:
        return bool(
            self.collection_policy.get_uncovered_core_fields(user_profile)
            or self.collection_policy.get_uncovered_medium_fields(user_profile)
        )

    @staticmethod
    def _looks_like_strong_concern_interrupt(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        strong_markers = (
            "中介",
            "套路",
            "骗人",
            "骗",
            "靠谱吗",
            "靠不靠谱",
            "安全",
            "隐私",
            "骚扰",
            "会不会",
            "真的假的",
            "真实吗",
            "托",
        )
        return any(marker in message for marker in strong_markers)

    def _resolve_interrupted_followup_field(
        self,
        user_profile: UserProfile,
        *,
        last_response: str = "",
        fallback_user_message: str = "",
    ) -> Optional[str]:
        def _needs_resume(field_name: str) -> bool:
            if not field_name or field_name == "contact":
                return False
            if field_name in getattr(self.collection_policy, "MEDIUM_FIELDS", []):
                return not self.collection_policy.is_collected(user_profile, field_name)
            return not self.collection_policy.is_field_covered(user_profile, field_name)

        last_asked_field = str(getattr(user_profile, "last_asked_field", "") or "").strip()
        if _needs_resume(last_asked_field):
            return last_asked_field

        previous_asked_field = self.turn_understanding_service._detect_which_field_is_asked(last_response)  # noqa: SLF001
        if _needs_resume(previous_asked_field):
            return previous_asked_field

        resume_target = str(getattr(user_profile, "resume_profile_target", "") or "").strip()
        if _needs_resume(resume_target):
            return resume_target

        decision = self.collection_policy.decide(
            user_profile,
            user_message=fallback_user_message,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        )
        next_field = str(decision.main_target or "").strip()
        if next_field and next_field != "contact" and self.collection_policy.can_actively_ask(user_profile, next_field):
            return next_field
        next_progress_target = str(
            self._select_next_progress_target(user_profile, user_message=fallback_user_message) or ""
        ).strip()
        if next_progress_target and next_progress_target != "contact":
            return next_progress_target
        return None

    def _build_resume_after_interrupt_response(
        self,
        answer_text: str,
        user_profile: UserProfile,
        *,
        user_message: str,
        last_response: str = "",
    ) -> str:
        followup_field = self._resolve_interrupted_followup_field(
            user_profile,
            last_response=last_response,
            fallback_user_message=user_message,
        )
        if not followup_field:
            return answer_text.strip()
        followup = self._build_followup_seed_for_model_rewrite(
            followup_field,
            user_profile,
            user_message=user_message,
        ).strip()
        if not followup:
            return answer_text.strip()
        return f"{answer_text.strip()} {followup}".strip()

    def _enforce_opening_listener_first_policy(
        self,
        response: str,
        understanding: Optional[TurnUnderstandingResult],
        user_message: str,
    ) -> str:
        text = str(response or "").strip()
        if not text or understanding is None:
            return text

        if understanding.primary_turn_type == "opening" and understanding.subtype == "greeting":
            if not any(marker in text for marker in ("找对象", "了解下", "看看情况", "问问情况", "聊聊")):
                return self.greeting_service.get_greeting_response(user_message)
            return text

        if understanding.primary_turn_type == "opening" and any(token in user_message for token in ("喜欢", "想找", "偏向")):
            if not any(token in text for token in ("深圳", "女生", "同城", "偏向", "看重")):
                pref_fragments = []
                if "深圳" in user_message:
                    pref_fragments.append("深圳这边")
                if "女生" in user_message:
                    pref_fragments.append("女生")
                if not pref_fragments and any(token in user_message for token in ("同城", "本地")):
                    pref_fragments.append("同城")
                if pref_fragments:
                    joined = "".join(pref_fragments)
                    return f"你是更偏{joined}这类是吧。那你也说说你自己的情况，我顺着了解。".strip()
                opening_ack = self.turn_understanding_service._build_opening_profile_ack(user_message)  # noqa: SLF001
                if opening_ack:
                    return f"{opening_ack} 你也可以先简单说说自己，我顺着了解。".strip()

        if understanding.primary_turn_type == "opening" and understanding.subtype in {"matchmaking_intent", "low_pressure_opening"}:
            if not any(marker in text for marker in ("介绍下自己", "简单说说自己", "顺着了解", "大概情况")):
                return self.greeting_service.get_open_self_intro_response()
            return text

        if understanding.primary_turn_type == "refusal_boundary_complaint" and (understanding.subtype or "") in {"boundary_defensive", "refusal"}:
            if not any(marker in text for marker in ("可以", "不强求", "不留也行", "先聊")):
                return "可以，不想留也行，我们先聊别的。"
            return text

        return text

    @staticmethod
    def _build_quick_turn_decision(
        *,
        intent: str,
        risk: str,
        stage: str,
        primary_move: str,
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        followup_topic: Optional[str] = None,
        context_ack_type: Optional[str] = None,
        context_ack_payload: Optional[Dict[str, Any]] = None,
        context_ack_occupation: Optional[str] = None,
        context_ack_location: Optional[str] = None,
        context_ack_preference: Optional[str] = None,
        context_ack_field_ack: Optional[str] = None,
        soft_retry_field: Optional[str] = None,
        in_repair_mode: bool = False,
        repair_cooldown_remaining: int = 0,
        priority_primary_task: Optional[str] = None,
        priority_level: int = 0,
        priority_reason: Optional[str] = None,
        priority_response_mode: Optional[str] = None,
        priority_suppressed_tasks: Optional[list[str]] = None,
    ) -> TurnDecision:
        tone_policy = {
            "ack_budget_per_n_turns": 3,
            "max_core_question_per_turn": 1,
            "allow_related_medium_side_target": True,
            "enforce_contact_transition": False,
            "core_streak_max": 1 if primary_move == "soft_hold" else 3,
        }
        return TurnDecision(
            intent=intent,
            risk=risk,
            stage=stage,
            next_action="continue",
            primary_move=primary_move,
            ask_field=None,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            response_channel="quick_faq",
            tone_policy=tone_policy,
            in_repair_mode=in_repair_mode,
            repair_cooldown_remaining=repair_cooldown_remaining,
            followup_topic=followup_topic,
            context_ack_required=bool(followup_topic or context_ack_type),
            context_ack_type=context_ack_type,
            context_ack_payload=dict(context_ack_payload or {}),
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
            priority_primary_task=priority_primary_task,
            priority_level=priority_level,
            priority_reason=priority_reason,
            priority_response_mode=priority_response_mode,
            priority_suppressed_tasks=list(priority_suppressed_tasks or []),
        )

    @staticmethod
    def _get_priority_decision(understanding: TurnUnderstandingResult | None):
        return getattr(understanding, "priority_decision", None) if understanding is not None else None

    @classmethod
    def _priority_kwargs_from_understanding(cls, understanding: TurnUnderstandingResult | None) -> Dict[str, Any]:
        priority = cls._get_priority_decision(understanding)
        if priority is None:
            return {}
        return {
            "priority_primary_task": getattr(priority, "primary_task", None),
            "priority_level": int(getattr(priority, "priority_level", 0) or 0),
            "priority_reason": getattr(priority, "decision_reason", None),
            "priority_response_mode": getattr(priority, "response_mode", None),
            "priority_suppressed_tasks": list(getattr(priority, "suppressed_tasks", []) or []),
        }

    def _build_status_priority_turn_decision(
        self,
        *,
        understanding: TurnUnderstandingResult,
        stage: str,
        followup_topic: Optional[str],
        context_ack_payload: Dict[str, Any],
    ) -> TurnDecision | None:
        priority = self._get_priority_decision(understanding)
        if priority is None or getattr(priority, "primary_task", "") != "status_confirmation":
            return None

        locked_field = str(getattr(priority, "locked_field", "") or "").strip() or None
        priority_reason = str(getattr(priority, "decision_reason", "") or "").strip()
        next_action = "confirm_divorce_status" if priority_reason == "divorce_confirmation_pending" else "continue"
        return self._build_general_turn_decision(
            intent="confirmation",
            risk="none",
            stage=stage,
            next_action=next_action,
            primary_move="confirm_status_only",
            ask_field=locked_field,
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=False,
            response_channel="model",
            in_repair_mode=False,
            repair_cooldown_remaining=0,
            user_concern_type=None,
            resume_mode=None,
            resume_target=None,
            resume_applied=False,
            followup_topic=followup_topic,
            context_ack_payload=context_ack_payload,
            context_ack_occupation=getattr(understanding, "context_ack_occupation", None),
            context_ack_location=getattr(understanding, "context_ack_location", None),
            context_ack_preference=getattr(understanding, "context_ack_preference", None),
            context_ack_field_ack=getattr(understanding, "context_ack_field_ack", None),
            soft_retry_field=getattr(understanding, "soft_retry_field", None),
            **self._priority_kwargs_from_understanding(understanding),
        )

    def _build_understanding_quick_decision(
        self,
        *,
        understanding: TurnUnderstandingResult,
        user_profile: UserProfile,
        user_message: str,
        stage: str,
        followup_topic: Optional[str],
        context_ack_payload: Dict[str, Any],
    ) -> TurnDecision | None:
        context_ack_occupation = getattr(understanding, "context_ack_occupation", None)
        context_ack_location = getattr(understanding, "context_ack_location", None)
        context_ack_preference = getattr(understanding, "context_ack_preference", None)
        context_ack_field_ack = getattr(understanding, "context_ack_field_ack", None)
        soft_retry_field = getattr(understanding, "soft_retry_field", None)
        priority_kwargs = self._priority_kwargs_from_understanding(understanding)
        opening_followup_decision = self._build_opening_profile_provided_followup_decision(
            understanding=understanding,
            user_profile=user_profile,
            user_message=user_message,
            stage=stage,
            followup_topic=followup_topic,
            context_ack_payload=context_ack_payload,
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
        )
        if opening_followup_decision is not None:
            return opening_followup_decision
        if understanding.primary_turn_type == "risk_guard":
            return self._build_quick_turn_decision(
                intent="risk_guard",
                risk="high_risk",
                stage=stage,
                primary_move="answer_then_pause",
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                context_ack_type=understanding.context_ack_type,
                **priority_kwargs,
            )
        if understanding.primary_turn_type == "closing_exit":
            return self._build_quick_turn_decision(
                intent="withdraw_or_stop",
                risk="withdraw",
                stage=stage,
                primary_move="soft_hold",
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                **priority_kwargs,
            )
        if understanding.primary_turn_type == "refusal_boundary_complaint":
            subtype = understanding.subtype or ""
            if subtype == "complaint":
                if not (user_profile.repair_mode and user_profile.ask_cooldown_turns > 0):
                    user_profile.enter_repair_mode(
                        reason=understanding.complaint_reason or "complaint",
                        cooldown_turns=3,
                    )
                return self._build_quick_turn_decision(
                    intent="complaint",
                    risk="none",
                    stage=stage,
                    primary_move="repair_and_release",
                    prioritize_user_question=False,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic=followup_topic,
                    context_ack_type=understanding.context_ack_type,
                    context_ack_payload=context_ack_payload,
                    context_ack_occupation=context_ack_occupation,
                    context_ack_location=context_ack_location,
                    context_ack_preference=context_ack_preference,
                    context_ack_field_ack=context_ack_field_ack,
                    soft_retry_field=soft_retry_field,
                    in_repair_mode=True,
                    repair_cooldown_remaining=user_profile.ask_cooldown_turns,
                    **priority_kwargs,
                )
            if subtype == "contact_refusal":
                return None
            if subtype in {"boundary_defensive", "refusal"}:
                return self._build_quick_turn_decision(
                    intent="boundary",
                    risk="boundary",
                    stage=stage,
                    primary_move="ack_and_hold",
                    prioritize_user_question=False,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic=followup_topic,
                    context_ack_type=understanding.context_ack_type,
                    context_ack_payload=context_ack_payload,
                    context_ack_occupation=context_ack_occupation,
                    context_ack_location=context_ack_location,
                    context_ack_preference=context_ack_preference,
                    context_ack_field_ack=context_ack_field_ack,
                    soft_retry_field=soft_retry_field,
                    **priority_kwargs,
                )
        if understanding.primary_turn_type == "opening":
            secondary_signals = set(understanding.secondary_signals or [])
            if understanding.subtype == "greeting":
                return self._build_quick_turn_decision(
                    intent="opening_probe",
                    risk="none",
                    stage=stage,
                    primary_move="answer_then_pause",
                    prioritize_user_question=True,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic=followup_topic,
                    **priority_kwargs,
                )
            if understanding.subtype == "opening_clarify":
                return self._build_quick_turn_decision(
                    intent="opening_clarify",
                    risk="none",
                    stage=stage,
                    primary_move="answer_then_pause",
                    prioritize_user_question=True,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic="opening_clarify",
                    **priority_kwargs,
                )
            if understanding.subtype == "matchmaking_intent":
                if (
                    "service_confirmation_like" in secondary_signals
                    and not self._effective_resolved_slots(understanding)
                ):
                    return self._build_quick_turn_decision(
                        intent="opening_light_consult",
                        risk="none",
                        stage=stage,
                        primary_move="answer_then_pause",
                        prioritize_user_question=True,
                        allow_contact_target=False,
                        allow_medium_target=False,
                        followup_topic="opening_self_intro",
                        **priority_kwargs,
                    )
                return self._build_quick_turn_decision(
                    intent="opening_self_intro",
                    risk="none",
                    stage=stage,
                    primary_move="answer_then_pause",
                    prioritize_user_question=False,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic=followup_topic,
                    context_ack_type=understanding.context_ack_type,
                    context_ack_payload=context_ack_payload,
                    context_ack_occupation=context_ack_occupation,
                    context_ack_location=context_ack_location,
                    context_ack_preference=context_ack_preference,
                    context_ack_field_ack=context_ack_field_ack,
                    soft_retry_field=soft_retry_field,
                    **priority_kwargs,
                )
            if understanding.subtype in {"low_pressure_opening", "service_confirmation_opening"}:
                return self._build_quick_turn_decision(
                    intent="opening_light_consult" if understanding.subtype == "service_confirmation_opening" else "opening_self_intro",
                    risk="none",
                    stage=stage,
                    primary_move="answer_then_pause",
                    prioritize_user_question=understanding.subtype == "service_confirmation_opening",
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic="opening_self_intro" if understanding.subtype == "service_confirmation_opening" else followup_topic,
                    **priority_kwargs,
                )
        if understanding.primary_turn_type == "faq_concern" and understanding.subtype == "service_confirmation_mid":
            return self._build_quick_turn_decision(
                intent="service_confirmation",
                risk="none",
                stage=stage,
                primary_move="answer_then_pause",
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                **priority_kwargs,
            )
        return None

    def _build_opening_profile_provided_followup_decision(
        self,
        *,
        understanding: TurnUnderstandingResult,
        user_profile: UserProfile,
        user_message: str,
        stage: str,
        followup_topic: Optional[str],
        context_ack_payload: Dict[str, Any],
        context_ack_occupation: Optional[str],
        context_ack_location: Optional[str],
        context_ack_preference: Optional[str],
        context_ack_field_ack: Optional[str],
        soft_retry_field: Optional[str],
    ) -> TurnDecision | None:
        if understanding.primary_turn_type != "opening":
            return None
        if understanding.subtype not in {"greeting", "matchmaking_intent", "low_pressure_opening"}:
            return None
        if (
            understanding.subtype == "matchmaking_intent"
            and not self._get_meaningful_opening_resolved_slots(understanding)
            and not self._opening_message_has_substantive_profile_content(user_message, understanding)
        ):
            return None
        opening_resolved_slots = self._get_meaningful_opening_resolved_slots(understanding)
        if not (opening_resolved_slots or self._opening_message_has_substantive_profile_content(user_message, understanding)):
            return None

        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            message_count=0,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
            understanding_result=understanding,
        )
        ask_field = str(policy_decision.main_target or "").strip()
        if not ask_field or ask_field == "contact":
            return None

        tone_policy = {
            "ack_budget_per_n_turns": 3,
            "max_core_question_per_turn": 1,
            "allow_related_medium_side_target": True,
            "enforce_contact_transition": False,
            "core_streak_max": 3,
        }
        resolved_followup_topic = followup_topic or getattr(understanding, "context_ack_type", None)
        return TurnDecision(
            intent="opening_self_intro",
            risk="none",
            stage=stage,
            next_action="continue",
            primary_move=policy_decision.primary_move,
            ask_field=ask_field,
            prioritize_user_question=False,
            allow_contact_target=False,
            allow_medium_target=policy_decision.allow_medium_target,
            response_channel="model",
            tone_policy=tone_policy,
            in_repair_mode=False,
            repair_cooldown_remaining=0,
            followup_topic=resolved_followup_topic,
            context_ack_required=bool(resolved_followup_topic),
            context_ack_type=resolved_followup_topic,
            context_ack_payload=dict(context_ack_payload or {}),
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
        )

    def _should_force_model_expression(
        self,
        *,
        understanding: TurnUnderstandingResult,
        turn_decision: TurnDecision,
        user_message: str,
    ) -> bool:
        """复合业务场景不走 quick_faq 直返，统一切到模型表达链。"""
        if turn_decision.response_channel != "quick_faq":
            return False

        if (
            str(getattr(turn_decision, "priority_primary_task", "") or "").strip() == "user_question"
            and str(getattr(turn_decision, "priority_response_mode", "") or "").strip() in {"answer_only", "answer_then_resume"}
            and self._extract_priority_question_intent_from_understanding(understanding)
        ):
            return False

        primary_turn_type = understanding.primary_turn_type or ""
        subtype = understanding.subtype or ""
        secondary_signals = set(understanding.secondary_signals or [])
        resolved_slots = (
            self._get_meaningful_opening_resolved_slots(understanding)
            if primary_turn_type == "opening"
            else self._effective_resolved_slots(understanding)
        )
        message = str(user_message or "").strip()

        if primary_turn_type == "opening":
            pure_service_confirmation_opening = (
                subtype == "matchmaking_intent"
                and secondary_signals == {"opening_matchmaking_intent", "service_confirmation_like"}
                and not resolved_slots
            )
            if pure_service_confirmation_opening:
                return False
            if subtype in {
                "matchmaking_intent",
                "service_confirmation_opening",
                "low_pressure_opening",
                "opening_clarify",
            }:
                return True
            if len(secondary_signals) >= 2:
                return True
            if secondary_signals.intersection({"service_confirmation_like", "opening_matchmaking_intent"}):
                return True
            if resolved_slots:
                return True
            if message and any(token in message for token in ("介绍对象", "找对象", "男朋友", "女朋友", "脱单")):
                return True

        if primary_turn_type == "faq_concern" and subtype == "service_confirmation_mid":
            return True

        if primary_turn_type in {"contact_answer", "confirmation"} and (
            self._contains_contact_push_markers(message)
            or any(token in message for token in ("手机号", "电话", "微信", "联系方式"))
        ):
            return True

        if turn_decision.response_channel == "quick_faq" and not self._is_safe_quick_faq_expression(
            understanding=understanding,
            user_message=message,
        ):
            return True

        return False

    def _is_safe_quick_faq_expression(
        self,
        *,
        understanding: TurnUnderstandingResult,
        user_message: str,
    ) -> bool:
        """只有低歧义、非业务复合场景才允许 quick_faq 直返。"""
        primary_turn_type = understanding.primary_turn_type or ""
        subtype = understanding.subtype or ""
        secondary_signals = set(understanding.secondary_signals or [])
        resolved_slots = (
            self._get_meaningful_opening_resolved_slots(understanding)
            if primary_turn_type == "opening"
            else self._effective_resolved_slots(understanding)
        )
        message = str(user_message or "").strip()

        if resolved_slots:
            return False

        if primary_turn_type == "opening":
            return (
                subtype == "greeting"
                and secondary_signals.issubset({"opening_greeting"})
                and not any(token in message for token in ("找对象", "介绍对象", "男朋友", "女朋友", "脱单", "情况", "帮忙"))
            )

        if primary_turn_type == "faq_concern":
            return (
                subtype not in {"service_confirmation_mid", "contact_exchange", "contact_why"}
                and not secondary_signals
            )

        return False

    def _apply_general_turn_resolution(
        self,
        *,
        user_profile: UserProfile,
        message: str,
        last_response: str,
        message_count: int,
        understanding: TurnUnderstandingResult,
        policy_decision,
        contact_context: bool,
        intent: str,
        risk: str,
        primary_move: str,
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        resume_profile_collection: bool,
        post_answer_reentry: bool,
    ) -> tuple[object, Optional[str], Optional[str], str, bool, bool, bool, bool]:
        ask_field = policy_decision.main_target
        resume_target = policy_decision.resume_target or user_profile.resume_profile_target
        resume_mode = policy_decision.resume_mode or user_profile.resume_profile_mode
        next_action = "continue"
        resume_applied = False
        soft_retry_field = str(getattr(understanding, "soft_retry_field", "") or "").strip()

        if contact_context and intent == "general" and risk == "none" and not self.contact_service.is_contact_complete(user_profile):
            ask_field = "contact"

        if ask_field == "contact" and self.contact_service.is_contact_complete(user_profile):
            ask_field = resume_target or None
            if not ask_field or self.collection_policy.is_field_covered(user_profile, ask_field):
                unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
                unresolved_medium_fields = self.collection_policy.get_uncovered_medium_fields(user_profile)
                ask_field = (unresolved_core_fields or unresolved_medium_fields or [None])[0]
            allow_contact_target = False

        allow_contact_target = allow_contact_target and policy_decision.engagement_mode in {"full", "compact"}

        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            next_action = "confirm_divorce_status"
        elif intent == "complaint":
            next_action = "repair_and_release"

        if (
            prioritize_user_question
            and not contact_context
            and policy_decision.next_mode not in {"contact_flow", "terminate_conversion"}
        ):
            interrupted_followup_target = (
                self._resolve_interrupted_followup_field(
                    user_profile,
                    last_response=last_response,
                    fallback_user_message=message,
                )
                or policy_decision.resume_target
                or policy_decision.main_target
            )
            interrupted_followup_mode = policy_decision.resume_mode or policy_decision.next_mode or "collect_profile"
            if interrupted_followup_target:
                user_profile.set_resume_profile_target(
                    interrupted_followup_mode,
                    interrupted_followup_target,
                    policy_decision.user_concern_type or "faq",
                )
                resume_target = interrupted_followup_target
                resume_mode = interrupted_followup_mode
            ask_field = None

        if (
            prioritize_user_question
            and not contact_context
            and policy_decision.next_mode not in {"contact_flow", "terminate_conversion"}
            and policy_decision.main_target
            and not resume_target
        ):
            user_profile.set_resume_profile_target(
                policy_decision.resume_mode or policy_decision.next_mode,
                policy_decision.resume_target or policy_decision.main_target,
                policy_decision.user_concern_type or "faq",
            )
            resume_target = policy_decision.resume_target or policy_decision.main_target
            resume_mode = policy_decision.resume_mode or policy_decision.next_mode

        if (
            understanding.subtype == "soft_refusal_current_field"
            and soft_retry_field
            and soft_retry_field in ASK_GUARD_CORE_FIELDS
            and not self.collection_policy.is_collected(user_profile, soft_retry_field)
        ):
            ask_field = soft_retry_field
            allow_contact_target = False
            allow_medium_target = False
            user_profile.set_pending_retry_field(soft_retry_field)

        if (
            not prioritize_user_question
            and not contact_context
            and not self.collection_policy.has_ongoing_contact_flow(user_profile)
            and (
                (
                    user_profile.resume_profile_target
                    and not self.collection_policy.is_field_covered(user_profile, user_profile.resume_profile_target)
                )
                or (
                    post_answer_reentry
                    and not user_profile.resume_profile_target
                    and self._resolve_interrupted_followup_field(
                        user_profile,
                        last_response=last_response,
                        fallback_user_message=message,
                    )
                )
            )
        ):
            ask_field = user_profile.resume_profile_target or self._resolve_interrupted_followup_field(
                user_profile,
                last_response=last_response,
                fallback_user_message=message,
            )
            primary_move = "light_followup"
            allow_contact_target = False
            allow_medium_target = False
            resume_target = ask_field
            resume_mode = user_profile.resume_profile_mode
            resume_applied = True
            if user_profile.resume_profile_target:
                user_profile.clear_resume_profile_target()

        if not allow_contact_target and ask_field == "contact":
            policy_decision = self.collection_policy.decide(
                user_profile,
                user_message=message,
                message_count=message_count,
                allow_contact_target=False,
                allow_medium_target=allow_medium_target,
                prioritize_user_question=prioritize_user_question,
                primary_move=primary_move,
                resume_profile_collection=(resume_profile_collection or post_answer_reentry),
                understanding_result=understanding,
            )
            ask_field = policy_decision.main_target

        return (
            policy_decision,
            ask_field,
            resume_target,
            resume_mode,
            next_action,
            resume_applied,
            allow_contact_target,
            allow_medium_target,
        )

    @staticmethod
    def _should_keep_contact_context_faq_priority(intent: str, message: str) -> bool:
        if intent not in {"contact_exchange", "contact_why"}:
            return True
        direct_exchange_markers = ("直接加", "对方微信", "互加", "直接联系对方")
        return any(marker in message for marker in direct_exchange_markers)

    def _resolve_contact_context_intent(self, *, intent: str, message: str, contact_context: bool) -> str:
        if not contact_context:
            return intent
        if self._should_keep_contact_context_faq_priority(intent, message):
            return intent
        return "general"

    def _derive_general_turn_defaults(
        self,
        *,
        message: str,
        user_profile: UserProfile,
        understanding: TurnUnderstandingResult,
        contact_context: bool,
    ) -> tuple[str, str, bool, str | None]:
        priority_question_intent = self._extract_priority_question_intent_from_understanding(understanding)

        intent = priority_question_intent or "general"
        if priority_question_intent:
            intent = understanding.subtype or priority_question_intent or "faq"
        elif understanding.primary_turn_type == "confirmation":
            unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
            interrupted_followup_target = None
            if understanding.post_answer_reentry and not contact_context:
                interrupted_followup_target = self._resolve_interrupted_followup_field(
                    user_profile,
                    fallback_user_message=message,
                )
            if (
                not contact_context
                and (
                    user_profile.resume_profile_target
                    or interrupted_followup_target
                    or user_profile.pending_sex_confirmation
                    or bool(unresolved_core_fields)
                )
            ):
                intent = "general"
            else:
                intent = "confirmation"

        intent = self._resolve_contact_context_intent(
            intent=intent,
            message=message,
            contact_context=contact_context,
        )
        prioritize_user_question = intent != "general"
        user_concern_type = None if intent == "general" else self._normalize_user_concern_type(intent)
        return intent, "quick_faq" if prioritize_user_question else "model", prioritize_user_question, user_concern_type

    def _apply_priority_policy_overrides(
        self,
        *,
        understanding: TurnUnderstandingResult,
        message: str,
        contact_context: bool,
        intent: str,
        response_channel: str,
        primary_move: str,
        ask_field: Optional[str],
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        user_concern_type: Optional[str],
    ) -> tuple[str, str, str, Optional[str], bool, bool, bool, Optional[str]]:
        priority = self._get_priority_decision(understanding)
        if priority is None:
            return (
                intent,
                response_channel,
                primary_move,
                ask_field,
                prioritize_user_question,
                allow_contact_target,
                allow_medium_target,
                user_concern_type,
            )

        primary_task = str(getattr(priority, "primary_task", "") or "").strip()
        question_intent = str(getattr(priority, "prioritized_question_intent", "") or "").strip()
        locked_field = str(getattr(priority, "locked_field", "") or "").strip() or None

        if primary_task == "user_question":
            if (
                contact_context
                and question_intent in {"contact_why", "contact_exchange"}
                and not self._should_keep_contact_context_faq_priority(question_intent, message)
            ):
                return (
                    "general",
                    "model",
                    primary_move,
                    ask_field,
                    False,
                    allow_contact_target,
                    allow_medium_target,
                    None,
                )
            prioritize_user_question = True
            allow_contact_target = False
            allow_medium_target = False
            if question_intent:
                intent = question_intent
                user_concern_type = self._normalize_user_concern_type(question_intent)
            response_channel = "quick_faq"
            return (
                intent,
                response_channel,
                primary_move,
                ask_field,
                prioritize_user_question,
                allow_contact_target,
                allow_medium_target,
                user_concern_type,
            )

        if primary_task == "status_confirmation":
            return (
                "confirmation",
                "model",
                "confirm_status_only",
                locked_field,
                False,
                False,
                False,
                None,
            )

        if primary_task == "contact_record":
            return (
                intent,
                response_channel,
                primary_move,
                ask_field,
                prioritize_user_question,
                False,
                False,
                user_concern_type,
            )

        if primary_task == "core_profile_collection":
            allow_contact_target = False

        return (
            intent,
            response_channel,
            primary_move,
            ask_field,
            prioritize_user_question,
            allow_contact_target,
            allow_medium_target,
            user_concern_type,
        )

    def _derive_raw_turn_intent(
        self,
        *,
        message: str,
        understanding: TurnUnderstandingResult,
    ) -> str:
        priority_question_intent = self._extract_priority_question_intent_from_understanding(understanding)

        raw_intent = priority_question_intent or "general"
        if priority_question_intent:
            return understanding.subtype or priority_question_intent or "faq"
        if understanding.primary_turn_type == "confirmation":
            return "confirmation"
        return raw_intent

    def _apply_turn_state_overrides(
        self,
        *,
        message: str,
        user_profile: UserProfile,
        understanding: TurnUnderstandingResult,
        complaint_reason: Optional[str],
        primary_move: str,
        user_concern_type: Optional[str],
        allow_contact_target: bool,
        allow_medium_target: bool,
    ) -> tuple[str, Optional[str], bool, bool, str, bool]:
        risk = "none"
        in_repair_mode = user_profile.repair_mode and user_profile.ask_cooldown_turns > 0

        if complaint_reason:
            if not in_repair_mode:
                user_profile.enter_repair_mode(
                    reason=complaint_reason,
                    cooldown_turns=3,
                )
                in_repair_mode = True
                logger.info(f"[repair_mode] 用户投诉触发，进入修复模式，原因: {complaint_reason}")
            primary_move = "repair_and_release"
            user_concern_type = "complaint"
            allow_contact_target = False
            allow_medium_target = False
        elif understanding.primary_turn_type == "risk_guard":
            risk = "high_risk"
            primary_move = "answer_then_pause"
            allow_contact_target = False
        elif (
            understanding.primary_turn_type == "refusal_boundary_complaint"
            and understanding.subtype != "soft_refusal_current_field"
            and not self._should_keep_contact_refusal_in_contact_flow(message, user_profile)
        ):
            risk = "boundary"
            primary_move = "soft_hold"
            allow_contact_target = False
        elif in_repair_mode and user_profile.is_ask_intent_blocked("ask_basic_profile"):
            primary_move = "ack_only"
            allow_contact_target = False
            allow_medium_target = False
            logger.info(f"[repair_mode] 冷却期内，禁止追问，剩余冷却轮数: {user_profile.ask_cooldown_turns}")

        return (
            risk,
            user_concern_type,
            allow_contact_target,
            allow_medium_target,
            primary_move,
            in_repair_mode,
        )

    def _prepare_policy_decision(
        self,
        *,
        user_profile: UserProfile,
        message: str,
        message_count: int,
        understanding: TurnUnderstandingResult,
        contact_context: bool,
        contact_context_faq_downgraded: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        prioritize_user_question: bool,
        primary_move: str,
        resume_profile_collection: bool,
        post_answer_reentry: bool,
    ):
        allow_medium_target = not self.collection_policy.should_block_medium_fields_for_turn(
            user_profile,
            user_message=message,
            allow_contact_target=allow_contact_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            resume_profile_collection=(resume_profile_collection or post_answer_reentry),
        )
        if contact_context:
            allow_medium_target = False

        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=message,
            message_count=message_count,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            resume_profile_collection=(resume_profile_collection or post_answer_reentry),
            understanding_result=None if contact_context_faq_downgraded else understanding,
        )
        return allow_medium_target, policy_decision

    async def _analyze_turn_understanding(
        self,
        *,
        message: str,
        user_profile: UserProfile,
        last_response: str = "",
        message_count: int = 0,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> TurnUnderstandingResult:
        context = dict(conversation_context or {})
        if last_response and not context.get("recent_responses"):
            context["recent_responses"] = [last_response]
        return await self.unified_turn_understanding_service.analyze(
            TurnUnderstandingInput(
                user_message=message,
                last_response=last_response,
                message_count=message_count,
                user_profile=user_profile,
                conversation_context=context,
                in_contact_flow=self._has_active_contact_context(user_profile, user_message=message),
            )
        )

    @staticmethod
    def _build_general_turn_decision(
        *,
        intent: str,
        risk: str,
        stage: str,
        next_action: str,
        primary_move: str,
        ask_field: Optional[str],
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        response_channel: str,
        in_repair_mode: bool,
        repair_cooldown_remaining: int,
        user_concern_type: Optional[str],
        resume_mode: Optional[str],
        resume_target: Optional[str],
        resume_applied: bool,
        followup_topic: Optional[str],
        context_ack_payload: Dict[str, Any],
        context_ack_occupation: Optional[str],
        context_ack_location: Optional[str],
        context_ack_preference: Optional[str],
        context_ack_field_ack: Optional[str],
        soft_retry_field: Optional[str],
        priority_primary_task: Optional[str] = None,
        priority_level: int = 0,
        priority_reason: Optional[str] = None,
        priority_response_mode: Optional[str] = None,
        priority_suppressed_tasks: Optional[list[str]] = None,
    ) -> TurnDecision:
        tone_policy = {
            "ack_budget_per_n_turns": 3,
            "max_core_question_per_turn": 1,
            "allow_related_medium_side_target": True,
            "enforce_contact_transition": True,
            "core_streak_max": 3,
        }
        return TurnDecision(
            intent=intent,
            risk=risk,
            stage=stage,
            next_action=next_action,
            primary_move=primary_move,
            ask_field=ask_field,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            response_channel=response_channel,
            tone_policy=tone_policy,
            in_repair_mode=in_repair_mode,
            repair_cooldown_remaining=repair_cooldown_remaining,
            user_concern_type=user_concern_type,
            resume_mode=resume_mode,
            resume_target=resume_target,
            resume_applied=resume_applied,
            followup_topic=followup_topic,
            context_ack_required=bool(followup_topic),
            context_ack_type=followup_topic,
            context_ack_payload=context_ack_payload,
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
            priority_primary_task=priority_primary_task,
            priority_level=priority_level,
            priority_reason=priority_reason,
            priority_response_mode=priority_response_mode,
            priority_suppressed_tasks=list(priority_suppressed_tasks or []),
        )

    def _apply_resume_after_faq_override(
        self,
        *,
        user_profile: UserProfile,
        message: str,
        last_response: str,
        contact_context: bool,
        post_answer_reentry: bool,
        intent: str,
        primary_move: str,
        ask_field: Optional[str],
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        response_channel: str,
        user_concern_type: Optional[str],
        resume_target: Optional[str],
        resume_applied: bool,
    ) -> tuple[str, str, Optional[str], bool, bool, bool, str, Optional[str], Optional[str], bool]:
        if contact_context or not post_answer_reentry or self.collection_policy.has_ongoing_contact_flow(user_profile):
            return (
                intent,
                primary_move,
                ask_field,
                prioritize_user_question,
                allow_contact_target,
                allow_medium_target,
                response_channel,
                user_concern_type,
                resume_target,
                resume_applied,
            )

        if ask_field and ask_field != "contact" and primary_move == "light_followup" and not prioritize_user_question:
            return (
                intent,
                primary_move,
                ask_field,
                prioritize_user_question,
                allow_contact_target,
                allow_medium_target,
                response_channel,
                user_concern_type,
                resume_target,
                resume_applied,
            )

        plan = self.unified_turn_understanding_service.followup_planning_layer.resolve_resume_after_faq(
            understanding=TurnUnderstandingResult(primary_turn_type="confirmation", post_answer_reentry=post_answer_reentry),
            turn_decision=TurnDecision(
                intent=intent,
                primary_move=primary_move,
                ask_field=ask_field,
                prioritize_user_question=prioritize_user_question,
                allow_contact_target=allow_contact_target,
                allow_medium_target=allow_medium_target,
                response_channel=response_channel,
            ),
            user_profile=user_profile,
            decision_profile=None,
            user_message=message,
            last_response=last_response,
            resolve_interrupted_followup_field=self._resolve_interrupted_followup_field,
            is_field_covered=self.collection_policy.is_field_covered,
        )
        if not plan.field:
            return (
                intent,
                primary_move,
                ask_field,
                prioritize_user_question,
                allow_contact_target,
                allow_medium_target,
                response_channel,
                user_concern_type,
                resume_target,
                resume_applied,
            )

        interrupted_followup_field = plan.field
        if user_profile.resume_profile_target == interrupted_followup_field:
            user_profile.clear_resume_profile_target()

        logger.info(
            "[resume_after_faq_override] ask_field=%s source=%s",
            interrupted_followup_field,
            plan.source or ("resume_profile_target" if resume_target == interrupted_followup_field else "interrupted_followup_field"),
        )
        return (
            "general",
            "light_followup",
            interrupted_followup_field,
            False,
            False,
            False,
            "model",
            None,
            interrupted_followup_field,
            True,
        )

    @staticmethod
    def _apply_policy_turn_overrides(
        *,
        policy_decision,
        primary_move: str,
        prioritize_user_question: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        user_concern_type: Optional[str],
    ) -> tuple[str, bool, bool, bool, Optional[str]]:
        primary_move = policy_decision.primary_move
        prioritize_user_question = policy_decision.prioritize_user_question
        allow_contact_target = policy_decision.allow_contact_target
        allow_medium_target = policy_decision.allow_medium_target
        if policy_decision.user_concern_type is not None:
            user_concern_type = policy_decision.user_concern_type
        return (
            primary_move,
            prioritize_user_question,
            allow_contact_target,
            allow_medium_target,
            user_concern_type,
        )

    def _build_turn_decision(
        self,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any] | None = None,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> TurnDecision | asyncio.Future:
        """
        兼容同步/异步两种旧调用方式。

        回归测试和少量遗留入口仍直接同步调用这个方法；新流程则在异步上下文里
        `await` 它。这里统一路由到异步实现，避免把 coroutine 直接泄漏给同步调用方。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self._build_turn_decision_async(
                    user_message=user_message,
                    user_profile=user_profile,
                    conversation_context=conversation_context,
                    understanding_result=understanding_result,
                )
            )

        return self._build_turn_decision_async(
            user_message=user_message,
            user_profile=user_profile,
            conversation_context=conversation_context,
            understanding_result=understanding_result,
        )

    async def _build_turn_decision_async(
        self,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any] | None = None,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> TurnDecision:
        """
        单轮统一决策器（结构化输出，供主流程/兜底/快答共用）。
        """
        context = conversation_context or {}
        message_count = int(context.get("message_count", 0))
        stage = self.dialogue_manager.detect_conversation_stage(user_profile, message_count)
        message = (user_message or "").strip()
        recent_responses = context.get("recent_responses") or []
        last_response = str(recent_responses[-1]).strip() if recent_responses else ""
        understanding = understanding_result or await self._analyze_turn_understanding(
            message=message,
            user_profile=user_profile,
            last_response=last_response,
            message_count=message_count,
            conversation_context=context,
        )
        followup_topic = str(understanding.context_ack_type or "").strip() or None
        context_ack_payload = dict(understanding.context_ack_payload or {})
        context_ack_occupation = getattr(understanding, "context_ack_occupation", None)
        context_ack_location = getattr(understanding, "context_ack_location", None)
        context_ack_preference = getattr(understanding, "context_ack_preference", None)
        context_ack_field_ack = getattr(understanding, "context_ack_field_ack", None)
        soft_retry_field = getattr(understanding, "soft_retry_field", None)
        risk = "none"
        contact_context = self._has_active_contact_context(
            user_profile,
            user_message=message,
            understanding_result=understanding,
        )
        withdraw_intent = self._classify_withdraw_intent(message)

        if understanding:
            pre_generation_transition_reason = str(
                getattr(getattr(understanding, "pre_generation_resolution", None), "transition_reason", "") or ""
            ).strip()
            if (
                understanding.primary_turn_type == "refusal_boundary_complaint"
                and (understanding.subtype or "") == "contact_refusal"
                and not self._should_keep_contact_refusal_in_contact_flow(
                    message,
                    user_profile,
                    understanding=understanding,
                )
            ):
                return self._build_quick_turn_decision(
                    intent="boundary",
                    risk="boundary",
                    stage=stage,
                    primary_move="ack_and_hold",
                    prioritize_user_question=False,
                    allow_contact_target=False,
                    allow_medium_target=False,
                    followup_topic=followup_topic,
                    context_ack_type=understanding.context_ack_type,
                    context_ack_payload=context_ack_payload,
                    context_ack_occupation=context_ack_occupation,
                    context_ack_location=context_ack_location,
                    context_ack_preference=context_ack_preference,
                    context_ack_field_ack=context_ack_field_ack,
                    soft_retry_field=soft_retry_field,
                    **self._priority_kwargs_from_understanding(understanding),
                )
            status_priority_decision = None
            if pre_generation_transition_reason != "resume_after_divorce_confirmation_complete":
                status_priority_decision = self._build_status_priority_turn_decision(
                    understanding=understanding,
                    stage=stage,
                    followup_topic=followup_topic,
                    context_ack_payload=context_ack_payload,
                )
            if status_priority_decision is not None:
                return status_priority_decision
            quick_decision = self._build_understanding_quick_decision(
                understanding=understanding,
                user_profile=user_profile,
                user_message=message,
                stage=stage,
                followup_topic=followup_topic,
                context_ack_payload=context_ack_payload,
            )
            if (
                quick_decision is not None
                and understanding.primary_turn_type == "faq_concern"
                and understanding.subtype == "clarification"
                and self._looks_like_contact_clarification_in_context(
                    message,
                    user_profile,
                    understanding_result=understanding,
                )
            ):
                quick_decision = None
            if (
                quick_decision is not None
                and self._should_keep_contact_refusal_in_contact_flow(
                    message,
                    user_profile,
                    understanding=understanding,
                )
            ):
                quick_decision = None
            if quick_decision is not None:
                return quick_decision

        if withdraw_intent and understanding.primary_turn_type != "risk_guard":
            return self._build_quick_turn_decision(
                intent="withdraw_or_stop",
                risk="withdraw",
                stage=stage,
                primary_move="soft_hold",
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                **self._priority_kwargs_from_understanding(understanding),
            )

        # 联系方式上下文里，仅联系方式推进相关 FAQ 降级回主线；
        # timeline 这类仍保持答疑优先。
        raw_intent = self._derive_raw_turn_intent(message=message, understanding=understanding)
        intent, response_channel, prioritize_user_question, user_concern_type = self._derive_general_turn_defaults(
            message=message,
            user_profile=user_profile,
            understanding=understanding,
            contact_context=contact_context,
        )
        contact_context_faq_downgraded = intent != raw_intent
        primary_move = "ack_and_ask"
        resume_profile_collection = bool(understanding.resume_profile_collection)
        post_answer_reentry = bool(understanding.post_answer_reentry)
        allow_contact_target = True
        allow_medium_target = True
        complaint_reason = understanding.complaint_reason
        resume_target = None
        resume_mode = None
        resume_applied = False
        ask_field = None

        (
            risk,
            user_concern_type,
            allow_contact_target,
            allow_medium_target,
            primary_move,
            in_repair_mode,
        ) = self._apply_turn_state_overrides(
            message=message,
            user_profile=user_profile,
            understanding=understanding,
            complaint_reason=complaint_reason,
            primary_move=primary_move,
            user_concern_type=user_concern_type,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
        )
        if complaint_reason:
            intent = "complaint"

        (
            intent,
            response_channel,
            primary_move,
            ask_field,
            prioritize_user_question,
            allow_contact_target,
            allow_medium_target,
            user_concern_type,
        ) = self._apply_priority_policy_overrides(
            understanding=understanding,
            message=message,
            contact_context=contact_context,
            intent=intent,
            response_channel=response_channel,
            primary_move=primary_move,
            ask_field=ask_field,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            user_concern_type=user_concern_type,
        )

        allow_medium_target, policy_decision = self._prepare_policy_decision(
            user_profile=user_profile,
            message=message,
            message_count=message_count,
            understanding=understanding,
            contact_context=contact_context,
            contact_context_faq_downgraded=contact_context_faq_downgraded,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            prioritize_user_question=prioritize_user_question,
            primary_move=primary_move,
            resume_profile_collection=resume_profile_collection,
            post_answer_reentry=post_answer_reentry,
        )
        (
            primary_move,
            prioritize_user_question,
            allow_contact_target,
            allow_medium_target,
            user_concern_type,
        ) = self._apply_policy_turn_overrides(
            policy_decision=policy_decision,
            primary_move=primary_move,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            user_concern_type=user_concern_type,
        )
        (
            policy_decision,
            ask_field,
            resume_target,
            resume_mode,
            next_action,
            resume_applied,
            allow_contact_target,
            allow_medium_target,
        ) = self._apply_general_turn_resolution(
            user_profile=user_profile,
            message=message,
            last_response=last_response,
            message_count=message_count,
            understanding=understanding,
            policy_decision=policy_decision,
            contact_context=contact_context,
            intent=intent,
            risk=risk,
            primary_move=primary_move,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            resume_profile_collection=resume_profile_collection,
            post_answer_reentry=post_answer_reentry,
        )
        (
            intent,
            primary_move,
            ask_field,
            prioritize_user_question,
            allow_contact_target,
            allow_medium_target,
            response_channel,
            user_concern_type,
            resume_target,
            resume_applied,
        ) = self._apply_resume_after_faq_override(
            user_profile=user_profile,
            message=message,
            last_response=last_response,
            contact_context=contact_context,
            post_answer_reentry=post_answer_reentry,
            intent=intent,
            primary_move=primary_move,
            ask_field=ask_field,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            response_channel=response_channel,
            user_concern_type=user_concern_type,
            resume_target=resume_target,
            resume_applied=resume_applied,
        )

        return self._build_general_turn_decision(
            intent=intent,
            risk=risk,
            stage=stage,
            next_action=next_action,
            primary_move=primary_move,
            ask_field=ask_field,
            prioritize_user_question=prioritize_user_question,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            response_channel=response_channel,
            in_repair_mode=in_repair_mode,
            repair_cooldown_remaining=user_profile.ask_cooldown_turns,
            user_concern_type=user_concern_type,
            resume_mode=resume_mode,
            resume_target=resume_target,
            resume_applied=resume_applied,
            followup_topic=followup_topic,
            context_ack_payload=context_ack_payload,
            context_ack_occupation=context_ack_occupation,
            context_ack_location=context_ack_location,
            context_ack_preference=context_ack_preference,
            context_ack_field_ack=context_ack_field_ack,
            soft_retry_field=soft_retry_field,
            **self._priority_kwargs_from_understanding(understanding),
        )

    # Phase orchestration entrypoints: pre-generation preparation.
    async def prepare_turn_execution(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any],
        last_response: str,
        message_count: int,
    ) -> TurnExecutionPreparation:
        return await self.preparation_service.prepare_turn_execution(
            user_message=user_message,
            user_profile=user_profile,
            conversation_context=conversation_context,
            last_response=last_response,
            message_count=message_count,
        )

    async def consume_bridge_back_prefix(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        in_repair_mode: bool,
    ) -> str:
        return await self.preparation_service.consume_bridge_back_prefix(
            account_id=account_id,
            user_profile=user_profile,
            in_repair_mode=in_repair_mode,
        )

    async def _update_progress_runtime_counters(
        self,
        account_id: str,
        user_profile: UserProfile,
        *,
        user_message: str,
        collection_result: Dict[str, Any],
        turn_decision: TurnDecision,
        message_count: int = 0,
        previous_asked_field: Optional[str] = None,
        previous_asked_side_field: Optional[str] = None,
    ) -> UserProfile:
        """更新不配合/跑题/开放式补画像等运行态计数。"""
        extracted_fields = collection_result.get("all_fields", []) if isinstance(collection_result, dict) else []
        extracted_field_names = {
            str(item.get("field") or "").strip()
            for item in extracted_fields
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        }
        effective_progress_fields = extracted_field_names & {
            "sex",
            "age",
            "education",
            "occupation",
            "location",
            "marital_status",
            "partner_requirement",
            "monthly_income",
            "phone",
            "wechat",
            "contact",
        }
        extracted_any = bool(effective_progress_fields)
        message = str(user_message or "").strip()
        normalized = re.sub(r"[，。！？!?~～、\s]+", "", message)
        deflective_messages = {"嗯", "哦", "哈哈", "呵呵", "还行", "一般", "再说吧", "行", "好的", "知道了"}
        made_effective_progress = extracted_any or bool(turn_decision.resume_applied)

        if previous_asked_field:
            if previous_asked_field in extracted_field_names:
                user_profile.clear_field_miss_streak(previous_asked_field)
            elif extracted_any and not turn_decision.prioritize_user_question:
                miss_streak = user_profile.mark_field_miss(previous_asked_field)
                if miss_streak == 1:
                    rolled_back = user_profile.decrement_ask_count(previous_asked_field)
                    logger.info(
                        "[字段覆盖] 字段 %s 首次错位回答，回退 ask_count，current=%s",
                        previous_asked_field,
                        rolled_back,
                    )

        if previous_asked_side_field:
            if previous_asked_side_field in extracted_field_names:
                if str(getattr(user_profile, "pending_retry_field", "") or "").strip() == previous_asked_side_field:
                    user_profile.clear_pending_retry_field()
            elif (
                previous_asked_field
                and previous_asked_field in extracted_field_names
                and not turn_decision.prioritize_user_question
                and self.collection_policy.can_actively_ask(user_profile, previous_asked_side_field)
                and not self.collection_policy.is_collected(user_profile, previous_asked_side_field)
            ):
                user_profile.set_pending_retry_field(previous_asked_side_field)
                logger.info(
                    "[side_target_pending] 主字段 %s 已回答，顺带字段 %s 未回答，设置 pending_retry_field",
                    previous_asked_field,
                    previous_asked_side_field,
                )

        if made_effective_progress:
            user_profile.reset_non_cooperation()
            user_profile.reset_off_topic()
            user_profile.reset_open_profile_attempts()
        else:
            if turn_decision.prioritize_user_question or turn_decision.response_channel == "quick_faq":
                user_profile.mark_off_topic()
            elif normalized in deflective_messages or len(normalized) <= 4:
                user_profile.mark_non_cooperation()
            else:
                user_profile.reset_non_cooperation()

        post_decision = self.collection_policy.decide(
            user_profile,
            user_message=message,
            message_count=message_count,
            allow_contact_target=turn_decision.allow_contact_target,
            allow_medium_target=turn_decision.allow_medium_target,
            prioritize_user_question=turn_decision.prioritize_user_question,
            primary_move=turn_decision.primary_move,
        )
        if post_decision.next_mode == "open_profile_repair":
            user_profile.mark_open_profile_attempt()
        elif extracted_any or post_decision.next_mode != "open_profile_repair":
            user_profile.reset_open_profile_attempts()

        user_profile.last_effective_progress = made_effective_progress
        user_profile.last_engagement_mode = post_decision.engagement_mode
        await self.user_service.save_user_profile(account_id, user_profile)
        logger.debug(
            "[progress_runtime] made_effective_progress=%s extracted_fields=%s previous_asked_field=%s",
            made_effective_progress,
            sorted(effective_progress_fields),
            previous_asked_field or "-",
        )
        return user_profile

    @staticmethod
    def _normalize_user_concern_type(intent: str) -> str:
        intent_value = str(intent or "").strip().lower()
        if intent_value in {"reliable", "privacy"}:
            return intent_value
        if intent_value in {"clarification", "service_area", "timeline", "photo", "success_rate", "mediator"}:
            return "faq"
        return "faq"

    def _extract_priority_question_intent_from_understanding(
        self,
        understanding_result: TurnUnderstandingResult | None,
    ) -> str | None:
        def _normalize_quick_faq_topic(topic: str) -> str:
            topic_value = str(topic or "").strip()
            topic_map = {
                "safety": "reliable",
                "contact_policy": "contact_why",
                "service_flow": "how_match",
                "pricing": "fee",
            }
            return topic_map.get(topic_value, topic_value)

        if understanding_result is None:
            return None

        semantic_frame = getattr(understanding_result, "semantic_frame", None)
        if semantic_frame is not None:
            user_questions = list(getattr(semantic_frame, "user_questions", []) or [])
            if user_questions:
                topic = _normalize_quick_faq_topic(str(getattr(user_questions[0], "topic", "") or "").strip())
                if topic:
                    return topic

        intent = str(getattr(understanding_result, "subtype", "") or "").strip()
        if not intent:
            return None

        if getattr(understanding_result, "primary_turn_type", "") == "faq_concern":
            return intent or "faq"

        if not getattr(understanding_result, "answer_first", False):
            return None

        recognized_intents = {"timeline", "faq"}
        faq_rules = getattr(self.user_question_service, "FAQ_RESPONSE_RULES", ())
        for intent_id, _, _ in faq_rules:
            recognized_intents.add(str(intent_id))

        if intent in recognized_intents:
            return intent
        return None

    def _has_faq_priority_signal(
        self,
        user_message: str,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> bool:
        """统一 FAQ/顾虑优先信号，避免 complaint/withdraw/opening guard 各自分叉判定。"""
        if self._extract_priority_question_intent_from_understanding(understanding_result):
            return True
        return bool(self.turn_understanding_service._detect_faq_intent(user_message))  # noqa: SLF001

    def _get_priority_question_response(
        self,
        user_message: str,
        user_profile: UserProfile,
        *,
        repeat_count: int = 1,
        recent_responses: tuple[str, ...] | list[str] | None = None,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> str | None:
        intent = self._extract_priority_question_intent_from_understanding(understanding_result)
        if intent is None:
            intent = self.turn_understanding_service._detect_faq_intent(user_message)  # noqa: SLF001
        if not intent:
            return None
        if intent == "timeline":
            return self.expectation_service.get_matching_timeline_response(user_profile)
        return self.user_question_service.get_quick_faq_response_by_intent(
            intent,
            repeat_count=repeat_count,
            recent_responses=recent_responses,
        )

    @staticmethod
    def _is_explicit_matchmaking_intent_message(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        return bool(
            re.search(
                r"((?:想)?找(?:个)?(?:对象|另一半|男朋友|女朋友)|(?:帮(?:我|忙)?|给我)?(?:找|介绍|介绍下|牵线|安排)(?:个)?(?:对象|另一半|男朋友|女朋友)|介绍(?:个)?(?:对象|另一半|男朋友|女朋友)|相亲|脱单|认真聊聊)",
                message,
            )
        )

    def _opening_message_has_substantive_profile_content(
        self,
        user_message: str,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> bool:
        """开场轮里如果用户已经提供了画像/偏好信息，就不该再被打回开放自述模板。"""
        semantic_frame = getattr(understanding_result, "semantic_frame", None) if understanding_result is not None else None
        if semantic_frame is not None:
            for observation in list(getattr(semantic_frame, "field_observations", []) or []):
                field = str(getattr(observation, "field", "") or "").strip()
                scope = str(getattr(observation, "scope", "") or "").strip()
                value = str(getattr(observation, "normalized_value", "") or getattr(observation, "value", "") or "").strip()
                if scope not in {"self", "partner", "contact"}:
                    continue
                if field in {
                    "location",
                    "age",
                    "age_label",
                    "education",
                    "occupation",
                    "marital_status",
                    "monthly_income",
                    "partner_requirement",
                    "height",
                    "weight",
                } and value:
                    if field == "partner_requirement" and value in {"找对象", "想找对象", "找个对象", "找另一半", "想找另一半"}:
                        continue
                    if field == "location" and re.search(r"(在吗|你好|您好)", value):
                        continue
                    return True

        message = str(user_message or "").strip()
        if not message:
            return False
        if (
            understanding_result is not None
            and getattr(understanding_result, "primary_turn_type", "") == "opening"
            and getattr(understanding_result, "subtype", "") == "matchmaking_intent"
            and not self._extract_turn_level_fields(message)
            and self._is_explicit_matchmaking_intent_message(message)
        ):
            return False

        extracted = self._extract_turn_level_fields(message)
        canonical = self._canonicalize_extracted_fields(extracted)
        substantive_fields = {
            "location",
            "age",
            "age_label",
            "education",
            "occupation",
            "marital_status",
            "monthly_income",
            "partner_requirement",
            "height",
            "weight",
        }
        for field in substantive_fields & set(canonical.keys()):
            value = str(canonical.get(field) or "").strip()
            if not value:
                continue
            if field == "location" and re.search(r"(在吗|你好|您好)", value):
                continue
            return True

        preference = self.turn_understanding_service._extract_simple_partner_requirement(message)  # noqa: SLF001
        if preference:
            return True

        return False

    def _get_meaningful_opening_resolved_slots(
        self,
        understanding: Optional[TurnUnderstandingResult],
    ) -> Dict[str, Any]:
        """过滤 opening 轮里被重复招呼/噪声误抽出的伪资料字段。"""
        persistence_plan = getattr(understanding, "persistence_plan", None) if understanding is not None else None
        if persistence_plan is not None and getattr(persistence_plan, "accepted_fields", None):
            high_risk_fields = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
            accepted = {
                field.field: field.normalized_value
                for field in list(getattr(persistence_plan, "accepted_fields", []) or [])
                if str(getattr(field, "scope", "") or "").strip() in {"self", "partner", "contact"}
                and str(getattr(field, "persistence_state", "committed") or "committed").strip() == "committed"
                and (
                    str(getattr(field, "field", "") or "").strip() not in high_risk_fields
                    or str(getattr(field, "source_channel", "unknown") or "unknown").strip() == "ai"
                )
            }
            generic_partner_requirement = str(accepted.get("partner_requirement") or "").strip()
            if generic_partner_requirement in {"找对象", "想找对象", "找个对象", "找另一半", "想找另一半"}:
                accepted.pop("partner_requirement", None)
            if accepted:
                return accepted

        resolved_slots = self._effective_resolved_slots(understanding)
        if not resolved_slots:
            return {}

        filtered: Dict[str, Any] = {}
        for field, raw_value in resolved_slots.items():
            value = str(raw_value or "").strip()
            if not value:
                continue
            if field == "partner_requirement" and value in {"找对象", "想找对象", "找个对象", "找另一半", "想找另一半"}:
                continue
            if field == "location":
                normalized = re.sub(r"[呀啊吗呢哈哦～~？，,。.!！?？\s]+", "", value)
                if not normalized:
                    continue
                if re.fullmatch(r"[你您好吗在不呀啊哈喽嗨]+", normalized):
                    continue
            filtered[field] = raw_value
        return filtered

    @staticmethod
    def _is_opening_probe_followup_message(user_message: str, last_response: str = "") -> bool:
        message = str(user_message or "").strip()
        previous = str(last_response or "").strip()
        if not message or not previous:
            return False
        probe_markers = (
            "想找对象",
            "先了解下",
            "先问问情况",
            "先看看情况",
            "认真聊聊",
            "简单介绍下自己",
            "简单说说自己",
            "讲讲自己的情况",
            "顺着了解",
        )
        return any(marker in previous for marker in probe_markers)

    @staticmethod
    def _pick_seeded_variant(key: str, candidates: tuple[str, ...], seed_hint: str) -> str:
        if not candidates:
            return ""
        digest = hashlib.sha1(f"{key}:{seed_hint}".encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(candidates)
        return candidates[idx]

    @staticmethod
    def _get_turn_decision_ack_value(turn_decision: TurnDecision, field: str) -> str:
        method_name = {
            "occupation": "get_context_ack_occupation",
            "location": "get_context_ack_location",
            "preference": "get_context_ack_preference",
            "field_ack": "get_context_ack_field_ack",
            "soft_retry_field": "get_soft_retry_field",
        }.get(field, "")
        method = getattr(turn_decision, method_name, None)
        if callable(method):
            return str(method() or "").strip()

        attr_name = {
            "occupation": "context_ack_occupation",
            "location": "context_ack_location",
            "preference": "context_ack_preference",
            "field_ack": "context_ack_field_ack",
            "soft_retry_field": "soft_retry_field",
        }.get(field, "")
        attr_value = getattr(turn_decision, attr_name, None)
        if attr_value:
            return str(attr_value).strip()

        payload = dict(getattr(turn_decision, "context_ack_payload", {}) or {})
        legacy_key = {
            "occupation": "occupation",
            "location": "location",
            "preference": "preference",
            "field_ack": "field_ack",
            "soft_retry_field": "field",
        }.get(field, "")
        return str(payload.get(legacy_key) or "").strip()

    def _render_context_ack(
        self,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        user_message: str,
    ) -> str:
        ack_type = str(turn_decision.context_ack_type or "").strip()
        if not ack_type:
            return ""

        seed_hint = f"{ack_type}:{user_message}:{user_profile.account_id}:{user_profile.updated_at.isoformat()}"

        if ack_type == "work_busy":
            occupation = str(self._get_turn_decision_ack_value(turn_decision, "occupation") or user_profile.occupation or "").strip()
            if occupation:
                variants = tuple(
                    v.format(
                        occupation=ChatServiceAckRenderService.render_occupation_for_ack(occupation)
                    )
                    for v in WORK_BUSY_OCCUPATION_ACK_VARIANTS
                )
                return self._pick_seeded_variant("context:work_busy_occ", variants, seed_hint)
            return self._pick_seeded_variant("context:work_busy", WORK_BUSY_ACK_VARIANTS, seed_hint)

        if ack_type == "location_reuse":
            location = str(self._get_turn_decision_ack_value(turn_decision, "location") or user_profile.location or "").strip()
            if not location:
                return ""
            variants = tuple(v.format(location=location) for v in LOCATION_REUSE_ACK_VARIANTS)
            return self._pick_seeded_variant("context:location_reuse", variants, seed_hint)

        if ack_type == "preference_reuse":
            gender_preference = str(getattr(user_profile, "partner_gender_preference", "") or "").strip()
            normalized_gender = "男生" if gender_preference == "男" else ("女生" if gender_preference == "女" else "")
            preference = str(
                self._get_turn_decision_ack_value(turn_decision, "preference")
                or normalized_gender
                or ChatServiceAckRenderService.render_preference_for_ack(
                    str(user_profile.partner_requirement or "").strip()
                )
            ).strip()
            if not preference:
                return ""
            variants = tuple(v.format(preference=preference) for v in PREFERENCE_REUSE_ACK_VARIANTS)
            return self._pick_seeded_variant("context:preference_reuse", variants, seed_hint)

        if ack_type == "boundary_pause":
            return self._pick_seeded_variant("context:boundary", BOUNDARY_ACK_VARIANTS, seed_hint)

        if ack_type == "topic_shift":
            return self._pick_seeded_variant("context:topic_shift", TOPIC_SHIFT_ACK_VARIANTS, seed_hint)

        if ack_type == "profile_partial_with_boundary":
            field_ack = str(
                self._get_turn_decision_ack_value(turn_decision, "field_ack")
                or self.turn_understanding_service._build_lightweight_field_ack(user_message, user_profile)
            ).strip()  # noqa: SLF001
            if not field_ack:
                return self._pick_seeded_variant("context:boundary", BOUNDARY_ACK_VARIANTS, seed_hint)
            variants = tuple(v.format(field_ack=field_ack) for v in PROFILE_PARTIAL_BOUNDARY_ACK_VARIANTS)
            return self._pick_seeded_variant("context:partial_boundary", variants, seed_hint)

        if ack_type == "field_soft_refusal_retry":
            field = self._get_turn_decision_ack_value(turn_decision, "soft_retry_field")
            variants = FIELD_SOFT_REFUSAL_RETRY_ACK_VARIANTS.get(field) or ()
            if variants:
                return self._pick_seeded_variant(f"context:soft_refusal_retry:{field}", variants, seed_hint)
            return self._pick_seeded_variant("context:boundary", BOUNDARY_ACK_VARIANTS, seed_hint)

        if ack_type == "opening_profile_ack":
            field_ack = str(
                self._get_turn_decision_ack_value(turn_decision, "field_ack")
                or self.turn_understanding_service._build_opening_profile_ack(user_message)
            ).strip()  # noqa: SLF001
            if not field_ack:
                return ""
            variants = tuple(v.format(field_ack=field_ack) for v in OPENING_PROFILE_ACK_VARIANTS)
            return self._pick_seeded_variant("context:opening_profile_ack", variants, seed_hint)

        return ""

    def _response_has_context_ack(
        self,
        response: str,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
    ) -> bool:
        text = str(response or "").strip()
        if not text or not turn_decision.context_ack_required:
            return True

        ack_type = str(turn_decision.context_ack_type or "").strip()
        if ack_type == "work_busy":
            occupation = str(self._get_turn_decision_ack_value(turn_decision, "occupation") or user_profile.occupation or "").strip()
            return any(token and token in text for token in (occupation, "工作", "忙", "节奏"))
        if ack_type == "location_reuse":
            location = str(self._get_turn_decision_ack_value(turn_decision, "location") or user_profile.location or "").strip()
            return any(token and token in text for token in (location, "那边", "同城", "本地"))
        if ack_type == "preference_reuse":
            gender_preference = str(getattr(user_profile, "partner_gender_preference", "") or "").strip()
            normalized_gender = "男生" if gender_preference == "男" else ("女生" if gender_preference == "女" else "")
            preference = str(
                self._get_turn_decision_ack_value(turn_decision, "preference")
                or normalized_gender
                or ChatServiceAckRenderService.render_preference_for_ack(
                    str(user_profile.partner_requirement or "").strip()
                )
            ).strip()
            pref_tokens = [token for token in re.split(r"[，,、\s]+", preference) if token]
            pref_tokens.extend(["看重", "偏向", "合拍", "推荐"])
            return any(token and token in text for token in pref_tokens)
        if ack_type == "opening_profile_ack":
            field_ack = self._get_turn_decision_ack_value(turn_decision, "field_ack")
            return bool(field_ack) and any(token and token in text for token in (field_ack, "知道了", "接住", "这点"))
        if ack_type == "field_soft_refusal_retry":
            field = self._get_turn_decision_ack_value(turn_decision, "soft_retry_field")
            field_tokens = {
                "location": ("城市", "哪边", "常住"),
                "education": ("学历", "背景", "读书"),
                "occupation": ("工作", "做什么", "方向"),
                "sex": ("男生", "女生", "基本情况"),
                "age": ("年龄", "多大", "年龄段"),
                "marital_status": ("单身", "感情状态", "婚况"),
            }.get(field, ())
            return any(token in text for token in ("我不是想问得很细", "大概了解下", "不用说得太细")) and any(
                token in text for token in field_tokens
            )
        if ack_type in {"boundary_pause", "topic_shift", "profile_partial_with_boundary"}:
            boundary_tokens = ("先不追", "不勉强", "没关系", "先不聊", "先收住", "舒服的节奏", "先顺着")
            if ack_type == "profile_partial_with_boundary":
                field_ack = self._get_turn_decision_ack_value(turn_decision, "field_ack")
                return (
                    any(token in text for token in boundary_tokens)
                    and (not field_ack or field_ack[:2] in text or field_ack[:4] in text)
                )
            return any(token in text for token in boundary_tokens)
        return False

    def _should_use_opening_clarify(self, user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False

        normalized = re.sub(r"[\s,，。！？!?~～、]+", "", message)
        if not normalized:
            return False

        if "\ufffd" in message or "�" in message:
            return True

        if self.input_fallback_service.is_nonsense_input(message):
            return True

        weird_char_count = len(re.findall(r"[^\w\s\u4e00-\u9fa5，。！？!?~～、]", message))
        if weird_char_count >= 2:
            return True

        if len(normalized) <= 3 and not re.search(r"[\u4e00-\u9fa5a-zA-Z]", normalized):
            return True

        return False

    @staticmethod
    def _is_resume_profile_collection_message(user_message: str) -> bool:
        return ChatServiceMessageSignalService.is_resume_profile_collection_message(user_message)

    @staticmethod
    def _is_acknowledgement_only_message(user_message: str) -> bool:
        return ChatServiceMessageSignalService.is_acknowledgement_only_message(user_message)

    def _is_post_answer_reentry_turn(self, user_message: str, last_response: str = "") -> bool:
        """
        FAQ / 解释后的承接轮次禁止直接跳去中等字段，
        但不阻断主线字段或联系方式恢复。
        """
        message = str(user_message or "").strip()
        previous_response = str(last_response or "").strip()
        if not message or not previous_response:
            return False
        if not self._is_acknowledgement_only_message(message):
            return False

        faq_answer_markers = (
            "收费",
            "免费",
            "隐私",
            "流程",
            "联系方式只是为了",
            "方便联系",
            "不会随便",
            "不会外泄",
            "保护你的隐私",
            "给你说清楚",
            "我先跟你说清楚",
            "我先说清楚",
            "你可以放心",
            "理解偏了",
            "乱登记",
            "乱用",
            "这些资料主要是为了",
            "不会拿去",
            "不是拿去",
        )
        if self._has_faq_priority_signal(previous_response):
            return True
        return any(marker in previous_response for marker in faq_answer_markers)

    @staticmethod
    def _build_user_feeling_ack(user_message: str) -> str:
        message = str(user_message or "").strip()
        if "电话" in message and "不方便" in message:
            return "行，电话这块你现在不方便也没事。"
        if "微信" in message and ("不留" in message or "不方便" in message):
            return "行，微信这块你现在不想留也没事。"
        if "隐私" in message or "不太方便" in message or "先不留" in message:
            return "行，你这会儿不太想展开我能理解。"
        if "查户口" in message or "问这么细" in message:
            return "你会觉得我问得有点细，这个我能理解。"
        if "靠谱吗" in message or "担心" in message:
            return "你会担心这件事靠不靠谱，这很正常。"
        return "行，我明白你的顾虑。"

    def _ensure_conservative_empathy(self, user_message: str, answer: str) -> str:
        ack = self._build_user_feeling_ack(user_message)
        leading_content = ""
        for splitter in ("，", ",", "。"):
            if splitter in user_message:
                first_part = user_message.split(splitter, 1)[0].strip()
                if first_part and first_part not in ack and first_part not in answer:
                    leading_content = first_part
                break
        if not answer:
            return f"{leading_content}，{ack}" if leading_content else ack
        if "不太方便" in user_message or "先不留" in user_message or "隐私" in user_message:
            ack = ack.replace("我能理解。", "，这点我能理解。")
        if leading_content:
            return f"{leading_content}，{ack}{answer}"
        return f"{ack}{answer}"

    def _ensure_listener_first_ack(self, user_message: str, answer: str) -> str:
        ack = self._build_user_feeling_ack(user_message)
        if "查户口" in user_message or "问这么细" in user_message:
            ack = "你会觉得有点像查户口、问得太细，这个我听到了。"
        elif "靠谱吗" in user_message or "担心" in user_message:
            ack = "你会先担心靠不靠谱，这很正常。"
        return f"{ack}{answer}"

    def _get_risk_guard_response(self, user_message: str, user_profile: Optional[UserProfile] = None) -> str:
        message = str(user_message or "").strip()
        if self._matches_any_pattern(message, SELF_HARM_GUARD_PATTERNS):
            return (
                "这条我得先把安全放前面。先保证安全，"
                "先确保自己现在是安全的，"
                "尽快立刻联系身边能帮到你的人，或者直接联系当地心理援助热线 / 紧急援助渠道。"
            )
        if self._matches_any_pattern(message, MEDICAL_GUARD_PATTERNS):
            return "这类医疗判断我不适合直接替你给结论，最好还是尽快找正规医生或专业机构确认。"
        if self._matches_any_pattern(message, LEGAL_GUARD_PATTERNS):
            return "这类法律问题我不适合直接替你判断，最好找专业律师按你的实际情况看。"
        if self._matches_any_pattern(message, OVERREACH_GUARD_PATTERNS):
            return "这个我不方便直接给，涉及隐私边界的部分我得守住。"
        if self._matches_any_pattern(message, AI_IDENTITY_GUARD_PATTERNS):
            return "你会担心隐私，这很正常。简单说下流程：我这边先顺着把情况聊清楚，不会乱接你的话。"
        if self._matches_any_pattern(message, ABUSE_GUARD_PATTERNS):
            return "我先接住你这句，这轮我先不追问。你要是还想聊，我们就顺着你现在想说的来。"
        return "这句我先接住。你要是愿意，可以换个你更想聊的点。"

    def _get_boundary_pause_response(self, user_message: str) -> str:
        message = str(user_message or "").strip()
        if "电话" in message and "不方便" in message:
            return "行，电话这块你现在不方便也没事，这轮我先不追问。等你哪天觉得方便了再说，按你方便的方式来就行。"
        if self._matches_any_pattern(message, TOPIC_SHIFT_PATTERNS):
            return "好，那就先顺着你现在更想聊的这个来，资料这块我先不追问。"
        if "隐私" in message or "不太方便" in message or "先不留" in message:
            return "行，你这会儿不太想展开我能理解。隐私这块你放心，我们就顺着你舒服的节奏来。"
        return "行，我明白你这会儿不太方便。这块我先不追问，我们先顺着你舒服一点的节奏来。"

    def _get_complaint_repair_response(self, user_message: str) -> str:
        """
        用户抱怨问太多/重复问时的修复响应。

        修复要求：
        1. 承认刚才确实问重复了/问错了
        2. 不暴露“追资料/流程控制”等内部策略
        3. 不继续采集，不追加开放式尾问
        4. 简短自然收住，像朋友聊天
        """
        message = str(user_message or "").strip()
        # 根据具体抱怨内容做轻微适配
        if "查户口" in message or "问这么细" in message or "问得太细" in message:
            return (
                "是，刚才那样问确实容易让人烦。"
                "没关系，这个我先收住，你想接着聊什么就顺着说。"
            )
        if any(token in message for token in ("问这么多", "问这么多信息", "怎么问这么多")):
            return (
                "能理解你会觉得我一下子问得有点多。"
                "主要也是想把你的情况先摸得更清楚一点，这样后面聊合适方向会更准。"
                "不过这轮我先收一下，你想继续聊什么我就顺着来。"
            )
        if "重复" in message or "又问" in message or "问一遍" in message:
            return (
                "对，刚才这个我重复问了。"
                "这个点我们就不绕回去了，接着往下聊就行。"
            )
        if "不是说了" in message or "都说了" in message:
            return (
                "对，这个你前面已经说过了，是我刚刚岔开了。"
                "这个点先收住，我们接着往下聊。"
            )
        if "烦" in message or "啰嗦" in message:
            return (
                "嗯，这句我听到了，刚才确实让你觉得烦了。"
                "这个点我先收住，你想聊别的我就顺着你说。"
            )
        # 默认修复响应
        return (
            "对，刚才那句是我接得不够好。"
            "这个点我先收住，你想继续聊什么都行。"
        )

    def _should_add_light_appreciation(self, user_profile: UserProfile, marker: str) -> bool:
        """克制认可只偶尔出现，避免每轮都夸。"""
        if self._has_any_contact(user_profile):
            return False
        account_id = str(getattr(user_profile, "account_id", "") or "")
        progress_count = sum(1 for value in (user_profile.collection_progress or {}).values() if value)
        if progress_count < 2 or progress_count > 5:
            return False
        seed = f"{account_id}:{marker}:{progress_count}"
        return (sum(ord(ch) for ch in seed) % 5) == 0

    def _apply_income_appreciation_policy(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """高条件场景下偶尔补一小句克制认可，避免完全无情绪反馈。"""
        text = str(response or "").strip()
        if not text:
            return text

        all_fields = (collection_result or {}).get("all_fields") or []
        extracted_fields = {
            str(item.get("field") or "").strip()
            for item in all_fields
            if isinstance(item, dict)
        }

        if any(marker in text for marker in ("还不错", "挺可以", "挺不错", "条件挺", "不错呀")):
            return text
        if self._contains_contact_push_markers(text):
            return text

        compliment = ""
        marker = ""

        if "monthly_income" in extracted_fields:
            income_amount = self.expectation_service.parse_monthly_income_amount(user_profile.monthly_income)
            if income_amount is not None and income_amount >= 30000:
                compliment = "这块还挺不错的。"
                marker = "income"

        if not compliment and "education" in extracted_fields:
            education = str(getattr(user_profile, "education", "") or "").strip()
            if education in {"博士", "硕士", "研究生"}:
                compliment = "这个学历也挺不错的。"
                marker = "education"

        if not compliment and "occupation" in extracted_fields:
            occupation = str(getattr(user_profile, "occupation", "") or "").strip().lower()
            if occupation in {"it", "程序员", "医生", "教师", "老师", "金融", "运营"}:
                compliment = "这行做下来也挺稳的。"
                marker = "occupation"

        if not compliment or not marker:
            return text
        if not self._should_add_light_appreciation(user_profile, marker):
            return text

        if text.startswith(("好", "嗯", "行", "对", "是")):
            first_stop = min(
                [pos for pos in (text.find("。"), text.find("？"), text.find("?")) if pos != -1] or [-1]
            )
            if first_stop != -1:
                return f"{text[:first_stop + 1]} {compliment} {text[first_stop + 1:].lstrip()}".strip()
        return f"{compliment} {text}".strip()

    def _avoid_reasking_just_collected_field(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        *,
        current_ask_field: Optional[str],
        user_message: str = "",
        allow_medium_target: bool = True,
    ) -> str:
        """如果本轮已经收集到当前主问字段，就不要在回复里继续追问同一字段。"""
        text = str(response or "").strip()
        if not text or not current_ask_field:
            return text
        if current_ask_field not in ASK_GUARD_CORE_FIELDS:
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result.get("all_fields") or [])
            if isinstance(item, dict)
        }
        if current_ask_field not in collected_fields:
            return text
        if (
            current_ask_field == "age"
            and str(getattr(user_profile, "pending_birth_year_bucket", "") or "").strip()
            and not getattr(user_profile, "birth_year_confirmation_closed", False)
        ):
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if asked_fields and current_ask_field not in asked_fields:
            return text

        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=True,
            allow_medium_target=allow_medium_target,
        )
        next_field = decision.main_target
        if current_ask_field == "location" and not self.collection_policy.is_collected(user_profile, "education"):
            next_field = "education"
        elif not next_field or next_field == current_ask_field:
            if current_ask_field == "location" and not self.collection_policy.is_collected(user_profile, "education"):
                next_field = "education"
            elif self.collection_policy.can_actively_ask(user_profile, "marital_status") and current_ask_field != "marital_status":
                next_field = "marital_status"
            elif self.collection_policy.can_enter_contact(user_profile):
                next_field = "contact"
            else:
                return text

        logger.info(
            "[主线纠偏] 本轮已收集 %s，回复仍在追问同字段，改为追问 %s",
            current_ask_field,
            next_field,
        )
        if (
            next_field in {"education", "occupation"}
            and self._should_allow_interleaving_followup(
                user_profile,
                next_field,
                decision.side_target,
                allow_medium_target=allow_medium_target,
            )
        ):
            return self._build_interleaving_seed_for_model_rewrite(
                user_profile,
                user_message,
                main_target=next_field,
                preferred_side_target=decision.side_target,
                allow_medium_target=allow_medium_target,
            )
        return self._build_followup_seed_for_model_rewrite(next_field, user_profile, user_message=user_message)

    def _avoid_reasking_already_collected_fields(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        allow_medium_target: bool = True,
    ) -> str:
        """凡是已经收集完成的字段，不允许在后续回复里再次追问。"""
        text = str(response or "").strip()
        if not text or response_channel != "model":
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        broad_questioned_fields = self._detect_all_questioned_fields_in_response(text)
        asked_fields |= broad_questioned_fields
        if not asked_fields:
            return text

        covered_fields = {
            field for field in ASK_GUARD_MANAGED_FIELDS
            if self.collection_policy.is_collected(user_profile, field)
        }
        repeated_fields = asked_fields & covered_fields
        if not repeated_fields:
            return text

        effective_uncovered_priority = (
            "partner_requirement",
            "monthly_income",
            "marital_status",
            "occupation",
            "education",
            "location",
            "age",
            "sex",
        )
        for candidate in effective_uncovered_priority:
            if candidate in asked_fields and candidate not in covered_fields and self.collection_policy.can_actively_ask(user_profile, candidate):
                logger.info(
                    "[重问纠偏] 回复包含已收字段 %s，但仍有未收字段 %s，优先改为未收字段",
                    sorted(repeated_fields),
                    candidate,
                )
                if candidate in ASK_GUARD_MEDIUM_FIELDS:
                    if candidate == "partner_requirement":
                        return self._build_followup_seed_for_model_rewrite(candidate, user_profile, user_message=user_message)
                    host_field = self.collection_policy.get_medium_transition_host(user_profile, candidate)
                    if host_field:
                        return self._build_interleaving_seed_for_model_rewrite(
                            user_profile,
                            user_message,
                            main_target=host_field,
                            preferred_side_target=candidate,
                            allow_medium_target=allow_medium_target,
                        )
                return self._build_followup_seed_for_model_rewrite(candidate, user_profile, user_message=user_message)

        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=True,
            allow_medium_target=allow_medium_target,
        )

        if decision.main_target:
            logger.info(
                "[重问纠偏] 回复追问了已收字段 %s，改为当前未收目标 %s",
                sorted(repeated_fields),
                decision.main_target,
            )
            if self._should_allow_interleaving_followup(
                user_profile,
                decision.main_target,
                decision.side_target,
                allow_medium_target=allow_medium_target,
            ):
                return self._build_interleaving_seed_for_model_rewrite(
                    user_profile,
                    user_message,
                    main_target=decision.main_target,
                    preferred_side_target=decision.side_target,
                    allow_medium_target=allow_medium_target,
                )
            return self._build_followup_seed_for_model_rewrite(decision.main_target, user_profile, user_message=user_message)

        forced_target = decision.forced_cover_target
        if forced_target and self.collection_policy.can_actively_ask(user_profile, forced_target):
            logger.info(
                "[重问纠偏] 回复追问了已收字段 %s，改为剩余覆盖目标 %s",
                sorted(repeated_fields),
                forced_target,
            )
            host_field = self.collection_policy.get_medium_transition_host(user_profile, forced_target)
            if host_field:
                return self._build_interleaving_seed_for_model_rewrite(
                    user_profile,
                    user_message,
                    main_target=host_field,
                    preferred_side_target=forced_target,
                    allow_medium_target=allow_medium_target,
                )
            return self._build_followup_seed_for_model_rewrite(forced_target, user_profile, user_message=user_message)

        if self.collection_policy.can_enter_contact(user_profile):
            logger.info(
                "[重问纠偏] 回复追问了已收字段 %s，改为联系方式入口",
                sorted(repeated_fields),
            )
            return self._build_followup_seed_for_model_rewrite("contact", user_profile, user_message=user_message)

        return text

    def _detect_all_questioned_fields_in_response(self, response: str) -> set[str]:
        text = str(response or "").strip()
        if not text:
            return set()

        fields: set[str] = set()
        question_segments = [
            segment.strip()
            for segment in re.split(r"[。!！\n]+", text)
            if segment.strip() and ("？" in segment or "?" in segment)
        ]
        if not question_segments:
            return fields

        for segment in question_segments:
            fields |= self._detect_question_fields_in_segment(segment)
        return fields

    @staticmethod
    def _question_field_pattern_map() -> dict[str, tuple[str, ...]]:
        return {
            "sex": (r"男生还是女生", r"男生女生", r"你是男生", r"你是女生", r"女孩子", r"男孩子"),
            "age": (r"多大", r"几岁", r"年龄", r"年纪", r"几几年的", r"哪一年的", r"哪年出生", r"哪一年出生"),
            "location": (r"哪个城市", r"什么城市", r"在哪个城市", r"在哪边", r"哪里生活"),
            "education": (r"学历",),
            "occupation": (r"做什么工作", r"做哪方面", r"什么工作", r"职业", r"工作"),
            "marital_status": (r"单身状态", r"感情状态", r"婚况", r"离异"),
            "monthly_income": (r"月收入", r"月薪", r"收入", r"工资", r"收入区间", r"收入大概"),
            "partner_requirement": (r"另一半", r"要求", r"看重", r"想找个什么样", r"更在意哪方面", r"更看重哪一点"),
        }

    @classmethod
    def _detect_question_fields_in_segment(cls, segment: str) -> set[str]:
        text = str(segment or "").strip()
        if not text:
            return set()

        detected: set[str] = set()
        for field, patterns in cls._question_field_pattern_map().items():
            if any(re.search(pattern, text) for pattern in patterns):
                detected.add(field)
        return detected

    @staticmethod
    def _extract_explicit_question_segments(response: str) -> list[str]:
        text = str(response or "").strip()
        if not text:
            return []
        return [
            segment.strip()
            for segment in re.findall(r"[^。!！\n]*?[？?]", text)
            if segment.strip()
        ]

    def _count_questioned_fields_in_response(self, response: str) -> Dict[str, int]:
        text = str(response or "").strip()
        if not text:
            return {}

        counts: Dict[str, int] = {}
        segments = self._extract_explicit_question_segments(text)
        if not segments:
            segments = [
                segment.strip()
                for segment in re.split(r"[。!！\n]+", text)
                if segment.strip() and any(cue in segment for cue in ASK_GUARD_QUESTION_CUES)
            ]
        for segment in segments:
            normalized_segment = re.sub(r"[？?]+\s*$", "", segment).strip()
            if not normalized_segment:
                continue
            for field in self._detect_question_fields_in_segment(normalized_segment):
                counts[field] = counts.get(field, 0) + 1
        return counts

    def _resolve_primary_followup_field_from_response(
        self,
        *,
        response: str,
        planned_ask_field: str = "",
    ) -> str:
        planned = str(planned_ask_field or "").strip()
        if planned:
            return planned

        for segment in self._extract_explicit_question_segments(response):
            normalized_segment = re.sub(r"[？?]+\s*$", "", str(segment or "")).strip()
            detected_fields = list(self._detect_question_fields_in_segment(normalized_segment))
            if detected_fields:
                return detected_fields[0]
        return ""

    @staticmethod
    def _looks_like_dense_intro_message_for_budget_guard(
        *,
        user_profile: UserProfile,
        user_message: str,
    ) -> bool:
        semantic_summary = dict(getattr(user_profile, "last_semantic_summary", {}) or {})
        if str(semantic_summary.get("turn_mode") or "").strip() == "dense_intro":
            return True

        message = str(user_message or "").strip()
        if len(message) < 20:
            return False
        punctuation_count = len(re.findall(r"[，,、；;。.!！？]", message))
        return punctuation_count >= 3

    def _append_safe_short_answer_followup(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        *,
        previous_asked_field: Optional[str],
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        ask_field: Optional[str] = None,
        followup_topic: Optional[str] = None,
    ) -> str:
        """短答命中上一轮字段且当前回复停住时，安全续问下一个核心字段。"""
        text = str(response or "").strip()
        if not text or response_channel != "model" or primary_move != "light_followup":
            return text
        if ask_field or followup_topic:
            return text
        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            return text
        if self._should_lock_divorce_confirmation(user_profile, user_message):
            return text
        if self._has_active_contact_context(user_profile, collection_result=collection_result, user_message=user_message):
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result.get("all_fields") or [])
            if isinstance(item, dict)
        }
        if not previous_asked_field or previous_asked_field not in collected_fields:
            return text
        if previous_asked_field not in ASK_GUARD_CORE_FIELDS:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if asked_fields:
            return text

        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=False,
        )
        next_field = decision.main_target
        safe_followup_fields = {"age", "location", "education", "occupation"}
        if not next_field or next_field == previous_asked_field or next_field not in safe_followup_fields:
            return text
        if not self.collection_policy.can_actively_ask(user_profile, next_field):
            return text

        followup = self._build_followup_seed_for_model_rewrite(next_field, user_profile, user_message=user_message).strip()
        if not followup:
            return text

        logger.info(
            "[短答续问] 上一轮字段 %s 已命中，本轮轻确认后续问 %s",
            previous_asked_field,
            next_field,
        )
        if text.endswith(("。", "！", "？", ".", "!", "?")):
            return f"{text} {followup}".strip()
        return f"{text}。 {followup}".strip()

    def _prepend_multi_field_ack_transition(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        *,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        ask_field: Optional[str] = None,
        followup_topic: Optional[str] = None,
    ) -> str:
        """本轮提取到多个资料字段时，先轻承接一个点，再进入下一问。"""
        text = str(response or "").strip()
        if not text or response_channel != "model" or primary_move not in {"ack_and_ask", "light_followup"}:
            return text
        if not ask_field or followup_topic:
            return text
        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            return text
        if self._should_lock_divorce_confirmation(user_profile, user_message):
            return text
        if self._has_active_contact_context(user_profile, collection_result=collection_result, user_message=user_message):
            return text
        asked_fields = self._detect_asked_fields_in_response(text)
        if asked_fields and asked_fields <= {"contact"}:
            return text

        all_fields = [
            item for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        if len(all_fields) < 2:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if ask_field not in asked_fields:
            return text
        if len(asked_fields) >= 2:
            return text

        candidate_order = ("occupation", "location", "marital_status", "education", "age", "sex")
        chosen_ack = ""
        for field_name in candidate_order:
            matched = next((item for item in all_fields if str(item.get("field") or "").strip() == field_name), None)
            if not matched:
                continue
            ack = self._build_contextual_followup_ack(
                field_name,
                matched.get("value"),
                ask_field=ask_field,
                user_profile=user_profile,
                include_followup_transition=False,
            )
            if ack:
                chosen_ack = ack.strip()
                break

        if not chosen_ack:
            return text

        normalized_text = text.replace(" ", "")
        normalized_ack = chosen_ack.replace(" ", "")
        if normalized_ack in normalized_text:
            return text
        matched_value = str(matched.get("value") or "").strip()
        if matched_value and matched_value.replace(" ", "") in normalized_text:
            return text
        if field_name == "location" and self._response_already_absorbs_location_context(text, matched.get("value")):
            return text
        if self._response_already_acks_field(text, field_name, matched.get("value")):
            return text

        logger.info(
            "[多字段承接] 本轮提取到多个字段，先承接 %s 再追问 %s",
            chosen_ack,
            ask_field,
        )
        return ChatServiceResponseCleanupService.compress_multi_action_response(
            f"{chosen_ack} {text}".strip()
        )

    def _prepend_single_field_ack_transition(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        *,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        ask_field: Optional[str] = None,
        followup_topic: Optional[str] = None,
    ) -> str:
        """单字段短答已命中且后续仍在追问时，补一个轻承接。"""
        text = str(response or "").strip()
        if not text or response_channel != "model" or primary_move not in {"ack_and_ask", "light_followup"}:
            return text
        if not ask_field or followup_topic:
            return text
        if not self._is_short_answer(user_message):
            return text
        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            return text
        if self._should_lock_divorce_confirmation(user_profile, user_message):
            return text
        if self._has_active_contact_context(user_profile, collection_result=collection_result, user_message=user_message):
            return text

        all_fields = [
            item for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        if len(all_fields) != 1:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if ask_field not in asked_fields:
            return text

        field_name = str(all_fields[0].get("field") or "").strip()
        if field_name in {"education", "age", "age_label"}:
            return text
        ack = self._build_contextual_followup_ack(
            field_name,
            all_fields[0].get("value"),
            ask_field=ask_field,
            user_profile=user_profile,
            include_followup_transition=False,
        ).strip()
        if not ack:
            return text

        normalized_text = text.replace(" ", "")
        normalized_ack = ack.replace(" ", "")
        if normalized_ack in normalized_text:
            return text
        matched_value = str(all_fields[0].get("value") or "").strip()
        if matched_value and matched_value.replace(" ", "") in normalized_text:
            return text
        if field_name == "location" and self._response_already_absorbs_location_context(text, all_fields[0].get("value")):
            return text
        if self._response_already_acks_field(text, field_name, all_fields[0].get("value")):
            return text

        logger.info(
            "[单字段承接] 本轮提取到 %s，先承接再追问 %s",
            field_name,
            ask_field,
        )
        return ChatServiceResponseCleanupService.compress_multi_action_response(
            f"{ack} {text}".strip()
        )

    def _ensure_humanlike_memory_ack(self, user_message: str, user_profile: UserProfile, response: str) -> str:
        message = str(user_message or "").strip()
        if not response:
            return response

        if "查户口" in message or "问这么细" in message:
            return f"我知道你会觉得我问得细一点，不过也是想尽量聊得更匹配。{response}"

        location = str(getattr(user_profile, "location", "") or "").strip()
        if location and location not in response and any(token in message for token in ("那边", "这边", "那里")):
            return f"{location}这边的话，{response}"

        occupation = str(getattr(user_profile, "occupation", "") or "").strip()
        if occupation and occupation not in response and ("工作" in message or "忙" in message):
            return f"你平时做{occupation}，我知道你工作节奏可能会比较忙。{response}"

        return response

    def _apply_priority_question_guard(
        self,
        response: str,
        turn_decision: TurnDecision,
        user_message: str,
    ) -> str:
        text = str(response or "").strip()
        if not text or not turn_decision.prioritize_user_question:
            return text

        faq_response = self._get_priority_question_response(user_message, UserProfile(account_id="priority_question_guard"))
        if not faq_response:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if self._contains_contact_push_markers(text) or asked_fields:
            return faq_response
        return text

    def _apply_context_ack_policy(
        self,
        response: str,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        user_message: str,
    ) -> str:
        text = str(response or "").strip()
        if not text or not turn_decision.context_ack_required:
            return text
        if self._response_has_context_ack(text, turn_decision, user_profile):
            return text

        ack = self._render_context_ack(turn_decision, user_profile, user_message)
        if not ack:
            return text

        if turn_decision.context_ack_type in {"boundary_pause", "topic_shift", "profile_partial_with_boundary"}:
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return ack

        return f"{ack} {text}".strip()

    def _build_rotating_ending_message(self, user_profile: UserProfile, last_response: str) -> str:
        candidates = [msg for msg in ROTATING_ENDING_VARIANTS if msg != last_response] or list(ROTATING_ENDING_VARIANTS)
        return random.choice(candidates)

    async def _call_ai(
        self,
        prompt: str,
        account_id: str,
        user_message: str = "",
        *,
        turn_decision: TurnDecision | None = None,
    ) -> str:
        """
        调用 AI 服务。

        Args:
            prompt: 完整的对话提示词
            account_id: 用户ID

        Returns:
            str: AI 回复内容
        """
        chosen_model = self._select_model_for_turn(user_message, prompt)
        response_max_tokens = self._select_max_tokens_for_turn(user_message, prompt)
        response_reasoning_effort = self._select_reasoning_effort_for_turn(turn_decision=turn_decision)
        use_max_completion_tokens = self._should_use_max_completion_tokens_for_turn(turn_decision=turn_decision)
        self._last_ai_failure_reason = None
        result = await self.ai_response_generator.generate(
            prompt=prompt,
            account_id=account_id,
            user_message=user_message,
            model_name=chosen_model,
            max_tokens=response_max_tokens,
            use_max_completion_tokens=use_max_completion_tokens,
            reasoning_effort=response_reasoning_effort,
        )
        self._last_ai_failure_reason = result.failure_reason
        return result.content

    def _should_run_opening_intent_detection(
        self,
        conversation_context: Optional[Dict[str, Any]],
        user_profile: UserProfile,
    ) -> bool:
        if not self._env_flag("CHAT_GENERATION_OPENING_INTENT_ENABLED", False):
            return False
        message_count = int((conversation_context or {}).get("message_count", 0))
        if message_count > 2:
            return False
        if self.collection_policy.has_ongoing_contact_flow(user_profile):
            return False
        if user_profile.repair_mode and user_profile.ask_cooldown_turns > 0:
            return False
        if getattr(user_profile, "conversation_ended", False):
            return False
        return True

    @staticmethod
    def _normalize_opening_probe_text(user_message: str) -> str:
        message = str(user_message or "").strip().lower()
        if not message:
            return ""
        normalized = re.sub(r"[\s,，。！？!?~～、:：;；\"'`()（）]+", "", message)
        normalized = re.sub(r"(呀|啊|呢|哈|啦|嘛|呐|喔|哦|噢)+", "", normalized)
        normalized = re.sub(r"(在吗){2,}", "在吗", normalized)
        normalized = re.sub(r"(在不){2,}", "在不", normalized)
        normalized = re.sub(r"(你好){2,}", "你好", normalized)
        normalized = re.sub(r"(hi){2,}", "hi", normalized)
        normalized = re.sub(r"(hello){2,}", "hello", normalized)
        return normalized

    def _is_stable_opening_greeting(self, user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        if self.greeting_service.is_greeting(message):
            return True
        normalized = self._normalize_opening_probe_text(message)
        if not normalized:
            return False
        greeting_tokens = ("你好", "您好", "hi", "hello", "哈喽", "嗨", "在吗", "在不", "早上好", "下午好", "晚上好")
        if any(token in normalized for token in greeting_tokens):
            remainder = normalized
            for token in greeting_tokens:
                remainder = remainder.replace(token, "")
            return remainder == ""
        return False

    def _is_noisy_opening_clarify_message(self, user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        if self._should_use_opening_clarify(message):
            return True
        normalized = self._normalize_opening_probe_text(message)
        if not normalized:
            return False
        if any(token in normalized for token in ("你好", "您好", "在吗", "在不")):
            stripped = normalized
            for token in ("你好", "您好", "在吗", "在不"):
                stripped = stripped.replace(token, "")
            return bool(stripped) and not self.greeting_service.is_greeting(stripped)
        return False

    def _build_service_confirmation_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        message_count: int,
        last_response: str = "",
    ) -> str:
        ack = random.choice(SERVICE_CONFIRMATION_MID_ACK_VARIANTS).strip()
        previous_asked_field = self._resolve_interrupted_followup_field(
            user_profile,
            last_response=last_response,
            fallback_user_message=user_message,
        )
        if previous_asked_field:
            followup = self._build_followup_seed_for_model_rewrite(previous_asked_field, user_profile, user_message=user_message).strip()
            if followup:
                return f"{ack} {followup}".strip()
        unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core_fields:
            for next_core in ("occupation", "education", "age", "location", "sex"):
                if next_core not in unresolved_core_fields:
                    continue
                if self.collection_policy.can_actively_ask(user_profile, next_core):
                    followup = self._build_followup_seed_for_model_rewrite(next_core, user_profile, user_message=user_message).strip()
                    if followup:
                        return f"{ack} {followup}".strip()
        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            message_count=message_count,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        )
        next_field = decision.main_target
        if next_field == "contact":
            next_field = None
        if next_field and self.collection_policy.can_actively_ask(user_profile, next_field):
            followup = self._build_followup_seed_for_model_rewrite(next_field, user_profile, user_message=user_message).strip()
            if followup:
                return f"{ack} {followup}".strip()
        return ack

    def _build_opening_matchmaking_response(
        self,
        *,
        user_message: str,
        seed_hint: str,
        understanding: Optional[TurnUnderstandingResult] = None,
    ) -> str:
        followup = self.greeting_service.get_open_self_intro_response(seed_hint=seed_hint).strip()
        opening_ack = self.turn_understanding_service._build_opening_profile_ack(user_message)  # noqa: SLF001
        secondary_signals = set((understanding.secondary_signals or []) if understanding else [])
        has_service_confirmation = "service_confirmation_like" in secondary_signals or self.turn_understanding_service._is_service_confirmation_like(user_message)  # noqa: SLF001

        if has_service_confirmation:
            ack = random.choice(SERVICE_CONFIRMATION_OPENING_ACK_VARIANTS).strip()
            if opening_ack:
                return f"{ack} {opening_ack} {followup}".strip()
            return f"{ack} {followup}".strip()

        if opening_ack:
            return f"{opening_ack} {followup}".strip()
        return followup

    def _build_profile_bridge_generation_instruction(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        turn_decision: TurnDecision,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """为“用户刚给资料 -> 顺着资料追问主字段+相近字段”场景补充生成约束。"""
        bridge_bundle = self._resolve_profile_bridge_bundle(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )
        if not bridge_bundle:
            return ""

        bridge_context = bridge_bundle["context"]
        main_prompt_label = bridge_bundle["main_prompt_label"]
        side_prompt_labels = bridge_bundle["side_prompt_labels"]
        summary = "；".join(f"{key}={value}" for key, value in bridge_context.items())
        return self.profile_bridge_prompt_formatter.build_generation_instruction(
            summary=summary,
            main_prompt_label=main_prompt_label,
            side_prompt_labels=side_prompt_labels,
        )

    def build_generation_prompt(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any],
        turn_decision: TurnDecision,
        understanding_result: TurnUnderstandingResult,
    ) -> str:
        return self.generation_prompt_service.build_generation_prompt(
            user_message=user_message,
            user_profile=user_profile,
            conversation_context=conversation_context,
            turn_decision=turn_decision,
            understanding_result=understanding_result,
        )

    async def extract_and_merge_generated_fields(
        self,
        *,
        ai_response: str,
        user_message: str,
        last_response: str,
        user_profile: UserProfile,
        understanding_result: TurnUnderstandingResult,
        infra_fail: bool,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """统一承接模型回复后的字段提取、规则兜底和确认分类 fallback。"""
        response_text = str(ai_response or "")
        has_structured_extract = "<extract>" in response_text or "```json" in response_text
        ai_extracted_data = (
            {}
            if infra_fail or not has_structured_extract
            else self.extraction_service.extract_json_from_response(ai_response)
        )
        rule_extracted_data = self._extract_turn_level_fields(
            user_message,
            understanding_result=understanding_result,
            last_response=last_response,
        )
        extracted_data, extraction_meta = self._fuse_extracted_fields(
            ai_extracted_data,
            {
                **dict(rule_extracted_data or {}),
                **(
                    {"age": int(str((rule_extracted_data or {}).get("age") or "").strip())}
                    if isinstance((rule_extracted_data or {}).get("age"), str)
                    and str((rule_extracted_data or {}).get("age") or "").strip().isdigit()
                    else {}
                ),
            },
            user_message,
            user_profile=user_profile,
            last_response=last_response,
            understanding_result=understanding_result,
        )
        if understanding_result is None and not extracted_data.get("partner_requirement"):
            pref = self._extract_simple_partner_requirement(user_message)
            if pref:
                extracted_data["partner_requirement"] = pref
                extraction_meta["partner_requirement"] = {
                    "source": "rule_fallback",
                    "confidence": 0.86,
                    "source_text": user_message,
                }
        if understanding_result is None and not extracted_data.get("partner_gender_preference"):
            partner_gender = self.turn_understanding_service._extract_partner_gender_preference(user_message)  # noqa: SLF001
            if partner_gender:
                extracted_data["partner_gender_preference"] = partner_gender
                extraction_meta["partner_gender_preference"] = {
                    "source": "rule_fallback",
                    "confidence": 0.86,
                    "source_text": user_message,
                }
        return await self._apply_confirmation_ai_fallback(
            extracted_data,
            extraction_meta,
            user_message=user_message,
            last_response=last_response,
            user_profile=user_profile,
        )

    async def refresh_turn_decision_after_collection(
        self,
        *,
        ai_response: str,
        account_id: str,
        user_message: str,
        user_profile: UserProfile,
        conversation_context: Dict[str, Any],
        understanding_result: TurnUnderstandingResult,
        previous_turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
    ) -> tuple[str, TurnDecision]:
        """在收集结果落库后，统一刷新决策，但不再改写第一次生成的话术。"""
        if previous_turn_decision.response_channel != "model":
            return ai_response, previous_turn_decision

        refreshed_decision_profile = self._build_shadow_profile_for_decision(
            user_profile,
            user_message,
            last_response=str((conversation_context.get("recent_responses") or [""])[-1] or ""),
            understanding_result=understanding_result,
        )
        refreshed_decision_profile = self._merge_collection_result_into_shadow_profile(
            refreshed_decision_profile,
            collection_result=collection_result,
            understanding_result=understanding_result,
        )
        refreshed_turn_decision = await self._build_turn_decision(
            user_message,
            refreshed_decision_profile,
            conversation_context=conversation_context,
            understanding_result=understanding_result,
        )
        if self._should_force_progress_followup_after_collection(
            refreshed_turn_decision=refreshed_turn_decision,
            collection_result=collection_result,
            user_profile=refreshed_decision_profile,
        ):
            forced_field = self._select_next_progress_target(
                refreshed_decision_profile,
                user_message=user_message,
            )
            if forced_field:
                refreshed_turn_decision.intent = "general"
                refreshed_turn_decision.primary_move = "light_followup"
                refreshed_turn_decision.ask_field = forced_field
                refreshed_turn_decision.prioritize_user_question = False
                refreshed_turn_decision.allow_contact_target = forced_field == "contact"
                refreshed_turn_decision.allow_medium_target = forced_field != "contact"
                refreshed_turn_decision.response_channel = "model"
                refreshed_turn_decision.user_concern_type = None
                logger.info(
                    "[refresh_turn_decision_force_followup] forced_ask_field=%s",
                    forced_field,
                )
        if previous_turn_decision.resume_applied and previous_turn_decision.ask_field:
            previous_field = str(previous_turn_decision.ask_field or "").strip()
            refreshed_field = str(getattr(refreshed_turn_decision, "ask_field", "") or "").strip()
            if (
                previous_turn_decision.primary_move == "light_followup"
                and previous_turn_decision.intent == "general"
                and previous_field
                and (
                    refreshed_turn_decision.prioritize_user_question
                    or not refreshed_field
                    or refreshed_turn_decision.intent == "confirmation"
                )
            ):
                logger.info(
                    "[refresh_turn_decision_preserve_resume] ask_field=%s refreshed_intent=%s",
                    previous_field,
                    refreshed_turn_decision.intent,
                )
                return ai_response, previous_turn_decision
        return ai_response, refreshed_turn_decision

    def _merge_collection_result_into_shadow_profile(
        self,
        shadow_profile: UserProfile,
        *,
        collection_result: Dict[str, Any],
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> UserProfile:
        merged = shadow_profile.model_copy(deep=True)
        for item in (collection_result.get("all_fields") or []):
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            value = item.get("value")
            if not field or value in (None, ""):
                continue
            if hasattr(merged, field):
                setattr(merged, field, value)
            if field in merged.collection_progress:
                merged.collection_progress[field] = True
            if field == "phone":
                merged.phone_collected = True
                merged.collection_progress["contact"] = True
            elif field == "wechat":
                merged.wechat_collected = True
                merged.collection_progress["contact"] = True
            elif field == "contact":
                merged.collection_progress["contact"] = True

        persistence_plan = getattr(understanding_result, "persistence_plan", None) if understanding_result is not None else None
        if persistence_plan is not None:
            for field in list(getattr(persistence_plan, "accepted_fields", []) or []):
                field_name = str(getattr(field, "field", "") or "").strip()
                value = getattr(field, "normalized_value", None)
                scope = str(getattr(field, "scope", "") or "").strip()
                persistence_state = str(getattr(field, "persistence_state", "committed") or "committed").strip()
                source_channel = str(getattr(field, "source_channel", "unknown") or "unknown").strip()
                if not field_name or value in (None, ""):
                    continue
                if scope not in {"self", "contact", "partner"} or persistence_state != "committed":
                    continue
                if (
                    field_name in {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
                    and not ChatService._allows_high_risk_field_from_persistence_plan(field)
                ):
                    continue
                if hasattr(merged, field_name):
                    setattr(merged, field_name, value)
                if field_name in merged.collection_progress:
                    merged.collection_progress[field_name] = True
                if field_name in {"phone", "wechat", "contact"}:
                    merged.collection_progress["contact"] = True
                    if field_name == "phone":
                        merged.phone_collected = True
                    if field_name == "wechat":
                        merged.wechat_collected = True
        return merged

    def _should_force_progress_followup_after_collection(
        self,
        *,
        refreshed_turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
        user_profile: UserProfile,
    ) -> bool:
        collected_fields = list((collection_result.get("all_fields") or []))
        has_valid_contact_progress = any(
            isinstance(item, dict)
            and str(item.get("field") or "").strip() in {"contact", "phone", "wechat"}
            and str(item.get("value") or "").strip()
            for item in collected_fields
        )
        if has_valid_contact_progress:
            return False
        if str(getattr(refreshed_turn_decision, "priority_primary_task", "") or "").strip() == "contact_record":
            return False
        if str(getattr(refreshed_turn_decision, "ask_field", "") or "").strip():
            return False
        if getattr(refreshed_turn_decision, "prioritize_user_question", False):
            return False
        if getattr(refreshed_turn_decision, "next_action", "") in {"repair_and_release"}:
            return False
        transition_reason = str(
            getattr(refreshed_turn_decision, "context_ack_payload", {}).get("pre_generation_transition_reason") or ""
        ).strip()
        has_progress = bool(collected_fields)
        if transition_reason == "resume_after_divorce_confirmation_complete":
            has_progress = True
        if not has_progress:
            return False
        return bool(
            self._select_next_progress_target(user_profile, user_message="")  # noqa: B023
        )

    def _select_next_progress_target(
        self,
        user_profile: UserProfile,
        *,
        user_message: str = "",
    ) -> Optional[str]:
        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=True,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="light_followup",
        )
        candidate = str(getattr(policy_decision, "main_target", "") or "").strip()
        if candidate == "contact":
            return "contact" if self.collection_policy.can_enter_contact(user_profile) else None
        if candidate and self.collection_policy.can_actively_ask(user_profile, candidate):
            return candidate

        for field in [
            *self.collection_policy.get_uncovered_core_fields(user_profile),
            *self.collection_policy.get_uncovered_medium_fields(user_profile),
        ]:
            if self.collection_policy.can_actively_ask(user_profile, field):
                return field
        if self.collection_policy.can_enter_contact(user_profile) and not self.collection_policy.is_collected(user_profile, "contact"):
            return "contact"
        return None

    async def finalize_generated_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
        response_to_clean: str,
        ai_response: str,
        bridge_prefix: str,
        contact_gate_before: bool,
        message_count: int,
    ) -> tuple[str, bool, UserProfile]:
        return await self.finalize_service.finalize_generated_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            collection_result=collection_result,
            response_to_clean=response_to_clean,
            ai_response=ai_response,
            bridge_prefix=bridge_prefix,
            contact_gate_before=contact_gate_before,
            message_count=message_count,
        )

    async def build_short_circuit_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        collection_result: Dict[str, Any],
        dialog_id: str,
        response_route: str,
        field_ask_count_before: Optional[Dict[str, int]] = None,
        track_asked_fields: bool = False,
        ai_response_for_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """统一处理短路返回：更新状态、刷新资料并构建 payload。"""
        await self._update_conversation_state(
            account_id,
            user_message,
            final_response,
            ai_response_for_state or final_response,
            turn_decision=None,
            track_asked_fields=track_asked_fields,
        )
        user_profile = await self.user_service.get_user_profile(account_id)
        return await self._build_chat_response(
            account_id,
            user_profile,
            final_response,
            collection_result,
            dialog_id,
            field_ask_count_before or (dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}),
            response_route=response_route,
        )

    # Phase orchestration entrypoints: pre-generation short-circuits.
    async def maybe_build_quick_faq_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        decision_profile: UserProfile,
        conversation_context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return await self.preparation_service.maybe_build_quick_faq_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            decision_profile=decision_profile,
            conversation_context=conversation_context,
        )

    async def maybe_build_pre_generation_short_circuit_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        message_count: int,
    ) -> tuple[Optional[str], Optional[Dict[str, Any]], UserProfile]:
        return await self.preparation_service.maybe_build_pre_generation_short_circuit_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            message_count=message_count,
        )

    async def maybe_build_already_ended_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        is_new_user_session: bool,
    ) -> Optional[AlreadyEndedPreparation]:
        return await self.preparation_service.maybe_build_already_ended_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            is_new_user_session=is_new_user_session,
        )

    # Phase orchestration entrypoints: final payload assembly.
    async def maybe_build_preset_response_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        collection_result: Dict[str, Any],
    ) -> Optional[tuple[str, Dict[str, Any]]]:
        return await self.preset_response_service.maybe_build_preset_response_payload(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            collection_result=collection_result,
        )

    async def build_final_turn_payload(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        final_response: str,
        collection_result: Dict[str, Any],
        dialog_id: str,
        route_name: str,
        infra_fail: bool = False,
        infra_fail_reason: str = "",
    ) -> Dict[str, Any]:
        return await self.delivery_service.build_final_turn_payload(
            account_id=account_id,
            user_profile=user_profile,
            final_response=final_response,
            collection_result=collection_result,
            dialog_id=dialog_id,
            route_name=route_name,
            infra_fail=infra_fail,
            infra_fail_reason=infra_fail_reason,
        )

    # Phase orchestration entrypoints: generation + collection.
    async def generate_turn_response_text(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        main_prompt: str,
        turn_decision: TurnDecision,
        conversation_context: Dict[str, Any],
    ) -> tuple[str, bool, str]:
        return await self.generation_service.generate_turn_response_text(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            main_prompt=main_prompt,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )

    async def build_enhanced_response_to_clean(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        collection_result: Dict[str, Any],
        ai_response: str,
    ) -> str:
        return await self.delivery_service.build_enhanced_response_to_clean(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            collection_result=collection_result,
            ai_response=ai_response,
        )

    async def process_collection_phase(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        extraction_meta: Dict[str, Any],
        user_message: str,
        message_count: int,
        understanding_result: TurnUnderstandingResult,
        conversation_context: Dict[str, Any],
        turn_decision: TurnDecision,
        ai_response: str,
    ) -> CollectionPhaseOutcome:
        return await self.generation_service.process_collection_phase(
            account_id=account_id,
            user_profile=user_profile,
            extracted_data=extracted_data,
            extraction_meta=extraction_meta,
            user_message=user_message,
            message_count=message_count,
            understanding_result=understanding_result,
            conversation_context=conversation_context,
            turn_decision=turn_decision,
            ai_response=ai_response,
        )

    async def run_generation_collection_phase(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        main_prompt: str,
        last_response: str,
        message_count: int,
        understanding_result: TurnUnderstandingResult,
        conversation_context: Dict[str, Any],
        turn_decision: TurnDecision,
    ) -> GenerationCollectionPhaseOutcome:
        return await self.generation_service.run_generation_collection_phase(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            main_prompt=main_prompt,
            last_response=last_response,
            message_count=message_count,
            understanding_result=understanding_result,
            conversation_context=conversation_context,
            turn_decision=turn_decision,
        )

    # Phase orchestration entrypoints: post-generation delivery sync.
    async def sync_post_delivery_state(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        ai_response: str,
        delivery_ok: bool,
        turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
        message_count: int,
        previous_asked_field: Optional[str],
        previous_asked_side_field: Optional[str] = None,
    ) -> tuple[str, UserProfile]:
        return await self.delivery_service.sync_post_delivery_state(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            ai_response=ai_response,
            delivery_ok=delivery_ok,
            turn_decision=turn_decision,
            collection_result=collection_result,
            message_count=message_count,
            previous_asked_field=previous_asked_field,
            previous_asked_side_field=previous_asked_side_field,
        )

    def _resolve_profile_bridge_bundle(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        turn_decision: TurnDecision,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """解析桥接模式所需的上下文和必带相近字段。"""
        bridge_context = self._extract_profile_bridge_context(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )
        if not bridge_context:
            return {}

        main_target = str(getattr(turn_decision, "ask_field", "") or "").strip()
        if not main_target:
            return {}
        side_targets: list[str] = []
        main_prompt_label = ""
        side_prompt_labels: list[str] = []

        side_target = ""
        if getattr(turn_decision, "allow_medium_target", False):
            policy_decision = self.collection_policy.decide(
                user_profile,
                user_message=user_message,
                message_count=int((conversation_context or {}).get("message_count", 0)),
                allow_contact_target=False,
                allow_medium_target=True,
                prioritize_user_question=getattr(turn_decision, "prioritize_user_question", False),
                primary_move=getattr(turn_decision, "primary_move", "ack_and_ask"),
            )
            if policy_decision.main_target == main_target:
                side_target = str(policy_decision.side_target or "").strip()
        force_bridge_income_side_target = False
        if main_target == "occupation" and bridge_context.get("当前状态"):
            side_target = "monthly_income"
            force_bridge_income_side_target = True
        if not side_target and getattr(turn_decision, "allow_medium_target", False):
            contextual_side_target_map = {
                "occupation": "monthly_income",
                "marital_status": "partner_requirement",
                "education": "marital_status",
                "location": "marital_status",
                "age": "partner_requirement",
            }
            side_target = contextual_side_target_map.get(main_target, "")
        if not side_target:
            return {}

        prompt_label_map = {
            "occupation": "工作/做什么",
            "education": "学历/教育背景",
            "age": "年龄/年龄段",
            "location": "城市/常住地",
            "marital_status": "感情状态/婚况",
        }
        side_label_map = {
            "monthly_income": "月薪/收入区间",
            "partner_requirement": "择偶要求/更看重哪一点",
            "marital_status": "感情状态/婚况",
        }
        allow_bridge_side_target = (
            force_bridge_income_side_target
            and side_target == "monthly_income"
            and bool(bridge_context)
        )
        if not allow_bridge_side_target and not self.collection_policy.can_actively_ask(user_profile, side_target):
            return {}
        main_prompt_label = prompt_label_map.get(main_target, "")
        side_prompt_label = side_label_map.get(side_target, "")
        if not main_prompt_label or not side_prompt_label:
            return {}
        side_targets = [side_target]
        side_prompt_labels = [side_prompt_label]

        return {
            "context": bridge_context,
            "main_target": main_target,
            "side_targets": side_targets,
            "main_prompt_label": main_prompt_label,
            "side_prompt_labels": side_prompt_labels,
        }

    def _extract_profile_bridge_context(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
        turn_decision: TurnDecision,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """提取可用于桥接追问的本轮新增资料。"""
        if turn_decision.response_channel != "model":
            return {}
        if not turn_decision.ask_field:
            return {}

        message_count = int((conversation_context or {}).get("message_count", 0))
        if message_count > 3:
            return {}

        extracted = self._extract_turn_level_fields(user_message)
        if not extracted:
            extracted = {}
        if not extracted.get("marital_status"):
            message = str(user_message or "").strip()
            if re.search(r"(目前|现在)?一个人(生活|过|在)?", message) or "单着" in message:
                extracted["marital_status"] = "单身"
        if (
            turn_decision.ask_field == "occupation"
            and extracted.get("occupation")
            and not self.turn_understanding_service._is_low_quality_occupation_text(  # noqa: SLF001
                str(extracted.get("occupation") or "")
            )
        ):
            return {}
        if turn_decision.ask_field == "marital_status" and extracted.get("marital_status"):
            return {}

        bridge_bits: Dict[str, str] = {}
        location = str(extracted.get("location") or "").strip()
        marital_status = str(extracted.get("marital_status") or "").strip()
        occupation = str(extracted.get("occupation") or "").strip()
        education = str(extracted.get("education") or "").strip()
        if location:
            bridge_bits["城市"] = location
        if marital_status:
            bridge_bits["当前状态"] = marital_status
        if occupation:
            bridge_bits["工作"] = occupation
        if education:
            bridge_bits["学历"] = education
        return bridge_bits

    @staticmethod
    def _augment_prompt_for_profile_bridge_followup(prompt: str, bridge_instruction: str) -> str:
        return ProfileBridgePromptFormatter.prepend_instruction(prompt, bridge_instruction)

    @staticmethod
    def _extract_opening_intent_block(response: str) -> tuple[OpeningIntentSignal | None, str]:
        text = str(response or "")
        if not text:
            return None, ""
        match = re.search(r"<opening_intent>(.*?)</opening_intent>", text, flags=re.DOTALL)
        if not match:
            return None, text.strip()
        payload = match.group(1).strip()
        natural = (text[:match.start()] + text[match.end():]).strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return OpeningIntentSignal(parse_failed=True), natural

        intent = str(data.get("intent") or "").strip()
        secondary_intent = data.get("secondary_intent")
        secondary_intent = str(secondary_intent).strip() if secondary_intent else None
        confidence_raw = data.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        primary, secondary = ChatService._resolve_opening_intent_priority(intent, secondary_intent)
        return OpeningIntentSignal(
            intent=primary,
            confidence=confidence,
            secondary_intent=secondary,
            parse_failed=False,
        ), natural

    @staticmethod
    def _resolve_opening_intent_priority(intent: str, secondary_intent: Optional[str]) -> tuple[str, Optional[str]]:
        primary = str(intent or "").strip()
        secondary = str(secondary_intent or "").strip() or None
        if primary == "opening_mixed_intent" and secondary:
            primary = secondary
            secondary = None
        if not primary:
            return "", secondary
        if secondary and OPENING_INTENT_PRIORITY.get(secondary, 999) < OPENING_INTENT_PRIORITY.get(primary, 999):
            return secondary, primary
        return primary, secondary

    def _apply_opening_intent_signal_to_turn_decision(
        self,
        signal: Optional[OpeningIntentSignal],
        turn_decision: TurnDecision,
        *,
        user_message: str,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> None:
        if not signal or signal.parse_failed or signal.confidence < 0.6:
            return
        if signal.intent == "opening_greeting":
            turn_decision.intent = "opening_probe"
            turn_decision.primary_move = "answer_then_pause"
            turn_decision.ask_field = None
            turn_decision.prioritize_user_question = True
            turn_decision.allow_contact_target = False
            turn_decision.allow_medium_target = False
            turn_decision.followup_topic = None
        elif signal.intent in {"explicit_matchmaking_opening", "low_pressure_opening", "opening_light_consult"}:
            if self._opening_message_has_substantive_profile_content(user_message, understanding_result):
                return
            turn_decision.intent = "opening_self_intro"
            turn_decision.primary_move = "answer_then_pause"
            turn_decision.ask_field = None
            turn_decision.allow_contact_target = False
            turn_decision.allow_medium_target = False
            turn_decision.followup_topic = "opening_self_intro"
        elif signal.intent == "opening_faq":
            turn_decision.prioritize_user_question = True
            turn_decision.primary_move = "answer_then_pause"
            turn_decision.ask_field = None
            turn_decision.allow_contact_target = False
            turn_decision.allow_medium_target = False
        elif signal.intent in {"opening_boundary_or_contact_refusal", "opening_emotional_or_defensive", "opening_reverse_question"}:
            turn_decision.primary_move = "soft_hold"
            turn_decision.ask_field = None
            turn_decision.allow_contact_target = False
            turn_decision.allow_medium_target = False
            if signal.intent == "opening_boundary_or_contact_refusal":
                turn_decision.risk = "boundary"
        elif signal.intent == "opening_profile_provided":
            turn_decision.followup_topic = None
        elif signal.intent == "opening_spam_or_promo":
            turn_decision.primary_move = "soft_hold"
            turn_decision.ask_field = None
            turn_decision.allow_contact_target = False
            turn_decision.allow_medium_target = False

    def _enforce_opening_intent_consistency(
        self,
        response: str,
        signal: Optional[OpeningIntentSignal],
        *,
        user_message: str,
        seed_hint: str,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> str:
        text = str(response or "").strip()
        if not text or not signal or signal.parse_failed or signal.confidence < 0.6:
            return text
        if signal.intent == "opening_greeting":
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return self.greeting_service.get_opening_clarify_response(seed_hint=seed_hint)
        if signal.intent in {"explicit_matchmaking_opening", "low_pressure_opening", "opening_light_consult"}:
            if self._opening_message_has_substantive_profile_content(user_message, understanding_result):
                return text
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return self._build_opening_matchmaking_response(
                    user_message=user_message,
                    seed_hint=seed_hint,
                )
        if signal.intent == "opening_faq":
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                faq_response = self._get_priority_question_response(
                    user_message,
                    UserProfile(account_id="opening_faq_guard"),
                )
                if faq_response:
                    return faq_response
        if signal.intent in {"opening_boundary_or_contact_refusal", "opening_emotional_or_defensive", "opening_reverse_question"}:
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return self._get_boundary_pause_response(user_message)
        return text

    @staticmethod
    def _split_response_and_extract(response: str) -> tuple[str, str]:
        text = str(response or "")
        if not text:
            return "", ""
        match = re.search(r"(<extract>.*?</extract>)", text, flags=re.DOTALL)
        if not match:
            return text.strip(), ""
        natural = text[:match.start()].strip()
        extract_block = match.group(1).strip()
        return natural, extract_block

    def _ensure_short_answer_ack_transition(
        self,
        response: str,
        *,
        user_message: str,
        user_profile: Optional[UserProfile] = None,
    ) -> str:
        natural_response, extract_block = self._split_response_and_extract(response)
        if not natural_response:
            return response
        if not self._is_short_answer(user_message):
            return response

        ack = self.turn_understanding_service._build_lightweight_field_ack(user_message, user_profile)  # noqa: SLF001
        if not ack:
            return response

        text = self._safe_clean_response(natural_response)
        if not text:
            return response

        if self._response_already_acknowledges_short_answer(text, user_message, ack=ack):
            return response

        if "？" not in text and "?" not in text:
            return response

        merged = f"{ack} {text}".strip()
        if extract_block:
            return f"{merged}\n{extract_block}"
        return merged

    @staticmethod
    def _response_already_acknowledges_short_answer(text: str, user_message: str, *, ack: str = "") -> bool:
        return ChatServiceTextPolicyService.response_already_acknowledges_short_answer(
            text,
            user_message,
            ack=ack,
        )

    @staticmethod
    def _collapse_duplicate_ack_segments(response: str) -> str:
        return ChatServiceTextPolicyService.collapse_duplicate_ack_segments(response)

    @staticmethod
    def _is_divorce_status_complete_message(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        negative_patterns = [
            "没办完",
            "没有办完",
            "没办好",
            "没有办好",
            "没办妥",
            "没有办妥",
            "还没办好",
            "还没办完",
            "还没离干净",
            "手续没办完",
            "手续没有办完",
            "手续还在办",
            "还在办理",
            "办理中",
            "没离",
        ]
        if any(pattern in text for pattern in negative_patterns):
            return False
        normalized = (
            text.replace("离婚", "")
            .replace("手续", "")
            .replace("已经", "")
            .replace("现在", "")
            .replace("都", "")
            .replace("啦", "")
            .replace("了啊", "了")
            .replace("呢", "")
            .replace("呀", "")
            .replace("哈", "")
            .replace("帮", "")
            .strip()
        )
        keywords = [
            "有法院判决书",
            "法院判决书",
            "判决书",
            "有判决书",
            "有离婚证",
            "离婚证",
            "有调解书",
            "调解书",
            "办妥了",
            "办好了",
            "办了好了",
            "办理好了",
            "已办妥",
            "已办好",
            "已经办妥",
            "已经办好",
            "办完了",
            "办理完了",
            "办好了呀",
            "手续办了",
            "手续好了",
            "手续都办好了",
            "手续已经办好了",
            "都办好了",
            "都弄好了",
            "处理好了",
            "离干净了",
            "恢复单身",
            "现在是单身",
            "办妥",
            "办好",
            "办完",
        ]
        if any(keyword in text for keyword in keywords):
            return True

        compact = normalized.replace(" ", "")
        regex_patterns = [
            r"办[理\s]*好[了啦呀啊哈]*",
            r"办了好[了啦呀啊哈]*",
            r"办[妥完][了啦呀啊哈]*",
            r"都[弄办处][好完妥][了啦呀啊哈]*",
            r"恢复单身",
            r"离干净了",
            r"(法院判决书|判决书|离婚证|调解书)",
        ]
        return any(re.search(pattern, compact) for pattern in regex_patterns)

    @staticmethod
    def _is_divorce_status_incomplete_message(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        incomplete_patterns = [
            "没办完",
            "没有办完",
            "没办好",
            "没有办好",
            "没办妥",
            "没有办妥",
            "还没办好",
            "还没办完",
            "手续没办完",
            "手续没有办完",
            "手续还没办完",
            "手续还在办",
            "手续在办",
            "还在办手续",
            "还在办理",
            "办理中",
            "没离干净",
            "还没离干净",
            "分居中",
            "正在分居",
            "还没离",
        ]
        return any(pattern in text for pattern in incomplete_patterns)

    @staticmethod
    def _is_short_negative_reply(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        compact = re.sub(r"[，。！？!?~～、\s]+", "", text)
        return compact in {"没", "没有", "还没", "没呢", "没有呢", "还没有"}

    @staticmethod
    def _is_divorce_confirmation_question(last_response: str) -> bool:
        text = str(last_response or "").strip()
        if not text:
            return False
        if "离婚" not in text:
            return False
        return any(token in text for token in ("办妥", "办好", "办完", "处理妥当", "手续", "判决书", "离婚证", "调解书"))

    def _should_lock_divorce_confirmation(self, user_profile: UserProfile, user_message: str) -> bool:
        marital_status = str(getattr(user_profile, "marital_status", "") or "").strip()
        if "离异" not in marital_status or "办妥" in marital_status:
            return False
        if user_profile.divorce_confirmed or user_profile.conversation_ended:
            return False
        if self._is_divorce_status_complete_message(user_message):
            return False
        return True

    @staticmethod
    def _build_divorce_confirmation_response() -> str:
        return random.choice(DIVORCE_CONFIRMATION_PROMPT_VARIANTS)

    @staticmethod
    def _build_divorce_confirmation_cleared_response(next_field: str | None) -> str:
        normalized_field = None if next_field == "marital_status" else next_field
        variants = DIVORCE_CONFIRMED_ACK_VARIANTS.get(
            normalized_field or "",
            DIVORCE_CONFIRMED_ACK_VARIANTS["contact"],
        )
        return random.choice(variants)

    def _get_post_divorce_mainline_target(
        self,
        user_profile: UserProfile,
        user_message: str,
        message_count: int = 0,
    ) -> str | None:
        """离异手续确认完成后，本轮先回资料主线，不直接切联系方式。"""
        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            message_count=message_count,
            allow_contact_target=False,
        )
        if decision.main_target and decision.main_target != "marital_status":
            return decision.main_target

        for field in ("occupation", "education", "location", "monthly_income", "partner_requirement", "age", "sex"):
            if self.collection_policy.can_actively_ask(user_profile, field):
                return field
        return None

    async def _record_delivered_contact_ask_if_needed(
        self,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
    ) -> UserProfile:
        """
        只有当联系方式询问真实展示给用户时，才记一次有效询问。
        """
        if not ChatServiceResponseCleanupService.is_delivery_viable(final_response):
            return user_profile

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return user_profile

        updated = False
        if (
            action_value in {"ask_phone", "persuade_phone"}
            and ChatServiceContactTextService.response_mentions_phone_request(final_response)
        ):
            previous = user_profile.phone_ask_count
            self.contact_service.record_ask(user_profile, "phone")
            updated = user_profile.phone_ask_count != previous
        elif (
            action_value in {"ask_wechat", "persuade_wechat"}
            and ChatServiceContactTextService.response_mentions_wechat_request(final_response)
        ):
            previous = user_profile.wechat_ask_count
            self.contact_service.record_ask(user_profile, "wechat")
            updated = user_profile.wechat_ask_count != previous

        if updated:
            user_profile.contact = self.contact_service.get_status_display(user_profile)
            await self.user_service.save_user_profile(account_id, user_profile)
        return user_profile

    async def _process_collection_result(
        self,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        user_message: str,
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
        turn_id: Optional[int] = None,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> Dict[str, Any]:
        """处理收集结果"""
        last_response, collection_result, refreshed_user_profile = await self.collection_extraction_service.run_extraction(
            account_id=account_id,
            user_profile=user_profile,
            extracted_data=extracted_data,
            user_message=user_message,
            extraction_meta=extraction_meta,
            turn_id=turn_id,
            understanding_result=understanding_result,
        )
        return await self.collection_postprocess_service.process_after_extraction(
            account_id=account_id,
            user_profile=refreshed_user_profile,
            collection_result=collection_result,
            user_message=user_message,
            last_response=last_response,
            understanding_result=understanding_result,
        )

    async def _apply_confirmation_ai_fallback(
        self,
        extracted_data: Dict[str, Any],
        extraction_meta: Dict[str, Dict[str, Any]],
        *,
        user_message: str,
        last_response: str,
        user_profile: UserProfile,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        return await self.confirmation_fallback_service.apply_confirmation_ai_fallback(
            extracted_data,
            extraction_meta,
            user_message=user_message,
            last_response=last_response,
            user_profile=user_profile,
        )

    async def _handle_contact_validation(
        self,
        account_id: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        ai_response: str,
        user_message: str = "",
    ) -> str:
        return await self.contact_validation_flow_service.handle_contact_validation(
            account_id,
            user_profile,
            collection_result,
            ai_response,
            user_message,
        )

    async def _build_validation_feedback(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        invalid_value: Optional[str],
        error_info: Optional[Dict[str, Any]],
    ) -> str:
        return await self.validation_recovery_service.build_validation_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info=error_info,
        )

    async def _generate_validation_retry_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        invalid_value: Optional[str],
        error_info: Dict[str, Any],
    ) -> str:
        return await self.validation_recovery_service.generate_validation_retry_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info=error_info,
        )

    async def _generate_ai_ending_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        ending_info: Optional[Dict[str, Any]],
        fallback_response: str = "",
    ) -> str:
        return await self.ending_generation_service.generate_ai_ending_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            ending_info=ending_info,
            fallback_response=fallback_response,
        )

    def _safe_clean_response(self, response: str) -> str:
        """Minimal cleanup only. No semantic rewrite."""
        import re

        text = re.sub(r"<extract>.*?</extract>", "", str(response or ""), flags=re.DOTALL).strip()
        text = re.sub(r"^(?:了|啦|呀|呢|哈|啊)[。．]\s*", "", text)
        text = re.sub(r"([。！？!?])\s*(哈哈，原来|原来|这样的话|所以说)\s*$", r"\1", text)
        text = re.sub(r"^(哈哈，原来|原来|这样的话|所以说)\s*$", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = ChatServiceResponseCleanupService.strip_broken_edge_fragments(text)
        return text

    def _should_count_soft_sex_confirmation_in_opening(
        self,
        *,
        user_message: str,
        user_profile: UserProfile,
    ) -> bool:
        if str(getattr(user_profile, "sex", "") or "").strip():
            return False
        preference = str(
            getattr(user_profile, "partner_gender_preference", "")
            or self.turn_understanding_service._extract_partner_gender_preference(user_message)  # noqa: SLF001
            or ""
        ).strip()
        return preference in {"男", "女"}

    def _enforce_question_budget_guard(
        self,
        response: str,
        *,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: Optional[TurnDecision],
    ) -> str:
        text = str(response or "").strip()
        if not text or not turn_decision:
            return text
        if str(getattr(turn_decision, "response_channel", "model") or "model") != "model":
            return text
        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        soft_sex_confirmation_in_opening = False
        if self._looks_like_broken_followup_fragment(text, ask_field=ask_field):
            logger.info(
                "[问题预算护栏] 命中残句保护，直接回退到稳定追问: ask_field=%s",
                ask_field or "-",
            )
            fallback = self._build_budget_guard_fallback_response(
                user_profile=user_profile,
                user_message=user_message,
                ask_field=ask_field,
                allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False)),
            )
            if fallback:
                return self._build_style_preserving_followup_response(
                    original_response=text,
                    fallback_response=fallback,
                )

        asked_fields = self._detect_asked_fields_in_response(text)
        asked_fields |= self._detect_all_questioned_fields_in_response(text)
        allow_fields: set[str] = set()
        if ask_field:
            allow_fields.add(ask_field)
        if ask_field and ask_field != "contact" and getattr(turn_decision, "allow_medium_target", False):
            try:
                policy_decision = self.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=getattr(turn_decision, "allow_contact_target", False),
                    allow_medium_target=True,
                    prioritize_user_question=getattr(turn_decision, "prioritize_user_question", False),
                    primary_move=getattr(turn_decision, "primary_move", "ack_and_ask"),
                )
                if str(getattr(policy_decision, "main_target", "") or "").strip() == ask_field:
                    side_target = str(getattr(policy_decision, "side_target", "") or "").strip()
                    if (
                        side_target
                        and self._is_allowed_main_side_pair(ask_field, side_target)
                    ):
                        allow_fields.add(side_target)
            except Exception:
                pass

        soft_sex_confirmation_in_opening = self._should_count_soft_sex_confirmation_in_opening(
            user_message=user_message,
            user_profile=user_profile,
        )
        if not soft_sex_confirmation_in_opening:
            soft_sex_confirmation_in_opening = bool(
                re.search(r"(你应该是|看着像|听着像).{0,6}(男生|女生).{0,3}(对吧|吧)", text)
            )
        if soft_sex_confirmation_in_opening:
            allow_fields.add("sex")
            if len(allow_fields) >= 2 and "monthly_income" in allow_fields:
                allow_fields.discard("monthly_income")

        repeated_question_fields = {
            field
            for field, count in self._count_questioned_fields_in_response(text).items()
            if count > 1
        }
        primary_followup_field = self._resolve_primary_followup_field_from_response(
            response=text,
            planned_ask_field=ask_field,
        )
        if primary_followup_field and repeated_question_fields:
            logger.info(
                "[问题预算护栏] 命中重复追问，回退到单主问题稳定追问: ask_field=%s repeated=%s",
                primary_followup_field,
                sorted(repeated_question_fields),
            )
            fallback = self._build_budget_guard_fallback_response(
                user_profile=user_profile,
                user_message=user_message,
                ask_field=primary_followup_field,
                allow_medium_target=False,
            )
            if fallback:
                return fallback

        stage = str(getattr(turn_decision, "stage", "") or "").strip()
        explicit_question_segments = self._extract_explicit_question_segments(text)
        if (
            primary_followup_field
            and len(explicit_question_segments) > 1
            and (
                stage == "opening"
                or self._looks_like_dense_intro_message_for_budget_guard(
                    user_profile=user_profile,
                    user_message=user_message,
                )
            )
        ):
            logger.info(
                "[问题预算护栏] dense_intro/opening轮多问并列，回退到单主问题稳定追问: ask_field=%s question_segments=%s",
                primary_followup_field,
                len(explicit_question_segments),
            )
            fallback = self._build_budget_guard_fallback_response(
                user_profile=user_profile,
                user_message=user_message,
                ask_field=primary_followup_field,
                allow_medium_target=False,
            )
            if fallback:
                return fallback

        if len(asked_fields) <= 2:
            if ask_field and getattr(turn_decision, "allow_medium_target", False):
                for candidate in sorted(asked_fields - {ask_field}):
                    if soft_sex_confirmation_in_opening and candidate == "monthly_income":
                        continue
                    if self._is_allowed_main_side_pair(ask_field, candidate):
                        allow_fields.add(candidate)
            if not asked_fields:
                return text
            if not allow_fields or asked_fields <= allow_fields:
                return text

        disallowed_fields = asked_fields - allow_fields
        updated = text
        for field in sorted(disallowed_fields):
            updated = ChatServiceResponseCleanupService.strip_question_clause_for_field(updated, field)

        updated = self._safe_clean_response(updated)
        updated_asked_fields = self._detect_asked_fields_in_response(updated) | self._detect_all_questioned_fields_in_response(updated)
        if disallowed_fields and (updated_asked_fields & disallowed_fields):
            logger.info(
                "[问题预算护栏] 裁剪后仍残留非法问题，回退到稳定追问: ask_field=%s disallowed=%s",
                ask_field or "-",
                sorted(disallowed_fields),
            )
            fallback = self._build_budget_guard_fallback_response(
                user_profile=user_profile,
                user_message=user_message,
                ask_field=ask_field,
                allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False))
                and not soft_sex_confirmation_in_opening,
            )
            if fallback:
                return self._build_style_preserving_followup_response(
                    original_response=updated or text,
                    fallback_response=fallback,
                )
        if len(updated_asked_fields) < len(asked_fields):
            if self._looks_like_broken_followup_fragment(updated, ask_field=ask_field):
                logger.info(
                    "[问题预算护栏] 裁剪后命中残句保护，回退到稳定追问: ask_field=%s",
                    ask_field or "-",
                )
                fallback = self._build_budget_guard_fallback_response(
                    user_profile=user_profile,
                    user_message=user_message,
                    ask_field=ask_field,
                    allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False))
                    and not soft_sex_confirmation_in_opening,
                )
                return self._build_style_preserving_followup_response(
                    original_response=updated or text,
                    fallback_response=fallback,
                )
            logger.info(
                "[问题预算护栏] 单轮问题数超限，fields=%s allow=%s trimmed_to=%s",
                sorted(asked_fields),
                sorted(allow_fields),
                sorted(updated_asked_fields),
            )
            return updated
        if updated != text:
            return updated
        if self._looks_like_broken_followup_fragment(updated, ask_field=ask_field):
            logger.info(
                "[问题预算护栏] 裁剪未减少问题数但命中残句保护，回退到稳定追问: ask_field=%s",
                ask_field or "-",
            )
            fallback = self._build_budget_guard_fallback_response(
                user_profile=user_profile,
                user_message=user_message,
                ask_field=ask_field,
                allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False))
                and not soft_sex_confirmation_in_opening,
            )
            return self._build_style_preserving_followup_response(
                original_response=updated or text,
                fallback_response=fallback,
            )
        return text

    def _build_budget_guard_fallback_response(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        ask_field: str,
        allow_medium_target: bool,
    ) -> str:
        main_target = str(ask_field or "").strip()
        if not main_target:
            main_target = str(
                self._select_next_progress_target(user_profile, user_message=user_message) or ""
            ).strip()
        preferred_side_target = None
        if main_target and main_target != "contact" and allow_medium_target:
            try:
                policy_decision = self.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=False,
                    allow_medium_target=True,
                    prioritize_user_question=False,
                    primary_move="ack_and_ask",
                )
                if str(getattr(policy_decision, "main_target", "") or "").strip() == main_target:
                    candidate_side_target = str(getattr(policy_decision, "side_target", "") or "").strip()
                    if candidate_side_target and self.collection_policy.can_actively_ask(user_profile, candidate_side_target):
                        preferred_side_target = candidate_side_target
            except Exception:
                preferred_side_target = None

        direct_followup = ""
        if main_target:
            direct_followup = self._build_followup_seed_for_model_rewrite(
                main_target,
                user_profile,
                user_message=user_message,
            ).strip()
            if direct_followup and not preferred_side_target:
                return direct_followup

        fallback = self._build_interleaving_seed_for_model_rewrite(
            user_profile,
            user_message,
            main_target=main_target or None,
            preferred_side_target=preferred_side_target,
            allow_medium_target=allow_medium_target,
        ).strip()
        if (
            fallback
            and main_target
            and self._looks_like_low_information_model_reply(fallback)
            and direct_followup
        ):
            return direct_followup
        if fallback:
            return fallback
        if direct_followup:
            return direct_followup
        return ""

    def _build_style_preserving_followup_response(
        self,
        *,
        original_response: str,
        fallback_response: str,
    ) -> str:
        fallback = str(fallback_response or "").strip()
        if not fallback:
            return fallback

        prefix = self._extract_style_preserving_followup_prefix(original_response)
        if not prefix:
            return fallback
        return f"{prefix} {fallback}".strip()

    def _extract_style_preserving_followup_prefix(self, response: str) -> str:
        text = self._safe_clean_response(response)
        if not text:
            return ""

        if "？" in text or "?" in text:
            text = re.split(r"[？?]", text, maxsplit=1)[0].strip()

        text = re.sub(
            r"(?:[，,、]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
            "",
            text,
        ).strip()
        text = re.sub(
            r"(?:[。！？!?]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
            "",
            text,
        ).strip()
        text = re.sub(
            r"([。！？!?])\s*(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
            r"\1",
            text,
        ).strip()

        if re.search(r"(对吧|是不是|是吧|好吗|行吗|吗|么|呢|呀|嘛)\s*$", text):
            parts = [part.strip() for part in re.split(r"[，,、]", text) if part.strip()]
            text = "，".join(parts[:-1]).strip() if len(parts) > 1 else ""
            text = re.sub(
                r"(?:[，,、]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
                "",
                text,
            ).strip()
            text = re.sub(
                r"(?:[。！？!?]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
                "",
                text,
            ).strip()

        while text and (self._detect_asked_fields_in_response(text) or self._detect_all_questioned_fields_in_response(text)):
            shortened = re.sub(r"(?:[，,、。！？!?]\s*[^，,、。！？!?]*)$", "", text).strip()
            if not shortened or shortened == text:
                text = ""
                break
            text = shortened
            text = re.sub(
                r"(?:[，,、]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
                "",
                text,
            ).strip()
            text = re.sub(
                r"(?:[。！？!?]\s*)?(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
                "",
                text,
            ).strip()
            text = re.sub(
                r"([。！？!?])\s*(?:对了|另外|顺便|还有|然后|那就|那|所以|这样的话|说到这儿|说到这里)\s*$",
                r"\1",
                text,
            ).strip()

        text = ChatServiceResponseCleanupService.strip_broken_edge_fragments(text)
        text = re.sub(r"[，,、~～]\s*$", "", text).strip()
        if not text:
            return ""
        if self._looks_like_broken_followup_fragment(text):
            return ""
        if self._looks_like_speculative_followup_prefix(text):
            return ""
        if self._detect_asked_fields_in_response(text) or self._detect_all_questioned_fields_in_response(text):
            return ""
        if self._looks_like_low_information_model_reply(text):
            return ""
        if not re.search(r"[。！？!?]$", text):
            text = f"{text}。"
        return text

    @staticmethod
    def _looks_like_speculative_followup_prefix(response: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return False
        speculative_patterns = (
            r"应该还挺[^。！？!?，,、]*",
            r"应该[^。！？!?，,、]*(不错|可以|稳定|合适|还行)",
            r"(看起来|感觉|估计|大概)[^。！？!?，,、]*(不错|可以|稳定|合适|还行)",
        )
        return any(re.search(pattern, text) for pattern in speculative_patterns)

    @staticmethod
    def _looks_like_broken_followup_fragment(response: str, *, ask_field: str = "") -> bool:
        text = str(response or "").strip()
        if not text:
            return True
        if re.search(r"[。！？!?？]$", text):
            return False
        if "？" in text or "?" in text:
            return False
        broken_prefix_patterns = (
            r"看来你",
            r"我记下啦?$",
            r"我先记下啦?$",
            r"你找对象",
            r"后面有合适",
            r"联系你也更方便",
            r"那你",
            r"大概的$",
            r"顺便的$",
            r"另外的$",
        )
        if any(re.search(pattern, text) for pattern in broken_prefix_patterns):
            return True
        if re.search(r"(大概的|顺便|另外|还有|以及)\s*$", text):
            return True
        if ask_field and len(text) <= 10:
            return True
        return False

    def _legacy_clean_response(self, response: str) -> str:
        """Legacy cleanup path. Includes semantic rewrites kept for rollback compatibility."""
        text = self._safe_clean_response(response)
        text = ChatServiceResponseCleanupService.normalize_redundant_confirmation_phrasing(text)
        text = ChatServiceResponseCleanupService.soften_awkward_age_question(text)
        text = ChatServiceResponseCleanupService.compress_multi_action_response(text)
        return text

    def _build_terminal_response(
        self,
        ending_info: Optional[Dict[str, Any]],
        user_profile: UserProfile,
    ) -> Optional[str]:
        """为强制收尾场景生成稳定回复，避免模型继续推进联系方式。"""
        scenario = (ending_info or {}).get("scenario")
        preset_response = str((ending_info or {}).get("response") or "").strip()
        if preset_response:
            return preset_response

        if scenario == "both_rejected":
            return self._get_both_rejected_ending_response()
        if scenario == "normal_complete":
            if self._can_end_with_contact_completion(user_profile):
                return self._get_contact_completion_ending_response(user_profile)
            if self._can_end_without_contact(user_profile):
                return self._get_no_contact_completion_response()
        if scenario == "already_ended":
            return self._get_already_ended_response()

        if self.contact_service.should_end_conversation(user_profile):
            return self._get_both_rejected_ending_response()

        if user_profile.conversation_ended and user_profile.rejected_phone and user_profile.rejected_wechat:
            return self._get_both_rejected_ending_response()
        return None

    def _get_already_ended_response(self) -> str:
        return self.ending_state_service.get_already_ended_response()

    def _get_both_rejected_ending_response(self) -> str:
        return self.ending_state_service.get_both_rejected_ending_response()

    @staticmethod
    def _has_any_contact(user_profile: UserProfile) -> bool:
        return ChatServiceEndingStateService.has_any_contact(user_profile)

    def _is_profile_collection_complete_or_exhausted(self, user_profile: UserProfile) -> bool:
        return self.ending_state_service.is_profile_collection_complete_or_exhausted(user_profile)

    def _can_end_with_contact_completion(self, user_profile: UserProfile) -> bool:
        return self.ending_state_service.can_end_with_contact_completion(user_profile)

    def _can_end_without_contact(self, user_profile: UserProfile) -> bool:
        return self.ending_state_service.can_end_without_contact(user_profile)

    def _get_no_contact_completion_response(self) -> str:
        return self.ending_state_service.get_no_contact_completion_response()

    def _get_contact_completion_ending_response(self, user_profile: UserProfile) -> str:
        return self.ending_state_service.get_contact_completion_ending_response(user_profile)

    def _should_allow_interleaving_followup(
        self,
        user_profile: UserProfile,
        main_target: Optional[str],
        preferred_side_target: Optional[str],
        *,
        allow_medium_target: bool,
    ) -> bool:
        if not allow_medium_target or not main_target or not preferred_side_target:
            return False
        if not self._is_allowed_main_side_pair(main_target, preferred_side_target):
            return False
        return True

    def _get_contact_terminal_or_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        return self.contact_resume_service.get_contact_terminal_or_resume_response(
            user_profile,
            user_message,
        )

    @staticmethod
    def _contains_contact_push_markers(response: str) -> bool:
        return ChatServiceTextPolicyService.contains_contact_push_markers(response)

    def _enforce_terminal_response_policy(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        ended / 双拒场景下，禁止继续索要联系方式或抛出新问题。
        """
        ending_info = (collection_result or {}).get("ending_info") if collection_result else None
        forced_terminal = self._build_terminal_response(ending_info, user_profile)
        if forced_terminal is not None:
            return forced_terminal

        if not response:
            return response

        if not user_profile.conversation_ended:
            return response

        if self._contains_contact_push_markers(response) or "？" in response or "?" in response:
            return self._get_already_ended_response()
        return response

    def _has_active_contact_context(
        self,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> bool:
        return self.contact_context_service.has_active_contact_context(
            user_profile,
            collection_result=collection_result,
            user_message=user_message,
            understanding_result=understanding_result,
        )

    def _apply_field_ask_guard(
        self,
        user_profile: UserProfile,
        response: str,
        *,
        user_message: str = "",
        allow_medium_target: bool = True,
    ) -> str:
        """
        策略层硬约束：冷却字段和已问满字段不允许继续追问。
        """
        if not response:
            return response

        blocked_fields = set()
        for field in ASK_GUARD_MANAGED_FIELDS | ASK_GUARD_MEDIUM_FIELDS | ASK_GUARD_LOW_PRIORITY_FIELDS:
            raw_ask_count = int((getattr(user_profile, "field_ask_count", {}) or {}).get(field, 0) or 0)
            ask_limit = int(self.collection_policy.ASK_LIMITS.get(field, 0) or 0)
            if user_profile.collection_progress.get(field, False):
                blocked_fields.add(field)
                continue
            if user_profile.skipped_fields.get(field, False):
                blocked_fields.add(field)
                continue
            if ask_limit > 0 and raw_ask_count >= ask_limit:
                blocked_fields.add(field)
                continue
            if field in ASK_GUARD_LOW_PRIORITY_FIELDS:
                blocked_fields.add(field)
                continue
            if field in ASK_GUARD_MEDIUM_FIELDS:
                if not allow_medium_target or not self.collection_policy.can_actively_ask(user_profile, field):
                    blocked_fields.add(field)
                continue
            if not self.collection_policy.can_actively_ask(user_profile, field):
                blocked_fields.add(field)

        # Phase 1 & 2: 偏好类去重 guard - 使用策略层统一判断
        if self.collection_policy.should_block_preference_ask(user_profile, ""):  # noqa: SLF001
            blocked_fields.add("partner_requirement")

        if not blocked_fields:
            return response

        field_keywords = get_field_keywords()
        blocked_keywords = {
            keyword
            for field in blocked_fields
            for keyword in field_keywords.get(field, [])
            if keyword
        }
        # Phase 1 & 2: 偏好类去重 guard - 扩展泛化偏好问题关键词
        if self.collection_policy.should_block_preference_ask(user_profile, ""):  # noqa: SLF001
            blocked_keywords.update({
                "最看重哪一点",
                "最在意哪一点",
                "更在意哪几点",
                "最看重的匹配条件",
                "最看重的匹配点",
                "最在意的匹配点",
                "你更看重对方哪几点",
                "你最在意同城",
                # Phase 2: 新增扩展关键词
                "按这个方向帮你筛",
                "按这个优先推进",
                "我照这个方向",
                "说一个最在意的匹配点",
                "先说一个最在意",
                "你先告诉我你最看重",
                "我们可以先说一个",
                "会更看重哪个",
                "你会更偏哪边",
                "先顺手说说",
                "你最看重哪一点，可以先顺手说说",
                "你对另一半大概有什么要求",
                "你想找个什么样的",
            })

        asked_fields = self._detect_asked_fields_in_response(response)
        current_core_target = self.collection_policy.get_main_target(
            user_profile,
            can_enter_contact=False,
            allow_contact_target=False,
        )
        if current_core_target in blocked_fields:
            current_core_target = next(
                (
                    field
                    for field in self.collection_policy._get_priority_order(user_profile)  # noqa: SLF001
                    if field not in blocked_fields
                    and field in ASK_GUARD_CORE_FIELDS
                    and self.collection_policy.can_actively_ask(user_profile, field)
                ),
                None,
            )
        if (
            current_core_target in ASK_GUARD_CORE_FIELDS
            and asked_fields
            and (asked_fields & ASK_GUARD_MEDIUM_FIELDS)
            and current_core_target not in asked_fields
        ):
            return self._build_followup_seed_for_model_rewrite(current_core_target, user_profile, user_message=user_message)

        deterministic_fields = self._extract_turn_level_fields(user_message)
        user_supplied_fields = {field for field in deterministic_fields if field in asked_fields}
        if user_supplied_fields and (
            all(field in blocked_fields for field in user_supplied_fields)
            or all(user_profile.collection_progress.get(field, False) for field in user_supplied_fields)
        ):
            if all(
                self.collection_policy.is_collected(user_profile, field)
                for field in self.collection_policy.CORE_CONTACT_FIELDS
            ):
                return self._build_followup_seed_for_model_rewrite("contact", user_profile, user_message=user_message)
            if self.collection_policy.can_enter_contact(user_profile):
                return self._build_followup_seed_for_model_rewrite("contact", user_profile, user_message=user_message)
            if current_core_target:
                return self._build_followup_seed_for_model_rewrite(current_core_target, user_profile, user_message=user_message)
            return random.choice(NO_REPEAT_FIELD_VARIANTS)

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
        if all(
            self.collection_policy.is_collected(user_profile, field)
            for field in self.collection_policy.CORE_CONTACT_FIELDS
        ):
            return self._build_followup_seed_for_model_rewrite("contact", user_profile, user_message=user_message)
        if self.collection_policy.can_enter_contact(user_profile):
            return self._build_followup_seed_for_model_rewrite("contact", user_profile, user_message=user_message)
        if current_core_target:
            return self._build_followup_seed_for_model_rewrite(current_core_target, user_profile, user_message=user_message)
        return ""


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
            r'(?:微信|vx|wx|weixin)[^a-zA-Z0-9_-]*(?:就是手机号)?([a-zA-Z][a-zA-Z0-9_-]{4,19}|1[3-9]\d{9}|[5-9]\d{7})\b',
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

        compact_message = re.sub(r"\s+", "", message)

        def _looks_like_profile_intake(text: str) -> bool:
            profile_markers = ("岁", "cm", "厘米", "kg", "斤", "本科", "大专", "硕士", "博士", "单身", "离异", "男", "女")
            profile_hits = sum(1 for marker in profile_markers if marker in text)
            return profile_hits >= 2

        # 电话流程：只在“明显在留联系方式”的消息里兜底推断，避免把年龄/身高/体重数字串误判成电话。
        if next_action in {"ask_phone", "persuade_phone"}:
            has_phone_marker = bool(re.search(r"(电话|手机|手机号|号码|联系)", message))
            compact_digits_only = bool(re.fullmatch(r"(?:\+?86)?[\d\s-]{7,17}", message))
            if not has_phone_marker and not compact_digits_only:
                return None, None
            if _looks_like_profile_intake(message):
                return None, None

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
            if _looks_like_profile_intake(compact_message):
                return None, None
            if re.search(r"[a-z]", cleaned) and re.search(r"\d", cleaned):
                return cleaned, "wechat"
            explicit_id_match = re.search(r"\b(?:wx|vx|weixin)[:：\s]*([a-z][a-z0-9_-]{4,19})\b", lowered)
            if explicit_id_match:
                return explicit_id_match.group(1), "wechat"
            # 仅出现“微信”意向词（例如“用微信联系吧”）不应当作“已提供微信号”。
            if re.match(r"^[a-z][a-z0-9_-]{4,19}$", cleaned):
                return cleaned, "wechat"

        return None, None

    def _looks_like_contact_clarification_in_context(
        self,
        user_message: str,
        user_profile: UserProfile,
        *,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        if not self._has_active_contact_context(
            user_profile,
            user_message=message,
            understanding_result=understanding_result,
        ):
            return False
        if self._looks_like_contact_value(message):
            return True
        understanding_turn_type = str(getattr(understanding_result, "primary_turn_type", "") or "").strip()
        understanding_slots = set(self._effective_resolved_slots(understanding_result).keys())
        if understanding_turn_type == "contact_answer" or bool({"phone", "wechat"} & understanding_slots):
            return True
        if self.turn_understanding_service._extract_bare_contact_candidate(message):  # noqa: SLF001
            return True
        contact_retry_markers = (
            "微信", "微信号", "电话", "手机号", "号码", "联系",
            "看不懂", "没看懂", "没太看懂", "为什么看不懂", "为啥看不懂",
        )
        return any(marker in message for marker in contact_retry_markers)

    def _extract_turn_level_fields(
        self,
        user_message: str,
        *,
        understanding_result: TurnUnderstandingResult | None = None,
        last_response: str = "",
    ) -> Dict[str, Any]:
        """统一单轮字段读取入口，优先消费 unified understanding，缺失时才回退规则提取。"""
        extracted: Dict[str, Any] = {}

        if understanding_result is not None:
            extracted.update(self._effective_resolved_slots(understanding_result))
            raw_resolved_slots = dict(getattr(understanding_result, "resolved_slots", {}) or {})
            for field_name, field_value in raw_resolved_slots.items():
                normalized_field = str(field_name or "").strip()
                if not normalized_field or normalized_field in extracted:
                    continue
                if field_value in (None, ""):
                    continue
                if self._should_use_raw_understanding_fallback_field(
                    field_name=normalized_field,
                    user_message=user_message,
                ):
                    extracted[normalized_field] = field_value
            derivations = dict(getattr(understanding_result, "field_derivations", {}) or {})
            for field_name, field_value in derivations.items():
                extracted.setdefault(field_name, field_value)
            if self._should_merge_non_ai_understanding_fallback(understanding_result):
                deterministic = dict(self.turn_understanding_service._extract_deterministic_profile_fields(user_message))  # noqa: SLF001
                deterministic = self.turn_understanding_service._apply_extraction_guards(  # noqa: SLF001
                    deterministic,
                    user_message,
                    last_response=last_response,
                )
                for field_name, field_value in deterministic.items():
                    if field_value in (None, ""):
                        continue
                    extracted.setdefault(field_name, field_value)
                extraction_service = getattr(self, "extraction_service", None)
                if (
                    "partner_requirement" not in extracted
                    and extraction_service is not None
                    and hasattr(extraction_service, "_resolve_partner_requirement_from_message")
                ):
                    partner_requirement = str(
                        extraction_service._resolve_partner_requirement_from_message(  # noqa: SLF001
                            user_message,
                            allow_legacy_fallback=True,
                            prefer_structured=True,
                        )
                        or ""
                    ).strip()
                    if partner_requirement:
                        extracted["partner_requirement"] = partner_requirement
                if "partner_gender_preference" not in extracted:
                    partner_gender = self.turn_understanding_service._extract_partner_gender_preference(user_message)  # noqa: SLF001
                    if partner_gender:
                        extracted["partner_gender_preference"] = partner_gender
            return extracted

        deterministic = dict(self.turn_understanding_service._extract_deterministic_profile_fields(user_message))  # noqa: SLF001
        return self.turn_understanding_service._apply_extraction_guards(  # noqa: SLF001
            deterministic,
            user_message,
            last_response=last_response,
        )

    def _should_use_raw_understanding_fallback_field(
        self,
        *,
        field_name: str,
        user_message: str,
    ) -> bool:
        if field_name not in {"age", "age_label"}:
            return False
        checker = getattr(self.turn_understanding_service, "_message_explicitly_answers_field", None)  # noqa: SLF001
        if callable(checker):
            try:
                return bool(checker("age", str(user_message or "")))
            except Exception:  # noqa: BLE001
                return False
        return bool(re.search(r"(\d{1,2}岁|(?:19|20)\d{2}年|\d{2}后|\d{2}年)", str(user_message or "")))

    @staticmethod
    def _should_merge_non_ai_understanding_fallback(understanding_result: TurnUnderstandingResult | None) -> bool:
        if understanding_result is None:
            return False
        semantic_frame = getattr(understanding_result, "semantic_frame", None)
        source = str(getattr(semantic_frame, "source", "") or "").strip()
        if source == "ai_structured_extraction":
            return False
        return source in {"hybrid_semantic_projection", "legacy_projection"}

    @staticmethod
    def _canonicalize_no_reask_field(field_name: str) -> str:
        field = str(field_name or "").strip()
        if field in {"age_label"}:
            return "age"
        if field in {"phone", "wechat"}:
            return "contact"
        if field == "partner_gender_preference" or field.startswith("partner_pref_"):
            return "partner_requirement"
        return field

    @classmethod
    def _is_explicit_no_reask_observation(cls, *, user_message: str, observation: Any) -> bool:
        field_name = cls._canonicalize_no_reask_field(str(getattr(observation, "field", "") or "").strip())
        scope = str(getattr(observation, "scope", "") or "").strip()
        evidence_text = str(getattr(observation, "evidence_text", "") or "").strip()
        normalized_value = str(getattr(observation, "normalized_value", "") or "").strip()
        source = str(getattr(observation, "source", "") or "").strip()
        message = str(user_message or "")

        if scope not in {"self", "contact", "partner"}:
            return False
        if field_name == "contact":
            return scope == "contact" and bool(normalized_value or evidence_text)
        if field_name == "partner_requirement":
            return scope == "partner" and bool(normalized_value or evidence_text)
        if field_name == "age":
            pattern = r"((?:19|20)\d{2}年|\d{2}年(?:的)?|\d{2}后|(?:今年)?\d{1,2}岁)"
            return bool(re.search(pattern, evidence_text or normalized_value or message))
        if field_name == "sex":
            return bool(
                scope == "self"
                and (
                    source.endswith("explicit_self_marker")
                    or re.search(r"(女生|男生|女的|男的|我是女|我是男|本人女|本人男)", evidence_text or message)
                )
            )
        if field_name == "marital_status":
            return bool(re.search(r"(未婚|单身|离异|已婚|感情状态)", evidence_text or normalized_value or message))
        if field_name == "monthly_income":
            return bool(re.search(r"(收入|月薪|年薪|年入|年新)", evidence_text or normalized_value or message))
        return bool(normalized_value or evidence_text)

    def _extract_no_reask_fields(
        self,
        *,
        user_message: str,
        understanding_result: TurnUnderstandingResult | None,
    ) -> list[str]:
        semantic_frame = getattr(understanding_result, "semantic_frame", None) if understanding_result is not None else None
        if semantic_frame is None:
            return []
        fields: list[str] = []
        for observation in list(getattr(semantic_frame, "field_observations", []) or []):
            if not self._is_explicit_no_reask_observation(user_message=user_message, observation=observation):
                continue
            field_name = self._canonicalize_no_reask_field(str(getattr(observation, "field", "") or "").strip())
            if field_name:
                fields.append(field_name)
        ordered_unique: list[str] = []
        seen: set[str] = set()
        for field_name in fields:
            if field_name in seen:
                continue
            seen.add(field_name)
            ordered_unique.append(field_name)
        return ordered_unique

    def _build_last_semantic_summary_payload(
        self,
        *,
        user_message: str,
        understanding_result: TurnUnderstandingResult | None,
    ) -> Dict[str, Any]:
        semantic_frame = getattr(understanding_result, "semantic_frame", None) if understanding_result is not None else None
        persistence_plan = getattr(understanding_result, "persistence_plan", None) if understanding_result is not None else None
        if semantic_frame is None:
            return {}
        turn_mode = "default"
        soft_profile_summary = ""
        partner_summary = ""
        for note in list(getattr(understanding_result, "notes", []) or []):
            clean_note = str(note or "").strip()
            if clean_note.startswith("turn_mode="):
                turn_mode = clean_note.split("=", 1)[1].strip() or "default"
                break
        for note in list(getattr(semantic_frame, "notes", []) or []):
            clean_note = str(note or "").strip()
            if clean_note.startswith("soft_profile_summary="):
                soft_profile_summary = clean_note.split("=", 1)[1].strip()
            elif clean_note.startswith("partner_summary="):
                partner_summary = clean_note.split("=", 1)[1].strip()
        return {
            "primary_domain": getattr(semantic_frame, "primary_domain", None),
            "acts": list(getattr(semantic_frame, "acts", []) or []),
            "user_questions": [
                str(getattr(item, "topic", "") or "").strip()
                for item in list(getattr(semantic_frame, "user_questions", []) or [])
                if str(getattr(item, "topic", "") or "").strip()
            ],
            "observed_fields": [
                str(getattr(item, "field", "") or "").strip()
                for item in list(getattr(semantic_frame, "field_observations", []) or [])
                if str(getattr(item, "field", "") or "").strip()
            ],
            "pending_fields": [
                str(getattr(item, "field", "") or "").strip()
                for item in list(getattr(persistence_plan, "pending_fields", []) or [])
                if str(getattr(item, "field", "") or "").strip()
            ],
            "resume_target": getattr(persistence_plan, "next_resume_target", None) if persistence_plan is not None else None,
            "no_reask_fields": self._extract_no_reask_fields(
                user_message=user_message,
                understanding_result=understanding_result,
            ),
            "turn_mode": turn_mode,
            "soft_profile_summary": soft_profile_summary,
            "partner_summary": partner_summary,
        }

    def _build_shadow_profile_for_decision(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        last_response: str = "",
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> UserProfile:
        """
        基于用户当前输入生成只用于“本轮决策/问句生成”的临时画像副本。

        目的：
        - 让决策器看到“用户这句话说完之后”的最新状态
        - 不直接改真实 profile，不影响正式落库
        """
        shadow_profile = user_profile.model_copy(deep=True)
        if understanding_result is not None:
            semantic_summary_payload = self._build_last_semantic_summary_payload(
                user_message=user_message,
                understanding_result=understanding_result,
            )
            if semantic_summary_payload:
                shadow_profile.set_last_semantic_summary(semantic_summary_payload)
        extracted = self._extract_turn_level_fields(
            user_message,
            understanding_result=understanding_result,
            last_response=last_response,
        )
        if not extracted:
            return shadow_profile

        for field, value in extracted.items():
            if value in (None, ""):
                continue
            if field == "age_label":
                age_label = str(value).strip()
                shadow_profile.age_label = age_label
                if re.search(r"^\d{2}后$", age_label):
                    shadow_profile.pending_birth_year_bucket = age_label
                    shadow_profile.birth_year_confirmation_closed = False
                    shadow_profile.collection_progress["age"] = False
                elif re.search(r"^(\d{2}|19\d{2}|20\d{2})年$", age_label):
                    shadow_profile.pending_birth_year_bucket = None
                    shadow_profile.birth_year_confirmation_closed = False
                    shadow_profile.collection_progress["age"] = True
                continue
            if hasattr(shadow_profile, field):
                shadow_profile.update_field(field, value)
                if field in shadow_profile.collection_progress:
                    shadow_profile.collection_progress[field] = True

        age_label = str(extracted.get("age_label") or "").strip()
        has_bucket_only_age = bool(re.search(r"^\d{2}后$", age_label))
        if has_bucket_only_age:
            shadow_profile.pending_birth_year_bucket = age_label
            shadow_profile.birth_year_confirmation_closed = False
            shadow_profile.collection_progress["age"] = False
        if extracted.get("age") and not shadow_profile.collection_progress.get("age") and not has_bucket_only_age:
            shadow_profile.collection_progress["age"] = True
        if extracted.get("partner_requirement") and str(extracted.get("partner_requirement") or "").strip() not in {"男生", "女生"}:
            shadow_profile.collection_progress["partner_requirement"] = True
        if extracted.get("partner_gender_preference"):
            shadow_profile.collection_progress["partner_gender_preference"] = True
        if extracted.get("monthly_income"):
            shadow_profile.collection_progress["monthly_income"] = True
        return shadow_profile

    @staticmethod
    def _extract_simple_partner_requirement(user_message: str) -> Optional[str]:
        """轻量提取明确的择偶偏好短答。"""
        message = (user_message or "").strip()
        if not message:
            return None
        compact_message = re.sub(r"\s+", "", message)
        compact_message = re.sub(
            r"(^|[，,])我(?=(温柔|性格好|聊得来|合适|人好|高挑|高一点|同城优先|成熟稳重|三观合拍))",
            r"\1",
            compact_message,
        )

        values_with_pos: list[tuple[int, str]] = []
        numeric_height_preference = TurnUnderstandingService._extract_numeric_height_preference(compact_message)  # noqa: SLF001
        if numeric_height_preference:
            height_pos = compact_message.find(re.sub(r"身高", "", numeric_height_preference).replace("cm", ""))
            values_with_pos.append((height_pos if height_pos >= 0 else len(compact_message), numeric_height_preference))

        patterns = [
            r"(接受\d{1,2}岁上下年龄差)",
            r"(能接受\d{1,2}岁上下年龄差)",
            r"(接受上下\d{1,2}岁年龄差)",
            r"(上下\d{1,2}岁年龄差)",
            r"(上下\d{1,2}岁)",
            r"(卡身高\d{2,3}\+)",
            r"(身高\d{2,3}\+)",
            r"(身高至少\d{2,3})",
            r"(身高不低于\d{2,3})",
            r"(爱笑)",
            r"(喜欢笑)",
            r"(温柔(?:一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?)",
            r"(温柔就行(?:了)?(?:吧|呀|呢)?)",
            r"(性格好就行(?:了)?(?:吧|呀|呢)?)",
            r"(聊得来就行(?:了)?(?:吧|呀|呢)?)",
            r"(合适就行(?:了)?(?:吧|呀|呢)?)",
            r"(人好就行(?:了)?(?:吧|呀|呢)?)",
            r"(高挑)",
            r"(高一点)",
            r"(同城优先)",
            r"(不要超过\d{2}岁)",
            r"(不超过\d{2}岁)",
            r"(不要同[^，。！？!?]{1,12}行业)",
            r"(别同[^，。！？!?]{1,12}行业)",
            r"(最好不要同[^，。！？!?]{1,12}行业)",
            r"(倾向于稳定行业)",
            r"(倾向稳定行业)",
            r"(稳定行业)",
            r"(成熟稳重)",
            r"(三观合拍)",
            r"(喜欢[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(想找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, compact_message):
                values_with_pos.append((match.start(1), match.group(1).strip()))
        if values_with_pos:
            normalized = []
            for _, value in sorted(values_with_pos, key=lambda item: item[0]):
                if value in normalized:
                    continue
                value = re.sub(r"^(?:接受|能接受)上下(\d{1,2})岁年龄差$", r"年龄上下\1岁", value)
                value = re.sub(r"^(?:接受|能接受)(\d{1,2})岁上下年龄差$", r"年龄上下\1岁", value)
                value = re.sub(r"^上下(\d{1,2})岁年龄差$", r"年龄上下\1岁", value)
                value = re.sub(r"^上下(\d{1,2})岁$", r"年龄上下\1岁", value)
                value = re.sub(r"^(?:卡身高|身高)(\d{2,3})\+$", r"身高至少\1", value)
                value = re.sub(r"^喜欢笑$", "爱笑", value)
                value = re.sub(r"(温柔)(一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?$", r"\1", value)
                value = re.sub(r"^(温柔)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(性格好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(聊得来)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(合适)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(人好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(?:最好)?不要同", "不要同", value)
                value = re.sub(r"^别同", "不要同", value)
                value = re.sub(r"^倾向于稳定行业$", "稳定行业", value)
                value = re.sub(r"^倾向稳定行业$", "稳定行业", value)
                value = re.sub(r"稳定行业(?:男生|女生|男的|女的|男性|女性)$", "稳定行业", value)
                normalized.append(value)
            normalized = list(dict.fromkeys(normalized))
            if len(normalized) == 1 and normalized[0] in {"男生", "女生"}:
                return None
            return "，".join(normalized)
        return None

    @staticmethod
    def _build_fused_partner_requirement_prompt(
        main_target: Optional[str],
        user_profile: Optional[UserProfile] = None,
    ) -> str:
        gender_preference = str(getattr(user_profile, "partner_gender_preference", "") or "").strip() if user_profile else ""
        gender_label = "男生" if gender_preference == "男" else "女生" if gender_preference == "女" else ""
        if main_target == "age":
            if gender_label:
                variants = (
                    f"你大概是哪一年出生的呀？顺着这个聊，除了偏{gender_label}这点，你还会更看重对方哪一点也可以一起说说。",
                    f"你是几几年的呀？另外找{gender_label}这类之外，你更在意对方哪方面，也能顺手带一句。",
                    f"你大概是哪一年的呀？说到这儿，除了{gender_label}这个方向，你对另一半还会更看重什么？",
                )
                return random.choice(variants)
            variants = (
                "你大概是哪一年出生的呀？顺着这个聊，你对另一半更看重哪一点也可以一起说说。",
                "你是几几年的呀？另外你找对象时更在意对方哪方面，也能顺手带一句。",
                "你大概是哪一年的呀？说到这儿，你对另一半会更看重什么？",
            )
            return random.choice(variants)
        if main_target == "education":
            if gender_label:
                variants = (
                    f"你大概是什么学历呀？偏{gender_label}这点我先记着，除此之外你更看重另一半哪一点，也可以一起说说。",
                    f"学历这边你方便说个大概吗？除了{gender_label}这个方向，你对另一半更在意哪方面，也能顺手带一句。",
                    f"你大概是什么学历呀？另外说到找对象，找{gender_label}这类之外你会更看重对方哪一点？",
                )
                return random.choice(variants)
            variants = (
                "你大概是什么学历呀？平时更看重另一半哪一点，也可以一起说说。",
                "学历这边你方便说个大概吗？你对另一半更在意哪方面，也能顺手带一句。",
                "你大概是什么学历呀？另外说到找对象，你会更看重对方哪一点？",
            )
            return random.choice(variants)
        if main_target == "occupation":
            occupation_prompt = self.followup_prompt_service.build_soft_occupation_confirmation_prompt(user_profile)
            if gender_label:
                variants = (
                    f"{occupation_prompt} 顺着这个聊，除了偏{gender_label}这点，你对另一半还会更看重哪一点？",
                    f"{occupation_prompt} 另外找{gender_label}这类之外，你更在意对方哪方面，也可以一起说说。",
                    f"{occupation_prompt} 说到这儿，除了{gender_label}这个方向，你会更看重对方什么？",
                )
                return random.choice(variants)
            variants = (
                f"{occupation_prompt} 顺着这个聊，你对另一半会更看重哪一点？",
                f"{occupation_prompt} 另外你找对象时更在意对方哪方面，也可以一起说说。",
                f"{occupation_prompt} 说到这儿，你会更看重对方什么？",
            )
            return random.choice(variants)
        if main_target == "marital_status":
            if gender_label:
                variants = (
                    f"婚况这边我先确认一下，另外除了偏{gender_label}这点，你对另一半还会更看重哪一点？",
                    f"你现在婚况方便说个大概吗？顺着这个聊，找{gender_label}这类之外你更在意对方哪方面？",
                    f"现在的感情状态我先确认一下，另外除了{gender_label}这个方向，你会更看重另一半什么？",
                )
                return random.choice(variants)
            variants = (
                "你现在婚况方便说个大概吗？顺着这个聊，你对另一半还会更看重哪一点？",
                "现在的感情状态我先确认一下，另外你找对象时更在意对方哪方面？",
                "婚况这边我先了解个大概，另外你会更看重另一半什么，也可以一起说说。",
            )
            return random.choice(variants)
        return random.choice(PARTNER_REQUIREMENT_ASK_VARIANTS)

    @staticmethod
    def _extract_city_for_followup(user_message: str, user_profile: Optional[UserProfile] = None) -> str:
        message = str(user_message or "").strip()
        city_match = re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", message)
        if not city_match and user_profile:
            city_match = re.search(
                r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)",
                str(getattr(user_profile, "location", "") or ""),
            )
        return city_match.group(1) if city_match else ""

    @classmethod
    def _build_fused_income_prompt(
        cls,
        main_target: Optional[str],
        user_profile: Optional[UserProfile] = None,
        *,
        user_message: str = "",
    ) -> str:
        if main_target == "occupation":
            city = cls._extract_city_for_followup(user_message, user_profile)
            occupation_prompt = ChatServiceFollowupPromptService.build_soft_occupation_confirmation_prompt(user_profile)
            if city:
                occupation_variants = (
                    f"你现在在{city}主要做哪方面工作呀？",
                    f"在{city}主要做哪方面工作呀？",
                )
                return f"{random.choice(occupation_variants)} {random.choice(INCOME_ASK_VARIANTS)}"
            variants = (
                f"{occupation_prompt} 收入这块大概在什么区间，也可以顺手说个大概。",
                f"{occupation_prompt} 你现在收入大概在哪个范围，也可以一起说说。",
                f"{occupation_prompt} 如果方便的话，收入区间也说个大概就行。",
            )
            return random.choice(variants)
        return random.choice(INCOME_ASK_VARIANTS)

    @staticmethod
    def _build_fused_marital_status_prompt(main_target: Optional[str]) -> str:
        if main_target == "occupation":
            variants = (
                "你现在主要做哪方面工作呀？另外婚况这边也方便说个大概吗？我想确认准一点，因为有的人分居中也会直接说自己单身。",
                "平时是做什么工作的？还有你现在的感情状态，也可以顺手带一句，我多问一句哈，主要是有些情况不一定一句单身就能概括。",
                "你现在主要做哪方面工作呀？另外婚况这边我也想先了解个大概，像分居中这种情况，很多人也会直接说自己单身。",
            )
            return random.choice(variants)
        if main_target == "location":
            variants = (
                "你现在常住在哪座城市呀？另外婚况这边也方便顺手说个大概吗？我想确认准一点，因为有的人分居中也会直接说自己单身。",
                "你平时主要在哪个城市生活呀？还有感情状态这边我也想先了解一下，我多问一句哈，主要是有些情况不一定一句单身就能概括。",
                "你现在常住哪座城市呀？另外婚况这边我也先确认个大概，像分居中这种情况，很多人也会直接说自己单身。",
            )
            return random.choice(variants)
        if main_target == "education":
            variants = (
                "你大概是什么学历呀？另外你现在婚况也方便顺手说个大概吗？我想确认准一点，因为有的人分居中也会直接说自己单身。",
                "学历这边你方便说个大概吗？还有感情状态这边我也想先了解一下，我多问一句哈，主要是有些情况不一定一句单身就能概括。",
            )
            return random.choice(variants)
        variants = (
            "你现在婚况方便说个大概吗？我想确认准一点，因为有的人分居中也会直接说自己单身。",
            "感情状态这边你方便说个大概吗？我多问一句哈，主要是有些情况不一定一句单身就能概括。",
            "我想先了解下你现在婚况大概是怎样的呀？像分居中这种情况，很多人也会直接说自己单身。",
        )
        return random.choice(variants)

    @staticmethod
    def _build_response_opening_signature(text: str) -> str:
        normalized = re.sub(r"[\s，,。！？!?~～、:：;；'\"（）()]+", "", str(text or ""))
        return normalized[:8]

    def _pick_variant_avoiding_recent_openings(
        self,
        candidates: tuple[str, ...],
        user_profile: Optional[UserProfile],
    ) -> str:
        if not candidates:
            return ""
        recent = {
            self._build_response_opening_signature(item)
            for item in getattr(user_profile, "recent_response_openings", [])[-5:]
            if str(item or "").strip()
        }
        ordered = list(candidates)
        random.shuffle(ordered)
        for candidate in ordered:
            if self._build_response_opening_signature(candidate) not in recent:
                return candidate
        return ordered[0]

    def _build_contextual_short_ack(self, field: str, value: Any, user_profile: Optional[UserProfile] = None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        if field == "sex":
            return ""

        if field in {"age", "age_label"}:
            return ""

        if field == "location":
            variants = (
                f"你现在在{text}。",
                f"现在主要在{text}。",
            )
            return self._pick_variant_avoiding_recent_openings(variants, user_profile)

        if field == "education":
            variants = (
                f"{text}是吧。",
                f"学历这块是{text}。",
                f"{text}这个学历。",
            )
            return self._pick_variant_avoiding_recent_openings(variants, user_profile)

        if field == "occupation":
            rendered = ChatService._render_occupation_for_ack(text)
            variants = (
                f"做{rendered}呀。",
                f"现在做{rendered}这块呀。",
                f"{rendered}这行呀。",
            )
            return self._pick_variant_avoiding_recent_openings(variants, user_profile)

        if field == "marital_status":
            if "离异" in text:
                return "现在是离异呀。"
            if "单身" in text or "未婚" in text:
                return "单身呀。"
        return ""

    @staticmethod
    def _render_occupation_for_ack(value: str) -> str:
        return ChatServiceAckRenderService.render_occupation_for_ack(value)

    def _build_contextual_followup_ack(
        self,
        field: str,
        value: Any,
        *,
        ask_field: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
        include_followup_transition: bool = True,
    ) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        if field == "occupation" and ask_field == "education":
            rendered = ChatService._render_occupation_for_ack(text)
            normalized = rendered.lower()
            if not include_followup_transition:
                variants = (
                    f"做{rendered}呀。",
                    f"{rendered}这行呀。",
                    f"现在做{rendered}这块呀。",
                )
                return self._pick_variant_avoiding_recent_openings(variants, user_profile)
            if normalized in {"it", "互联网", "程序员", "开发", "研发", "技术", "技术岗", "工程师"}:
                variants = (
                    f"做{rendered}呀，那学历这块一般也会看一点。",
                    f"{rendered}这行呀，学历这块通常也会看一下。",
                    f"现在做{rendered}这块呀，那我顺着问下学历。",
                )
                return self._pick_variant_avoiding_recent_openings(variants, user_profile)

            variants = (
                f"做{rendered}呀，那我顺着问下学历。",
                f"{rendered}这行呀，我再了解下你的学历。",
                f"现在做{rendered}这块呀，那学历这边我也顺手问一下。",
            )
            return self._pick_variant_avoiding_recent_openings(variants, user_profile)

        return self._build_contextual_short_ack(field, value, user_profile)

    def _format_fast_path_ack(self, field: str, value: Any) -> str:
        rendered = str(value or "").strip()
        if not rendered:
            return ""

        if field == "age":
            rendered = ChatServiceAckRenderService.render_age_value(rendered)
        elif field == "age_label":
            field = "age"
        elif field == "sex":
            rendered = "男" if "男" in rendered else "女"
        elif field == "occupation":
            rendered = ChatServiceAckRenderService.render_occupation_for_ack(rendered)
        elif field == "marital_status":
            rendered = ChatServiceAckRenderService.render_marital_status_for_ack(rendered)

        variants = FAST_PATH_ACK_VARIANTS.get(field)
        if not variants:
            return ""
        formatted = tuple(v.format(value=rendered) for v in variants)
        return random.choice(formatted).strip()

    @staticmethod
    def _get_recent_core_streak(user_profile: UserProfile) -> int:
        streak = 0
        for field in reversed(list(getattr(user_profile, "recent_asked_fields", []) or [])):
            if field in ASK_GUARD_CORE_FIELDS:
                streak += 1
                continue
            break
        return streak

    def _detect_asked_fields_in_response(self, response: str) -> set[str]:
        text = str(response or "").strip()
        if not text:
            return set()

        asked_fields: set[str] = set()
        if self._contains_contact_push_markers(text):
            asked_fields.add("contact")
        segments = [segment.strip() for segment in re.split(r"[。!！\n]+", text) if segment.strip()]
        question_segments = [
            segment for segment in segments
            if "？" in segment or "?" in segment or any(cue in segment for cue in ASK_GUARD_QUESTION_CUES)
        ]
        if not question_segments:
            question_segments = [self._extract_primary_question_segment(text)]

        field_keywords = get_field_keywords()
        pattern_map = {
            "sex": (
                r"男生还是女生",
                r"男生吗还是女生",
                r"性别",
                r"你这边是男生",
                r"你这边是女生",
                r"男生对吧",
                r"女生对吧",
            ),
            "age": (r"多大", r"几岁", r"年龄", r"年纪", r"几几年的", r"哪一年的", r"哪年出生", r"哪一年出生", r"9几年的"),
            "location": (r"哪个城市", r"什么城市", r"在哪个城市", r"在哪边", r"哪里生活"),
            "education": (r"学历",),
            "occupation": (r"做什么工作", r"做哪方面", r"什么工作", r"职业", r"工作"),
            "marital_status": (r"单身状态", r"感情状态", r"婚况", r"离异"),
        }
        for question_text in question_segments:
            if any(marker in question_text for marker in PARTNER_REQUIREMENT_ASK_MARKERS):
                asked_fields.add("partner_requirement")
            if any(marker in question_text for marker in ("月收入", "月薪", "收入", "工资")) and any(cue in question_text for cue in ASK_GUARD_QUESTION_CUES):
                asked_fields.add("monthly_income")

            if not any(cue in question_text for cue in ASK_GUARD_QUESTION_CUES):
                continue

            for field in ASK_GUARD_MANAGED_FIELDS:
                for keyword in field_keywords.get(field, []):
                    if keyword and keyword in question_text:
                        asked_fields.add(field)
                        break

            for field, patterns in pattern_map.items():
                if any(re.search(pattern, question_text) for pattern in patterns):
                    asked_fields.add(field)

        return asked_fields

    def _build_structured_question_state(
        self,
        *,
        canonical_response: str,
        asked_field: str,
        side_asked_field: str | None,
        turn_decision: Optional[TurnDecision],
        planned_ask_field: str | None = None,
        question_source: str = "actual",
    ) -> Dict[str, Any]:
        asked_fields = [field for field in [asked_field] if field]
        side_fields = [field for field in [side_asked_field] if field]
        expected_scope = "self"
        question_intent = "unknown"
        allow_mixed_answer = False

        if asked_field in {"phone", "wechat", "contact"}:
            question_intent = "contact_followup"
            expected_scope = "contact"
        elif asked_field == "partner_requirement" or side_asked_field == "partner_requirement":
            question_intent = "preference_followup"
            expected_scope = "partner"
        elif asked_field or side_asked_field:
            question_intent = "profile_followup"
            expected_scope = "self"
            allow_mixed_answer = bool(side_fields or asked_field in {"monthly_income", "occupation", "location", "education", "marital_status"})
        elif turn_decision and getattr(turn_decision, "prioritize_user_question", False):
            question_intent = "faq_response"
            expected_scope = "mixed"
        elif turn_decision and getattr(turn_decision, "followup_topic", None):
            question_intent = str(getattr(turn_decision, "followup_topic") or "").strip() or "unknown"
            expected_scope = "mixed"

        if side_fields:
            allow_mixed_answer = True

        return {
            "question_intent": question_intent,
            "asked_fields": asked_fields,
            "side_fields": side_fields,
            "expected_scope": expected_scope,
            "allow_mixed_answer": allow_mixed_answer,
            "resume_target": str(getattr(turn_decision, "resume_target", "") or "").strip() or None,
            "planned_ask_field": str(planned_ask_field or "").strip() or None,
            "question_source": str(question_source or "").strip() or "actual",
            "source_response": canonical_response[:120],
        }

    @staticmethod
    def _extract_primary_question_segment(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return ""

        segments = [segment.strip() for segment in re.split(r"[。!！\n]+", text) if segment.strip()]
        question_segments = [
            segment for segment in segments
            if "？" in segment or "?" in segment or any(cue in segment for cue in ASK_GUARD_QUESTION_CUES)
        ]
        target = question_segments[-1] if question_segments else text

        comma_parts = [part.strip() for part in re.split(r"[，,；;]", target) if part.strip()]
        for part in reversed(comma_parts):
            if "？" in part or "?" in part or any(cue in part for cue in ASK_GUARD_QUESTION_CUES):
                return part
        return target

    @staticmethod
    def _looks_like_low_information_model_reply(text: str) -> bool:
        return ChatServiceTextPolicyService.looks_like_low_information_model_reply(text)

    @staticmethod
    def _response_already_acks_field(response: str, field_name: str, value: Any) -> bool:
        return ChatServiceTextPolicyService.response_already_acks_field(response, field_name, value)

    @staticmethod
    def _response_already_absorbs_location_context(response: str, value: Any) -> bool:
        return ChatServiceTextPolicyService.response_already_absorbs_location_context(response, value)

    def _build_interleaving_followup(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        main_target: Optional[str] = None,
        preferred_side_target: Optional[str] = None,
        allow_medium_target: bool = True,
    ) -> str:
        ack = self.turn_understanding_service._build_lightweight_field_ack(user_message, user_profile)  # noqa: SLF001
        if main_target and self.collection_policy.is_collected(user_profile, main_target):
            logger.info(
                "[交错追问] 主目标 %s 已收集，降级为 side-target/直接追问模式",
                main_target,
            )
            main_target = None
        bridge_bundle = self._resolve_profile_bridge_bundle(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=TurnDecision(
                ask_field=main_target,
                response_channel="model",
                allow_medium_target=allow_medium_target,
            ),
            conversation_context={"message_count": 0},
        )
        bridge_context = bridge_bundle.get("context") if bridge_bundle else {}

        main_prompt = ""
        if main_target:
            main_prompt = self._build_policy_field_prompt(main_target, user_profile, user_message=user_message).strip()

        side_prompt = ""
        if (
            allow_medium_target
            and preferred_side_target
            and (
                self._is_allowed_main_side_pair(main_target, preferred_side_target)
                or self.collection_policy.can_actively_ask(user_profile, preferred_side_target)
            )
        ):
            side_prompt = self._build_semantic_side_prompt(
                side_target=preferred_side_target,
                main_target=main_target,
                user_profile=user_profile,
                user_message=user_message,
                bridge_context=bridge_context,
            )
        elif allow_medium_target and preferred_side_target and not main_target:
            side_prompt = self._build_policy_field_prompt(preferred_side_target, user_profile, user_message=user_message)

        if (
            main_target == "occupation"
            and preferred_side_target == "monthly_income"
            and side_prompt
        ):
            prompt = side_prompt
        elif main_prompt and side_prompt:
            prompt = f"{main_prompt} {side_prompt}".strip()
        elif main_prompt:
            prompt = main_prompt
        elif side_prompt:
            prompt = side_prompt
        else:
            prompt = random.choice(NEUTRAL_HOLD_VARIANTS)

        if (
            ack
            and getattr(user_profile, "location", None)
            and self._response_already_absorbs_location_context(prompt, user_profile.location)
        ):
            ack = ""

        if ack:
            return f"{ack} {prompt}".strip()
        return prompt

    def _can_semantically_attach_side_target(
        self,
        side_target: str,
        *,
        main_target: Optional[str],
    ) -> bool:
        if not side_target or not main_target:
            return False
        return self._is_allowed_main_side_pair(main_target, side_target)

    def _is_allowed_main_side_pair(self, main_target: Optional[str], side_target: Optional[str]) -> bool:
        main = str(main_target or "").strip()
        side = str(side_target or "").strip()
        if not main or not side:
            return False
        return side in self._ALLOWED_MAIN_SIDE_PAIRS.get(main, set())

    def _build_semantic_side_prompt(
        self,
        *,
        side_target: str,
        main_target: Optional[str],
        user_profile: UserProfile,
        user_message: str,
        bridge_context: Optional[dict[str, Any]] = None,
    ) -> str:
        if side_target == "partner_requirement":
            if not main_target:
                return random.choice(PARTNER_REQUIREMENT_ASK_VARIANTS)
            if self._can_semantically_attach_side_target(side_target, main_target=main_target):
                return self._build_fused_partner_requirement_prompt(main_target, user_profile)
            return ""

        if side_target == "monthly_income":
            if not main_target:
                return random.choice(INCOME_ASK_VARIANTS)
            if self._can_semantically_attach_side_target(side_target, main_target=main_target):
                if main_target == "occupation" and bridge_context:
                    return self._build_fused_income_prompt(
                        main_target,
                        user_profile,
                        user_message=user_message,
                    )
                return self._build_fused_income_prompt(
                    main_target,
                    user_profile,
                    user_message=user_message,
                )
            return ""

        if side_target == "marital_status":
            if self._can_semantically_attach_side_target(side_target, main_target=main_target):
                return self._build_fused_marital_status_prompt(main_target)
            return ""

        return self._build_policy_field_prompt(side_target, user_profile, user_message=user_message)

    def _build_interleaving_seed_for_model_rewrite(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        main_target: Optional[str] = None,
        preferred_side_target: Optional[str] = None,
        allow_medium_target: bool = True,
    ) -> str:
        """给模型链使用的中性交错追问 seed，避免直接复用本地融合模板。"""
        ack = self.turn_understanding_service._build_lightweight_field_ack(user_message, user_profile)  # noqa: SLF001
        if main_target and self.collection_policy.is_collected(user_profile, main_target):
            main_target = None

        main_seed = ""
        if main_target:
            main_seed = self._build_followup_seed_for_model_rewrite(
                main_target,
                user_profile,
                user_message=user_message,
            ).strip()

        side_seed = ""
        if allow_medium_target and preferred_side_target:
            if self._is_allowed_main_side_pair(main_target, preferred_side_target):
                side_seed = self._build_interleaving_side_seed(
                    side_target=preferred_side_target,
                    main_target=main_target,
                ).strip()
            elif self.collection_policy.can_actively_ask(user_profile, preferred_side_target):
                side_seed = self._build_followup_seed_for_model_rewrite(
                    preferred_side_target,
                    user_profile,
                    user_message=user_message,
                ).strip()

        if main_seed and side_seed:
            prompt = f"{main_seed} {side_seed}".strip()
        elif main_seed:
            prompt = main_seed
        elif side_seed:
            prompt = side_seed
        else:
            prompt = random.choice(NEUTRAL_HOLD_VARIANTS)

        if (
            ack
            and getattr(user_profile, "location", None)
            and self._response_already_absorbs_location_context(prompt, user_profile.location)
        ):
            ack = ""

        if ack:
            return f"{ack} {prompt}".strip()
        return prompt

    @staticmethod
    def _build_interleaving_side_seed(*, side_target: str, main_target: Optional[str]) -> str:
        if side_target == "monthly_income":
            return random.choice(
                (
                    "月收入大概在哪个区间？",
                    "收入区间也可以顺手说个大概。",
                    "月收入这块你说个大概范围就行。",
                )
            )
        if side_target == "marital_status":
            return random.choice(
                (
                    "婚况也方便说个大概吗？",
                    "现在的感情状态也可以顺手带一句。",
                    "婚况这边你说个大概就行。",
                )
            )
        if side_target == "partner_requirement":
            return random.choice(
                (
                    "你对另一半更看重哪一点？",
                    "找对象时你更在意对方哪方面？",
                    "你想找个什么样的，也可以顺手说说。",
                )
            )
        return ""

    @staticmethod
    def _looks_like_contact_value(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        digits_only = re.sub(r"\D", "", text)
        if re.match(r"^1[3-9]\d{9}$", digits_only) or re.match(r"^[5-9]\d{7}$", digits_only):
            return True
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9_-]{4,19}$", text))

    def _is_contact_like_user_message(
        self,
        user_message: str,
        *,
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        understanding_turn_type = str(getattr(understanding_result, "primary_turn_type", "") or "").strip()
        understanding_slots = set(self._effective_resolved_slots(understanding_result).keys())
        if understanding_turn_type == "contact_answer" or bool({"phone", "wechat"} & understanding_slots):
            return True
        if any(token in text for token in CONTACT_ASK_MARKERS):
            return True
        if self._looks_like_contact_value(text):
            return True
        if self.turn_understanding_service._extract_contact_candidate(text) or self._extract_contacts_from_message(text):  # noqa: SLF001
            return True
        return False

    def _apply_refusal_respect_guard(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        return self.text_cleanup_service.apply_refusal_respect_guard(
            response,
            user_profile,
            user_message=user_message,
        )

    def _apply_humanlike_turn_structure_policy(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
        *,
        allow_medium_target: bool = True,
    ) -> str:
        return self.turn_text_policy_service.apply_humanlike_turn_structure_policy(
            response,
            user_profile,
            user_message=user_message,
            allow_medium_target=allow_medium_target,
        )

    def _build_policy_field_prompt(
        self,
        field: Optional[str],
        user_profile: Optional[UserProfile] = None,
        *,
        user_message: str = "",
        stage: str = "trust",
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.followup_prompt_service.build_policy_field_prompt(
            field,
            user_profile,
            user_message=user_message,
            stage=stage,
            collection_result=collection_result,
        )

    def _build_followup_seed_for_model_rewrite(
        self,
        field: Optional[str],
        user_profile: Optional[UserProfile] = None,
        *,
        user_message: str = "",
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.followup_prompt_service.build_followup_seed_for_model_rewrite(
            field,
            user_profile,
            user_message=user_message,
            collection_result=collection_result,
        )

    def _resolve_effective_followup_field(
        self,
        user_profile: UserProfile,
        *,
        ask_field: Optional[str],
        collected_fields: set[str],
        user_message: str = "",
        allow_medium_target: bool = True,
    ) -> Optional[str]:
        """当当前 ask_field 已在本轮被收集时，解析本轮真正应追问的后续字段。"""
        if not ask_field:
            return ask_field
        pending_retry_field = str(getattr(user_profile, "pending_retry_field", "") or "").strip()
        if (
            pending_retry_field
            and pending_retry_field != ask_field
            and pending_retry_field not in collected_fields
            and self.collection_policy.can_actively_ask(user_profile, pending_retry_field)
        ):
            return pending_retry_field
        if ask_field not in collected_fields:
            return ask_field
        if (
            ask_field == "age"
            and str(getattr(user_profile, "pending_birth_year_bucket", "") or "").strip()
            and not getattr(user_profile, "birth_year_confirmation_closed", False)
        ):
            return "age"

        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=True,
            allow_medium_target=allow_medium_target,
        )
        next_field = decision.main_target
        if ask_field == "location":
            if not self.collection_policy.is_collected(user_profile, "occupation"):
                return "occupation"
            if not self.collection_policy.is_collected(user_profile, "education"):
                return "education"
        if next_field and next_field != ask_field:
            return next_field
        forced_target = decision.forced_cover_target
        if forced_target and forced_target != ask_field:
            return forced_target
        if self.collection_policy.can_actively_ask(user_profile, "marital_status") and ask_field != "marital_status":
            return "marital_status"
        if self.collection_policy.can_enter_contact(user_profile):
            return "contact"
        return ask_field

    def _strip_unverified_memory_ack(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """字段未真实落库时，避免输出“记好了/记住了”这类假修复话术。"""
        text = str(response or "").strip()
        if not text:
            return text
        if not re.search(r"(记好|记住|记下)", text):
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        }
        if collected_fields:
            return text

        if self.collection_policy.get_uncovered_core_fields(user_profile):
            text = re.sub(r"[^。！？!?]*(记好|记住|记下)[^。！？!?]*[。！？!?]?\s*", "", text, count=1).strip()
            return text or "这个点我再确认一下，我们顺着往下聊。"
        return text

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

    @staticmethod
    def _accepted_fields_from_persistence_plan(
        understanding_result: TurnUnderstandingResult | None,
    ) -> Dict[str, Any]:
        persistence_plan = getattr(understanding_result, "persistence_plan", None) if understanding_result is not None else None
        if persistence_plan is None:
            return {}
        accepted_fields = getattr(persistence_plan, "accepted_fields", None) or []
        high_risk_fields = {"occupation", "age", "monthly_income", "contact", "partner_requirement", "sex"}
        return {
            str(getattr(field, "field", "") or "").strip(): getattr(field, "normalized_value", None)
            for field in accepted_fields
            if str(getattr(field, "field", "") or "").strip()
            and str(getattr(field, "scope", "") or "").strip() in {"self", "contact", "partner"}
            and str(getattr(field, "persistence_state", "committed") or "committed").strip() == "committed"
            and (
                str(getattr(field, "field", "") or "").strip() not in high_risk_fields
                or ChatService._allows_high_risk_field_from_persistence_plan(field)
            )
        }

    @staticmethod
    def _allows_high_risk_field_from_persistence_plan(field: Any) -> bool:
        source_channel = str(getattr(field, "source_channel", "unknown") or "unknown").strip()
        if source_channel == "ai":
            return True
        field_name = str(getattr(field, "field", "") or "").strip()
        acceptance_reason = str(getattr(field, "acceptance_reason", "") or "").strip()
        return field_name in {"sex", "age", "occupation", "monthly_income"} and acceptance_reason == "explicit_self_marker"

    @classmethod
    def _effective_resolved_slots(
        cls,
        understanding_result: TurnUnderstandingResult | None,
    ) -> Dict[str, Any]:
        persistence_plan = getattr(understanding_result, "persistence_plan", None) if understanding_result is not None else None
        if persistence_plan is not None:
            return dict(cls._accepted_fields_from_persistence_plan(understanding_result))
        return dict(getattr(understanding_result, "resolved_slots", {}) or {})

    def _fuse_extracted_fields(
        self,
        ai_extracted: Dict[str, Any],
        rule_extracted: Dict[str, Any],
        user_message: str,
        user_profile: UserProfile | None = None,
        last_response: str = "",
        understanding_result: TurnUnderstandingResult | None = None,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        多源提取融合（AI + 规则）并产出证据元信息。

        规则：
        1. 双源一致 -> 高置信
        2. 关键字段冲突 -> 优先规则值
        3. 非关键字段冲突 -> 优先 AI 值
        """
        ai_fields = self._canonicalize_extracted_fields(ai_extracted)
        persistence_fields = self._canonicalize_extracted_fields(
            self._accepted_fields_from_persistence_plan(understanding_result)
        )
        understanding_fields = self._canonicalize_extracted_fields(
            self._effective_resolved_slots(understanding_result)
        )
        merged_rule_fields = dict(rule_extracted or {})
        merged_rule_fields.update(understanding_fields)
        merged_rule_fields.update(persistence_fields)
        rule_fields = self._canonicalize_extracted_fields(merged_rule_fields)
        fused: Dict[str, Any] = {}
        meta: Dict[str, Dict[str, Any]] = {}
        evidence_map = dict((understanding_result.resolved_field_evidence if understanding_result else {}) or {})
        derivations = dict((understanding_result.field_derivations if understanding_result else {}) or {})

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
                        "source": "persistence_plan_override" if field in persistence_fields else "rule_override",
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
                meta[field] = self._build_fused_field_meta(
                    field=field,
                    fallback_source="persistence_plan" if field in persistence_fields else "rule",
                    fallback_confidence=0.88 if field in EXTRACTION_CRITICAL_FIELDS else 0.8,
                    fallback_source_text=user_message,
                    evidence_map=evidence_map,
                )
                continue

            if ai_value is not None:
                fused[field] = ai_value
                meta[field] = {
                    "source": "ai",
                    "confidence": 0.72,
                    "source_text": str(ai_value),
                }

        for field, derived_value in derivations.items():
            normalized_value = str(derived_value or "").strip()
            if not normalized_value:
                continue
            fused.setdefault(field, normalized_value)
            if field not in meta:
                meta[field] = self._build_fused_field_meta(
                    field=field,
                    fallback_source="derived",
                    fallback_confidence=0.92,
                    fallback_source_text=normalized_value,
                    evidence_map=evidence_map,
                    derived_from=self._derive_field_parent(field),
                )
            meta[field]["derived_value"] = normalized_value

        self._normalize_partner_preference_fields_after_fusion(
            fused,
            meta,
            user_message=user_message,
        )
        governed_fused = self.extraction_service.govern_role_consistent_fields(
            extracted_fields=fused,
            user_message=user_message,
            user_profile=user_profile,
            last_response=last_response,
            extraction_meta=meta,
        )
        removed_fields = set(fused) - set(governed_fused)
        for field in removed_fields:
            meta.pop(field, None)
        fused = governed_fused
        return fused, meta

    @staticmethod
    def _derive_field_parent(field: str) -> str:
        if field in {"age_label", "birth_year"}:
            return "age"
        return ""

    def _build_fused_field_meta(
        self,
        *,
        field: str,
        fallback_source: str,
        fallback_confidence: float,
        fallback_source_text: str,
        evidence_map: Dict[str, Any],
        derived_from: str = "",
    ) -> Dict[str, Any]:
        evidence = evidence_map.get(field)
        if evidence is None and derived_from:
            evidence = evidence_map.get(derived_from)
        meta = {
            "source": fallback_source,
            "confidence": fallback_confidence,
            "source_text": fallback_source_text,
        }
        if evidence is None:
            if derived_from:
                meta["derived_from"] = derived_from
            return meta
        meta.update(
            {
                "source": str(getattr(evidence, "source_type", "") or fallback_source),
                "confidence": float(getattr(evidence, "confidence", fallback_confidence) or fallback_confidence),
                "source_text": str(getattr(evidence, "source_text", "") or fallback_source_text),
                "source_span": str(getattr(evidence, "source_span", "") or ""),
                "scope": str(getattr(evidence, "scope", "") or "mixed"),
            }
        )
        if derived_from:
            meta["derived_from"] = derived_from
        return meta

    def _normalize_partner_preference_fields_after_fusion(
        self,
        fused: Dict[str, Any],
        meta: Dict[str, Dict[str, Any]],
        *,
        user_message: str,
    ) -> None:
        raw_requirement = str(fused.get("partner_requirement") or "").strip()
        structured_subslots = {
            field: str(fused.get(field) or "").strip()
            for field in ChatServiceSummaryHelperService.STRUCTURED_PARTNER_PREFERENCE_FIELDS
            if str(fused.get(field) or "").strip()
        }
        if not raw_requirement and structured_subslots:
            raw_surface = self.extraction_service._extract_partner_requirement_raw_surface_from_message(  # noqa: SLF001
                user_message,
                structured_subslots=structured_subslots,
            )
            raw_requirement = self.extraction_service._compose_partner_requirement_from_subslots(  # noqa: SLF001
                structured_subslots,
                raw_surface,
            )
            fused["partner_requirement"] = raw_requirement
            meta.setdefault(
                "partner_requirement",
                {
                    "source": "structured_partner_requirement_compose",
                    "confidence": 0.84,
                    "source_text": raw_surface or raw_requirement,
                    "scope": "partner",
                },
            )
        if not raw_requirement:
            return

        inferred_gender_preference = self.turn_understanding_service._extract_partner_gender_preference(  # noqa: SLF001
            raw_requirement
        )
        if not inferred_gender_preference:
            if re.search(r"(男朋友|男生|男性|男孩子)", raw_requirement):
                inferred_gender_preference = "男"
            elif re.search(r"(女朋友|女生|女性|女孩子)", raw_requirement):
                inferred_gender_preference = "女"
        normalized_requirement = self._extract_simple_partner_requirement(raw_requirement)
        normalized_keeps_rich_content = bool(
            normalized_requirement
            and self.extraction_service._looks_like_partner_requirement_content(normalized_requirement)  # noqa: SLF001
        )
        raw_has_rich_content = bool(
            self.extraction_service._looks_like_partner_requirement_content(raw_requirement)  # noqa: SLF001
        )
        raw_has_distinct_requirement_markers = any(
            marker in raw_requirement
            for marker in ("接受", "对方", "倾向", "以上", "男生", "女生", "男性", "女性", "深圳", "广州", "杭州", "上海", "北京")
        )
        normalized_dropped_too_much_detail = bool(
            normalized_requirement
            and raw_has_distinct_requirement_markers
            and len(normalized_requirement) + 6 < len(raw_requirement)
        )

        if inferred_gender_preference and not fused.get("partner_gender_preference"):
            fused["partner_gender_preference"] = inferred_gender_preference
            meta["partner_gender_preference"] = {
                "source": "partner_requirement_normalized",
                "confidence": 0.86,
                "source_text": raw_requirement,
            }

        def _hydrate_partner_preference_subslots(requirement_text: str) -> None:
            if not str(requirement_text or "").strip():
                return
            subslots = self.extraction_service._extract_partner_preference_subslots(requirement_text)  # noqa: SLF001
            for subfield, subvalue in subslots.items():
                if not str(subvalue or "").strip() or fused.get(subfield):
                    continue
                fused[subfield] = subvalue
                meta[subfield] = {
                    "source": "partner_requirement_subslot_normalized",
                    "confidence": 0.84,
                    "source_text": raw_requirement,
                    "derived_from": "partner_requirement",
                    "scope": "partner",
                }

        _hydrate_partner_preference_subslots(normalized_requirement or raw_requirement)

        if normalized_requirement and not normalized_dropped_too_much_detail and (
            normalized_keeps_rich_content or not raw_has_rich_content
        ):
            fused["partner_requirement"] = normalized_requirement
            if "partner_requirement" in meta:
                meta["partner_requirement"] = {
                    **meta["partner_requirement"],
                    "source": "normalized_partner_requirement",
                    "source_text": raw_requirement,
                }
            return

        if raw_has_rich_content:
            fused["partner_requirement"] = raw_requirement
            if "partner_requirement" in meta:
                meta["partner_requirement"] = {
                    **meta["partner_requirement"],
                    "source": str(meta["partner_requirement"].get("source") or "rich_partner_requirement_preserved")
                    if meta["partner_requirement"].get("source") == "structured_partner_requirement_compose"
                    else "rich_partner_requirement_preserved",
                    "source_text": raw_requirement,
                }
            return

        if inferred_gender_preference:
            fused.pop("partner_requirement", None)
            meta.pop("partner_requirement", None)

    async def _update_conversation_state(
        self,
        account_id: str,
        user_message: str,
        clean_response: str,
        raw_response: str,
        turn_decision: Optional[TurnDecision] = None,
        track_asked_fields: bool = True,
    ) -> None:
        """更新对话状态"""
        canonical_response = self.dialogue_manager.normalize_assistant_response(clean_response)
        # 添加到历史
        await self.dialogue_manager.add_to_history(account_id, 'user', user_message)
        await self.dialogue_manager.add_to_history(account_id, 'assistant', canonical_response)

        # 更新最近回复（使用清理后的回复，而不是原始回复）
        # 注意：_handle_contact_validation 可能已经添加了微信询问回复，这里不要覆盖
        # 检查 recent_responses 最后一条是否已经是当前回复
        last_response = await self.dialogue_manager.get_last_response(account_id)
        if last_response != canonical_response:
            await self.dialogue_manager.update_recent_responses(account_id, canonical_response)
        await self.dialogue_manager.update_prompt_style_memory(account_id, canonical_response)

        # 增加消息计数
        await self.dialogue_manager.increment_message_count(account_id)

        faq_resume_context = bool(
            turn_decision
            and (
                getattr(turn_decision, "response_channel", "") == "quick_faq"
                or getattr(turn_decision, "prioritize_user_question", False)
            )
        )

        # 智能追问机制：追踪AI询问的字段
        if (
            track_asked_fields
            and not faq_resume_context
            and ChatServiceResponseCleanupService.is_delivery_viable(canonical_response)
        ):
            await self.ask_tracking_service.track_ai_asked_fields(account_id, canonical_response)

        # Phase 2: 记录本轮追问的字段（用于短答槽位绑定）
        user_profile = await self.user_service.get_user_profile(account_id)
        opening_signature = self._build_response_opening_signature(canonical_response)
        message_count = await self.dialogue_manager.get_message_count(account_id)
        detected_asked_fields = self._detect_asked_fields_in_response(canonical_response)
        all_questioned_fields = self._detect_all_questioned_fields_in_response(canonical_response)
        effective_questioned_fields = detected_asked_fields | all_questioned_fields
        planned_ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        has_question_intent = bool(
            self._contains_contact_push_markers(canonical_response)
            or detected_asked_fields
            or all_questioned_fields
            or ("？" in canonical_response or "?" in canonical_response)
        )
        actual_question_field_order = (
            "contact",
            "phone",
            "wechat",
            "occupation",
            "location",
            "education",
            "age",
            "marital_status",
            "monthly_income",
            "partner_requirement",
            "partner_gender_preference",
            "sex",
        )
        actual_asked_field_pool = detected_asked_fields or all_questioned_fields
        actual_asked_fields = [
            field
            for field in actual_question_field_order
            if field in actual_asked_field_pool
        ]
        question_source = "actual"
        if faq_resume_context:
            asked_field = ""
        elif actual_asked_fields:
            asked_field = actual_asked_fields[0]
        else:
            asked_field = self.turn_understanding_service._detect_which_field_is_asked(canonical_response)  # noqa: SLF001
        if (
            asked_field
            and planned_ask_field
            and asked_field != planned_ask_field
            and planned_ask_field not in effective_questioned_fields
        ):
            question_source = "actual_drifted"
        elif asked_field and planned_ask_field and asked_field == planned_ask_field:
            question_source = "planned_aligned"
        elif asked_field:
            question_source = "actual"
        elif planned_ask_field and has_question_intent:
            asked_field = planned_ask_field
            question_source = "planned_fallback"
        if faq_resume_context:
            side_asked_field = None
        elif actual_asked_fields:
            side_asked_field = next((field for field in actual_asked_fields[1:] if field != asked_field), None)
        else:
            side_asked_field = next(
                (
                    field
                    for field in ("marital_status", "monthly_income", "partner_requirement")
                    if field in effective_questioned_fields and field != asked_field
                ),
                None,
            )
        pending_sex_confirmation = _extract_confirmed_sex_candidate_from_context(canonical_response)
        profile_changed = False
        if opening_signature:
            recent_openings = list(getattr(user_profile, "recent_response_openings", []) or [])
            recent_openings.append(opening_signature)
            user_profile.recent_response_openings = recent_openings[-5:]
            profile_changed = True
        if pending_sex_confirmation and (asked_field == "sex" or planned_ask_field == "sex"):
            if user_profile.pending_sex_confirmation != pending_sex_confirmation:
                user_profile.pending_sex_confirmation = pending_sex_confirmation
                profile_changed = True
        elif asked_field and asked_field != "sex" and user_profile.pending_sex_confirmation:
            user_profile.pending_sex_confirmation = None
            profile_changed = True
        if (
            planned_ask_field
            and asked_field
            and planned_ask_field != asked_field
            and planned_ask_field not in effective_questioned_fields
            and not str(getattr(user_profile, "resume_profile_target", "") or "").strip()
        ):
            user_profile.set_resume_profile_target(
                getattr(user_profile, "resume_profile_mode", None) or "collect_profile",
                planned_ask_field,
                getattr(user_profile, "last_user_concern_type", None),
            )
            profile_changed = True
        if asked_field:
            user_profile.set_last_asked_field(asked_field, message_count, side_field=side_asked_field)
            user_profile.set_last_question_state(
                self._build_structured_question_state(
                    canonical_response=canonical_response,
                    asked_field=asked_field,
                    side_asked_field=side_asked_field,
                    turn_decision=turn_decision,
                    planned_ask_field=planned_ask_field,
                    question_source=question_source,
                )
            )
            if side_asked_field:
                logger.debug(
                    f"[短答槽位绑定] 记录本轮追问字段: {asked_field}, side={side_asked_field}, turn_index: {message_count}"
                )
            else:
                logger.debug(f"[短答槽位绑定] 记录本轮追问字段: {asked_field}, turn_index: {message_count}")
            if str(getattr(user_profile, "pending_retry_field", "") or "").strip() == asked_field:
                user_profile.clear_pending_retry_field()
            profile_changed = True
        elif user_profile.last_asked_field:
            preserve_interrupted_followup_context = bool(
                faq_resume_context or str(getattr(user_profile, "resume_profile_target", "") or "").strip()
            )
            if preserve_interrupted_followup_context:
                if not str(getattr(user_profile, "resume_profile_target", "") or "").strip():
                    user_profile.set_resume_profile_target(
                        getattr(user_profile, "resume_profile_mode", None) or "collect_profile",
                        user_profile.last_asked_field,
                        getattr(user_profile, "last_user_concern_type", None) or "faq",
                    )
                    profile_changed = True
                    logger.info(
                        "[resume_target_preserved] field=%s reason=%s",
                        user_profile.last_asked_field,
                        "faq_resume_context",
                    )
                logger.info(
                    "[last_asked_preserved] field=%s reason=%s",
                    user_profile.last_asked_field,
                    "faq_resume_context",
                )
                if not getattr(user_profile, "last_question_state", None):
                    user_profile.set_last_question_state(
                        self._build_structured_question_state(
                            canonical_response=canonical_response,
                            asked_field=str(getattr(user_profile, "last_asked_field", "") or "").strip(),
                            side_asked_field=str(getattr(user_profile, "last_asked_side_field", "") or "").strip() or None,
                            turn_decision=turn_decision,
                            planned_ask_field=planned_ask_field,
                        )
                    )
                    profile_changed = True
            else:
                # 如果本轮没有追问，清除上一轮记录
                user_profile.clear_last_asked_field()
                user_profile.clear_last_question_state()
                profile_changed = True
        if profile_changed:
            await self.user_service.save_user_profile(account_id, user_profile)

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
        if response_route != "quick_faq":
            response = self._sanitize_forbidden_sales_phrases(response)
        latest_profile = await self.user_service.get_user_profile(account_id)
        if isinstance(latest_profile, UserProfile):
            user_profile = latest_profile
        if response_route:
            await self._simulate_non_ai_human_delay(response, route=response_route)

        # 检查是否拒绝
        is_refusal = RefusalDetector.is_refusing(response)

        # 获取消息计数
        message_count = await self.dialogue_manager.get_message_count(account_id)

        # 使用"增加前"的快照来判断"已跳过"显示（如果没有快照，使用当前值）
        ask_count_snapshot = field_ask_count_before if field_ask_count_before is not None else {}
        current_turn_fields: Dict[str, Any] = {}
        for item in (collection_result or {}).get("all_fields", []) or []:
            if not isinstance(item, dict):
                continue
            field_name = str(item.get("field") or "").strip()
            if not field_name:
                continue
            current_turn_fields[field_name] = item.get("value")
        display_fields = dict((collection_result or {}).get("display_fields") or {})

        # 辅助函数：获取字段显示值（区分"未留"和"已跳过"）
        def get_field_display(field_name: str, value, default: str = "未留") -> str:
            turn_value = current_turn_fields.get(field_name)
            if turn_value not in (None, ""):
                return str(turn_value)
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
            if current_turn_fields.get("contact") not in (None, ""):
                return str(current_turn_fields["contact"])
            phone_value = current_turn_fields.get("phone")
            wechat_value = current_turn_fields.get("wechat")
            if phone_value not in (None, "") and wechat_value not in (None, ""):
                return f"电话: {phone_value}, 微信: {wechat_value}"
            if phone_value not in (None, ""):
                existing_wechat = str(getattr(user_profile, "wechat", "") or "").strip()
                if existing_wechat:
                    return f"电话: {phone_value}, 微信: {existing_wechat}"
                return f"电话: {phone_value}"
            if wechat_value not in (None, ""):
                existing_phone = str(getattr(user_profile, "phone", "") or "").strip()
                if existing_phone:
                    return f"电话: {existing_phone}, 微信: {wechat_value}"
                return f"微信: {wechat_value}"
            return self.contact_service.get_status_display(user_profile)

        def get_occupation_display() -> str:
            if current_turn_fields.get("occupation") not in (None, ""):
                return str(current_turn_fields["occupation"])
            occupation = str(getattr(user_profile, "occupation", "") or "").strip()
            if occupation:
                return occupation
            if str(getattr(user_profile, "occupation_inference_candidate", "") or "").strip():
                return "未确认"
            return get_field_display("occupation", None)

        def get_occupation_inference_display() -> str:
            if str(getattr(user_profile, "occupation", "") or "").strip():
                return "无"
            candidate = str(getattr(user_profile, "occupation_inference_candidate", "") or "").strip()
            if not candidate:
                return "无"
            evidence = dict(getattr(user_profile, "extraction_evidence", {}) or {}).get("occupation_inference_candidate") or {}
            confidence = evidence.get("confidence")
            reason = str(evidence.get("reason") or "").strip()
            reason_label_map = {
                "explicit_self_industry": "自述行业",
                "same_industry_exclusion": "同行反推",
                "same_work_alignment": "同行表述",
                "industry_context_fallback": "语境弱推断",
            }
            reason_label = reason_label_map.get(reason, reason)
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = None
            if confidence_value is None:
                return f"[推断] {candidate} ({reason_label})" if reason_label else f"[推断] {candidate}"
            confidence_label = (
                "高置信" if confidence_value >= 0.85
                else "中置信" if confidence_value >= 0.70
                else "低置信"
            )
            suffix_parts = [f"{confidence_value:.2f}", confidence_label]
            if reason_label:
                suffix_parts.append(reason_label)
            return f"[推断] {candidate} ({', '.join(suffix_parts)})"

        raw_partner_requirement = str(
            current_turn_fields.get("partner_requirement")
            or display_fields.get("partner_requirement")
            or getattr(user_profile, "partner_requirement", "")
            or ""
        ).strip()
        display_partner_requirement_override = str(display_fields.get("partner_requirement") or "").strip()
        partner_requirement_hint = ChatServiceSummaryHelperService.extract_partner_requirement_hint(
            collection_result=collection_result,
            profile=user_profile,
        )
        if display_partner_requirement_override:
            partner_requirement_hint = display_partner_requirement_override
        elif not partner_requirement_hint:
            partner_requirement_hint = display_partner_requirement_override
        inferred_partner_gender_from_requirement = self.turn_understanding_service._extract_partner_gender_preference(  # noqa: SLF001
            raw_partner_requirement or partner_requirement_hint
        )
        normalized_partner_requirement = str(
            self._extract_simple_partner_requirement(raw_partner_requirement or partner_requirement_hint) or ""
        ).strip()
        if normalized_partner_requirement in ChatServiceSummaryHelperService.GENERIC_PARTNER_REQUIREMENT_VALUES:
            normalized_partner_requirement = ""
        display_partner_requirement = (
            partner_requirement_hint
            if partner_requirement_hint
            else normalized_partner_requirement
            if normalized_partner_requirement
            else None if inferred_partner_gender_from_requirement
            else raw_partner_requirement
        )
        display_partner_gender = getattr(user_profile, "partner_gender_preference", None) or inferred_partner_gender_from_requirement

        # 构建已收集信息（联系方式合并显示，性别偏好与择偶要求分开展示）
        collected_info = {
            "sex": get_field_display("sex", user_profile.sex),
            "last_name": get_field_display("last_name", user_profile.last_name, "未留称呼"),
            "age": get_field_display(
                "age",
                (
                    f"{current_turn_fields.get('age_label')}({current_turn_fields.get('age')}岁)"
                    if current_turn_fields.get("age_label") and current_turn_fields.get("age")
                    else (
                        f"{user_profile.age_label}({user_profile.age}岁)"
                        if user_profile.age_label and user_profile.age
                        else user_profile.age_label or user_profile.age
                    )
                ),
            ),
            "height": get_field_display("height", user_profile.height),
            "weight": get_field_display("weight", user_profile.weight),
            "location": get_field_display("location", user_profile.location),
            "education": get_field_display("education", user_profile.education),
            "marital_status": get_field_display("marital_status", user_profile.marital_status),
            "monthly_income": get_field_display("monthly_income", user_profile.monthly_income),
            "occupation": get_occupation_display(),
            "occupation_inference_candidate": get_occupation_inference_display(),
            "contact": get_contact_display(),
            "partner_gender_preference": get_field_display(
                "partner_gender_preference",
                "男生" if display_partner_gender == "男"
                else "女生" if display_partner_gender == "女"
                else None,
            ),
            "partner_requirement": get_field_display("partner_requirement", display_partner_requirement)
        }

        # 返回响应
        meta: Dict[str, Any] = {}
        if collection_result and collection_result.get("ending_info"):
            meta["ending"] = dict(collection_result["ending_info"])

        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id,
            "collected_info": collected_info,
            "collected": collection_result.get("collected", False) if collection_result else False,
            "field": collection_result.get("field") if collection_result else None,
            "value": collection_result.get("value") if collection_result else None,
            "meta": meta,
        }

    def _sanitize_forbidden_sales_phrases(self, response: str) -> str:
        """清理会暴露业务流程或违规承诺的固定话术。"""
        text = str(response or "")
        if not text:
            return text

        original = text
        for pattern in self.FORBIDDEN_SALES_PATTERNS:
            text = re.sub(pattern, "", text)
        for pattern in self.SALESY_CLAUSE_PATTERNS:
            text = re.sub(pattern, "", text)

        # 联系方式相关句子里，压掉过重的语气尾词，避免显得油腻或销售感过强。
        contacty = self._contains_contact_push_markers(text) or any(token in text for token in ("骚扰", "广告", "资源"))
        if contacty:
            text = re.sub(r"([呀哈呢啦哦啊]{1,3})([。！？!?])", r"\2", text)

        # 清理替换后残留的重复空白和标点。
        text = re.sub(r"[，,。]{2,}", "。", text)
        text = re.sub(r"[，,]\s*[。！？!?]", lambda m: m.group(0)[-1], text)
        text = re.sub(r"\s+", " ", text).strip(" ，,。")

        if text != original:
            logger.debug("[话术合规] 已替换禁语表达，避免出现见面/发资料承诺")
        return text

    def _strip_false_input_error_followup(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Optional[Dict[str, Any]],
        *,
        user_message: str,
        ask_field: Optional[str],
    ) -> str:
        """本轮已经稳定提取到资料时，不再把用户正常输入说成错字/没看懂。"""
        text = str(response or "").strip()
        if not text:
            return text

        typo_markers = ("打错字", "没看懂", "看不懂", "没太看懂", "乱码", "手滑")
        if not any(marker in text for marker in typo_markers):
            return text

        extracted_fields = [
            item.get("field")
            for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and item.get("field")
        ]
        if not extracted_fields:
            return text

        # 只有本轮已经拿到了明确资料时，才压掉“是不是打错字/没看懂”这类误判。
        if not any(field in {"sex", "age", "age_label", "location", "education", "occupation", "monthly_income", "partner_requirement"} for field in extracted_fields):
            return text

        followup = self._build_followup_seed_for_model_rewrite(  # noqa: SLF001
            ask_field,
            user_profile,
            user_message=user_message,
        ).strip() if ask_field else ""
        ack = self.turn_understanding_service._build_opening_profile_ack(user_message) or self.turn_understanding_service._build_lightweight_field_ack(  # noqa: SLF001
            user_message,
            user_profile,
        )
        if not ack and "age" in extracted_fields and user_profile.age:
            ack = (
                f"{ChatServiceAckRenderService.render_age_value(str(user_profile.age))}"
                "这个年龄段我先记下了。"
            )

        rebuilt = " ".join(part for part in (ack, followup) if part).strip()
        return rebuilt or text

    @staticmethod
    def _sanitize_robotic_tone(response: str) -> str:
        return ChatServiceTextCleanupService.sanitize_robotic_tone(response)

    @staticmethod
    def _should_emit_profile_summary(
        profile: UserProfile,
        current_message_count: int,
        min_collected_fields: int = 4,
        min_turns_between_summaries: int = 5,
        max_summaries_per_conversation: int = 2,
    ) -> bool:
        """
        Phase 2: 判断是否应该输出画像小结。

        触发条件：
        1. 关键字段（年龄、城市、学历、收入、偏好）收集到 4 个及以上
        2. 距离上次小结至少 min_turns_between_summaries 轮
        3. 本次对话小结次数未超过 max_summaries_per_conversation

        Args:
            profile: 用户画像
            current_message_count: 当前消息序号
            min_collected_fields: 最少收集字段数
            min_turns_between_summaries: 两次小结间的最少轮数
            max_summaries_per_conversation: 每次对话最多小结次数

        Returns:
            是否应该输出画像小结
        """
        # 画像小结会把主回复洗成“系统在读档案”，当前阶段默认禁用。
        return False

        # 关键字段列表
        key_fields = ["age", "age_label", "location", "education", "monthly_income", "partner_requirement"]

        # 偏好已收集后，不再自动播报画像小结，避免“你XX岁、偏XX是吧”这类摘要感。
        if profile.collection_progress.get("partner_requirement", False) or getattr(profile, "partner_requirement", None):
            return False

        # 统计已收集的关键字段数量
        collected_count = sum(
            1 for field in key_fields
            if profile.collection_progress.get(field, False) or getattr(profile, field, None)
        )

        if collected_count < min_collected_fields:
            return False

        # 检查距离上次小结的轮数
        last_summary_turn = profile.last_profile_summary_turn or 0
        if current_message_count - last_summary_turn < min_turns_between_summaries:
            return False

        # 检查本次对话小结次数（通过 last_profile_summary_turn 是否设置过判断）
        # 如果 last_summary_turn > 0，说明已经小结过至少一次
        # 这里简化处理：最多小结 2 次
        if last_summary_turn > 0 and current_message_count - last_summary_turn < min_turns_between_summaries * 2:
            # 已经小结过，且距离不够远，不再小结
            return False

        return True

    @staticmethod
    def _is_short_answer(user_message: str, max_length: int = 12) -> bool:
        return ChatServiceMessageSignalService.is_short_answer(user_message, max_length=max_length)

    def _prevent_no_repeat_hold_from_blocking_progress(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        return self.text_cleanup_service.prevent_no_repeat_hold_from_blocking_progress(
            response,
            user_profile,
            collection_result=collection_result,
            user_message=user_message,
        )

    def _downgrade_premature_profile_summary(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        ask_field: Optional[str] = None,
    ) -> str:
        return self.text_cleanup_service.downgrade_premature_profile_summary(
            response,
            user_profile,
            collection_result=collection_result,
            ask_field=ask_field,
        )

    def _needs_style_retry(
        self,
        natural_response: str,
        *,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        text = str(natural_response or "").strip()
        if not text:
            return False
        blocked_phrases = (
            "你好呀～对了，想问下",
            "对了，想问下",
            "方便说下自己的年龄",
            "你方便说下自己的年龄",
            "好，你是男生啦",
            "好，你是女生啦",
            "好嘞，你是男生啦",
            "好嘞，你是女生啦",
        )
        if any(phrase in text for phrase in blocked_phrases):
            return True

        recent_responses = (conversation_context or {}).get("recent_responses") or []
        current_signature = self.dialogue_manager.build_prompt_signature(text)
        recent_signatures = [
            self.dialogue_manager.build_prompt_signature(str(item or ""))
            for item in recent_responses[-2:]
            if str(item or "").strip()
        ]
        return bool(current_signature and current_signature in recent_signatures)

    def _error_response(
        self,
        error: str,
        dialog_id: Optional[str],
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建错误响应"""
        # 检测是否是429配额错误，如果是则返回空响应（不显示错误消息）
        if '429' in error or 'SetLimitExceeded' in error or 'TooManyRequests' in error:
            return {
                "success": True,
                "response": "",
                "dialogId": dialog_id,
                "silent": True,
                "error_code": error_code or "RATE_LIMIT_EXCEEDED",
            }

        return {
            "success": False,
            "error": error,
            "error_code": error_code or "INTERNAL_ERROR",
            "details": details or {},
            "dialogId": dialog_id
        }

    def build_error_response(
        self,
        error: str,
        dialog_id: Optional[str],
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._error_response(
            error,
            dialog_id,
            error_code=error_code,
            details=details,
        )

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

    @staticmethod
    def _env_flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def _is_ai_raw_response_mode_enabled(self) -> bool:
        if self._env_flag("AI_RAW_RESPONSE_KILL_SWITCH", False):
            return False
        return self._env_flag("AI_RAW_RESPONSE_MODE", True)

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

        route_floor = self._env_float("MQ_NON_AI_DELAY_FLOOR_SECONDS", 1.05)
        floor_by_route = {}
        selected_floor = max(0.0, floor_by_route.get(route, route_floor))

        if jitter_max < jitter_min:
            jitter_min, jitter_max = jitter_max, jitter_min

        delay = base + max(0, len(response_text)) * per_char + random.uniform(jitter_min, jitter_max)
        delay = max(0.0, min(delay, max(0.0, cap)))
        if selected_floor > 0:
            delay = max(delay, selected_floor)
        logger.info(f"[拟人延时] route={route}, delay={delay:.3f}s")
        await asyncio.sleep(delay)

    # ============ 打招呼检测 ============

    # ============ 无意义输入检测 ============

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
