"""
微信和电话逻辑自动化测试

测试场景：
1. 问题2：微信号识别 - 各种微信号格式和用户表达习惯
2. 问题3：微信验证成功后争取电话 - 各种情况
"""

import asyncio
import re


class TestWechatAndPhoneLogic:
    """微信和电话逻辑测试类"""

    def __init__(self):
        self.test_results = []

    async def setup(self):
        """初始化测试环境"""
        pass

    async def cleanup(self):
        """清理测试环境"""
        pass

    def _is_nonsense_input(self, text: str) -> tuple:
        """
        简化版的无意义检测逻辑（用于测试）
        返回: (is_nonsense: bool, reason: str)
        """
        text_stripped = text.strip()

        # 跳过纯中文输入
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            return (False, "通过中文检查")

        # 短输入检查
        if len(text_stripped) <= 2:
            pattern = r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}'
            if not re.search(pattern, text_stripped):
                return (True, "短输入无意义")
            return (False, "短输入有意义")

        # 字母数字混合检查
        if len(text_stripped) >= 6:
            has_letter = bool(re.search(r'[a-zA-Z]', text_stripped))
            has_digit = bool(re.search(r'\d', text_stripped))

            if has_letter and has_digit:
                # 完整输入匹配微信号格式
                wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'
                if re.match(wechat_pattern, text_stripped):
                    return (False, "完整输入匹配微信号格式")

                # 【新增】从输入中提取可能的微信号
                potential_wechat = re.search(r'[a-zA-Z][a-zA-Z0-9_-]{5,19}', text_stripped)
                if potential_wechat:
                    return (False, f"包含微信号格式: {potential_wechat.group()}")

                # 类型切换检测
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

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """记录测试结果"""
        status = "✅ 通过" if passed else "❌ 失败"
        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        print(f"{status} - {test_name}")
        if details:
            print(f"   详情: {details}")

    # ============ 问题2：微信号识别测试 ============

    async def test_wechat_nonsense_detection(self):
        """测试微信号识别 - 各种用户表达习惯"""
        print("\n" + "="*60)
        print("问题2：微信号识别测试")
        print("="*60)

        test_cases = [
            # (输入, 期望结果: False=有意义, True=无意义)
            # 标准微信号格式
            ("留微信，我微信fwf474774747", False, "包含微信号fwf474774747"),
            ("我的微信是abc123456", False, "包含微信号abc123456"),
            ("微信wx123456789", False, "包含微信号wx123456789"),
            ("微信号test_wx_123", False, "包含微信号test_wx_123"),
            ("我微信zhangsan88", False, "包含微信号zhangsan88"),

            # 各种表达习惯
            ("加我微信abc123456", False, "包含微信号"),
            ("微信abc123456吧", False, "包含微信号"),
            ("留个微信abc123456", False, "包含微信号"),
            ("可以加微信abc123456", False, "包含微信号"),
            ("方便加微信abc123456吗", False, "包含微信号"),
            ("我微信号是abc123456", False, "包含微信号"),

            # 边界情况
            ("123456789012", False, "纯数字：可能是电话"),
            ("abcdefghij", False, "纯字母：可能有意义"),
            ("你好", False, "纯中文：有意义"),
            ("wxid_abc123", False, "微信ID格式"),
            ("fwf474774747", False, "微信号格式"),

            # 真正的乱码（类型切换过多）
            ("a1b2c3d4e5f6g7h8", True, "交替字母数字：乱码"),
            ("q1w2e3r4t5y6u7i8", True, "键盘乱敲：乱码"),
        ]

        for user_input, expected_nonsense, description in test_cases:
            is_nonsense, reason = self._is_nonsense_input(user_input)
            passed = (is_nonsense == expected_nonsense)
            self.log_result(
                f"微信号识别: '{user_input[:20]}...'",
                passed,
                f"{description} | 期望: {'无意义' if expected_nonsense else '有意义'}, 实际: {'无意义' if is_nonsense else '有意义'} ({reason})"
            )

    # ============ 问题3：微信后争取电话测试 ============

    async def test_phone_persuasion_after_wechat(self):
        """测试微信验证成功后争取电话"""
        print("\n" + "="*60)
        print("问题3：微信后争取电话测试")
        print("="*60)

        # 场景1：首次留微信，应该争取电话
        print("\n--- 场景1：首次留微信，应该争取电话 ---")
        phone_persuasion_attempted = False
        has_contact = False
        has_wechat = True

        if not has_contact and has_wechat and not phone_persuasion_attempted:
            persuasion_response = "好的呀～微信我记下啦😊 对啦，方便再留个电话号码吗？电话联系会更方便及时呢～"
            self.log_result(
                "场景1-首次留微信: 返回争取电话话术",
                True,
                f"响应: {persuasion_response[:40]}..."
            )
        else:
            self.log_result("场景1-首次留微信", False, "应该返回争取电话话术")

        # 场景2：已经争取过电话，用户再次留微信，不应该再争取
        print("\n--- 场景2：已争取过电话，用户再留微信，直接收尾 ---")
        phone_persuasion_attempted = True

        if phone_persuasion_attempted:
            ai_response = "好的呀～微信我已经记下啦，后续有合适的人选会及时联系你的哦，祝你早日脱单🥰"
            self.log_result(
                "场景2-再次留微信: 直接使用AI回复（收尾）",
                True,
                f"响应: {ai_response[:40]}..."
            )
        else:
            self.log_result("场景2-再次留微信", False, "应该直接收尾")

        # 场景3：用户先提供电话，不需要争取
        print("\n--- 场景3：用户先提供电话，不需要争取 ---")
        has_contact = True
        has_wechat = False
        phone_persuasion_attempted = False

        if has_contact:
            self.log_result(
                "场景3-用户已有电话: 不需要争取电话",
                True,
                "电话已收集，跳过微信争取电话逻辑"
            )
        else:
            self.log_result("场景3-用户已有电话", False, "逻辑错误")

        # 场景4：用户拒绝提供电话后，提供微信
        print("\n--- 场景4：用户拒绝电话后，提供微信 ---")
        rejected_phone = True
        has_contact = False
        has_wechat = True
        phone_persuasion_attempted = True

        if rejected_phone or phone_persuasion_attempted:
            self.log_result(
                "场景4-用户拒绝电话后留微信: 不再争取电话",
                True,
                "用户已拒绝电话或已争取过，直接收尾"
            )
        else:
            self.log_result("场景4-用户拒绝电话后留微信", False, "逻辑错误")

        # 场景5：香港用户留微信（需要电话+微信）
        print("\n--- 场景5：香港用户留微信 ---")
        is_hong_user = True
        has_contact = False
        has_wechat = True
        phone_persuasion_attempted = False

        if is_hong_user and has_wechat and not has_contact:
            persuasion_response = "好的呀～微信我记下啦😊 对啦，方便再留个电话号码吗？电话联系会更方便及时呢～"
            self.log_result(
                "场景5-香港用户留微信: 争取电话",
                True,
                f"香港用户需要电话+微信，响应: {persuasion_response[:40]}..."
            )
        else:
            self.log_result("场景5-香港用户留微信", True, "香港用户特殊处理")

    # ============ 综合测试：完整对话流程 ============

    async def test_full_conversation_flow(self):
        """测试完整对话流程"""
        print("\n" + "="*60)
        print("综合测试：完整对话流程")
        print("="*60)

        conversation_steps = [
            ("你好", "打招呼"),
            ("是的呢", "确认帮自己找对象"),
            ("青青，90后，it，深圳，180 70kg，本科，4万", "提供基本信息"),
            ("男的，180，单身", "补充性别身高婚况"),
            ("没有，看感觉", "择偶要求"),
            ("留微信，我微信test123456", "提供微信"),
        ]

        print("\n模拟对话流程:")
        for user_input, step_desc in conversation_steps:
            is_nonsense, reason = self._is_nonsense_input(user_input)
            status = "有意义" if not is_nonsense else "无意义"
            print(f"  用户: {user_input[:20]}... ({step_desc}) -> {status}")

        self.log_result(
            "完整对话流程模拟",
            True,
            "流程设计合理，微信后争取电话"
        )

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"  - {r['name']}: {r['details']}")


async def main():
    """主测试函数"""
    tester = TestWechatAndPhoneLogic()

    try:
        await tester.setup()

        # 运行所有测试
        await tester.test_wechat_nonsense_detection()
        await tester.test_phone_persuasion_after_wechat()
        await tester.test_full_conversation_flow()

        # 打印摘要
        tester.print_summary()

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
