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
        'contact': '联系方式',
        # 注意：last_name已包含称呼信息，不再单独收集preferred_call
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
        # 每个字段跟踪：错误次数、尝试次数、上次提醒时间、是否跳过
        # 每个字段最多尝试2次收集，失败后永久跳过

    def _init_field_state(self, account_id: str, field_name: str) -> None:
        """初始化字段状态"""
        key = f"{account_id}_{field_name}"
        if key not in self.collection_state:
            self.collection_state[key] = {
                'error_count': 0,
                'attempt_count': 0,
                'last_reminded': False,
                'skipped': False  # 新增：标记是否已跳过该字段
            }

    def _get_field_state(self, account_id: str, field_name: str) -> Dict[str, Any]:
        """获取字段状态"""
        key = f"{account_id}_{field_name}"
        return self.collection_state.get(key, {
            'error_count': 0,
            'attempt_count': 0,
            'last_reminded': False,
            'skipped': False
        })

    def _skip_field(self, account_id: str, field_name: str) -> None:
        """永久跳过某个字段"""
        key = f"{account_id}_{field_name}"
        if key in self.collection_state:
            self.collection_state[key]['skipped'] = True
            self.collection_state[key]['attempt_count'] = 999  # 设置为高值确保不再尝试
        else:
            self.collection_state[key] = {
                'error_count': 0,
                'attempt_count': 999,
                'last_reminded': False,
                'skipped': True
            }
        logger.info(f"字段 {field_name} 已跳过，不再收集")

    def _is_field_skipped(self, account_id: str, field_name: str) -> bool:
        """检查字段是否已被跳过"""
        key = f"{account_id}_{field_name}"
        state = self.collection_state.get(key, {})
        return state.get('skipped', False)

    def extract_sex(self, text: str) -> Optional[str]:
        """
        从文本中提取性别（首要收集字段）

        注意：这是第一个要收集的字段

        Returns:
            Optional[str]: 性别（"男"或"女"）
        """
        text = text.strip()

        # 优先检测：用户说"找男生/找女生" -> 可以反推用户性别
        # 如果用户找男生 -> 用户是女生
        # 如果用户找女生 -> 用户是男生
        if '找男生' in text:
            return '女'
        if '找女生' in text:
            return '男'
        # 匹配"找一个男的"、"给我找个男"等模式
        if re.search(r'找.*个.*男[^生]', text):
            return '女'
        if re.search(r'找.*个.*女[^生]', text):
            return '男'

        # 男性关键词（必须是自称，不是找对象）
        male_keywords = ['我是男', '我是男生', '我是男宝', '我是帅哥']
        for keyword in male_keywords:
            if keyword in text:
                return '男'

        # 女性关键词（必须是自称，不是找对象）
        female_keywords = ['我是女', '我是女生', '我是女宝', '我是美女']
        for keyword in female_keywords:
            if keyword in text:
                return '女'

        return None

    def extract_birth_year(self, text: str) -> Optional[int]:
        """
        从文本中提取出生年份

        Returns:
            Optional[int]: 出生年份
        """
        # 模式1: "95年"、"1995年年"、"90的"（口语）
        pattern1 = r'(\d{2,4})[年的]'
        match1 = re.search(pattern1, text)
        if match1:
            year_str = match1.group(1)
            year = int(year_str)
            # 如果是2位数，补全为19XX
            if year < 100:
                year = 1900 + year
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

        # 模式4: 3位数字且不是年份（140-220之间）
        # 优先级：如果有明确身高范围数字，返回它
        all_numbers = re.findall(r'\d+', text)
        for num_str in all_numbers:
            num = int(num_str)
            if 140 <= num <= 220:
                return f"{num}cm"

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

        # 模式3: "XX斤"格式（优先处理）
        pattern3 = r'(\d{2,3})斤'
        match3 = re.search(pattern3, text)
        if match3:
            weight_val = int(match3.group(1)) // 2
            if 30 <= weight_val <= 200:
                return f"{weight_val}kg"

        # 模式4: 纯数字（2-3位），排除身高范围
        # 优先级：如果有明确体重范围数字且不是身高范围，返回它
        # 注意：
        # 1. 如果文本中有"年"字，优先认为是年份，不匹配为体重
        # 2. 如果文本是"XX的"格式（如"90的"），且数字是2位数，优先认为是年份（如90年），不匹配为体重
        # 3. 如果文本以"呢"、"哈"、"呀"、"哒"等语气词结尾，且前面是"XX的"格式，很可能是年份回答
        if '年' in text:
            return None

        # 检查"XX的+语气词"格式，很可能是年份回答（如"90的呢"、"90的呀"）
        if re.search(r'(\d{2})[的][呢哈呀哒~！？，。]*$', text.strip()):
            return None

        all_numbers = re.findall(r'\d+', text)
        for num_str in all_numbers:
            num = int(num_str)
            # 体重范围：30-200，且不是身高范围（140-220）
            if 30 <= num <= 200 and not (140 <= num <= 220):
                return f"{num}kg"

        return None

    def extract_location(self, text: str) -> Optional[str]:
        """
        从文本中提取所在地

        Returns:
            Optional[str]: 所在地
        """
        # 支持更多表达方式
        for city in self.CITIES:
            # 匹配：深圳、深圳的、在深圳、深圳男生、深圳女生等
            if city in text:
                return city
            # 匹配：找深圳的、给我找一个深圳的
            if f'找{city}' in text or f'找一个{city}' in text or f'给我找一个{city}' in text:
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

    def extract_last_name(self, text: str) -> Optional[str]:
        """
        从文本中提取姓氏

        Returns:
            Optional[str]: 姓氏（中文单字姓氏）
        """
        # 常见中文姓氏（覆盖95%以上人口）
        common_surnames = [
            '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周',
            '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗',
            '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹',
            '彭', '曾', '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡',
            '余', '杜', '叶', '程', '苏', '魏', '吕', '丁', '任', '沈',
            '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金',
            '石', '廖', '贾', '韦', '夏', '付', '方', '白', '邹', '孟',
            '熊', '秦', '邱', '江', '尹', '薛', '闫', '段', '雷', '侯',
            '龙', '陶', '史', '黎', '贺', '顾', '毛', '郝', '龚', '邵'
        ]

        text = text.strip()

        # 模式0: 直接回答姓氏/称呼，如"小张"、"张三"、"张小美"
        # 匹配"小+姓氏"、"姓氏+字"、"姓氏+名字"
        pattern0 = r'小([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾韦夏付方白邹孟熊秦邱江尹薛闫段雷侯龙陶史黎贺顾毛郝龚邵])'
        match0 = re.search(pattern0, text)
        if match0:
            return match0.group(1)

        # 模式0.5: 姓氏开头的名字，如"张三"、"张小美"、"王建国"
        # 模式1: 姓氏后接一个字（如张三）
        pattern1 = r'([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾韦夏付方白邹孟熊秦邱江尹薛闫段雷侯龙陶史黎贺顾毛郝龚邵])[\s]*[一-十a-zA-Z]'
        match1 = re.search(pattern1, text)
        if match1:
            return match1.group(1)

        # 模式0.5_2: 姓氏后接任何字符（如张小美、王建国、李小明）
        pattern1_2 = r'([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾韦夏付方白邹孟熊秦邱江尹薛闫段雷侯龙陶史黎贺顾毛郝龚邵]).'
        match1_2 = re.search(pattern1_2, text)
        if match1_2:
            return match1_2.group(1)

        # 模式2: "叫我X"、"可以叫我X"、"你叫我X"
        pattern2 = r'(?:叫我|可以叫我|你叫我|称呼我为)([^\s，。！？、]{1,2})'
        match2 = re.search(pattern2, text)
        if match2:
            name = match2.group(1)
            # 检查是否是常见姓氏
            if any(name.startswith(s) for s in common_surnames):
                return name[0]  # 返回姓氏
            # 如果是两个字且第一个字是姓氏
            elif len(name) >= 2 and name[0] in common_surnames:
                return name[0]
            # 单字直接返回
            elif name in common_surnames:
                return name

        # 模式3: "我姓X"、"我是X姓"
        pattern3 = r'(?:我姓|我是.*姓)([^\s，。！？、]{1,2})'
        match3 = re.search(pattern3, text)
        if match3:
            name = match3.group(1)
            if name in common_surnames:
                return name

        # 模式4: "X小姐"、"X先生"、"X美女"、"X哥哥"中的姓氏
        pattern4 = r'([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾韦夏付方白邹孟熊秦邱江尹薛闫段雷侯龙陶史黎贺顾毛郝龚邵]+)(?:小姐|先生|美女|哥哥|姐姐|女士)'
        match4 = re.search(pattern4, text)
        if match4:
            return match4.group(1)

        return None

    def extract_monthly_income(self, text: str) -> Optional[str]:
        """
        从文本中提取月收入

        Returns:
            Optional[str]: 月收入
        """
        # 模式0: "30左右吧"、"30左右"、"20左右呢" - 默认单位是k
        # 这种口语表达通常指k（千）
        pattern0 = r'(\d{1,3})\s*(?:左右吧|左右|左右呢|左右哈|左右呀|左右哒|左右~|呢|吧|哈|呀|哒|~)'
        match0 = re.search(pattern0, text)
        if match0:
            income = float(match0.group(1))
            # 只有当数字在合理薪资范围内（5-100之间）才匹配
            if 5 <= income <= 100:
                return f"{income:g}k"

        # 模式1: "20k"、"20K"、"30k左右"、"30左右k"
        pattern1 = r'(\d+\.?\d*)\s*[kK](?:左右吧|左右|吗|的)?(?:元|月|收入|工资|薪)?'
        match1 = re.search(pattern1, text)
        if match1:
            income = float(match1.group(1))
            return f"{income:g}k"

        # 模式2: "20k月"、"30k左右"、"月薪30左右吧"
        pattern2 = r'(?:月\s*(?:薪|收|入)\s*)?(\d+\.?\d*)\s*(?:kK|万|千)(?:左右吧|左右|吗|的)?'
        match2 = re.search(pattern2, text)
        if match2:
            income = float(match2.group(1))
            unit = match2.group(0).lower()[-1]  # 取最后一个字符作为单位
            if 'k' in match2.group(0).lower():
                return f"{income:g}k"
            elif '万' in match2.group(0).lower():
                return f"{income}万"
            elif '千' in match2.group(0).lower():
                return f"{income}千"

        # 模式3: "月薪1.5万"、"月薪15000"
        pattern3 = r'月\s*(薪|收|入)\s*(\d+\.?\d*)[万千]?'
        match3 = re.search(pattern3, text)
        if match3:
            income = float(match3.group(2))
            unit = match3.group(0)[-1] if match3.group(0)[-1] in ['万', '千'] else ''
            if unit == '万':
                return f"{income}万"
            elif unit == '千':
                return f"{income/10:.1f}万"
            elif income > 1000:
                return f"{income/10000:.1f}万"
            else:
                return f"{income}万"

        # 模式4: "工资1万"、"收入1.5w"
        pattern4 = r'(工资|薪|收入|挣|赚|钱)\s*(\d+\.?\d*)[万wk]?'
        match4 = re.search(pattern4, text, re.IGNORECASE)
        if match4:
            income = float(match4.group(2))
            return f"{income}万"

        # 模式5: "一万五"、"两万"
        pattern5 = r'(一|二|三|四|五|六|七|八|九|十)(万|万五|万五)'
        match5 = re.search(pattern5, text)
        if match5:
            return match5.group(0)

        return None

    def extract_contact(self, text: str) -> Optional[str]:
        """
        从文本中提取联系方式（主要是电话号码）

        Returns:
            Optional[str]: 提取的电话号码或联系方式类型
        """
        # 模式1: 11位手机号
        pattern1 = r'1[3-9]\d{9}'
        match1 = re.search(pattern1, text)
        if match1:
            return match1.group(0)

        # 模式1.5: "电话"、"电话吧"、"用电话" - 返回标识类型
        if '电话' in text or '手机' in text:
            # 只是没有号码的情况，返回标识
            return 'phone'

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

        # 模式3.5: "微信"、"微信吧"、"用微信" - 返回标识类型
        if '微信' in text or '微同' in text:
            return 'wechat'

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

    # 注意：preferred_call 已移除，称呼信息通过 last_name 收集

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
        conversation_history: List[Dict[str, Any]],
        _depth: int = 0  # 内部参数，防止无限递归
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
        # 安全检查：防止无限递归
        if _depth > 20:  # 最大20个字段，超过说明有异常
            logger.warning(f"递归深度超过限制 (account: {account_id}, depth: {_depth})")
            return "嗯嗯～", None

        # 获取下一个需要收集的字段
        next_field = profile.get_next_field_to_collect()
        if not next_field:
            # 所有信息已收集 - 返回简短回应，不暴露收集意图
            # 模拟真人：信息收集完成后，简短回应或不回应
            import random
            if random.random() < 0.4:
                # 40%概率不返回任何内容（模拟真人不再回复）
                return "", None
            else:
                # 60%概率返回极简短的回应
                short_responses = ["嗯嗯～", "好哒～", "收到啦～", "嗯嗯", "好哒"]
                return random.choice(short_responses), None

        # 检查该字段是否已被跳过
        if self._is_field_skipped(account_id, next_field):
            # 递归获取下一个未跳过的字段
            return self.generate_collection_prompt(account_id, profile, user_message, conversation_history, _depth + 1)

        self._init_field_state(account_id, next_field)
        field_state = self._get_field_state(account_id, next_field)

        # 检查是否达到尝试次数限制（最多2次）
        if field_state['attempt_count'] >= 2:
            # 跳过这个字段
            self._skip_field(account_id, next_field)
            # 递归获取下一个字段
            return self.generate_collection_prompt(account_id, profile, user_message, conversation_history, _depth + 1)

        # 尝试从用户消息中提取信息
        field_name_chinese = self.FIELD_NAMES.get(next_field, next_field)
        extracted_info = self._extract_field(next_field, user_message)

        if extracted_info is not None:
            # 提取成功
            success = profile.update_field(next_field, extracted_info)
            if success:
                # 重置错误计数和尝试次数
                self.collection_state[f"{account_id}_{next_field}"]['error_count'] = 0
                self.collection_state[f"{account_id}_{next_field}"]['attempt_count'] = 0
                return f"嗯嗯，记下来啦～", {next_field: extracted_info}
            else:
                # 提取了但验证失败
                return f"好的呢～", None
        else:
            # 没有提取到，增加尝试次数
            field_state['attempt_count'] += 1
            self.collection_state[f"{account_id}_{next_field}"]['attempt_count'] = field_state['attempt_count']

            # 第一次尝试 - 返回提示
            if field_state['attempt_count'] == 1:
                prompt = self._generate_subtle_prompt(next_field, conversation_history)
                return prompt, None
            # 第二次尝试 - 跳过这个字段
            elif field_state['attempt_count'] == 2:
                self._skip_field(account_id, next_field)
                # 递归获取下一个字段
                return self.generate_collection_prompt(account_id, profile, user_message, conversation_history, _depth + 1)

        # 默认返回
        return "嗯嗯～", None

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
            # 注意：preferred_call 已移除，称呼信息通过 last_name 收集
            'contact': self.extract_contact
        }

        extractor = extractors.get(field_name)
        if extractor:
            return extractor(text)
        return None

    def _generate_subtle_prompt(
        self,
        field_name: str,
        conversation_history: List[Dict[str, Any]],
        _depth: int = 0  # 内部参数，防止无限递归
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
            # 注意：preferred_call 已移除，称呼信息通过 last_name 收集
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

    # 注意：_prompt_preferred_call 已移除，称呼信息通过 last_name 收集

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

        # 检查1: 包含数字（可能是身高、体重、年龄等信息）
        if re.search(r'\d+', text):
            return True, ""

        # 检查2: 只要包含中文就是可理解的
        if re.search(r'[\u4e00-\u9fff]', text):
            return True, ""

        # 检查3: 过多的重复字符
        if len(set(text)) < 3 and len(text) > 10:
            return False, "这是什么意思呢～没太理解～"

        # 检查4: 纯英文字母但不符合常见模式
        if re.match(r'^[a-zA-Z]+$', text) and len(text) > 15:
            return False, "没太理解呢，能换种方式说吗～"

        # 检查5: 检查错误次数
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
