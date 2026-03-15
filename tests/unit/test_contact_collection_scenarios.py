"""
联系方式收集逻辑全面测试

测试所有场景：
1. 电话、微信均被拒绝
2. 仅拒绝其中一种联系方式
3. 用户主动提供联系方式
4. AI主动询问联系方式（香港用户/非香港用户）
"""

import pytest
from src.models.user_profile import UserProfile
from src.services.collection.contact_collection_service import ContactCollectionService


class TestContactCollectionScenarios:
    """测试联系方式收集的所有场景"""

    def setup_method(self):
        """每个测试前重置"""
        pass

    # ==========================================
    # 场景1: 电话、微信均被拒绝
    # ==========================================

    def test_both_rejected_phone_first(self):
        """先拒绝电话2次，再询问微信，微信也拒绝"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 第一次拒绝电话
        profile.rejected_phone = False
        profile.phone_ask_count = 0
        
        # 模拟第一次询问电话后拒绝
        profile.increment_phone_ask_count()
        assert profile.phone_ask_count == 1
        
        # 模拟第二次询问电话后拒绝（达到限制）
        profile.increment_phone_ask_count()
        assert profile.phone_ask_count == 2
        profile.rejected_phone = True
        
        # 现在应该询问微信
        assert profile.can_ask_wechat() == True
        
        # 拒绝微信2次
        profile.increment_wechat_ask_count()
        profile.increment_wechat_ask_count()
        profile.rejected_wechat = True
        
        # 都被拒绝，应该结束
        assert profile.rejected_phone and profile.rejected_wechat

        contact_status = profile.get_contact_status()
        assert "不愿留电话" in contact_status
        assert "不愿留微信" in contact_status

    def test_both_rejected_wechat_first(self):
        """先拒绝微信2次，再询问电话，电话也拒绝"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 拒绝微信2次
        profile.increment_wechat_ask_count()
        profile.increment_wechat_ask_count()
        profile.rejected_wechat = True
        
        # 现在应该询问电话
        assert profile.can_ask_phone() == True
        
        # 拒绝电话2次
        profile.increment_phone_ask_count()
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        # 都被拒绝
        contact_status = profile.get_contact_status()
        assert "不愿留电话" in contact_status
        assert "不愿留微信" in contact_status

    # ==========================================
    # 场景2: 仅拒绝其中一种联系方式
    # ==========================================

    def test_reject_phone_only_provide_wechat(self):
        """拒绝电话，但提供微信"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 拒绝电话2次
        profile.increment_phone_ask_count()
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        # 提供微信
        profile.wechat = "test_wx"
        profile.wechat_collected = True
        
        contact_status = profile.get_contact_status()
        assert "不愿留电话" in contact_status
        assert "微信: test_wx" in contact_status

    def test_reject_wechat_only_provide_phone(self):
        """拒绝微信，但提供电话"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 拒绝微信2次
        profile.increment_wechat_ask_count()
        profile.increment_wechat_ask_count()
        profile.rejected_wechat = True
        
        # 提供电话
        profile.phone = "13800138000"
        profile.phone_collected = True
        
        contact_status = profile.get_contact_status()
        assert "电话: 13800138000" in contact_status
        assert "不愿留微信" in contact_status

    def test_phone_rejected_then_ask_wechat(self):
        """拒绝电话后，询问微信"""
        profile = UserProfile(account_id="test_user", location="北京")

        # 拒绝电话1次
        profile.increment_phone_ask_count()
        assert profile.phone_ask_count == 1

        # 拒绝电话第2次
        profile.increment_phone_ask_count()
        profile.rejected_phone = True

        # 非香港用户，电话被拒绝（不是已收集），微信最多2次
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 2  # 电话被拒绝时，微信最多2次

        # 可以询问微信
        assert profile.can_ask_wechat() == True

    # ==========================================
    # 场景3: 用户主动提供联系方式
    # ==========================================

    def test_user_provides_phone_hongkong(self):
        """香港用户主动提供电话， 再询问微信最多2次"""
        profile = UserProfile(account_id="test_hk", location="香港")
        
        # 主动提供电话
        profile.phone = "51234567"
        profile.phone_collected = True
        
        # 香港用户，微信最多2次
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 2
        
        # 可以询问微信
        assert profile.can_ask_wechat() == True
        
        # 拒绝微信1次
        profile.increment_wechat_ask_count()
        assert profile.can_ask_wechat() == True  # 还可以问
        
        # 拒绝微信2次
        profile.increment_wechat_ask_count()
        assert profile.can_ask_wechat() == False  # 不能再问了

        profile.rejected_wechat = True
        
        contact_status = profile.get_contact_status()
        assert "电话: 51234567" in contact_status
        assert "不愿留微信" in contact_status

    def test_user_provides_phone_non_hongkong(self):
        """非香港用户主动提供电话, 再询问微信最多1次"""
        profile = UserProfile(account_id="test_bj", location="北京")
        
        # 主动提供电话
        profile.phone = "13800138000"
        profile.phone_collected = True
        
        # 非香港用户，电话已收集，微信最多1次
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 1
        
        # 可以询问微信
        assert profile.can_ask_wechat() == True
        
        # 拒绝微信1次
        profile.increment_wechat_ask_count()
        assert profile.can_ask_wechat() == False  # 不能再问了
        
        profile.rejected_wechat = True
        
        contact_status = profile.get_contact_status()
        assert "电话: 13800138000" in contact_status
        assert "不愿留微信" in contact_status

    def test_user_provides_wechat_then_phone(self):
        """用户主动提供微信, 再询问电话"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 主动提供微信
        profile.wechat = "test_wx"
        profile.wechat_collected = True
        
        # 电话最多2次
        assert profile.can_ask_phone() == True
        
        # 拒绝电话2次
        profile.increment_phone_ask_count()
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        contact_status = profile.get_contact_status()
        assert "不愿留电话" in contact_status
        assert "微信: test_wx" in contact_status

    # ==========================================
    # 场景4: AI主动询问联系方式
    # ==========================================

    def test_ai_ask_hongkong_user(self):
        """香港用户: AI依次询问电话、微信, 各最多2次"""
        profile = UserProfile(account_id="test_hk", location="香港")
        
        # 验证是香港用户
        assert profile.check_is_hongkong_user() == True
        
        # 电话最多2次
        max_phone = 2
        assert profile.can_ask_phone() == True
        
        # 拒绝电话1次
        profile.increment_phone_ask_count()
        assert profile.can_ask_phone() == True
        
        # 拒绝电话2次
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        # 微信最多2次
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 2
        assert profile.can_ask_wechat() == True

    def test_ai_ask_non_hongkong_user_phone_rejected(self):
        """非香港用户: AI先询问电话, 用户拒绝后再询问微信"""
        profile = UserProfile(account_id="test_bj", location="北京")
        
        # 验证不是香港用户
        assert profile.check_is_hongkong_user() == False
        
        # 电话最多2次
        assert profile.can_ask_phone() == True
        
        # 拒绝电话1次
        profile.increment_phone_ask_count()
        assert profile.can_ask_phone() == True
        
        # 拒绝电话2次
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        # 电话被拒绝后, 微信最多2次（因为电话未收集）
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 2

    def test_ai_ask_non_hongkong_user_phone_collected(self):
        """非香港用户: AI询问电话成功后, 微信最多1次"""
        profile = UserProfile(account_id="test_bj", location="北京")
        
        # 用户提供电话
        profile.phone = "13800138000"
        profile.phone_collected = True
        
        # 电话已收集, 微信最多1次
        max_wechat = profile.get_max_wechat_asks()
        assert max_wechat == 1
        
        assert profile.can_ask_wechat() == True
        
        # 拒绝微信1次
        profile.increment_wechat_ask_count()
        assert profile.can_ask_wechat() == False  # 不能再问

    def test_contact_status_display(self):
        """测试状态显示的各种情况"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 初始状态
        assert profile.get_contact_status() == "未留"
        
        # 电话争取中
        profile.phone_ask_count = 1
        assert profile.get_contact_status() == "电话争取中"
        
        # 有电话
        profile.phone = "13800138000"
        profile.phone_collected = True
        assert "电话: 13800138000" in profile.get_contact_status()
        
        # 微信争取中
        profile.wechat_ask_count = 1
        status = profile.get_contact_status()
        assert "电话: 13800138000" in status
        assert "微信争取中" in status
        
        # 都有
        profile.wechat = "test_wx"
        profile.wechat_collected = True
        status = profile.get_contact_status()
        assert "电话: 13800138000" in status
        assert "微信: test_wx" in status

    def test_both_not_collected_end_conversation(self):
        """电话和微信均未收集成功 -> 执行收尾结束"""
        profile = UserProfile(account_id="test_user", location="北京")
        
        # 拒绝电话
        profile.increment_phone_ask_count()
        profile.increment_phone_ask_count()
        profile.rejected_phone = True
        
        # 拒绝微信
        profile.increment_wechat_ask_count()
        profile.increment_wechat_ask_count()
        profile.rejected_wechat = True
        
        # 验证都未收集成功
        assert profile.rejected_phone == True
        assert profile.rejected_wechat == True
        
        # 状态显示
        status = profile.get_contact_status()
        assert "不愿留电话" in status
        assert "不愿留微信" in status

    def test_build_contact_instruction_both_rejected(self):
        """测试 ContactCollectionService: 双方都被拒绝"""
        service = ContactCollectionService()
        profile = UserProfile(account_id="test_user", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True

        instruction, action = service.build_instruction(profile)
        next_action = service.get_action_dict(action)

        assert next_action['end'] == True
        # 修改：匹配模板中的关键词，        assert "结束对话" in instruction or "有需要" in instruction

    def test_build_contact_instruction_phone_rejected(self):
        """测试 ContactCollectionService: 电话被拒绝, 询问微信"""
        service = ContactCollectionService()
        profile = UserProfile(account_id="test_user", location="北京")
        profile.rejected_phone = True
        profile.phone_ask_count = 2

        instruction, action = service.build_instruction(profile)
        next_action = service.get_action_dict(action)

        assert next_action['ask_wechat'] == True
        assert "微信" in instruction

    def test_build_contact_instruction_normal_flow(self):
        """测试 ContactCollectionService: 正常流程"""
        service = ContactCollectionService()
        profile = UserProfile(account_id="test_user", location="北京")

        instruction, action = service.build_instruction(profile)
        next_action = service.get_action_dict(action)

        # 应该询问电话
        assert next_action['ask_phone'] == True
