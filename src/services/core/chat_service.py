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
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, Any, Optional, List

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.data.user_service import UserService
from src.services.collection.profile_collection_coordinator import ProfileCollectionCoordinator
from src.services.application.process_chat_turn import ProcessChatTurnUseCase
from src.modules.contact_collection.domain.contact_collection_service import ContactCollectionService
from src.modules.contact_collection.domain.refusal_service import RefusalService
from src.modules.conversation.domain.dialogue_manager import DialogueManager
from src.modules.conversation.domain.conversation_ending_service import ConversationEndingService
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.conversation.domain.greeting_service import GreetingService
from src.modules.conversation.domain.input_fallback_service import InputFallbackService
from src.modules.conversation.domain.dialogue_expression_service import DialogueExpressionService
from src.modules.conversation.domain.user_question_service import UserQuestionService
from src.modules.conversation.domain.conversation_rule_service import ConversationRuleService
from src.modules.conversation.domain.turn_intent_classifier import TurnIntentClassifier
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.profile_collection.domain.ask_tracking_service import AskTrackingService
from src.modules.profile_collection.domain.extraction_service import ExtractionService
from src.modules.profile_collection.domain.validation_service import ValidationService
from src.modules.profile_collection.domain.field_skip_service import FieldSkipService
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.utils.validators import RefusalDetector
from src.core.exceptions import ValidationException, AIServiceException
from src.config.settings import settings, get_field_keywords

logger = logging.getLogger(__name__)

STYLE_RETRY_BLOCKED_PHRASES = (
    "你好呀～对了，想问下",
    "对了，想问下",
    "我是小缘",
    "好，你是男生啦",
    "好，你是女生啦",
    "好嘞，你是男生啦",
    "好嘞，你是女生啦",
    "你学历这块大概是什么背景呀",
    "学历这块你方便说下吗",
    "还有婚况这块，我也顺带确认下",
    "你现在是单身、未婚，还是离异呢",
)

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
SERVICE_CONFIRMATION_SUBJECT_PATTERNS = (
    "你们",
    "这边",
    "这里",
    "你家",
    "你们这",
)
SERVICE_CONFIRMATION_SERVICE_PATTERNS = (
    "介绍对象",
    "介绍",
    "牵线",
    "找对象",
    "相亲",
    "脱单",
)
SERVICE_CONFIRMATION_QUESTION_PATTERNS = (
    "吗",
    "是吧",
    "对吧",
    "啊",
    "呀",
    "?",
    "？",
)
SERVICE_CONFIRMATION_DIRECT_PATTERNS = (
    r"你们.*介绍对象",
    r"你们.*牵线",
    r"你们.*找对象",
    r"这边.*介绍对象",
    r"这边.*牵线",
    r"这边.*找对象",
    r"这里.*介绍对象",
    r"这里.*牵线",
    r"帮.*介绍对象",
    r"帮.*找对象",
    r"做.*相亲介绍",
    r"做.*介绍对象",
    r"做.*牵线",
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
    if re.search(r"(你这边是|你是|我理解你是)\s*男(?:生|的)?", content):
        return "男"
    if re.search(r"(你这边是|你是|我理解你是)\s*女(?:生|的)?", content):
        return "女"
    return None


def _is_affirmative_confirmation_answer(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)\s*[，,、 ]*\s*$",
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
PARTNER_REQUIREMENT_ASK_MARKERS = ("择偶", "偏好", "看重对方", "另一半", "喜欢什么样", "想找什么类型")
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
    "这个偏好我知道了，后面就顺着你这个感觉聊。",
    "好，这个点我听进去了。",
    "明白，你更在意的这个点我有数了。",
)
LOCATION_MEMORY_ACK_VARIANTS = (
    "你现在在{location}这边，是吧。",
    "好，你现在主要在{location}。",
    "{location}这点我知道了。",
)
NO_REPEAT_FIELD_VARIANTS = (
    "这个点我不重复绕了，你想聊别的就顺着说。",
    "这个我知道了，咱们不在这上面打转。",
)
NEUTRAL_HOLD_VARIANTS = (
    "这个点我知道了，我们接着往下聊。",
    "这个我知道了，咱们继续往下说。",
)
WORK_BUSY_ACK_VARIANTS = (
    "工作忙这点我接住了。",
    "平时工作节奏比较满是吧。",
    "忙一点我能理解。",
)
WORK_BUSY_OCCUPATION_ACK_VARIANTS = (
    "做{occupation}的话，忙一点也挺正常。",
    "像{occupation}这种工作，节奏忙我能理解。",
    "你平时做{occupation}，忙起来也正常。",
)
LOCATION_REUSE_ACK_VARIANTS = (
    "{location}这边我记着呢。",
    "你在{location}这边是吧。",
    "同城这个语境我接住了。",
)
PREFERENCE_REUSE_ACK_VARIANTS = (
    "你前面提过更偏向{preference}这一类，这个我记着。",
    "你会更看重{preference}这个点，对吧。",
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
    "{field_ack} 这个我知道了，我们先按你舒服的节奏来。",
)
OPENING_PROFILE_ACK_VARIANTS = (
    "{field_ack} 这点我知道了。",
    "好，{field_ack}",
    "{field_ack} 我先接住了。",
)
WITHDRAW_RETAIN_VARIANTS = (
    "怎么啦，是哪块让你有点不想继续聊呀？",
    "没关系，我先不往下问了。你要是有顾虑，也可以直接告诉我。",
    "是我刚才问得有点快了，还是你对这件事本身还有点担心呀？",
)
WITHDRAW_SOFT_CLOSE_VARIANTS = (
    "好，那我先不打扰你了，咱们先这样。后面你想继续聊了再来找我就行。",
    "没关系，那这轮我先收住，后面你要是想继续再来找我。",
)
NO_REPEAT_PARTNER_REQUIREMENT_STATEMENT = "这个条件我知道了，后面我会顺着这个方向聊，不重复追问。"
PARTNER_REQUIREMENT_ASK_VARIANTS = (
    "你对另一半大概有什么要求呀？",
    "你要是方便，也可以说说你想找个什么样的。",
    "你对另一半大概有什么要求呀？比如年龄、城市、性格这些，你会更在意哪方面？",
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
)
INTERLEAVING_BUFFER_VARIANTS = (
    "你继续说，我顺着往下了解。",
    "这个我知道了，我们接着往下聊。",
)
ROTATING_ENDING_VARIANTS = (
    "那今天先聊到这儿，后面如果继续往下走，会先提前约时间再联系你。",
    "我们先聊到这儿，后面真要继续推进，也会在联系前先和你约个合适时间。",
    "先到这儿吧，后面如果还有需要继续沟通的地方，也会在联系前先跟你约时间。",
)


@dataclass
class OpeningIntentSignal:
    intent: str = ""
    confidence: float = 0.0
    secondary_intent: str | None = None
    parse_failed: bool = False
