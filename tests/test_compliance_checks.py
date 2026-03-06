"""
合规检测自动化测试

测试场景：
1. 年龄限制（< 24岁）
2. LGBT用户检测
3. 已婚用户检测
4. 虚假信息检测
5. 骚扰/广告检测
6. 代相亲检测
7. 分居中检测
8. 离异未办妥检测
9. 正常用户（应该通过）
10. 边界情况
"""


class TestComplianceChecks:
    """合规检测测试类"""

    def __init__(self):
        self.test_results = []

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

    # ============ 年龄限制测试 ============

    def test_age_limit(self):
        """测试年龄限制检测"""
        print("\n" + "="*60)
        print("1. 年龄限制测试")
        print("="*60)

        test_cases = [
            ("我今年16岁", True, "16岁 < 24岁"),
            ("我今年18岁", True, "18岁 < 24岁"),
            ("我今年20岁", True, "20岁 < 24岁"),
            ("我今年23岁", True, "23岁 < 24岁"),
            ("我今年24岁", False, "24岁 >= 24岁， 应通过"),
            ("我今年25岁", False, "25岁 >= 24岁, 应通过"),
            ("我今年30岁", False, "30岁 >= 24岁, 应通过"),
            ("我今年50岁", False, "50岁 >= 24岁, 应通过"),
        ]

        for user_input, expected_reject, description in test_cases:
            age = self._parse_age_from_input(user_input)
            is_reject = age is not None and age < 24
            passed = is_reject == expected_reject
            self.log_result(
                f"年龄限制: '{user_input}'",
                passed,
                f"{description} | 解析年龄: {age}, 拒绝: {is_reject}"
            )

    def _parse_age_from_input(self, text: str) -> int:
        """从输入中解析年龄"""
        import re
        match = re.search(r'(\d{1,3})\s*岁?', text)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d{1,3})', text)
        if match:
            return int(match.group(1))
        return None

    # ============ LGBT用户测试 ============

    def test_lgbt_detection(self):
        """测试LGBT用户检测"""
        print("\n" + "="*60)
        print("2. LGBT用户测试")
        print("="*60)

        test_cases = [
            ("我是gay", True),
            ("我是les", True),
            ("我喜欢女生", True),
            ("我喜欢男的", True),
            ("我是同性恋", True),
            ("我是百合", True),
            ("我是拉拉", True),
            ("你好", False),
            ("我今年28岁", False),
            ("我想找女朋友", False),
        ]

        for user_input, expected_reject in test_cases:
            detected = self._detect_lgbt(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"LGBT检测: '{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_lgbt(self, text: str) -> bool:
        """检测LGBT关键词"""
        lgbt_keywords = [
            '同性恋', 'gay', '拉拉', 'les', 'lesbian',
            '百合', '女同', '我喜欢女生', '我喜欢男的',
            '我是les', '我是gay', '同志'
        ]
        text_lower = text.lower()
        for keyword in lgbt_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    # ============ 已婚用户测试 ============

    def test_married_detection(self):
        """测试已婚用户检测"""
        print("\n" + "="*60)
        print("3. 已婚用户测试")
        print("="*60)

        test_cases = [
            ("我结婚了", True),
            ("我已经结婚了", True),
            ("我有老婆", True),
            ("我有老公", True),
            ("我已婚", True),
            ("家里有老婆", True),
            ("家里有老公", True),
            ("我不是单身", True),
            ("我单身", False),
            ("我离异了", False),
            ("你好", False),
        ]

        for user_input, expected_reject in test_cases:
            detected = self._detect_married(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"已婚检测: '{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_married(self, text: str) -> bool:
        """检测已婚关键词"""
        married_keywords = [
            '我结婚了', '我已经结婚了', '我有老公', '我有老婆',
            '我有丈夫', '我有妻子', '我已婚', '已婚了',
            '家里有老婆', '家里有老公', '我有爱人', '我有对象',
            '我不是单身', '我有伴了'
        ]
        for keyword in married_keywords:
            if keyword in text:
                return True
        return False
    # ============ 虚假信息测试 ============

    def test_fake_info_detection(self):
        """测试虚假信息检测"""
        print("\n" + "="*60)
        print("4. 虚假信息测试")
        print("="*60)

        test_cases = [
            ("我身高300cm", True, "身高 > 250"),
            ("我身高500cm", True, "身高 > 250"),
            ("我体重500kg", True, "体重 > 300"),
            ("我体重1000kg", True, "体重 > 300"),
            ("我今年100岁", True, "年龄 > 80"),
            ("我今年200岁", True, "年龄 > 80"),
            ("我身高180cm", False, "身高正常"),
            ("我体重70kg", False, "体重正常"),
            ("我今年28岁", False, "年龄正常"),
        ]

        for user_input, expected_reject, description in test_cases:
            detected = self._detect_fake_info(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"虚假信息: '{user_input}'",
                passed,
                f"{description}, 检测结果: {detected}"
            )

    def _detect_fake_info(self, text: str) -> bool:
        """检测虚假信息"""
        import re
        # 身高检测
        height_match = re.search(r'(\d{1,3})\s*(cm|厘米)?', text)
        if height_match:
            height = int(height_match.group(1))
            if height > 250:
                return True
        # 体重检测
        weight_match = re.search(r'(\d{1,3})\s*(kg|公斤)?', text)
        if weight_match:
            weight = int(weight_match.group(1))
            if weight > 300:
                return True
        # 年龄检测
        age_match = re.search(r'(\d{1,3})\s*岁?', text)
        if age_match:
            age = int(age_match.group(1))
            if age > 80:
                return True
        return False
    # ============ 骚扰/广告测试 ============

    def test_spam_detection(self):
        """测试骚扰/广告检测"""
        print("\n" + "="*60)
        print("5. 骚扰/广告测试")
        print("="*60)

        test_cases = [
            ("加微信：xxx123", True),
            ("加我微信：abc456", True),
            ("联系我：13800138000", True),
            ("私聊：13800138000", True),
            ("点击链接：http://xxx.com", True),
            ("关注公众号：xxx", True),
            ("你好", False),
            ("我想找对象", False),
        ]

        for user_input, expected_reject in test_cases:
            detected = self._detect_spam(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"骚扰/广告: '{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_spam(self, text: str) -> bool:
        """检测骚扰/广告关键词"""
        spam_keywords = [
            '加微信', '加我微信', '联系我', '私聊',
            '点击链接', '关注公众号', '加q群', '扫二维码',
            '加qq', '加Q群', '私信我'
        ]
        for keyword in spam_keywords:
            if keyword in text:
                return True
        return False
    # ============ 代相亲测试 ============

    def test_proxy_detection(self):
        """测试代相亲检测"""
        print("\n" + "="*60)
        print("6. 代相亲测试")
        print("="*60)

        test_cases = [
            ("帮朋友问问", True),
            ("帮我问问", True),
            ("帮家人问", True),
            ("替朋友问", True),
            ("我帮同事问", True),
            ("你好", False),
            ("我想找对象", False),
        ]

        for user_input, expected_reject in test_cases:
            detected = self._detect_proxy(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"代相亲: '{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_proxy(self, text: str) -> bool:
        """检测代相亲关键词"""
        proxy_keywords = [
            '帮朋友', '帮家人', '帮同事', '替朋友', '帮亲戚',
            '帮我妈', '帮我爸', '帮兄弟', '帮姐妹', '代问'
        ]
        for keyword in proxy_keywords:
            if keyword in text:
                return True
        return False
    # ============ 分居中测试 ============

    def test_separated_detection(self):
        """测试分居中检测"""
        print("\n" + "="*60)
        print("7. 分居中测试")
        print("="*60)

        test_cases = [
            ("我分居中", True),
            ("正在分居", True),
            ("还没离", True),
            ("手续没办", True),
            ("还没办好", True),
            ("正在办手续", True),
            ("我离异了", False),
            ("你好", False),
        ]

        for user_input, expected_reject in test_cases:
            detected = self._detect_separated(user_input)
            passed = detected == expected_reject
            self.log_result(
                f"分居中: '{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_separated(self, text: str) -> bool:
        """检测分居中关键词"""
        separated_keywords = [
            '分居中', '正在分居', '还没离',
            '手续没办', '还没办好', '正在办手续', '办理中',
        ]
        for keyword in separated_keywords:
            if keyword in text:
                return True
        return False
    # ============ 离异未办妥测试 ============

    def test_divorce_incomplete_detection(self):
        """测试离异未办妥检测（结合婚况状态）"""
        print("\n" + "="*60)
        print("8. 离异未办妥测试")
        print("="*60)

        test_cases = [
            # (婚况, 用户输入, 期望拒绝)
            ("离异", "还没办好", True),
            ("离异", "正在办", True),
            ("离异", "手续没办", True),
            ("离异", "办好了", False),
            ("离异", "已办妥", False),
            ("单身", "还没办好", False),  # 单身用户说这个不应该拒绝
        ]

        for marital_status, user_input, expected_reject in test_cases:
            detected = self._detect_divorce_incomplete(marital_status, user_input)
            passed = detected == expected_reject
            self.log_result(
                f"离异未办妥: 婚况={marital_status}, 输入='{user_input}'",
                passed,
                f"期望拒绝: {expected_reject}, 实际: {detected}"
            )

    def _detect_divorce_incomplete(self, marital_status: str, text: str) -> bool:
        """检测离异未办妥"""
        if marital_status != '离异' and '离异' not in str(marital_status):
            return False
        incomplete_keywords = [
            '还没办好', '还没办妥', '还没办', '正在办', '办理中',
            '正在办理', '手续没办', '还没离', '办手续中', '分居中', '正在分居'
        ]
        for keyword in incomplete_keywords:
            if keyword in text:
                return True
        return False
    # ============ 正常用户测试 ============

    def test_normal_user(self):
        """测试正常用户（应该通过）"""
        print("\n" + "="*60)
        print("9. 正常用户测试（应该通过）")
        print("="*60)

        normal_inputs = [
            "你好",
            "我今年28岁",
            "我叫小明",
            "我身高175cm",
            "我在深圳工作",
            "我本科毕业",
            "我想找个女朋友",
            "我离异了",
            "我单身",
        ]

        for user_input in normal_inputs:
            # 检查所有检测
            is_lgbt = self._detect_lgbt(user_input)
            is_married = self._detect_married(user_input)
            is_spam = self._detect_spam(user_input)
            is_proxy = self._detect_proxy(user_input)
            is_separated = self._detect_separated(user_input)
            is_fake = self._detect_fake_info(user_input)

            should_pass = not any([is_lgbt, is_married, is_spam, is_proxy, is_separated, is_fake])
            passed = should_pass
            self.log_result(
                f"正常用户: '{user_input}'",
                passed,
                f"所有检测: {should_pass}"
            )

    # ============ 边界情况测试 ============

    def test_edge_cases(self):
        """测试边界情况"""
        print("\n" + "="*60)
        print("10. 边界情况测试")
        print("="*60)

        # 年龄边界
        edge_cases = [
            ("我今年24岁", False, "24岁 = 边界， 应通过"),
            ("我今年23岁", True, "23岁 < 边界, 应拒绝"),
            ("我身高250cm", False, "250cm = 边界, 应通过"),
            ("我身高251cm", True, "251cm > 边界, 应拒绝"),
            ("我体重300kg", False, "300kg = 边界, 应通过"),
            ("我体重301kg", True, "301kg > 边界, 应拒绝"),
            ("我今年80岁", False, "80岁 = 边界, 应通过"),
            ("我今年81岁", True, "81岁 > 边界, 应拒绝"),
        ]

        for user_input, expected_reject, description in edge_cases:
            is_fake = self._detect_fake_info(user_input)
            age = self._parse_age_from_input(user_input)
            if age is not None:
                is_reject = age < 24
            else:
                is_reject = is_fake

            passed = is_reject == expected_reject
            self.log_result(
                f"边界情况: '{user_input}'",
                passed,
                f"{description}, 拒绝: {is_reject}"
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

    def run_all_tests(self):
        """运行所有测试"""
        self.test_age_limit()
        self.test_lgbt_detection()
        self.test_married_detection()
        self.test_fake_info_detection()
        self.test_spam_detection()
        self.test_proxy_detection()
        self.test_separated_detection()
        self.test_divorce_incomplete_detection()
        self.test_normal_user()
        self.test_edge_cases()
        self.print_summary()


def main():
    """主测试函数"""
    tester = TestComplianceChecks()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
