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

    # 待收集的信息（初始为 None）
    sex: Optional[str] = Field(None, description="性别（男/女）- 核心字段")
    last_name: Optional[str] = Field(None, description="用户主动提供的称呼/昵称（低优字段）")
    age: Optional[int] = Field(None, description="年龄（数字）")
    age_label: Optional[str] = Field(None, description="年龄原始表达（如90后、95后）")
    extraction_evidence: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="字段提取证据链：value/source_text/turn_id/confidence/source"
    )
    height: Optional[str] = Field(None, description="身高（低优字段，例如：165cm）")
    weight: Optional[str] = Field(None, description="体重（低优字段，例如：55kg）")
    location: Optional[str] = Field(None, description="工作地/所在地（城市/地区）")
    education: Optional[str] = Field(None, description="学历（核心字段）")
    marital_status: Optional[str] = Field(None, description="婚况（准核心字段）")
    monthly_income: Optional[str] = Field(None, description="月薪（月收入范围，中等字段）")
    occupation: Optional[str] = Field(None, description="职业（核心字段）")
    contact: Optional[str] = Field(None, description="联系方式状态显示（核心字段）")
    phone: Optional[str] = Field(None, description="电话号码（单独存储）")
    wechat: Optional[str] = Field(None, description="微信号")
    partner_requirement: Optional[str] = Field(None, description="择偶要求（中等字段）")

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
    recent_asked_fields: List[str] = Field(
        default_factory=list,
        description="最近被 AI 主动追问的字段历史（按轮次）"
    )

    # 联系方式收集状态（新设计）
    phone_collected: bool = Field(default=False, description="电话是否已收集")
    wechat_collected: bool = Field(default=False, description="微信是否已收集")
    phone_ask_count: int = Field(default=0, description="电话询问次数（0-2）")
    wechat_ask_count: int = Field(default=0, description="微信询问次数（0-2）")
    is_hongkong_user: Optional[bool] = Field(default=None, description="是否是香港用户（缓存）")

    # 联系方式拒绝状态（兼容旧字段，逐步迁移）
    rejected_wechat: bool = Field(default=False, description="用户是否拒绝微信")
    rejected_phone: bool = Field(default=False, description="用户是否拒绝电话")

    # 对话状态
    conversation_ended: bool = Field(default=False, description="对话是否已结束")
    divorce_confirmed: bool = Field(default=False, description="离异手续是否已确认办妥")
    age_under_limit: bool = Field(default=False, description="年龄是否低于服务限制（24岁以下）")
    lgbt_user: bool = Field(default=False, description="是否是LGBT用户（同性恋/百合）")
    already_married: bool = Field(default=False, description="用户是否已婚")
    proxy_user: bool = Field(default=False, description="是否是代相亲（帮别人问）")
    spam_user: bool = Field(default=False, description="是否是骚扰/广告用户")

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
                    birth_year_match = re.search(r'^(19\d{2}|20\d{2})年?$', value_str)
                    if birth_year_match:
                        birth_year = int(birth_year_match.group(1))
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
                # 择偶要求字段：追加而不是覆盖，但要避免重复
                existing = getattr(self, 'partner_requirement', None)
                if existing and existing != "":
                    # 拆分现有值和新值，只添加不存在的部分
                    existing_items = [item.strip() for item in existing.split(',')]
                    new_items = [item.strip() for item in value.split(',')]

                    # 只添加现有值中没有的部分
                    items_to_add = []
                    for item in new_items:
                        if item and item not in existing_items:
                            items_to_add.append(item)

                    if items_to_add:
                        validated = f"{existing},{','.join(items_to_add)}"
                    else:
                        validated = existing  # 所有内容都已存在，不更新
                else:
                    validated = value
            else:
                validated = value

            # 只有值不为 None 时才更新
            if validated is not None and validated != "":
                # 调试：检查 last_name 是否被设置为拼接字符串
                if field_name == 'last_name' and '/' in str(validated):
                    import logging
                    logging.getLogger(__name__).warning(f"last_name 被设置为拼接字符串: {validated}")
                setattr(self, field_name, validated)
                self.collection_progress[field_name] = True
                # 字段成功收集后，重置追问计数
                self.reset_ask_count(field_name)

                # 特殊处理：phone 和 wechat 字段收集成功后更新状态
                if field_name == 'phone':
                    self.phone_collected = True
                    # 同时更新 contact 字段为状态显示
                    self.contact = self.get_contact_status()
                elif field_name == 'wechat':
                    self.wechat_collected = True
                    # 同时更新 contact 字段为状态显示
                    self.contact = self.get_contact_status()

                self.updated_at = datetime.now()
                return True

        except Exception as e:
            # 记录错误但不更新
            self.error_count[field_name] = self.error_count.get(field_name, 0) + 1
            return False

        return False

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
                      'monthly_income', 'occupation', 'contact', 'partner_requirement']
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
        # 当前策略顺序：核心 -> 准核心 -> 中等 -> 低优
        priority_order = [
            'sex',
            'age',
            'location',
            'education',
            'occupation',
            'marital_status',
            'contact',
            'monthly_income',
            'partner_requirement',
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

    def get_ask_count(self, field_name: str) -> int:
        """
        获取字段追问次数

        Args:
            field_name: 字段名

        Returns:
            int: 追问次数
        """
        return self.field_ask_count.get(field_name, 0)

    def get_fields_asked_multiple_times(self, min_times: int = 2) -> list:
        """
        获取被问过多次但未回答的字段列表

        Args:
            min_times: 最小追问次数

        Returns:
            list: 被问过多次的字段名列表
        """
        result = []
        for field, count in self.field_ask_count.items():
            if count >= min_times:
                # 检查字段是否还未收集且未被跳过
                is_collected = self.collection_progress.get(field, False)
                is_skipped = self.skipped_fields.get(field, False)
                if not is_collected and not is_skipped:
                    result.append((field, count))
        return result

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
            "sex": self.sex,
            "last_name": self.last_name,
            "age": self.age,
            "age_label": self.age_label,
            "height": self.height,
            "weight": self.weight,
            "location": self.location,
            "education": self.education,
            "marital_status": self.marital_status,
            "monthly_income": self.monthly_income,
            "occupation": self.occupation,
            "contact": self.contact,
            "phone": self.phone,
            "wechat": self.wechat,
            "partner_requirement": self.partner_requirement,
            "extraction_evidence": self.extraction_evidence,
            "collection_progress": self.collection_progress,
            "progress_percentage": round(self.get_progress() * 100, 2),
            "missing_fields": self.get_missing_fields(),
            "skipped_fields": self.skipped_fields,
            "field_ask_count": self.field_ask_count,
            "recent_asked_fields": self.recent_asked_fields,
            "error_count": self.error_count,
            "conversation_ended": self.conversation_ended,
            "divorce_confirmed": self.divorce_confirmed,
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
            "is_hongkong_user": self.is_hongkong_user,
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
    ) -> None:
        """记录字段提取证据，便于回溯与评估融合质量。"""
        safe_confidence = max(0.0, min(1.0, float(confidence)))
        self.extraction_evidence[field_name] = {
            "value": value,
            "source_text": (source_text or "")[:200],
            "turn_id": turn_id,
            "confidence": round(safe_confidence, 3),
            "source": source or "unknown",
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
