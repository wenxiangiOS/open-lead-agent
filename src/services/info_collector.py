"""Information collector for extracting user data from conversations"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class InfoCollector:
    """
    信息收集器 - 从对话中隐晦地提取用户信息

    特点：
    1. 隐晦式收集 - 不直接询问，通过对话自然带出
    2. 智能容错 - 错误提醒有次数限制
    3. 上下文感知 - 根据对话历史判断是否继续收集
    4. 性别识别优先 - 利用目标对象反推用户性别
    """

    # 字段名称到中文的映射
    FIELD_NAMES = {
        'sex': '性别',
        'birth_year': '出生年',
        'height': '身高',
        'weight': '体重',
        'location': '坐标',
        'education': '学历',
        'marital_status': '婚况',
        'monthly_income': '月薪',
        'occupation': '职业',
        'preferred_call': '称呼',
        'contact': '联系方式',
    }

    # 常见城市
    CITIES = [
        '北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安',
        '天津', '苏州', '长沙', '郑州', '青岛', '大连', '宁波', '厦门', '福州',
        '济南', '石家庄', '长春', '哈尔滨', '沈阳', '南昌', '合肥', '昆明',
        '贵阳', '南宁', '海口', '兰州', '西宁', '银川', '呼和浩特', '乌鲁木齐',
        '拉萨', '太原', '台北', '香港', '澳门'
    ]

    # 婚姻状况关键词
    MARITAL_KEYWORDS = {
        '单身': ['单身', '未婚', '没结婚', '没对象', '还单身', '一个人'],
        '离异': ['离异', '离婚', '分开了', '单身很久了']
    }

    # 学历关键词
    EDUCATION_KEYWORDS = {
        '高中': ['高中', '中专', '技校'],
        '大专': ['大专', '职业学院'],
        '本科': ['本科', '大学', '学士', '211', '985'],
        '硕士': ['硕士', '研究生'],
        '博士': ['博士', '博后']
    }

    # 职业关键词（用于对话理解）
    OCCUPATION_KEYWORDS = {
        'IT': ['程序员', '工程师', '开发', 'IT', '技术', '产品经理', '运营', '测试'],
        '金融': ['金融', '银行', '证券', '保险', '投资', '会计', '审计'],
        '教育': ['老师', '教育', '培训', '教练'],
        '医疗': ['医生', '护士', '医疗', '药剂师'],
        '销售': ['销售', '业务', '市场', '推广'],
        '服务': ['服务员', '客服', '导购'],
        '公务员': ['公务员', '事业单位', '机关', '政府'],
        '自由职业': ['自由职业', '个体', '创业', '老板', '自己做'],
        '学生': ['学生', '在读', '上学', '大四', '大三']
    }

    def __init__(self):
        """初始化信息收集器"""
        self.collection_state: Dict[str, Dict[str, Any]] = {}
        # 每个字段跟踪：错误次数、尝试次数、上次提醒时间

    def _init_field_state(self, account_id: str, field_name: str) -> None:
        """初始化字段状态"""
        key = f"{account_id}_{field_name}"
        if key not in self.collection_state:
            self.collection_state[key] = {
                'error_count': 0,
                'attempt_count': 0,
                'last_reminded': False
            }

    def _get_field_state(self, account_id: str, field_name: str) -> Dict[str, Any]:
        """获取字段状态"""
        key = f"{account_id}_{field_name}"
        return self.collection_state.get(key, {
            'error_count': 0,
            'attempt_count': 0,
            'last_reminded': False
        })

    def extract_sex(self, text: str) -> Optional[str]:
        """
        从文本中提取性别（首要收集字段）

        注意：这是第一个要收集的字段

        Returns:
            Optional[str]: 性别（"男"或"女"）
        """
        text = text.strip()

        # 男性关键词
        male_keywords = ['男', '男的', '我是男生', '我是男生', '哥哥', '帅哥', '先生', 'M']
        for keyword in male_keywords:
            if keyword in text and '女' not in text:
                return '男'

        # 女性关键词
        female_keywords = ['女', '女的', '我是女生', '我是女生', '姐姐', '妹妹', '美女', '女士', 'F']
        for keyword in female_keywords:
            if keyword in text and '男' not in text:
                return '女'

        return None

    def extract_birth_year(self, text: str) -> Optional[int]:
        """
        从文本中提取出生年份

        Returns:
            Optional[int]: 出生年份
        """
        # 模式1: "95年"、"1995年"
        pattern1 = r'(\d{4})年'
        match1 = re.search(pattern1, text)
        if match1:
            year = int(match1.group(1))
            current_year = datetime.now().year
            if 1960 <= year <= current_year:
                return year

        # 模式2: "95后"、"90后"
        pattern2 = r'(\d{2})后'
        match2 = re.search(pattern2, text)
        if match2:
            year_prefix = int(match2.group(1))
            # 90后 -> 1990-1999
            current_year = datetime.now().year
            year_prefix_str = f"19{year_prefix:02d}"
            possible_year = int(year_prefix_str)
            if 1960 <= possible_year <= current_year:
                return possible_year

        # 模式3: 直接说年份 "我1995出生"
        pattern3 = r'[我是]?(\d{4})'
        match3 = re.search(pattern3, text)
        if match3:
            year = int(match3.group(1))
            current_year = datetime.now().year
            if 1960 <= year <= current_year:
                return year

        return None

    def extract_height(self, text: str) -> Optional[str]:
        """
        从文本中提取身高

        Returns:
            Optional[str]: 身高（格式：170cm）
        """
        # 模式1: "170cm"、"170公分"
        pattern1 = r'(\d{3})\s*(cm|公分)'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            height_val = int(match1.group(1))
            if 140 <= height_val <= 220:
                return f"{height_val}cm"

        # 模式2: "一米七"、"一米七五"
        pattern2 = r'一米[零一]?([七八九零\d])'
        match2 = re.search(pattern2, text)
        if match2:
            last_digit = match2.group(1)
            digit_map = {'零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
                        '五': '5', '六': '6', '七': '7', '八': '8', '九': '9'}
            digit = digit_map.get(last_digit, last_digit)
            height_val = int(f"17{digit}")
            if 140 <= height_val <= 220:
                return f"{height_val}cm"

        # 模式3: 直接数字 "身高170"
        pattern3 = r'身高[为是]?(\d{3})'
        match3 = re.search(pattern3, text)
        if match3:
            height_val = int(match3.group(1))
            if 140 <= height_val <= 220:
                return f"{height_val}cm"

        return None

    def extract_weight(self, text: str) -> Optional[str]:
        """
        从文本中提取体重

        Returns:
            Optional[str]: 体重（格式：55kg）
        """
        # 模式1: "55kg"、"55公斤"、"55斤"
        pattern1 = r'(\d{2,3})\s*(kg|公斤|斤)'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            weight_val = int(match1.group(1))
            unit = match1.group(2).lower()

            # 如果是斤，转换为kg（除以2）
            if '斤' in unit:
                weight_val = weight_val // 2

            if 30 <= weight_val <= 200:
                return f"{weight_val}kg"

        # 模式2: "体重55"
        pattern2 = r'体重[为是]?(\d{2,3})'
        match2 = re.search(pattern2, text)
        if match2:
            weight_val = int(match2.group(1))
            if 30 <= weight_val <= 200:
                return f"{weight_val}kg"

        # 模式3: "一百二十斤"等
        pattern3 = r'(\d{2,3})斤'
        match3 = re.search(pattern3, text)
        if match3:
            weight_val = int(match3.group(1)) // 2
            if 30 <= weight_val <= 200:
                return f"{weight_val}kg"

        return None

    def extract_location(self, text: str) -> Optional[str]:
        """
        从文本中提取所在地

        Returns:
            Optional[str]: 所在地
        """
        for city in self.CITIES:
            if city in text:
                return city
        return None

    def extract_education(self, text: str) -> Optional[str]:
        """
        从文本中提取学历

        Returns:
            Optional[str]: 学历
        """
        for level, keywords in self.EDUCATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return level
        return None

    def extract_marital_status(self, text: str) -> Optional[str]:
        """
        从文本中提取婚姻状况

        Returns:
            Optional[str]: 婚姻状况
        """
        for status, keywords in self.MARITAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return status
        return None

    def extract_monthly_income(self, text: str) -> Optional[str]:
        """
        从文本中提取月收入

        Returns:
            Optional[str]: 月收入
        """
        # 模式1: "月薪1.5万"、"月薪15000"
        pattern1 = r'月\s*(薪|收|入)\s*(\d+\.?\d*)[万千]?'
        match1 = re.search(pattern1, text)
        if match1:
            income = float(match1.group(2))
            unit = match1.group(0)[-1] if match1.group(0)[-1] in ['万', '千'] else ''
            if unit == '万':
                return f"{income}万"
            elif unit == '千':
                return f"{income/10:.1f}万"
            elif income > 1000:
                return f"{income/10000:.1f}万"
            else:
                return f"{income}万"

        # 模式2: "工资1万"、"收入1.5w"
        pattern2 = r'(工资|薪|收入|挣|赚|钱)\s*(\d+\.?\d*)[万wk]?'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            income = float(match2.group(2))
            return f"{income}万"

        # 模式3: "一万五"、"两万"
        pattern3 = r'(一|二|三|四|五|六|七|八|九|十)(万|万五|万五)'
        match3 = re.search(pattern3, text)
        if match3:
            return match3.group(0)

        return None

    def extract_contact(self, text: str) -> Optional[str]:
        """
        从文本中提取联系方式（主要是电话号码）

        Returns:
            Optional[str]: 提取的电话号码
        """
        # 模式1: 11位手机号
        pattern1 = r'1[3-9]\d{9}'
        match1 = re.search(pattern1, text)
        if match1:
            return match1.group(0)

        # 模式2: 带区号的座机
        pattern2 = r'(0\d{2,3}-?\d{7,8})'
        match2 = re.search(pattern2, text)
        if match2:
            return match2.group(0)

        # 模式3: 微信号（字母+数字）
        pattern3 = r'wx[a-zA-Z0-9_-]{6,20}'
        match3 = re.search(pattern3, text.lower())
        if match3:
            return match3.group(0)

        return None

    def extract_occupation(self, text: str) -> Optional[str]:
        """
        从文本中提取职业

        Returns:
            Optional[str]: 职业
        """
        # 检查职业关键词
        for category, keywords in self.OCCUPATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return keyword

        # 检查直接说职业
        work_keywords = ['在', '工作', '做', '职业', '上班', '公司']
        if any(kw in text for kw in work_keywords):
            # 尝试提取关键词
            words = text.split()
            for word in words:
                if len(word) >= 2 and word not in work_keywords and '在' not in word:
                    return word

        return None

    def extract_preferred_call(self, text: str) -> Optional[str]:
        """
        从文本中提取对方希望的称呼

        Returns:
            Optional[str]: 称呼
        """
        # 模式1: "叫我XX"、"叫我XX"
        pattern1 = r'叫我[是]*([^\s，。！？]{1,4})'
        match1 = re.search(pattern1, text)
        if match1:
            call = match1.group(1)
            if len(call) <= 4 and call not in ['他', '她']:
                return call

        # 模式2: "叫XX"后面跟"就行"、"可以"等
        pattern2 = r'叫([^\s，。！？]{1,3})[就]行[可]以'
        match2 = re.search(pattern2, text)
        if match2:
            call = match2.group(1)
            if len(call) <= 3 and call not in ['他', '她']:
                return call

        return None

    def is_valid_phone(self, phone: str) -> Tuple[bool, str]:
        """
        验证手机号码是否有效

        Args:
            phone: 手机号码

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not phone:
            return False, "没看到手机号呢～"

        cleaned = ''.join(c for c in phone if c.isdigit())
        if len(cleaned) != 11:
            return False, "这个数字好像不太对哦～"
        if not cleaned.startswith('1'):
            return False, "手机号应该是1开头的呢～"
        if not cleaned[1:4].isdigit():
            return False, "这个号码看起来有点问题～"

        return True, ""

    def generate_collection_prompt(
        self,
        account_id: str,
        profile: UserProfile,
        user_message: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """
        生成隐晦的信息收集提示

        Args:
            account_id: 用户账号ID
            profile: 用户信息档案
            user_message: 用户当前消息
            conversation_history: 对话历史

        Returns:
            Tuple[str, Optional[str], Optional[Dict[str, Any]]: (系统提示, 提取到的信息)
        """
        # 获取下一个需要收集的字段
        next_field = profile.get_next_field_to_collect()
        if not next_field:
            # 所有信息已收集
            collection_summary = profile.get_collection_summary()
            return f"{collection_summary}想聊点什么呢～", None

        self._init_field_state(account_id, next_field)
        field_state = self._get_field_state(account_id, next_field)

        # 检查是否达到错误次数限制
        if field_state['error_count'] >= 2:
            # 跳过这个字段，收集下一个
            profile.collection_progress[next_field] = False  # 标记为不收集
            return self.generate_collection_prompt(account_id, profile, user_message, conversation_history)

        # 尝试从用户消息中提取信息
        field_name_chinese = self.FIELD_NAMES.get(next_field, next_field)
        extracted_info = self._extract_field(next_field, user_message)

        if extracted_info is not None:
            # 提取成功
            success = profile.update_field(next_field, extracted_info)
            if success:
                # 重置错误计数
                self.collection_state[f"{account_id}_{next_field}"]['error_count'] = 0
                return f"嗯嗯，记下来啦～", {next_field: extracted_info}
            else:
                # 提取了但验证失败
                return f"好的呢～", None
        else:
            # 没有提取到，尝试提示
            field_state['attempt_count'] += 1

            # 第一次尝试
            if field_state['attempt_count'] == 1:
                prompt = self._generate_subtle_prompt(next_field, conversation_history)
                return prompt, None
            # 第二次尝试，仍然没有提取
            elif field_state['attempt_count'] == 2:
                # 跳过这个字段
                profile.collection_progress[next_field] = False
                return self.generate_collection_prompt(account_id, profile, user_message, conversation_history)
            # 尝试次数太多，跳过
            else:
                profile.collection_progress[next_field] = False
                return self.generate_collection_prompt(account_id, profile, user_message, conversation_history)

    def _extract_field(self, field_name: str, text: str) -> Optional[Any]:
        """提取指定字段"""
        extractors = {
            'sex': self.extract_sex,
            'birth_year': self.extract_birth_year,
            'height': self.extract_height,
            'weight': self.extract_weight,
            'location': self.extract_location,
            'education': self.extract_education,
            'marital_status': self.extract_marital_status,
            'monthly_income': self.extract_monthly_income,
            'occupation': self.extract_occupation,
            'preferred_call': self.extract_preferred_call,
            'contact': self.extract_contact
        }

        extractor = extractors.get(field_name)
        if extractor:
            return extractor(text)
        return None

    def _generate_subtle_prompt(
        self,
        field_name: str,
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        生成隐晦的信息收集提示

        Args:
            field_name: 字段名
            conversation_history: 对话历史

        Returns:
            str: 隐晦的提示语
        """
        # 检查对话历史长度
        history_length = len(conversation_history)

        # 获取用户最近的几条消息
        recent_user_messages = [
            msg['user_message'] for msg in conversation_history[-3:] if 'user_message' in msg
        ]

        # 根据字段生成不同的隐晦提示
        prompts = {
            'sex': self._prompt_sex(history_length, recent_user_messages),
            'birth_year': self._prompt_birth_year(history_length),
            'height': self._prompt_height(history_length),
            'weight': self._prompt_weight(history_length),
            'location': self._prompt_location(history_length),
            'education': self._prompt_education(history_length),
            'marital_status': self._prompt_marital(history_length),
            'monthly_income': self._prompt_income(history_length),
            'occupation': self._prompt_occupation(history_length),
            'preferred_call': self._prompt_preferred_call(history_length),
            'contact': self._prompt_contact(history_length, recent_user_messages)
        }

        return prompts.get(field_name, "嗯嗯～")

    def _prompt_sex(self, history_length: int, recent_messages: List[str]) -> str:
        """
        生成性别收集提示（首要字段，隐晦自然）
        """
        return "你是男生还是女生呀？"

    def _prompt_birth_year(self, history_length: int) -> str:
        """生成出生年收集提示（隐晦）"""
        if history_length < 6:
            return "你是哪一年的呀？"
        return "好奇你的年龄呢~"

    def _prompt_height(self, history_length: int) -> str:
        """生成身高收集提示（隐晦）"""
        if history_length < 8:
            return "身高大概多少呢？"
        return "想了解一下你的情况~"

    def _prompt_weight(self, history_length: int) -> str:
        """生成体重收集提示（隐晦）"""
        if history_length < 8:
            return "体重大概多少呀？"
        return "想了解你的情况~"

    def _prompt_location(self, history_length: int) -> str:
        """生成坐标收集提示"""
        if history_length < 6:
            return "你在哪个城市呢～"
        return "好奇你是在哪里呀～"

    def _prompt_education(self, history_length: int) -> str:
        """生成学历收集提示"""
        if history_length < 10:
            return "是什么学历呢～"
        return "好奇你的学历～"

    def _prompt_marital(self, history_length: int) -> str:
        """生成婚况收集提示"""
        if history_length < 8:
            return "现在是一个人吗？还是～"
        return "想了解一下你的情况～"

    def _prompt_income(self, history_length: int) -> str:
        """生成月收入收集提示（隐晦）"""
        if history_length < 12:
            return "工作怎么样呀？"
        return "最近工作忙吗~"

    def _prompt_occupation(self, history_length: int) -> str:
        """生成职业收集提示（隐晦）"""
        if history_length < 10:
            return "平时做什么工作呀？"
        return "在哪里工作呢~"

    def _prompt_preferred_call(self, history_length: int) -> str:
        """生成称呼收集提示（隐晦）"""
        if history_length < 15:
            return "希望对方怎么称呼你呀？"
        return "有什么特别想说的吗~"

    def _prompt_contact(self, history_length: int, recent_messages: List[str]) -> str:
        """生成联系方式收集提示（隐晦）"""
        if history_length < 5:
            return "方便留个联系方式吗？微信或者电话都行~"
        return "有需要的话，可以告诉我怎么联系你哦~"

    def check_input_understandability(self, text: str, account_id: str) -> Tuple[bool, str]:
        """
        检查用户输入是否可理解

        Args:
            text: 用户输入
            account_id: 用户账号ID

        Returns:
            Tuple[bool, str]: (是否可理解, 提醒消息)
        """
        # 检查是否完全是乱码/不可理解的内容
        text = text.strip()

        # 检查1: 只有特殊字符
        if not re.search(r'[\u4e00-\u9fff]', text):
            return False, "抱歉，没看懂你说什么呢～"

        # 检查2: 过多的重复字符
        if len(set(text)) < 3 and len(text) > 10:
            return False, "这是什么意思呢～没太理解～"

        # 检查3: 纯英文字母但不符合常见模式
        if re.match(r'^[a-zA-Z]+$', text) and len(text) > 15:
            return False, "没太理解呢，能换种方式说吗～"

        # 检查4: 检查错误次数
        self._init_field_state(account_id, 'general')
        field_state = self._get_field_state(account_id, 'general')

        if field_state['error_count'] >= 2:
            # 错误次数过多，跳过提醒
            return True, ""

        return True, ""

    def record_input_error(self, account_id: str) -> None:
        """
        记录用户输入错误

        Args:
            account_id: 用户账号ID
        """
        self._init_field_state(account_id, 'general')
        self.collection_state[f"{account_id}_general"]['error_count'] += 1

    def reset_errors(self, account_id: str) -> None:
        """
        重置所有错误计数

        Args:
            account_id: 用户账号ID
        """
        for key in list(self.collection_state.keys()):
            if key.startswith(f"{account_id}_"):
                self.collection_state[key]['error_count'] = 0
