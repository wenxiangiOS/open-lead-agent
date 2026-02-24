"""
信息提取服务

负责从 AI 回复和用户消息中提取结构化数据
"""

import logging
import re
from typing import Dict, Any, List, Optional
from src.models.user_profile import UserProfile
from src.services.user_service import UserService

logger = logging.getLogger(__name__)


class ExtractionService:
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
        "婚况": "marital_status",
        "联系方式": "contact",
        "择偶要求": "partner_requirement",
        "择偶": "partner_requirement",
        "要求": "partner_requirement",
        # 英文字段名（直接映射）
        "last_name": "last_name",
        "sex": "sex",
        "location": "location",
        "age": "age",
        "height": "height",
        "weight": "weight",
        "education": "education",
        "occupation": "occupation",
        "monthly_income": "monthly_income",
        "marital_status": "marital_status",
        "contact": "contact",
        "partner_requirement": "partner_requirement",
        # 带空格的字段名（AI 可能返回）
        " 职业": "occupation",
        " 学历": "education",
        " 身高": "height",
        " 体重": "weight",
        " 月收入": "monthly_income",
        " 婚况": "marital_status",
        " 联系方式": "contact",
        " 择偶要求": "partner_requirement",
    }

    # 无效名称列表
    INVALID_NAMES = {'小姐姐', '小哥哥', '你好呀', '你好呢', '你好', '哈喽', '嗨', '呀', '呢', '哒', '哦', '哈'}

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

        # 1. 优先匹配 <extract>...</extract> XML 标签格式
        extract_pattern = r'<extract>\s*\n?(.*?)\n?</extract>'
        match = re.search(extract_pattern, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 调试：显示原始内容（限制长度）
            logger.info(f"[提取原始] {repr(content[:100])}")
            extracted = self._parse_extract_content(content)
            if extracted:
                # 简化日志：只显示提取到的非空字段
                non_empty = {k: v for k, v in extracted.items() if v not in [None, '', 'null']}
                logger.info(f"[提取] {non_empty}")
                return extracted

        # 2. 尝试匹配 ```json...``` 代码块格式
        json_pattern = r'```json\s*\n?(.*?)\n?```'
        match = re.search(json_pattern, response, re.DOTALL)
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
        - field:value 格式（多行，支持 /n 和 \n 换行）

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

        # 尝试 field:value 格式解析（支持多行）
        result = {}
        # 支持 /n 和 \n 作为换行符
        content = content.replace('/n', '\n')
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 匹配 field:value 格式
            match = re.match(r'^([^:]+)\s*:\s*(.+)$', line)
            if match:
                field, value = match.groups()
                # 清理值中的引号
                value = value.strip().strip('"')
                # 如果值是 "null"，转换为 None
                if value == 'null':
                    value = None
                # 清理值末尾的 /n 或 \n（仅当 value 不为 None 时）
                if value is not None:
                    value = value.rstrip('/n').rstrip('\n').strip()
                result[field] = value

        return result

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
        extracted_data: Dict[str, Any]
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

        if not extracted_data:
            return {
                "collected": False,
                "all_fields": []
            }

        # 遍历提取结果，更新用户档案
        for field_name, value in extracted_data.items():
            if value is not None and value != "" and value != "null":
                # 清理字段名（去除前后空格）
                clean_field_name = field_name.strip()
                # 字段名映射：中文字段名 -> 英文字段名
                mapped_field = self.FIELD_MAPPING.get(clean_field_name, clean_field_name)

                # 检查是否为无效值
                if mapped_field == "last_name":
                    if value in self.INVALID_NAMES or len(value) <= 1:
                        continue

                # 检查字段是否需要更新
                is_collected = user_profile.collection_progress.get(mapped_field, False)
                current_value = getattr(user_profile, mapped_field, None)
                needs_update = not is_collected or (current_value != value)

                if needs_update:
                    success = await self.user_service.update_user_profile_field(
                        account_id, mapped_field, value
                    )
                    if success:
                        collected_fields.append({"field": mapped_field, "value": value})

        # 更新 profile
        user_profile = await self.user_service.get_user_profile(account_id)

        if collected_fields:
            return {
                "collected": True,
                "field": collected_fields[0]["field"] if collected_fields else None,
                "value": collected_fields[0]["value"] if collected_fields else None,
                "all_fields": collected_fields
            }

        return {
            "collected": False,
            "all_fields": []
        }

    def get_collected_info_summary(self, user_profile: UserProfile) -> str:
        """
        获取已收集信息的摘要

        使用压缩格式节省 token

        Args:
            user_profile: 用户档案

        Returns:
            str: 已收集信息摘要
        """
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
            parts.append(f"{user_profile.age}岁({birth_year}年)")
        if user_profile.education:
            parts.append(str(user_profile.education))
        if user_profile.occupation:
            parts.append(str(user_profile.occupation))
        if user_profile.height:
            parts.append(str(user_profile.height))
        if user_profile.weight:
            parts.append(str(user_profile.weight))
        if user_profile.monthly_income:
            parts.append(str(user_profile.monthly_income))
        if user_profile.marital_status:
            parts.append(str(user_profile.marital_status))

        if parts:
            # 检查是否已收集联系方式（信息收集完成的标志）
            # 只检查 contact 字段是否有值，不依赖 collection_progress
            if user_profile.contact and user_profile.contact != "":
                parts.append("已留联系")
                # 确保 collection_progress 也被标记（用于 is_collection_complete()）
                if not user_profile.collection_progress.get('contact', False):
                    user_profile.collection_progress['contact'] = True
            # 添加择偶要求（如果有）
            if user_profile.partner_requirement:
                parts.append(f"要求:{user_profile.partner_requirement}")
            return "【已收集】" + ",".join(parts)
        return "【已收集】无"

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
