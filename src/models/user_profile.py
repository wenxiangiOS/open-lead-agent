"""User profile model for collecting personal information"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class UserProfile(BaseModel):
    """
    用户个人信息模型

    收集字段（按优先级）：
    1. 性别 - 男/女（首要）
    2. 出生年 - 哪一年出生的
    3. 身高体重 - 例如：165cm/55kg
    4. 坐标 - 所在城市/地区
    5. 学历 - 高中/大专/本科/硕士/博士
    6. 婚况 - 单身/离异
    7. 月薪 - 月收入大概多少
    8. 职业 - 做什么工作
    9. 称呼 - 对方希望怎么称呼自己
    10. 电话/微信 - 联系方式
    """

    # 基本信息
    account_id: str = Field(..., description="用户账号ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 待收集的信息（初始为 None）- 按优先级顺序
    sex: Optional[str] = Field(None, description="性别（男/女）- 首要收集")
    last_name: Optional[str] = Field(None, description="姓氏（对方希望怎么称呼自己）")
    age: Optional[int] = Field(None, description="年龄（数字）")
    height: Optional[str] = Field(None, description="身高（例如：165cm）")
    weight: Optional[str] = Field(None, description="体重（例如：55kg）")
    location: Optional[str] = Field(None, description="坐标/所在地（城市/地区）")
    education: Optional[str] = Field(None, description="学历（高中/大专/本科/硕士/博士）")
    marital_status: Optional[str] = Field(None, description="婚况（单身/离异）")
    monthly_income: Optional[str] = Field(None, description="月薪（月收入范围）")
    occupation: Optional[str] = Field(None, description="职业（做什么工作）")
    contact: Optional[str] = Field(None, description="联系方式（电话/微信）")

    # 收集状态跟踪
    collection_progress: Dict[str, bool] = Field(
        default_factory=lambda: {
            "sex": False,
            "last_name": False,
            "age": False,
            "height": False,
            "weight": False,
            "location": False,
            "education": False,
            "marital_status": False,
            "monthly_income": False,
            "occupation": False,
            "contact": False,
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

    @validator('sex')
    def validate_sex(cls, v):
        """验证性别字段"""
        if v is not None:
            v = str(v).strip()
            if v in ['男', '男宝', '男生的', '帅哥', '小哥哥', '哥哥', '先生', 'M', 'm']:
                return '男'
            elif v in ['女', '女宝', '女生的', '美女', '小姐姐', '妹妹', '女士', 'F', 'f']:
                return '女'
        return v

    @validator('contact')
    def validate_contact(cls, v):
        """验证联系方式（电话号码）"""
        if v is not None:
            v = str(v).strip()
            # 移除非数字字符
            cleaned = ''.join(c for c in v if c.isdigit())
            # 中国手机号验证
            if len(cleaned) == 11 and cleaned.startswith('1'):
                return cleaned
        return v

    @validator('age')
    def validate_age(cls, v):
        """验证年龄"""
        if v is not None:
            if isinstance(v, str):
                v = str(v).strip()
                # 提取数字（支持"28岁"格式）
                import re
                match = re.search(r'(\d+)', v)
                if match:
                    v = int(match.group(1))
                else:
                    return None
            if 18 <= v <= 100:
                return v
        return v

    @validator('height')
    def validate_height(cls, v):
        """验证身高"""
        if v is not None:
            v = str(v).strip()
            # 提取数字
            import re
            match = re.search(r'(\d+)', v)
            if match:
                height_val = int(match.group(1))
                if 140 <= height_val <= 220:
                    return f"{height_val}cm"
        return v

    @validator('weight')
    def validate_weight(cls, v):
        """验证体重"""
        if v is not None:
            v = str(v).strip()
            # 提取数字
            import re
            match = re.search(r'(\d+)', v)
            if match:
                weight_val = int(match.group(1))
                if 30 <= weight_val <= 200:
                    return f"{weight_val}kg"
        return v

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
            if field_name == 'contact':
                validated = self.validate_contact(value)
            elif field_name == 'sex':
                validated = self.validate_sex(value)
            elif field_name == 'age':
                validated = self.validate_age(value)
            elif field_name == 'height':
                validated = self.validate_height(value)
            elif field_name == 'weight':
                validated = self.validate_weight(value)
            elif field_name == 'last_name':
                # 姓氏字段直接使用提取的值，不经过额外验证
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
                self.updated_at = datetime.now()
                return True

        except Exception as e:
            # 记录错误但不更新
            self.error_count[field_name] = self.error_count.get(field_name, 0) + 1
            return False

        return False

    def get_progress(self) -> float:
        """
        获取收集进度（百分比）

        跳过的字段视为已完成，计入进度

        Returns:
            float: 收集进度 0.0 - 1.0
        """
        completed = sum(1 for status in self.collection_progress.values() if status)
        skipped = len(self.skipped_fields)
        total = len(self.collection_progress)
        return (completed + skipped) / total if total > 0 else 0.0

    def is_collection_complete(self) -> bool:
        """
        检查信息收集是否完成

        Returns:
            bool: 是否已完成收集（进度 >= 90%）
        """
        return self.get_progress() >= 0.9

    def is_empty(self) -> bool:
        """
        检查用户档案是否为空（全新用户）

        Returns:
            bool: 是否为空（所有关键字段都是 None）
        """
        # 检查所有关键字段是否都为空
        key_fields = ['sex', 'last_name', 'age', 'height', 'weight',
                      'location', 'education', 'marital_status',
                      'monthly_income', 'occupation', 'contact']
        return all(getattr(self, field) is None for field in key_fields)

    def get_missing_fields(self) -> list:
        """
        获取未收集的字段

        不包括已跳过的字段

        Returns:
            list: 未收集的字段名列表
        """
        return [
            field for field, collected in self.collection_progress.items()
            if not collected and field not in self.skipped_fields
        ]

    def get_next_field_to_collect(self) -> Optional[str]:
        """
        获取下一个需要收集的字段

        按照收集优先级顺序返回未收集的字段
        跳过已被用户拒绝提供的字段

        Returns:
            Optional[str]: 下一个要收集的字段名
        """
        # 新的优先级顺序：姓氏优先
        priority_order = [
            'sex',  # 性别 - 首要
            'last_name',  # 姓氏 - 对方希望怎么称呼
            'age',  # 年龄
            'height',  # 身高
            'weight',  # 体重
            'location',  # 坐标
            'education',  # 学历
            'marital_status',  # 婚况
            'monthly_income',  # 月薪
            'occupation',  # 职业
            'contact',  # 联系方式
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
            "height": self.height,
            "weight": self.weight,
            "location": self.location,
            "education": self.education,
            "marital_status": self.marital_status,
            "monthly_income": self.monthly_income,
            "occupation": self.occupation,
            "contact": self.contact,
            "collection_progress": self.collection_progress,
            "progress_percentage": round(self.get_progress() * 100, 2),
            "missing_fields": self.get_missing_fields(),
            "skipped_fields": self.skipped_fields,
        }

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
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典创建 UserProfile"""
        # 处理日期字段
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)
