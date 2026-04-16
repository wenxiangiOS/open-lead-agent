"""
输入兜底服务

负责无意义输入检测、确认词追踪、以及相关兜底回复。
"""

import logging
import random
import re
from typing import Optional

from src.models.user_profile import UserProfile
from src.services.data.user_service import UserService

logger = logging.getLogger(__name__)


class InputFallbackService:
    """管理弱输入、乱码输入和确认词兜底逻辑。"""

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
        '欧阳', '司马', '上官', '诸葛', '东方', '皇甫', '令狐', '夏侯',
    })

    def __init__(self, user_service: UserService, nonsense_prefix: str, confirm_prefix: str):
        self.user_service = user_service
        self.nonsense_count_prefix = nonsense_prefix
        self.confirm_count_prefix = confirm_prefix

    async def get_nonsense_count(self, user_id: str) -> int:
        from src.services.data.redis_service import redis_service
        key = f"{self.nonsense_count_prefix}{user_id}"
        count = await redis_service.get(key)
        return int(count) if count else 0

    async def increment_nonsense_count(self, user_id: str) -> int:
        from src.services.data.redis_service import redis_service
        key = f"{self.nonsense_count_prefix}{user_id}"
        count = await self.get_nonsense_count(user_id) + 1
        await redis_service.set(key, str(count), ttl=3600)
        return count

    async def reset_nonsense_count(self, user_id: str) -> None:
        from src.services.data.redis_service import redis_service
        key = f"{self.nonsense_count_prefix}{user_id}"
        await redis_service.delete(key)

    async def get_confirm_count(self, user_id: str) -> int:
        from src.services.data.redis_service import redis_service
        key = f"{self.confirm_count_prefix}{user_id}"
        count = await redis_service.get(key)
        return int(count) if count else 0

    async def increment_confirm_count(self, user_id: str) -> int:
        from src.services.data.redis_service import redis_service
        key = f"{self.confirm_count_prefix}{user_id}"
        count = await self.get_confirm_count(user_id) + 1
        await redis_service.set(key, str(count), ttl=3600)
        return count

    async def reset_confirm_count(self, user_id: str) -> None:
        from src.services.data.redis_service import redis_service
        key = f"{self.confirm_count_prefix}{user_id}"
        await redis_service.delete(key)

    def is_nonsense_input(self, text: str) -> bool:
        """检测是否是无意义输入。"""
        text_stripped = text.strip()

        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            logger.info(f"[无意义检测] 通过中文检查: {text_stripped}")
            return False

        if len(text_stripped) <= 2:
            if text_stripped in self.COMMON_SURNAMES:
                logger.info(f"[无意义检测] 判定为有意义（常见姓氏）: {text_stripped}")
                return False

            pattern = r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}'
            match = re.search(pattern, text_stripped)
            logger.info(f"[无意义检测] 短输入 '{text_stripped}' (len={len(text_stripped)}) 正则匹配: {match}")
            if not match:
                income_pattern = r'^\d+[万千百kKwW]?$|^\d+[万千百kKwW]$'
                if re.match(income_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（收入格式）: {text_stripped}")
                    return False
                logger.info(f"[无意义检测] 判定为无意义: {text_stripped}")
                return True
            logger.info(f"[无意义检测] 判定为有意义: {text_stripped}，返回 False")
            return False

        emoji_pattern = re.compile(
            '[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            '\U00002702-\U000027B0\U000024C2-\U000027BF'
            '\u2600-\u26FF]'
        )
        emoji_count = len(emoji_pattern.findall(text_stripped))
        if emoji_count > 0 and len(text_stripped) > 0:
            emoji_ratio = emoji_count / len(text_stripped)
            if emoji_ratio > 0.3:
                logger.info(f"[无意义检测] 表情符号过多: {text_stripped}")
                return True

        if re.match(r'^[\d\s\+\-\(\)\*#]{3,}$', text_stripped):
            clean_num = re.sub(r'\s+', '', text_stripped)
            if re.match(r'^1[3-9]\d{9}$', clean_num) or re.match(r'^[5-9]\d{7}$', clean_num):
                logger.info(f"[无意义检测] 手机号格式，判定有意义: {text_stripped}")
                return False
            try:
                num = int(clean_num)
                if 100 <= num <= 250:
                    logger.info(f"[无意义检测] 可能是身高，判定有意义: {text_stripped}")
                    return False
                if 30 <= num <= 300:
                    logger.info(f"[无意义检测] 可能是体重，判定有意义: {text_stripped}")
                    return False
                if 18 <= num <= 80:
                    logger.info(f"[无意义检测] 可能是年龄，判定有意义: {text_stripped}")
                    return False
                if num >= 1000:
                    logger.info(f"[无意义检测] 可能是收入等大数字，判定有意义: {text_stripped}")
                    return False
            except ValueError:
                pass
            logger.info(f"[无意义检测] 纯数字但无法识别含义: {text_stripped}")
            return True

        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'qwer', 'asdf', 'zxcv', 'tyui', 'ghjk', 'bnm',
            'rtyu', 'fghj', 'cvbn', 'yuiop', 'hjkl'
        ]
        text_lower = text_stripped.lower()
        for seq in keyboard_sequences:
            if seq in text_lower or seq[::-1] in text_lower:
                logger.info(f"[无意义检测] 键盘乱敲: {text_stripped}")
                return True

        if len(text_stripped) >= 6:
            has_letter = bool(re.search(r'[a-zA-Z]', text_stripped))
            has_digit = bool(re.search(r'\d', text_stripped))
            logger.info(f"[无意义检测] 字母数字检查: has_letter={has_letter}, has_digit={has_digit}")

            if has_letter and has_digit:
                wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{4,19}$'
                if re.match(wechat_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（微信号格式）: {text_stripped}")
                    return False
                potential_wechat = re.search(r'[a-zA-Z][a-zA-Z0-9_-]{4,19}', text_stripped)
                if potential_wechat:
                    logger.info(f"[无意义检测] 包含可能的微信号格式: {potential_wechat.group()}")
                    return False

                for pattern_len in range(2, 5):
                    if len(text_stripped) >= pattern_len * 3:
                        patterns = [text_stripped[i:i + pattern_len].lower() for i in range(len(text_stripped) - pattern_len + 1)]
                        from collections import Counter
                        pattern_counts = Counter(patterns)
                        for pattern, count in pattern_counts.items():
                            if count >= 3 and pattern.isalnum() and any(c.isalpha() for c in pattern) and any(c.isdigit() for c in pattern):
                                logger.info(f"[无意义检测] 重复模式(字母数字混合): {pattern} count={count}")
                                return True

                meaningful_patterns = [
                    r'\d+kg',
                    r'\d+cm',
                    r'\d+岁',
                    r'\d+年',
                    r'wx[a-zA-Z0-9]+',
                    r'\d+\.?\d*[wW万千百]',
                ]
                for pattern in meaningful_patterns:
                    if re.search(pattern, text_stripped.lower()):
                        logger.info(f"[无意义检测] 包含有意义格式({pattern})，跳过乱码检测: {text_stripped}")
                        return False

                type_switches = 0
                prev_was_digit = text_stripped[0].isdigit()
                for char in text_stripped[1:]:
                    current_is_digit = char.isdigit()
                    if current_is_digit != prev_was_digit and char.isalnum():
                        type_switches += 1
                    prev_was_digit = current_is_digit

                if type_switches > len(text_stripped) * 0.4:
                    logger.info(f"[无意义检测] 类型切换过多: type_switches={type_switches}, len={len(text_stripped)}")
                    return True

        if len(text_stripped) >= 8:
            if re.match(r'^1[3-9]\d{9}$', text_stripped) or re.match(r'^[5-9]\d{7}$', text_stripped):
                return False
            unique_chars = set(text_stripped.lower())
            unique_ratio = len(unique_chars) / len(text_stripped)
            if unique_ratio < 0.5:
                return True

        if len(text_stripped) > 5 and re.search(r'(.)\1{4,}', text_stripped):
            return True

        if re.match(r'^[a-zA-Z]{4,}$', text_stripped):
            has_vowel = bool(re.search(r'[aeiou]', text_stripped.lower()))
            if not has_vowel:
                return True
            if re.search(r'[^aeiou\s]{5,}', text_stripped.lower()):
                return True

        special_char_pattern = re.compile(r'[^\w\s\u4e00-\u9fa5]{8,}')
        if special_char_pattern.search(text_stripped):
            return True

        return False

    async def check_and_handle_nonsense(
        self,
        user_input: str,
        user_id: str,
        user_profile: UserProfile,
        last_ai_response: str,
    ) -> Optional[str]:
        """检测并处理无意义输入。"""
        logger.info(f"[_check_and_handle_nonsense] 开始检查: input={user_input}")
        is_nonsense = self.is_nonsense_input(user_input)
        logger.info(f"[_check_and_handle_nonsense] is_nonsense={is_nonsense}")

        if not is_nonsense:
            await self.reset_nonsense_count(user_id)
            return None

        count = await self.increment_nonsense_count(user_id)
        end_intent_count = user_profile.get_ask_count('conversation_end_intent')
        if end_intent_count >= 1:
            retention_keywords = [
                '随时可以', '随时', '想聊', '想聊了就聊', '什么时候都可以',
                '先这样', '下次再聊', '拜拜', '没关系', '不打扰',
                '慢慢来', '别急着', '不着急', '有什么不方便', '有什么顾虑',
                '怎么了', '可以和我说', '告诉我', '可以慢慢'
            ]
            if last_ai_response and any(kw in last_ai_response for kw in retention_keywords):
                logger.info(f"[挽留失败检测] 用户接受结束，输入: {user_input}, 上一轮AI: {last_ai_response[:50]}...")
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(user_id, user_profile)
                await self.reset_nonsense_count(user_id)

                sex = user_profile.sex if user_profile else None
                call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
                responses = [
                    f"好，{call_name}，那我们先聊到这儿。",
                    f"行，{call_name}，那今天先这样。",
                ]
                return random.choice(responses)

        if count == 1:
            return self.get_first_nonsense_response(user_profile)
        if count == 2:
            return self.get_second_nonsense_response(user_profile)
        if count == 3:
            return self.get_third_nonsense_response(user_profile)
        return self.get_closing_response(user_profile)

    def get_first_nonsense_response(self, user_profile: UserProfile) -> str:
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
        return random.choice([
            f"嗯...{call_name}是不是不小心输错啦～我看到的内容有点看不懂呢",
            f"{call_name}你是想说什么呢？我刚才看到的消息有点奇怪呢～",
            f"啊呀，{call_name}是不是手机不小心碰到啦～发的内容我没太看明白",
        ])

    def get_second_nonsense_response(self, user_profile: UserProfile) -> str:
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
        has_name = user_profile and user_profile.last_name
        has_location = user_profile and user_profile.location

        if has_name and not has_location:
            responses = [
                f"{call_name}要是现在不想聊这些，我们就先简单一点。你现在主要在哪个城市？",
                f"没关系，{call_name}。那我先问个简单的，你现在在哪个城市？",
            ]
        elif has_name:
            responses = [
                f"{call_name}要是现在不想聊这些也没事，我们慢慢来。",
                f"没关系，{call_name}。要不我们换个轻松点的话题。",
            ]
        else:
            responses = [
                f"{call_name}要不我们重新捋一下。你现在主要在哪个城市工作生活？",
                f"{call_name}要是现在不想聊太多，我们就先从简单的开始。你在哪个城市？",
                f"{call_name}那我们先从轻松点的开始，你现在在哪个城市？",
            ]
        return random.choice(responses)

    def get_third_nonsense_response(self, user_profile: UserProfile) -> str:
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
        return random.choice([
            f"感觉{call_name}现在可能不太想聊这个。等你想聊的时候我们再继续。",
            f"{call_name}你现在要是不想展开也没关系，我们先停一下，想聊了再继续。",
            f"我感觉{call_name}现在可能不太方便，那我们晚点再聊也行。",
        ])

    def get_closing_response(self, user_profile: UserProfile) -> str:
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
        return random.choice([
            f"好，{call_name}，那我们今天就先聊到这儿，之后想继续随时找我。",
            f"感觉{call_name}今天不太想继续，那我就先收住了，不打扰你。",
            f"行，{call_name}，那我们先这样，之后想继续随时找我再聊也行。",
        ])

    def get_confirm_word_response(self, user_profile: UserProfile, confirm_count: int) -> Optional[str]:
        """根据确认词次数返回对应回复。"""
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        if confirm_count == 1:
            return random.choice([
                "电话这块主要是后面需要的时候能联系到你。你要是方便，发我一个号码就行。",
                "这个电话只是想在需要时能联系到你。你方便的话，给我一个号码就可以。",
                "电话这块如果你方便，就发我一个号码。不方便我们也可以先不聊这个。",
            ])
        if confirm_count == 2:
            return random.choice([
                "如果电话不方便，微信也可以。",
                "你要是不想留电话也没关系，微信方便的话说一个也行。",
                "电话这块不方便的话，我们也可以换成微信。",
            ])
        if confirm_count == 3:
            return random.choice([
                "好，那这个我先不继续问了。",
                f"没事，{call_name}，那我们先聊到这儿。",
                "行，这个话题我先收住。",
            ])
        return ""
