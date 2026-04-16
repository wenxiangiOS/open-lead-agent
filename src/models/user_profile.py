"""User profile model for collecting personal information"""

from typing import Dict, Any, Optional, List, ClassVar
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator


class UserProfile(BaseModel):
    """
    用户个人信息模型

    收集字段（按当前策略分层）：
    1. 核心字段：性别、年龄、学历、职业、工作地、联系方式
    2. 准核心字段：婚况
    3. 中等字段：月薪、择偶要求
    4. 低优字段：称呼、身高、体重（仅被动记录，不主动追问）
    """

    # 基本信息
    account_id: str = Field(..., description="用户账号ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    profile_version: int = Field(default=0, description="资料字段版本号，仅在真实资料字段变更时递增")

    # 待收集的信息（初始为 None）
    sex: Optional[str] = Field(None, description="性别（男/女）- 核心字段")
    last_name: Optional[str] = Field(None, description="用户主动提供的称呼/昵称（低优字段）")
    age: Optional[int] = Field(None, description="年龄（数字）")
    age_label: Optional[str] = Field(None, description="年龄原始表达（如90后、95后）")
    pending_birth_year_bucket: Optional[str] = Field(None, description="待确认的出生年份桶（如90后）")
    birth_year_confirmation_closed: bool = Field(default=False, description="是否已停止主动追问具体出生年份")
    extraction_evidence: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="字段提取证据链：value/source_text/turn_id/confidence/source"
    )
    height: Optional[str] = Field(None, description="身高（低优字段，例如：165cm）")
    weight: Optional[str] = Field(None, description="体重（低优字段，例如：55kg）")
    location: Optional[str] = Field(None, description="工作地/所在地（城市/地区）")
    education: Optional[str] = Field(None, description="学历（核心字段）")
    marital_status: Optional[str] = Field(None, description="婚况（准核心字段）")
    monthly_income: Optional[str] = Field(None, description="收入信息（可收月薪/年薪/区间，中等字段）")
    occupation: Optional[str] = Field(None, description="职业（核心字段）")
    occupation_inference_candidate: Optional[str] = Field(None, description="职业弱推断候选（不作为正式已收集职业）")
    contact: Optional[str] = Field(None, description="联系方式状态显示（核心字段）")
    phone: Optional[str] = Field(None, description="电话号码（单独存储）")
    wechat: Optional[str] = Field(None, description="微信号")
    partner_requirement: Optional[str] = Field(None, description="择偶要求聚合展示文本（中等字段，结构化子槽优先）")
    partner_gender_preference: Optional[str] = Field(None, description="择偶性别偏好（男/女）")

    # Phase 2: 择偶偏好结构化子槽（主链优先消费，partner_requirement 仅作聚合展示）
    partner_pref_location: Optional[str] = Field(None, description="择偶地区偏好")
    partner_pref_age: Optional[str] = Field(None, description="择偶年龄偏好")
    partner_pref_industry: Optional[str] = Field(None, description="择偶行业偏好")
    partner_pref_age_relation: Optional[str] = Field(None, description="择偶年龄关系偏好")
    partner_pref_locality: Optional[str] = Field(None, description="择偶同城/本地偏好")
    partner_pref_height: Optional[str] = Field(None, description="择偶身高偏好")
    partner_pref_education: Optional[str] = Field(None, description="择偶学历偏好")
    partner_pref_personality: Optional[str] = Field(None, description="择偶性格偏好")
    partner_pref_income: Optional[str] = Field(None, description="择偶收入偏好")
    partner_pref_other: Optional[str] = Field(None, description="择偶其他偏好")

    # 收集状态跟踪
    collection_progress: Dict[str, bool] = Field(
        default_factory=lambda: {
            "sex": False,
            "last_name": False,
            "age": False,
            "age_label": False,
            "height": False,
            "weight": False,
            "location": False,
            "education": False,
            "marital_status": False,
            "monthly_income": False,
            "occupation": False,
            "contact": False,
            "partner_requirement": False,
            "partner_gender_preference": False,
            # Phase 2: 择偶要求子槽
            "partner_pref_location": False,
            "partner_pref_age": False,
            "partner_pref_industry": False,
            "partner_pref_age_relation": False,
            "partner_pref_locality": False,
            "partner_pref_height": False,
            "partner_pref_education": False,
            "partner_pref_personality": False,
            "partner_pref_income": False,
            "partner_pref_other": False,
        },
        description="各字段收集状态"
    )

    # 容错跟踪
    error_count: Dict[str, int] = Field(
        default_factory=dict,
        description="各字段错误提醒次数"
    )

    # 跳过的字段（用户拒绝提供的字段）
    skipped_fields: Dict[str, bool] = Field(
        default_factory=dict,
        description="用户拒绝提供、永久跳过的字段"
    )

    # 字段追问计数（智能追问机制）
    field_ask_count: Dict[str, int] = Field(
        default_factory=dict,
        description="每个字段被问过的次数，用于智能追问机制"
    )
    effective_field_ask_count: Dict[str, int] = Field(
        default_factory=dict,
        description="每个字段真实展示给用户的有效询问次数，用于主动追问上限控制"
    )
    recent_asked_fields: List[str] = Field(
        default_factory=list,
        description="最近被 AI 主动追问的字段历史（按轮次）"
    )
    active_ask_closed_fields: Dict[str, bool] = Field(
        default_factory=dict,
        description="字段是否已关闭主动追问；关闭后仅允许被动提取"
    )

    # 联系方式收集状态（新设计）
    phone_collected: bool = Field(default=False, description="电话是否已收集")
    wechat_collected: bool = Field(default=False, description="微信是否已收集")
    phone_ask_count: int = Field(default=0, description="电话询问次数（0-2）")
    wechat_ask_count: int = Field(default=0, description="微信询问次数（0-2）")
    phone_effective_ask_count: int = Field(default=0, description="电话有效询问次数（用于联系方式流程完成判断）")
    wechat_effective_ask_count: int = Field(default=0, description="微信有效询问次数（用于联系方式流程完成判断）")
    phone_invalid_input_retry_count: int = Field(default=0, description="电话无效输入重试次数")
    wechat_invalid_input_retry_count: int = Field(default=0, description="微信无效输入重试次数")
    phone_invalid_input_closed: bool = Field(default=False, description="电话是否因连续无效输入而关闭主动追问")
    wechat_invalid_input_closed: bool = Field(default=False, description="微信是否因连续无效输入而关闭主动追问")
    contact_complete: bool = Field(default=False, description="联系方式流程是否已完成（电话流程和微信流程都已完成）")
    last_contact_request_type: Optional[str] = Field(default=None, description="最近一次真实展示给用户的联系方式类型（phone/wechat）")
    is_hongkong_user: Optional[bool] = Field(default=None, description="是否是香港用户（缓存）")
    pending_contact_candidate: Optional[str] = Field(default=None, description="待用户确认的联系方式候选")
    pending_contact_field: Optional[str] = Field(default=None, description="待确认的联系方式字段（phone/wechat）")
    pending_contact_hint: Optional[str] = Field(default=None, description="待确认联系方式的提示类型")

    # 联系方式拒绝状态（兼容旧字段，逐步迁移）
    rejected_wechat: bool = Field(default=False, description="用户是否拒绝微信")
    rejected_phone: bool = Field(default=False, description="用户是否拒绝电话")

    # 对话状态
    conversation_ended: bool = Field(default=False, description="对话是否已结束")
    divorce_confirmed: bool = Field(default=False, description="离异手续是否已确认办妥")
    divorce_confirmation_pending: bool = Field(default=False, description="离异后是否仍待确认手续状态")
    pending_sex_confirmation: Optional[str] = Field(default=None, description="待确认的性别候选（男/女）")
    needs_bridge_back: bool = Field(default=False, description="FAQ/边界轮后是否需要桥接回主线")
    last_side_topic_type: Optional[str] = Field(None, description="最近支线话题类型 (faq_photo/faq_contact/faq_process/boundary/complaint)")
    complaint_cooldown_until: Optional[int] = Field(None, description="complaint cooldown 结束的消息序号")
    last_profile_summary_turn: Optional[int] = Field(None, description="上次画像小结的消息序号")
    recent_semantic_slots: List[str] = Field(
        default_factory=list,
        description="最近 5 轮收集的语义槽（用于去重，如 partner_pref_location, partner_pref_age）"
    )
    recent_response_openings: List[str] = Field(
        default_factory=list,
        description="最近 5 轮 assistant 回复开头签名，用于避免重复使用同一开场骨架"
    )
    age_under_limit: bool = Field(default=False, description="年龄是否低于服务限制（24岁以下）")
    lgbt_user: bool = Field(default=False, description="是否是LGBT用户（同性恋/百合）")
    already_married: bool = Field(default=False, description="用户是否已婚")
    proxy_user: bool = Field(default=False, description="是否是代相亲（帮别人问）")
    spam_user: bool = Field(default=False, description="是否是骚扰/广告用户")

    # === 投诉修复与追问冷却状态 ===
    repair_mode: bool = Field(default=False, description="是否处于投诉修复模式（冷却期内）")
    repair_reason: Optional[str] = Field(None, description="进入修复模式的原因（repeat_ask/rude_tone/over_questioning）")
    ask_cooldown_turns: int = Field(default=0, description="追问冷却剩余轮数（每轮递减，0表示可正常追问）")
    blocked_ask_intents: List[str] = Field(
        default_factory=list,
        description="被禁止的追问意图类型（ask_partner_requirement/ask_matching_priority/ask_basic_profile）"
    )
    last_asked_field: Optional[str] = Field(None, description="上一轮 AI 明确追问的字段（用于短答槽位绑定）")
    last_asked_side_field: Optional[str] = Field(None, description="上一轮 AI 顺带追问的字段（用于主次双答绑定）")
    last_asked_turn_index: Optional[int] = Field(None, description="上一轮追问的消息序号")
    last_question_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="上一轮结构化提问状态（question_intent/asked_fields/side_fields/expected_scope/allow_mixed_answer/resume_target）",
    )
    last_semantic_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="上一轮统一语义摘要（primary_domain/acts/user_questions/observed_fields/pending_fields/resume_target）",
    )
    non_cooperation_turns: int = Field(default=0, description="连续不配合主流程的轮数")
    off_topic_turns: int = Field(default=0, description="连续偏离主流程的轮数")
    open_profile_attempts: int = Field(default=0, description="开放式补画像尝试次数")
    last_engagement_mode: Optional[str] = Field(None, description="最近一轮投入模式（full/compact/light/close）")
    resume_profile_mode: Optional[str] = Field(default=None, description="答疑/顾虑轮后待恢复的资料收集模式")
    resume_profile_target: Optional[str] = Field(default=None, description="答疑/顾虑轮后待恢复的主目标字段")
    last_user_concern_type: Optional[str] = Field(default=None, description="最近一次用户疑问/顾虑类型")
    field_miss_streak: Dict[str, int] = Field(
        default_factory=dict,
        description="字段被错位回答的连续次数，用于第一次错位不计 ask_count",
    )
    last_effective_progress: bool = Field(default=False, description="最近一轮是否产生有效推进")
    pending_retry_field: Optional[str] = Field(
        default=None,
        description="当前允许无视普通冷却再追问一次的字段（用于核心字段隐晦拒绝后的解释型重问）",
    )

    # 通用资料概览只统计业务关键字段；低优字段和派生展示字段不计入公共完成度。
    SUMMARY_PROGRESS_FIELDS: ClassVar[tuple[str, ...]] = (
        "sex",
        "age",
        "location",
        "education",
        "occupation",
        "marital_status",
        "contact",
    )

    @staticmethod
    def normalize_sex(v):
        """规范化性别字段"""
        if v is not None:
            v = str(v).strip()
            if v in ['男', '男宝', '男生的', '帅哥', '小哥哥', '哥哥', '先生', 'M', 'm']:
                return '男'
            elif v in ['女', '女宝', '女生的', '美女', '小姐姐', '妹妹', '女士', 'F', 'f']:
                return '女'
        return v

    @staticmethod
    def normalize_contact(v):
        """规范化联系方式（电话号码，支持中国大陆和香港）"""
        if v is not None:
            v = str(v).strip()
            cleaned = ''.join(c for c in v if c.isdigit())
            if re.match(r'^1[3-9]\d{9}$', cleaned):  # 中国大陆
                return cleaned
            if re.match(r'^[5-9]\d{7}$', cleaned):  # 香港
                return cleaned
            return None
        return v

    @staticmethod
    def normalize_age(v):
        """规范化年龄"""
        if v is not None:
            if isinstance(v, str):
                value_str = str(v).strip()
                # 优先识别“90后/95后”一类表达，避免被通用数字提取误解析成 90/95 岁。
                suffix_match = re.search(r'(\d{2})后', value_str)
                if suffix_match:
                    year_suffix = int(suffix_match.group(1))
                    current_year_suffix = datetime.now().year % 100
                    birth_year = 2000 + year_suffix if year_suffix <= current_year_suffix else 1900 + year_suffix
                    v = datetime.now().year - birth_year
                else:
                    birth_year_match = re.search(r'(19\d{2}|20\d{2})年?(?:出生)?', value_str)
                    if birth_year_match:
                        birth_year = int(birth_year_match.group(1))
                        v = datetime.now().year - birth_year
                    else:
                        short_birth_year_match = re.search(r'(?<!\d)(\d{2})年(?:的)?(?:出生)?', value_str)
                        if short_birth_year_match:
                            year_suffix = int(short_birth_year_match.group(1))
                            current_year_suffix = datetime.now().year % 100
                            birth_year = 2000 + year_suffix if year_suffix <= current_year_suffix else 1900 + year_suffix
                            v = datetime.now().year - birth_year
                        else:
                            age_match = re.search(r'(\d{1,3})\s*岁?', value_str)
                            if not age_match:
                                return None
                            v = int(age_match.group(1))
            if 18 <= v <= 100:
                return v
            return None
        return v

    @staticmethod
    def normalize_height(v):
        """规范化身高"""
        if v is not None:
            v = str(v).strip()
            match = re.search(r'(\d+)', v)
            if match:
                height_val = int(match.group(1))
                if 140 <= height_val <= 220:
                    return f"{height_val}cm"
        return v

    @staticmethod
    def normalize_weight(v):
        """规范化体重"""
        if v is not None:
            v = str(v).strip()
            match = re.search(r'(\d+)', v)
            if match:
                weight_val = int(match.group(1))
                if 30 <= weight_val <= 200:
                    return f"{weight_val}kg"
        return v

    @field_validator('sex', mode='before')
    @classmethod
    def validate_sex(cls, v):
        """验证性别字段"""
        return cls.normalize_sex(v)

    @field_validator('contact', mode='before')
    @classmethod
    def validate_contact(cls, v):
        """验证联系方式字段"""
        return cls.normalize_contact(v)

    @field_validator('age', mode='before')
    @classmethod
    def validate_age(cls, v):
        """验证年龄字段"""
        return cls.normalize_age(v)

    @field_validator('height', mode='before')
    @classmethod
    def validate_height(cls, v):
        """验证身高字段"""
        return cls.normalize_height(v)

    @field_validator('weight', mode='before')
    @classmethod
    def validate_weight(cls, v):
        """验证体重字段"""
        return cls.normalize_weight(v)

    def update_field(self, field_name: str, value: Any) -> bool:
        """
        更新用户信息字段

        Args:
            field_name: 字段名称
            value: 字段值

        Returns:
            bool: 是否更新成功
        """
        if not hasattr(self, field_name):
            return False

        # 验证并更新字段
        try:
            if field_name == 'phone':
                # 电话号码验证
                validated = self._validate_phone(value)
            elif field_name == 'contact':
                validated = self.normalize_contact(value)
            elif field_name == 'sex':
                validated = self.normalize_sex(value)
            elif field_name == 'age':
                validated = self.normalize_age(value)
            elif field_name == 'age_label':
                validated = str(value).strip()
            elif field_name == 'height':
                validated = self.normalize_height(value)
            elif field_name == 'weight':
                validated = self.normalize_weight(value)
            elif field_name == 'last_name':
                # 姓氏字段直接使用提取的值，不经过额外验证
                validated = value
            elif field_name == 'partner_requirement':
                # 择偶要求字段：按分片去重合并；当新值已覆盖旧值时，允许直接替换为更完整的结构化文本。
                existing = getattr(self, 'partner_requirement', None)
                normalized_value = str(value or "").strip()
                if existing and existing != "":
                    existing_items = [item.strip() for item in re.split(r'[，,、]+', str(existing)) if item.strip()]
                    new_items = [item.strip() for item in re.split(r'[，,、]+', normalized_value) if item.strip()]
                    existing_norm = {item.replace(" ", "") for item in existing_items}
                    new_norm = {item.replace(" ", "") for item in new_items}

                    if new_items and existing_norm.issubset(new_norm):
                        validated = normalized_value
                    else:
                        merged_items = list(existing_items)
                        for item in new_items:
                            item_norm = item.replace(" ", "")
                            if item_norm and item_norm not in {existing_item.replace(" ", "") for existing_item in merged_items}:
                                merged_items.append(item)
                        validated = "，".join(merged_items) if merged_items else normalized_value
                else:
                    validated = normalized_value
            elif field_name == 'partner_gender_preference':
                normalized = str(value or '').strip()
                if normalized in {'男生', '男', 'male'}:
                    validated = '男'
                elif normalized in {'女生', '女', 'female'}:
                    validated = '女'
                else:
                    validated = value
            elif field_name == 'occupation_inference_candidate':
                validated = self._normalize_occupation_value_for_candidate(value)
            else:
                validated = value

            # 只有值不为 None 时才更新
            if validated is not None and validated != "":
                # 调试：检查 last_name 是否被设置为拼接字符串
                if field_name == 'last_name' and '/' in str(validated):
                    import logging
                    logging.getLogger(__name__).warning(f"last_name 被设置为拼接字符串: {validated}")
                setattr(self, field_name, validated)
                if field_name != 'occupation_inference_candidate':
                    self.collection_progress[field_name] = True
                    # 字段成功收集后，重置追问计数
                    self.reset_ask_count(field_name)
                if field_name == 'sex':
                    self.pending_sex_confirmation = None
                if field_name == 'age':
                    age_label = str(getattr(self, 'age_label', '') or '').strip()
                    if re.search(r'^\d{2}年$', age_label) or re.search(r'^(19|20)\d{2}年$', age_label):
                        self.pending_birth_year_bucket = None
                        self.birth_year_confirmation_closed = False
                elif field_name == 'age_label':
                    age_label = str(validated or "").strip()
                    derived_age = self.normalize_age(age_label)
                    if isinstance(derived_age, int):
                        self.age = derived_age
                    if re.search(r'^\d{2}后$', age_label):
                        self.pending_birth_year_bucket = age_label
                        self.birth_year_confirmation_closed = False
                        # 年龄桶不是最终精度，不算年龄字段完成
                        self.collection_progress['age'] = False
                    elif re.search(r'^(\d{2}|19\d{2}|20\d{2})年$', age_label):
                        self.pending_birth_year_bucket = None
                        self.birth_year_confirmation_closed = False
                        self.collection_progress['age'] = True

                if field_name == 'occupation':
                    self.occupation_inference_candidate = None

                # 特殊处理：phone 和 wechat 字段收集成功后更新状态
                if field_name == 'phone':
                    self.phone_collected = True
                    # 同时更新 contact 字段为状态显示
                    self.contact = self.get_contact_status()
                elif field_name == 'wechat':
                    self.wechat_collected = True
                    # 同时更新 contact 字段为状态显示
                    self.contact = self.get_contact_status()

                self._touch_profile_data(increment_version=(field_name != 'occupation_inference_candidate'))
                return True

        except Exception as e:
            # 记录错误但不更新
            self.error_count[field_name] = self.error_count.get(field_name, 0) + 1
            return False

        return False

    def _touch_profile_data(self, *, increment_version: bool = True) -> None:
        self.updated_at = datetime.now()
        if increment_version:
            self.profile_version = int(getattr(self, "profile_version", 0) or 0) + 1

    def _validate_phone(self, value: Any) -> Optional[str]:
        """
        验证电话号码（支持中国大陆和香港）

        Args:
            value: 电话号码值

        Returns:
            Optional[str]: 验证后的电话号码，失败返回 None
        """
        if value is None:
            return None

        import re
        v = str(value).strip()
        # 移除非数字字符
        cleaned = ''.join(c for c in v if c.isdigit())
        # 手机号验证：中国大陆(1开头+3-9,11位) 或 香港(5-9开头,8位)
        if re.match(r'^1[3-9]\d{9}$', cleaned):  # 中国大陆
            return cleaned
        if re.match(r'^[5-9]\d{7}$', cleaned):  # 香港
            return cleaned
        # 验证失败返回 None
        return None

    def get_progress(self) -> float:
        """
        获取收集进度（百分比）

        跳过的字段视为已完成，计入进度

        Returns:
            float: 收集进度 0.0 - 1.0
        """
        tracked_fields = self.SUMMARY_PROGRESS_FIELDS
        completed = sum(1 for field in tracked_fields if self.collection_progress.get(field, False))
        skipped = sum(1 for field in tracked_fields if self.skipped_fields.get(field, False))
        total = len(tracked_fields)
        return (completed + skipped) / total if total > 0 else 0.0

    def is_collection_complete(self) -> bool:
        """
        检查信息收集是否完成

        Returns:
            bool: 是否已完成收集（进度 >= 90%）
        """
        return self.get_progress() >= 1.0

    def is_empty(self) -> bool:
        """
        检查用户档案是否为空（全新用户）

        Returns:
            bool: 是否为空（所有关键字段都是 None）
        """
        # 检查所有关键字段是否都为空
        key_fields = ['sex', 'last_name', 'age', 'height', 'weight',
                      'location', 'education', 'marital_status',
                      'monthly_income', 'occupation', 'contact', 'partner_requirement', 'partner_gender_preference']
        return all(getattr(self, field) is None for field in key_fields)

    def get_missing_fields(self) -> list:
        """
        获取未收集的字段

        不包括已跳过的字段

        Returns:
            list: 未收集的字段名列表
        """
        return [
            field for field in self.SUMMARY_PROGRESS_FIELDS
            if not self.collection_progress.get(field, False) and field not in self.skipped_fields
        ]

    def get_next_field_to_collect(self) -> Optional[str]:
        """
        获取下一个需要收集的字段

        按当前资料收集策略返回优先级最高的未收集字段。
        这里只用于兼容旧调用，主流程实际调度应优先使用 ProfileCollectionPolicy。

        Returns:
            Optional[str]: 下一个要收集的字段名
        """
        # Phase 2 调整后的策略顺序：
        # 1. 性别 2. 年龄 3. 城市 4. 偏好轻聊(提前) 5. 学历/工作 6. 婚姻状态 7. 收入(后移) 8. 联系方式
        priority_order = [
            'sex',
            'age',
            'location',
            'partner_requirement',  # Phase 2: 偏好提前
            'education',
            'occupation',
            'marital_status',
            'monthly_income',  # Phase 2: 收入后移
            'contact',
            'last_name',
            'height',
            'weight',
        ]

        for field in priority_order:
            # 检查是否已收集或已跳过
            is_collected = self.collection_progress.get(field, False)
            is_skipped = self.skipped_fields.get(field, False)
            if not is_collected and not is_skipped:
                return field

        return None

    def is_field_error_limit_reached(self, field_name: str, max_errors: int = 2) -> bool:
        """
        检查字段错误次数是否达到限制

        Args:
            field_name: 字段名
            max_errors: 最大错误次数，默认2次

        Returns:
            bool: 是否达到错误限制
        """
        return self.error_count.get(field_name, 0) >= max_errors

    def reset_error_count(self, field_name: str) -> None:
        """
        重置字段错误计数

        Args:
            field_name: 字段名
        """
        if field_name in self.error_count:
            self.error_count[field_name] = 0

    def increment_ask_count(self, field_name: str) -> int:
        """
        增加字段追问计数

        Args:
            field_name: 字段名

        Returns:
            int: 当前的追问次数
        """
        self.field_ask_count[field_name] = self.field_ask_count.get(field_name, 0) + 1
        return self.field_ask_count[field_name]

    def increment_effective_ask_count(self, field_name: str) -> int:
        """
        增加字段有效询问计数。

        有效询问用于控制主动追问上限，不能被错位回答回退或冷却逻辑冲掉。
        """
        self.effective_field_ask_count[field_name] = self.effective_field_ask_count.get(field_name, 0) + 1
        return self.effective_field_ask_count[field_name]

    def decrement_ask_count(self, field_name: str) -> int:
        """
        回退字段追问计数。

        用于用户首次错位回答时，不把上一轮字段追问视作一次有效覆盖尝试。
        """
        current = self.field_ask_count.get(field_name, 0)
        if current <= 0:
            return 0
        self.field_ask_count[field_name] = current - 1
        return self.field_ask_count[field_name]

    def close_active_ask(self, field_name: str) -> None:
        """
        关闭某个字段的主动追问资格，后续仅允许被动提取。

        Args:
            field_name: 字段名
        """
        if field_name:
            self.active_ask_closed_fields[field_name] = True

    def is_active_ask_closed(self, field_name: str) -> bool:
        """
        判断字段是否已关闭主动追问。

        Args:
            field_name: 字段名

        Returns:
            bool: 是否已关闭主动追问
        """
        return bool(self.active_ask_closed_fields.get(field_name, False))

    def mark_recent_asked_field(self, field_name: str, max_history: int = 10) -> None:
        """
        记录本轮主动追问的主字段，用于短轮次冷却控制。

        Args:
            field_name: 本轮主追问字段
            max_history: 最多保留的历史条数
        """
        if not field_name:
            return
        self.recent_asked_fields.append(field_name)
        if len(self.recent_asked_fields) > max_history:
            self.recent_asked_fields = self.recent_asked_fields[-max_history:]

    def get_cooldown_fields(self, cooldown_turns: int) -> List[str]:
        """
        获取当前仍在冷却窗口内的字段列表。
        """
        turns = max(0, int(cooldown_turns))
        if turns <= 0:
            return []
        return self.recent_asked_fields[-turns:]

    def reset_ask_count(self, field_name: str) -> None:
        """
        重置字段追问计数（字段被成功收集时调用）

        Args:
            field_name: 字段名
        """
        if field_name in self.field_ask_count:
            self.field_ask_count[field_name] = 0
        if field_name in self.effective_field_ask_count:
            self.effective_field_ask_count[field_name] = 0
        self.clear_field_miss_streak(field_name)

    def get_effective_ask_count(self, field_name: str) -> int:
        """
        获取字段有效询问次数。
        """
        return self.effective_field_ask_count.get(field_name, 0)

    def get_ask_count(self, field_name: str) -> int:
        """
        获取字段追问次数

        Args:
            field_name: 字段名

        Returns:
            int: 追问次数
        """
        return self.field_ask_count.get(field_name, 0)

    def mark_field_miss(self, field_name: str) -> int:
        self.field_miss_streak[field_name] = self.field_miss_streak.get(field_name, 0) + 1
        return self.field_miss_streak[field_name]

    def clear_field_miss_streak(self, field_name: str) -> None:
        if field_name in self.field_miss_streak:
            self.field_miss_streak.pop(field_name, None)

    def get_field_miss_streak(self, field_name: str) -> int:
        return self.field_miss_streak.get(field_name, 0)

    def set_resume_profile_target(
        self,
        mode: Optional[str],
        field_name: Optional[str],
        concern_type: Optional[str] = None,
    ) -> None:
        self.resume_profile_mode = mode
        self.resume_profile_target = field_name
        self.last_user_concern_type = concern_type
        self.updated_at = datetime.now()

    def clear_resume_profile_target(self) -> None:
        self.resume_profile_mode = None
        self.resume_profile_target = None
        self.last_user_concern_type = None
        self.updated_at = datetime.now()

    def set_pending_retry_field(self, field_name: Optional[str]) -> None:
        self.pending_retry_field = field_name or None
        self.updated_at = datetime.now()

    def clear_pending_retry_field(self) -> None:
        self.pending_retry_field = None
        self.updated_at = datetime.now()

    def get_fields_asked_multiple_times(self, min_times: int = 2) -> list:
        """
        获取被问过多次但未回答的字段列表

        Args:
            min_times: 最小追问次数

        Returns:
            list: 被问过多次的字段名列表
        """
        result = []
        for field, count in self.effective_field_ask_count.items():
            if count >= min_times:
                # 检查字段是否还未收集且未被跳过
                is_collected = self.collection_progress.get(field, False)
                is_skipped = self.skipped_fields.get(field, False)
                if not is_collected and not is_skipped:
                    result.append((field, count))
        return result

    def mark_non_cooperation(self) -> int:
        self.non_cooperation_turns += 1
        return self.non_cooperation_turns

    def reset_non_cooperation(self) -> None:
        self.non_cooperation_turns = 0

    def mark_off_topic(self) -> int:
        self.off_topic_turns += 1
        return self.off_topic_turns

    def reset_off_topic(self) -> None:
        self.off_topic_turns = 0

    def mark_open_profile_attempt(self) -> int:
        self.open_profile_attempts += 1
        return self.open_profile_attempts

    def reset_open_profile_attempts(self) -> None:
        self.open_profile_attempts = 0

    # === 投诉修复与追问冷却管理 ===

    def enter_repair_mode(self, reason: str, cooldown_turns: int = 3) -> None:
        """
        进入投诉修复模式。

        Args:
            reason: 进入修复模式的原因（repeat_ask/rude_tone/over_questioning）
            cooldown_turns: 冷却轮数（默认3轮）
        """
        self.repair_mode = True
        self.repair_reason = reason
        self.ask_cooldown_turns = cooldown_turns
        # 根据原因设置被禁止的追问意图
        if reason == "repeat_ask":
            self.blocked_ask_intents = [
                "ask_partner_requirement",
                "ask_matching_priority",
                "ask_basic_profile",
            ]
        elif reason == "over_questioning":
            self.blocked_ask_intents = [
                "ask_partner_requirement",
                "ask_matching_priority",
                "ask_basic_profile",
                "ask_contact",
            ]
        else:
            self.blocked_ask_intents = ["ask_partner_requirement", "ask_matching_priority"]
        self.updated_at = datetime.now()

    def decrement_cooldown(self) -> None:
        """
        冷却轮数递减（每轮对话结束时调用）。
        当冷却归零时自动退出修复模式。
        """
        if self.ask_cooldown_turns > 0:
            self.ask_cooldown_turns -= 1
            if self.ask_cooldown_turns == 0:
                self.repair_mode = False
                self.repair_reason = None
                self.blocked_ask_intents = []
        self.updated_at = datetime.now()

    def is_ask_intent_blocked(self, intent: str) -> bool:
        """
        检查某个追问意图是否被禁止。

        Args:
            intent: 追问意图（ask_partner_requirement/ask_matching_priority/ask_basic_profile）

        Returns:
            是否被禁止
        """
        if not self.repair_mode:
            return False
        return intent in self.blocked_ask_intents

    def set_last_asked_field(self, field_name: str, turn_index: int, *, side_field: Optional[str] = None) -> None:
        """
        记录上一轮追问的字段（用于短答槽位绑定）。

        Args:
            field_name: 字段名
            turn_index: 消息序号
            side_field: 顺带追问字段
        """
        self.last_asked_field = field_name
        self.last_asked_side_field = side_field
        self.last_asked_turn_index = turn_index
        self.updated_at = datetime.now()

    def clear_last_asked_field(self) -> None:
        """清除上一轮追问字段记录。"""
        self.last_asked_field = None
        self.last_asked_side_field = None
        self.last_asked_turn_index = None
        self.updated_at = datetime.now()

    def set_last_question_state(self, state: Optional[Dict[str, Any]]) -> None:
        normalized = dict(state or {})
        normalized["asked_fields"] = [
            str(item).strip()
            for item in normalized.get("asked_fields", [])
            if str(item).strip()
        ]
        normalized["side_fields"] = [
            str(item).strip()
            for item in normalized.get("side_fields", [])
            if str(item).strip()
        ]
        expected_scope = str(normalized.get("expected_scope") or "").strip()
        normalized["expected_scope"] = expected_scope or "self"
        normalized["question_intent"] = str(normalized.get("question_intent") or "").strip() or "unknown"
        normalized["resume_target"] = str(normalized.get("resume_target") or "").strip() or None
        normalized["allow_mixed_answer"] = bool(normalized.get("allow_mixed_answer", False))
        self.last_question_state = normalized
        self.updated_at = datetime.now()

    def clear_last_question_state(self) -> None:
        self.last_question_state = {}
        self.updated_at = datetime.now()

    def set_last_semantic_summary(self, summary: Optional[Dict[str, Any]]) -> None:
        normalized = dict(summary or {})
        normalized["acts"] = [
            str(item).strip()
            for item in normalized.get("acts", [])
            if str(item).strip()
        ]
        normalized["user_questions"] = [
            str(item).strip()
            for item in normalized.get("user_questions", [])
            if str(item).strip()
        ]
        normalized["observed_fields"] = [
            str(item).strip()
            for item in normalized.get("observed_fields", [])
            if str(item).strip()
        ]
        normalized["pending_fields"] = [
            str(item).strip()
            for item in normalized.get("pending_fields", [])
            if str(item).strip()
        ]
        normalized["no_reask_fields"] = [
            str(item).strip()
            for item in normalized.get("no_reask_fields", [])
            if str(item).strip()
        ]
        normalized["primary_domain"] = str(normalized.get("primary_domain") or "").strip() or "unknown"
        normalized["resume_target"] = str(normalized.get("resume_target") or "").strip() or None
        normalized["turn_mode"] = str(normalized.get("turn_mode") or "").strip() or "default"
        self.last_semantic_summary = normalized
        self.updated_at = datetime.now()

    def clear_last_semantic_summary(self) -> None:
        self.last_semantic_summary = {}
        self.updated_at = datetime.now()

    def get_expected_field_for_short_answer(self, current_turn_index: int, max_gap: int = 1) -> Optional[str]:
        """
        获取短答应该优先解析的字段。

        如果上一轮明确在问某个字段，且距离当前轮次在 max_gap 内，
        则返回该字段名，用于短答优先解析。

        Args:
            current_turn_index: 当前消息序号
            max_gap: 最大允许的轮次间隔（默认1，即只看上一轮）

        Returns:
            期望的字段名，或 None
        """
        if not self.last_asked_field or self.last_asked_turn_index is None:
            return None
        if current_turn_index - self.last_asked_turn_index > max_gap:
            return None
        return self.last_asked_field

    def get_greeting(self) -> str:
        """
        根据已收集的信息生成合适的称呼

        Returns:
            str: 称呼（优先使用性别称呼"小哥哥"/"小姐姐"，其次考虑姓氏）
        """
        # 称呼规则：
        # 1. 性别称呼为基础（小哥哥/小姐姐）- 这是主要称呼方式
        # 2. last_name（用户提供的昵称）仅作为补充，不替代性别称呼

        if self.sex == '男':
            return "小哥哥"
        elif self.sex == '女':
            return "小姐姐"
        else:
            return "你"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "account_id": self.account_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile_version": self.profile_version,
            "sex": self.sex,
            "last_name": self.last_name,
            "age": self.age,
            "age_label": self.age_label,
            "pending_birth_year_bucket": self.pending_birth_year_bucket,
            "birth_year_confirmation_closed": self.birth_year_confirmation_closed,
            "height": self.height,
            "weight": self.weight,
            "location": self.location,
            "education": self.education,
            "marital_status": self.marital_status,
            "monthly_income": self.monthly_income,
            "occupation": self.occupation,
            "occupation_inference_candidate": self.occupation_inference_candidate,
            "contact": self.contact,
            "phone": self.phone,
            "wechat": self.wechat,
            "partner_requirement": self.partner_requirement,
            "partner_gender_preference": self.partner_gender_preference,
            "partner_pref_location": self.partner_pref_location,
            "partner_pref_age": self.partner_pref_age,
            "partner_pref_industry": self.partner_pref_industry,
            "partner_pref_age_relation": self.partner_pref_age_relation,
            "partner_pref_locality": self.partner_pref_locality,
            "partner_pref_height": self.partner_pref_height,
            "partner_pref_education": self.partner_pref_education,
            "partner_pref_personality": self.partner_pref_personality,
            "partner_pref_income": self.partner_pref_income,
            "partner_pref_other": self.partner_pref_other,
            "extraction_evidence": self.extraction_evidence,
            "collection_progress": self.collection_progress,
            "progress_percentage": round(self.get_progress() * 100, 2),
            "missing_fields": self.get_missing_fields(),
            "skipped_fields": self.skipped_fields,
            "field_ask_count": self.field_ask_count,
            "effective_field_ask_count": self.effective_field_ask_count,
            "recent_asked_fields": self.recent_asked_fields,
            "active_ask_closed_fields": self.active_ask_closed_fields,
            "error_count": self.error_count,
            "conversation_ended": self.conversation_ended,
            "divorce_confirmed": self.divorce_confirmed,
            "divorce_confirmation_pending": self.divorce_confirmation_pending,
            "pending_sex_confirmation": self.pending_sex_confirmation,
            "age_under_limit": self.age_under_limit,
            "lgbt_user": self.lgbt_user,
            "already_married": self.already_married,
            "proxy_user": self.proxy_user,
            "spam_user": self.spam_user,
            # 新字段
            "phone_collected": self.phone_collected,
            "wechat_collected": self.wechat_collected,
            "phone_ask_count": self.phone_ask_count,
            "wechat_ask_count": self.wechat_ask_count,
            "last_contact_request_type": self.last_contact_request_type,
            "is_hongkong_user": self.is_hongkong_user,
            "resume_profile_mode": self.resume_profile_mode,
            "resume_profile_target": self.resume_profile_target,
            "last_user_concern_type": self.last_user_concern_type,
            "field_miss_streak": self.field_miss_streak,
            "last_effective_progress": self.last_effective_progress,
            "last_asked_field": self.last_asked_field,
            "last_asked_side_field": self.last_asked_side_field,
            "last_asked_turn_index": self.last_asked_turn_index,
            "last_question_state": self.last_question_state,
            "last_semantic_summary": self.last_semantic_summary,
            "pending_retry_field": self.pending_retry_field,
            "needs_bridge_back": self.needs_bridge_back,
            "last_side_topic_type": self.last_side_topic_type,
            "complaint_cooldown_until": self.complaint_cooldown_until,
            "recent_semantic_slots": self.recent_semantic_slots,
            "recent_response_openings": self.recent_response_openings,
            "repair_mode": self.repair_mode,
            "repair_reason": self.repair_reason,
            "ask_cooldown_turns": self.ask_cooldown_turns,
            "blocked_ask_intents": self.blocked_ask_intents,
            "non_cooperation_turns": self.non_cooperation_turns,
            "off_topic_turns": self.off_topic_turns,
            "open_profile_attempts": self.open_profile_attempts,
            "last_engagement_mode": self.last_engagement_mode,
            # 兼容旧字段
            "rejected_wechat": self.rejected_wechat,
            "rejected_phone": self.rejected_phone,
        }

    def set_extraction_evidence(
        self,
        field_name: str,
        value: Any,
        source_text: str,
        turn_id: Optional[int],
        confidence: float,
        source: str,
        reason: Optional[str] = None,
    ) -> None:
        """记录字段提取证据，便于回溯与评估融合质量。"""
        safe_confidence = max(0.0, min(1.0, float(confidence)))
        self.extraction_evidence[field_name] = {
            "value": value,
            "source_text": (source_text or "")[:200],
            "turn_id": turn_id,
            "confidence": round(safe_confidence, 3),
            "source": source or "unknown",
            "reason": str(reason or "").strip() or None,
            "updated_at": datetime.now().isoformat(),
        }
        self.updated_at = datetime.now()

    def get_collection_summary(self) -> str:
        """
        获取收集进度的自然语言描述

        Returns:
            str: 收集进度描述
        """
        progress = self.get_progress()
        if progress == 1.0:
            return "所有信息已收集完成啦～"
        elif progress >= 0.7:
            missing = ", ".join(self.get_missing_fields()[:2])
            return f"就差一点点啦~ 还需要{missing}"
        elif progress >= 0.5:
            missing = ", ".join(self.get_missing_fields()[:2])
            return f"嗯嗯，还需要了解{missing}"
        else:
            return "刚认识你，想多了解一些基本信息呀～"

    def get_contact_status(self) -> str:
        """
        获取联系方式状态显示

        Returns:
            str: 状态字符串
        """
        # 获取各状态
        phone = self.phone
        wechat = self.wechat
        phone_collected = self.phone_collected
        wechat_collected = self.wechat_collected
        rejected_phone = self.rejected_phone
        rejected_wechat = self.rejected_wechat

        # 判断是否正在询问（询问次数 > 0 且未收集且未拒绝）
        phone_asking = self.phone_ask_count > 0 and not phone_collected and not rejected_phone
        wechat_asking = self.wechat_ask_count > 0 and not wechat_collected and not rejected_wechat

        # 构建状态列表
        phone_status = None
        wechat_status = None

        # 电话状态
        if phone_collected and phone:
            phone_status = f"电话: {phone}"
        elif rejected_phone:
            phone_status = "不愿留电话"
        elif phone_asking:
            phone_status = "电话争取中"

        # 微信状态
        if wechat_collected and wechat:
            wechat_status = f"微信: {wechat}"
        elif rejected_wechat:
            wechat_status = "不愿留微信"
        elif wechat_asking:
            wechat_status = "微信争取中"

        # 组合状态
        if phone_status and wechat_status:
            return f"{phone_status}, {wechat_status}"
        elif phone_status:
            return phone_status
        elif wechat_status:
            return wechat_status
        else:
            return "未留"

    def check_is_hongkong_user(self) -> bool:
        """
        检查是否是香港用户（根据 location 字段判断）

        Returns:
            bool: 是否是香港用户
        """
        if self.is_hongkong_user is not None:
            return self.is_hongkong_user

        if not self.location:
            return False

        location_lower = self.location.lower()
        self.is_hongkong_user = '香港' in location_lower or 'hk' in location_lower
        return self.is_hongkong_user

    def can_ask_phone(self) -> bool:
        """
        判断是否可以询问电话

        Returns:
            bool: 是否可以询问
        """
        # 已收集或已拒绝，不能再问
        if self.phone_collected or self.rejected_phone:
            return False

        # 香港用户最多2次
        if self.check_is_hongkong_user():
            return self.phone_ask_count < 2

        # 非香港用户最多2次
        return self.phone_ask_count < 2

    def can_ask_wechat(self) -> bool:
        """
        判断是否可以询问微信

        Returns:
            bool: 是否可以询问
        """
        # 已收集或已拒绝，不能再问
        if self.wechat_collected or self.rejected_wechat:
            return False

        is_hong = self.check_is_hongkong_user()

        # 香港用户最多2次
        if is_hong:
            return self.wechat_ask_count < 2

        # 非香港用户：电话已收集最多1次，电话未收集最多2次
        if self.phone_collected:
            return self.wechat_ask_count < 1
        else:
            return self.wechat_ask_count < 2

    def get_max_wechat_asks(self) -> int:
        """
        获取微信最大询问次数

        Returns:
            int: 最大询问次数
        """
        is_hong = self.check_is_hongkong_user()

        # 香港用户：最多2次
        if is_hong:
            return 2

        # 非香港用户：电话已收集最多1次，电话未收集最多2次
        if self.phone_collected:
            return 1
        else:
            return 2

    def increment_phone_ask_count(self) -> int:
        """
        增加电话询问次数

        Returns:
            int: 当前询问次数
        """
        self.phone_ask_count += 1
        return self.phone_ask_count

    def increment_wechat_ask_count(self) -> int:
        """
        增加微信询问次数

        Returns:
            int: 当前询问次数
        """
        self.wechat_ask_count += 1
        return self.wechat_ask_count
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典创建 UserProfile"""
        # 处理日期字段
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    @staticmethod
    def _normalize_occupation_value_for_candidate(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        text = re.sub(r"[，,、。！？!?~～\s]+", "", text)
        text = re.sub(r"(行业|相关|类工作|工作方向|方向)$", "", text)
        return text or None
