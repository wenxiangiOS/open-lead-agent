"""
信息提取服务

负责从 AI 回复和用户消息中提取结构化数据
"""

import logging
import re
from typing import Dict, Any, List, Optional
from src.models.user_profile import UserProfile
from src.services.data.user_service import UserService

logger = logging.getLogger(__name__)


class ExtractionService:
    _PARTNER_PREFERENCE_SUBSLOT_FIELDS = (
        "partner_pref_age",
        "partner_pref_age_relation",
        "partner_pref_location",
        "partner_pref_locality",
        "partner_pref_height",
        "partner_pref_education",
        "partner_pref_industry",
        "partner_pref_personality",
        "partner_pref_income",
        "partner_pref_other",
    )
    _SELF_PROFILE_FIELDS = {
        "sex",
        "age",
        "age_label",
        "location",
        "education",
        "occupation",
        "marital_status",
        "monthly_income",
    }
    _ROLE_CONSISTENT_FIELD_RULES = {
        "location": {
            "partner_context_checker": "_looks_like_partner_preference_location_context",
            "mixed_intro_checker": "_looks_like_mixed_self_intro_with_location_preference",
            "explicit_signal_checker": "_has_explicit_self_update_signal",
        },
        "education": {
            "partner_context_checker": "_looks_like_partner_preference_education_context",
            "mixed_intro_checker": (
                "_looks_like_mixed_self_intro_with_education_preference",
                "_looks_like_profile_led_self_intro_with_education",
            ),
            "explicit_signal_checker": "_has_explicit_self_update_signal",
        },
        "occupation": {
            "partner_value_checker": "_looks_like_partner_requirement_content",
            "mixed_intro_checker": "_looks_like_mixed_self_intro_with_occupation_preference",
            "explicit_signal_checker": "_has_explicit_self_update_signal",
        },
    }

    # 预编译正则表达式（性能优化）
    _EXTRACT_PATTERN = re.compile(r'<extract>\s*\n?(.*?)\n?</extract>', re.DOTALL)
    _JSON_PATTERN = re.compile(r'```json\s*\n?(.*?)\n?```', re.DOTALL)
    _FIELD_VALUE_PATTERN = re.compile(r'^([^:]+)\s*:\s*(.+)$')
    _AGE_PATTERN = re.compile(r'(\d{1,3})\s*岁')
    _YEAR_SUFFIX_PATTERN = re.compile(r'(\d{2})后')
    _BIRTH_YEAR_PATTERN = re.compile(r'^(19\d{2}|20\d{2})$')
    _EXTRACT_NUMBER_PATTERN = re.compile(r'(\d{1,3})')
    _PLACEHOLDER_VALUES = {
        '值',
        '值null',
        '值/null',
        'value',
        'valuenull',
        'value/null',
        '示例',
        '示例值',
        'xxx',
        'xxxx',
        'xx',
        '待填写',
        '未提及',
        '未提供',
        'unknown',
        'n/a',
        'na',
    }
    _STABLE_PROFILE_FIELDS = {
        "sex",
        "age",
        "location",
        "education",
        "occupation",
        "marital_status",
    }
    _OCCUPATION_ALIASES = {
        "it": "IT",
        "ui": "UI",
        "ui设计": "UI",
        "ui设计师": "UI",
        "hr": "HR",
        "hrbp": "HR",
        "qa": "QA",
        "qa测试工程师": "QA",
        "admin": "行政",
        "行政前台": "行政",
        "行政人事": "行政",
        "人事行政": "行政",
        "产品": "产品",
        "产品经理": "产品",
        "运营": "运营",
        "运营助理": "运营",
        "产品运营": "产品运营",
        "电商运营": "电商运营",
        "设计": "设计",
        "开发": "开发",
        "前端开发": "前端开发",
        "前端工程师": "前端开发",
        "后端开发": "后端开发",
        "后端工程师": "后端开发",
        "程序员": "程序员",
        "销售": "销售",
        "老师": "老师",
        "医生": "医生",
        "护士": "护士",
        "公务员": "公务员",
        "财会": "财务",
        "财务": "财务",
        "外贸": "外贸",
        "外贸行业": "外贸",
        "医护": "医护",
        "美容": "美容",
        "美容师": "美容师",
        "美业": "美业",
        "医美": "医美",
    }
    _EDUCATION_TYPO_ALIASES = {
        "本可": "本科",
        "夲科": "本科",
        "木科": "本科",
        "港本": "本科",
        "硕土": "硕士",
        "港硕": "硕士",
        "海归硕": "硕士",
        "博土": "博士",
        "专科": "大专",
        "研一": "研究生",
        "研二": "研究生",
        "研三": "研究生",
        "在读硕士": "硕士",
        "博后": "博士",
        "博士后": "博士",
        "在读博": "博士",
        "专升本": "本科",
    }
    _OCCUPATION_FALLBACK_CHARS = {"恶", "呃", "额", "嗯", "啊", "哈", "哎"}
    _LOW_QUALITY_GENERIC_TOKENS = {
        "可以",
        "可以啊",
        "可以呀",
        "可以哦",
        "好",
        "好的",
        "好啊",
        "行",
        "行啊",
        "嗯",
        "嗯嗯",
        "哦",
        "哈",
        "是吗",
        "有不",
        "行不",
        "都可以",
        "hi",
        "hello",
        "在吗",
        "在不",
        "想了解下",
        "我先看看",
        "先看看",
        "我问问你情况",
        "问问你情况",
        "坏呼叫",
    }
    _LOW_QUALITY_QUESTION_MARKERS = (
        "机构是吗",
        "资源怎么样",
        "靠谱吗",
        "靠不靠谱",
        "香港有不",
        "有不",
        "行不",
        "怎么样",
        "是吗",
        "吗",
        "?",
        "？",
    )
    _LOW_QUALITY_OCCUPATION_FRAGMENTS = (
        "你好",
        "您好",
        "hi",
        "hello",
        "在吗",
        "在不",
        "想了解下",
        "问问你情况",
        "我先看看",
        "坏呼叫",
        "不要同",
        "别同",
        "最好不要同",
    )
    _VALID_EDUCATION_VALUES = {"博士", "硕士", "研究生", "本科", "大专", "中专", "高中", "没学历"}
    """
    信息提取服务

    职责：
    1. 从 AI 回复中提取 JSON/XML 格式的数据
    2. 处理提取的数据并更新用户档案
    3. 推断用户拒绝的字段
    4. 生成已收集信息的摘要
    """

    # AI 返回的中文字段名到 UserProfile 字段名的映射
    FIELD_MAPPING = {
        "称呼": "last_name",
        "性别": "sex",
        "所在地": "location",
        "年龄": "age",
        "身高": "height",
        "体重": "weight",
        "学历": "education",
        "职业": "occupation",
        "月收入": "monthly_income",
        "收入": "monthly_income",  # AI 可能简写为"收入"
        "婚况": "marital_status",
        "联系方式": "contact",
        "电话": "phone",
        "电话号码": "phone",
        "手机": "phone",
        "手机号": "phone",
        "微信": "wechat",
        "微信号": "wechat",
        "择偶要求": "partner_requirement",
        "择偶": "partner_requirement",
        "要求": "partner_requirement",
        # 英文字段名（直接映射）
        "last_name": "last_name",
        "sex": "sex",
        "location": "location",
        "age": "age",
        "年龄段": "age_label",
        "height": "height",
        "weight": "weight",
        "education": "education",
        "occupation": "occupation",
        "monthly_income": "monthly_income",
        "marital_status": "marital_status",
        "contact": "contact",
        "phone": "phone",
        "wechat": "wechat",
        "partner_requirement": "partner_requirement",
        # 带空格的字段名（AI 可能返回）
        " 职业": "occupation",
        " 学历": "education",
        " 身高": "height",
        " 体重": "weight",
        " 月收入": "monthly_income",
        " 收入": "monthly_income",
        " 婚况": "marital_status",
        " 联系方式": "contact",
        " 电话": "phone",
        " 微信": "wechat",
        " 择偶要求": "partner_requirement",
    }

    # 无效名称列表（这些词不应该被识别为名字）
    INVALID_NAMES = {
        '小姐姐', '小哥哥', '你好呀', '你好呢', '你好', '哈喽', '嗨', '呀', '呢', '哒', '哦', '哈',
        '好的', '嗯嗯', '好的呢', '好呀', '行', '可以', 'ok', '好的哈', '好哒',
        '哈德', '哈哈', '哈哈哈', '呵呵', '嘿嘿', '哇', '咦', '唉', '嗯',
        '什么', '怎么', '为什么', '哪里', '谁', '多少',
    }

    @staticmethod
    def _extract_confirmed_sex_candidate_from_context(text: str) -> Optional[str]:
        content = str(text or "").strip()
        if not content:
            return None
        if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*男(?:生|的|孩子)?", content):
            return "男"
        if re.search(r"(你这边是|你是|我理解你是|你应该是|应该是)\s*女(?:生|的|孩子)?", content):
            return "女"
        return None

    @staticmethod
    def _is_affirmative_confirmation_answer(text: str) -> bool:
        return bool(
            re.search(
                r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
                r"(?:[呀呢啊哦哈啦嘛]*)?"
                r"(?:\s*[，,、 ]\s*)?$",
                str(text or ""),
            )
        )

    # 字段关键词映射（用于推断拒绝的字段）
    FIELD_KEYWORDS = {
        'location': ['所在地', '在哪个城市', '哪个城市', '在哪', '城市'],
        'age': ['年龄', '多大', '几岁', '哪年', '出生'],
        'education': ['学历', '学位'],
        'occupation': ['职业', '工作', '做什么'],
        'height': ['身高'],
        'weight': ['体重'],
        'monthly_income': ['收入', '月薪', '年薪', '工资'],
        'partner_requirement': ['择偶', '要求', '找什么样的', '什么类型的', '喜欢的类型'],
    }

    def __init__(self, user_service: UserService):
        """
        初始化提取服务

        Args:
            user_service: 用户服务
        """
        self.user_service = user_service

    @staticmethod
    def _message_looks_like_contact_attempt(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if re.fullmatch(r"(?:\+?86)?[\d-]{7,17}", compact):
            return True
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{5,19}", compact):
            return True
        return bool(re.search(r"(电话|手机|手机号|号码|微信|vx|wx|weixin)", text, re.IGNORECASE))

    @staticmethod
    def _message_has_explicit_age_semantics(user_message: str) -> bool:
        return bool(re.search(r"(岁|年龄|今年|出生|哪年|90后|95后|85后)", str(user_message or "")))

    @staticmethod
    def _looks_like_income_context_message(user_message: str) -> bool:
        return bool(re.search(r"(月薪|月[收搜]入|[收搜]入|工资|年薪|年[收搜]入|税前|税后|年包)", str(user_message or "")))

    @staticmethod
    def _looks_like_partner_preference_income_context(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        return bool(
            re.search(
                r"(?:找|想找|喜欢|偏向|偏好|希望|就想找|更想找).{0,10}(?:月入|月薪|收入|工资|年薪|年收入)"
                r"|(?:月入|月薪|收入|工资|年薪|年收入).{0,8}(?:的男生|的女生|的对象|的另一半|就行|以上的)",
                compact,
            )
        )

    @classmethod
    def _has_explicit_self_income_signal(cls, user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        return bool(
            re.search(
                r"(?:我|自己|本人)(?:现在|目前)?(?:的)?(?:月入|月薪|收入|工资|年薪|年收入|年包)"
                r"|(?:我|自己|本人).{0,8}(?:月入|月薪|收入|工资|年薪|年收入|年包)",
                compact,
            )
        )

    @classmethod
    def _looks_like_mixed_self_intro_with_income_preference(cls, user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        has_self_income = cls._has_explicit_self_income_signal(text)
        has_preference_income = cls._looks_like_partner_preference_income_context(text)
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|未婚|离异|已婚|单身|本科|大专|硕士|博士|南山|深圳|广州|杭州|上海|北京)", text)
        )
        return has_self_income and has_preference_income and has_self_profile_payload

    @staticmethod
    def _looks_like_partner_requirement_correction_message(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        return bool(
            re.search(r"(我的意思是|我意思是|你理解反了|理解反了|不是.+是.+|不是这个意思|说反了|搞反了|更正一下)", text)
        )

    @staticmethod
    def _looks_like_partner_age_range_expression(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        patterns = (
            r"上下\d{1,2}岁",
            r"上下相差\d{1,2}岁",
            r"和我上下相差\d{1,2}岁",
            r"和我相差\d{1,2}岁",
            r"跟我相差\d{1,2}岁",
            r"大我\d{1,2}岁",
            r"小我\d{1,2}岁",
            r"比我大\d{1,2}岁",
            r"比我小\d{1,2}岁",
            r"差(?:个|不多)?\d{1,2}岁",
            r"年龄差.{0,4}\d{1,2}岁",
            r"同龄",
            r"差不多大",
            r"\d{2}年到\d{2}年之间",
            r"\d{2}后到\d{2}后",
        )
        return any(re.search(pattern, compact) for pattern in patterns)

    def analyze_numeric_semantics(self, user_message: str) -> Dict[str, Any]:
        text = str(user_message or "").strip()
        compact = re.sub(r"\s+", "", text)
        analysis: Dict[str, Any] = {
            "self_age_candidates": [],
            "birth_year_candidates": [],
            "partner_age_gap_candidates": [],
            "partner_age_range_candidates": [],
            "income_candidates": [],
            "height_candidates": [],
            "weight_candidates": [],
            "contact_candidates": [],
            "other_numeric_candidates": [],
            "has_multiple_numeric_roles": False,
            "has_multiple_age_roles": False,
        }
        if not compact:
            return analysis

        self_age_candidates: list[int] = []
        birth_year_candidates: list[int] = []
        partner_age_gap_candidates: list[int] = []
        partner_age_range_candidates: list[int] = []
        income_candidates: list[str] = []
        height_candidates: list[str] = []
        weight_candidates: list[str] = []
        contact_candidates: list[str] = []

        def _append_unique(target: list[int], value: Optional[int]) -> None:
            if value is None:
                return
            if value not in target:
                target.append(value)

        def _append_unique_text(target: list[str], value: Optional[str]) -> None:
            normalized = str(value or "").strip()
            if not normalized:
                return
            if normalized not in target:
                target.append(normalized)

        for pattern in (
            r"我(?:今年|现在)?(?:是|有|都)?(\d{1,4})(?:岁)?",
            r"本人(?:今年|现在)?(?:是|有|都)?(\d{1,4})(?:岁)?",
            r"今年(\d{1,4})(?:岁)?",
            r"年龄(?:是|有)?(\d{1,4})(?:岁)?",
        ):
            for match in re.finditer(pattern, compact):
                _append_unique(self_age_candidates, int(match.group(1)))

        for match in re.finditer(r"(19\d{2}|20\d{2})年(?:出生)?", compact):
            candidate = self._parse_age(match.group(0))
            _append_unique(birth_year_candidates, candidate)
        for match in re.finditer(r"(?<!\d)(\d{2})年(?:的)?(?:出生)?", compact):
            candidate = self._parse_age(match.group(0))
            _append_unique(birth_year_candidates, candidate)

        for pattern in (
            r"上下(?:相差)?(\d{1,2})岁",
            r"(?:和我|跟我|同我|与我)相差(\d{1,2})岁",
            r"(?:和我|跟我|同我|与我)差(?:个|不多)?(\d{1,2})岁",
            r"大我(\d{1,2})岁",
            r"小我(\d{1,2})岁",
            r"比我大(\d{1,2})岁",
            r"比我小(\d{1,2})岁",
            r"年龄差.{0,4}(\d{1,2})岁",
            r"差(?:个|不多)?(\d{1,2})岁",
            r"(\d{1,2})岁(?:内|左右)",
        ):
            for match in re.finditer(pattern, compact):
                _append_unique(partner_age_gap_candidates, int(match.group(1)))

        for match in re.finditer(r"(\d{1,2})到(\d{1,2})岁", compact):
            low = int(match.group(1))
            high = int(match.group(2))
            if 18 <= low <= 100 and 18 <= high <= 100:
                _append_unique(partner_age_range_candidates, low)
                _append_unique(partner_age_range_candidates, high)

        for pattern in (
            r"((?:月薪|月收入|工资|收入|到手|年薪|年收入|年包|一年|每年|大概收入|收入区间)"
            r"(?:大概|差不多|有|在)?\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)\s*(?:-|~|到|至|—|–)\s*"
            r"\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)(?:左右|上下|出头|\+)?)",
            r"((?:\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)\s*(?:-|~|到|至|—|–)\s*"
            r"\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元))(?:一个月|每月|月薪|月收入|工资|收入|到手|年薪|年收入|年包|一年|每年)?)",
            r"((?:年薪|年收入|年包|一年|每年)(?:税前|税后)?(?:大概|差不多|有|在)?\d+(?:\.\d+)?\s*"
            r"(?:-|~|到|至|—|–)\s*\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)?(?:左右|上下|出头|\+)?)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)\s*(?:-|~|到|至|—|–)\s*"
            r"(?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)(?:左右|上下|出头)?)",
            r"(?:月薪|月收入|工资|收入|到手|年薪)(?:大概|差不多|有|在)?(\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元))",
            r"(\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元))(?:一个月|每月|月薪|月收入|工资|收入|到手|年薪)",
            r"(?:年薪|年收入|年包)(?:税前|税后)?(?:大概|差不多|有|在)?(\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)?(?:左右|上下|出头|\+)?)",
            r"(?:税前|税后)(?:年薪|年收入)?(?:大概|差不多|有|在)?(\d+(?:\.\d+)?(?:万|千|k|K|w|W|块|元)?(?:左右|上下|出头|\+)?)",
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d)+(?:万|千)(?:左右|上下|出头))",
            r"(?<![a-zA-Z])(\d+(?:\.\d+)?(?:万|千|k|K|w|W)(?:左右|上下|出头|\+)?)(?![a-zA-Z])",
        ):
            for match in re.finditer(pattern, compact):
                _append_unique_text(income_candidates, match.group(1))

        for pattern in (
            r"身高(?:大概|差不多|有|在)?(\d{2,3}(?:cm|CM|厘米|米)?)",
            r"(?<!月薪)(?<!收入)(?<!工资)(?<!年薪)(\d{3})(?:cm|CM|厘米)",
            r"(?<!\d)(1\.\d{2})(?:米)",
        ):
            for match in re.finditer(pattern, compact):
                _append_unique_text(height_candidates, match.group(1))

        for pattern in (
            r"体重(?:大概|差不多|有|在)?(\d{2,3}(?:kg|KG|公斤|斤)?)",
            r"(?<!\d)(\d{2,3})(?:kg|KG|公斤|斤)",
        ):
            for match in re.finditer(pattern, compact):
                _append_unique_text(weight_candidates, match.group(1))

        if self._message_looks_like_contact_attempt(text):
            for match in re.finditer(r"(?<!\d)(?:86)?1[3-9]\d{9}(?!\d)", compact):
                digits = match.group(0)
                if digits.startswith("86") and len(digits) == 13:
                    digits = digits[2:]
                _append_unique_text(contact_candidates, digits)
            for match in re.finditer(r"(?<!\d)[5-9]\d{7}(?!\d)", compact):
                _append_unique_text(contact_candidates, match.group(0))
            wechat_like = re.sub(r"^(?:微信号?|weixin|vx|wx)[:：]?", "", compact, flags=re.IGNORECASE)
            if re.fullmatch(r"(?i)[a-z][a-z0-9_-]{5,19}", wechat_like):
                _append_unique_text(contact_candidates, wechat_like)

        analysis["self_age_candidates"] = self_age_candidates
        analysis["birth_year_candidates"] = birth_year_candidates
        analysis["partner_age_gap_candidates"] = partner_age_gap_candidates
        analysis["partner_age_range_candidates"] = partner_age_range_candidates
        analysis["income_candidates"] = income_candidates
        analysis["height_candidates"] = height_candidates
        analysis["weight_candidates"] = weight_candidates
        analysis["contact_candidates"] = contact_candidates

        age_roles = [
            bool(self_age_candidates or birth_year_candidates),
            bool(partner_age_gap_candidates),
            bool(partner_age_range_candidates),
        ]
        numeric_roles = [
            *age_roles,
            bool(income_candidates),
            bool(height_candidates),
            bool(weight_candidates),
            bool(contact_candidates),
        ]
        analysis["has_multiple_age_roles"] = sum(1 for item in age_roles if item) >= 2
        analysis["has_multiple_numeric_roles"] = sum(1 for item in numeric_roles if item) >= 2
        return analysis

    def resolve_stable_self_age(
        self,
        *,
        user_message: str,
        resolved_age: Optional[str] = None,
    ) -> tuple[Optional[int], Dict[str, Any]]:
        analysis = self.analyze_numeric_semantics(user_message)

        parsed_resolved_age = self._parse_age(resolved_age) if resolved_age else None
        if parsed_resolved_age is not None:
            has_explicit_self_age_signal = bool(
                (analysis.get("self_age_candidates") or []) or (analysis.get("birth_year_candidates") or [])
            )
            has_competing_numeric_roles = any(
                bool(analysis.get(key))
                for key in (
                    "partner_age_gap_candidates",
                    "partner_age_range_candidates",
                    "income_candidates",
                    "height_candidates",
                    "weight_candidates",
                    "contact_candidates",
                )
            )
            if has_explicit_self_age_signal or not has_competing_numeric_roles:
                return parsed_resolved_age, analysis

        self_age_candidates = list(analysis.get("self_age_candidates") or [])
        if len(self_age_candidates) == 1:
            return self_age_candidates[0], analysis

        birth_year_candidates = list(analysis.get("birth_year_candidates") or [])
        if len(birth_year_candidates) == 1:
            return birth_year_candidates[0], analysis

        return None, analysis

    def should_accept_numeric_field(
        self,
        *,
        mapped_field: str,
        user_message: str,
        value: Any,
    ) -> bool:
        numeric_fields = {"age", "height", "weight", "monthly_income", "phone", "wechat"}
        if mapped_field not in numeric_fields:
            return True

        analysis = self.analyze_numeric_semantics(user_message)
        value_text = str(value or "").strip()

        if mapped_field == "age":
            stable_self_age, _ = self.resolve_stable_self_age(
                user_message=user_message,
                resolved_age=value_text or None,
            )
            if stable_self_age is not None:
                return True
            competing = any(
                bool(analysis.get(key))
                for key in ("partner_age_gap_candidates", "partner_age_range_candidates", "income_candidates", "height_candidates", "weight_candidates", "contact_candidates")
            )
            return not competing

        if mapped_field == "monthly_income":
            if analysis.get("income_candidates"):
                return True
            competing = any(
                bool(analysis.get(key))
                for key in ("self_age_candidates", "birth_year_candidates", "height_candidates", "weight_candidates", "contact_candidates")
            )
            return not competing

        if mapped_field == "height":
            if analysis.get("height_candidates"):
                return True
            competing = any(
                bool(analysis.get(key))
                for key in ("self_age_candidates", "birth_year_candidates", "income_candidates", "weight_candidates", "contact_candidates")
            )
            return not competing

        if mapped_field == "weight":
            if analysis.get("weight_candidates"):
                return True
            competing = any(
                bool(analysis.get(key))
                for key in ("self_age_candidates", "birth_year_candidates", "income_candidates", "height_candidates", "contact_candidates")
            )
            return not competing

        if mapped_field in {"phone", "wechat"}:
            if analysis.get("contact_candidates"):
                return True
            competing = any(
                bool(analysis.get(key))
                for key in ("self_age_candidates", "birth_year_candidates", "income_candidates", "height_candidates", "weight_candidates")
            )
            return not competing

        return True

    def govern_role_consistent_fields(
        self,
        *,
        extracted_fields: Dict[str, Any],
        user_message: str,
        user_profile: Optional[UserProfile] = None,
        last_response: str = "",
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        governed = dict(extracted_fields or {})
        if not governed:
            return governed
        deterministic_self = self._extract_deterministic_self_field_candidates(user_message)
        extraction_meta = extraction_meta or {}

        active_asked_fields: set[str] = set()
        profile = user_profile
        last_asked_field = str(getattr(profile, "last_asked_field", "") or "").strip() if profile else ""
        last_asked_side_field = str(getattr(profile, "last_asked_side_field", "") or "").strip() if profile else ""
        if last_asked_field:
            active_asked_fields.add(last_asked_field)
        if last_asked_side_field:
            active_asked_fields.add(last_asked_side_field)

        if last_response:
            active_asked_fields |= self._detect_asked_fields_from_context(last_response)

        def _asked(field_name: str) -> bool:
            return field_name in active_asked_fields

        def _scope(field_name: str) -> str:
            return str((extraction_meta.get(field_name, {}) or {}).get("scope") or "").strip() or "mixed"

        def _call_bool_checker(checker_name: str, *args: Any) -> bool:
            checker = getattr(self, checker_name, None)
            if checker is None:
                return False
            return bool(checker(*args))

        def _resolve_mixed_intro(rule: Dict[str, Any]) -> bool:
            mixed_checker = rule.get("mixed_intro_checker")
            if isinstance(mixed_checker, str):
                return _call_bool_checker(mixed_checker, user_message)
            if isinstance(mixed_checker, (tuple, list)):
                return any(_call_bool_checker(checker_name, user_message) for checker_name in mixed_checker)
            return False

        for field_name, rule in self._ROLE_CONSISTENT_FIELD_RULES.items():
            if field_name not in governed:
                continue
            current_value = str(governed.get(field_name) or "").strip()
            deterministic_value = str(deterministic_self.get(field_name) or "").strip()
            explicit_self_field = (
                _asked(field_name)
                or _call_bool_checker(str(rule.get("explicit_signal_checker") or ""), field_name, user_message)
            )
            mixed_self_intro = _resolve_mixed_intro(rule)
            field_scope = _scope(field_name)
            partner_context_checker = str(rule.get("partner_context_checker") or "").strip()
            partner_value_checker = str(rule.get("partner_value_checker") or "").strip()
            partner_signal = False
            if partner_context_checker:
                partner_signal = _call_bool_checker(partner_context_checker, user_message)
            elif partner_value_checker:
                partner_signal = _call_bool_checker(partner_value_checker, governed.get(field_name))

            if field_scope == "partner" and not deterministic_value:
                governed.pop(field_name, None)
                continue

            if deterministic_value:
                if (
                    field_name in {"location", "education"}
                    or not current_value
                    or (
                        partner_signal
                        and not mixed_self_intro
                        and deterministic_value != current_value
                    )
                    or (
                        field_name == "occupation"
                        and self._is_low_quality_self_field_value(
                            field_name,
                            current_value,
                            user_message=user_message,
                            scope=field_scope,
                        )
                    )
                    or field_scope == "partner"
                ):
                    governed[field_name] = deterministic_value
                continue

            if not explicit_self_field and partner_signal and not mixed_self_intro:
                governed.pop(field_name, None)

        if "marital_status" in governed:
            explicit_self_marital = (
                _asked("marital_status")
                or self._has_explicit_self_update_signal("marital_status", user_message)
            )
            mixed_self_intro = self._looks_like_mixed_self_intro_with_marital_preference(user_message)
            if (
                not mixed_self_intro
                and governed.get("partner_requirement")
                and re.search(r"(?:^|[，,、\s])\d{2}(?:年|后)?(?:单身|未婚|离异|已婚)", str(user_message or ""))
            ):
                mixed_self_intro = True
            if (
                not explicit_self_marital
                and self._looks_like_partner_preference_marital_context(user_message)
                and not mixed_self_intro
            ):
                governed.pop("marital_status", None)

        if "monthly_income" in governed:
            explicit_self_income = (
                _asked("monthly_income")
                or self._has_explicit_self_income_signal(user_message)
            )
            mixed_self_intro = self._looks_like_mixed_self_intro_with_income_preference(user_message)
            if (
                not explicit_self_income
                and self._looks_like_partner_preference_income_context(user_message)
                and not mixed_self_intro
            ):
                governed.pop("monthly_income", None)

        if "age" in governed:
            explicit_self_age = _asked("age") or self._has_explicit_self_update_signal("age", user_message)
            analysis = self.analyze_numeric_semantics(user_message)
            has_partner_age_signal = bool(
                analysis.get("partner_age_gap_candidates")
                or analysis.get("partner_age_range_candidates")
            )
            if not has_partner_age_signal:
                preference = self._resolve_partner_requirement_from_message(
                    user_message,
                    allow_legacy_fallback=False,
                ) or ""
                has_partner_age_signal = "年龄" in preference
            if has_partner_age_signal and not explicit_self_age:
                governed.pop("age", None)
                governed.pop("age_label", None)

        return governed

    @classmethod
    def _extract_deterministic_self_field_candidates(cls, user_message: str) -> Dict[str, str]:
        text = str(user_message or "").strip()
        if not text:
            return {}

        extracted: Dict[str, str] = {}
        non_occupation_phrases = {
            "单身", "未婚", "离异", "已婚", "分居", "男", "女", "男生", "女生",
            "深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "香港",
        }
        compact = re.sub(r"[，。！？!?；;、/\\]+", " ", text)
        compact = re.sub(r"\s+", " ", compact).strip()
        tokens = [token.strip() for token in compact.split(" ") if token.strip()]
        marital_tokens = {"单身", "未婚", "离异", "已婚", "分居"}
        education_tokens = {"博士", "硕士", "研究生", "本科", "大专", "中专", "高中"}

        location_match = re.search(
            r"(?:我在|来自|人在|目前在|现在在|住在)\s*(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)",
            text,
        )
        if location_match:
            extracted["location"] = location_match.group(1)
        else:
            for token in tokens:
                if re.fullmatch(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)(?:男生|女生|男的|女的|人|这边)?", token):
                    extracted["location"] = re.sub(r"(男生|女生|男的|女的|人|这边)$", "", token)
                    break

        sex_patterns = (
            ("女", r"(?:^|[，,、\s])(?:女生|女的|女)\s*(?:找|想找|喜欢|偏向|偏好).{0,8}(?:男朋友|男盆友|男生|男性|对象|另一半)"),
            ("男", r"(?:^|[，,、\s])(?:男生|男的|男)\s*(?:找|想找|喜欢|偏向|偏好).{0,8}(?:女朋友|女盆友|女生|女性|对象|另一半)"),
            ("女", r"(?:^|[，,、\s])女找男(?:$|[，,、\s])"),
            ("男", r"(?:^|[，,、\s])男找女(?:$|[，,、\s])"),
        )
        for value, pattern in sex_patterns:
            if re.search(pattern, text):
                extracted["sex"] = value
                break

        linked_education = cls._extract_linked_self_partner_education_value(text)
        if cls._has_explicit_self_update_signal("education", text) or cls._looks_like_profile_led_self_intro_with_education(text):
            edu_match = re.search(r"(本科|大专|硕士|博士|研究生)", text)
            if edu_match:
                extracted["education"] = edu_match.group(1)
        elif linked_education:
            extracted["education"] = linked_education

        marital_match = re.search(r"(单身|未婚|离异|已婚|分居|离过婚|离过|已经离婚)", text)
        if marital_match:
            marital_value = marital_match.group(1)
            extracted["marital_status"] = "离异" if marital_value in {"离过婚", "离过", "已经离婚"} else marital_value

        self_tokens, _ = cls._split_compact_intro_tokens(text)
        for token in self_tokens:
            normalized = cls._normalize_occupation_value(token)
            if (
                normalized
                and normalized not in non_occupation_phrases
                and not re.fullmatch(r"\d{2,4}", str(token or "").strip())
                and re.fullmatch(r"[\u4e00-\u9fffA-Za-z]{2,8}", str(token or "").strip())
                and not cls._is_low_quality_self_field_value("occupation", normalized, user_message=text)
            ):
                extracted["occupation"] = normalized
                break

        if "occupation" not in extracted:
            for token in tokens:
                candidate = str(token or "").strip()
                if not candidate or candidate in marital_tokens or candidate in education_tokens:
                    continue
                normalized = cls._normalize_occupation_value(candidate)
                if (
                    normalized
                    and normalized not in non_occupation_phrases
                    and not re.fullmatch(r"\d{2,4}", candidate)
                    and re.fullmatch(r"[\u4e00-\u9fffA-Za-z]{2,8}", re.sub(r"(单身|未婚|离异|已婚|分居)+$", "", candidate))
                    and not cls._is_low_quality_self_field_value("occupation", normalized, user_message=text)
                ):
                    extracted["occupation"] = normalized
                    break

        return extracted

    @staticmethod
    def _detect_asked_fields_from_context(response: str) -> set[str]:
        text = str(response or "").strip().lower()
        if not text:
            return set()

        asked_fields: set[str] = set()
        pattern_map = {
            "sex": (r"男生还是女生", r"男的还是女的", r"性别"),
            "age": (r"多大", r"几岁", r"年龄", r"出生"),
            "location": (r"哪个城市", r"什么城市", r"在哪个城市", r"常住", r"在哪边", r"哪里生活"),
            "education": (r"学历", r"什么学历", r"最高学历", r"毕业"),
            "occupation": (r"做什么工作", r"做哪方面", r"什么工作", r"职业", r"做哪行"),
            "marital_status": (r"感情状态", r"婚况", r"单身状态", r"单身吗"),
            "monthly_income": (r"月收入", r"月薪", r"收入", r"工资"),
            "partner_requirement": (r"另一半", r"择偶", r"看重哪", r"更看重", r"有什么要求", r"想找个什么样"),
        }
        for field, patterns in pattern_map.items():
            if any(re.search(pattern, text) for pattern in patterns):
                asked_fields.add(field)
        return asked_fields

    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        从 AI 回复中提取 JSON 数据

        支持两种格式：
        1. <extract>...</extract> XML 标签格式（推荐）
        2. ```json...``` 代码块格式

        Args:
            response: AI 回复文本

        Returns:
            Dict[str, Any]: 提取的数据
        """
        if not response:
            return {}

        # 调试：显示 AI 原始回复（限制长度）
        # 简化日志：只记录回复长度和前50字符
        logger.debug(f"[AI回复] 长度={len(response)}, 摘要={response[:50]}...")

        # 1. 优先匹配 <extract>...</extract> XML 标签格式
        match = self._EXTRACT_PATTERN.search(response)
        if match:
            content = match.group(1).strip()
            # 调试：显示原始内容（限制长度）
            logger.debug(f"[提取原始] 长度={len(content)}")
            extracted = self._parse_extract_content(content)
            if extracted:
                # 简化日志：只显示提取到的非空字段
                non_empty = {k: v for k, v in extracted.items() if v not in [None, '', 'null']}
                logger.debug(f"[提取] 字段数={len(non_empty)}")
                return extracted
        else:
            logger.warning(f"[提取失败] AI 回复中没有找到 <extract> 标签！")

        # 2. 尝试匹配 ```json...``` 代码块格式
        match = self._JSON_PATTERN.search(response)
        if match:
            import json
            try:
                data = json.loads(match.group(1).strip())
                non_empty = {k: v for k, v in data.items() if v not in [None, '', 'null']}
                logger.info(f"[提取JSON] {non_empty}")
                return data
            except json.JSONDecodeError:
                logger.warning("```json 代码块解析失败")

        return {}

    def _parse_extract_content(self, content: str) -> Dict[str, Any]:
        """
        解析 <extract> 标签内的内容

        支持：
        - JSON 格式
        - field:value 格式（多行或单行空格分隔）

        Args:
            content: 提取标签内的内容

        Returns:
            Dict[str, Any]: 解析后的数据
        """
        import json

        # 尝试 JSON 解析
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # 尝试 field:value 格式解析
        result = {}
        # 支持 /n 和 \n 作为分隔符
        content = content.replace('/n', ' ').replace('\n', ' ')
        # 用空格分割各个字段
        parts = content.split()
        for part in parts:
            part = part.strip()
            if not part or part.startswith('#'):
                continue

            # 匹配 field:value 格式
            match = self._FIELD_VALUE_PATTERN.match(part)
            if match:
                field, value = match.groups()
                # 清理值中的引号
                value = value.strip().strip('"')
                # 如果值是 "null"，转换为 None
                if value == 'null':
                    value = None
                result[field] = value

        return result

    @classmethod
    def _normalize_extracted_value(cls, value: Any) -> Any:
        """清理模型误抄的占位词，避免把模板内容写入档案。"""
        if value is None:
            return None

        value_str = str(value).strip().strip('"').strip("'")
        if not value_str:
            return None

        lower_value = value_str.lower()
        if lower_value == 'null' or lower_value.startswith('null（') or lower_value.startswith('null('):
            return None

        if lower_value in cls._PLACEHOLDER_VALUES:
            return None

        # 检测"值"开头的各种占位符变体（如：值null、值/null、值xxx等）
        if lower_value.startswith('值') and len(value_str) <= 10:
            # 如果是"值"开头且长度很短，很可能是占位符
            return None

        # 检测"value"开头的各种占位符变体（如：valuenull、value/xxx等）
        if lower_value.startswith('value') and len(value_str) <= 12:
            return None

        return value_str

    @classmethod
    def _normalize_occupation_value(cls, value: Any) -> Any:
        value_str = cls._normalize_extracted_value(value)
        if value_str is None:
            return None
        text = re.sub(r"[，,、。！？!?~～\s]+", "", str(value_str))
        text = re.sub(r"^(?:我|自己|本人)(?:也是|是)?", "", text)
        text = re.sub(r"^(?:目前|现在)?是[a-z]?(?:在)?做(?:的是)?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(单身|未婚|离异|已婚|分居)+$", "", text)
        text = re.sub(r"(吧|呀|呢|哈|哦|啊)+$", "", text)
        text = re.sub(r"^(做|做的|做的是|我是|从事|搞|干)\s*", "", text)
        text = re.sub(r"(工作|上班)$", "", text)
        text = re.sub(r"(测试)$", "", text)
        normalized = text.lower()
        if normalized in cls._OCCUPATION_ALIASES:
            return cls._OCCUPATION_ALIASES[normalized]
        simplified = re.sub(r"(相关|方向|行业|这块|这行|的)$", "", text)
        simplified_normalized = simplified.lower()
        if simplified_normalized in cls._OCCUPATION_ALIASES:
            return cls._OCCUPATION_ALIASES[simplified_normalized]
        if text and text[0] in cls._OCCUPATION_FALLBACK_CHARS and len(text) >= 2:
            trimmed = text[1:]
            trimmed_normalized = trimmed.lower()
            if trimmed_normalized in cls._OCCUPATION_ALIASES:
                return cls._OCCUPATION_ALIASES[trimmed_normalized]
            for stem in ("美容师", "美业", "医美", "美容", "程序员", "销售", "老师", "医生", "护士", "公务员", "产品", "运营", "设计", "开发"):
                if stem in trimmed:
                    residue = trimmed.replace(stem, "")
                    if not residue or set(residue) <= cls._OCCUPATION_FALLBACK_CHARS:
                        return stem
        if simplified in cls._OCCUPATION_ALIASES.values():
            return simplified
        return cls._OCCUPATION_ALIASES.get(normalized, text)

    @staticmethod
    def _is_effectively_same_value(current_value: Any, new_value: Any) -> bool:
        """宽松等价比较，避免仅因格式差异触发重写。"""
        current = "" if current_value is None else str(current_value).strip()
        new = "" if new_value is None else str(new_value).strip()
        if not current and not new:
            return True
        return current == new

    @staticmethod
    def _compact_text(value: Any) -> str:
        return re.sub(r"[，,、。！？!?~～\s]+", "", str(value or "")).strip()

    @classmethod
    def _normalize_education_value(cls, value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        if text in {"没有学历", "无学历"}:
            return "没学历"
        if text in cls._VALID_EDUCATION_VALUES:
            return text
        if text in cls._EDUCATION_TYPO_ALIASES:
            return cls._EDUCATION_TYPO_ALIASES[text]
        match = re.fullmatch(r"(博士|硕士|研究生|本科|大专|中专|高中)(?:毕业|在读|毕业的)?", text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_income_unit_clarification(user_message: Any) -> Optional[str]:
        text = str(user_message or "").strip()
        if not text:
            return None
        compact = re.sub(r"[，,、。！？!?~～\s]+", "", text)
        if not compact:
            return None
        if re.fullmatch(r"(?:是|按)?(?:税前|税后)?(?:年薪|年收入|年包)(?:呢|呀|啊|哦|哈|啦|算|的)?", compact):
            return "年薪"
        if re.fullmatch(r"(?:是|按)?(?:税前|税后)?(?:月薪|月收入|月入|收入|工资)(?:呢|呀|啊|哦|哈|啦|算|的)?", compact):
            return "月薪"
        return None

    @classmethod
    def _merge_income_value_and_unit(cls, current_value: Any, new_value: Any) -> Optional[str]:
        current = re.sub(r"\s+", "", str(current_value or "").strip())
        incoming = re.sub(r"\s+", "", str(new_value or "").strip())
        if not current and not incoming:
            return None

        normalized_unit = cls._extract_income_unit_clarification(incoming) or incoming
        if normalized_unit not in {"年薪", "月薪"}:
            return incoming or current or None
        if not current:
            return normalized_unit
        if normalized_unit in current:
            return current

        tax_prefix_match = re.match(r"^(税前|税后)", current)
        tax_prefix = tax_prefix_match.group(1) if tax_prefix_match else ""
        amount = re.sub(r"^(税前|税后)", "", current)
        amount = re.sub(r"^(年薪|年收入|年包|月薪|月收入|月入|收入|工资)", "", amount)
        amount = amount.strip()
        if not amount:
            return f"{tax_prefix}{normalized_unit}"
        return f"{tax_prefix}{normalized_unit}{amount}"

    @classmethod
    def _is_low_quality_self_field_value(
        cls,
        field: str,
        value: Any,
        *,
        user_message: str = "",
        scope: str = "self",
    ) -> bool:
        if field not in {"occupation", "location", "education"}:
            return False

        if scope and scope not in {"", "self", "mixed"}:
            return True

        text = str(value or "").strip()
        compact_value = cls._compact_text(text)
        compact_message = cls._compact_text(user_message)
        if not compact_value:
            return True

        if compact_value in cls._LOW_QUALITY_GENERIC_TOKENS:
            return True

        if field == "occupation" and compact_value in {"男", "女", "男生", "女生", "男的", "女的"}:
            return True

        if any(marker in compact_value for marker in cls._LOW_QUALITY_QUESTION_MARKERS):
            return True

        if any(marker in compact_message for marker in cls._LOW_QUALITY_QUESTION_MARKERS):
            if field == "location" and not cls._has_explicit_self_update_signal("location", user_message):
                return True
            if field == "occupation":
                return True

        if len(compact_value) <= 1:
            return True

        if field == "education":
            return cls._normalize_education_value(text) is None

        if field == "location":
            if compact_value in {"香港", "深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州", "南山", "福田", "宝安", "龙岗", "龙华"}:
                return bool(any(marker in compact_message for marker in ("有不", "行不", "怎么样", "是吗")) and not cls._has_explicit_self_update_signal("location", user_message))
            return not bool(
                re.fullmatch(r"[\u4e00-\u9fa5]{2,12}(?:市|省|区|县|州|特别行政区)?", text)
                and not any(marker in compact_value for marker in cls._LOW_QUALITY_QUESTION_MARKERS)
            )

        if field == "occupation":
            normalized = cls._normalize_occupation_value(text)
            if normalized is None:
                return True
            normalized_compact = cls._compact_text(normalized)
            if normalized_compact in cls._LOW_QUALITY_GENERIC_TOKENS or normalized_compact in {"男", "女", "男生", "女生", "男的", "女的"}:
                return True
            if normalized_compact in {"不错", "挺不错", "还不错", "听不错"} or normalized_compact.endswith("不错"):
                return True
            if re.search(r"(怎么|咋|为什么|为啥|啥|什么情况|怎么回事|怎么多了)", normalized_compact):
                return True
            if any(token in normalized_compact for token in ("结婚", "离婚", "离异", "未婚", "单身", "已婚")):
                return True
            if any(token in normalized_compact for token in ("找对象", "找另一半", "找男朋友", "找女朋友", "男生找女朋友", "女生找男朋友", "男朋友", "女朋友", "另一半")):
                return True
            if any(token in normalized_compact for token in ("本科", "大专", "硕士", "博士", "研究生", "学历")):
                return True
            if re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|南京|香港|南山|福田|宝安|龙岗|龙华)", normalized_compact):
                return True
            if any(token in normalized_compact for token in cls._LOW_QUALITY_OCCUPATION_FRAGMENTS):
                return True
            if any(token in normalized_compact for token in ("一个人", "单着", "活不下去", "活不下去了")):
                return True
            if normalized_compact.startswith(("姓", "我叫", "叫我")):
                return True
            if normalized_compact.startswith(("不是", "先", "想找", "找", "我想", "暂时")):
                return True
            return False

        return False

    @classmethod
    def _is_high_quality_field_value(
        cls,
        field: str,
        value: Any,
        *,
        user_message: str = "",
        scope: str = "self",
    ) -> bool:
        if field in {"occupation", "location", "education"}:
            return not cls._is_low_quality_self_field_value(
                field,
                value,
                user_message=user_message,
                scope=scope,
            )
        return bool(str(value or "").strip())

    @classmethod
    def _extract_partner_preference_subslots(cls, requirement: Any) -> Dict[str, str]:
        text = str(requirement or "").strip()
        if not text:
            return {}

        compact = re.sub(r"\s+", "", text)
        self_tokens, preference_tokens = cls._split_compact_intro_tokens(text)
        partner_scope_compact = (
            re.sub(r"\s+", "", "".join(preference_tokens))
            if (preference_tokens and any(cls._looks_like_profile_intro_token(token) for token in self_tokens))
            else compact
        )
        extracted: Dict[str, str] = {}

        age_match = re.search(
            r"((?:8|9|0)\d后|(?:19\d{2}|20\d{2}|\d{2}年)|年龄(?:上下\d{1,2}岁|不超过\d{1,2}岁|\d{1,2}左右))",
            partner_scope_compact,
        )
        if age_match:
            extracted["partner_pref_age"] = age_match.group(1)

        location_match = re.search(
            r"(?:同在|同城|本地|优先|最好|希望|偏向|倾向|喜欢).{0,8}(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)"
            r"|"
            r"(?:想找|找).{0,2}(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)"
            r"|"
            r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)(?:优先|都行|都可|也行|也可|最好|本地|同城|发展)",
            partner_scope_compact,
        )
        if location_match:
            extracted["partner_pref_location"] = (
                location_match.group(1)
                or location_match.group(2)
                or location_match.group(3)
            )
        elif re.fullmatch(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)", compact):
            extracted["partner_pref_location"] = compact
        else:
            location_tokens = [
                re.sub(r"\s+", "", str(token or ""))
                for token in re.split(r"[，,、/]+", text)
                if str(token or "").strip()
            ]
            for token in location_tokens:
                short_match = re.fullmatch(
                    r"(?:想找|找)?(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)",
                    token,
                )
                if short_match:
                    extracted["partner_pref_location"] = short_match.group(1)
                    break

        industry_match = re.search(
            r"(同[^，。！？!?]{1,8}体系|同[^，。！？!?]{1,8}行业|程序员|互联网|大厂程序员|医生|老师|教师|护士|公务员|体制内|财务|金融|销售|运营|产品|开发|医疗体系)",
            partner_scope_compact,
        )
        if industry_match:
            extracted["partner_pref_industry"] = industry_match.group(1)

        education_match = re.search(
            r"(学历本科及以上|学历本科以上|学历本科起步|本科及以上|本科以上|本科起步|硕士及以上|硕士以上|大专及以上|大专以上)",
            partner_scope_compact,
        )
        if education_match:
            education_value = education_match.group(1)
            if education_value.startswith("本科"):
                education_value = education_value.replace("本科以上", "本科及以上").replace("本科起步", "本科及以上")
                education_value = f"学历{education_value}"
            elif education_value.startswith("硕士"):
                education_value = education_value.replace("硕士以上", "硕士及以上")
                education_value = f"学历{education_value}"
            elif education_value.startswith("大专"):
                education_value = education_value.replace("大专以上", "大专及以上")
                education_value = f"学历{education_value}"
            extracted["partner_pref_education"] = education_value
        else:
            linked_education = cls._extract_linked_self_partner_education_value(compact)
            if linked_education:
                extracted["partner_pref_education"] = cls._normalize_partner_preference_education_value(linked_education)

        if "本地优先" in compact:
            extracted["partner_pref_locality"] = "本地优先"
        elif "同城优先" in compact or "同城" in compact:
            extracted["partner_pref_locality"] = "同城优先"

        if re.search(r"比(?:自己|我)大|年纪大点|年龄大点", compact):
            extracted["partner_pref_age_relation"] = "比自己大"
        elif re.search(r"比(?:自己|我)小|年纪小点|年龄小点", compact):
            extracted["partner_pref_age_relation"] = "比自己小"

        return extracted

    @classmethod
    def _extract_partner_requirement_raw_surface_from_message(
        cls,
        user_message: str,
        *,
        structured_subslots: Dict[str, str] | None = None,
    ) -> str:
        message = str(user_message or "").strip()
        if not message:
            return ""

        _, preference_tokens = cls._split_compact_intro_tokens(message)
        if not preference_tokens:
            return ""

        normalized_subslots = {
            str(field or "").strip(): str(value or "").strip()
            for field, value in dict(structured_subslots or {}).items()
            if str(field or "").strip() and str(value or "").strip()
        }
        parts: List[str] = []
        for token in preference_tokens:
            raw_part = str(token or "").strip("，,、。！？!?；; ")
            if not raw_part:
                continue
            compact_part = re.sub(r"\s+", "", raw_part)
            if cls._looks_like_contact_or_question_fragment(compact_part):
                continue

            cleaned_part = cls._remove_unspoken_inferred_partner_requirement_content(raw_part, message).strip("，,、。！？!?；; ")
            if not cleaned_part:
                continue
            if cls._is_structured_covered_partner_requirement_fragment(cleaned_part, normalized_subslots):
                continue
            if cleaned_part not in parts:
                parts.append(cleaned_part)

        return "，".join(parts)

    @classmethod
    def _is_structured_covered_partner_requirement_fragment(
        cls,
        fragment: str,
        structured_subslots: Dict[str, str] | None,
    ) -> bool:
        text = str(fragment or "").strip()
        if not text:
            return True
        subslots = dict(structured_subslots or {})
        if not subslots:
            return False

        location_value = str(subslots.get("partner_pref_location") or "").strip()
        if location_value and text == location_value:
            return True

        industry_value = str(subslots.get("partner_pref_industry") or "").strip()
        if industry_value and text == industry_value:
            return True

        age_value = str(subslots.get("partner_pref_age") or "").strip()
        if age_value and text == age_value:
            return True

        income_value = str(subslots.get("partner_pref_income") or "").strip()
        if income_value and text == income_value:
            return True

        education_value = str(subslots.get("partner_pref_education") or "").strip()
        linked_education = cls._extract_linked_self_partner_education_value(text)
        normalized_linked_education = (
            cls._normalize_partner_preference_education_value(linked_education)
            if linked_education
            else ""
        )
        if education_value and (
            text == education_value
            or normalized_linked_education == education_value
            or cls._normalize_partner_preference_education_value(text) == education_value
        ):
            return True

        return False

    @staticmethod
    def _looks_like_contact_or_question_fragment(value: str) -> bool:
        text = re.sub(r"\s+", "", str(value or "").strip())
        if not text:
            return True
        if re.search(r"1\d{10}", text):
            return True
        if re.search(r"(电话|手机号|联系方式|联系这边|联系我|直接联系|微信|vx|wx|weixin)", text, flags=re.IGNORECASE):
            return True
        if re.search(r"(怎么收费|收费|多少钱|价格|费用|收费吗|先了解下|了解下收费)", text):
            return True
        return False

    @staticmethod
    def _normalize_partner_preference_education_value(value: str) -> str:
        education_value = str(value or "").strip()
        if not education_value:
            return ""
        if education_value.startswith("学历"):
            return education_value
        if education_value in {"本科", "大专", "硕士", "博士", "研究生"}:
            return f"学历{education_value}及以上"
        return education_value

    @staticmethod
    def _extract_linked_self_partner_education_value(message: str) -> Optional[str]:
        text = re.sub(r"\s+", "", str(message or ""))
        if not text:
            return None
        match = re.search(
            r"(?:一样|也|最好也|同样)(本科|大专|硕士|博士|研究生)"
            r"|(?:本科|大专|硕士|博士|研究生)(?:也一样|也行|也可以)",
            text,
        )
        if not match:
            return None
        for group in match.groups():
            if group:
                return group
        return None

    @staticmethod
    def _compose_structured_partner_preference_text(user_profile: Any) -> str:
        parts: list[str] = []
        for field in ExtractionService._PARTNER_PREFERENCE_SUBSLOT_FIELDS:
            value = str(getattr(user_profile, field, "") or "").strip()
            if value and value not in parts:
                parts.append(value)
        return "，".join(parts)

    @classmethod
    def _compose_partner_requirement_from_subslots(
        cls,
        subslots: Dict[str, str],
        raw_requirement: Any,
    ) -> str:
        ordered_parts: list[str] = []
        for field in cls._PARTNER_PREFERENCE_SUBSLOT_FIELDS:
            value = str(subslots.get(field) or "").strip()
            if value and value not in ordered_parts:
                ordered_parts.append(value)

        raw_parts = [
            str(part or "").strip()
            for part in re.split(r"[，,、]+", str(raw_requirement or "").strip())
        ]
        structured_parts = [
            cls._normalize_partner_requirement_part(part) or part
            for part in ordered_parts
            if part
        ]

        for part in raw_parts:
            if not part:
                continue
            normalized_part = cls._normalize_partner_requirement_part(part) or part
            replaced = False
            for index, existing in enumerate(structured_parts):
                if not existing:
                    continue
                if (
                    normalized_part == existing
                    or normalized_part in existing
                    or existing in normalized_part
                ):
                    if len(part) > len(ordered_parts[index]):
                        ordered_parts[index] = part
                        structured_parts[index] = normalized_part
                    replaced = True
                    break
            if not replaced and part not in ordered_parts:
                ordered_parts.append(part)
                structured_parts.append(normalized_part)

        return "，".join(ordered_parts)

    @staticmethod
    def _should_apply_structured_partner_requirement_compose(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if re.search(r"(看中|看重|倾向|偏向|喜欢|气质|身高有要求|未婚|离异|已婚)", compact):
            return False
        return True

    @staticmethod
    def _preferred_partner_requirement_surface(raw_part: str, normalized_part: str) -> str:
        raw_text = str(raw_part or "").strip()
        normalized_text = str(normalized_part or "").strip()
        if not normalized_text:
            return raw_text
        if not raw_text:
            return normalized_text
        if re.search(r"(未婚|离异|已婚|身高有要求|倾向)", raw_text):
            return raw_text
        return normalized_text

    @classmethod
    def _collect_partner_preference_subslots(
        cls,
        extracted_data: Dict[str, Any],
        user_profile: Optional[UserProfile] = None,
    ) -> Dict[str, str]:
        subslots: Dict[str, str] = {}
        for field in cls._PARTNER_PREFERENCE_SUBSLOT_FIELDS:
            value = str(extracted_data.get(field) or "").strip()
            if not value and user_profile is not None:
                value = str(getattr(user_profile, field, "") or "").strip()
            if not value:
                continue
            if field == "partner_pref_education":
                value = cls._normalize_partner_preference_education_value(value)
            subslots[field] = value
        return subslots

    @classmethod
    def _maybe_compose_partner_requirement_from_structured_inputs(
        cls,
        *,
        extracted_data: Dict[str, Any],
        user_profile: UserProfile,
        user_message: str = "",
    ) -> Optional[str]:
        raw_requirement = str(extracted_data.get("partner_requirement") or "").strip()
        current_requirement = str(getattr(user_profile, "partner_requirement", "") or "").strip()
        current_turn_subslots = cls._collect_partner_preference_subslots(extracted_data)
        if not raw_requirement and not current_turn_subslots:
            return None

        merged_subslots = cls._collect_partner_preference_subslots(extracted_data, user_profile=user_profile)
        if not merged_subslots:
            return raw_requirement or None

        if raw_requirement:
            if cls._should_apply_structured_partner_requirement_compose(raw_requirement):
                return cls._compose_partner_requirement_from_subslots(merged_subslots, raw_requirement)
            return raw_requirement

        if user_message:
            raw_surface = cls._extract_partner_requirement_raw_surface_from_message(
                user_message,
                structured_subslots=merged_subslots,
            )
            if raw_surface:
                return cls._compose_partner_requirement_from_subslots(merged_subslots, raw_surface)

        if current_requirement:
            return cls._compose_partner_requirement_from_subslots(merged_subslots, current_requirement)

        return cls._compose_partner_requirement_from_subslots(merged_subslots, "")

    @classmethod
    def _has_explicit_self_update_signal(cls, field: str, user_message: str) -> bool:
        """
        仅在用户明确自述更新时，允许覆盖已收集的稳定字段，降低字段抖动。
        """
        text = str(user_message or "").strip()
        if not text:
            return False

        explicit_patterns = {
            "sex": r"(我是|本人|我)\s*(男生|女生|男的|女的|男|女)",
            "age": r"(我\s*\d{1,3}\s*岁|我是一?个?\d{1,3}岁|出生于|我是\d{2}后|我是\d{4}年)",
            "location": r"(我在|我住在|我现在在|我目前在|我人在|我在.*(工作|生活)|我是.*的)",
            "education": r"((?:我|自己|本人).{0,4}(本科|大专|硕士|博士|研究生)|学历(?:是|为)?\s*(本科|大专|硕士|博士|研究生)|(?:本科|大专|硕士|博士|研究生)(?:毕业|在读|毕业的))",
            "occupation": r"((?:我是|我做|从事|职业是|工作是).{0,10}(?:[A-Za-z]{1,12}|[\u4e00-\u9fa5]{1,12})|我目前是做.{0,10}|我现在是做.{0,10}|目前是做.{0,10}|现在是做.{0,10}|^\s*做\s*[A-Za-z\u4e00-\u9fa5]{1,12}(?:[，,、\s]|$)|^\s*[A-Za-z]{1,12}\s*[，,、\s])",
            "marital_status": r"((我是|目前|现在|我)\s*(单身|未婚|离异|已婚|分居)|离过婚|离过|已经离婚)",
            "monthly_income": r"((?:我|自己|本人).{0,6}(?:月薪|月收入|月入|收入|工资|年薪|年收入|年包)|^(?:是|按)?(?:税前|税后)?(?:年薪|年收入|年包|月薪|月收入|月入|收入|工资)(?:呢|呀|啊|哦|哈|啦|算|的)?$)",
        }
        pattern = explicit_patterns.get(field)
        if field == "education" and any(token in text for token in cls._EDUCATION_TYPO_ALIASES):
            return True
        if field == "monthly_income" and cls._extract_income_unit_clarification(text):
            return True
        return bool(pattern and re.search(pattern, text))

    @classmethod
    def _has_explicit_field_correction_signal(
        cls,
        field: str,
        user_message: str,
        current_value: Any,
        new_value: Any,
    ) -> bool:
        """识别“不是A，是B / 我不在A，在B”这类明确更正，允许覆盖稳定字段。"""
        text = str(user_message or "").strip()
        current = "" if current_value is None else str(current_value).strip()
        new = "" if new_value is None else str(new_value).strip()
        if not text or not current or not new:
            return False
        if cls._is_effectively_same_value(current, new):
            return False

        if field == "location":
            patterns = (
                rf"(不是|不在){re.escape(current)}.*(是|在){re.escape(new)}",
                rf"{re.escape(current)}.*(说错|搞错)",
                rf"(改成|改为).*(?:在)?{re.escape(new)}",
            )
            return any(re.search(pattern, text) for pattern in patterns)

        if field == "marital_status":
            if "离异" in new and any(token in text for token in ("我离异", "我是离异", "离过婚", "已经离婚")):
                return True
            if "单身" in new and any(token in text for token in ("我单身", "我是单身", "现在单身")):
                return True
            patterns = (
                rf"(不是|不算){re.escape(current)}.*{re.escape(new)}",
                rf"{re.escape(current)}.*(说错|搞错)",
            )
            return any(re.search(pattern, text) for pattern in patterns)

        if field in {"education", "occupation"}:
            patterns = (
                rf"(不是|不做){re.escape(current)}.*(是|做){re.escape(new)}",
                rf"{re.escape(current)}.*(说错|搞错)",
            )
            return any(re.search(pattern, text) for pattern in patterns)

        return False

    def _parse_age(self, value) -> Optional[int]:
        """
        从值中解析年龄

        支持：
        - 数字（如 28）
        - "XX岁" 格式（如 28岁）
        - "XX后" 格式（如 90后，计算年龄）
        - 出生年份（如 1990，计算年龄）

        Args:
            value: 年龄值（字符串或数字）

        Returns:
            Optional[int]: 解析后的年龄，失败返回 None
        """
        if value is None:
            return None

        # 如果已经是数字，直接返回
        if isinstance(value, int):
            return value

        value_str = str(value).strip()
        compact_value = re.sub(r"\s+", "", value_str)
        if re.fullmatch(r"(?i)(?:微信|微信号)?(?:vx|wx|weixin)?[a-z][a-z0-9_-]{5,19}", compact_value):
            return None
        if re.search(r"(?i)(?:微信|微信号|vx|wx|weixin)[a-z0-9_-]{4,19}", compact_value):
            return None

        # 1. 尝试匹配 "XX岁" 格式
        match = re.search(r'(\d{1,4})\s*岁', value_str)
        if match:
            return int(match.group(1))

        # 2. 尝试匹配 "XX后" 格式（如 90后 = 1990 年代出生）
        match = re.search(r'(\d{2})后', value_str)
        if match:
            year_suffix = int(match.group(1))
            from datetime import datetime
            current_year = datetime.now().year
            current_year_suffix = current_year % 100
            birth_year = 2000 + year_suffix if year_suffix <= current_year_suffix else 1900 + year_suffix
            return current_year - birth_year

        # 3. 尝试匹配出生年份（支持“1998”“1998年”“89年”“89年的”）
        match = re.search(r'(19\d{2}|20\d{2})年?(?:出生)?', value_str)
        if match:
            birth_year = int(match.group(1))
            from datetime import datetime
            current_year = datetime.now().year
            return current_year - birth_year

        match = re.search(r'(?<!\d)(\d{2})年(?:的)?(?:出生)?', value_str)
        if match:
            year_suffix = int(match.group(1))
            from datetime import datetime
            current_year = datetime.now().year
            current_year_suffix = current_year % 100
            birth_year = 2000 + year_suffix if year_suffix <= current_year_suffix else 1900 + year_suffix
            return current_year - birth_year

        # 4. 尝试提取任意数字
        match = re.search(r'(\d{1,3})', value_str)
        if match:
            age = int(match.group(1))
            # 年龄应该在合理范围内（18-100）
            if 18 <= age <= 100:
                return age

        return None

    @staticmethod
    def _extract_age_label(value: Any) -> Optional[str]:
        """保留用户原始年龄表达，便于展示和回归校验。"""
        if value is None:
            return None

        value_str = str(value).strip()
        if not value_str:
            return None

        match = re.search(r'(\d{2})后', value_str)
        if match:
            return f"{match.group(1)}后"

        match = re.search(r'((?:19\d{2}|20\d{2})年|(?:\d{2})年(?:的)?)', value_str)
        if match:
            return match.group(1)

        return None

    @classmethod
    def _derive_age_label_from_meta(
        cls,
        *,
        age_value: Any,
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Optional[str]:
        meta = dict(extraction_meta or {})
        explicit_age_label = cls._extract_age_label((meta.get("age_label", {}) or {}).get("source_span"))
        if explicit_age_label:
            return explicit_age_label
        explicit_age_label = cls._extract_age_label((meta.get("age_label", {}) or {}).get("source_text"))
        if explicit_age_label:
            return explicit_age_label
        derived_age_label = str((meta.get("age_label", {}) or {}).get("derived_value") or "").strip()
        if cls._extract_age_label(derived_age_label):
            return cls._extract_age_label(derived_age_label)
        explicit_age_label = cls._extract_age_label((meta.get("age", {}) or {}).get("source_span"))
        if explicit_age_label:
            return explicit_age_label
        return cls._extract_age_label(age_value)

    @staticmethod
    def _extract_partner_requirement_from_user_message(user_message: str) -> Optional[str]:
        """从用户原话中保守提取择偶要求，优先保留否定语义，避免模型反转。"""
        message = str(user_message or "").strip()
        if not message:
            return None
        _, compact_preference_tokens = ExtractionService._split_compact_intro_tokens(message)
        compact_partner_requirement = ExtractionService._extract_compact_partner_requirement_from_tokens(
            compact_preference_tokens
        )
        compact_message = re.sub(r"\s+", "", message)
        has_rich_preference_markers = bool(
            re.search(
                r"(接受\d{1,2}岁上下年龄差|喜欢笑|爱笑|卡身高\d{3}\+|不要同[^，。！？!?]{1,12}行业|"
                r"倾向(?:于)?稳定行业|成熟稳重|三观合拍|同城优先|本地优先|"
                r"看重|稳重|成熟|身高.{0,4}(?:以上|不低于|至少|打底)|多金|有钱|经济条件好|条件好)",
                compact_message,
            )
        )
        if compact_partner_requirement and not has_rich_preference_markers:
            return compact_partner_requirement
        compact_message = re.sub(
            r"(^|[，,])我(?=(温柔|性格好|聊得来|合适|人好|高挑|高一点|同城优先|成熟稳重|三观合拍))",
            r"\1",
            compact_message,
        )

        values_with_pos: List[tuple[int, str]] = []
        values_with_pos.extend(ExtractionService._extract_structured_numeric_partner_preferences(compact_message))
        has_partner_age_bucket_context = bool(
            re.search(r"(看重|都可以|都行|有不|行不|优先|要求|另一半|对象|想找|找|希望|偏向|偏好|喜欢)", compact_message)
        )
        for match in re.finditer(
            r"((?:8|9|0)\d后)(?:(?:都|也)?(?:可以|可|行|成)|左右|都行|都可以|有不|行不)?",
            compact_message,
        ):
            matched = str(match.group(1) or "").strip()
            if matched and has_partner_age_bucket_context:
                values_with_pos.append((match.start(1), matched))
        patterns = [
            r"(深二代)",
            r"(富二代)",
            r"(拆二代)",
            r"(找未婚)",
            r"(未婚找未婚)",
            r"(一样本科)",
            r"(本科起步)",
            r"(本科或者以上)",
            r"(本科及以上)",
            r"(大专或者以上)",
            r"(大专及以上)",
            r"(硕士或者以上)",
            r"(硕士及以上)",
            r"(博士或者以上)",
            r"(博士及以上)",
            r"(程序员最好)",
            r"(大厂程序员)",
            r"(港男)",
            r"(年龄不超过\d{1,2}岁)",
            r"(不超过\d{1,2}岁)",
            r"(\d{1,2}岁以下)",
            r"(接受\d{1,2}岁上下年龄差)",
            r"(能接受\d{1,2}岁上下年龄差)",
            r"(接受上下\d{1,2}岁年龄差)",
            r"(上下\d{1,2}岁)",
            r"((?<!\d)\d{1,2}左右)",
            r"(三十出头)",
            r"(30出头)",
            r"(三十来岁)",
            r"(三十郎当岁)",
            r"(三十上下)",
            r"(三十多点)",
            r"(三十好几)",
            r"(三十冒头)",
            r"(三十左右都可)",
            r"(30上下都行)",
            r"(30来岁也行)",
            r"(30来岁都成)",
            r"(30来岁左右)",
            r"(30来岁上下)",
            r"(30来岁上下都行)",
            r"(30来岁上下都可)",
            r"(30来岁上下都成)",
            r"(30来岁上下也成)",
            r"(30来岁也都行)",
            r"(30来岁也可以)",
            r"(30来岁差不多)",
            r"(30来岁上下差不多)",
            r"(30来岁还行)",
            r"(30来岁还成)",
            r"(30来岁说得过去)",
            r"(30来岁问题不大)",
            r"(30来岁没啥问题)",
            r"(30来岁还过得去)",
            r"(30来岁马马虎虎)",
            r"(30来岁也还行)",
            r"(30来岁不赖)",
            r"(30来岁将就)",
            r"(30来岁还凑合)",
            r"(30来岁也凑合)",
            r"(30左右上下)",
            r"(大我\d{1,2}岁)",
            r"(小我\d{1,2}岁)",
            r"(比我大\d{1,2}岁)",
            r"(比我小\d{1,2}岁)",
            r"(年龄差.{0,4}\d{1,2}岁)",
            r"(\d{2}年到\d{2}年之间)",
            r"(年龄至少\d{1,3})",
            r"(卡身高\d{2,3}\+)",
            r"(身高\d{2,3}\+)",
            r"(身高要\d{2,3}以上)",
            r"(身高至少\d{2,3})",
            r"(身高不低于\d{2,3})",
            r"(不要低于\d{2,3})",
            r"(别低于\d{2,3})",
            r"(不低于\d{2,3})",
            r"(至少\d{2,3})",
            r"(\d{3}往上)",
            r"(一米七五以上)",
            r"(一米七五朝上)",
            r"(一米七五打底)",
            r"(一米七五左右)",
            r"(一米七五上下都行)",
            r"(身高差不多175)",
            r"(身高175左右都成)",
            r"(175左右都可以)",
            r"(175附近)",
            r"(175前后)",
            r"(175上下差不多)",
            r"(175上下都可)",
            r"(175上下都成)",
            r"(175上下都OK)",
            r"(175上下都ok啦)",
            r"(175上下都ok的)",
            r"(175上下也行)",
            r"(175上下都还行)",
            r"(175上下差不太多)",
            r"(175上下大差不差)",
            r"(175上下凑合)",
            r"(175上下过得去)",
            r"(175上下说得过去)",
            r"(175上下没毛病)",
            r"(175上下没啥问题)",
            r"(175上下还过得去)",
            r"(175上下马马虎虎)",
            r"(175上下也还行)",
            r"(175上下不赖)",
            r"(175上下将就)",
            r"(175上下还凑合)",
            r"(175上下也凑合)",
            r"(175差不离)",
            r"(175差不多)",
            r"(175上下)",
            r"(175上下浮动)",
            r"(爱笑)",
            r"(喜欢笑)",
            r"(月入别太低)",
            r"(收入别太低)",
            r"(收入别太拉垮)",
            r"(收入别太低就行)",
            r"(收入过得去就行)",
            r"(收入差不多就行)",
            r"(收入别太寒碜)",
            r"(收入别太难看)",
            r"(收入看得过去就行)",
            r"(收入说得过去就行)",
            r"(收入能看就行)",
            r"(收入过得去就成)",
            r"(收入过得去就好)",
            r"(收入说得过去就好)",
            r"(收入别太说不过去)",
            r"(收入别太拿不出手)",
            r"(收入别太掉价)",
            r"(收入别太上不了台面)",
            r"(收入别太寒酸)",
            r"(收入别太捉襟见肘)",
            r"(收入别太拮据)",
            r"(收入别太紧巴)",
            r"(收入别太磕巴)",
            r"(收入别太寒碜吧)",
            r"(收入别太磕碜吧)",
            r"(收入别太掉面儿)",
            r"(收入别太上不得台面)",
            r"(收入别太寒掺)",
            r"(收入别太没法看)",
            r"(收入别太磕搀)",
            r"(收入别太寒碜着)",
            r"(收入别太跌份)",
            r"(收入别太寒伧)",
            r"(收入差不离就行)",
            r"(收入别太磕碜)",
            r"(收入别太埋汰)",
            r"(收入别太拉胯)",
            r"(收入别太埋汰)",
            r"(不要同[^，。！？!?]{1,12}行业)",
            r"(别同[^，。！？!?]{1,12}行业)",
            r"(最好不要同[^，。！？!?]{1,12}行业)",
            r"(倾向于稳定行业)",
            r"(倾向稳定行业)",
            r"(稳定行业)",
            r"(稳重)",
            r"(成熟)",
            r"(温柔(?:一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?)",
            r"(温柔就行(?:了)?(?:吧|呀|呢)?)",
            r"(性格好就行(?:了)?(?:吧|呀|呢)?)",
            r"(聊得来就行(?:了)?(?:吧|呀|呢)?)",
            r"(合适就行(?:了)?(?:吧|呀|呢)?)",
            r"(人好就行(?:了)?(?:吧|呀|呢)?)",
            r"(气质(?:好|佳)?(?:一点|些)?(?:的)?)",
            r"(漂亮点(?:的)?)",
            r"(长相漂亮)",
            r"(好看点(?:的)?)",
            r"(同城优先)",
            r"(成熟稳重)",
            r"(三观合拍)",
            r"(多金(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(有钱(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(条件好(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(经济条件好(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(收入高(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(收入不错(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(会赚钱(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
            r"(赚钱能力强(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, compact_message):
                matched = match.group(1)
                cleaned = str(matched).strip("，,。；; ")
                if cleaned:
                    values_with_pos.append((match.start(1), cleaned))

        if not values_with_pos:
            return None

        normalized_with_pos: List[tuple[int, str]] = []
        for pos, value in values_with_pos:
            value = re.sub(r"^不超过(\d{1,2})岁$", r"年龄不超过\1岁", value)
            value = re.sub(r"^(\d{1,2})岁以下$", r"年龄不超过\1岁", value)
            value = re.sub(r"^(?:未婚找未婚|找未婚)$", "未婚", value)
            value = re.sub(r"^一样本科$", r"学历本科及以上", value)
            value = re.sub(r"^本科起步$", r"学历本科及以上", value)
            value = re.sub(r"^(本科|大专|硕士|博士)(?:或者|及)以上$", r"学历\1及以上", value)
            value = re.sub(r"^程序员最好$", r"程序员", value)
            value = re.sub(r"^港男$", r"香港", value)
            value = re.sub(r"^(?:接受|能接受)(\d{1,2})岁上下年龄差$", r"年龄上下\1岁", value)
            value = re.sub(r"^接受上下(\d{1,2})岁年龄差$", r"年龄上下\1岁", value)
            structured_numeric_alias = ExtractionService._normalize_structured_numeric_partner_preference_alias(value)
            if structured_numeric_alias:
                value = structured_numeric_alias
            value = re.sub(r"^(\d{1,2})左右$", r"年龄\1左右", value)
            value = re.sub(r"^三十出头$", "年龄30左右", value)
            value = re.sub(r"^30出头$", "年龄30左右", value)
            value = re.sub(r"^三十来岁$", "年龄30左右", value)
            value = re.sub(r"^三十上下$", "年龄30左右", value)
            value = re.sub(r"^三十多点$", "年龄30左右", value)
            value = re.sub(r"^三十郎当岁$", "年龄30左右", value)
            value = re.sub(r"^三十好几$", "年龄30左右", value)
            value = re.sub(r"^三十冒头$", "年龄30左右", value)
            value = re.sub(r"^三十左右都可$", "年龄30左右", value)
            value = re.sub(r"^30上下都行$", "年龄30左右", value)
            value = re.sub(r"^30来岁也行$", "年龄30左右", value)
            value = re.sub(r"^30来岁都成$", "年龄30左右", value)
            value = re.sub(r"^30来岁左右$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下都行$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下都可$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下都成$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下也成$", "年龄30左右", value)
            value = re.sub(r"^30来岁也都行$", "年龄30左右", value)
            value = re.sub(r"^30来岁也可以$", "年龄30左右", value)
            value = re.sub(r"^30来岁差不多$", "年龄30左右", value)
            value = re.sub(r"^30来岁上下差不多$", "年龄30左右", value)
            value = re.sub(r"^30来岁还行$", "年龄30左右", value)
            value = re.sub(r"^30来岁还成$", "年龄30左右", value)
            value = re.sub(r"^30来岁说得过去$", "年龄30左右", value)
            value = re.sub(r"^30来岁问题不大$", "年龄30左右", value)
            value = re.sub(r"^30来岁没啥问题$", "年龄30左右", value)
            value = re.sub(r"^30来岁还过得去$", "年龄30左右", value)
            value = re.sub(r"^30来岁马马虎虎$", "年龄30左右", value)
            value = re.sub(r"^30来岁也还行$", "年龄30左右", value)
            value = re.sub(r"^30来岁不赖$", "年龄30左右", value)
            value = re.sub(r"^30来岁将就$", "年龄30左右", value)
            value = re.sub(r"^30来岁还凑合$", "年龄30左右", value)
            value = re.sub(r"^30来岁也凑合$", "年龄30左右", value)
            value = re.sub(r"^30左右上下$", "年龄30左右", value)
            value = re.sub(r"^至少(\d{2,3})$", r"身高至少\1", value)
            value = re.sub(r"^(?:不要低于|别低于|不低于)(\d{2,3})$", r"身高不低于\1", value)
            value = re.sub(r"^(?:卡身高|身高)(\d{2,3})\+$", r"身高至少\1", value)
            value = re.sub(r"^身高要(\d{2,3})以上$", r"身高\1cm以上", value)
            value = re.sub(r"^(\d{3})往上$", r"身高\1cm以上", value)
            value = re.sub(r"^一米七五以上$", "身高175cm以上", value)
            value = re.sub(r"^一米七五朝上$", "身高175cm以上", value)
            value = re.sub(r"^一米七五打底$", "身高175cm以上", value)
            value = re.sub(r"^一米七五左右$", "身高175cm左右", value)
            value = re.sub(r"^一米七五上下都行$", "身高175cm左右", value)
            value = re.sub(r"^身高差不多175$", "身高175cm左右", value)
            value = re.sub(r"^身高175左右都成$", "身高175cm左右", value)
            value = re.sub(r"^175左右都可以$", "身高175cm左右", value)
            value = re.sub(r"^175附近$", "身高175cm左右", value)
            value = re.sub(r"^175前后$", "身高175cm左右", value)
            value = re.sub(r"^175上下差不多$", "身高175cm左右", value)
            value = re.sub(r"^175上下都可$", "身高175cm左右", value)
            value = re.sub(r"^175上下都成$", "身高175cm左右", value)
            value = re.sub(r"^175上下都OK$", "身高175cm左右", value)
            value = re.sub(r"^175上下都ok啦$", "身高175cm左右", value)
            value = re.sub(r"^175上下都ok的$", "身高175cm左右", value)
            value = re.sub(r"^175上下也行$", "身高175cm左右", value)
            value = re.sub(r"^175上下都还行$", "身高175cm左右", value)
            value = re.sub(r"^175上下差不太多$", "身高175cm左右", value)
            value = re.sub(r"^175上下大差不差$", "身高175cm左右", value)
            value = re.sub(r"^175上下凑合$", "身高175cm左右", value)
            value = re.sub(r"^175上下过得去$", "身高175cm左右", value)
            value = re.sub(r"^175上下说得过去$", "身高175cm左右", value)
            value = re.sub(r"^175上下没毛病$", "身高175cm左右", value)
            value = re.sub(r"^175上下没啥问题$", "身高175cm左右", value)
            value = re.sub(r"^175上下还过得去$", "身高175cm左右", value)
            value = re.sub(r"^175上下马马虎虎$", "身高175cm左右", value)
            value = re.sub(r"^175上下也还行$", "身高175cm左右", value)
            value = re.sub(r"^175上下不赖$", "身高175cm左右", value)
            value = re.sub(r"^175上下将就$", "身高175cm左右", value)
            value = re.sub(r"^175上下还凑合$", "身高175cm左右", value)
            value = re.sub(r"^175上下也凑合$", "身高175cm左右", value)
            value = re.sub(r"^175差不离$", "身高175cm左右", value)
            value = re.sub(r"^175差不多$", "身高175cm左右", value)
            value = re.sub(r"^175上下$", "身高175cm左右", value)
            value = re.sub(r"^175上下浮动$", "身高175cm左右", value)
            value = re.sub(r"^喜欢笑$", "爱笑", value)
            value = re.sub(r"^月入别太低$", "收入别太低", value)
            value = re.sub(r"^收入别太低$", "收入别太低", value)
            value = re.sub(r"^收入别太拉垮$", "收入别太低", value)
            value = re.sub(r"^收入别太低就行$", "收入别太低", value)
            value = re.sub(r"^收入过得去就行$", "收入别太低", value)
            value = re.sub(r"^收入差不多就行$", "收入别太低", value)
            value = re.sub(r"^收入别太寒碜$", "收入别太低", value)
            value = re.sub(r"^收入别太难看$", "收入别太低", value)
            value = re.sub(r"^收入看得过去就行$", "收入别太低", value)
            value = re.sub(r"^收入说得过去就行$", "收入别太低", value)
            value = re.sub(r"^收入能看就行$", "收入别太低", value)
            value = re.sub(r"^收入过得去就成$", "收入别太低", value)
            value = re.sub(r"^收入过得去就好$", "收入别太低", value)
            value = re.sub(r"^收入说得过去就好$", "收入别太低", value)
            value = re.sub(r"^收入别太说不过去$", "收入别太低", value)
            value = re.sub(r"^收入别太拿不出手$", "收入别太低", value)
            value = re.sub(r"^收入别太掉价$", "收入别太低", value)
            value = re.sub(r"^收入别太上不了台面$", "收入别太低", value)
            value = re.sub(r"^收入别太寒酸$", "收入别太低", value)
            value = re.sub(r"^收入别太捉襟见肘$", "收入别太低", value)
            value = re.sub(r"^收入别太拮据$", "收入别太低", value)
            value = re.sub(r"^收入别太紧巴$", "收入别太低", value)
            value = re.sub(r"^收入别太磕巴$", "收入别太低", value)
            value = re.sub(r"^收入别太寒碜吧$", "收入别太低", value)
            value = re.sub(r"^收入别太磕碜吧$", "收入别太低", value)
            value = re.sub(r"^收入别太掉面儿$", "收入别太低", value)
            value = re.sub(r"^收入别太上不得台面$", "收入别太低", value)
            value = re.sub(r"^收入别太寒掺$", "收入别太低", value)
            value = re.sub(r"^收入别太没法看$", "收入别太低", value)
            value = re.sub(r"^收入别太磕搀$", "收入别太低", value)
            value = re.sub(r"^收入别太寒碜着$", "收入别太低", value)
            value = re.sub(r"^收入别太跌份$", "收入别太低", value)
            value = re.sub(r"^收入别太寒伧$", "收入别太低", value)
            value = re.sub(r"^收入差不离就行$", "收入别太低", value)
            value = re.sub(r"^收入别太磕碜$", "收入别太低", value)
            value = re.sub(r"^收入别太埋汰$", "收入别太低", value)
            value = re.sub(r"^收入别太拉胯$", "收入别太低", value)
            value = re.sub(r"^收入别太埋汰$", "收入别太低", value)
            value = re.sub(r"^上下(\d{1,2})岁$", r"年龄上下\1岁", value)
            value = re.sub(r"^大我(\d{1,2})岁$", r"比我大\1岁", value)
            value = re.sub(r"^小我(\d{1,2})岁$", r"比我小\1岁", value)
            value = re.sub(r"(温柔)(一点|点|些)?(?:的)?(?:吧|呀|呢|啊|呗|哈|啦)?$", r"\1", value)
            value = re.sub(r"^(温柔)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(性格好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(聊得来)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(合适)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(人好)就行(?:了)?(?:吧|呀|呢)?$", r"\1", value)
            value = re.sub(r"^(成熟|稳重)$", "成熟稳重", value)
            value = re.sub(r"^(多金)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(有钱)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(条件好)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(经济条件好)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(收入高)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(收入不错)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(会赚钱)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"^(赚钱能力强)(?:一点|些)?(?:最好|优先|就行|就好|吧|呀|咯)?$", r"\1", value)
            value = re.sub(r"(气质)(好|佳)?(一点|些)?(?:的)?$", r"\1", value)
            value = re.sub(r"^(漂亮点)(?:的)?$", r"\1", value)
            value = re.sub(r"^长相漂亮$", r"漂亮点", value)
            value = re.sub(r"^(好看点)(?:的)?$", r"\1", value)
            value = re.sub(r"^(?:最好)?不要同", "不要同", value)
            value = re.sub(r"^别同", "不要同", value)
            value = re.sub(r"^倾向于稳定行业$", r"稳定行业", value)
            value = re.sub(r"^倾向稳定行业$", r"稳定行业", value)
            value = re.sub(r"稳定行业(?:男朋友|女朋友|男生|女生|男孩子|女孩子|男的|女的)$", "稳定行业", value)
            existing_index = next((idx for idx, (_p, existing) in enumerate(normalized_with_pos) if existing == value), None)
            if existing_index is None:
                normalized_with_pos.append((pos, value))
            else:
                existing_pos, existing_value = normalized_with_pos[existing_index]
                if pos < existing_pos:
                    normalized_with_pos[existing_index] = (pos, existing_value)

        preference_match = re.search(
            r"(?:看中|看重|更看重|比较看重|喜欢|偏向|希望).{0,8}(?:对方|另一半)?(.{0,8}气质)",
            message,
        )
        if preference_match:
            preference_value = preference_match.group(1).strip("，,。；; ")
            preference_value = re.sub(r"^(对方|另一半)", "", preference_value)
            preference_value = re.sub(r"(吧|呀|呢|啊)$", "", preference_value).strip()
            if preference_value:
                preference_value = ExtractionService._normalize_partner_requirement_part(preference_value)
                existing_index = next((idx for idx, (_p, existing) in enumerate(normalized_with_pos) if existing == preference_value), None)
                if existing_index is None:
                    normalized_with_pos.append((len(compact_message), preference_value))

        normalized = [value for _, value in sorted(normalized_with_pos, key=lambda item: item[0])]
        normalized = [
            value
            for value in normalized
            if not re.fullmatch(
                r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好)?(?:男朋友|男盆友|男生|男性|男孩子|男的|男|港男|女朋友|女盆友|女生|女性|女孩子|女的|女|港女)",
                value,
            )
        ]
        normalized = [value for value in normalized if not ExtractionService._is_gender_preference_like_partner_requirement(value)]
        return "，".join(normalized)

    @classmethod
    def _resolve_partner_requirement_from_message(
        cls,
        user_message: str,
        *,
        allow_legacy_fallback: bool = False,
        prefer_structured: bool = True,
    ) -> Optional[str]:
        message = str(user_message or "").strip()
        if not message:
            return None
        if allow_legacy_fallback and not prefer_structured:
            legacy_value = cls._extract_partner_requirement_from_user_message(message)
            if legacy_value:
                return legacy_value
        subslots = cls._extract_partner_preference_subslots(message)
        normalized_subslots = {
            field: str(value or "").strip()
            for field, value in dict(subslots or {}).items()
            if str(value or "").strip()
        }
        if normalized_subslots:
            raw_surface = cls._extract_partner_requirement_raw_surface_from_message(
                message,
                structured_subslots=normalized_subslots,
            )
            if not raw_surface:
                compact = re.sub(r"\s+", "", message)
                if (
                    len(compact) <= 20
                    and re.search(r"(都可以|都行|有不|行不|优先|不要同|别同|稳定行业)", compact)
                ):
                    raw_surface = message
            if not raw_surface and allow_legacy_fallback:
                raw_surface = str(cls._extract_partner_requirement_from_user_message(message) or "").strip()
            return cls._compose_partner_requirement_from_subslots(normalized_subslots, raw_surface)
        if allow_legacy_fallback:
            return cls._extract_partner_requirement_from_user_message(message)
        return None

    @staticmethod
    def _split_compact_intro_tokens(message: str) -> tuple[List[str], List[str]]:
        compact = re.sub(r"[，。！？!?；;、/\\]+", " ", str(message or "").strip())
        compact = re.sub(r"\s+", " ", compact).strip()
        if not compact:
            return [], []

        tokens = [token.strip() for token in compact.split(" ") if token.strip()]
        if not tokens:
            return [], []

        preference_markers = (
            "找",
            "想找",
            "希望",
            "喜欢",
            "偏向",
            "倾向",
            "最好",
            "同城",
            "本地",
            "同在",
            "比自己",
            "比我",
            "大一点",
            "小一点",
        )
        generic_opening_tokens = {
            "找对象",
            "相亲",
            "征婚",
            "女生找男朋友",
            "女生找对象",
            "男生找女朋友",
            "男生找对象",
            "女找男",
            "男找女",
        }
        preference_start = len(tokens)
        for idx, token in enumerate(tokens):
            compact_token = re.sub(r"\s+", "", str(token or "").strip())
            if compact_token in generic_opening_tokens:
                continue
            if any(marker in token for marker in preference_markers):
                preference_start = idx
                break

        return tokens[:preference_start], tokens[preference_start:]

    @staticmethod
    def _looks_like_profile_intro_token(token: str) -> bool:
        text = str(token or "").strip()
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return False
        if re.search(r"(我|本人|自己)", compact):
            return True
        if re.search(r"(未婚|单身|离异|已婚|分居|学历|本科|大专|硕士|博士|研究生|收入|月薪|年薪|工资|月入|年入)", compact):
            return True
        if re.search(r"(教师|老师|医生|程序员|开发|运营|产品|设计|财务|销售|行政|客服|在编)", compact):
            return True
        if re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华|老家|河南人)", compact):
            return True
        if re.search(r"(?<!\d)(1[4-9]\d)\s*/\s*([5-9]\d|1\d{2})(?!\d)", text):
            return True
        return False

    @staticmethod
    def _extract_compact_partner_requirement_from_tokens(tokens: List[str]) -> Optional[str]:
        if not tokens:
            return None

        parts: List[str] = []

        def _append(value: Optional[str]) -> None:
            normalized = str(value or "").strip()
            if not normalized or normalized in parts:
                return
            parts.append(normalized)

        for token in tokens:
            compact = re.sub(r"\s+", "", str(token or "").strip())
            if not compact:
                continue

            same_field_match = re.search(r"同([^，。！？!?]{1,8})(?:体系|行业|圈子)", compact)
            if same_field_match:
                _append(f"同{same_field_match.group(1)}体系")

            same_city_match = re.search(r"同在([^，。！？!?]{1,8})发展", compact)
            if same_city_match:
                _append(f"同在{same_city_match.group(1)}发展")

            if "同城" in compact:
                _append("同城优先")
            if "本地" in compact:
                _append("本地优先")

            if re.search(r"比(?:自己|我)大", compact) or re.search(r"(?:年纪|年龄)大点", compact):
                _append("比自己大")
            if re.search(r"比(?:自己|我)小", compact) or re.search(r"(?:年纪|年龄)小点", compact):
                _append("比自己小")

            partner_age_bucket = re.search(
                r"((?:8|9|0)\d后)(?:(?:都|也)?(?:可以|可|行|成)|左右|都行|都可以)?",
                compact,
            )
            if partner_age_bucket:
                _append(partner_age_bucket.group(1))

        if not parts:
            return None

        def _priority(value: str) -> tuple[int, int]:
            if "同" in value and "体系" in value:
                return (0, parts.index(value))
            if value.startswith("同在") and value.endswith("发展"):
                return (1, parts.index(value))
            if "本地" in value or "同城" in value:
                return (2, parts.index(value))
            if "比自己" in value or "比我" in value or "年纪" in value or "年龄" in value:
                return (3, parts.index(value))
            return (4, parts.index(value))

        parts = sorted(parts, key=_priority)
        return "，".join(parts)

    @staticmethod
    def _extract_structured_numeric_partner_preferences(message: str) -> List[tuple[int, str]]:
        semantics = ExtractionService._extract_structured_numeric_partner_preference_semantics(message)
        return [
            (int(item["pos"]), ExtractionService._render_structured_numeric_partner_preference(item))
            for item in semantics
        ]

    @staticmethod
    def _normalize_structured_numeric_partner_preference_alias(value: str) -> Optional[str]:
        compact = re.sub(r"\s+", "", str(value or "").strip())
        if not compact:
            return None
        semantics = ExtractionService._extract_structured_numeric_partner_preference_semantics(f"想找{compact}")
        if len(semantics) != 1:
            return None
        return ExtractionService._render_structured_numeric_partner_preference(semantics[0]) or None

    @staticmethod
    def _extract_structured_numeric_partner_preference_semantics(message: str) -> List[Dict[str, Any]]:
        text = str(message or "").strip()
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return []
        semantics: List[Dict[str, Any]] = []
        preference_prefix_pattern = r"(找|想找|喜欢|偏向|偏好|希望|就想找|更想找|对象|另一半)"
        has_preference_context = bool(re.search(preference_prefix_pattern, compact))
        optional_preference_tail_pattern = (
            r"(?:的)?(?:(?:都|也)?(?:可以|可|行|成|ok|OK)(?:啦|的)?|就行|就好)?"
        )

        def _normalize_income_amount(raw: str) -> str:
            amount = str(raw or "").strip()
            amount = amount.replace("W", "w")
            if re.fullmatch(r"\d+(?:\.\d+)?w", amount):
                return f"{amount[:-1]}万"
            return amount

        def _append(pos: int, field: str, operator: str, value: str) -> None:
            rendered = ExtractionService._render_structured_numeric_partner_preference(
                {"field": field, "operator": operator, "value": value}
            )
            for existing in semantics:
                if ExtractionService._render_structured_numeric_partner_preference(existing) == rendered:
                    return
            semantics.append({"pos": pos, "field": field, "operator": operator, "value": value})

        def _clause_window_around(match: re.Match[str], *, prefix_len: int = 10, suffix_len: int = 8) -> str:
            prefix = compact[max(0, match.start() - prefix_len):match.start()]
            current_span = compact[match.start():match.end()]
            suffix = compact[match.end():match.end() + suffix_len]
            prefix = re.split(r"[，,、；;。]", prefix)[-1]
            suffix = re.split(r"[，,、；;。]", suffix, maxsplit=1)[0]
            return prefix + current_span + suffix

        def _has_income_semantics_near(match: re.Match[str], *, prefix_len: int = 10, suffix_len: int = 8) -> bool:
            nearby = _clause_window_around(match, prefix_len=prefix_len, suffix_len=suffix_len)
            return bool(re.search(r"(月入|月薪|收入|工资|年薪|年收入|税前|税后|年包|k|K|w|W|万)", nearby))

        colloquial_height_around_pattern = re.compile(
            rf"(?<!\d)(1[5-9]\d)(?:左右|上下|前后|附近|差不多){optional_preference_tail_pattern}"
        )
        for match in colloquial_height_around_pattern.finditer(compact):
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=2)
            if re.search(r"(收入|月入|月薪|工资|年薪|年龄|岁)", nearby):
                continue
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            if re.search(preference_prefix_pattern, prefix) or has_preference_context:
                _append(match.start(), "height", "around", match.group(1))

        colloquial_age_around_zh_pattern = re.compile(
            rf"(三十来岁|三十出头|三十上下|三十左右){optional_preference_tail_pattern}"
        )
        for match in colloquial_age_around_zh_pattern.finditer(compact):
            if has_preference_context:
                _append(match.start(), "age", "around", "30")

        colloquial_income_soft_floor_pattern = re.compile(
            r"(?:月入|收入)(?:别太低|过得去|差不多|说得过去)(?:就行|就好|都行|都可以|都可|也行|也可以)?|收入别太寒碜(?:吧)?"
        )
        for match in colloquial_income_soft_floor_pattern.finditer(compact):
            if has_preference_context:
                _append(match.start(), "income", "not_too_low", "")

        bare_height_lower_bound_pattern = re.compile(
            rf"(?<!\d)(1[5-9]\d)\+{optional_preference_tail_pattern}"
        )
        for match in bare_height_lower_bound_pattern.finditer(compact):
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=6)
            if re.search(r"(收入|月入|月薪|工资|年薪|年龄|岁)", nearby):
                continue
            if re.search(preference_prefix_pattern, prefix):
                _append(match.start(), "height", "lower_bound", match.group(1))

        bare_height_above_pattern = re.compile(
            rf"(?<!\d)(1[5-9]\d)(?:以上|往上){optional_preference_tail_pattern}"
        )
        for match in bare_height_above_pattern.finditer(compact):
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=6)
            if re.search(r"(收入|月入|月薪|工资|年薪|年龄|岁)", nearby):
                continue
            if re.search(preference_prefix_pattern, prefix):
                _append(match.start(), "height", "lower_bound", match.group(1))

        bare_age_lower_bound_pattern = re.compile(
            rf"(?<!\d)([2-5]\d)\+{optional_preference_tail_pattern}"
        )
        for match in bare_age_lower_bound_pattern.finditer(compact):
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=8)
            if re.search(r"(身高|cm|CM|一米)", nearby) or _has_income_semantics_near(match, suffix_len=0):
                continue
            if re.search(preference_prefix_pattern, prefix) or has_preference_context:
                _append(match.start(), "age", "lower_bound", match.group(1))

        bare_age_around_pattern = re.compile(
            rf"(?<!\d)([2-5]\d)左右{optional_preference_tail_pattern}"
        )
        for match in bare_age_around_pattern.finditer(compact):
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=8)
            if re.search(r"(身高|cm|CM|一米)", nearby) or _has_income_semantics_near(match, suffix_len=0):
                continue
            if re.search(preference_prefix_pattern, prefix) or has_preference_context:
                _append(match.start(), "age", "around", match.group(1))

        bare_age_around_range_pattern = re.compile(
            rf"(?<!\d)([2-5]\d)(?:上下|前后){optional_preference_tail_pattern}"
        )
        for match in bare_age_around_range_pattern.finditer(compact):
            prefix = re.split(r"[，,、；;。]", compact[max(0, match.start() - 10):match.start()])[-1]
            nearby = _clause_window_around(match, prefix_len=10, suffix_len=8)
            if re.search(r"(身高|cm|CM|一米)", nearby) or _has_income_semantics_near(match, suffix_len=0):
                continue
            if re.search(preference_prefix_pattern, prefix) or has_preference_context:
                _append(match.start(), "age", "around", match.group(1))

        income_lower_bound_pattern = re.compile(r"(?:月入|收入)(\d+(?:\.\d+)?(?:w|W|万))\+")
        for match in income_lower_bound_pattern.finditer(compact):
            _append(match.start(), "income", "lower_bound", _normalize_income_amount(match.group(1)))

        income_over_ten_thousand_pattern = re.compile(r"(?:月入|收入)过万")
        for match in income_over_ten_thousand_pattern.finditer(compact):
            _append(match.start(), "income", "lower_bound", "1万")

        explicit_height_lower_bound_pattern = re.compile(
            rf"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找)(?:一个|个)?(1[5-9]\d)往上{optional_preference_tail_pattern}"
        )
        for match in explicit_height_lower_bound_pattern.finditer(compact):
            _append(match.start(1), "height", "lower_bound", match.group(1))

        explicit_height_around_pattern = re.compile(
            rf"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找)(?:一个|个)?(1[5-9]\d)(?:左右|上下|前后){optional_preference_tail_pattern}"
        )
        for match in explicit_height_around_pattern.finditer(compact):
            _append(match.start(1), "height", "around", match.group(1))

        explicit_age_around_pattern = re.compile(
            rf"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找)(?:一个|个)?([2-5]\d)左右{optional_preference_tail_pattern}"
        )
        for match in explicit_age_around_pattern.finditer(compact):
            _append(match.start(1), "age", "around", match.group(1))

        explicit_age_around_range_pattern = re.compile(
            rf"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找)(?:一个|个)?([2-5]\d)(?:上下|前后){optional_preference_tail_pattern}"
        )
        for match in explicit_age_around_range_pattern.finditer(compact):
            _append(match.start(1), "age", "around", match.group(1))

        explicit_income_over_ten_thousand_pattern = re.compile(r"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找).{0,8}?(?:月入|收入)过万(?:的)?")
        for match in explicit_income_over_ten_thousand_pattern.finditer(compact):
            _append(match.start(), "income", "lower_bound", "1万")

        explicit_income_lower_bound_pattern = re.compile(r"(?:想找|找|喜欢|偏向|偏好|希望|就想找|更想找).{0,8}?(?:月入|收入)(\d+(?:\.\d+)?(?:w|W|万))以上(?:的)?")
        for match in explicit_income_lower_bound_pattern.finditer(compact):
            _append(match.start(1), "income", "lower_bound", _normalize_income_amount(match.group(1)))

        bare_income_lower_bound_pattern = re.compile(r"(?:月入|收入)(\d+(?:\.\d+)?(?:w|W|万))以上(?:的)?")
        for match in bare_income_lower_bound_pattern.finditer(compact):
            if has_preference_context:
                _append(match.start(1), "income", "lower_bound", _normalize_income_amount(match.group(1)))

        return sorted(semantics, key=lambda item: int(item["pos"]))

    @staticmethod
    def _render_structured_numeric_partner_preference(item: Dict[str, Any]) -> str:
        field = str(item.get("field") or "").strip()
        operator = str(item.get("operator") or "").strip()
        value = str(item.get("value") or "").strip()
        if field == "height" and operator == "lower_bound":
            return f"身高{value}cm以上"
        if field == "height" and operator == "around":
            return f"身高{value}cm左右"
        if field == "age" and operator == "lower_bound":
            return f"年龄{value}以上"
        if field == "age" and operator == "around":
            return f"年龄{value}左右"
        if field == "income" and operator == "lower_bound":
            return f"收入{value}以上"
        if field == "income" and operator == "not_too_low":
            return "收入别太低"
        return ""

    @staticmethod
    def _user_explicitly_mentions_zodiac(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        zodiac_tokens = ("生肖", "属鼠", "属牛", "属虎", "属兔", "属龙", "属蛇", "属马", "属羊", "属猴", "属鸡", "属狗", "属猪")
        return any(token in text for token in zodiac_tokens)

    @classmethod
    def _remove_unspoken_inferred_partner_requirement_content(cls, value: str, user_message: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if not cls._user_explicitly_mentions_zodiac(user_message):
            text = re.sub(r"属(?:鼠|牛|虎|兔|龙|蛇|马|羊|猴|鸡|狗|猪)的?", "", text)
            text = re.sub(r"生肖(?:鼠|牛|虎|兔|龙|蛇|马|羊|猴|鸡|狗|猪)", "", text)
        text = re.sub(r"(?:男朋友|女朋友|男生|女生|男孩子|女孩子|男的|女的)$", "", text)
        text = re.sub(r"(?:对象)$", "", text)
        text = re.sub(r"^(?:找个|找一个|找|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找)", "", text)
        text = re.sub(
            r"\s*(?:暂时就|暂时先这样|先这样|就这些|就这样)(?:\s*(?:吧|哈|啦|了))?(?:\s*(?:怎么多了|怎么又多了|这怎么多了|这咋多了|为啥多了))?\s*$",
            "",
            text,
        )
        text = re.sub(r"\s*(?:怎么多了|怎么又多了|这怎么多了|这咋多了|为啥多了)\s*$", "", text)
        text = re.sub(r"[，,、]+", "，", text).strip("，,、 ")
        return text

    @staticmethod
    def _normalize_partner_requirement_part(part: str) -> str:
        value = str(part or "").strip()
        value = re.sub(r"^(?:看中|看重|更看重|比较看重|喜欢|偏向|希望)(?:对方|另一半)?", "", value)
        value = re.sub(r"^(?:对方|另一半)", "", value)
        value = value.strip("，,。；; ")
        value = re.sub(r"(身高\d{2,3}cm(?:以上|左右)?)(?:的)?(?:男朋友|男盆友|男生|男性|男孩子|男的|男)$", r"\1", value)
        value = re.sub(r"(身高\d{2,3}cm(?:以上|左右)?)(?:的)?(?:女朋友|女盆友|女生|女性|女孩子|女的|女)$", r"\1", value)
        value = re.sub(r"^(?:希望)?匹配", "", value)
        value = re.sub(r"地区的?$", "", value)
        value = re.sub(r"地区$", "", value)
        value = re.sub(r"香港地区(?:的)?(?:对象)?$", "香港", value)
        value = re.sub(r"深圳地区(?:的)?(?:对象)?$", "深圳", value)
        value = re.sub(r"广州地区(?:的)?(?:对象)?$", "广州", value)
        value = re.sub(r"杭州地区(?:的)?(?:对象)?$", "杭州", value)
        value = re.sub(r"上海地区(?:的)?(?:对象)?$", "上海", value)
        value = re.sub(r"北京地区(?:的)?(?:对象)?$", "北京", value)
        if re.fullmatch(r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好)?(?:港男|港女)", value):
            return ""
        if re.fullmatch(r"(港男|港女)", value):
            return "香港"
        wrapped_gender_preference = re.fullmatch(
            r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找)(.+?)(?:的)?"
            r"(?:男朋友|男盆友|男生|男性|男孩子|男的|男|港男|女朋友|女盆友|女生|女性|女孩子|女的|女|港女)",
            value,
        )
        if wrapped_gender_preference:
            inner = str(wrapped_gender_preference.group(1) or "").strip("，,、 ")
            inner = re.sub(r"的$", "", inner).strip()
            if re.fullmatch(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)", inner):
                return inner
            if re.search(r"(未婚|离异|已婚|本科|大专|硕士|博士|学历|身高|年龄|程序员|大厂|稳定行业|深二代|富二代|拆二代)", inner):
                return ""
        if "气质" in value:
            return "气质"
        return value

    @staticmethod
    def _is_gender_preference_like_partner_requirement(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        return bool(
            re.fullmatch(r"(男生|女生|男性|女性|男孩子|女孩子)", text)
            or re.search(r"(找(?:个|一个)?男朋友|找(?:个|一个)?女朋友|找(?:个|一个)?男生|找(?:个|一个)?女生|喜欢男生|喜欢女生)", text)
        )

    @staticmethod
    def _extract_partner_gender_preference(message: str) -> Optional[str]:
        text = str(message or "").strip()
        if not text:
            return None
        if re.search(r"(?:我是|本人|我)\s*(?:男生|女生|男的|女的|男|女)", text):
            return None
        male_preference_pattern = (
            r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找)"
            r"[^，,。！？!?]{0,16}?"
            r"(?:男朋友|男盆友|男生|男孩子|男的|男性|男|港男)"
        )
        if re.search(
            male_preference_pattern,
            text,
        ) or re.search(r"(?:男朋友|男盆友|港男)", text):
            return "男"
        if re.search(
            r"(?:找(?:个|一个)?|想找|喜欢|偏向|偏好|想要|希望|就想找|更想找)"
            r"[^，,。！？!?]{0,16}?"
            r"(?:女朋友|女盆友|女生|女孩子|女的|女性|女|港女)",
            text,
        ) or re.search(r"(?:女朋友|女盆友|港女)", text):
            return "女"
        return None

    @staticmethod
    def _infer_occupation_candidate_from_partner_requirement(value: Any) -> tuple[Optional[str], float, str]:
        text = str(value or "").strip()
        if not text:
            return None, 0.0, ""

        def _clean_candidate(raw: str) -> Optional[str]:
            candidate = str(raw or "").strip()
            candidate = re.sub(r"^(?:做|在做|从事)", "", candidate)
            candidate = re.sub(r"(相关|方向|的)$", "", candidate.strip())
            return candidate or None

        explicit_self_match = re.search(
            r"(?:我自己|我本人|我是|我做|本人做|本人是)\s*([^，,、。！？!?]{1,12})(?:行业|这行|相关)",
            text,
        )
        if explicit_self_match:
            return _clean_candidate(explicit_self_match.group(1)), 0.93, "explicit_self_industry"

        same_industry_match = re.search(r"(?:不要|别|最好不要|尽量不要)\s*(?:和我)?同([^，,、。！？!?]{1,12})行业", text)
        if same_industry_match:
            return _clean_candidate(same_industry_match.group(1)), 0.82, "same_industry_exclusion"

        same_work_match = re.search(
            r"(?:和我一样|跟我一样)\s*(?:做|在)\s*([^，,、。！？!?]{1,12})(?:行业|这行|相关)",
            text,
        )
        if same_work_match:
            return _clean_candidate(same_work_match.group(1)), 0.88, "same_work_alignment"

        fallback_match = re.search(r"同([^，,、。！？!?]{1,12})行业", text)
        if not fallback_match:
            return None, 0.0, ""
        return _clean_candidate(fallback_match.group(1)), 0.66, "industry_context_fallback"

    @classmethod
    def _extract_occupation_inference_candidate_from_partner_requirement(cls, value: Any) -> Optional[str]:
        candidate, _, _ = cls._infer_occupation_candidate_from_partner_requirement(value)
        return candidate

    @staticmethod
    def _should_skip_partner_requirement_part(
        part: str,
        user_message: str,
        extracted_data: Dict[str, Any],
    ) -> bool:
        clean_part = str(part or "").strip()
        if not clean_part:
            return True
        clean_part = ExtractionService._remove_unspoken_inferred_partner_requirement_content(clean_part, user_message)
        if not clean_part:
            return True
        clean_part = ExtractionService._normalize_partner_requirement_part(clean_part)
        if ExtractionService._is_gender_preference_like_partner_requirement(clean_part):
            return True

        education_value = str((extracted_data or {}).get("education") or "").strip()
        looks_like_education = bool(
            re.fullmatch(
                r"(?:本科|大专|硕士|博士|研究生|中专|高中)(?:以上|及以上)?",
                clean_part,
            )
        )
        has_explicit_preference_marker = bool(
            re.search(r"(另一半|对方|择偶|想找|希望|要求|看重)", str(user_message or ""))
        )
        if looks_like_education and education_value and clean_part == education_value and not has_explicit_preference_marker:
            return True

        if (
            re.fullmatch(r"年龄\d{1,2}(?:左右|上下|以上)", clean_part)
            and ExtractionService._looks_like_income_context_message(user_message)
            and not ExtractionService._message_has_explicit_age_semantics(user_message)
        ):
            return True

        return False

    @staticmethod
    def _looks_like_partner_requirement_content(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        return bool(
            re.search(
                r"(对方|另一半|气质|眼缘|感觉|性格|成熟稳重|三观|未婚|离异|本科|大专|硕士|博士|学历|身高|收入|工资|月薪|程序员|大厂|互联网|体制内|同城|深圳|广州|杭州|上海|北京|南山)",
                text,
            )
        )

    @staticmethod
    def _looks_like_mixed_self_intro_with_gender_preference(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        has_self_sex_phrase = bool(
            re.search(r"(?:^|[，,、\s])(男生|女生|男的|女的|男|女)(?:找|想找|喜欢|偏向|偏好)", text)
            or re.search(
                r"(?:^|[，,、\s])(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)?\s*(男生|女生|男的|女的)\s*[，,、]",
                text,
            )
            or re.search(
                r"(男生|女生|男的|女的|男|女).{0,4}(?:找|想找).{0,8}(男朋友|女朋友|男盆友|女盆友|男生|女生|男性|女性)",
                text,
            )
        )
        has_direct_partner_preference = bool(
            re.search(
                r"^(男生|女生|男的|女的|男|女).{0,16}(?:找|想找|喜欢|偏向|偏好).{0,16}(?:\d{3}\+|男朋友|女朋友|男盆友|女盆友|男生|女生|男性|女性|男的|女的)",
                text,
            )
        )
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|未婚|离异|已婚|单身|本科|大专|硕士|博士|互联网|程序员|南山|深圳)", text)
        )
        return has_self_sex_phrase and (has_self_profile_payload or has_direct_partner_preference)

    @staticmethod
    def _looks_like_mixed_self_intro_with_location_preference(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        has_self_location_anchor = bool(
            re.search(
                r"(?:^|[，,、\s])(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)(?:男生|女生|男的|女的|人|这边)",
                text,
            )
            or re.search(r"(?:我在|来自|人在|目前在|现在在|住在)\s*(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", text)
        )
        has_preference_location = bool(
            re.search(
                r"(?:找|想找|喜欢|偏向|更想找).{0,8}(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)",
                text,
            )
        )
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|未婚|离异|已婚|单身|本科|大专|硕士|博士|互联网|程序员)", text)
        )
        return has_self_location_anchor and has_preference_location and has_self_profile_payload

    @staticmethod
    def _looks_like_partner_preference_location_context(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        return bool(
            re.search(
                r"(?:找|想找|喜欢|偏向|更想找|希望).{0,8}(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|南山|福田|宝安|龙岗|龙华)",
                text,
            )
        )

    @staticmethod
    def _looks_like_partner_preference_education_context(message: str) -> bool:
        text = re.sub(r"\s+", "", str(message or ""))
        if not text:
            return False
        return bool(
            re.search(
                r"(?:卡学历|学历要求|本科及以上|本科以上|本科起步|最好本科|一样本科|也本科|最好也本科|"
                r"想找.{0,8}本科|找.{0,8}本科)",
                text,
            )
        )

    @staticmethod
    def _looks_like_profile_led_self_intro_with_education(message: str) -> bool:
        text = str(message or "").strip()
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return False
        has_self_intro = bool(
            re.search(r"(女生|男生|男的|女的)", text)
            and (
                re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁)", text)
                or re.search(r"(未婚|离异|已婚|单身)", text)
                or re.search(r"(自己也是做|自己做|我是做|从事|互联网|程序员|开发|运营|产品|设计)", text)
            )
        )
        has_education = bool(re.search(r"(本科|大专|硕士|博士|研究生)", compact))
        has_strong_preference_education = bool(
            re.search(
                r"(卡学历|学历要求|本科起步|本科及以上|本科以上|本科或者以上|最好本科|"
                r"(?:找|想找|希望|倾向|偏向|要求).{0,8}(?:本科|大专|硕士|博士|研究生))",
                compact,
            )
        )
        return has_self_intro and has_education and not has_strong_preference_education

    @staticmethod
    def _looks_like_mixed_self_intro_with_education_preference(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        has_self_education_anchor = bool(
            re.search(r"(?:我|自己|本人).{0,4}(?:本科|大专|硕士|博士|研究生)", text)
            or re.search(r"(?:本科|大专|硕士|博士|研究生).{0,4}(?:毕业|在读)", text)
        )
        has_preference_education = ExtractionService._looks_like_partner_preference_education_context(text)
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|未婚|离异|已婚|单身|南山|深圳|广州|杭州|上海|北京)", text)
        )
        return has_self_education_anchor and has_preference_education and has_self_profile_payload

    @staticmethod
    def _looks_like_mixed_self_intro_with_occupation_preference(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        has_self_occupation_anchor = bool(
            re.search(r"(?:我|自己|本人).{0,6}(?:也是|也在|从事|做|做着).{0,8}(互联网|程序员|开发|运营|产品|设计|财务|教师|医生)", text)
            or re.search(r"(互联网|程序员|开发|运营|产品|设计|财务|教师|医生).{0,6}(?:的|行业).{0,6}(?:我|自己|本人)", text)
        )
        has_preference_occupation = bool(
            re.search(r"(?:倾向|偏向|更想找|喜欢|希望|最好).{0,10}(大厂程序员|程序员|互联网|体制内|稳定行业|财务行业)", text)
        )
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|未婚|离异|已婚|单身|本科|大专|硕士|博士|南山|深圳|广州|杭州|上海|北京)", text)
        )
        return has_self_occupation_anchor and has_preference_occupation and has_self_profile_payload

    @staticmethod
    def _looks_like_partner_preference_marital_context(message: str) -> bool:
        text = re.sub(r"\s+", "", str(message or ""))
        if not text:
            return False
        return bool(
            re.search(
                r"(?:找|想找|希望|要求|对方|另一半).{0,8}(未婚|单身|离异|已婚)"
                r"|(?:未婚找未婚|找未婚|找单身)",
                text,
            )
        )

    @staticmethod
    def _looks_like_mixed_self_intro_with_marital_preference(message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        has_self_marital_anchor = bool(
            re.search(r"(?:我|自己|本人|现在|目前).{0,6}(单身|未婚|离异|已婚)", text)
            or re.search(r"(?:^|[，,、\s]|就是)\d{2}(?:年|后)?(?:单身|未婚|离异|已婚)", text)
        )
        has_preference_marital = ExtractionService._looks_like_partner_preference_marital_context(text)
        has_self_profile_payload = bool(
            re.search(r"(19\d{2}|20\d{2}|\d{2}年|\d{2}后|\d{1,2}岁|本科|大专|硕士|博士|互联网|程序员|南山|深圳|广州|杭州|上海|北京)", text)
        )
        return has_self_marital_anchor and has_preference_marital and has_self_profile_payload

    def infer_refused_fields(self, last_question: str) -> List[str]:
        """
        根据上一个问题推断用户拒绝的字段

        Args:
            last_question: AI 上一个问题

        Returns:
            List[str]: 拒绝的字段名列表
        """
        if not last_question:
            return []

        question_lower = last_question.lower()
        refused_fields = []

        for field, keywords in self.FIELD_KEYWORDS.items():
            if any(keyword in question_lower for keyword in keywords):
                refused_fields.append(field)

        return refused_fields

    async def process_extracted_data(
        self,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        user_message: str = "",
        last_response: str = "",
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
        turn_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        处理从 AI 回复中提取的数据

        Args:
            account_id: 用户 ID
            user_profile: 用户档案
            extracted_data: 提取的字段数据

        Returns:
            Dict[str, Any]: 收集结果
        """
        collected_fields = []
        collected_field_names: List[str] = []
        invalid_contact_attempt = None
        extraction_meta = extraction_meta or {}

        if not extracted_data:
            return {
                "collected": False,
                "all_fields": []
            }

        linked_education = self._extract_linked_self_partner_education_value(user_message)
        if linked_education:
            if not str(extracted_data.get("education") or "").strip():
                extracted_data["education"] = linked_education
                extraction_meta["education"] = {
                    "scope": "self",
                    "source": "linked_phrase_rule",
                    "source_text": user_message,
                    "source_span": f"一样{linked_education}",
                    "confidence": 0.78,
                    "value": linked_education,
                }
            if not str(extracted_data.get("partner_pref_education") or "").strip():
                normalized_linked_pref = self._normalize_partner_preference_education_value(linked_education)
                extracted_data["partner_pref_education"] = normalized_linked_pref
                extraction_meta["partner_pref_education"] = {
                    "scope": "partner",
                    "source": "linked_phrase_rule",
                    "source_text": user_message,
                    "source_span": f"一样{linked_education}",
                    "confidence": 0.82,
                    "derived_from": "linked_self_partner_education_phrase",
                    "value": normalized_linked_pref,
                }

        partner_requirement_value = str(extracted_data.get("partner_requirement") or "").strip()
        if partner_requirement_value:
            hydrated_partner_subslots = self._extract_partner_preference_subslots(partner_requirement_value)
            if hydrated_partner_subslots:
                partner_meta = dict(extraction_meta.get("partner_requirement", {}) or {})
                partner_scope = str(partner_meta.get("scope", "") or "partner").strip() or "partner"
                partner_source = str(partner_meta.get("source", "") or "derived").strip() or "derived"
                partner_source_text = str(partner_meta.get("source_text", "") or partner_requirement_value).strip() or partner_requirement_value
                partner_source_span = str(partner_meta.get("source_span", "") or partner_requirement_value).strip() or partner_requirement_value
                partner_confidence = float(partner_meta.get("confidence", 0.85) or 0.85)
                for subfield, subvalue in hydrated_partner_subslots.items():
                    clean_subvalue = str(subvalue or "").strip()
                    if not clean_subvalue or str(extracted_data.get(subfield) or "").strip():
                        continue
                    extracted_data[subfield] = clean_subvalue
                    extraction_meta[subfield] = {
                        "scope": "partner" if partner_scope == "partner" else partner_scope,
                        "source": "partner_requirement_subslot_derived",
                        "source_text": partner_source_text,
                        "source_span": partner_source_span,
                        "confidence": partner_confidence,
                        "derived_from": "partner_requirement",
                        "value": clean_subvalue,
                    }

        partner_requirement_from_subslots_only = not partner_requirement_value
        composed_partner_requirement = self._maybe_compose_partner_requirement_from_structured_inputs(
            extracted_data=extracted_data,
            user_profile=user_profile,
            user_message=user_message,
        )
        if composed_partner_requirement:
            extracted_data["partner_requirement"] = composed_partner_requirement
            partner_meta = dict(extraction_meta.get("partner_requirement", {}) or {})
            extraction_meta["partner_requirement"] = {
                **partner_meta,
                "scope": str(partner_meta.get("scope", "") or "partner").strip() or "partner",
                "source": (
                    "partner_requirement_structured_compose"
                    if partner_requirement_from_subslots_only
                    else str(partner_meta.get("source", "") or "").strip()
                )
                or "partner_requirement_structured_compose",
                "source_text": str(partner_meta.get("source_text", "") or user_message or composed_partner_requirement).strip()
                or composed_partner_requirement,
                "source_span": str(partner_meta.get("source_span", "") or composed_partner_requirement).strip()
                or composed_partner_requirement,
                "confidence": float(partner_meta.get("confidence", 0.85) or 0.85),
                "value": composed_partner_requirement,
            }

        # 从用户原始输入提取“可判定为合法/非法”的数字序列，
        # 用于拦截“超长号码被模型截断成11位误收集”问题。
        valid_phone_candidates = set()
        overlong_digit_sequences = []
        contaminated_wechat_tokens = []
        if user_message:
            for seq in re.findall(r'\d{8,}', user_message):
                normalized = seq
                if normalized.startswith("86") and len(normalized) == 13 and normalized[2] == "1":
                    normalized = normalized[2:]
                if re.match(r'^1[3-9]\d{9}$', normalized) or re.match(r'^[5-9]\d{7}$', normalized):
                    valid_phone_candidates.add(normalized)
                elif len(seq) > 11:
                    overlong_digit_sequences.append(seq)

            # 微信脏串保护：字母开头 token 中间出现中文后仍接字母/数字，通常是误输入或拼接脏数据。
            contaminated_wechat_tokens = re.findall(
                r'[a-zA-Z][a-zA-Z0-9_-]{5,19}[\u4e00-\u9fff]+[a-zA-Z0-9_-]+',
                user_message
            )

        # 遍历提取结果，更新用户档案
        for field_name, value in extracted_data.items():
            normalized_value = self._normalize_extracted_value(value)
            if normalized_value is not None:
                # 清理字段名（去除前后空格）
                clean_field_name = field_name.strip()
                # 字段名映射：中文字段名 -> 英文字段名
                mapped_field = self.FIELD_MAPPING.get(clean_field_name, clean_field_name)
                value = normalized_value
                current_value = getattr(user_profile, mapped_field, None)

                if mapped_field == "occupation":
                    value = self._normalize_occupation_value(value)
                    if value is None:
                        logger.debug("[提取保护] occupation 归一化后为空，跳过职业更新")
                        continue
                elif mapped_field == "education":
                    normalized_education = self._normalize_education_value(value)
                    if normalized_education:
                        value = normalized_education

                field_meta = extraction_meta.get(mapped_field, {})
                field_scope = str(field_meta.get("scope", "") or "mixed").strip() or "mixed"

                if mapped_field in self._SELF_PROFILE_FIELDS and field_scope in {"partner", "faq", "contact"}:
                    logger.debug("[提取保护] %s 命中非 self scope=%s，跳过主档写入", mapped_field, field_scope)
                    continue

                if self._is_low_quality_self_field_value(
                    mapped_field,
                    value,
                    user_message=user_message,
                    scope=field_scope,
                ):
                    logger.debug("[提取保护] %s 命中低质量值门禁，跳过主档写入: %s", mapped_field, value)
                    continue

                if not self.should_accept_numeric_field(
                    mapped_field=mapped_field,
                    user_message=user_message,
                    value=value,
                ):
                    logger.debug("[提取保护] 数字语义角色不匹配，跳过 %s 写入: %s", mapped_field, value)
                    continue

                # 兼容 AI 把联系方式统一提取为 contact 的场景：
                # 必须路由到 phone / wechat，保证 phone_collected/wechat_collected 状态一致。
                if mapped_field == "contact":
                    raw_contact = str(value).strip()
                    digits_only = ''.join(c for c in raw_contact if c.isdigit())
                    normalized_phone = digits_only
                    if normalized_phone.startswith("86") and len(normalized_phone) == 13 and normalized_phone[2] == "1":
                        normalized_phone = normalized_phone[2:]

                    if re.match(r'^1[3-9]\d{9}$', normalized_phone) or re.match(r'^[5-9]\d{7}$', normalized_phone):
                        mapped_field = "phone"
                        value = normalized_phone
                    else:
                        wechat_candidate = re.sub(
                            r"^(?:微信号?|weixin|vx|wx)\s*[:：]\s*",
                            "",
                            raw_contact,
                            flags=re.IGNORECASE,
                        ).strip()
                        wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'
                        mobile_like_wechat = ''.join(c for c in wechat_candidate if c.isdigit())
                        if re.match(wechat_pattern, wechat_candidate):
                            mapped_field = "wechat"
                            value = wechat_candidate
                        elif re.match(r'^1[3-9]\d{9}$', mobile_like_wechat) or re.match(r'^[5-9]\d{7}$', mobile_like_wechat):
                            mapped_field = "wechat"
                            value = mobile_like_wechat
                        else:
                            logger.info(f"[联系方式路由] contact 无法识别为电话/微信: {value}")
                            invalid_contact_attempt = raw_contact
                            continue

                # 检查是否为无效值
                if mapped_field == "last_name":
                    # 名字必须是1-4个字符（允许单字姓氏如"李"、"王"）
                    if len(value) < 1 or len(value) > 4:
                        logger.info(f"[名字验证] 长度不符合要求(1-4字符): {value}")
                        continue
                    # 名字不能在无效名称列表中
                    if value in self.INVALID_NAMES:
                        logger.info(f"[名字验证] 在无效名称列表中: {value}")
                        continue
                    # 名字不能全是数字
                    if value.isdigit():
                        logger.info(f"[名字验证] 不能全是数字: {value}")
                        continue

                if mapped_field == "age":
                    # 联系方式上下文或明显联系方式尝试里，不允许年龄字段抢数字串。
                    # 这层是落库前最终保险丝，避免 1879987654 -> age=18。
                    if (
                        self._message_looks_like_contact_attempt(user_message)
                        and not self._message_has_explicit_age_semantics(user_message)
                    ):
                        logger.debug("[提取保护] 联系方式语境命中，跳过 age 写入: %s", value)
                        continue
                    if self._looks_like_partner_age_range_expression(user_message):
                        logger.debug("[提取保护] 择偶年龄范围语境命中，跳过 age 下限短路参与: %s", value)
                        # 这里不跳过 age 正常落库，只禁止后面的 under-limit 短路。
                        pass
                    if (
                        self._looks_like_income_context_message(user_message)
                        and not self._message_has_explicit_age_semantics(user_message)
                    ):
                        logger.debug("[提取保护] 收入语境命中，跳过 age 写入/短路参与: %s", value)
                        continue

                # 年龄限制检查：用户必须年满24岁
                if mapped_field == "age":
                    stable_self_age, numeric_analysis = self.resolve_stable_self_age(
                        user_message=user_message,
                        resolved_age=str(value or "") if value is not None else None,
                    )
                    age_label = self._derive_age_label_from_meta(
                        age_value=value,
                        extraction_meta=extraction_meta,
                    )
                    if (
                        stable_self_age is not None
                        and stable_self_age < 24
                        and not bool((numeric_analysis or {}).get("has_multiple_age_roles"))
                    ):
                        logger.info(f"[年龄限制] 用户年龄 {stable_self_age} 岁低于24岁，不符合服务条件")
                        # 设置年龄限制标志
                        user_profile.age_under_limit = True
                        user_profile.age = stable_self_age
                        if age_label:
                            user_profile.age_label = age_label
                        await self.user_service.save_user_profile(account_id, user_profile)
                        user_profile.set_extraction_evidence(
                            "age",
                            stable_self_age,
                            source_text=(extraction_meta.get("age", {}) or {}).get("source_text", user_message),
                            turn_id=turn_id,
                            confidence=float((extraction_meta.get("age", {}) or {}).get("confidence", 1.0)),
                            source=(extraction_meta.get("age", {}) or {}).get("source", "rule"),
                        )
                        if age_label:
                            user_profile.set_extraction_evidence(
                                "age_label",
                                age_label,
                                source_text=(extraction_meta.get("age_label", {}) or {}).get("source_text", user_message),
                                turn_id=turn_id,
                                confidence=float((extraction_meta.get("age_label", {}) or {}).get("confidence", 1.0)),
                                source=(extraction_meta.get("age_label", {}) or {}).get("source", "rule"),
                            )
                        await self.user_service.save_user_profile(account_id, user_profile)
                        # 返回特殊结果，通知调用方
                        return {
                            "collected": True,
                            "field": "age",
                            "value": stable_self_age,
                            "under_limit": True
                        }

                # 电话号码验证和处理
                if mapped_field == "phone":
                    # 验证电话号码格式（中国大陆和香港）
                    cleaned = ''.join(c for c in str(value) if c.isdigit())
                    # 归一化中国区号前缀：+86xxxxxxxxxxx / 86xxxxxxxxxxx -> xxxxxxxxxxx
                    if cleaned.startswith("86") and len(cleaned) == 13 and cleaned[2] == "1":
                        cleaned = cleaned[2:]
                    # 手机号验证：中国大陆(1开头+3-9,11位) 或 香港(5-9开头,8位)
                    if re.match(r'^1[3-9]\d{9}$', cleaned):  # 中国大陆
                        value = cleaned
                        logger.debug(f"[电话验证] 中国大陆手机号: {cleaned}")
                    elif re.match(r'^[5-9]\d{7}$', cleaned):  # 香港
                        value = cleaned
                        logger.debug(f"[电话验证] 香港手机号: {cleaned}")
                    else:
                        logger.info(f"[电话验证] 无效的电话号码格式: {value}")
                        invalid_contact_attempt = cleaned or str(value)
                        continue  # 跳过无效号码

                    # 若用户原始输入中存在超长数字串，且当前号码仅是其截断子串，
                    # 且用户本轮没有给出合法长度候选，则视为无效并要求重试。
                    if overlong_digit_sequences and cleaned not in valid_phone_candidates:
                        is_truncated_from_overlong = any(
                            cleaned in seq and len(seq) > len(cleaned)
                            for seq in overlong_digit_sequences
                        )
                        if is_truncated_from_overlong:
                            logger.info(f"[电话验证] 命中超长号码截断保护: cleaned={cleaned}, overlong={overlong_digit_sequences}")
                            invalid_contact_attempt = overlong_digit_sequences[0]
                            continue

                # 微信号校验：避免把过短/非法格式误记为有效微信
                if mapped_field == "wechat":
                    cleaned_wechat = str(value).strip()
                    wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'
                    mobile_like_wechat = ''.join(c for c in cleaned_wechat if c.isdigit())
                    lower_cleaned = cleaned_wechat.lower()

                    # 如果用户原文中存在“微信脏串”，且当前候选是该脏串的前缀，判为无效并要求重输。
                    if contaminated_wechat_tokens:
                        matched_dirty = next(
                            (token for token in contaminated_wechat_tokens if token.lower().startswith(lower_cleaned)),
                            None,
                        )
                        if matched_dirty:
                            logger.info(f"[微信验证] 命中脏串截断保护: cleaned={cleaned_wechat}, dirty={matched_dirty}")
                            invalid_contact_attempt = matched_dirty
                            continue

                    if re.match(wechat_pattern, cleaned_wechat):
                        value = cleaned_wechat
                    elif re.match(r'^1[3-9]\d{9}$', mobile_like_wechat) or re.match(r'^[5-9]\d{7}$', mobile_like_wechat):
                        # 兼容“微信就是手机号”这类输入
                        value = mobile_like_wechat
                        logger.debug(f"[微信验证] 按手机号型微信号收集: {mobile_like_wechat}")
                    else:
                        logger.info(f"[微信验证] 无效的微信格式: {value}")
                        invalid_contact_attempt = cleaned_wechat
                        continue

                # 检查字段是否需要更新
                if mapped_field == "sex":
                    # 只在用户明确自述性别时写入 sex，避免由“找男/找女”等择偶偏好误推断污染主档。
                    # 兼容“我叫小张，男的，30岁”这类常见自我介绍格式。
                    explicit_self_sex = re.search(
                        r"(?:我是|本人|我)\s*(男生|女生|男的|女的|男|女)",
                        user_message or "",
                    ) or re.search(
                        r"(?:上面|前面|之前).{0,8}(?:说过|说了|提过).{0,6}(?:是)?(男生|女生|男的|女的|男|女)",
                        user_message or "",
                    ) or re.search(
                        r"我叫[^，,。！？!\s]{1,8}\s*[，,、 ]\s*(男生|女生|男的|女的|男|女)",
                        user_message or "",
                    ) or re.search(
                        r"^\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?\s*$",
                        user_message or "",
                    ) or re.search(
                        r"^\s*(男生|女生|男的|女的|男|女)\s*[，,、 ]+\s*$",
                        user_message or "",
                    ) or re.search(
                        r"^\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?\s*[，,、 ]?\s*(?:单身|未婚|离异|已婚|分居)",
                        user_message or "",
                    ) or re.search(
                        r"^\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?\s*[，,、 ]?\s*(?:是的|对|嗯|好的|好)\s*[，,、 ]?\s*(?:单身|未婚|离异|已婚|分居)",
                        user_message or "",
                    ) or re.search(
                        r"(?:^|[，,、 ])\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?\s*[，,、 ]?\s*(?:单身|未婚|离异|已婚|分居)(?:$|[，,。！？!? ])",
                        user_message or "",
                    )
                    confirmation_context_sex = (
                        user_profile.pending_sex_confirmation
                        or self._extract_confirmed_sex_candidate_from_context(last_response)
                    )
                    contextual_embedded_sex = re.search(
                        r"(?:^|[，,、 ]|是|就是)\s*(男生|女生|男的|女的|男|女)\s*(?:呀|呢|哈|哦|啊)?(?:$|[，,。！？!? ])",
                        user_message or "",
                    )
                    affirmative_prefixed_sex = re.search(
                        r"^\s*(?:是的|对|对的|嗯|嗯嗯|好的|好|没错)"
                        r"(?:[呀呢啊哦哈啦嘛]*)?\s*(男生|女生|男的|女的|男|女)"
                        r"(?:\s*[，,、 ]\s*(?:\d{2}年|\d{2}后|\d{2}岁|19\d{2}年|20\d{2}年).*)?$",
                        user_message or "",
                    )
                    occupation_gender_self_intro = re.search(
                        r"(?:^|[，,、 ])(?:在编)?(男教师|女教师|男老师|女老师)(?:$|[，,。！？!? ])",
                        user_message or "",
                    ) or re.search(
                        r"(?:^|[，,、 ])(?:在编)(男|女)教师(?:$|[，,。！？!? ])",
                        user_message or "",
                    )
                    if confirmation_context_sex and contextual_embedded_sex:
                        explicit_self_sex = True
                        raw = contextual_embedded_sex.group(1)
                        value = "男" if "男" in raw else "女"
                    if confirmation_context_sex and affirmative_prefixed_sex:
                        explicit_self_sex = True
                        raw = affirmative_prefixed_sex.group(1)
                        value = "男" if "男" in raw else "女"
                    if confirmation_context_sex and self._is_affirmative_confirmation_answer(user_message):
                        explicit_self_sex = True
                        value = confirmation_context_sex
                    if occupation_gender_self_intro:
                        explicit_self_sex = True
                        raw = occupation_gender_self_intro.group(1)
                        value = "男" if "男" in raw else "女"
                    if not explicit_self_sex and self._looks_like_mixed_self_intro_with_gender_preference(user_message):
                        explicit_self_sex = True
                    if not explicit_self_sex:
                        logger.debug("[提取保护] sex 仅允许用户自述写入，本轮跳过 sex 更新")
                        continue

                inferred_self_intro_sex: Optional[str] = None

                if mapped_field == "occupation":
                    occupation_gender_self_intro = re.search(
                        r"(?:在编)?(男教师|女教师|男老师|女老师)",
                        user_message or "",
                    ) or re.search(
                        r"(?:在编)?(男|女)教师",
                        user_message or "",
                    )
                    if occupation_gender_self_intro:
                        raw = occupation_gender_self_intro.group(1)
                        inferred_self_intro_sex = "男" if "男" in raw else "女"
                    explicit_self_occupation = (
                        self._has_explicit_self_update_signal("occupation", user_message)
                        or bool(occupation_gender_self_intro)
                    )
                    has_preference_signal = bool(
                        self._resolve_partner_requirement_from_message(
                            user_message,
                            allow_legacy_fallback=False,
                        )
                    )
                    mixed_self_intro_with_occupation_preference = self._looks_like_mixed_self_intro_with_occupation_preference(
                        user_message
                    )
                    if not explicit_self_occupation and (
                        (has_preference_signal or self._looks_like_partner_requirement_content(value))
                        and not mixed_self_intro_with_occupation_preference
                    ):
                        logger.debug("[提取保护] occupation 命中择偶偏好语境，本轮跳过职业更新")
                        continue

                if mapped_field == "location":
                    explicit_self_location = self._has_explicit_self_update_signal("location", user_message)
                    mixed_self_intro_with_location_preference = self._looks_like_mixed_self_intro_with_location_preference(
                        user_message
                    )
                    if not explicit_self_location and (
                        self._looks_like_partner_preference_location_context(user_message)
                        and not mixed_self_intro_with_location_preference
                    ):
                        logger.debug("[提取保护] location 命中择偶偏好语境，本轮跳过所在地更新")
                        continue

                if mapped_field == "education":
                    explicit_self_education = (
                        self._has_explicit_self_update_signal("education", user_message)
                        or bool(self._extract_linked_self_partner_education_value(user_message))
                    )
                    mixed_self_intro_with_education_preference = (
                        self._looks_like_mixed_self_intro_with_education_preference(user_message)
                        or self._looks_like_profile_led_self_intro_with_education(user_message)
                    )
                    if (
                        not explicit_self_education
                        and self._looks_like_partner_preference_education_context(user_message)
                        and not mixed_self_intro_with_education_preference
                    ):
                        logger.debug("[提取保护] education 命中择偶学历语境，本轮跳过学历更新")
                        continue

                if mapped_field == "marital_status":
                    explicit_self_marital = self._has_explicit_self_update_signal("marital_status", user_message)
                    mixed_self_intro_with_marital_preference = self._looks_like_mixed_self_intro_with_marital_preference(
                        user_message
                    )
                    if (
                        not explicit_self_marital
                        and self._looks_like_partner_preference_marital_context(user_message)
                        and not mixed_self_intro_with_marital_preference
                    ):
                        logger.debug("[提取保护] marital_status 命中择偶婚况语境，本轮跳过婚况更新")
                        continue

                if mapped_field == "monthly_income":
                    merged_income = self._merge_income_value_and_unit(current_value, value)
                    if merged_income:
                        value = merged_income
                    explicit_self_income = self._has_explicit_self_income_signal(user_message)
                    mixed_self_intro_with_income_preference = self._looks_like_mixed_self_intro_with_income_preference(
                        user_message
                    )
                    if (
                        not explicit_self_income
                        and self._looks_like_partner_preference_income_context(user_message)
                        and not mixed_self_intro_with_income_preference
                    ):
                        logger.debug("[提取保护] monthly_income 命中择偶收入语境，本轮跳过收入更新")
                        continue

                is_collected = user_profile.collection_progress.get(mapped_field, False)

                # 特殊处理：择偶要求字段需要累积而不是覆盖
                if mapped_field == "partner_requirement":
                    partner_requirement_source = str(field_meta.get("source", "") or "").strip()
                    user_message_preferred_value = self._resolve_partner_requirement_from_message(
                        user_message,
                        allow_legacy_fallback=True,
                        prefer_structured=True,
                    )
                    raw_model_value = str(value or "").strip()
                    model_value = self._remove_unspoken_inferred_partner_requirement_content(raw_model_value, user_message)
                    correction_like_turn = self._looks_like_partner_requirement_correction_message(user_message)
                    if partner_requirement_source == "partner_requirement_structured_compose":
                        value = raw_model_value
                    elif user_message_preferred_value:
                        if not model_value:
                            value = user_message_preferred_value
                        elif len(user_message_preferred_value) > len(model_value):
                            value = user_message_preferred_value
                        else:
                            merged_parts: List[str] = []
                            for part in re.split(r"[，,、]+", model_value):
                                clean_part = self._normalize_partner_requirement_part(part)
                                if self._should_skip_partner_requirement_part(clean_part, user_message, extracted_data):
                                    continue
                                preferred_part = self._preferred_partner_requirement_surface(part, clean_part)
                                if preferred_part and not any(
                                    clean_part in existing or existing in clean_part
                                    for existing in merged_parts
                                ):
                                    merged_parts.append(preferred_part)
                            for part in re.split(r"[，,、]+", user_message_preferred_value):
                                clean_part = self._normalize_partner_requirement_part(part)
                                if self._should_skip_partner_requirement_part(clean_part, user_message, extracted_data):
                                    continue
                                preferred_part = self._preferred_partner_requirement_surface(part, clean_part)
                                if preferred_part and not any(
                                    clean_part in existing or existing in clean_part
                                    for existing in merged_parts
                                ):
                                    merged_parts.append(preferred_part)
                            value = "，".join(merged_parts)
                    else:
                        value = model_value

                    no_requirement_signals = ['没有', '没有了', '没', '无', '无特别要求', '没要求', '没特别', '暂时没有', '就这些']
                    value_stripped = value.strip()
                    if value_stripped in no_requirement_signals or any(value_stripped == sig for sig in no_requirement_signals):
                        if not current_value:
                            value = "无特别要求"
                            logger.debug("[择偶要求] 设置为'无特别要求'")
                        else:
                            logger.debug("[择偶要求] 无补充，保持原值")
                            continue

                    if current_value:
                        if correction_like_turn:
                            logger.info("[择偶要求] 纠正语境命中，使用本轮新值覆盖旧值")
                        elif partner_requirement_source == "partner_requirement_structured_compose":
                            logger.debug("[择偶要求] 结构化 compose 已包含旧尾巴，直接使用重组结果覆盖展示字段")
                        else:
                            # 已有旧值，需要累积追加
                            # 检查新值是否已经存在于旧值中（去重）
                            existing_requirements = [r.strip() for r in current_value.split(',')]

                            # 规范化新值用于比较
                            normalized_new = value.strip()
                            is_duplicate = False
                            for existing in existing_requirements:
                                # 检查是否重复（包含关系）
                                if normalized_new in existing or existing in normalized_new:
                                    is_duplicate = True
                                    break

                            if is_duplicate:
                                logger.debug(f"[择偶要求] 跳过重复值")
                                continue

                            # 追加新值
                            new_value = f"{current_value},{value}"
                            logger.debug(f"[择偶要求] 累积: +{value}")
                            value = new_value

                    normalized_requirement = self._resolve_partner_requirement_from_message(
                        str(value or ""),
                        allow_legacy_fallback=True,
                    )
                    raw_gender_preference = self._is_gender_preference_like_partner_requirement(raw_model_value)
                    user_gender_preference = self._extract_partner_gender_preference(user_message)
                    raw_requirement_payload = self._remove_unspoken_inferred_partner_requirement_content(
                        raw_model_value,
                        user_message,
                    )
                    raw_requirement_has_rich_content = self._looks_like_partner_requirement_content(
                        raw_requirement_payload,
                    )
                    if normalized_requirement and raw_requirement_has_rich_content:
                        raw_parts = [
                            str(part or "").strip()
                            for part in re.split(r"[，,、]+", str(raw_requirement_payload or "").strip())
                            if str(part or "").strip()
                        ]
                        normalized_parts = [
                            str(part or "").strip()
                            for part in re.split(r"[，,、]+", str(normalized_requirement or "").strip())
                            if str(part or "").strip()
                        ]
                        if len(raw_parts) <= 1 and len(normalized_parts) == 1:
                            value = normalized_requirement
                        else:
                            merged_parts = []
                            for source_value, prefer_raw_surface in (
                                (raw_requirement_payload, True),
                                (normalized_requirement, False),
                            ):
                                for part in re.split(r"[，,、]+", str(source_value or "").strip()):
                                    clean_part = self._normalize_partner_requirement_part(part) or str(part or "").strip()
                                    if not clean_part:
                                        continue
                                    if self._should_skip_partner_requirement_part(clean_part, user_message, extracted_data):
                                        continue
                                    preferred_part = (
                                        str(part or "").strip()
                                        if prefer_raw_surface
                                        else self._preferred_partner_requirement_surface(part, clean_part)
                                    )
                                    if preferred_part and not any(
                                        clean_part in (self._normalize_partner_requirement_part(existing) or existing)
                                        or (self._normalize_partner_requirement_part(existing) or existing) in clean_part
                                        for existing in merged_parts
                                    ):
                                        merged_parts.append(preferred_part)
                            if merged_parts:
                                value = "，".join(merged_parts)
                    elif normalized_requirement:
                        value = normalized_requirement
                    inferred_partner_gender = (
                        user_gender_preference
                        or ("男" if "男" in raw_model_value else "女" if "女" in raw_model_value else None)
                    )
                    if inferred_partner_gender and not getattr(user_profile, "partner_gender_preference", None):
                        gender_updated = await self.user_service.update_user_profile_field(
                            account_id,
                            "partner_gender_preference",
                            inferred_partner_gender,
                        )
                        if gender_updated:
                            collected_fields.append(
                                {"field": "partner_gender_preference", "value": inferred_partner_gender}
                            )
                            collected_field_names.append("partner_gender_preference")
                            user_profile.partner_gender_preference = inferred_partner_gender
                    if not normalized_requirement and raw_requirement_has_rich_content:
                        normalized_requirement = raw_requirement_payload
                        value = raw_requirement_payload
                    if not normalized_requirement and raw_gender_preference:
                        logger.debug("[提取保护] partner_requirement 命中纯性别偏好，改写入 partner_gender_preference")
                        continue

                current_value_is_high_quality = self._is_high_quality_field_value(mapped_field, current_value)
                new_value_is_high_quality = self._is_high_quality_field_value(
                    mapped_field,
                    value,
                    user_message=user_message,
                    scope=field_scope,
                )

                if (
                    mapped_field in self._STABLE_PROFILE_FIELDS
                    and is_collected
                    and current_value
                    and current_value_is_high_quality
                    and not self._is_effectively_same_value(current_value, value)
                    and not self._has_explicit_self_update_signal(mapped_field, user_message)
                    and not self._has_explicit_field_correction_signal(
                        mapped_field,
                        user_message,
                        current_value,
                        value,
                    )
                ):
                    logger.info(
                        f"[字段稳定保护] 跳过 {mapped_field} 改写: current={current_value}, new={value}"
                    )
                    continue

                if (
                    mapped_field in self._STABLE_PROFILE_FIELDS
                    and is_collected
                    and current_value
                    and not current_value_is_high_quality
                    and new_value_is_high_quality
                ):
                    logger.info(
                        f"[字段稳定保护] 放行高质量新值覆盖低质量旧值: field={mapped_field}, current={current_value}, new={value}"
                    )

                needs_update = not is_collected or (not self._is_effectively_same_value(current_value, value))

                if needs_update:
                    success = await self.user_service.update_user_profile_field(
                        account_id, mapped_field, value
                    )
                    if success:
                        collected_fields.append({"field": mapped_field, "value": value})
                        collected_field_names.append(mapped_field)
                        if mapped_field == "age":
                            age_label = self._derive_age_label_from_meta(
                                age_value=value,
                                extraction_meta=extraction_meta,
                            )
                            if age_label:
                                label_updated = await self.user_service.update_user_profile_field(
                                    account_id,
                                    "age_label",
                                    age_label,
                                )
                                if label_updated:
                                    collected_fields.append({"field": "age_label", "value": age_label})
                                    collected_field_names.append("age_label")
                            elif user_profile.age_label:
                                user_profile.age_label = None
                                user_profile.collection_progress["age_label"] = False
                                await self.user_service.save_user_profile(account_id, user_profile)
                        if mapped_field == "partner_requirement":
                            for subfield, subvalue in self._extract_partner_preference_subslots(value).items():
                                if not str(subvalue or "").strip():
                                    continue
                                if str(extracted_data.get(subfield) or "").strip():
                                    continue
                                subfield_success = await self.user_service.update_user_profile_field(
                                    account_id,
                                    subfield,
                                    subvalue,
                                )
                                if subfield_success:
                                    collected_fields.append({"field": subfield, "value": subvalue})
                                    collected_field_names.append(subfield)
                        if (
                            mapped_field == "occupation"
                            and inferred_self_intro_sex
                            and not getattr(user_profile, "sex", None)
                        ):
                            sex_success = await self.user_service.update_user_profile_field(
                                account_id,
                                "sex",
                                inferred_self_intro_sex,
                            )
                            if sex_success:
                                collected_fields.append({"field": "sex", "value": inferred_self_intro_sex})
                                collected_field_names.append("sex")

        # 更新 profile
        user_profile = await self.user_service.get_user_profile(account_id)
        if collected_field_names:
            for field_info in collected_fields:
                field_name = field_info.get("field")
                if not field_name:
                    continue
                field_meta = extraction_meta.get(field_name, {})
                user_profile.set_extraction_evidence(
                    field_name=field_name,
                    value=field_info.get("value"),
                    source_text=str(field_meta.get("source_text") or user_message or field_info.get("value") or ""),
                    turn_id=turn_id,
                    confidence=float(field_meta.get("confidence", 0.75)),
                    source=str(field_meta.get("source") or "ai"),
                )
            await self.user_service.save_user_profile(account_id, user_profile)

        if collected_fields:
            result = {
                "collected": True,
                "field": collected_fields[0]["field"] if collected_fields else None,
                "value": collected_fields[0]["value"] if collected_fields else None,
                "all_fields": collected_fields
            }
            if invalid_contact_attempt:
                result["invalid_contact_attempt"] = invalid_contact_attempt
            return result

        result = {
            "collected": False,
            "all_fields": []
        }
        if invalid_contact_attempt:
            result["invalid_contact_attempt"] = invalid_contact_attempt
        return result

    def get_collected_info_summary(self, user_profile: UserProfile) -> str:
        """
        获取已收集信息的摘要

        使用压缩格式节省 token

        Args:
            user_profile: 用户档案

        Returns:
            str: 已收集信息摘要
        """
        # 字段名映射（英文 -> 中文）
        field_name_map = {
            'last_name': '称呼',
            'sex': '性别',
            'age': '年龄',
            'height': '身高',
            'weight': '体重',
            'location': '所在地',
            'education': '学历',
            'occupation': '职业',
            'occupation_inference_candidate': '职业弱推断',
            'monthly_income': '月收入',
            'marital_status': '婚况',
            'contact': '联系方式',
            'phone': '电话',
            'wechat': '微信',
            'partner_gender_preference': '择偶性别偏好',
            'partner_requirement': '择偶要求'
        }

        # 按固定顺序收集
        parts = []
        if user_profile.last_name:
            parts.append(str(user_profile.last_name))
        if user_profile.sex:
            parts.append(str(user_profile.sex))
        if user_profile.location:
            parts.append(str(user_profile.location))
        if user_profile.age:
            # 计算出生年份，让AI理解年龄和出生年份是同一信息
            from datetime import datetime
            birth_year = datetime.now().year - user_profile.age
            if user_profile.age_label:
                parts.append(f"{user_profile.age_label}({user_profile.age}岁/{birth_year}年)")
            else:
                parts.append(f"{user_profile.age}岁({birth_year}年)")
        if user_profile.education:
            parts.append(str(user_profile.education))
        if user_profile.occupation:
            parts.append(str(user_profile.occupation))
        elif getattr(user_profile, "occupation_inference_candidate", None):
            parts.append(f"职业弱推断:{user_profile.occupation_inference_candidate}")
        if user_profile.height:
            parts.append(str(user_profile.height))
        if user_profile.weight:
            parts.append(str(user_profile.weight))
        if user_profile.monthly_income:
            parts.append(str(user_profile.monthly_income))
        if user_profile.marital_status:
            parts.append(str(user_profile.marital_status))

        # 构建基础摘要
        if parts:
            # 添加择偶性别偏好/择偶要求（如果有）- 在联系方式之前
            if user_profile.partner_gender_preference:
                gender_label = "男生" if user_profile.partner_gender_preference == "男" else "女生" if user_profile.partner_gender_preference == "女" else str(user_profile.partner_gender_preference)
                parts.append(f"偏好性别:{gender_label}")
            partner_requirement_text = str(user_profile.partner_requirement or "").strip()
            if not partner_requirement_text:
                partner_requirement_text = self._compose_structured_partner_preference_text(user_profile)
            if partner_requirement_text:
                parts.append(f"要求:{partner_requirement_text}")

            # 使用新的联系方式状态显示
            contact_status = user_profile.get_contact_status()
            if contact_status != "未留":
                parts.append(contact_status)
                # 只有当联系方式真正被收集时才标记（电话或微信已收集）
                # 注意：不能在"争取中"状态就标记为已收集
                has_real_contact = (
                    (user_profile.phone and user_profile.phone_collected) or
                    (user_profile.wechat and user_profile.wechat_collected)
                )
                if has_real_contact and not user_profile.collection_progress.get('contact', False):
                    user_profile.collection_progress['contact'] = True

            # 添加离异确认标记（如果用户是离异且已确认）
            if user_profile.marital_status == '离异' and hasattr(user_profile, 'divorce_confirmed') and user_profile.divorce_confirmed:
                parts.append("离异确认")
            summary = "【已收集】" + ",".join(parts)
        else:
            summary = "【已收集】无"

        # 添加"已跳过"的字段列表（使用 skipped_fields 字典，而不是 field_ask_count）
        # 字段被标记为跳过的条件：AI 问了 2 次用户都没回答
        skipped_list = []
        for field in user_profile.skipped_fields.keys():
            # 检查字段是否还未收集
            is_collected = user_profile.collection_progress.get(field, False)
            has_value = getattr(user_profile, field, None) is not None
            if not is_collected and not has_value:
                field_cn = field_name_map.get(field, field)
                count = user_profile.field_ask_count.get(field, 2)
                skipped_list.append(f"{field_cn}({count}次未答)")

        if skipped_list:
            summary += "\n【⚠️已跳过】" + "、".join(skipped_list) + "（禁止再问这些字段！）"

        return summary

    def get_recent_collected_info_prompt(
        self,
        collected_fields: List[Dict[str, Any]],
        user_profile: UserProfile
    ) -> str:
        """
        生成最近收集信息的确认提示

        Args:
            collected_fields: 最近收集的字段列表
            user_profile: 用户档案

        Returns:
            str: 确认提示文本
        """
        if not collected_fields:
            return ""

        field_mapping = {
            'last_name': '称呼',
            'sex': '性别',
            'age': '年龄',
            'height': '身高',
            'location': '地区',
            'marital_status': '婚况',
            'education': '学历',
            'occupation': '职业',
            'monthly_income': '收入',
            'contact': '联系方式',
            'partner_requirement': '择偶要求'
        }

        prompts = []
        for field_info in collected_fields:
            field = field_info.get('field')
            value = field_info.get('value')

            field_name = field_mapping.get(field, field)
            prompts.append(f"【收集到{field_name}】{value}")

        return " ".join(prompts)
