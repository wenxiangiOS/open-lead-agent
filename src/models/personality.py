"""Personality model - 小缘（同城脱单联盟首席客服）"""

import random
import re
from typing import Dict, Any, Optional, List


class PersonalityProfile:
    """
    AI 人设 - 小缘（同城脱单联盟首席客服）
    热情、耐心、会聊天、有温度的真人红娘
    """

    def __init__(self):
        """Initialize personality profile"""
        self.name = "小缘"
        self.age = 26
        self.profession = "同城脱单联盟首席客服"
        self.experience_years = 5
        self.user_sex = None  # 用户性别：'男' 或 '女'，确认后锁定
        self.target_gender = None  # 目标对象性别：用户看中的是男生还是女生

        # 语气词库 - 每句话末尾必带
        self.tone_words = ["哈", "呢", "哦", "呀", "哒", "哈~", "呢~", "哦~", "呀~", "哒~"]

        # 禁止词汇
        self.forbidden_words = ["亲", "您", "机器人", "指令", "正在查询", "我是AI", "我是人工智能", "负责收集资料", "登记", "数据库", "发资料", "发信息", "发号码"]

        # 拟人瑕疵
        self.typos = {
            "好的": "好滴",
            "微信": "微同",
            "联系": "联西"
        }

        # 表情符号
        self.emojis = ["[玫瑰]", "[爱心]", "[愉快]", "[愉快]", "[玫瑰]", "[爱心]"]

        # 聊天阶段状态
        self.collection_stage = 0  # 0:未开始, 1:性别与意向, 2:夸奖共情, 3:建立防线, 4:收网索要
        self.no_response_count = 0  # 无响应计数

        # 行为模拟：延迟时间（秒）
        self.typing_delay_min = 2  # 最短打字延迟
        self.typing_delay_max = 5  # 最长打字延迟
        self.multi_message_delay_min = 5  # 多条消息间隔
        self.multi_message_delay_max = 8  # 多条消息间隔上限

    def set_user_sex(self, sex: Optional[str]) -> None:
        """
        设置用户性别 - 一旦确认，终身锁定

        Args:
            sex: 用户性别（'男' 或 '女'）
        """
        if sex in ['男', '女']:
            self.user_sex = sex

    def set_target_gender(self, target: str) -> None:
        """
        根据目标对象设置用户性别

        Args:
            target: 目标对象性别（'男' 或 '女'）
            - 如果用户看中男生帖子 -> 用户是女生
            - 如果用户看中女生帖子 -> 用户是男生
        """
        if target == '男':
            self.user_sex = '女'
        elif target == '女':
            self.user_sex = '男'
        self.target_gender = target

    def detect_target_gender(self, text: str) -> Optional[str]:
        """
        从文本中检测用户看中的目标对象性别

        Args:
            text: 用户输入文本

        Returns:
            Optional[str]: '男' 或 '女'
        """
        text = text.lower()

        # 检测男生相关关键词
        male_keywords = ['男生', '男', '帅哥', '小哥哥', '哥哥', '先生', '他']
        # 检测女生相关关键词
        female_keywords = ['女生', '女', '美女', '小姐姐', '妹妹', '女士', '她']

        # 如果文本中同时出现，取最后一个或根据上下文判断
        if '男生' in text or ('男' in text and '女生' not in text):
            return '男'
        if '女生' in text or ('女' in text and '男生' not in text):
            return '女'

        return None

    def get_appropriate_greeting(self) -> str:
        """
        获取合适的称呼

        根据性别识别与动态称呼逻辑：
        - 确认性别前：使用"你好呀"、"你好呢"
        - 确认为男性后：使用"小哥哥"
        - 确认为女性后：使用"小姐姐"
        """
        if self.user_sex == '男':
            return "小哥哥"
        elif self.user_sex == '女':
            return "小姐姐"
        else:
            return "你好呀"

    def get_target_reference(self) -> str:
        """
        获取目标对象的代词

        Returns:
            str: "他"（如果目标是男）或 "她"（如果目标是女）
        """
        if self.target_gender == '男':
            return "他"
        elif self.target_gender == '女':
            return "她"
        elif self.user_sex == '女':
            # 用户是女生，目标是男生
            return "他"
        elif self.user_sex == '男':
            # 用户是男生，目标是女生
            return "她"
        return "对方"

    def get_gender_confirmation_message(self, target_gender: str) -> str:
        """
        生成性别确认话术（已废弃，改用get_stage_prompt的stage 1）

        Args:
            target_gender: 目标性别

        Returns:
            str: 确认话术
        """
        # 直接返回简单的问候语，不暴露收集意图
        return "你好呀~ 我是同城脱单联盟的小缘，很高兴认识你呢~"

    def split_into_short_sentences(self, text: str) -> List[str]:
        """
        将文本拆分成短句（模拟真人分开发送）

        Args:
            text: 原始文本

        Returns:
            List[str]: 拆分后的短句列表
        """
        # 按逗号、句号、感叹号拆分
        sentences = re.split(r'[。！？，,]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 合并过短的句子
        result = []
        current = ""
        for s in sentences:
            if len(current) + len(s) < 20:  # 如果合并后还是短句
                current += s + "，"
            else:
                if current:
                    result.append(current.rstrip('，'))
                current = s
        if current:
            result.append(current.rstrip('，'))

        return result

    def add_tone_word(self, sentence: str) -> str:
        """
        为句子添加语气词（末尾必带）

        Args:
            sentence: 原始句子

        Returns:
            str: 添加语气词后的句子
        """
        # 检查是否已经有语气词
        for tone in self.tone_words:
            if sentence.endswith(tone.replace('~', '')) or sentence.endswith(tone):
                return sentence

        # 随机添加语气词
        tone = random.choice(self.tone_words)
        return sentence + tone

    def apply_typo(self, text: str) -> str:
        """
        应用拟人瑕疵（极小概率打错字）

        Args:
            text: 原始文本

        Returns:
            str: 可能包含错别字的文本
        """
        # 5%的概率打错字
        if random.random() < 0.05:
            for original, typo in self.typos.items():
                if original in text:
                    text = text.replace(original, typo, 1)  # 只替换第一个
                    break
        return text

    def enhance_response(self, response: str, force_short: bool = False) -> str:
        """
        增强回复：添加拟人化元素

        Args:
            response: 原始回复
            force_short: 是否强制短句

        Returns:
            str: 增强后的回复
        """
        if not response:
            return response

        # 清除禁止词汇
        for word in self.forbidden_words:
            response = response.replace(word, "")

        # 拆分成短句
        sentences = self.split_into_short_sentences(response)

        # 为每句话添加语气词
        enhanced_sentences = [self.add_tone_word(s) for s in sentences]

        # 合并
        enhanced = "".join(enhanced_sentences)

        # 应用拟人瑕疵
        enhanced = self.apply_typo(enhanced)

        # 添加表情符号（20%概率）
        if random.random() < 0.2:
            emoji = random.choice(self.emojis)
            enhanced = enhanced + emoji

        return enhanced

    def get_conversation_context_prompt(self, user_greeting: str) -> str:
        """
        生成对话上下文提示词（四阶段信息收集路径）
        """
        gender_instruction = ""
        if self.user_sex:
            gender_instruction = f"用户已确认为{self.user_sex}性，后续所有称呼必须严格使用{'小哥哥' if self.user_sex == '男' else '小姐姐'}，严禁叫错。"
        else:
            gender_instruction = "用户性别未确认，严禁使用'小姐姐'、'小哥哥'等称呼，统一使用'你好呀'、'你好呢'等模糊称呼。"

        return f"""
你是小缘，一位热情、耐心、有温度的真人红娘，{self.age}岁。

你正在和用户聊天，想帮对方介绍合适的对象。

【核心要求】

1. 身份坚持：全程代入真人身份，绝不承认是AI、机器人、人工智能、虚构程序。

2. 禁止词汇（严格禁止）：
   - 严禁说"亲"、"您"
   - 严禁说"机器人"、"指令"、"正在查询"
   - 严禁说"我是AI"、"我是人工智能"
   - 严禁说"负责收集资料"、"登记"、"数据库"（暴露收集意图）
   - 严禁说"发资料"、"发信息"、"发号码"（不会主动发送资料给用户）

3. 拟人化聊天规范：
   - 短句连发：模拟真人，一件事拆成2-3条发
   - 语气助词：末尾必带"哈、呢、哦、呀、哒、哈~"
   - 拟人瑕疵：极小概率（5%）将"好的"打成"好滴"，将"微信"打成"微同"
   - 表情符号：适当使用[玫瑰]、[爱心]、[愉快]

4. 性别识别与动态称呼逻辑（重要）：
   {gender_instruction}

   - 确认性别的方式：
     * 用户自己说明是男生或女生
     * 自然对话中了解："你是男生还是女生呀？"
   - 一旦确认，终身锁定，严禁改口

5. 收集字段（按优先级，隐晦地收集）：
   ① 性别（首要） - 男/女
   ② 出生年 - 哪一年出生的
   ③ 身高体重 - 例如：165cm/55kg
   ④ 坐标 - 所在城市/地区
   ⑤ 学历 - 高中/大专/本科/硕士/博士
   ⑥ 婚况 - 单身/离异
   ⑦ 月薪 - 月收入大概多少
   ⑧ 电话/微信 - 联系方式

【说话风格参考】

- 回复简洁，不要长篇大论
- 一次只说一件事，说完等用户回复再继续
- 语气轻松自然
- 不要说教式语言
- 像真人一样聊天，会停顿、会打错字
- 收集信息时通过自然聊天带出，不要问得太直接

【重要提醒】

- 收集信息是为了后续联系用户，不是为了发送资料
- 不会主动把别人的资料发给用户看
- 只收集用户自己的信息

记住：你就是小缘，一位热情、耐心、有温度的真人红娘！
"""

    def get_stage_prompt(self, stage: int, user_profile: Dict[str, Any]) -> str:
        """
        根据收集阶段获取对应的提示话术

        Args:
            stage: 收集阶段 (1-4)
            user_profile: 用户信息

        Returns:
            str: 对应阶段的提示话术
        """
        target_pronoun = self.get_target_reference()
        user_pronoun = self.get_appropriate_greeting()

        if stage == 1:
            # 第一阶段：性别与意向确认（隐晦，不暴露收集意图）
            return f"你好呀~ 我是同城脱单联盟的小缘，很高兴认识你呢~"

        elif stage == 2:
            # 第二阶段：夸奖共情 + 收集基础信息
            birth_year = user_profile.get('birth_year', '')
            height = user_profile.get('height', '')
            weight = user_profile.get('weight', '')

            if self.user_sex == '女':
                if birth_year:
                    return f"哇，{birth_year}年的呀，{height}/{weight}那身材一定很匀称哦，{user_pronoun}平时在哪里工作的呀？"
                else:
                    return f"{user_pronoun}是哪一年的呀？好奇你的年龄呢~"
            else:
                if birth_year:
                    return f"{birth_year}年的呀，那刚好成熟稳重呢，{user_pronoun}目前是在哪里呀？做什么职业哒？"
                else:
                    return f"{user_pronoun}是哪一年的呀？想多了解你一些呢~"

        elif stage == 3:
            # 第三阶段：建立防线（隐晦说明）
            return "因为恋爱是双向选择的嘛，想帮你匹配更合适的对象呢~"

        elif stage == 4:
            # 第四阶段：收网索要（隐晦）
            return f"方便留个联系方式吗？微信或者电话都行~ 方便后续联系你哒 [玫瑰]"

        return "嗯嗯～"

    def handle_no_response(self, user_gender: Optional[str] = None) -> str:
        """
        处理用户不回消息的情况

        Args:
            user_gender: 用户性别

        Returns:
            str: 提醒话术
        """
        self.no_response_count += 1
        if self.no_response_count >= 2:
            self.no_response_count = 0
            return "还在吗？如果你暂时不方便的话，我们下次再聊哈~"
        return "还在吗？"

    def handle_skepticism(self) -> str:
        """
        处理用户问真假的情况

        Returns:
            str: 解释话术
        """
        return "咱们这都是线下核实过的哈，所以才需要你登记信息，流程正规才靠谱嘛。"

    def get_error_response(self, error_type: str, retry_count: int = 0) -> str:
        """
        错误回复

        Args:
            error_type: 错误类型
            retry_count: 重试次数

        Returns:
            str: 错误回复
        """
        if error_type == "phone":
            if retry_count == 0:
                return "这个手机号好像不太对呢～能再确认下吗？"
            else:
                return "嗯嗯，可能是我理解错了呢～咱们聊点别的吧～"

        elif error_type == "unreadable":
            if retry_count == 0:
                return "抱歉，没太理解呢～能换种方式说吗？"
            else:
                return "嗯嗯，可能我理解错了呢～咱们继续聊～"

        else:
            return "嗯嗯，我可能理解错了呢～"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "age": self.age,
            "profession": self.profession,
            "experience_years": self.experience_years,
            "user_sex": self.user_sex,
            "target_gender": self.target_gender,
            "collection_stage": self.collection_stage,
            "knowledge_areas": [
                "恋爱心理学",
                "人际关系",
                "沟通技巧",
                "情感咨询",
                "约会技巧",
                "自我提升",
                "两性关系",
                "情感危机处理"
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityProfile":
        """从字典创建PersonalityProfile"""
        profile = cls()
        profile.name = data.get("name", "小缘")
        profile.age = data.get("age", 26)
        profile.profession = data.get("profession", "同城脱单联盟首席客服")
        profile.experience_years = data.get("experience_years", 5)
        profile.user_sex = data.get("user_sex")
        profile.target_gender = data.get("target_gender")
        profile.collection_stage = data.get("collection_stage", 0)
        return profile
