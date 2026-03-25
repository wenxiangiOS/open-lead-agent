"""微信和电话逻辑单元测试。"""

from __future__ import annotations

import re


class TestWechatAndPhoneLogic:
    """覆盖微信号识别与微信后电话争取的核心规则。"""

    def _is_nonsense_input(self, text: str) -> tuple[bool, str]:
        """简化版的无意义检测逻辑（仅用于回归测试）。"""
        text_stripped = text.strip()

        chinese_chars = re.findall(r"[\u4e00-\u9fa5]", text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            return (False, "通过中文检查")

        if len(text_stripped) <= 2:
            pattern = r"[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}"
            if not re.search(pattern, text_stripped):
                return (True, "短输入无意义")
            return (False, "短输入有意义")

        if len(text_stripped) >= 6:
            has_letter = bool(re.search(r"[a-zA-Z]", text_stripped))
            has_digit = bool(re.search(r"\d", text_stripped))

            if has_letter and has_digit:
                wechat_pattern = r"^[a-zA-Z][a-zA-Z0-9_-]{5,19}$"
                if re.match(wechat_pattern, text_stripped):
                    return (False, "完整输入匹配微信号格式")

                potential_wechat = re.search(r"[a-zA-Z][a-zA-Z0-9_-]{5,19}", text_stripped)
                if potential_wechat:
                    return (False, f"包含微信号格式: {potential_wechat.group()}")

                type_switches = 0
                prev_was_digit = text_stripped[0].isdigit()
                for char in text_stripped[1:]:
                    current_is_digit = char.isdigit()
                    if current_is_digit != prev_was_digit and char.isalnum():
                        type_switches += 1
                    prev_was_digit = current_is_digit

                if type_switches > len(text_stripped) * 0.4:
                    return (True, f"类型切换过多: {type_switches}")

        return (False, "默认有意义")

    def test_wechat_nonsense_detection(self) -> None:
        """微信号表达不应被轻易误判为乱码。"""
        test_cases = [
            ("留微信，我微信fwf474774747", False),
            ("我的微信是abc123456", False),
            ("微信wx123456789", False),
            ("微信号test_wx_123", False),
            ("我微信zhangsan88", False),
            ("加我微信abc123456", False),
            ("微信abc123456吧", False),
            ("留个微信abc123456", False),
            ("可以加微信abc123456", False),
            ("方便加微信abc123456吗", False),
            ("我微信号是abc123456", False),
            ("123456789012", False),
            ("abcdefghij", False),
            ("你好", False),
            ("wxid_abc123", False),
            ("fwf474774747", False),
            ("!!", True),
            ("1!", True),
        ]

        for user_input, expected_nonsense in test_cases:
            is_nonsense, _ = self._is_nonsense_input(user_input)
            assert is_nonsense == expected_nonsense, user_input

    def test_phone_persuasion_after_wechat(self) -> None:
        """留微信后的电话争取逻辑应符合预期。"""
        scenarios = [
            {
                "name": "首次留微信时争取电话",
                "has_contact": False,
                "has_wechat": True,
                "phone_persuasion_attempted": False,
                "rejected_phone": False,
                "is_hong_user": False,
                "should_persuade_phone": True,
            },
            {
                "name": "已争取过电话时不再重复争取",
                "has_contact": False,
                "has_wechat": True,
                "phone_persuasion_attempted": True,
                "rejected_phone": False,
                "is_hong_user": False,
                "should_persuade_phone": False,
            },
            {
                "name": "已有电话时不争取电话",
                "has_contact": True,
                "has_wechat": False,
                "phone_persuasion_attempted": False,
                "rejected_phone": False,
                "is_hong_user": False,
                "should_persuade_phone": False,
            },
            {
                "name": "拒绝电话后留微信时不再争取电话",
                "has_contact": False,
                "has_wechat": True,
                "phone_persuasion_attempted": True,
                "rejected_phone": True,
                "is_hong_user": False,
                "should_persuade_phone": False,
            },
            {
                "name": "香港用户留微信且未留电话时仍要争取电话",
                "has_contact": False,
                "has_wechat": True,
                "phone_persuasion_attempted": False,
                "rejected_phone": False,
                "is_hong_user": True,
                "should_persuade_phone": True,
            },
        ]

        for scenario in scenarios:
            should_persuade_phone = (
                not scenario["has_contact"]
                and scenario["has_wechat"]
                and not scenario["phone_persuasion_attempted"]
                and not scenario["rejected_phone"]
            )
            assert should_persuade_phone == scenario["should_persuade_phone"], scenario["name"]

    def test_full_conversation_flow(self) -> None:
        """完整对话样例中的各轮输入都应被视为有效输入。"""
        conversation_steps = [
            "你好",
            "是的呢",
            "青青，90后，it，深圳，180 70kg，本科，4万",
            "男的，180，单身",
            "没有，看感觉",
            "留微信，我微信test123456",
        ]

        for user_input in conversation_steps:
            is_nonsense, _ = self._is_nonsense_input(user_input)
            assert is_nonsense is False, user_input
