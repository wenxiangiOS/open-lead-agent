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

    @staticmethod
    def _is_effectively_same_value(current_value: Any, new_value: Any) -> bool:
        """宽松等价比较，避免仅因格式差异触发重写。"""
        current = "" if current_value is None else str(current_value).strip()
        new = "" if new_value is None else str(new_value).strip()
        if not current and not new:
            return True
        return current == new

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
            "location": r"(我在|我住在|我现在在|我在.*(工作|生活)|我是.*的)",
            "education": r"(我是|学历|读到|本科|大专|硕士|博士|研究生)",
            "occupation": r"(我是|我做|从事|职业是|工作是|做.*工作)",
            "marital_status": r"(我是|目前|现在).*(单身|未婚|离异|已婚|分居)",
        }
        pattern = explicit_patterns.get(field)
        return bool(pattern and re.search(pattern, text))

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

        # 3. 尝试匹配出生年份（支持“1998”或“1998年”）
        match = re.search(r'^(19\d{2}|20\d{2})年?$', value_str)
        if match:
            birth_year = int(match.group(1))
            from datetime import datetime
            current_year = datetime.now().year
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

        return None

    @staticmethod
    def _extract_partner_requirement_from_user_message(user_message: str) -> Optional[str]:
        """从用户原话中保守提取择偶要求，优先保留否定语义，避免模型反转。"""
        message = str(user_message or "").strip()
        if not message:
            return None

        values: List[str] = []
        patterns = [
            r"(年龄不超过\d{1,2}岁)",
            r"(不超过\d{1,2}岁)",
            r"(\d{1,2}岁以下)",
            r"(年龄至少\d{1,3})",
            r"(身高至少\d{2,3})",
            r"(身高不低于\d{2,3})",
            r"(至少\d{2,3})",
            r"(温柔(?:一点|些)?(?:的)?)",
            r"(气质(?:好|佳)?(?:一点|些)?(?:的)?)",
            r"(同城优先)",
            r"(成熟稳重)",
            r"(三观合拍)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, message)
            for matched in matches:
                cleaned = str(matched).strip("，,。；; ")
                if cleaned and cleaned not in values:
                    values.append(cleaned)

        if not values:
            return None

        normalized: List[str] = []
        for value in values:
            value = re.sub(r"^不超过(\d{1,2})岁$", r"年龄不超过\1岁", value)
            value = re.sub(r"^(\d{1,2})岁以下$", r"年龄不超过\1岁", value)
            value = re.sub(r"^至少(\d{2,3})$", r"身高至少\1", value)
            value = re.sub(r"(温柔)(一点|些)?(?:的)?$", r"\1", value)
            value = re.sub(r"(气质)(好|佳)?(一点|些)?(?:的)?$", r"\1", value)
            if value not in normalized:
                normalized.append(value)

        preference_match = re.search(
            r"(?:看中|看重|更看重|比较看重|喜欢|偏向|希望).{0,8}(?:对方|另一半)?(.{0,8}气质)",
            message,
        )
        if preference_match:
            preference_value = preference_match.group(1).strip("，,。；; ")
            preference_value = re.sub(r"^(对方|另一半)", "", preference_value)
            preference_value = re.sub(r"(吧|呀|呢|啊)$", "", preference_value).strip()
            if preference_value and preference_value not in normalized:
                normalized.append(preference_value)

        return "，".join(normalized)

    @staticmethod
    def _looks_like_partner_requirement_content(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        return bool(re.search(r"(对方|另一半|气质|眼缘|感觉|性格|成熟稳重|三观)", text))

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
                        wechat_candidate = raw_contact.replace("微信", "").replace("wx:", "").replace("WX:", "").strip()
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

                # 年龄限制检查：用户必须年满24岁
                if mapped_field == "age":
                    parsed_age = self._parse_age(value)
                    age_label = self._extract_age_label(value) or self._extract_age_label(user_message)
                    if parsed_age is not None and parsed_age < 24:
                        logger.info(f"[年龄限制] 用户年龄 {parsed_age} 岁低于24岁，不符合服务条件")
                        # 设置年龄限制标志
                        user_profile.age_under_limit = True
                        user_profile.age = parsed_age
                        if age_label:
                            user_profile.age_label = age_label
                        await self.user_service.save_user_profile(account_id, user_profile)
                        user_profile.set_extraction_evidence(
                            "age",
                            parsed_age,
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
                            "value": parsed_age,
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
                    explicit_self_sex = re.search(
                        r"(我是|本人|我)\s*(男生|女生|男的|女的|男|女)",
                        user_message or "",
                    ) or re.search(
                        r"^\s*(男生|女生|男的|女的|男|女)\s*(呀|呢|哈|哦|啊)?\s*$",
                        user_message or "",
                    )
                    if not explicit_self_sex:
                        logger.info("[提取保护] sex 仅允许用户自述写入，本轮跳过 sex 更新")
                        continue

                if mapped_field == "occupation":
                    explicit_self_occupation = self._has_explicit_self_update_signal("occupation", user_message)
                    has_preference_signal = bool(self._extract_partner_requirement_from_user_message(user_message))
                    if not explicit_self_occupation and (
                        has_preference_signal or self._looks_like_partner_requirement_content(value)
                    ):
                        logger.info("[提取保护] occupation 命中择偶偏好语境，本轮跳过职业更新")
                        continue

                is_collected = user_profile.collection_progress.get(mapped_field, False)
                current_value = getattr(user_profile, mapped_field, None)

                # 特殊处理：择偶要求字段需要累积而不是覆盖
                if mapped_field == "partner_requirement":
                    user_message_preferred_value = self._extract_partner_requirement_from_user_message(user_message)
                    if user_message_preferred_value:
                        value = user_message_preferred_value

                    # 有价值的内容关键词（即使包含结束信号，也要收集这些内容）
                    valuable_keywords = ['看感觉', '随缘', '看眼缘', '看缘分', '顺其自然', '都可以', '不限']

                    # 检查是否包含有价值的内容
                    has_valuable_content = any(kw in value for kw in valuable_keywords)

                    # 如果包含有价值内容，提取有价值部分
                    if has_valuable_content:
                        # 提取有价值的关键词
                        extracted_values = [kw for kw in valuable_keywords if kw in value]
                        if extracted_values:
                            value = '、'.join(extracted_values)
                            logger.debug(f"[择偶要求] 提取有价值内容: {value}")
                    else:
                        # 没有有价值内容，检查是否是"没有特别要求"的表达
                        no_requirement_signals = ['没有', '没有了', '没', '无', '无特别要求', '没要求', '没特别', '暂时没有', '就这些']
                        # 检查是否完全匹配"没有要求"的意思
                        value_stripped = value.strip()
                        if value_stripped in no_requirement_signals or any(value_stripped == sig for sig in no_requirement_signals):
                            # 用户明确表示没有特别要求，设置为"无特别要求"
                            # 注意：这是第一次说"没有"时，需要设置值
                            if not current_value:
                                value = "无特别要求"
                                logger.debug(f"[择偶要求] 设置为'无特别要求'")
                            else:
                                # 已经有值了，用户说"没有"表示没有其他补充，保持原值
                                logger.debug(f"[择偶要求] 无补充，保持原值")
                                continue

                    if current_value:
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

                if (
                    mapped_field in self._STABLE_PROFILE_FIELDS
                    and is_collected
                    and current_value
                    and not self._is_effectively_same_value(current_value, value)
                    and not self._has_explicit_self_update_signal(mapped_field, user_message)
                ):
                    logger.info(
                        f"[字段稳定保护] 跳过 {mapped_field} 改写: current={current_value}, new={value}"
                    )
                    continue

                needs_update = not is_collected or (not self._is_effectively_same_value(current_value, value))

                if needs_update:
                    success = await self.user_service.update_user_profile_field(
                        account_id, mapped_field, value
                    )
                    if success:
                        collected_fields.append({"field": mapped_field, "value": value})
                        collected_field_names.append(mapped_field)
                        if mapped_field == "age":
                            age_label = self._extract_age_label(value) or self._extract_age_label(user_message)
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
            'monthly_income': '月收入',
            'marital_status': '婚况',
            'contact': '联系方式',
            'phone': '电话',
            'wechat': '微信',
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
            # 添加择偶要求（如果有）- 在联系方式之前
            if user_profile.partner_requirement:
                parts.append(f"要求:{user_profile.partner_requirement}")

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