FAST_PATH_ACK_VARIANTS = {
    "sex": (
        "",
        "",
    ),
    "age": (
        "好，{value}是吧。",
        "行，那我大概知道了，{value}。",
    ),
    "location": (
        "好，那你现在主要在{value}这边。",
        "你现在在{value}是吧。",
    ),
    "education": (
        "好，学历这块是{value}。",
        "行，{value}是吧。",
    ),
    "occupation": (
        "好，你现在是做{value}的。",
        "行，你现在主要做{value}。",
    ),
    "marital_status": (
        "好，那你现在是{value}这个状态。",
        "行，婚况这块是{value}。",
    ),
}
FAST_PATH_PREFERENCE_ACK_VARIANTS = (
    "你这边更偏向{preference}，对吧。",
    "听起来你会更看重{preference}这一点。",
    "好，{preference}这个点我知道了。",
)
DIVORCE_CONFIRMATION_PROMPT_VARIANTS = (
    "可以的，我想先确认一下，你这边离婚手续已经办妥了吗？",
    "可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？",
    "可以的，我先确认下，你现在离婚手续是不是已经办妥了？",
)
DIVORCE_CONFIRMED_ACK_VARIANTS = {
    "location": (
        "好，那就行。你现在主要在哪个城市生活？",
        "那就没问题了。你现在是在哪个城市生活？",
    ),
    "education": (
        "好，那就行。你现在是什么学历？",
        "那就没问题了。你这边是什么学历？",
    ),
    "occupation": (
        "好，那就行。你现在是做什么工作的？",
        "那就没问题了。你现在主要做什么工作？",
    ),
    "marital_status": (
        "好，那我知道了。",
        "嗯，我知道了。",
    ),
    "contact": (
        "好，那就行。要是你愿意，留个电话也行。",
        "那就没问题了。你这边方便留个电话吗？",
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
        self.personality_profile = PersonalityProfile()
        self.profile_collection_coordinator = ProfileCollectionCoordinator(self)
        self.process_chat_turn_use_case = ProcessChatTurnUseCase(self)

        # 临时存储可能的拒绝字段
        self._temp_refused_fields = {}
        self._last_ai_failure_reason: Optional[str] = None
        self._last_validation_feedback_meta: Optional[Dict[str, Any]] = None
        self._last_opening_intent_signal: Optional[OpeningIntentSignal] = None

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

    def _select_model_for_turn(self, user_message: str, prompt: str) -> str:
        """
        拟人化优先：统一走主模型，避免快模型路由带来的表达质量波动。
        """
        return getattr(self.ai_service, "model_name", settings.model_name)

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

    def _is_risk_guard_triggered(self, user_message: str) -> bool:
        """高风险输入检测，仅用于决策打标。"""
        message = (user_message or "").strip()
        if not message:
            return False
        return any(
            [
                self._matches_any_pattern(message, SELF_HARM_GUARD_PATTERNS),
                self._matches_any_pattern(message, MEDICAL_GUARD_PATTERNS),
                self._matches_any_pattern(message, LEGAL_GUARD_PATTERNS),
                self._matches_any_pattern(message, OVERREACH_GUARD_PATTERNS),
                self._matches_any_pattern(message, AI_IDENTITY_GUARD_PATTERNS),
                self._matches_any_pattern(message, ABUSE_GUARD_PATTERNS),
            ]
        )

    def _is_boundary_pause_triggered(self, user_message: str, user_profile: Optional[UserProfile] = None) -> bool:
        """边界/顾虑输入检测，仅用于决策打标。"""
        message = (user_message or "").strip()
        if not message:
            return False
        # FAQ/联系方式偏好优先于 boundary pause，避免把“靠谱吗/安全吗/留微信可以吗”
        # 这类明确答疑或切流程请求误拦成固定安抚话术。
        if self._detect_priority_question_intent(message):
            return False
        if self.contact_service.prefers_wechat_over_phone(message, UserProfile(account_id="boundary_probe")):
            return False
        # 联系方式阶段中的拒绝，不走 boundary pause，避免吞掉“电话拒绝 -> 微信兜底”的自然转接。
        if user_profile is not None:
            contact_refusal_markers = [
                "不留电话", "不想留电话", "电话不方便",
                "不留微信", "不想留微信", "微信不方便",
            ]
            generic_contact_refusal_markers = [
                "不方便留", "不方便说", "先不留", "不想留", "不留呀", "不方便呀", "不方便呢",
            ]
            in_contact_stage = any(
                [
                    bool(user_profile.phone_ask_count > 0),
                    bool(user_profile.wechat_ask_count > 0),
                    bool(user_profile.rejected_phone),
                    bool(user_profile.rejected_wechat),
                ]
            )
            if in_contact_stage and (
                any(marker in message for marker in contact_refusal_markers)
                or any(marker in message for marker in generic_contact_refusal_markers)
            ):
                return False
        return self._matches_any_pattern(message, BOUNDARY_PAUSE_PATTERNS)

    @staticmethod
    def _looks_like_fake_info_message(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False

        age_match = re.search(r"(?:今年|我今年|年龄|岁数)?\s*(\d{1,4})\s*岁", message)
        if age_match:
            age_value = int(age_match.group(1))
            if age_value <= 10 or age_value >= 120:
                return True

        height_cm_match = re.search(r"(?:身高|高)\s*(\d{2,3})\s*(?:cm|厘米)?", message, re.IGNORECASE)
        if height_cm_match:
            height_value = int(height_cm_match.group(1))
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
        # FAQ 意图优先，避免把答疑请求误判为抱怨
        if self._detect_priority_question_intent(message):
            return False
        return self._matches_any_pattern(message, COMPLAINT_PATTERNS)

    def _detect_complaint_reason(self, user_message: str) -> Optional[str]:
        """
        检测用户投诉的具体原因。

        Returns:
            "repeat_ask" - 重复追问投诉（"不是说了吗/别再问了"）
            "over_questioning" - 问太多投诉（"查户口/太烦了"）
            None - 非投诉消息
        """
        message = (user_message or "").strip()
        if not message:
            return None
        # FAQ 意图优先，避免误判
        if self._detect_priority_question_intent(message):
            return None

        # 优先检测重复追问投诉
        if self._matches_any_pattern(message, REPEAT_ASK_COMPLAINT_PATTERNS):
            return "repeat_ask"

        # 检测问太多投诉
        if self._matches_any_pattern(message, COMPLAINT_PATTERNS):
            return "over_questioning"

        return None

    def _classify_withdraw_intent(self, user_message: str) -> Optional[str]:
        message = (user_message or "").strip()
        if not message:
            return None
        if self._detect_priority_question_intent(message):
            return None
        if self._matches_any_pattern(message, WITHDRAW_STRONG_PATTERNS):
            return "strong"
        if self._matches_any_pattern(message, WITHDRAW_SOFT_PATTERNS):
            return "soft"
        return None

    def _is_withdraw_or_stop_message(self, user_message: str) -> bool:
        return self._classify_withdraw_intent(user_message) is not None

    @staticmethod
    def _has_any_valid_contact(user_profile: Optional[UserProfile]) -> bool:
        if not user_profile:
            return False
        return bool(
            (user_profile.phone and user_profile.phone_collected)
            or (user_profile.wechat and user_profile.wechat_collected)
            or user_profile.collection_progress.get("contact", False)
        )

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
        if self._has_any_valid_contact(user_profile):
            return self.expectation_service.get_contact_completion_response(user_profile), True

        withdraw_count = user_profile.get_ask_count("conversation_end_intent")
        if self._reached_question_ceiling(user_profile) or withdraw_count >= 2:
            return random.choice(WITHDRAW_SOFT_CLOSE_VARIANTS), True

        return random.choice(WITHDRAW_RETAIN_VARIANTS), False

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
        normalized_message = re.sub(r"[\s,，。！？!?~～、]+", "", message)
        recent_responses = context.get("recent_responses") or []
        last_response = str(recent_responses[-1]).strip() if recent_responses else ""
        opening_profile_fields = self._extract_deterministic_profile_fields(message) if message_count == 0 else {}
        followup_topic = self._detect_followup_topic(
            message,
            user_profile,
            message_count=message_count,
            last_response=last_response,
        )
        context_ack_payload = self._build_context_ack_payload(
            followup_topic,
            user_message=message,
            user_profile=user_profile,
        )
        explicit_matchmaking_opening = (
            message_count <= 1
            and self._is_explicit_matchmaking_intent_message(message)
            and not opening_profile_fields
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
        )
        opening_clarify = (
            message_count == 0
            and self._should_use_opening_clarify(message)
            and not opening_profile_fields
            and not self._is_stable_opening_greeting(message)
            and not self._is_explicit_matchmaking_intent_message(message)
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
        )
        soft_opening_self_intro = (
            message_count <= 2
            and self._is_opening_probe_followup_message(message, last_response)
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
            and not opening_profile_fields
            and not self._extract_deterministic_profile_fields(message)
            and normalized_message
            in {
                "先了解下", "先了解一下", "了解下", "了解一下",
                "先看看", "看看情况", "问问情况", "先问问情况",
                "想了解下", "想了解一下", "先聊聊",
            }
        )
        pure_greeting_opening = (
            message_count == 0
            and self._is_stable_opening_greeting(message)
            and not opening_profile_fields
            and not self._is_explicit_matchmaking_intent_message(message)
        )
        noisy_greeting_clarify = (
            message_count == 0
            and self._is_noisy_opening_clarify_message(message)
            and not opening_profile_fields
            and not self._is_explicit_matchmaking_intent_message(message)
        )
        opening_service_confirmation = self._should_treat_as_opening_service_confirmation(
            user_profile,
            stage=stage,
            message_count=message_count,
            user_message=message,
            last_response=last_response,
        )
        mid_service_confirmation = self._should_treat_as_mid_service_confirmation(
            user_profile,
            stage=stage,
            message_count=message_count,
            user_message=message,
            last_response=last_response,
        )

        priority_question_intent = self._detect_priority_question_intent(message)
        intent = priority_question_intent or "general"
        risk = "none"
        next_action = "continue"
        contact_context = self._has_active_contact_context(user_profile, user_message=message)
        withdraw_intent = self._classify_withdraw_intent(message)

        if withdraw_intent and not self._is_risk_guard_triggered(message):
            return TurnDecision(
                intent="withdraw_or_stop",
                risk="withdraw",
                stage=stage,
                next_action="continue",
                primary_move="soft_hold",
                ask_field=None,
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 1,
                },
                followup_topic=None,
                context_ack_required=False,
                context_ack_type=None,
                context_ack_payload={},
            )

        if pure_greeting_opening:
            return TurnDecision(
                intent="opening_probe",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic=followup_topic,
            )

        if opening_clarify:
            return TurnDecision(
                intent="opening_clarify",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic="opening_clarify",
            )

        if noisy_greeting_clarify:
            return TurnDecision(
                intent="opening_clarify",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic="opening_clarify",
            )

        if opening_service_confirmation:
            return TurnDecision(
                intent="opening_light_consult",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic="opening_self_intro",
            )

        if mid_service_confirmation:
            return TurnDecision(
                intent="service_confirmation",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=True,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic=None,
            )

        if explicit_matchmaking_opening:
            return TurnDecision(
                intent="opening_self_intro",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic=followup_topic,
            )

        if soft_opening_self_intro:
            return TurnDecision(
                intent="opening_self_intro",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic=followup_topic,
            )

        opening_guard_intent = self.turn_intent_classifier.classify_opening_low_pressure(
            user_message=message,
            last_response=last_response,
            message_count=message_count,
            has_opening_fields=bool(opening_profile_fields),
            has_faq_intent=bool(priority_question_intent),
            has_boundary_pause=bool(self._is_boundary_pause_triggered(message, user_profile)),
            has_risk_guard=bool(self._is_risk_guard_triggered(message)),
        )
        if opening_guard_intent.intent == "low_pressure_opening":
            return TurnDecision(
                intent="opening_self_intro",
                risk="none",
                stage=stage,
                next_action="continue",
                primary_move="answer_then_pause",
                ask_field=None,
                prioritize_user_question=False,
                allow_contact_target=False,
                allow_medium_target=False,
                response_channel="quick_faq",
                tone_policy={
                    "ack_budget_per_n_turns": 3,
                    "max_question_per_turn": 1,
                    "enforce_contact_transition": False,
                    "core_streak_max": 3,
                },
                followup_topic="opening_self_intro",
            )

        # 联系方式上下文里，仅联系方式相关 FAQ 降级回主线；
        # 像“多久联系我”这类 timeline 问题仍应优先答疑。
        direct_exchange_faq = any(marker in message for marker in ("直接加", "对方微信", "互加", "直接联系对方"))
        if contact_context and intent in {"contact_exchange", "contact_why"} and not direct_exchange_faq:
            intent = "general"

        # 统一走主模型路径，避免轻量路径与主路径在字段状态和回复一致性上分叉。
        response_channel = "quick_faq" if intent != "general" else "model"

        primary_move = "ack_and_ask"
        prioritize_user_question = intent != "general"
        user_concern_type = None if intent == "general" else self._normalize_user_concern_type(intent)
        resume_profile_collection = self._is_resume_profile_collection_message(message)
        post_answer_reentry = self._is_post_answer_reentry_turn(message, last_response)
        allow_contact_target = True
        complaint_reason = self._detect_complaint_reason(message)
        is_complaint = complaint_reason is not None
        resume_target = None
        resume_mode = None
        resume_applied = False

        # Phase 2: 检查是否已在 repair_mode，如果是则应用冷却约束
        in_repair_mode = user_profile.repair_mode and user_profile.ask_cooldown_turns > 0

        # Phase 1: complaint / repair 意图处理
        if is_complaint:
            # 进入 repair_mode，设置冷却期
            if not in_repair_mode:
                user_profile.enter_repair_mode(
                    reason=complaint_reason,
                    cooldown_turns=3,  # 默认3轮冷却
                )
                in_repair_mode = True
                logger.info(f"[repair_mode] 用户投诉触发，进入修复模式，原因: {complaint_reason}")
            intent = "complaint"
            user_concern_type = "complaint"
            primary_move = "repair_and_release"
            allow_contact_target = False
            allow_medium_target = False
        elif self._is_risk_guard_triggered(message):
            risk = "high_risk"
            primary_move = "answer_then_pause"
            allow_contact_target = False
        elif self._is_boundary_pause_triggered(message, user_profile):
            risk = "boundary"
            primary_move = "soft_hold"
            allow_contact_target = False
        elif in_repair_mode:
            # 已在 repair_mode 中，继续应用约束
            # 检查是否有被禁止的追问意图
            if user_profile.is_ask_intent_blocked("ask_basic_profile"):
                primary_move = "ack_only"  # 只确认，不追问
                allow_contact_target = False
                allow_medium_target = False
                logger.info(f"[repair_mode] 冷却期内，禁止追问，剩余冷却轮数: {user_profile.ask_cooldown_turns}")

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
        )
        ask_field = policy_decision.main_target
        resume_target = user_profile.resume_profile_target
        resume_mode = user_profile.resume_profile_mode
        if contact_context and intent == "general" and risk == "none":
            ask_field = "contact"
        allow_contact_target = allow_contact_target and policy_decision.engagement_mode in {"full", "compact"}
        if policy_decision.next_mode in {"open_profile_repair", "low_pressure_chat", "terminate_conversion", "contact_hold"}:
            allow_contact_target = False
        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            next_action = "confirm_divorce_status"
            primary_move = "confirm_status_only"
            allow_contact_target = False
            allow_medium_target = False
        elif intent == "complaint":
            # complaint 意图保持 repair_and_release，不覆盖
            next_action = "repair_and_release"
            allow_contact_target = False
            allow_medium_target = False
        elif intent != "general":
            primary_move = "answer_then_pause"
            allow_contact_target = False
            allow_medium_target = False
        elif resume_profile_collection:
            primary_move = "light_followup"
            allow_contact_target = False
            allow_medium_target = False
        elif len(message) <= 4:
            primary_move = "light_followup"

        if policy_decision.next_mode == "open_profile_repair":
            ask_field = None
            allow_contact_target = False
            allow_medium_target = False
        elif policy_decision.next_mode in {"low_pressure_chat", "terminate_conversion"}:
            primary_move = "soft_hold"
            ask_field = None
            allow_contact_target = False
            allow_medium_target = False
        elif policy_decision.next_mode == "contact_hold":
            ask_field = None
            allow_contact_target = False
        elif policy_decision.next_mode == "contact_flow" and policy_decision.allow_contact_push:
            ask_field = "contact"

        if (
            prioritize_user_question
            and not contact_context
            and policy_decision.next_mode not in {"contact_flow", "terminate_conversion"}
            and policy_decision.main_target
        ):
            user_profile.set_resume_profile_target(
                policy_decision.next_mode,
                policy_decision.main_target,
                user_concern_type or "faq",
            )
            resume_target = policy_decision.main_target
            resume_mode = policy_decision.next_mode

        if (
            not prioritize_user_question
            and not contact_context
            and not self.collection_policy.has_ongoing_contact_flow(user_profile)
            and user_profile.resume_profile_target
            and not self.collection_policy.is_field_covered(user_profile, user_profile.resume_profile_target)
        ):
            ask_field = user_profile.resume_profile_target
            primary_move = "light_followup"
            allow_contact_target = False
            allow_medium_target = False
            resume_target = user_profile.resume_profile_target
            resume_mode = user_profile.resume_profile_mode
            resume_applied = True
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
            )
            ask_field = policy_decision.main_target

        tone_policy = {
            "ack_budget_per_n_turns": 3,
            "max_question_per_turn": 1,
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
            repair_cooldown_remaining=user_profile.ask_cooldown_turns,
            user_concern_type=user_concern_type,
            resume_mode=resume_mode,
            resume_target=resume_target,
            resume_applied=resume_applied,
            followup_topic=followup_topic,
            context_ack_required=bool(followup_topic),
            context_ack_type=followup_topic,
            context_ack_payload=context_ack_payload,
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
        logger.info(
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

    def _detect_priority_question_intent(self, user_message: str) -> str | None:
        """
        统一的用户疑问/顾虑识别入口。

        识别顺序：
        1. FAQ 词库/语义规则
        2. timeline 业务语义兜底
        """
        intent = self.user_question_service.detect_quick_faq_intent(user_message)
        if intent:
            return intent
        if self.expectation_service.is_matching_timeline_question(user_message):
            return "timeline"
        return None

    def _get_priority_question_response(
        self,
        user_message: str,
        user_profile: UserProfile,
        *,
        repeat_count: int = 1,
        recent_responses: tuple[str, ...] | list[str] | None = None,
    ) -> str | None:
        intent = self._detect_priority_question_intent(user_message)
        if not intent:
            return None
        if intent == "timeline":
            return self.expectation_service.get_matching_timeline_response(user_profile)
        return self.user_question_service.get_quick_faq_response(
            user_message,
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
                r"(找对象|想找对象|帮我找个对象|相亲|脱单|找另一半|找个男朋友|找个女朋友|认真聊聊)",
                message,
            )
        )

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

    def _detect_followup_topic(
        self,
        user_message: str,
        user_profile: UserProfile,
        *,
        message_count: int = 0,
        last_response: str = "",
    ) -> Optional[str]:
        message = str(user_message or "").strip()
        if not message:
            return None

        deterministic_fields = self._extract_deterministic_profile_fields(message)
        deterministic_fields = self._apply_extraction_guards(deterministic_fields, message, last_response=last_response)

        if self._matches_any_pattern(message, TOPIC_SHIFT_PATTERNS):
            return "topic_shift"

        if self._is_boundary_pause_triggered(message, user_profile):
            if deterministic_fields:
                return "profile_partial_with_boundary"
            return "boundary_pause"

        if user_profile.occupation and self._matches_any_pattern(message, WORK_BUSY_PATTERNS):
            return "work_busy"

        if user_profile.location and self._matches_any_pattern(message, LOCATION_REUSE_PATTERNS):
            return "location_reuse"

        if user_profile.partner_requirement and self._matches_any_pattern(message, PREFERENCE_REUSE_PATTERNS):
            return "preference_reuse"

        if message_count >= 1 and user_profile.location and "那边" in message:
            return "location_reuse"

        if message_count >= 1 and user_profile.partner_requirement and any(token in message for token in ("推荐", "合适", "这类", "这种")):
            return "preference_reuse"

        if message_count <= 1:
            lightweight_preference = self._extract_simple_partner_requirement(message)
            if deterministic_fields or lightweight_preference:
                return "opening_profile_ack"

        return None

    def _build_context_ack_payload(
        self,
        followup_topic: Optional[str],
        *,
        user_message: str,
        user_profile: UserProfile,
    ) -> Dict[str, Any]:
        if not followup_topic:
            return {}

        payload: Dict[str, Any] = {}
        if followup_topic == "work_busy":
            payload["occupation"] = str(user_profile.occupation or "").strip()
        elif followup_topic == "location_reuse":
            payload["location"] = str(user_profile.location or "").strip()
        elif followup_topic == "preference_reuse":
            payload["preference"] = self._render_preference_for_ack(str(user_profile.partner_requirement or "").strip())
        elif followup_topic == "profile_partial_with_boundary":
            payload["field_ack"] = self._build_lightweight_field_ack_from_message(user_message, user_profile)
        elif followup_topic == "opening_profile_ack":
            payload["field_ack"] = self._build_opening_profile_ack_from_message(user_message)
        return payload

    @staticmethod
    def _pick_seeded_variant(key: str, candidates: tuple[str, ...], seed_hint: str) -> str:
        if not candidates:
            return ""
        digest = hashlib.sha1(f"{key}:{seed_hint}".encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(candidates)
        return candidates[idx]

    def _render_context_ack(
        self,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        user_message: str,
    ) -> str:
        ack_type = str(turn_decision.context_ack_type or "").strip()
        if not ack_type:
            return ""

        payload = dict(turn_decision.context_ack_payload or {})
        seed_hint = f"{ack_type}:{user_message}:{user_profile.account_id}:{user_profile.updated_at.isoformat()}"

        if ack_type == "work_busy":
            occupation = str(payload.get("occupation") or user_profile.occupation or "").strip()
            if occupation:
                variants = tuple(v.format(occupation=self._render_occupation_for_ack(occupation)) for v in WORK_BUSY_OCCUPATION_ACK_VARIANTS)
                return self._pick_seeded_variant("context:work_busy_occ", variants, seed_hint)
            return self._pick_seeded_variant("context:work_busy", WORK_BUSY_ACK_VARIANTS, seed_hint)

        if ack_type == "location_reuse":
            location = str(payload.get("location") or user_profile.location or "").strip()
            if not location:
                return ""
            variants = tuple(v.format(location=location) for v in LOCATION_REUSE_ACK_VARIANTS)
            return self._pick_seeded_variant("context:location_reuse", variants, seed_hint)

        if ack_type == "preference_reuse":
            preference = str(payload.get("preference") or self._render_preference_for_ack(str(user_profile.partner_requirement or "").strip())).strip()
            if not preference:
                return ""
            variants = tuple(v.format(preference=preference) for v in PREFERENCE_REUSE_ACK_VARIANTS)
            return self._pick_seeded_variant("context:preference_reuse", variants, seed_hint)

        if ack_type == "boundary_pause":
            return self._pick_seeded_variant("context:boundary", BOUNDARY_ACK_VARIANTS, seed_hint)

        if ack_type == "topic_shift":
            return self._pick_seeded_variant("context:topic_shift", TOPIC_SHIFT_ACK_VARIANTS, seed_hint)

        if ack_type == "profile_partial_with_boundary":
            field_ack = str(payload.get("field_ack") or self._build_lightweight_field_ack_from_message(user_message, user_profile)).strip()
            if not field_ack:
                return self._pick_seeded_variant("context:boundary", BOUNDARY_ACK_VARIANTS, seed_hint)
            variants = tuple(v.format(field_ack=field_ack) for v in PROFILE_PARTIAL_BOUNDARY_ACK_VARIANTS)
            return self._pick_seeded_variant("context:partial_boundary", variants, seed_hint)

        if ack_type == "opening_profile_ack":
            field_ack = str(payload.get("field_ack") or self._build_opening_profile_ack_from_message(user_message)).strip()
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
        payload = dict(turn_decision.context_ack_payload or {})

        if ack_type == "work_busy":
            occupation = str(payload.get("occupation") or user_profile.occupation or "").strip()
            return any(token and token in text for token in (occupation, "工作", "忙", "节奏"))
        if ack_type == "location_reuse":
            location = str(payload.get("location") or user_profile.location or "").strip()
            return any(token and token in text for token in (location, "那边", "同城", "本地"))
        if ack_type == "preference_reuse":
            preference = str(payload.get("preference") or self._render_preference_for_ack(str(user_profile.partner_requirement or "").strip())).strip()
            pref_tokens = [token for token in re.split(r"[，,、\s]+", preference) if token]
            pref_tokens.extend(["看重", "偏向", "合拍", "推荐"])
            return any(token and token in text for token in pref_tokens)
        if ack_type == "opening_profile_ack":
            field_ack = str(payload.get("field_ack") or "").strip()
            return bool(field_ack) and any(token and token in text for token in (field_ack, "知道了", "接住", "这点"))
        if ack_type in {"boundary_pause", "topic_shift", "profile_partial_with_boundary"}:
            boundary_tokens = ("先不追", "不勉强", "没关系", "先不聊", "先收住", "舒服的节奏", "先顺着")
            if ack_type == "profile_partial_with_boundary":
                field_ack = str(payload.get("field_ack") or "").strip()
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
        message = str(user_message or "").strip()
        if not message:
            return False
        return any(pattern in message for pattern in RESUME_PROFILE_COLLECTION_PATTERNS)

    @staticmethod
    def _is_acknowledgement_only_message(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False

        normalized = re.sub(r"[，。！？!?~～、\s]+", "", message)
        acknowledgement_messages = {
            "好",
            "好的",
            "知道了",
            "了解了",
            "明白了",
            "行",
            "可以",
            "嗯",
            "嗯嗯",
            "哦",
            "收到",
            "没问题",
            "好哦",
        }
        return normalized in acknowledgement_messages

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
            "你可以放心",
        )
        if self._detect_priority_question_intent(previous_response):
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
                "这条我得先把安全放前面。你先保证安全，"
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
            return "你会担心隐私，这很正常。这个你可以放心，我不会乱接你的话。"
        if self._matches_any_pattern(message, ABUSE_GUARD_PATTERNS):
            return "我先接住你这句。你要是还想聊，我们就顺着你现在想说的来。"
        return "这句我先接住。你要是愿意，可以换个你更想聊的点。"

    def _get_boundary_pause_response(self, user_message: str) -> str:
        message = str(user_message or "").strip()
        if "电话" in message and "不方便" in message:
            return "行，电话这块你现在不方便也没事。等你哪天觉得方便了再说，按你方便的方式来就行。"
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

    def _apply_income_appreciation_policy(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """高收入场景下补一小句克制认可，避免完全无情绪反馈。"""
        text = str(response or "").strip()
        if not text:
            return text

        all_fields = (collection_result or {}).get("all_fields") or []
        extracted_fields = {
            str(item.get("field") or "").strip()
            for item in all_fields
            if isinstance(item, dict)
        }
        if "monthly_income" not in extracted_fields:
            return text

        income_amount = self.expectation_service.parse_monthly_income_amount(user_profile.monthly_income)
        if income_amount is None or income_amount < 30000:
            return text

        if any(marker in text for marker in ("还不错", "挺可以", "挺不错", "条件挺", "不错呀")):
            return text
        if self._contains_contact_push_markers(text):
            return text

        compliment = "那还不错呀。"
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
        if not next_field or next_field == current_ask_field:
            if self.collection_policy.can_actively_ask(user_profile, "marital_status") and current_ask_field != "marital_status":
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
            return self._build_interleaving_followup(
                user_profile,
                user_message,
                main_target=next_field,
                preferred_side_target=decision.side_target,
                allow_medium_target=allow_medium_target,
            )
        return self._build_policy_field_prompt(next_field, user_profile, user_message=user_message)

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
                    host_field = self.collection_policy.get_medium_transition_host(user_profile, candidate)
                    if host_field:
                        return self._build_interleaving_followup(
                            user_profile,
                            user_message,
                            main_target=host_field,
                            preferred_side_target=candidate,
                            allow_medium_target=allow_medium_target,
                        )
                return self._build_policy_field_prompt(candidate, user_profile, user_message=user_message)

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
                return self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=decision.main_target,
                    preferred_side_target=decision.side_target,
                    allow_medium_target=allow_medium_target,
                )
            return self._build_policy_field_prompt(decision.main_target, user_profile, user_message=user_message)

        forced_target = decision.forced_cover_target
        if forced_target and self.collection_policy.can_actively_ask(user_profile, forced_target):
            logger.info(
                "[重问纠偏] 回复追问了已收字段 %s，改为剩余覆盖目标 %s",
                sorted(repeated_fields),
                forced_target,
            )
            host_field = self.collection_policy.get_medium_transition_host(user_profile, forced_target)
            if host_field:
                return self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=host_field,
                    preferred_side_target=forced_target,
                    allow_medium_target=allow_medium_target,
                )
            return self._build_policy_field_prompt(forced_target, user_profile, user_message=user_message)

        if self.collection_policy.can_enter_contact(user_profile):
            logger.info(
                "[重问纠偏] 回复追问了已收字段 %s，改为联系方式入口",
                sorted(repeated_fields),
            )
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)

        return text

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

        followup = self._build_policy_field_prompt(next_field, user_profile, user_message=user_message).strip()
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

        all_fields = [
            item for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        if len(all_fields) < 2:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if ask_field not in asked_fields:
            return text

        candidate_order = ("occupation", "location", "marital_status", "education", "age", "sex")
        chosen_ack = ""
        for field_name in candidate_order:
            matched = next((item for item in all_fields if str(item.get("field") or "").strip() == field_name), None)
            if not matched:
                continue
            ack = self._build_contextual_short_ack(field_name, matched.get("value"))
            if ack:
                chosen_ack = ack.strip()
                break

        if not chosen_ack:
            return text

        normalized_text = text.replace(" ", "")
        normalized_ack = chosen_ack.replace(" ", "")
        if normalized_ack in normalized_text:
            return text
        if self._response_already_acks_field(text, field_name, matched.get("value")):
            return text

        logger.info(
            "[多字段承接] 本轮提取到多个字段，先承接 %s 再追问 %s",
            chosen_ack,
            ask_field,
        )
        return f"{chosen_ack} {text}".strip()

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
        ack = self._build_contextual_short_ack(field_name, all_fields[0].get("value")).strip()
        if not ack:
            return text

        normalized_text = text.replace(" ", "")
        normalized_ack = ack.replace(" ", "")
        if normalized_ack in normalized_text:
            return text
        if self._response_already_acks_field(text, field_name, all_fields[0].get("value")):
            return text

        logger.info(
            "[单字段承接] 本轮提取到 %s，先承接再追问 %s",
            field_name,
            ask_field,
        )
        return f"{ack} {text}".strip()

    def _ensure_humanlike_memory_ack(self, user_message: str, user_profile: UserProfile, response: str) -> str:
        message = str(user_message or "").strip()
        if not response:
            return response

        if "查户口" in message or "问这么细" in message:
            return f"我知道你会觉得我问得细一点，不过也是想尽量聊得更匹配。{response}"

        location = str(getattr(user_profile, "location", "") or "").strip()
        if location and location not in response:
            return f"你现在在{location}这边，这个我有听进去。{response}"

        occupation = str(getattr(user_profile, "occupation", "") or "").strip()
        if occupation and occupation not in response and ("工作" in message or "忙" in message):
            return f"你平时做{occupation}，我知道你工作节奏可能会比较忙。{response}"

        preference = str(getattr(user_profile, "partner_requirement", "") or "").strip()
        if preference and preference not in response:
            return f"你前面提过更偏向{preference}这一类，这个我知道。{response}"

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
        timeout_settings = self.ai_service.resolve_timeout_settings()
        soft_timeout = max(0.5, float(timeout_settings["chat_ai_timeout"]))
        hard_timeout = float(timeout_settings["chat_ai_hard_timeout"])
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

    def _should_run_opening_intent_detection(
        self,
        conversation_context: Optional[Dict[str, Any]],
        user_profile: UserProfile,
    ) -> bool:
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

    @staticmethod
    def _is_service_confirmation_like(user_message: str) -> bool:
        message = str(user_message or "").strip().lower()
        if not message:
            return False
        compact = re.sub(r"[\s,，。！？!?~～、：:；;（）()\"'`]+", "", message)
        if not compact:
            return False
        if any(re.search(pattern, compact) for pattern in SERVICE_CONFIRMATION_DIRECT_PATTERNS):
            return True
        has_subject = any(token in compact for token in SERVICE_CONFIRMATION_SUBJECT_PATTERNS)
        has_service = any(token in compact for token in SERVICE_CONFIRMATION_SERVICE_PATTERNS)
        has_question = any(token in compact for token in SERVICE_CONFIRMATION_QUESTION_PATTERNS)
        return has_subject and has_service and has_question

    @staticmethod
    def _count_collected_profile_fields(user_profile: UserProfile) -> int:
        count = 0
        for field in ("sex", "age", "location", "education", "occupation", "marital_status", "monthly_income", "partner_requirement"):
            value = getattr(user_profile, field, None)
            if str(value or "").strip():
                count += 1
                continue
            if user_profile.collection_progress.get(field):
                count += 1
        return count

    def _should_treat_as_opening_service_confirmation(
        self,
        user_profile: UserProfile,
        *,
        stage: str,
        message_count: int,
        user_message: str,
        last_response: str,
    ) -> bool:
        if not self._is_service_confirmation_like(user_message):
            return False
        if stage != "opening":
            return False
        if message_count > 1:
            return False
        if self._count_collected_profile_fields(user_profile) > 0:
            return False
        if self._extract_deterministic_profile_fields(user_message):
            return False
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return False
        if self._is_risk_guard_triggered(user_message):
            return False
        if self._detect_priority_question_intent(user_message):
            return False
        if last_response and self._detect_which_field_is_asked(last_response):
            return False
        return True

    def _should_treat_as_mid_service_confirmation(
        self,
        user_profile: UserProfile,
        *,
        stage: str,
        message_count: int,
        user_message: str,
        last_response: str,
    ) -> bool:
        if not self._is_service_confirmation_like(user_message):
            return False
        if self._should_treat_as_opening_service_confirmation(
            user_profile,
            stage=stage,
            message_count=message_count,
            user_message=user_message,
            last_response=last_response,
        ):
            return False
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return False
        if self._is_risk_guard_triggered(user_message):
            return False
        if self._count_collected_profile_fields(user_profile) > 0:
            return True
        return bool(last_response and self._detect_which_field_is_asked(last_response))

    def _build_service_confirmation_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        message_count: int,
        last_response: str = "",
    ) -> str:
        ack = random.choice(SERVICE_CONFIRMATION_MID_ACK_VARIANTS).strip()
        previous_asked_field = self._detect_which_field_is_asked(last_response)
        if (
            previous_asked_field
            and previous_asked_field != "contact"
            and self.collection_policy.can_actively_ask(user_profile, previous_asked_field)
        ):
            followup = self._build_policy_field_prompt(previous_asked_field, user_profile, user_message=user_message).strip()
            if followup:
                return f"{ack} {followup}".strip()
        unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core_fields:
            next_core = unresolved_core_fields[0]
            if self.collection_policy.can_actively_ask(user_profile, next_core):
                followup = self._build_policy_field_prompt(next_core, user_profile, user_message=user_message).strip()
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
            followup = self._build_policy_field_prompt(next_field, user_profile, user_message=user_message).strip()
            if followup:
                return f"{ack} {followup}".strip()
        return ack

    def _augment_prompt_for_opening_intent_detection(self, prompt: str) -> str:
        instruction = """
【开场意图识别】
如果当前仍处于开场前两轮，请先判断这句用户输入的开场意图，并在回复最前面输出：
<opening_intent>{"intent":"意图名","confidence":0.00,"secondary_intent":null}</opening_intent>

可选意图：
- opening_greeting
- opening_light_consult
- explicit_matchmaking_opening
- low_pressure_opening
- opening_faq
- opening_spam_or_promo
- opening_clarify
- opening_profile_provided
- opening_boundary_or_contact_refusal
- opening_mixed_intent
- opening_emotional_or_defensive
- opening_reverse_question
- opening_proxy_inquiry
- opening_eligibility_concern
- opening_resource_request
- opening_ambiguous_short
- opening_test_or_playful
- opening_hybrid_promo_real

要求：
1. 只输出一个主意图；如果确实混合，再给 secondary_intent。
2. 输出完 <opening_intent> 后，紧接着输出给用户看的自然回复。
3. 如果是 low_pressure_opening，不要直接追问 sex/age/location/education/occupation/contact。
4. 如果是 opening_faq，先答问题，不要直接切资料。
5. 如果是 opening_boundary_or_contact_refusal，先接住边界，不要推进电话微信或资料。
"""
        return f"{instruction.strip()}\n\n{prompt}"

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
        required_fields = "；".join([main_prompt_label, *side_prompt_labels])
        return (
            "【当前轮生成模式：PROFILE_BRIDGE（高优先级）】\n"
            "这条模式优先级高于通用的泛化融合追问风格。\n"
            f"用户这轮刚提供了这些信息：{summary}。\n"
            "本轮请顺着这些已给信息继续聊，不要先机械复述资料，也不要脱离上下文直接裸问。\n"
            f"本轮必须同时问到这些内容：{required_fields}。\n"
            "要求：\n"
            f"1. 以“{main_prompt_label}”为主问题，并把“{'；'.join(side_prompt_labels)}”自然带在同一句或紧邻句里一起问。\n"
            "2. 问法必须利用用户刚给的信息做桥接，比如顺着城市或当前状态继续聊，但不要写成固定模板。\n"
            "3. 如果回复里没有利用上面至少一项刚给信息，就算本轮生成不合格。\n"
            "4. 不要漏掉必须一起带出的相近字段，不要只问主字段。\n"
            "5. 保持口语化、像顺着聊下去，优先 1 句完成，不要列表，不要复述全部资料。\n"
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
        if not side_target:
            return {}

        prompt_label_map = {
            "occupation": "工作/做什么",
            "education": "学历/教育背景",
            "age": "年龄/年龄段",
            "location": "城市/常住地",
            "marital_status": "现在是否单身/婚况",
        }
        side_label_map = {
            "monthly_income": "月薪/收入区间",
            "partner_requirement": "择偶要求/更看重哪一点",
            "marital_status": "感情状态/是否单身",
        }
        if not self.collection_policy.can_actively_ask(user_profile, side_target):
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

        extracted = self._extract_deterministic_profile_fields(user_message)
        extracted = self._apply_extraction_guards(extracted, user_message)
        if not extracted:
            extracted = {}
        if not extracted.get("marital_status"):
            message = str(user_message or "").strip()
            if re.search(r"(目前|现在)?一个人(生活|过|在)?", message) or "单着" in message:
                extracted["marital_status"] = "单身"
        if turn_decision.ask_field == "occupation" and extracted.get("occupation"):
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
        if not bridge_instruction:
            return prompt
        return f"{bridge_instruction.strip()}\n\n{prompt}"

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
    ) -> str:
        text = str(response or "").strip()
        if not text or not signal or signal.parse_failed or signal.confidence < 0.6:
            return text
        if signal.intent == "opening_greeting":
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return self.greeting_service.get_greeting_response(user_message, seed_hint=seed_hint)
        if signal.intent in {"explicit_matchmaking_opening", "low_pressure_opening", "opening_light_consult"}:
            if self._contains_contact_push_markers(text) or self._detect_asked_fields_in_response(text):
                return self.greeting_service.get_open_self_intro_response(seed_hint=seed_hint)
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

    def _needs_style_retry(
        self,
        natural_response: str,
        *,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        text = self._clean_response(natural_response)
        if not text:
            return False
        if any(phrase in text for phrase in STYLE_RETRY_BLOCKED_PHRASES):
            return True

        preferences = (conversation_context or {}).get("preferences") or {}
        recent_signatures = preferences.get("recent_prompt_signatures") or []
        current_signature = self.dialogue_manager.build_prompt_signature(text)
        if current_signature and current_signature in recent_signatures[-2:]:
            return True

        recent_responses = (conversation_context or {}).get("recent_responses") or []
        recent_clean = [self._clean_response(item) for item in recent_responses[-2:] if str(item or "").strip()]
        current_opening = text[:12]
        if any(prev[:12] == current_opening for prev in recent_clean if len(prev) >= 6 and len(text) >= 6):
            return True

        return False

    async def _rewrite_response_for_style(
        self,
        *,
        natural_response: str,
        account_id: str,
        user_message: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        ask_field: Optional[str] = None,
    ) -> str:
        recent_responses = (conversation_context or {}).get("recent_responses") or []
        recent_text = " / ".join(self._clean_response(item) for item in recent_responses[-2:] if str(item or "").strip()) or "-"
        prompt = (
            "你在继续同一轮婚恋咨询聊天，请只重写给用户看的那一句或两句中文回复，不要输出extract，不要解释原因。\n"
            "要求：\n"
            "1. 保持原本要问的核心问题不变，只改说法。\n"
            "2. 更像真人聊天，先承接，再自然发问。\n"
            "3. 不要复用这些固定句：'你好呀～对了，想问下'、'对了，想问下'、'方便说下'、'我再确认一下'、'学历这块'、'婚况这块'。\n"
            "4. 如果涉及婚况，只问是否单身状态，不要并列说未婚和离异。\n"
            "5. 不要照抄最近两轮回复的开头。\n"
            f"本轮目标字段：{ask_field or '-'}\n"
            f"用户原话：{user_message or '-'}\n"
            f"最近两轮回复：{recent_text}\n"
            f"待重写原句：{natural_response or '-'}\n"
        )
        try:
            rewritten = await self.ai_service.generate_response(
                message=prompt,
                system_prompt="你是一个说中文的AI助手，请只输出重写后的中文回复。",
                max_tokens=160,
                timeout=max(0.5, float(self.ai_service.resolve_timeout_settings()["chat_ai_timeout"])),
                model_name=self._select_model_for_turn(user_message, prompt),
            )
            return self._clean_response(rewritten).strip()
        except Exception as exc:
            logger.warning("[话术重写] AI 重写失败: %s", exc)
            return ""

    async def _stabilize_style_response(
        self,
        response: str,
        *,
        account_id: str,
        user_message: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        ask_field: Optional[str] = None,
    ) -> str:
        natural_response, extract_block = self._split_response_and_extract(response)
        if not natural_response or not self._needs_style_retry(natural_response, conversation_context=conversation_context):
            return response

        rewritten = await self._rewrite_response_for_style(
            natural_response=natural_response,
            account_id=account_id,
            user_message=user_message,
            conversation_context=conversation_context,
            ask_field=ask_field,
        )
        if not rewritten:
            return response
        if extract_block:
            return f"{rewritten}\n{extract_block}"
        return rewritten

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

        ack = self._build_lightweight_field_ack_from_message(user_message, user_profile)
        if not ack:
            return response

        text = self._clean_response(natural_response)
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
        normalized_text = str(text or "").strip()
        normalized_user_message = str(user_message or "").strip()
        if not normalized_text or not normalized_user_message:
            return False

        head = normalized_text[:32]
        if head.startswith(("好，", "好。", "好的", "嗯，", "嗯。", "明白", "知道", "收到", "深圳", "本科", "90后", "男生", "女生", "单身")):
            return True

        if ack and ack[:4] in head:
            return True

        short_answer_aliases = {
            "男的": ("男的", "男生", "男性", "你是男"),
            "女的": ("女的", "女生", "女性", "你是女"),
            "男": ("男", "男生", "男性", "你是男"),
            "女": ("女", "女生", "女性", "你是女"),
            "单身": ("单身", "未婚"),
            "未婚": ("未婚", "单身"),
        }
        candidate_tokens = short_answer_aliases.get(normalized_user_message, (normalized_user_message,))
        return any(token and token in head for token in candidate_tokens)

    @staticmethod
    def _collapse_duplicate_ack_segments(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        natural_response, extract_block = ChatService._split_response_and_extract(text)
        if not natural_response:
            return text

        parts = [segment.strip() for segment in re.split(r"(?<=[。！？?!])\s*", natural_response) if segment.strip()]
        if len(parts) < 2:
            return text

        collapsed: list[str] = []
        previous_field: Optional[str] = None
        previous_is_ack = False

        def detect_ack_field(segment: str) -> Optional[str]:
            if any(token in segment for token in ("男生", "女生", "男的", "女的")):
                return "sex"
            if any(token in segment for token in ("90后", "80后", "00后", "岁")):
                return "age"
            if any(token in segment for token in ("深圳", "广州", "上海", "北京", "杭州", "成都")):
                return "location"
            if any(token in segment for token in ("本科", "大专", "硕士", "博士")):
                return "education"
            if "单身" in segment or "离异" in segment or "未婚" in segment:
                return "marital_status"
            return None

        def is_ack_segment(segment: str) -> bool:
            if "？" in segment or "?" in segment:
                return False
            return any(
                token in segment
                for token in (
                    "明白了", "知道了", "是吧", "我知道了", "我记住了", "好嘞", "好，", "好。", "好的", "收到",
                    "你这边是", "你是", "嗯嗯我知道啦", "你说的这些我都记下啦", "这个我知道了", "这个点我记住了",
                )
            )

        def question_segment_repeats_ack(segment: str, field: Optional[str]) -> bool:
            if not field or ("？" not in segment and "?" not in segment):
                return False
            prefix = re.split(r"[？?]", segment, maxsplit=1)[0]
            return detect_ack_field(prefix) == field and any(
                token in prefix for token in ("好", "好的", "明白", "知道", "是吧", "你是", "你这边是")
            )

        for part in parts:
            current_field = detect_ack_field(part)
            current_is_ack = is_ack_segment(part)
            if collapsed and previous_is_ack and current_is_ack:
                if previous_field and not current_field:
                    previous_is_ack = current_is_ack
                    continue
                if current_field and not previous_field:
                    collapsed[-1] = part
                    previous_field = current_field
                    previous_is_ack = current_is_ack
                    continue
            if collapsed and previous_is_ack and current_is_ack and previous_field and current_field == previous_field:
                collapsed[-1] = part
                previous_field = current_field
                previous_is_ack = current_is_ack
                continue
            if collapsed and previous_is_ack and previous_field and question_segment_repeats_ack(part, previous_field):
                collapsed[-1] = part
                previous_field = current_field or previous_field
                previous_is_ack = False
                continue
            collapsed.append(part)
            previous_field = current_field
            previous_is_ack = current_is_ack

        merged = " ".join(collapsed).strip()
        if extract_block:
            return f"{merged}\n{extract_block}"
        return merged

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
            "办妥了",
            "办好了",
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
            r"办[妥完][了啦呀啊哈]*",
            r"都[弄办处][好完妥][了啦呀啊哈]*",
            r"恢复单身",
            r"离干净了",
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
        return "离婚手续" in text and any(token in text for token in ("办妥", "办好", "办完"))

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

        for field in ("occupation", "education", "location", "monthly_income", "contact"):
            if field == "contact":
                if self.collection_policy.can_enter_contact(user_profile):
                    return "contact"
                continue
            if self.collection_policy.can_actively_ask(user_profile, field):
                return field
        return None

    @staticmethod
    def _looks_like_truncated_response(response: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return True
        return any(text.endswith(ending) for ending in DELIVERY_DANGLING_ENDINGS)

    def _is_delivery_viable(self, response: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return False
        return not self._looks_like_truncated_response(text)

    def _detect_which_field_is_asked(self, ai_response: str) -> Optional[str]:
        """
        检测 AI 回复中明确追问的字段（用于短答槽位绑定）。

        优先级：monthly_income > partner_requirement > sex > age > location > education > occupation > marital_status

        Args:
            ai_response: AI 回复文本

        Returns:
            被追问的字段名，或 None
        """
        text = str(ai_response or "").lower()
        if not text:
            return None

        detection_text = text

        occupation_patterns = [
            r"做什么工作", r"职业", r"从事", r"做哪行", r"做哪方面工作", r"主要做哪方面工作",
        ]
        income_patterns = [
            r"月收入", r"收入", r"月薪", r"工资", r"赚", r"多少钱",
            r"收入.*[？?]", r"月薪.*[？?]",
        ]
        asks_occupation = any(re.search(pattern, detection_text) for pattern in occupation_patterns)
        asks_income = any(re.search(pattern, detection_text) for pattern in income_patterns)
        if asks_occupation and asks_income:
            return "occupation"

        # 按优先级检测
        # 收入（最高优先级，因为容易与其他数字混淆）
        for pattern in income_patterns:
            if re.search(pattern, detection_text):
                return "monthly_income"

        # 性别
        sex_patterns = [
            r"男生还是女生",
            r"男的还是女的",
            r"你是男",
            r"你是女",
            r"性别",
            r"你这边是男生",
            r"你这边是女生",
            r"男生对吧",
            r"女生对吧",
        ]
        for pattern in sex_patterns:
            if re.search(pattern, detection_text):
                return "sex"

        partner_requirement_patterns = [
            r"另一半",
            r"有什么要求",
            r"看重哪",
            r"更在意哪",
            r"想找个什么样",
            r"择偶",
        ]
        for pattern in partner_requirement_patterns:
            if re.search(pattern, detection_text):
                return "partner_requirement"

        # 年龄
        age_patterns = [
            r"多大", r"年龄", r"几岁", r"岁数", r"出生", r"多老",
            r"年纪", r"年龄.*[？?]",
        ]
        for pattern in age_patterns:
            if re.search(pattern, detection_text):
                return "age"

        # 城市
        location_patterns = [
            r"哪个城市", r"在哪", r"在哪个城市", r"工作生活", r"生活.*城市",
            r"城市.*[？?]", r"哪里.*[？?]",
        ]
        for pattern in location_patterns:
            if re.search(pattern, detection_text):
                return "location"

        # 学历
        education_patterns = [
            r"学历", r"什么学历", r"毕业", r"大学", r"本科", r"研究生", r"博士",
            r"学历.*[？?]",
        ]
        for pattern in education_patterns:
            if re.search(pattern, detection_text):
                return "education"

        # 职业
        occupation_patterns = [
            r"做什么工作", r"职业", r"工作.*[？?]", r"从事", r"做哪行", r"做哪方面工作", r"主要做哪方面工作",
        ]
        for pattern in occupation_patterns:
            if re.search(pattern, detection_text):
                return "occupation"

        # 婚姻状态
        marital_patterns = [
            r"婚", r"单身", r"离异", r"未婚", r"结婚", r"婚姻",
        ]
        for pattern in marital_patterns:
            if re.search(pattern, detection_text):
                return "marital_status"

        return None

    @staticmethod
    def _response_mentions_phone_request(response: str) -> bool:
        text = str(response or "")
        return any(marker in text for marker in ("电话", "手机号", "号码"))

    @staticmethod
    def _response_mentions_wechat_request(response: str) -> bool:
        text = str(response or "")
        return "微信" in text

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
        if not self._is_delivery_viable(final_response):
            return user_profile

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return user_profile

        updated = False
        if action_value in {"ask_phone", "persuade_phone"} and self._response_mentions_phone_request(final_response):
            previous = user_profile.phone_ask_count
            self.contact_service.record_ask(user_profile, "phone")
            updated = user_profile.phone_ask_count != previous
        elif action_value in {"ask_wechat", "persuade_wechat"} and self._response_mentions_wechat_request(final_response):
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
            last_response=last_response,
            extraction_meta=extraction_meta,
            turn_id=turn_id,
        )

        # process_extracted_data 通过 user_service 持久化字段，刷新后再做收尾判断，
        # 否则同一轮新收集到的年龄/身高/联系方式会被旧 profile 漏掉。
        user_profile = await self.user_service.get_user_profile(account_id)

        if self._looks_like_fake_info_message(user_message):
            ending_info = self.ending_service.build_ending_info("fake_info", user_profile)
            await self.user_service.save_user_profile(account_id, user_profile)
            collection_result["ending_info"] = ending_info
            logger.info("[收尾检测] 命中虚假信息硬兜底 fake_info")
            return collection_result

        # === 使用统一的收尾服务检测收尾场景 ===
        # 调用 check_and_get_ending，参数顺序：user_message, profile, collection_result
        # 内部已调用 update_profile_for_ending，无需单独调用
        ending_info = self.ending_service.check_and_get_ending(
            user_message,        # 第1个参数：用户消息
            user_profile,        # 第2个参数：用户档案
            collection_result    # 第3个参数：收集结果
        )

        if ending_info:
            scenario = ending_info['scenario']
            logger.info(f"[收尾检测] 检测到收尾场景: {scenario}, AI生成: True")

            # 保存已更新的用户状态（check_and_get_ending 内部已更新 profile）
            await self.user_service.save_user_profile(account_id, user_profile)

            # 统一 AI 场景：不返回预设话术，由外部流程处理
            collection_result['ending_info'] = ending_info
            logger.info(f"[收尾检测] AI生成场景，传递给外部处理: {scenario}")

        # === 离异手续硬门控 ===
        # 1. 仅说“离异”时，锁定到手续确认状态，本轮禁止继续采集其他字段
        # 2. 用户确认“已办妥”后，清掉 pending 并回主线
        divorce_confirmation_negative = (
            self._is_short_negative_reply(user_message)
            and self._is_divorce_confirmation_question(last_response)
        )
        if "离异" in str(user_profile.marital_status or ""):
            if self._is_divorce_status_complete_message(user_message):
                user_profile.marital_status = "离异（手续已办妥）"
                user_profile.divorce_confirmed = True
                user_profile.divorce_confirmation_pending = False
                await self.user_service.save_user_profile(account_id, user_profile)
                collection_result["divorce_confirmation_cleared"] = True
                logger.info(f"[离异手续已办妥] 用户说: {user_message}，更新 marital_status=离异（手续已办妥）")
            elif self._is_divorce_status_incomplete_message(user_message) or divorce_confirmation_negative:
                user_profile.marital_status = "离异（手续未办妥）"
                user_profile.divorce_confirmed = False
                user_profile.divorce_confirmation_pending = False
                await self.user_service.save_user_profile(account_id, user_profile)
                collection_result["ending_info"] = self.ending_service.build_ending_info("divorce_incomplete", user_profile)
                logger.info(f"[离异手续未办妥] 用户说: {user_message}，进入结束场景 divorce_incomplete")
            elif not ending_info and "办妥" not in str(user_profile.marital_status or "") and not user_profile.divorce_confirmed:
                user_profile.divorce_confirmation_pending = True
                await self.user_service.save_user_profile(account_id, user_profile)
                collection_result["divorce_confirmation_pending"] = True
                logger.info(f"[离异手续待确认] 用户说: {user_message}，锁定本轮只确认手续")
        else:
            if user_profile.divorce_confirmation_pending:
                user_profile.divorce_confirmation_pending = False
                await self.user_service.save_user_profile(account_id, user_profile)

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
        self._last_validation_feedback_meta = None
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
            self.contact_service.reset_invalid_input(user_profile, 'wechat')
            self.contact_service.is_contact_complete(user_profile)
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
                if fallback_hint == "wechat" or "微信" in user_message:
                    is_valid, error_info = await self.validation_service.validate_wechat(
                        invalid_contact_attempt,
                        user_profile,
                        account_id,
                        self.user_service,
                    )
                else:
                    is_valid, error_info, _ = await self.validation_service.validate_contact(
                        invalid_contact_attempt,
                        user_profile,
                        account_id,
                        self.user_service
                    )
                if not is_valid:
                    return await self._build_validation_feedback(
                        account_id=account_id,
                        user_profile=user_profile,
                        user_message=user_message,
                        invalid_value=invalid_contact_attempt,
                        error_info=error_info,
                    )

            # 检查核心字段是否全部收集
            profile_complete_or_exhausted = self._is_profile_collection_complete_or_exhausted(user_profile)

            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 只有资料主线也完成/问尽后，才允许在已拿到联系方式的前提下收尾。
            if profile_complete_or_exhausted and contact_collected:
                # 检查联系方式收集流程是否还有下一步动作
                from src.services.collection.contact_collection_service import NextAction
                next_action = self.contact_service.get_next_action(user_profile)
                if not self.contact_service.is_contact_complete(user_profile) and next_action not in [NextAction.NONE, NextAction.END_CONVERSATION]:
                    # 联系方式收集流程还没结束，返回 AI 原回复（包含争取话术）
                    logger.info(f"[收尾检查] 联系方式收集流程未结束，next_action={next_action.value}")
                    return ai_response

                logger.info(f"[收尾检查] 所有字段已完成，优先返回 AI 原回复")
                return ai_response

            # 否则返回原回复
            return ai_response

        # 用户提供了联系方式（电话或微信），重置确认词计数器
        await self.input_fallback_service.reset_confirm_count(account_id)
        logger.info(f"[联系方式验证] 用户提供了联系方式，重置确认词计数器")

        # 如果只收集到微信（没有电话），尝试争取电话
        if contact_value is None and collected_wechat:
            has_phone_already = bool(user_profile.phone_collected and user_profile.phone)
            user_message_text = str(user_message or "")
            mentions_phone = any(marker in user_message_text for marker in ("电话", "手机", "手机号", "号码"))

            # 用户主动先给微信时，上一轮可能已经预问过电话。
            # 这里重置未兑现的电话询问计数，避免“首次拒绝电话”被误判为最终拒绝。
            if (
                not has_phone_already
                and not user_profile.rejected_phone
                and user_profile.phone_ask_count > 0
                and not mentions_phone
            ):
                logger.info(
                    f"[微信收集] 用户主动先给微信，重置未兑现的电话询问计数: phone_ask_count={user_profile.phone_ask_count}"
                )
                user_profile.phone_ask_count = 0
                await self.user_service.save_user_profile(account_id, user_profile)

            next_action = self.contact_service.get_next_action(user_profile)
            # 微信已在上面的代码中处理（设置 wechat_collected=True）
            # 检查是否可以收尾
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )
            profile_complete_or_exhausted = self._is_profile_collection_complete_or_exhausted(user_profile)

            if next_action.value in {"ask_phone", "persuade_phone"}:
                logger.info(f"[微信收集] 按状态机继续电话流程: next_action={next_action.value}")
                return self._build_contact_followup_response(next_action.value, "wechat")

            # 电话链路已结束且资料主线也完成/问尽，才允许带联系方式收尾。
            if profile_complete_or_exhausted and contact_collected and self.contact_service.is_contact_complete(user_profile):
                if has_phone_already:
                    logger.info("[微信收集] 电话和微信均已收齐，返回稳定双联系方式确认")
                    return self._build_dual_contact_ack()
                logger.info(f"[微信收集] 联系方式流程已结束，进入统一收尾链: next_action={next_action.value}")
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                collection_result['ending_info'] = self.ending_service.build_ending_info('normal_complete', user_profile)
                await self.user_service.save_user_profile(account_id, user_profile)

                if user_profile.rejected_phone or user_profile.rejected_wechat:
                    ending_response = self._get_contact_completion_ending_response(user_profile)
                    collection_result['ending_info']['use_ai'] = False
                    collection_result['ending_info']['response'] = ending_response
                    return ending_response

                terminal_response = self._build_terminal_response(collection_result.get('ending_info'), user_profile)
                return terminal_response or ai_response

            if self.contact_service.is_contact_complete(user_profile):
                return self._get_contact_terminal_or_resume_response(user_profile, str(user_message or ""))

            # === 资料未达到可服务阈值，继续收集重要字段 ===
            decision = self.collection_policy.decide(
                user_profile,
                allow_contact_target=False,
            )
            logger.info(
                f"[微信收集] 不进入电话追问，继续推进字段: next_action={next_action.value}, target={decision.main_target}"
            )
            return self._build_contact_collection_ack("wechat")

        # 验证电话号码
        logger.info(f"[联系方式验证] 开始验证电话: {contact_value}")

        is_valid, error_info, success_msg = await self.validation_service.validate_contact(
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
            self.contact_service.reset_invalid_input(user_profile, 'phone')
            self.contact_service.is_contact_complete(user_profile)
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
                return self._build_contact_followup_response(next_action.value, "phone")

            if user_profile.wechat_collected and user_profile.wechat and self.contact_service.is_contact_complete(user_profile):
                logger.info("[联系方式验证] 电话和微信均已收齐，返回稳定双联系方式确认")
                return self._build_dual_contact_ack()

            # === 核心字段完成度检查 ===
            # 检查核心字段是否全部收集（联系方式：电话或微信有一个即可）
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 核心字段检查（排除contact，因为上面单独检查了
            profile_complete_or_exhausted = self._is_profile_collection_complete_or_exhausted(user_profile)

            if profile_complete_or_exhausted and contact_collected:
                # === 核心字段全部收集完成，收尾 ===
                logger.info(f"[核心字段] 全部收集完成，进入统一收尾链")

                # 标记剩余未收集字段为"跳过"
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                collection_result['ending_info'] = self.ending_service.build_ending_info('normal_complete', user_profile)
                await self.user_service.save_user_profile(account_id, user_profile)

                return ai_response
            if self.contact_service.is_contact_complete(user_profile):
                return self._get_contact_terminal_or_resume_response(user_profile, str(user_message or ""))
            else:
                # === 资料未达到可服务阈值，继续收集重要字段 ===
                decision = self.collection_policy.decide(
                    user_profile,
                    allow_contact_target=False,
                )
                logger.info(f"[核心字段] 资料未完成，继续推进字段: {decision.main_target}")
                return self._build_contact_collection_ack("phone")
        else:
            # 撤销保存 - 直接修改传入的 user_profile 对象
            user_profile.contact = None
            user_profile.collection_progress['contact'] = False
            await self.user_service.save_user_profile(account_id, user_profile)

            logger.info(f"[联系方式验证失败] 已撤销保存")
            return await self._build_validation_feedback(
                account_id=account_id,
                user_profile=user_profile,
                user_message=user_message,
                invalid_value=contact_value,
                error_info=error_info,
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
        info = dict(error_info or {})
        error_code = info.get("code") or "VALIDATION_ERROR"
        self._last_validation_feedback_meta = {
            "error_code": error_code,
            "field": info.get("field"),
            "attempt": info.get("attempt"),
            "silent": bool(info.get("silent")),
        }
        contact_type = str(info.get("field") or "contact")
        if contact_type not in {"phone", "wechat"}:
            last_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
            contact_type = last_type if last_type in {"phone", "wechat"} else "contact"

        if contact_type in {"phone", "wechat"}:
            self.contact_service.record_invalid_input(user_profile, contact_type)
            self.contact_service.is_contact_complete(user_profile)
            await self.user_service.save_user_profile(account_id, user_profile)

        if info.get("silent"):
            if contact_type == "wechat":
                return self._build_contact_invalid_input_close_response("wechat")
            if contact_type == "phone":
                return self._build_contact_invalid_input_close_response("phone")
            return ""

        response = await self._generate_validation_retry_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info=info,
        )
        return response

    async def _generate_validation_retry_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        invalid_value: Optional[str],
        error_info: Dict[str, Any],
    ) -> str:
        field = error_info.get("field") or "contact"
        field_label = "微信号" if field == "wechat" else "联系方式"
        attempt = error_info.get("attempt") or 1
        detail = error_info.get("detail") or "invalid_format"
        prompt = (
            "你在继续一段婚恋咨询对话。"
            "用户刚发来的联系方式未通过校验，请只输出一条自然、简短、口语化的中文回复。\n"
            "要求：\n"
            "1. 不要提 AI、系统、校验规则、错误码。\n"
            "2. 轻轻提醒对方重新发一个可用的手机号或微信号。\n"
            "3. 保持一到两句，像真人聊天，不要模板腔。\n"
            "4. 给对方保留余地，如果现在不方便可以稍后再发。\n"
            f"当前字段：{field_label}\n"
            f"错误细节：{detail}\n"
            f"第几次无效输入：{attempt}\n"
            f"用户称呼：{user_profile.get_greeting()}\n"
            f"用户原话：{user_message or '-'}\n"
            f"本次疑似输入：{invalid_value or '-'}\n"
        )
        try:
            response = await self._call_ai(prompt, account_id, user_message or str(invalid_value or ""))
            return response.strip() if response else ""
        except Exception as exc:
            logger.warning("[联系方式验证] 生成 AI 引导失败: %s", exc)
            return ""

    def _build_contact_invalid_input_close_response(self, contact_type: str) -> str:
        """连续无效输入后，停止围绕联系方式反复追问。"""
        if contact_type == "wechat":
            variants = [
                "这边先不反复问你这个了，后面你要是方便再联系我哈。",
                "这块我先不继续追了，后面你方便的话再来找我就行。",
                "先不在这上面打转了，等你方便的时候我们再接着聊。",
            ]
        else:
            variants = [
                "这边先不反复问你这个了，后面你要是方便再联系我哈。",
                "这块我先不继续追了，后面你方便的话再来找我就行。",
                "先不在这上面打转了，等你方便的时候我们再接着聊。",
            ]
        return variants[0]

    async def _generate_ai_ending_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        ending_info: Optional[Dict[str, Any]],
        fallback_response: str = "",
    ) -> str:
        """为 use_ai 的收尾场景单独生成最终收尾句。"""
        info = dict(ending_info or {})
        if not info or not info.get("use_ai"):
            return str(fallback_response or "").strip()

        extra = str(info.get("extra_instructions") or "").strip()
        scenario = str(info.get("scenario") or "").strip()
        if not extra:
            return str(fallback_response or "").strip()

        profile_bits = [
            f"性别:{getattr(user_profile, 'sex', None) or '-'}",
            f"年龄:{getattr(user_profile, 'age_label', None) or getattr(user_profile, 'age', None) or '-'}",
            f"城市:{getattr(user_profile, 'location', None) or '-'}",
            f"学历:{getattr(user_profile, 'education', None) or '-'}",
            f"职业:{getattr(user_profile, 'occupation', None) or '-'}",
            f"婚况:{getattr(user_profile, 'marital_status', None) or '-'}",
            f"电话拒绝:{bool(getattr(user_profile, 'rejected_phone', False))}",
            f"微信拒绝:{bool(getattr(user_profile, 'rejected_wechat', False))}",
        ]
        fallback = str(fallback_response or "").strip() or "那我们就先聊到这里。"
        prompt = (
            "你在收尾一段中文婚恋咨询对话，请只输出最终要发给用户的一段中文收尾回复。\n"
            "要求：\n"
            "1. 只输出1到2句自然口语，不要解释规则，不要提AI、系统、配置。\n"
            "2. 不要再追问任何资料，不要再索要电话或微信。\n"
            "3. 不要使用项目符号，不要使用引号，不要输出额外说明。\n"
            f"收尾场景：{scenario or '-'}\n"
            f"收尾指令：{extra}\n"
            f"用户当前资料：{' | '.join(profile_bits)}\n"
            f"用户本轮原话：{user_message or '-'}\n"
            f"如果生成不出来，可参考这个语气：{fallback}\n"
        )
        try:
            response = await self._call_ai(prompt, account_id, user_message or scenario or "ending")
            cleaned = self._clean_response(response).strip() if response else ""
            return cleaned or fallback
        except Exception as exc:
            logger.warning("[收尾AI] 生成收尾回复失败: %s", exc)
            return fallback

    def _clean_response(self, response: str) -> str:
        """清理回复（移除 XML 标签）"""
        import re
        text = re.sub(r'<extract>.*?</extract>', '', response, flags=re.DOTALL).strip()
        text = re.sub(r"^(?:了|啦|呀|呢|哈|啊)[。．]\s*", "", text)
        text = re.sub(r"([。！？!?])\s*(哈哈，原来|原来|这样的话|所以说)\s*$", r"\1", text)
        text = re.sub(r"^(哈哈，原来|原来|这样的话|所以说)\s*$", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = self._strip_broken_edge_fragments(text)
        return text

    @staticmethod
    def _strip_broken_edge_fragments(response: str) -> str:
        """剔除裁剪后残留的句首碎片，避免出现“了。你是哪年的呀？”这类脏前缀。"""
        text = str(response or "").strip()
        if not text:
            return text

        text = re.sub(r"^(?:(?:了|啦|呀|呢|哈|啊|哦|嗯)[。．！？!?]\s*)+", "", text).strip()

        sentence_match = re.match(r"^([^。！？!?]{1,4}[。！？!?])\s*(.+)$", text)
        if sentence_match:
            first_sentence = sentence_match.group(1).strip()
            remainder = sentence_match.group(2).strip()
            first_body = re.sub(r"[。！？!?]", "", first_sentence).strip()
            if first_body in {"了", "啦", "呀", "呢", "哈", "啊", "哦", "嗯"}:
                text = remainder

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _build_contact_collection_ack(contact_type: str) -> str:
        """联系方式收集成功后的自然确认，避免登记腔。"""
        if contact_type == "wechat":
            return "好，微信我看到了。我们接着聊你的情况就行。"
        return "好，电话我收到了。我们接着聊你的情况就行。"

    @staticmethod
    def _build_contact_followup_response(next_action_value: str, collected_type: str) -> str:
        """基于最新联系方式状态生成稳定后续回复，避免沿用旧状态下的 AI 回复。"""
        if collected_type == "phone":
            if next_action_value == "ask_wechat":
                return "好，电话我收到了。方便留个微信吗？后面沟通会方便些。"
            if next_action_value == "persuade_wechat":
                return "好，电话我收到了。你要是方便的话，留个微信也行，后面沟通会顺一点。"
            return "好，电话我收到了。我们接着聊你的情况就行。"

        if next_action_value == "ask_phone":
            return "好，微信我看到了。方便留个电话吗？后面沟通会方便些。"
        if next_action_value == "persuade_phone":
            return "好，微信我看到了。你要是方便的话，留个手机号也行，后面沟通会顺一点。"
        return "好，微信我看到了。我们接着聊你的情况就行。"

    @staticmethod
    def _build_phone_persuasion_fallback() -> str:
        """电话二次争取的软性兜底，不用固定句式硬复读。"""
        variants = (
            "你要是现在不太方便细说也没事。留个常用手机号就行，后面真有合适的，我们也能及时联系到你。",
            "电话这块我轻轻问一句就行。你要是方便的话，留个常用手机号，后面有合适的也好继续联系你。",
            "你要是担心电话不方便，我这边就不说太满了。只是留个常用手机号，后面沟通起来会顺一点。",
            "不想留太多也没关系。给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你。",
        )
        return random.choice(variants)

    @staticmethod
    def _build_dual_contact_ack() -> str:
        """电话和微信都已收齐时返回稳定确认，避免沿用旧询问态回复。"""
        return "好，电话和微信我都看到了。还有其他要求的话也可以继续说。"

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
        if scenario == "already_ended":
            return self._get_already_ended_response()

        if self.contact_service.should_end_conversation(user_profile):
            return self._get_both_rejected_ending_response()

        if user_profile.conversation_ended and user_profile.rejected_phone and user_profile.rejected_wechat:
            return self._get_both_rejected_ending_response()
        return None

    def _get_already_ended_response(self) -> str:
        return self.ending_service.get_ending_response("already_ended") or ""

    def _get_both_rejected_ending_response(self) -> str:
        return self.ending_service.get_ending_response("both_rejected") or ""

    @staticmethod
    def _has_any_contact(user_profile: UserProfile) -> bool:
        return bool(
            (user_profile.phone_collected and user_profile.phone)
            or (user_profile.wechat_collected and user_profile.wechat)
            or user_profile.collection_progress.get("contact", False)
        )

    def _is_profile_collection_complete_or_exhausted(self, user_profile: UserProfile) -> bool:
        return self.collection_policy.is_coverage_complete(user_profile)

    def _can_end_with_contact_completion(self, user_profile: UserProfile) -> bool:
        return (
            self._has_any_contact(user_profile)
            and self.contact_service.is_contact_complete(user_profile)
            and self._is_profile_collection_complete_or_exhausted(user_profile)
        )

    def _can_end_without_contact(self, user_profile: UserProfile) -> bool:
        return (
            not self._has_any_contact(user_profile)
            and self.contact_service.is_contact_complete(user_profile)
        )

    def _get_no_contact_completion_response(self) -> str:
        return "这边就先不往下追着问啦，后面你要是方便，再来找我聊就行。"

    def _get_contact_completion_ending_response(self, user_profile: UserProfile) -> str:
        if not self._has_any_contact(user_profile):
            return self._get_no_contact_completion_response()
        return self.expectation_service.get_contact_completion_response(user_profile)

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
        high_risk_blocked_pairs = {
            ("education", "partner_requirement"),
        }
        if (main_target, preferred_side_target) in high_risk_blocked_pairs:
            return False
        return True

    def _get_contact_terminal_or_resume_response(
        self,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """
        联系方式流程结束后的统一出口。
        """
        if self._can_end_with_contact_completion(user_profile):
            return self._get_contact_completion_ending_response(user_profile)
        if self._can_end_without_contact(user_profile):
            return self._get_no_contact_completion_response()
        return self._build_post_contact_resume_response(user_profile, user_message)

    def _build_post_contact_resume_response(self, user_profile: UserProfile, user_message: str = "") -> str:
        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        )
        next_field = decision.main_target
        if next_field and next_field != "contact":
            prompt = self._build_policy_field_prompt(next_field, user_profile, user_message=user_message).strip()
            if prompt:
                return prompt
        unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core_fields:
            prompt = self._build_policy_field_prompt(unresolved_core_fields[0], user_profile, user_message=user_message).strip()
            if prompt:
                return prompt
        unresolved_medium_fields = self.collection_policy.get_uncovered_medium_fields(user_profile)
        if unresolved_medium_fields:
            prompt = self._build_policy_field_prompt(unresolved_medium_fields[0], user_profile, user_message=user_message).strip()
            if prompt:
                return prompt
        return "你继续说，我顺着往下了解。"

    @staticmethod
    def _contains_contact_push_markers(response: str) -> bool:
        text = (response or "").strip()
        if not text:
            return False

        if any(marker in text for marker in CONTACT_ASK_MARKERS):
            return True
        return any(marker in text for marker in ("加你", "加下", "微信号", "手机号", "联系到你"))

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

    def _enforce_contact_outcome_policy(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        """
        联系方式场景的最终兜底：一旦进入联系方式上下文，最终用户可见话术由状态机定稿，
        避免真实模型在 ask/persuade/end/complete 轮次漂移。
        """
        result = collection_result or {}
        all_fields = result.get("all_fields", []) or []
        collected_fields = {str(item.get("field") or "").strip() for item in all_fields if isinstance(item, dict)}
        if not self._has_active_contact_context(user_profile, collection_result=result, user_message=user_message):
            return response
        ending_info = result.get("ending_info") if isinstance(result, dict) else None

        scenario = str((ending_info or {}).get("scenario") or "").strip()
        if scenario == "both_rejected":
            return self._get_both_rejected_ending_response()
        if scenario == "already_ended" or self.contact_service.should_end_conversation(user_profile):
            return self._get_already_ended_response()

        if scenario == "normal_complete":
            if response:
                return response
            return self._get_contact_completion_ending_response(user_profile)

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return response

        if action_value in {"none", "", None, "end"} and self.contact_service.is_contact_complete(user_profile):
            return self._get_contact_terminal_or_resume_response(user_profile, user_message)

        if action_value == "ask_wechat":
            if self._response_matches_contact_action(response, "ask_wechat"):
                return response
            if user_profile.phone_collected and user_profile.phone:
                return self._build_contact_followup_response("ask_wechat", "phone")
            return "没关系，你要是觉得微信更方便，留个微信也可以。"

        if action_value == "persuade_wechat":
            if self._response_matches_contact_action(response, "persuade_wechat"):
                return response
            return "你要是更习惯微信的话，留个常用微信就行，后面沟通也方便一些。"

        if action_value == "ask_phone":
            if self._response_matches_contact_action(response, "ask_phone"):
                return response
            if user_profile.wechat_collected and user_profile.wechat:
                return self._build_contact_followup_response("ask_phone", "wechat")
            return "方便留个电话吗？后面沟通会方便些。"

        if action_value == "persuade_phone":
            if self._response_matches_contact_action(response, "persuade_phone"):
                return response
            return self._build_phone_persuasion_fallback()

        if action_value in {"none", "", None} and {"phone", "contact", "wechat"} & collected_fields:
            if not self._can_end_with_contact_completion(user_profile):
                return response
            if response:
                return response
            return self._get_contact_completion_ending_response(user_profile)

        return response

    def _response_matches_contact_action(self, response: str, action_value: str) -> bool:
        text = str(response or "").strip()
        if not text:
            return False
        if action_value in {"ask_phone", "persuade_phone"}:
            return self._response_mentions_phone_request(text)
        if action_value in {"ask_wechat", "persuade_wechat"}:
            return self._response_mentions_wechat_request(text)
        if action_value in {"none", "end"}:
            return not self._contains_contact_push_markers(text)
        return False

    def _has_active_contact_context(
        self,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> bool:
        result = collection_result or {}
        all_fields = result.get("all_fields", []) or []
        collected_fields = {
            str(item.get("field") or "").strip()
            for item in all_fields
            if isinstance(item, dict)
        }
        ending_info = result.get("ending_info") if isinstance(result, dict) else None
        return any(
            [
                bool(ending_info),
                bool(user_profile.phone_ask_count > 0),
                bool(user_profile.wechat_ask_count > 0),
                bool(user_profile.phone_collected and user_profile.phone),
                bool(user_profile.wechat_collected and user_profile.wechat),
                bool(user_profile.rejected_phone),
                bool(user_profile.rejected_wechat),
                bool({"phone", "contact", "wechat"} & collected_fields),
                bool(self._is_contact_like_user_message(user_message)),
            ]
        )

    def _apply_contact_persuasion_style_policy(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """
        联系方式第一次说服轮次统一降压，避免重复解释和销售腔。
        """
        if not response or user_profile.conversation_ended:
            return response

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return response

        if action_value == "persuade_wechat":
            if self._response_mentions_wechat_request(response):
                return response
            return "你要是更习惯微信的话，留个常用微信就行，后面沟通也方便一些。"

        if action_value == "persuade_phone":
            if self._response_mentions_phone_request(response) and any(
                token in response for token in ("联系", "沟通", "合适")
            ) and "再轻问一次" not in response:
                return response
            return self._build_phone_persuasion_fallback()

        return response

    def _is_contact_boundary_message(self, user_message: str) -> bool:
        message = (user_message or "").strip()
        if not message:
            return False
        if any(marker in message for marker in ("电话", "手机号", "微信")) and any(
            token in message for token in ("不方便", "不想留", "不留", "不给", "算了")
        ):
            return True
        return self._matches_any_pattern(message, BOUNDARY_PAUSE_PATTERNS)

    def _apply_contact_boundary_softening_policy(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """
        用户已经表达边界时，联系方式链路进一步降压，避免继续顶着推进。
        """
        if not response or user_profile.conversation_ended:
            return response
        if not self._is_contact_boundary_message(user_message):
            return response

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            return response

        if action_value == "persuade_phone":
            if self._response_matches_contact_action(response, "persuade_phone"):
                return response
            return self._build_phone_persuasion_fallback()

        if action_value == "ask_phone":
            if self._response_matches_contact_action(response, "ask_phone"):
                return response
            return "方便留个电话吗？后面沟通会方便些。"

        if action_value == "persuade_wechat":
            return "好，那微信这块我先不往下问了，我们先聊别的。"

        if action_value == "ask_wechat" and (user_profile.rejected_phone or user_profile.phone_ask_count >= 1):
            return "好，微信这块你要是现在也不想留，我们就先不碰联系方式。"

        if action_value == "ask_phone" and (user_profile.rejected_wechat or user_profile.wechat_ask_count >= 1):
            return "好，微信这块我知道了。电话如果你现在也不想留，我们就先聊别的。"

        return response

    def _apply_contact_action_guard(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """
        当联系方式状态机已经判定本轮不该继续推进时，硬阻断任何新的联系方式追问。
        """
        if not response or user_profile.conversation_ended:
            return response

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
            action_name = getattr(next_action, "name", str(next_action)).upper()
        except Exception:
            return response

        if self._has_active_contact_context(user_profile, user_message=user_message):
            return response

        if action_value != "none":
            if not self.collection_policy.should_allow_contact_instruction(user_profile, action_name):
                if self._contains_contact_push_markers(response):
                    fallback_field = self.collection_policy.get_forced_cover_target(user_profile)
                    if not fallback_field:
                        fallback_field = self.collection_policy.get_main_target(
                            user_profile,
                            can_enter_contact=False,
                            allow_contact_target=False,
                        )
                    if fallback_field:
                        logger.info("[联系方式守卫] 上游 gate 未通过，改回字段推进: %s", fallback_field)
                        return self._build_policy_field_prompt(fallback_field, user_profile, user_message=user_message)
                    return "我们先把你的情况聊顺一点，再往后走。"
            return response

        if self._contains_contact_push_markers(response):
            return "好，我们先不碰联系方式了，继续聊别的。"

        return response

    def _apply_contact_context_field_guard(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        """联系方式澄清/推进轮次只允许继续聊联系方式，禁止混入其他字段。"""
        if not response or user_profile.conversation_ended:
            return response
        if not self._has_active_contact_context(user_profile, user_message=user_message):
            return response

        if "微信" in str(user_message or "") and "微信" not in response and "电话" in response:
            return "对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。"

        asked_fields = self._detect_asked_fields_in_response(response)
        blocked_fields = {
            "sex",
            "age",
            "location",
            "education",
            "occupation",
            "marital_status",
            "monthly_income",
            "partner_requirement",
            "height",
            "weight",
            "last_name",
        }
        if not (asked_fields & blocked_fields):
            return response

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if "微信" in str(user_message or ""):
            return "对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。"
        if action_value == "ask_wechat":
            return "对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。"
        if action_value == "persuade_wechat":
            return "对，我们就先把微信这条说完。你要是更习惯微信的话，留个常用微信就行，不想留也没关系。"
        if action_value == "ask_phone":
            return "对，刚刚是在说电话这块。你要是方便的话，留个常用手机号就行，不想留也没关系。"
        if action_value == "persuade_phone":
            return "对，我们先把电话这条说完。你要是方便的话，留个常用手机号就行，不想留也没关系。"
        return "对，我们先把联系方式这条说清楚，其他信息先不往里插。"





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
            if user_profile.collection_progress.get(field, False):
                blocked_fields.add(field)
                continue
            if user_profile.skipped_fields.get(field, False):
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
        if (
            current_core_target in ASK_GUARD_CORE_FIELDS
            and asked_fields
            and (asked_fields & ASK_GUARD_MEDIUM_FIELDS)
            and current_core_target not in asked_fields
        ):
            return self._build_policy_field_prompt(current_core_target, user_profile, user_message=user_message)

        deterministic_fields = self._extract_deterministic_profile_fields(user_message)
        user_supplied_fields = {field for field in deterministic_fields if field in asked_fields}
        if user_supplied_fields and (
            all(field in blocked_fields for field in user_supplied_fields)
            or all(user_profile.collection_progress.get(field, False) for field in user_supplied_fields)
        ):
            if self.collection_policy.can_enter_contact(user_profile):
                return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)
            if current_core_target:
                return self._build_policy_field_prompt(current_core_target, user_profile, user_message=user_message)
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
        if self.collection_policy.can_enter_contact(user_profile):
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)
        if current_core_target:
            return self._build_policy_field_prompt(current_core_target, user_profile, user_message=user_message)
        return ""


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

        compact_message = re.sub(r"\s+", "", message)

        def _looks_like_profile_intake(text: str) -> bool:
            profile_markers = ("岁", "cm", "厘米", "kg", "斤", "本科", "大专", "硕士", "博士", "单身", "离异", "男", "女")
            profile_hits = sum(1 for marker in profile_markers if marker in text)
            return profile_hits >= 2

        # 电话流程：只在“明显在留联系方式”的消息里兜底推断，避免把年龄/身高/体重数字串误判成电话。
        if next_action in {"ask_phone", "persuade_phone"}:
            has_phone_marker = bool(re.search(r"(电话|手机|手机号|号码|联系)", message))
            compact_digits_only = bool(re.fullmatch(r"\+?86?[\d\s-]{7,17}", message))
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
            explicit_id_match = re.search(r"\b(?:wx|vx|weixin)[:：\s]*([a-z][a-z0-9_-]{5,19})\b", lowered)
            if explicit_id_match:
                return explicit_id_match.group(1), "wechat"
            # 仅出现“微信”意向词（例如“用微信联系吧”）不应当作“已提供微信号”。
            if re.match(r"^[a-z][a-z0-9_-]{5,19}$", cleaned):
                return cleaned, "wechat"

        return None, None

    def _extract_basic_fields_from_message(self, user_message: str) -> Dict[str, Any]:
        """AI 不可用时，用轻量规则兜底提取常见基础字段。"""
        if not user_message:
            return {}

        extracted: Dict[str, Any] = {}
        compact_message = re.sub(r"[，,、。！？!?~～\s]+", "", user_message)

        if '我是女生' in user_message or '本人女' in user_message:
            extracted['sex'] = '女'
        elif '我是男生' in user_message or '本人男' in user_message:
            extracted['sex'] = '男'
        else:
            sex_match = re.search(r"(?:^|[，,、\s])(?:(?:我是)?(男生|男的|女生|女的))(?:呢|呀|哈|哦|啊)?(?=$|[，,、。！？!?])", user_message)
            if sex_match:
                extracted['sex'] = '男' if '男' in sex_match.group(1) else '女'

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

        # 支持“我是女生，90后，深圳，本科”这类紧凑输入中的城市片段，同时避免把“在骗我”误提取为地点。
        city_candidates = {"深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港"}
        preference_context = bool(re.search(r"(喜欢|想找|找).*(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", user_message))
        if not preference_context:
            for city in city_candidates:
                if re.search(rf"(?:在|来自|住在)\s*{city}", user_message) or re.search(rf"(?:^|[，,、\s]){city}(?:$|[，,、\s])", user_message):
                    extracted["location"] = city
                    break
                if len(compact_message) <= 8 and re.fullmatch(rf"(?:我是|我在|我来自|我住在|我)?{city}(?:人|的|这边)?", compact_message):
                    extracted["location"] = city
                    break
            if not extracted.get("location"):
                location_match = re.search(
                    r'(?:在|来自|住在)\s*([\u4e00-\u9fa5]{2,8}(?:市|省|县|区|州|特别行政区))',
                    user_message,
                )
                if location_match:
                    extracted["location"] = location_match.group(1)

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
        else:
            compact_message = re.sub(r"[，,、。！？!?~～\s]+", "", message)
            for city in location_candidates:
                if len(compact_message) <= 8 and re.fullmatch(rf"(?:我是|我在|我来自|我住在|我)?{city}(?:人|的|这边)?", compact_message):
                    extracted["location"] = city
                    break

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

        if not extracted.get("occupation"):
            occupation_aliases = {
                "it": "IT",
                "ui": "UI",
                "hr": "HR",
                "qa": "QA",
                "产品": "产品",
                "运营": "运营",
                "设计": "设计",
                "开发": "开发",
                "程序员": "程序员",
                "销售": "销售",
                "老师": "老师",
                "医生": "医生",
                "公务员": "公务员",
            }
            normalized = message.strip().lower()
            if normalized in occupation_aliases:
                extracted["occupation"] = occupation_aliases[normalized]

        if not extracted.get("partner_requirement"):
            pref = self._extract_simple_partner_requirement(message)
            if pref:
                extracted["partner_requirement"] = pref
        if not extracted.get("monthly_income"):
            income = self._extract_simple_monthly_income(message)
            if income:
                extracted["monthly_income"] = income

        return extracted

    def _build_shadow_profile_for_decision(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        last_response: str = "",
    ) -> UserProfile:
        """
        基于用户当前输入生成只用于“本轮决策/问句生成”的临时画像副本。

        目的：
        - 让决策器看到“用户这句话说完之后”的最新状态
        - 不直接改真实 profile，不影响正式落库
        """
        shadow_profile = user_profile.model_copy(deep=True)
        extracted = self._extract_deterministic_profile_fields(user_message)
        extracted = self._apply_extraction_guards(extracted, user_message, last_response=last_response)
        if not extracted:
            return shadow_profile

        for field, value in extracted.items():
            if value in (None, ""):
                continue
            if field == "age_label":
                shadow_profile.age_label = str(value).strip()
                continue
            if hasattr(shadow_profile, field):
                shadow_profile.update_field(field, value)
                if field in shadow_profile.collection_progress:
                    shadow_profile.collection_progress[field] = True

        if extracted.get("age") and not shadow_profile.collection_progress.get("age"):
            shadow_profile.collection_progress["age"] = True
        if extracted.get("partner_requirement"):
            shadow_profile.collection_progress["partner_requirement"] = True
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

        patterns = [
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
            r"(成熟稳重)",
            r"(三观合拍)",
            r"(喜欢[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(想找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
            r"(找[^\s，,。]{1,10}(?:男生|女生|男的|女的|男|女))",
        ]
        values = []
        for pattern in patterns:
            match = re.search(pattern, compact_message)
            if match:
                values.append(match.group(1).strip())
        if values:
            normalized = []
            for value in dict.fromkeys(values):
                value = re.sub(r"(温柔)(一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?$", r"\1", value)
                value = re.sub(r"^(温柔)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(性格好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(聊得来)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(合适)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                value = re.sub(r"^(人好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
                normalized.append(value)
            return "，".join(normalized)
        return None

    @staticmethod
    def _extract_simple_monthly_income(user_message: str) -> Optional[str]:
        """轻量提取明确的月收入表达，供被动提取场景兜底。"""
        message = (user_message or "").strip().lower()
        if not message:
            return None

        # 体重/重量表达里常见 kg/公斤/斤，避免把 90kg 错提成 90k 收入。
        sanitized_message = re.sub(r"\d+(?:\.\d+)?\s*kg\b", " ", message, flags=re.IGNORECASE)
        sanitized_message = re.sub(r"\d+(?:\.\d+)?\s*(?:公斤|斤)\b", " ", sanitized_message, flags=re.IGNORECASE)

        patterns = [
            r"((?:税前|税后)?\s*\d+(?:\.\d+)?\s*(?:k|w|万)(?:\+|左右|上下)?)",
            r"((?:月收入|月薪|收入|工资)[^，。；,\s]{0,6}\d+(?:\.\d+)?\s*(?:k|w|万|元)(?:\+|左右|上下)?)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)左右)",
            r"(年包\d+(?:\.\d+)?(?:w|万)?左右)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)出头)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)上下)",
        ]
        for pattern in patterns:
            match = re.search(pattern, sanitized_message, re.IGNORECASE)
            if match:
                return re.sub(r"\s+", "", match.group(1))
        return None

    @staticmethod
    def _last_response_asked_partner_requirement(last_response: str) -> bool:
        text = str(last_response or "").strip()
        if not text:
            return False
        markers = (
            "对另一半",
            "有什么要求",
            "更看重",
            "看重哪方面",
            "想找什么样",
            "择偶要求",
            "喜欢什么样",
        )
        return any(marker in text for marker in markers)

    def _build_partner_requirement_fallback_followup(
        self,
        user_profile: UserProfile,
        *,
        user_message: str,
    ) -> str:
        preference = self._extract_simple_partner_requirement(user_message)
        if not preference:
            return "你继续说，我先顺着听"

        shadow_profile = user_profile.model_copy(deep=True)
        shadow_profile.partner_requirement = preference
        shadow_profile.collection_progress["partner_requirement"] = True
        shadow_profile.close_active_ask("partner_requirement")

        rendered_preference = self._render_preference_for_ack(preference)
        ack = random.choice(
            tuple(v.format(preference=rendered_preference) for v in FAST_PATH_PREFERENCE_ACK_VARIANTS)
        ).strip()

        decision = self.collection_policy.decide(
            shadow_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=True,
            prioritize_user_question=False,
            primary_move="ack_and_ask",
        )
        next_field = decision.main_target
        if next_field and next_field not in {"partner_requirement", "contact"}:
            followup = self._build_policy_field_prompt(next_field, shadow_profile, user_message=user_message)
            return f"{ack} {followup}".strip()
        return ack

    def _build_lightweight_field_ack_from_message(
        self,
        user_message: str,
        user_profile: Optional[UserProfile] = None,
    ) -> str:
        """
        从用户一句话里抽一条轻量资料承接，供 FAQ / 混合输入场景复用。
        """
        message = str(user_message or "").strip()
        if not message:
            return ""

        extracted = self._extract_deterministic_profile_fields(message)
        extracted = self._apply_extraction_guards(extracted, message)

        # FAQ 混合输入里，短答性别经常和问题写在一句里，规则提取未命中时做轻量兜底。
        if "sex" not in extracted:
            if re.match(r"^(男的|男生|我是男|男)\b", message):
                extracted["sex"] = "男"
            elif re.match(r"^(女的|女生|我是女|女)\b", message):
                extracted["sex"] = "女"

        preference = str(extracted.get("partner_requirement") or "").strip()
        if not preference:
            preference = self._extract_simple_partner_requirement(message) or ""
        if preference and not (user_profile and user_profile.is_active_ask_closed("partner_requirement")):
            natural_preference = self._render_preference_for_ack(preference)
            variants = tuple(v.format(preference=natural_preference) for v in FAST_PATH_PREFERENCE_ACK_VARIANTS)
            return random.choice(variants).strip()

        for field in ("sex", "age_label", "age", "location", "education", "occupation", "marital_status"):
            value = extracted.get(field)
            if not value:
                continue
            ack = self._build_contextual_short_ack(field, value)
            if ack:
                return ack

        return ""

    def _build_opening_profile_ack_from_message(self, user_message: str) -> str:
        message = str(user_message or "").strip()
        if not message:
            return ""

        extracted = self._extract_deterministic_profile_fields(message)
        extracted = self._apply_extraction_guards(extracted, message)
        preference = self._extract_simple_partner_requirement(message) or ""

        if extracted.get("sex"):
            return "好，你这边是男生。" if "男" in str(extracted["sex"]) else "好，你这边是女生。"
        if extracted.get("location"):
            return f"好，{str(extracted['location']).strip()}这边我知道了。"
        if extracted.get("education"):
            return f"好，{str(extracted['education']).strip()}这点我知道了。"
        if extracted.get("occupation"):
            occupation = self._render_occupation_for_ack(str(extracted["occupation"]).strip())
            return f"好，做{occupation}这点我知道了。"
        if extracted.get("age_label") or extracted.get("age"):
            age_text = str(extracted.get("age_label") or extracted.get("age") or "").strip()
            return f"好，{self._render_age_value(age_text)}我知道了。"
        if preference:
            natural_preference = self._render_preference_for_ack(preference)
            return f"好，你更偏向{natural_preference}这类。"
        return ""

    @staticmethod
    def _build_fused_partner_requirement_prompt(main_target: Optional[str]) -> str:
        if main_target == "education":
            variants = (
                "你大概是什么学历呀？平时更看重另一半哪一点，也可以一起说说。",
                "学历这边你方便说个大概吗？你对另一半更在意哪方面，也能顺手带一句。",
                "你大概是什么学历呀？另外说到找对象，你会更看重对方哪一点？",
            )
            return random.choice(variants)
        if main_target == "occupation":
            variants = (
                "你现在主要做哪方面工作呀？顺着这个聊，你对另一半会更看重哪一点？",
                "平时是做什么工作的？另外你找对象时更在意对方哪方面，也可以一起说说。",
                "你现在主要做哪方面工作呀？说到这儿，你会更看重对方什么？",
            )
            return random.choice(variants)
        return random.choice(PARTNER_REQUIREMENT_ASK_VARIANTS)

    @staticmethod
    def _build_fused_income_prompt(main_target: Optional[str]) -> str:
        if main_target == "occupation":
            variants = (
                "你现在主要做哪方面工作呀？收入这块大概在什么区间，也可以顺手说个大概。",
                "平时是做什么工作的？你现在收入大概在哪个范围，也可以一起说说。",
                "你现在主要做哪方面工作呀？如果方便的话，收入区间也说个大概就行。",
            )
            return random.choice(variants)
        return random.choice(INCOME_ASK_VARIANTS)

    @staticmethod
    def _build_fused_marital_status_prompt(main_target: Optional[str]) -> str:
        if main_target == "occupation":
            variants = (
                "你现在主要做哪方面工作呀？另外感情状态这边，我也顺手确认一下，你现在是单身状态吗？",
                "平时是做什么工作的？还有现在感情状态这边，你是单身状态在了解吗？",
                "你现在主要做哪方面工作呀？对了，我也确认下，你现在是单身状态吗？",
            )
            return random.choice(variants)
        if main_target == "education":
            variants = (
                "你大概是什么学历呀？感情状态这边我也顺手确认一下，你现在是单身状态吗？",
                "学历这边你方便说个大概吗？另外你现在是单身状态在了解吗？",
            )
            return random.choice(variants)
        return "我顺手确认一下，你现在是单身状态吗？"

    @staticmethod
    def _build_contextual_short_ack(field: str, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        if field == "sex":
            variants = (
                "好，男生是吧。",
                "男生，明白了。",
                "好，你这边是男生。",
            ) if "男" in text else (
                "好，女生是吧。",
                "女生，明白了。",
                "好，你这边是女生。",
            )
            return random.choice(variants)

        if field in {"age", "age_label"}:
            return ""

        if field == "location":
            return ""

        if field == "education":
            return ""

        if field == "occupation":
            return ""

        if field == "marital_status":
            if "离异" in text:
                return "好，这个状态我知道了。"
            if "单身" in text or "未婚" in text:
                return "好，这个状态我知道了。"
        return ""

    def _format_fast_path_ack(self, field: str, value: Any) -> str:
        rendered = str(value or "").strip()
        if not rendered:
            return ""

        if field == "age":
            rendered = self._render_age_value(rendered)
        elif field == "age_label":
            field = "age"
        elif field == "sex":
            rendered = "男" if "男" in rendered else "女"
        elif field == "occupation":
            rendered = self._render_occupation_for_ack(rendered)
        elif field == "marital_status":
            rendered = self._render_marital_status_for_ack(rendered)

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
        if any(marker in text for marker in PARTNER_REQUIREMENT_ASK_MARKERS):
            asked_fields.add("partner_requirement")
        if any(marker in text for marker in ("月收入", "月薪", "收入", "工资")) and any(cue in text for cue in ASK_GUARD_QUESTION_CUES):
            asked_fields.add("monthly_income")

        field_keywords = get_field_keywords()
        if any(cue in text for cue in ASK_GUARD_QUESTION_CUES):
            for field in ASK_GUARD_MANAGED_FIELDS:
                for keyword in field_keywords.get(field, []):
                    if keyword and keyword in text:
                        asked_fields.add(field)
                        break

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
                "age": (r"多大", r"几岁", r"年龄", r"年纪"),
                "location": (r"哪个城市", r"什么城市", r"在哪个城市", r"在哪边", r"哪里生活"),
                "education": (r"学历",),
                "occupation": (r"做什么工作", r"做哪方面", r"什么工作", r"职业", r"工作"),
                "marital_status": (r"单身状态", r"感情状态", r"婚况", r"离异"),
            }
            for field, patterns in pattern_map.items():
                if any(re.search(pattern, text) for pattern in patterns):
                    asked_fields.add(field)

        return asked_fields

    @staticmethod
    def _response_already_acks_field(response: str, field_name: str, value: Any) -> bool:
        text = str(response or "").strip()
        rendered = str(value or "").strip()
        if not text or not rendered:
            return False

        if field_name == "location":
            return rendered in text and any(marker in text for marker in ("这边", "知道", "是吧", "挺好", "常住", "生活"))
        if field_name == "occupation":
            return rendered in text and any(marker in text for marker in ("工作", "做", "方向", "知道", "明白"))
        if field_name == "education":
            return rendered in text and any(marker in text for marker in ("学历", "知道", "明白", "是吧"))
        if field_name == "marital_status":
            return rendered in text and any(marker in text for marker in ("状态", "婚况", "知道", "明白"))
        if field_name == "age":
            return rendered in text and any(marker in text for marker in ("岁", "知道", "明白", "是吧"))
        if field_name == "sex":
            return any(marker in text for marker in ("男生", "女生", "男的", "女的", "性别"))

        return rendered in text

    def _build_interleaving_followup(
        self,
        user_profile: UserProfile,
        user_message: str,
        *,
        main_target: Optional[str] = None,
        preferred_side_target: Optional[str] = None,
        allow_medium_target: bool = True,
    ) -> str:
        ack = self._build_lightweight_field_ack_from_message(user_message, user_profile)
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
            and preferred_side_target == "partner_requirement"
            and self.collection_policy.can_actively_ask(user_profile, "partner_requirement")
        ):
            if bridge_context:
                side_prompt = random.choice(PARTNER_REQUIREMENT_ASK_VARIANTS)
            elif main_target in {"education", "occupation"}:
                return self._build_fused_partner_requirement_prompt(main_target)
            else:
                side_prompt = random.choice(PARTNER_REQUIREMENT_ASK_VARIANTS)
        elif (
            allow_medium_target
            and preferred_side_target == "monthly_income"
            and self.collection_policy.can_actively_ask(user_profile, "monthly_income")
        ):
            if main_target == "occupation":
                if bridge_context:
                    side_prompt = random.choice(INCOME_ASK_VARIANTS)
                else:
                    return self._build_fused_income_prompt(main_target)
            else:
                side_prompt = random.choice(INCOME_ASK_VARIANTS)
        elif (
            allow_medium_target
            and preferred_side_target == "marital_status"
            and self.collection_policy.can_actively_ask(user_profile, "marital_status")
        ):
            if main_target in {"age", "location", "education", "occupation"}:
                return self._build_fused_marital_status_prompt(main_target)
            side_prompt = "感情状态这边我也顺手确认一下，你现在是单身状态吗？"
        elif allow_medium_target and preferred_side_target:
            side_prompt = self._build_policy_field_prompt(preferred_side_target, user_profile, user_message=user_message)

        if main_prompt and side_prompt:
            prompt = f"{main_prompt} {side_prompt}".strip()
        elif main_prompt:
            prompt = main_prompt
        elif side_prompt:
            prompt = side_prompt
        else:
            prompt = random.choice(NEUTRAL_HOLD_VARIANTS)

        if ack:
            return f"{ack} {prompt}".strip()
        return prompt

    async def _enforce_profile_bridge_response(
        self,
        response: str,
        *,
        account_id: str,
        user_message: str,
        user_profile: UserProfile,
        turn_decision: TurnDecision,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        text = str(response or "").strip()
        if not text or turn_decision.response_channel != "model":
            return text

        bridge_bundle = self._resolve_profile_bridge_bundle(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )
        if not bridge_bundle:
            return text

        natural_response, extract_block = self._split_response_and_extract(text)
        if not natural_response:
            return text

        asked_fields = self._detect_asked_fields_in_response(natural_response)
        main_target = str(bridge_bundle["main_target"])
        side_targets = set(bridge_bundle["side_targets"])
        has_splice_markers = self._contains_profile_bridge_splice_markers(natural_response)
        if main_target in asked_fields and side_targets.issubset(asked_fields) and not has_splice_markers:
            return text

        missing_side_targets = sorted(side_targets - asked_fields)
        logger.info(
            "[profile_bridge] enforce_needed main=%s missing=%s asked=%s splice=%s",
            main_target,
            missing_side_targets,
            sorted(asked_fields),
            int(has_splice_markers),
        )

        rewritten = await self._rewrite_response_for_profile_bridge(
            natural_response=natural_response,
            account_id=account_id,
            user_message=user_message,
            bridge_bundle=bridge_bundle,
            conversation_context=conversation_context,
        )
        if not rewritten:
            fallback_side_target = next(iter(side_targets)) if side_targets else None
            if self._should_allow_interleaving_followup(
                user_profile,
                main_target,
                fallback_side_target,
                allow_medium_target=turn_decision.allow_medium_target,
            ):
                fallback = self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=main_target,
                    preferred_side_target=fallback_side_target,
                    allow_medium_target=turn_decision.allow_medium_target,
                ).strip()
            else:
                fallback = self._build_policy_field_prompt(main_target, user_profile, user_message=user_message).strip()
            if fallback:
                if extract_block:
                    return f"{fallback}\n{extract_block}"
                return fallback
            return text
        if extract_block:
            return f"{rewritten}\n{extract_block}"
        return rewritten

    @staticmethod
    def _contains_profile_bridge_splice_markers(text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        markers = (
            "再补一个小问题",
            "我再补一个小问题",
            "如果你方便的话",
            "不方便说也没关系",
            "顺手说个大概",
            "顺手说说",
            "也可以一起说说",
            "另外我也顺手问下",
            "另外我也想顺手问下",
        )
        return any(marker in normalized for marker in markers)

    async def _rewrite_response_for_profile_bridge(
        self,
        *,
        natural_response: str,
        account_id: str,
        user_message: str,
        bridge_bundle: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        bridge_context = bridge_bundle.get("context") or {}
        summary = "；".join(f"{key}={value}" for key, value in bridge_context.items()) or "-"
        main_prompt_label = str(bridge_bundle.get("main_prompt_label") or "-")
        side_prompt_labels = "；".join(bridge_bundle.get("side_prompt_labels") or []) or "-"
        recent_responses = (conversation_context or {}).get("recent_responses") or []
        recent_text = " / ".join(
            self._clean_response(item) for item in recent_responses[-2:] if str(item or "").strip()
        ) or "-"
        prompt = (
            "你在继续同一轮婚恋咨询聊天，请只重写给用户看的一句或两句中文回复，不要输出extract，不要解释原因。\n"
            "当前是 PROFILE_BRIDGE 高优先级模式。\n"
            f"用户这轮刚给的信息：{summary}\n"
            f"本轮主问题必须问到：{main_prompt_label}\n"
            f"本轮必须一起带出：{side_prompt_labels}\n"
            "要求：\n"
            "1. 必须顺着用户刚给的信息继续聊，至少利用其中一项。\n"
            "2. 不要机械复述资料，不要写成固定模板，不要变成列表。\n"
            "3. 主问题和必带相近字段都要问到，不能只保留主问题。\n"
            "4. 不要使用补问式拼接表达，例如“再补一个小问题”“如果你方便的话”“不方便说也没关系”“也可以一起说说”。\n"
            "5. 要把主问题和相近字段自然融合，优先 1 句完成，最多 2 句。\n"
            f"用户原话：{user_message or '-'}\n"
            f"最近两轮回复：{recent_text}\n"
            f"待重写原句：{natural_response or '-'}\n"
        )
        try:
            rewritten = await self.ai_service.generate_response(
                message=prompt,
                system_prompt="你是一个说中文的AI助手，请只输出重写后的中文回复。",
                max_tokens=180,
                timeout=max(0.5, float(self.ai_service.resolve_timeout_settings()["chat_ai_timeout"])),
                model_name=self._select_model_for_turn(user_message, prompt),
            )
            return self._clean_response(rewritten).strip()
        except Exception as exc:
            logger.warning("[profile_bridge] AI 重写失败: %s", exc)
            return ""

    @staticmethod
    def _looks_like_contact_value(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        digits_only = re.sub(r"\D", "", text)
        if re.match(r"^1[3-9]\d{9}$", digits_only) or re.match(r"^[5-9]\d{7}$", digits_only):
            return True
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9_-]{5,19}$", text))

    def _is_contact_like_user_message(self, user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        if any(token in text for token in CONTACT_ASK_MARKERS):
            return True
        if self._looks_like_contact_value(text):
            return True
        if self._extract_contact_candidate_from_message(text) or self._extract_contacts_from_message(text):
            return True
        return False

    def _apply_refusal_respect_guard(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        message = str(user_message or "").strip()
        if not text or not message:
            return text
        if not any(re.search(pattern, message) for pattern in (r"不方便", r"不想说", r"先不说", r"不留", r"不太想", r"算了", r"再说吧")):
            return text
        if "必须" in text or "一定要" in text or "赶紧留电话" in text or "不留不行" in text:
            return "没关系，这块我们先不急，按你方便的节奏来。"

        try:
            next_action = self.contact_service.get_next_action(user_profile, message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value in {"none", "end"} and self.contact_service.is_contact_complete(user_profile):
            return self._get_contact_terminal_or_resume_response(user_profile, message)

        if action_value == "ask_wechat":
            return "没关系，你要是觉得微信更方便，留个微信也可以。"
        if action_value == "persuade_wechat":
            return "你要是更习惯微信的话，留个常用微信就行，后面沟通也方便一些。"
        if action_value == "ask_phone":
            return "没关系，这块我们先不急。你要是方便的话，留个手机号就行。"
        if action_value == "persuade_phone":
            return "我懂，你现在可能不太想留电话。只是后面要是真有合适的，留个常用手机号也方便继续联系上你。"
        if self._contains_contact_push_markers(text):
            return "没关系，这块我们先不急，继续聊别的也可以。"
        if not any(marker in text for marker in ("没关系", "不急", "不勉强", "理解", "那我们先")):
            return f"没关系，{text}"
        return text

    def _apply_humanlike_turn_structure_policy(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
        *,
        allow_medium_target: bool = True,
    ) -> str:
        text = str(response or "").strip()
        if not text or user_profile.conversation_ended:
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if not asked_fields:
            return text

        recent_asked_fields = list(getattr(user_profile, "recent_asked_fields", []) or [])
        last_asked_field = recent_asked_fields[-1] if recent_asked_fields else None

        if (
            last_asked_field
            and last_asked_field in (ASK_GUARD_CORE_FIELDS | ASK_GUARD_MEDIUM_FIELDS)
            and last_asked_field in asked_fields
        ):
            policy_decision = self.collection_policy.decide(
                user_profile,
                user_message=user_message,
                allow_contact_target=False,
                allow_medium_target=allow_medium_target,
            )
            return self._build_interleaving_followup(
                user_profile,
                user_message,
                main_target=policy_decision.main_target,
                preferred_side_target=policy_decision.side_target,
                allow_medium_target=allow_medium_target,
            )

        recent_core_streak = self._get_recent_core_streak(user_profile)
        asks_core_only = bool(asked_fields & ASK_GUARD_CORE_FIELDS) and not bool(asked_fields & ASK_GUARD_MEDIUM_FIELDS)
        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=allow_medium_target,
        )
        if (
            asks_core_only
            and policy_decision.main_target in {"education", "occupation"}
            and self._should_allow_interleaving_followup(
                user_profile,
                policy_decision.main_target,
                policy_decision.side_target,
                allow_medium_target=allow_medium_target,
            )
        ):
            return self._build_interleaving_followup(
                user_profile,
                user_message,
                main_target=policy_decision.main_target,
                preferred_side_target=policy_decision.side_target,
                allow_medium_target=allow_medium_target,
            )

        if recent_core_streak >= 3 and asks_core_only and self._should_allow_interleaving_followup(
            user_profile,
            policy_decision.main_target,
            policy_decision.side_target,
            allow_medium_target=allow_medium_target,
        ):
            return self._build_interleaving_followup(
                user_profile,
                user_message,
                main_target=policy_decision.main_target,
                preferred_side_target=policy_decision.side_target,
                allow_medium_target=allow_medium_target,
            )

        return text

    @staticmethod
    def _render_preference_for_ack(preference: str) -> str:
        text = str(preference or "").strip()
        if not text:
            return text

        text = re.sub(r"^(喜欢|想找|想要|找)\s*", "", text)
        text = re.sub(r"^一个", "", text)
        text = text.strip("，,。 ")

        if text.endswith("的女生"):
            return text[:-3] + "女生"
        if text.endswith("的男生"):
            return text[:-3] + "男生"
        if text.endswith("的女孩子"):
            return text[:-4] + "女孩子"
        if text.endswith("的男孩子"):
            return text[:-4] + "男孩子"
        return text

    @staticmethod
    def _render_occupation_for_ack(value: str) -> str:
        text = str(value or "").strip()
        if text.endswith("的") and len(text) >= 3:
            text = text[:-1]
        return text

    @staticmethod
    def _render_marital_status_for_ack(value: str) -> str:
        text = str(value or "").strip()
        if text == "单身":
            return "单身"
        if text in {"未婚", "离异", "已婚"}:
            return text
        return text

    def _build_policy_field_prompt(
        self,
        field: Optional[str],
        user_profile: Optional[UserProfile] = None,
        *,
        user_message: str = "",
        stage: str = "trust",
    ) -> str:
        return self.dialogue_expression_service.render_field_question(
            field,
            profile=user_profile,
            stage=stage,
            user_message=user_message,
        )

    def _enforce_core_mainline_followup(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        ask_field: Optional[str],
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "ack_and_ask",
    ) -> str:
        """如果本轮决策已锁定核心字段，后处理不得把它洗成空转或改问别的字段。"""
        text = str(response or "").strip()
        if not text:
            return text
        if response_channel != "model":
            return text
        if ask_field not in ASK_GUARD_CORE_FIELDS:
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text
        if self._contains_contact_push_markers(text):
            try:
                next_action = self.contact_service.get_next_action(user_profile, user_message)
                action_value = getattr(next_action, "value", str(next_action))
            except Exception:
                action_value = "none"
            if action_value in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}:
                return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict)
        }
        effective_ask_field = self._resolve_effective_followup_field(
            user_profile,
            ask_field=ask_field,
            collected_fields=collected_fields,
            user_message=user_message,
            allow_medium_target=True,
        )
        policy_decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=True,
        )

        asked_fields = self._detect_asked_fields_in_response(text)
        if effective_ask_field in asked_fields:
            return text

        approved_side_target = policy_decision.side_target
        if (
            effective_ask_field in {"education", "occupation"}
            and approved_side_target
            and approved_side_target in asked_fields
            and self._should_allow_interleaving_followup(
                user_profile,
                effective_ask_field,
                approved_side_target,
                allow_medium_target=True,
            )
        ):
            return self._build_interleaving_followup(
                user_profile,
                user_message,
                main_target=effective_ask_field,
                preferred_side_target=approved_side_target,
                allow_medium_target=True,
            )

        fallback_hold_markers = (
            "你接着说就行",
            "顺着往下了解",
            "顺着听",
            "你继续说",
            "我顺着听",
            "我顺着往下了解",
        )
        asks_wrong_field = bool(asked_fields) and effective_ask_field not in asked_fields
        is_empty_hold = any(marker in text for marker in fallback_hold_markers)

        if self.collection_policy.has_divorce_confirmation_pending(user_profile):
            return text
        if effective_ask_field == "marital_status" and self._should_lock_divorce_confirmation(user_profile, user_message):
            return self._build_divorce_confirmation_response()

        if asks_wrong_field or is_empty_hold or not asked_fields:
            if (
                effective_ask_field in {"education", "occupation"}
                and approved_side_target
                and self._should_allow_interleaving_followup(
                    user_profile,
                    effective_ask_field,
                    approved_side_target,
                    allow_medium_target=True,
                )
            ):
                return self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=effective_ask_field,
                    preferred_side_target=approved_side_target,
                    allow_medium_target=True,
                )
            return self._build_policy_field_prompt(effective_ask_field, user_profile, user_message=user_message)
        return text

    def _enforce_active_target_followup(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        ask_field: Optional[str],
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "ack_and_ask",
    ) -> str:
        """当本轮已有明确目标字段时，禁止回复退化成纯承接或空收口。"""
        text = str(response or "").strip()
        if not text:
            return text
        if response_channel != "model":
            return text
        if ask_field not in {"sex", "age", "location", "education", "occupation", "marital_status", "partner_requirement", "monthly_income"}:
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict)
        }
        effective_ask_field = self._resolve_effective_followup_field(
            user_profile,
            ask_field=ask_field,
            collected_fields=collected_fields,
            user_message=user_message,
            allow_medium_target=True,
        )

        asked_fields = self._detect_asked_fields_in_response(text)
        if effective_ask_field in asked_fields:
            return text

        generic_hold_markers = (
            "好的，信息我先记下了",
            "好，信息我先记下了",
            "信息我先记下了",
            "我先记下了",
            "好，我知道了",
            "我知道了",
            "先这样",
            "你继续说",
            "顺着聊",
        )
        if any(marker in text for marker in generic_hold_markers):
            return self._build_policy_field_prompt(effective_ask_field, user_profile, user_message=user_message)

        if not asked_fields and len(text) <= 18:
            return self._build_policy_field_prompt(effective_ask_field, user_profile, user_message=user_message)

        if asked_fields and effective_ask_field not in asked_fields:
            return self._build_policy_field_prompt(effective_ask_field, user_profile, user_message=user_message)

        return text

    def _enforce_pending_partner_requirement_followup(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        ask_field: Optional[str],
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "ack_and_ask",
    ) -> str:
        """当 partner_requirement 仍阻挡联系方式时，本轮必须真问出来。"""
        text = str(response or "").strip()
        if not text or response_channel != "model":
            return text
        if ask_field != "partner_requirement":
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text
        if self.collection_policy.should_block_preference_ask(user_profile, ""):
            return text
        if not self.collection_policy.can_actively_ask(user_profile, "partner_requirement"):
            return text

        asked_fields = self._detect_asked_fields_in_response(text)
        if "partner_requirement" in asked_fields:
            return text

        hold_markers = (
            "这个点我不重复绕了",
            "你想聊别的就顺着说",
            "你继续说",
            "顺着往下了解",
            "顺着听",
            "接着往下聊",
            "先收住",
        )
        if asked_fields or any(marker in text for marker in hold_markers):
            return self._build_policy_field_prompt("partner_requirement", user_profile, user_message=user_message)

        return text

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
        if ask_field not in collected_fields:
            return ask_field

        decision = self.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=True,
            allow_medium_target=allow_medium_target,
        )
        next_field = decision.main_target
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

    def _enforce_natural_completion_transition(
        self,
        response: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        *,
        user_message: str = "",
    ) -> str:
        """收完核心主线末段后，禁止空转，优先自然切到联系方式。"""
        text = str(response or "").strip()
        if not text:
            return text
        if self._contains_contact_push_markers(text):
            return text
        if self._is_contact_like_user_message(user_message):
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in (collection_result.get("all_fields") or [])
            if isinstance(item, dict)
        }
        hold_markers = (
            "你接着说就行",
            "你继续说",
            "顺着听",
            "顺着往下了解",
            "接着往下聊",
        )
        looks_like_hold = any(marker in text for marker in hold_markers)
        just_collected_occupation = "occupation" in collected_fields

        if just_collected_occupation and self.collection_policy.can_enter_contact(user_profile):
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)

        if looks_like_hold and self.collection_policy.can_enter_contact(user_profile):
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)

        return text

    def _handoff_to_contact_after_core_completion(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        contact_gate_before: bool = False,
    ) -> str:
        """本轮刚补齐最后一个核心字段时，同轮直接切到联系方式入口。"""
        text = str(response or "").strip()
        if not text or response_channel != "model":
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if contact_gate_before:
            return text
        if self._is_withdraw_or_stop_message(user_message):
            return text
        if not self.collection_policy.can_enter_contact(user_profile):
            return text
        if self._contains_contact_push_markers(text):
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text
        if (collection_result or {}).get("divorce_confirmation_cleared"):
            return text
        if self._is_resume_profile_collection_message(user_message):
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
        if not all_fields:
            return text

        collected_fields = {
            str(item.get("field") or "").strip()
            for item in all_fields
        }
        if not collected_fields & ASK_GUARD_CORE_FIELDS:
            return text

        try:
            next_action = self.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value == "ask_phone":
            if user_profile.wechat_collected and user_profile.wechat:
                return self._build_contact_followup_response("ask_phone", "wechat")
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)
        if action_value == "persuade_phone":
            return self._build_contact_followup_response("persuade_phone", "wechat")
        if action_value == "ask_wechat":
            if user_profile.phone_collected and user_profile.phone:
                return self._build_contact_followup_response("ask_wechat", "phone")
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)
        if action_value == "persuade_wechat":
            return self._build_contact_followup_response("persuade_wechat", "phone")

        if action_value in {"none", "", None}:
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)
        return text

    def _handoff_to_pending_target_after_core_completion(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
        contact_gate_before: bool = False,
    ) -> str:
        """最后一个核心字段刚补齐但联系方式仍未开放时，统一切到剩余中等目标。"""
        text = str(response or "").strip()
        if not text or response_channel != "model":
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if self.collection_policy.can_enter_contact(user_profile):
            return text
        if self._is_withdraw_or_stop_message(user_message):
            return text
        if self._contains_contact_push_markers(text):
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text
        if (collection_result or {}).get("divorce_confirmation_cleared"):
            return text
        if self._is_resume_profile_collection_message(user_message):
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
        collected_fields = {str(item.get("field") or "").strip() for item in all_fields}
        if not (collected_fields & ASK_GUARD_CORE_FIELDS):
            return text
        if self.collection_policy.get_uncovered_core_fields(user_profile):
            return text

        if self.collection_policy.can_actively_ask(user_profile, "partner_requirement"):
            host_field = self.collection_policy.get_medium_transition_host(user_profile, "partner_requirement")
            if host_field:
                return self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=host_field,
                    preferred_side_target="partner_requirement",
                    allow_medium_target=True,
                )
            return self._build_policy_field_prompt("partner_requirement", user_profile, user_message=user_message)
        if self.collection_policy.can_actively_ask(user_profile, "marital_status"):
            host_field = self.collection_policy.get_medium_transition_host(user_profile, "marital_status")
            if host_field:
                return self._build_interleaving_followup(
                    user_profile,
                    user_message,
                    main_target=host_field,
                    preferred_side_target="marital_status",
                    allow_medium_target=True,
                )
            return self._build_policy_field_prompt("marital_status", user_profile, user_message=user_message)
        if self.collection_policy.can_actively_ask(user_profile, "monthly_income"):
            return self._build_policy_field_prompt("monthly_income", user_profile, user_message=user_message)
        return text

    def _handoff_to_contact_after_medium_completion(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
        response_channel: str = "model",
        primary_move: str = "",
    ) -> str:
        """本轮补齐最后一个中等字段后，同轮直接切到联系方式。"""
        text = str(response or "").strip()
        if not text or response_channel != "model":
            return text
        if primary_move in {"repair_and_release", "answer_then_pause", "soft_hold", "ack_only", "confirm_status_only"}:
            return text
        if self._is_withdraw_or_stop_message(user_message):
            return text
        if self._contains_contact_push_markers(text):
            return text
        if self._is_contact_like_user_message(user_message):
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text
        if (collection_result or {}).get("divorce_confirmation_cleared"):
            return text
        if self._is_resume_profile_collection_message(user_message):
            return text
        if not self.collection_policy.can_enter_contact(user_profile):
            return text

        all_fields = [
            item for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        collected_fields = {str(item.get("field") or "").strip() for item in all_fields}
        if "partner_requirement" not in collected_fields:
            return text
        if self.collection_policy.get_uncovered_core_fields(user_profile):
            return text
        if self.collection_policy.get_uncovered_medium_fields(user_profile):
            return text

        return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)

    @staticmethod
    def _render_age_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return text
        if text.endswith(("岁", "后", "年")):
            return text
        if text.isdigit():
            return f"{text}岁"
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
        """AI 不可用时的本地兜底，优先保证用户收到完整回复。"""
        message = (user_message or "").strip()
        normalized_message = re.sub(r"[\s,，。！？!?~～、]+", "", message)
        seed_hint = f"{account_id}:{user_profile.updated_at.isoformat()}:{message}"
        opening_fields = self._extract_deterministic_profile_fields(message)
        try:
            last_response = await self.dialogue_manager.get_last_response(account_id) or ""
        except Exception:
            last_response = ""

        if self.collection_policy.has_divorce_confirmation_pending(user_profile) or self._should_lock_divorce_confirmation(user_profile, message):
            return self._build_divorce_confirmation_response()

        if (
            self._is_stable_opening_greeting(message)
            and not opening_fields
            and not self._is_explicit_matchmaking_intent_message(message)
        ):
            return self.greeting_service.get_greeting_response(message, seed_hint=seed_hint)

        if (
            not opening_fields
            and not self._is_explicit_matchmaking_intent_message(message)
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
            and not last_response
            and self._is_noisy_opening_clarify_message(message)
        ):
            return self.greeting_service.get_opening_clarify_response(seed_hint=seed_hint)

        if (
            not opening_fields
            and not self._is_stable_opening_greeting(message)
            and not self._is_explicit_matchmaking_intent_message(message)
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
            and not last_response
            and not self.collection_policy.has_divorce_confirmation_pending(user_profile)
            and not self._should_lock_divorce_confirmation(user_profile, message)
            and self._should_use_opening_clarify(message)
        ):
            return self.greeting_service.get_opening_clarify_response(seed_hint=seed_hint)

        if (
            self._is_explicit_matchmaking_intent_message(message)
            and not opening_fields
            and not self._detect_priority_question_intent(message)
            and not self._is_boundary_pause_triggered(message, user_profile)
            and not self._is_risk_guard_triggered(message)
        ):
            return self.greeting_service.get_open_self_intro_response(seed_hint=seed_hint)

        message_count = 1 if last_response else 0
        if self._should_treat_as_opening_service_confirmation(
            user_profile,
            stage="opening",
            message_count=message_count,
            user_message=message,
            last_response=last_response,
        ):
            return random.choice(SERVICE_CONFIRMATION_OPENING_ACK_VARIANTS)

        if self._should_treat_as_mid_service_confirmation(
            user_profile,
            stage="opening" if not last_response else "understanding",
            message_count=message_count,
            user_message=message,
            last_response=last_response,
        ):
            return self._build_service_confirmation_resume_response(
                user_profile,
                message,
                message_count=message_count,
                last_response=last_response,
            )

        faq_intent = self._detect_priority_question_intent(message)
        resume_profile_collection = self._is_resume_profile_collection_message(message)
        opening_guard_intent = self.turn_intent_classifier.classify_opening_low_pressure(
            user_message=message,
            last_response=last_response,
            message_count=message_count,
            has_opening_fields=bool(opening_fields),
            has_faq_intent=bool(faq_intent),
            has_boundary_pause=bool(self._is_boundary_pause_triggered(message, user_profile)),
            has_risk_guard=bool(self._is_risk_guard_triggered(message)),
        )
        if opening_guard_intent.intent == "low_pressure_opening":
            return self.greeting_service.get_open_self_intro_response(seed_hint=seed_hint)
        post_answer_reentry = self._is_post_answer_reentry_turn(message, last_response)
        allow_contact_target = not (
            bool(faq_intent)
            or resume_profile_collection
            or self._is_boundary_pause_triggered(message, user_profile)
            or self._is_risk_guard_triggered(message)
            or self.collection_policy.has_divorce_confirmation_pending(user_profile)
        )
        allow_medium_target = not self.collection_policy.should_block_medium_fields_for_turn(
            user_profile,
            user_message=message,
            allow_contact_target=allow_contact_target,
            prioritize_user_question=bool(faq_intent),
            primary_move="answer_then_pause" if faq_intent else ("soft_hold" if self._is_boundary_pause_triggered(message, user_profile) else "ack_and_ask"),
            resume_profile_collection=(resume_profile_collection or post_answer_reentry),
        )

        faq_response = self._get_priority_question_response(message, user_profile)
        if faq_response:
            return faq_response

        if self._last_response_asked_partner_requirement(last_response):
            preference = self._extract_simple_partner_requirement(message)
            if preference:
                return self._build_partner_requirement_fallback_followup(
                    user_profile,
                    user_message=message,
                )

        try:
            next_action = self.contact_service.get_next_action(user_profile, message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if allow_contact_target and (
            self.collection_policy.can_enter_contact(user_profile)
            or self._has_active_contact_context(user_profile, user_message=message)
        ):
            if action_value == "ask_phone":
                if user_profile.wechat_collected and user_profile.wechat:
                    return self._build_contact_followup_response("ask_phone", "wechat")
                return "方便留个电话吗？后面沟通会方便些。"
            if action_value == "persuade_phone":
                return self._build_phone_persuasion_fallback()
            if action_value == "ask_wechat":
                if user_profile.phone_collected and user_profile.phone:
                    return self._build_contact_followup_response("ask_wechat", "phone")
                return "没关系，你要是觉得微信更方便，留个微信也可以。"
            if action_value == "persuade_wechat":
                return "你要是更习惯微信的话，留个常用微信就行，后面沟通也方便一些。"
            if action_value == "end":
                return self._get_both_rejected_ending_response()
            if action_value in {"none", "", None}:
                if (
                    (user_profile.phone_collected and user_profile.phone)
                    or (user_profile.wechat_collected and user_profile.wechat)
                    or user_profile.rejected_phone
                    or user_profile.rejected_wechat
                ):
                    return self._get_contact_terminal_or_resume_response(user_profile, message)
                return self._build_policy_field_prompt("contact", user_profile, user_message=message)

        decision = self.collection_policy.decide(
            user_profile,
            user_message=message,
            allow_contact_target=allow_contact_target,
            allow_medium_target=allow_medium_target,
            prioritize_user_question=bool(faq_intent),
            primary_move="answer_then_pause" if faq_intent else ("soft_hold" if self._is_boundary_pause_triggered(message, user_profile) else "ack_and_ask"),
            resume_profile_collection=(resume_profile_collection or post_answer_reentry),
        )
        unresolved_core_fields = self.collection_policy.get_uncovered_core_fields(user_profile)
        core_resume_followup = None
        if unresolved_core_fields:
            next_core = unresolved_core_fields[0]
            if self.collection_policy.can_actively_ask(user_profile, next_core):
                core_resume_followup = self._build_policy_field_prompt(next_core, user_profile, user_message=message).strip()
        if decision.next_mode == "open_profile_repair":
            return "我大概有点了解你了，你也不用一项项回，顺着说说你现在的生活和工作状态就行。"
        if decision.next_mode in {"low_pressure_chat", "terminate_conversion"}:
            if core_resume_followup:
                return core_resume_followup
            ack = self._build_lightweight_field_ack_from_message(message, user_profile)
            return ack or "好，我先顺着听，你想聊什么就聊什么。"
        if decision.next_mode == "contact_hold":
            if core_resume_followup:
                return core_resume_followup
            ack = self._build_lightweight_field_ack_from_message(message, user_profile)
            return ack or "嗯，我知道了，我们先顺着你这句聊。"

        recent_core_streak = self._get_recent_core_streak(user_profile)
        if (
            decision.main_target in ASK_GUARD_CORE_FIELDS
            and recent_core_streak >= 3
            and allow_medium_target
            and decision.side_target
        ):
            return self._build_interleaving_followup(
                user_profile,
                message,
                main_target=decision.main_target,
                preferred_side_target=decision.side_target,
                allow_medium_target=allow_medium_target,
            )

        last_asked_field = (user_profile.recent_asked_fields or [])[-1] if user_profile.recent_asked_fields else None
        if decision.main_target and last_asked_field == decision.main_target:
            return self._build_interleaving_followup(
                user_profile,
                message,
                main_target=decision.main_target,
                preferred_side_target=decision.side_target,
                allow_medium_target=allow_medium_target,
            )

        ack = self._build_lightweight_field_ack_from_message(message, user_profile)

        # Phase 1: 偏好类去重 guard - 已有 partner_requirement 后禁止泛化偏好问题
        has_partner_requirement = bool(
            getattr(user_profile, "partner_requirement", None)
            or user_profile.collection_progress.get("partner_requirement")
        )

        if decision.main_target:
            # 如果已有偏好但决策要去问 partner_requirement，则跳过这个目标
            if decision.main_target == "partner_requirement" and has_partner_requirement:
                followup = "你继续说，我顺着往下了解。"
            else:
                followup = self._build_policy_field_prompt(decision.main_target, user_profile, user_message=message)
            if ack:
                return f"{ack} {followup}".strip()
            return followup

        if resume_profile_collection:
            return "我们先不把资料问得太密，你也可以先说说自己更在意哪块，我顺着往下了解。"

        if ack:
            return ack

        if core_resume_followup:
            return core_resume_followup

        if self.collection_policy.can_enter_contact(user_profile):
            return self._build_policy_field_prompt("contact", user_profile, user_message=message)
        return "你继续说，我先顺着听。"

    async def _update_conversation_state(
        self,
        account_id: str,
        user_message: str,
        clean_response: str,
        raw_response: str,
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

        # 智能追问机制：追踪AI询问的字段
        if track_asked_fields and self._is_delivery_viable(canonical_response):
            await self.ask_tracking_service.track_ai_asked_fields(account_id, canonical_response)

        # Phase 2: 记录本轮追问的字段（用于短答槽位绑定）
        user_profile = await self.user_service.get_user_profile(account_id)
        message_count = await self.dialogue_manager.get_message_count(account_id)
        asked_field = self._detect_which_field_is_asked(canonical_response)
        pending_sex_confirmation = _extract_confirmed_sex_candidate_from_context(canonical_response)
        profile_changed = False
        if pending_sex_confirmation and asked_field == "sex":
            if user_profile.pending_sex_confirmation != pending_sex_confirmation:
                user_profile.pending_sex_confirmation = pending_sex_confirmation
                profile_changed = True
        elif asked_field and asked_field != "sex" and user_profile.pending_sex_confirmation:
            user_profile.pending_sex_confirmation = None
            profile_changed = True
        if asked_field:
            user_profile.set_last_asked_field(asked_field, message_count)
            logger.info(f"[短答槽位绑定] 记录本轮追问字段: {asked_field}, turn_index: {message_count}")
            profile_changed = True
        elif user_profile.last_asked_field:
            # 如果本轮没有追问，清除上一轮记录
            user_profile.clear_last_asked_field()
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
            return self.contact_service.get_status_display(user_profile)

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
            logger.info("[话术合规] 已替换禁语表达，避免出现见面/发资料承诺")
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

        followup = self._build_policy_field_prompt(ask_field, user_profile, user_message=user_message).strip() if ask_field else ""
        ack = self._build_opening_profile_ack_from_message(user_message) or self._build_lightweight_field_ack_from_message(
            user_message,
            user_profile,
        )
        if not ack and "age" in extracted_fields and user_profile.age:
            ack = f"好，{self._render_age_value(str(user_profile.age))}我知道了。"

        rebuilt = " ".join(part for part in (ack, followup) if part).strip()
        return rebuilt or text

    @staticmethod
    def _sanitize_robotic_tone(response: str) -> str:
        """压掉明显的登记腔、客服腔和业务身份腔。"""
        text = str(response or "").strip()
        if not text:
            return text

        replacements = {
            "我是帮大家做交友匹配的小缘": "我是小缘",
            "交友匹配": "聊这个",
            "我先确认一下": "我想先确认一下",
            "顺口问下": "想问下",
            "给你匹配到合适的人选": "后面要是有合适的方向",
            "及时联系到你": "继续联系上你",
            "及时通知到你": "继续联系上你",
            "方便及时通知到你": "方便继续联系上你",
            "资料差不多先了解到了": "后面要是继续聊得合适",
            "我已经记下啦": "我知道了",
            "我先记下来啦": "我知道了",
            "哈哈是呀，": "",
            "是这样哦，": "",
        }
        for before, after in replacements.items():
            text = text.replace(before, after)

        # 只做安全的整句级清洗，避免片段替换把句子洗坏。
        text = re.sub(r"我记下你是", "你是", text)
        text = re.sub(r"我记下来啦", "我知道了", text)
        text = re.sub(r"我记下来", "我知道了", text)
        text = re.sub(r"我记下了", "我知道了", text)
        text = re.sub(r"我记下", "我知道了", text)
        text = re.sub(r"我先按([^，。！？!?]+)记(着|下|哈)?", r"\1是吧", text)
        text = re.sub(r"我先按([^，。！？!?]+)理解", r"\1是吧", text)
        text = re.sub(r"那我先按([^，。！？!?]+)记(着|下|哈)?", r"\1是吧", text)
        text = re.sub(r"我知道了来你是", "我知道了，你是", text)
        text = re.sub(r"我知道了你是", "你是", text)
        text = re.sub(r"(好的|好呀|好哒)，?你是", r"\1，你是", text)
        text = re.sub(r"^好[，,\s]*你是(男生|女生)(?:啦|呀|哈|啊)?[。.]?\s*", "", text)
        text = re.sub(r"^好[，,\s]*(男生|女生)是吧[。.]?\s*", "", text)
        text = re.sub(r"^(你是|是)(男生|女生)(?:啦|呀|哈|啊)?[。.]?\s*", "", text)
        text = re.sub(r"^你在[^。！？!?]{0,20}是吧[。.]?\s*", "", text)
        # 压掉轮轮复述型开头，避免“本科是吧 / 90后是吧 / 做美容是吧 / 在深圳这边是吧”过重。
        text = re.sub(r"^(?:好[，,\s]*)?(?:在)?[^。！？!?]{1,8}这边是吧[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?(?:做)?[^。！？!?]{1,10}(?:是吧|我知道了|这块我知道了|方向，明白了)[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?(?:90后|80后|00后|\d{2}岁)(?:呀[，,]?)?(?:知道了|明白了|我知道了|是吧)?[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?(?:本科|大专|硕士|博士)(?:这边明白了|我知道了|是吧)?[。.]?\s*", "", text)

        blacklist_patterns = [
            r"同城脱单联盟",
            r"牵线(小伙伴|同事)?",
            r"精准匹配",
            r"第一时间联系",
            r"好消息",
            r"祝你早日脱单[🥰~！!。]*",
            r"匹配一般1-8小时[^\n。！？!?]*",
        ]
        for pattern in blacklist_patterns:
            text = re.sub(pattern, "", text)

        # Phase 1: 元策略话术清洗 - 压掉内部策略暴露表达
        # "按X来聊" -> 替换成短确认
        text = re.sub(r"那我们就按([^，。！？!?]+)来聊", r"\1是吧", text)
        text = re.sub(r"按([^，。！？!?]+)来聊", r"\1是吧", text)
        text = re.sub(r"按这个方向来聊", "这个方向我大概有数了", text)
        text = re.sub(r"按这个优先推进", "", text)
        text = re.sub(r"按这个优先筛", "", text)
        text = re.sub(r"按你的优先级来", "", text)
        text = re.sub(r"我先按([^，。！？!?]+)来理解", r"\1是吧", text)
        text = re.sub(r"我先按([^，。！？!?]+)来聊", r"\1是吧", text)

        # "先不连着问资料" 类表达直接清洗
        text = re.sub(r"[，,]?我们先不连着问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不连着追问[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先把节奏放缓一点[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不继续追资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不追问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不追问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不往资料上追问[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?(我|那我)?语气放轻松(一点|些)?[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我就把语气放轻一点[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我就轻松一点跟你聊[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?问得有点密了[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?像查户口一样[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?按流程来[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?按当前沟通流程来[^。！？!?]*", "", text)

        # Phase 2: 内部策略语言清洗 - 压掉暴露策略的表达
        # "按X方向帮你筛" 类表达
        text = re.sub(r"按这个方向帮你筛[^。！？!?]*", "", text)
        text = re.sub(r"按这个优先推进[^。！？!?]*", "", text)
        text = re.sub(r"我照这个方向[^。！？!?]*", "", text)
        text = re.sub(r"按这个方向来[^。！？!?]*", "", text)

        # "最在意/最看重" 类偏好追问表达
        text = re.sub(r"说一个最在意的匹配点[^。！？!?]*", "", text)
        text = re.sub(r"先说一个最在意[^。！？!?]*", "", text)
        text = re.sub(r"你先告诉我你最看重[^。！？!?]*", "", text)
        text = re.sub(r"我们可以先说一个[^。！？!?]*", "", text)
        text = re.sub(r"最看重的匹配条件[^。！？!?]*", "", text)
        text = re.sub(r"我按这个优先筛[^。！？!?]*", "", text)
        text = re.sub(r"我好优先筛选[^。！？!?]*", "", text)
        text = re.sub(r"你最看重哪一点，可以先顺手说说[^。！？!?]*", "", text)
        text = re.sub(r"你会更看重哪个[^。！？!?]*", "", text)
        text = re.sub(r"你会更偏哪边[^。！？!?]*", "", text)
        text = re.sub(r"按同城思路跟你聊[^。！？!?]*", "", text)
        text = re.sub(r"你最看重[^？?]*[？?]", "", text)
        text = re.sub(r"你最在意[^？?]*[？?]", "", text)

        # 内部策略标签清洗
        text = re.sub(r"主目标[：:][^。\n]*", "", text)
        text = re.sub(r"顺带目标[：:][^。\n]*", "", text)
        text = re.sub(r"本轮计划[：:][^。\n]*", "", text)
        text = re.sub(r"用户类型[：:][^。\n]*", "", text)
        text = re.sub(r"可进联系方式[：:][^。\n]*", "", text)

        text = re.sub(r"^好的，[，,\s]*", "好，", text)
        text = re.sub(r"^好呀，[，,\s]*", "好，", text)
        text = re.sub(r"^好哒，[，,\s]*", "好，", text)
        text = re.sub(r"^哈哈好的[，,\s]*", "好，", text)
        text = re.sub(r"^哈哈[，,\s]*", "", text)
        text = re.sub(r"联系电话不([。！？!?]?)", r"联系电话吗\1", text)
        text = re.sub(r"^(?:了|啦|呀|呢|哈|啊)[。．]\s*", "", text)
        text = re.sub(r"([。！？!?])\s*(哈哈，原来|原来|这样的话|所以说)\s*$", r"\1", text)
        text = re.sub(r"^(哈哈，原来|原来|这样的话|所以说)\s*$", "", text)
        text = re.sub(r"[，,。]{2,}", "。", text)
        text = re.sub(r"([。！？!?])([^\s])", r"\1 \2", text)
        text = re.sub(r"\s+", " ", text).strip(" ，,。")
        text = ChatService._strip_broken_edge_fragments(text)
        return text

    @staticmethod
    def _build_bridge_back_prefix(last_side_topic_type: Optional[str]) -> str:
        """
        Phase 2: FAQ/边界/complaint 后的桥接前缀生成。

        根据上轮的支线话题类型生成自然过渡语，避免生硬跳回主线。

        Args:
            last_side_topic_type: 支线话题类型，如 "faq", "boundary", "complaint", "risk"

        Returns:
            桥接前缀字符串，如 "这块先这样。" 或空字符串
        """
        if not last_side_topic_type:
            return ""

        # 根据支线类型选择不同的桥接语
        bridge_variants = {
            "faq": [
                "这块先这样。",
                "这个先放一边。",
                "照片这块先不往下走。",
                "联系方式这块先这样。",
            ],
            "boundary": [
                "这块先不勉强。",
                "这个先放一边。",
                "这块先这样。",
            ],
            "complaint": [
                "嗯，那我们换个节奏。",
                "好，那我们先不聊资料。",
            ],
            "risk": [
                "这块先不聊了。",
                "这个话题先这样。",
            ],
        }

        variants = bridge_variants.get(last_side_topic_type, ["这块先这样。"])
        return random.choice(variants)  # noqa: S311

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
    def _build_profile_summary_line(profile: UserProfile) -> str:
        """
        Phase 2: 构建画像小结语句。

        根据已收集的关键字段生成自然的小结语。

        Args:
            profile: 用户画像

        Returns:
            画像小结语句，如 "你在深圳、偏同城是吧。"
        """
        summary_parts = []

        # 城市
        location = profile.location or ""
        if location:
            summary_parts.append(f"在{location}")

        # 年龄
        age = profile.age or profile.age_label or ""
        if age:
            if "后" in str(age) or "岁" in str(age):
                summary_parts.append(str(age))
            else:
                summary_parts.append(f"{age}岁")

        # 学历
        education = profile.education or ""
        if education:
            summary_parts.append(education)

        # 偏好
        partner_req = profile.partner_requirement or ""
        if partner_req:
            # 简化偏好描述
            if "同城" in partner_req:
                summary_parts.append("偏同城")
            elif len(partner_req) <= 10:
                summary_parts.append(f"偏{partner_req}")

        if not summary_parts:
            return ""

        # 构建小结语句
        summary_text = "、".join(summary_parts[:3])  # 最多取 3 个关键点
        return f"你{summary_text}是吧。"

    @staticmethod
    def _is_short_answer(user_message: str, max_length: int = 12) -> bool:
        """
        Phase 2: 判断用户消息是否为短答。

        短答特征：
        - 长度短（通常 <= 12 字符）
        - 内容简洁（单字段信息、确认词等）
        - 不是完整句子（不含"我"、"在"等主语/介词）

        Args:
            user_message: 用户消息
            max_length: 最大长度阈值

        Returns:
            是否为短答
        """
        message = (user_message or "").strip()
        if not message:
            return False

        # 长度检查
        if len(message) > max_length:
            return False

        # 短答模式：单字段回答
        short_answer_patterns = [
            r"^(男|女|男的|女的|男生|女生)$",
            r"^\d{2,4}$",  # 纯数字（年龄、收入等）
            r"^\d{1,2}后$",
            r"^\d{1,2}岁$",
            r"^[北上广深成杭武南京苏][^\s]{0,4}$",  # 城市短答
            r"^(本科|大专|硕士|博士|高中|初中|中专)$",
            r"^(已婚|未婚|离异|单身)$",
            r"^(是|对|嗯|好|好的|行|可以|ok)$",
            r"^(不是|不对|没有|没)$",
            r"^同城",
            r"^[\d.]+万?$",  # 收入短答
            r"^[\d.]+万左右$",  # 收入短答（带"左右"）
        ]

        for pattern in short_answer_patterns:
            if re.match(pattern, message):
                return True

        # 完整句子特征：包含主语或介词组合，不是短答
        sentence_markers = ["我在", "我是", "我是在", "我在是", "我现在", "我这边"]
        if any(m in message for m in sentence_markers):
            return False

        # 简单判断：短消息且不含复杂标点
        complex_puncts = {"？", "?", "。", "！", "!", "，", ",", "、"}
        if not any(p in message for p in complex_puncts):
            return True

        return False

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
        short_sex_answer = re.search(
            r"^\s*(?:你们)?\s*(男生|女生|男的|女的|男|女)"
            r"(?:\s*[，,、 ]\s*(?:是的|对|嗯|好的|好))?"
            r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
            message,
        )
        trailing_punct_sex_answer = re.search(
            r"^\s*(?:你们)?\s*(男生|女生|男的|女的|男|女)\s*[，,、 ]+\s*$",
            message,
        )
        confirmation_context_sex = _extract_confirmed_sex_candidate_from_context(last_ai)
        affirmative_confirmation = _is_affirmative_confirmation_answer(message)
        if sex_question_context and short_sex_answer:
            raw = short_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            partner_value = str(guarded.get("partner_requirement") or "")
            if partner_value and any(token in partner_value for token in ["男", "女"]):
                guarded.pop("partner_requirement", None)
                logger.info("[提取保护] 性别问答上下文命中，移除本轮 partner_requirement 性别污染值")
            logger.info("[提取保护] 性别问答上下文命中，按 short answer 强制写入 sex")
        elif sex_question_context and trailing_punct_sex_answer:
            raw = trailing_punct_sex_answer.group(1)
            guarded["sex"] = "男" if "男" in raw else "女"
            logger.info("[提取保护] 性别问答上下文命中，按 trailing short answer 强制写入 sex")
        elif confirmation_context_sex and affirmative_confirmation:
            guarded["sex"] = confirmation_context_sex
            logger.info("[提取保护] 性别确认上下文命中，按 affirmative answer 强制写入 sex")

        return guarded

    def _prevent_no_repeat_hold_from_blocking_progress(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        if not text or user_profile.conversation_ended:
            return text
        if self._contains_contact_push_markers(text):
            return text
        if self._is_boundary_pause_triggered(user_message, user_profile):
            return text
        if self._is_risk_guard_triggered(user_message):
            return text

        no_repeat_hold_markers = (
            "不在这上面打转",
            "不重复绕了",
            "继续往下聊",
            "继续往下说",
            "接着往下聊",
        )
        if not any(marker in text for marker in no_repeat_hold_markers):
            return text

        unresolved_core = self.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core:
            next_field = self.collection_policy.get_main_target(
                user_profile,
                can_enter_contact=False,
                allow_contact_target=False,
            ) or unresolved_core[0]
            if next_field:
                return self._build_policy_field_prompt(next_field, user_profile, user_message=user_message)

        if self.collection_policy.can_enter_contact(user_profile):
            return self._build_policy_field_prompt("contact", user_profile, user_message=user_message)

        return text

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
