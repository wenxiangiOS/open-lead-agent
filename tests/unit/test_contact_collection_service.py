"""
ContactCollectionService 单元测试

测试联系方式收集服务的核心功能
"""

import pytest
from src.services.collection.contact_collection_service import (
    ContactCollectionService,
    ContactFlowState,
    NextAction,
    RefusalResult
)
from src.models.user_profile import UserProfile


class TestContactCollectionService:
    """联系方式收集服务测试"""

    def setup_method(self):
        """每个测试前重置"""
        self.service = ContactCollectionService()

    # ==================== is_hongkong_user 测试 ====================

    def test_is_hongkong_user_with_hongkong(self):
        """香港用户识别 - 香港地区"""
        profile = UserProfile(account_id="test", location="香港")
        assert self.service.is_hongkong_user(profile) == True

    def test_is_hongkong_user_with_hk(self):
        """香港用户识别 - HK缩写"""
        profile = UserProfile(account_id="test", location="HK")
        assert self.service.is_hongkong_user(profile) == True

    def test_is_hongkong_user_with_beijing(self):
        """香港用户识别 - 非香港地区"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.is_hongkong_user(profile) == False

    def test_is_hongkong_user_with_none(self):
        """香港用户识别 - 无地区"""
        profile = UserProfile(account_id="test", location=None)
        assert self.service.is_hongkong_user(profile) == False

    def test_is_hongkong_user_cached(self):
        """香港用户识别 - 缓存测试"""
        profile = UserProfile(account_id="test", location="香港")
        # 第一次调用
        self.service.is_hongkong_user(profile)
        # 检查缓存
        assert profile.is_hongkong_user == True
        # 第二次调用应该使用缓存
        profile.location = "北京"  # 修改不影响缓存
        assert self.service.is_hongkong_user(profile) == True

    # ==================== get_max_asks 测试 ====================

    def test_get_max_asks_phone(self):
        """电话最大询问次数 - 始终2次"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.get_max_asks(profile, 'phone') == 2

    def test_get_max_asks_wechat_hongkong(self):
        """微信最大询问次数 - 香港用户"""
        profile = UserProfile(account_id="test", location="香港")
        assert self.service.get_max_asks(profile, 'wechat') == 2

    def test_get_max_asks_wechat_non_hk_with_phone(self):
        """微信最大询问次数 - 非香港用户 + 电话已收集"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_collected = True
        assert self.service.get_max_asks(profile, 'wechat') == 1

    def test_get_max_asks_wechat_non_hk_without_phone(self):
        """微信最大询问次数 - 非香港用户 + 电话未收集"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.get_max_asks(profile, 'wechat') == 2

    # ==================== get_next_action 测试 ====================

    def test_get_next_action_both_rejected(self):
        """下一步动作 - 双方都被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        assert self.service.get_next_action(profile) == NextAction.END_CONVERSATION

    def test_get_next_action_wechat_rejected_ask_phone(self):
        """下一步动作 - 微信被拒绝，询问电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_wechat = True
        assert self.service.get_next_action(profile) == NextAction.ASK_PHONE

    def test_get_next_action_wechat_rejected_persuade_phone(self):
        """下一步动作 - 微信被拒绝，争取电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_wechat = True
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_PHONE

    def test_get_next_action_phone_rejected_ask_wechat(self):
        """下一步动作 - 电话被拒绝，询问微信"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        assert self.service.get_next_action(profile) == NextAction.ASK_WECHAT

    def test_get_next_action_phone_rejected_persuade_wechat_hk(self):
        """下一步动作 - 电话被拒绝，争取微信（香港用户）"""
        profile = UserProfile(account_id="test", location="香港")
        profile.rejected_phone = True
        profile.wechat_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_WECHAT

    def test_get_next_action_normal_ask_phone(self):
        """下一步动作 - 正常流程，询问电话"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.get_next_action(profile) == NextAction.ASK_PHONE

    def test_get_next_action_hk_phone_collected_ask_wechat(self):
        """下一步动作 - 香港用户电话已收集，询问微信"""
        profile = UserProfile(account_id="test", location="香港")
        profile.phone_collected = True
        assert self.service.get_next_action(profile) == NextAction.ASK_WECHAT

    def test_get_next_action_non_hk_phone_collected_ask_wechat(self):
        """下一步动作 - 非香港用户电话已收集，询问微信（仅1次）"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_collected = True
        assert self.service.get_next_action(profile) == NextAction.ASK_WECHAT

    def test_get_next_action_non_hk_phone_collected_wechat_asked(self):
        """下一步动作 - 非香港用户电话已收集，微信已问过"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.NONE

    def test_get_next_action_prefers_wechat_over_phone(self):
        """下一步动作 - 用户明确想用微信替代电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile, "电话不方便，留微信可以吗") == NextAction.ASK_WECHAT

    def test_get_next_action_soft_ack_after_phone_flow_switches_to_wechat(self):
        """下一步动作 - 非香港用户低信息确认后不继续追问电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile, "嗯") == NextAction.ASK_WECHAT

    def test_get_next_action_soft_ack_does_not_switch_hk_phone_flow(self):
        """下一步动作 - 香港用户仍保持电话优先"""
        profile = UserProfile(account_id="test", location="香港")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile, "嗯") == NextAction.PERSUADE_PHONE

    def test_get_flow_state_phone_requested(self):
        """显式流程状态 - 首次询问电话"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.get_flow_state(profile) == ContactFlowState.PHONE_REQUESTED

    def test_get_flow_state_contact_closed(self):
        """显式流程状态 - 双拒后关闭"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        assert self.service.get_flow_state(profile) == ContactFlowState.CONTACT_CLOSED

    def test_get_flow_snapshot_contains_current_action_and_flags(self):
        """显式流程快照 - 包含状态、动作和核心标志"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        snapshot = self.service.get_flow_snapshot(profile)
        assert snapshot.state == ContactFlowState.WECHAT_REQUESTED
        assert snapshot.next_action == NextAction.ASK_WECHAT
        assert snapshot.phone_collected is True
        assert snapshot.wechat_collected is False

    # ==================== build_instruction 测试 ====================

    def test_build_instruction_end_conversation(self):
        """构建指令 - 结束对话（收尾由 prompts.py 统一处理）"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        instruction, action = self.service.build_instruction(profile)
        assert action == NextAction.END_CONVERSATION
        # 收尾逻辑统一由 prompts.py 处理，这里返回空指令
        assert instruction == ""

    def test_build_instruction_ask_phone(self):
        """构建指令 - 询问电话"""
        profile = UserProfile(account_id="test", location="北京")
        instruction, action = self.service.build_instruction(profile)
        assert action == NextAction.ASK_PHONE
        assert "电话" in instruction

    def test_build_instruction_returns_tuple(self):
        """构建指令 - 返回元组"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.build_instruction(profile)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], NextAction)

    def test_build_instruction_prefers_wechat_over_phone(self):
        """构建指令 - 用户主动提出留微信时应接住微信方案"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        instruction, action = self.service.build_instruction(profile, "电话不方便，留微信可以吗")
        assert action == NextAction.ASK_WECHAT
        assert "微信" in instruction
        assert "电话" not in instruction

    # ==================== detect_refusal 测试 ====================

    def test_detect_refusal_explicit_phone(self):
        """拒绝检测 - 显式拒绝电话"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal("不留电话", profile, None)
        assert result is not None
        assert result.contact_type == 'phone'
        assert result.is_refusal == True

    def test_detect_refusal_explicit_wechat(self):
        """拒绝检测 - 显式拒绝微信"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal("不留微信", profile, None)
        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_refusal == True

    def test_detect_refusal_explicit_wechat_reverse_phrase(self):
        """拒绝检测 - 反向表述的微信拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal("微信也不留", profile, None)
        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_refusal == True

    def test_detect_refusal_general_with_context(self):
        """拒绝检测 - 通用拒绝 + 上下文"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal(
            "不用了",
            profile,
            "方便留个电话吗？"
        )
        assert result is not None
        assert result.contact_type == 'phone'

    def test_detect_refusal_general_with_wechat_context(self):
        """拒绝检测 - 微信上下文中的通用拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "17688654321"
        profile.phone_collected = True
        result = self.service.detect_refusal(
            "先不留了",
            profile,
            "好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～"
        )
        assert result is not None
        assert result.contact_type == 'wechat'

    def test_detect_refusal_no_refusal(self):
        """拒绝检测 - 无拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal("好的，我叫张三", profile, None)
        assert result is None

    def test_detect_refusal_updates_ask_count(self):
        """拒绝检测 - 拒绝时递增询问次数"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 0
        result = self.service.detect_refusal("不留电话", profile, None)
        # 拒绝后，计数器应该递增
        assert profile.phone_ask_count == 1
        assert result is not None
        assert result.is_refusal == True

    def test_detect_refusal_marks_final_rejection(self):
        """拒绝检测 - 标记最终拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2  # 已达到上限
        result = self.service.detect_refusal("不留电话", profile, None)
        assert result.is_final == True
        assert profile.rejected_phone == True

    # ==================== get_status_display 测试 ====================

    def test_get_status_display_none(self):
        """状态显示 - 未留"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.get_status_display(profile) == "未留"

    def test_get_status_display_phone_collected(self):
        """状态显示 - 电话已收集"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        assert "电话: 13800138000" in self.service.get_status_display(profile)

    def test_get_status_display_wechat_collected(self):
        """状态显示 - 微信已收集"""
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat = "test_wx"
        profile.wechat_collected = True
        assert "微信: test_wx" in self.service.get_status_display(profile)

    def test_get_status_display_both_collected(self):
        """状态显示 - 都已收集"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat = "test_wx"
        profile.wechat_collected = True
        status = self.service.get_status_display(profile)
        assert "电话: 13800138000" in status
        assert "微信: test_wx" in status

    def test_get_status_display_phone_rejected(self):
        """状态显示 - 电话被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        assert "不愿留电话" in self.service.get_status_display(profile)

    def test_get_status_display_wechat_rejected(self):
        """状态显示 - 微信被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_wechat = True
        assert "不愿留微信" in self.service.get_status_display(profile)

    def test_get_status_display_both_rejected(self):
        """状态显示 - 都被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        status = self.service.get_status_display(profile)
        assert "不愿留电话" in status
        assert "不愿留微信" in status

    def test_get_status_display_phone_asking(self):
        """状态显示 - 电话争取中"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert "电话争取中" in self.service.get_status_display(profile)

    def test_get_status_display_wechat_asking(self):
        """状态显示 - 微信争取中"""
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat_ask_count = 1
        assert "微信争取中" in self.service.get_status_display(profile)

    # ==================== get_action_dict 测试 ====================

    def test_get_action_dict_ask_phone(self):
        """动作字典 - 询问电话"""
        d = self.service.get_action_dict(NextAction.ASK_PHONE)
        assert d['ask_phone'] == True
        assert d['ask_wechat'] == False
        assert d['end'] == False

    def test_get_action_dict_ask_wechat(self):
        """动作字典 - 询问微信"""
        d = self.service.get_action_dict(NextAction.ASK_WECHAT)
        assert d['ask_phone'] == False
        assert d['ask_wechat'] == True
        assert d['end'] == False

    def test_get_action_dict_end(self):
        """动作字典 - 结束对话"""
        d = self.service.get_action_dict(NextAction.END_CONVERSATION)
        assert d['ask_phone'] == False
        assert d['ask_wechat'] == False
        assert d['end'] == True

    def test_get_action_dict_persuade_phone(self):
        """动作字典 - 争取电话"""
        d = self.service.get_action_dict(NextAction.PERSUADE_PHONE)
        assert d['ask_phone'] == True
        assert d['ask_wechat'] == False
        assert d['end'] == False

    def test_get_action_dict_persuade_wechat(self):
        """动作字典 - 争取微信"""
        d = self.service.get_action_dict(NextAction.PERSUADE_WECHAT)
        assert d['ask_phone'] == False
        assert d['ask_wechat'] == True
        assert d['end'] == False

    # ==================== should_end_conversation 测试 ====================

    def test_should_end_conversation_both_rejected(self):
        """是否结束对话 - 双方都被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        assert self.service.should_end_conversation(profile) == True

    def test_should_end_conversation_one_rejected(self):
        """是否结束对话 - 只有一方被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        assert self.service.should_end_conversation(profile) == False

    def test_should_end_conversation_none_rejected(self):
        """是否结束对话 - 都没有被拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.should_end_conversation(profile) == False

    # ==================== record_* 方法测试 ====================

    def test_record_ask_phone(self):
        """记录询问 - 电话"""
        profile = UserProfile(account_id="test", location="北京")
        count = self.service.record_ask(profile, 'phone')
        assert count == 1
        assert profile.phone_ask_count == 1

    def test_record_ask_wechat(self):
        """记录询问 - 微信"""
        profile = UserProfile(account_id="test", location="北京")
        count = self.service.record_ask(profile, 'wechat')
        assert count == 1
        assert profile.wechat_ask_count == 1

    def test_record_rejection_phone(self):
        """记录拒绝 - 电话"""
        profile = UserProfile(account_id="test", location="北京")
        self.service.record_rejection(profile, 'phone')
        assert profile.rejected_phone == True

    def test_record_rejection_wechat(self):
        """记录拒绝 - 微信"""
        profile = UserProfile(account_id="test", location="北京")
        self.service.record_rejection(profile, 'wechat')
        assert profile.rejected_wechat == True

    def test_record_collection_phone(self):
        """记录收集 - 电话"""
        profile = UserProfile(account_id="test", location="北京")
        self.service.record_collection(profile, 'phone', '13800138000')
        assert profile.phone == '13800138000'
        assert profile.phone_collected == True

    def test_record_collection_wechat(self):
        """记录收集 - 微信"""
        profile = UserProfile(account_id="test", location="北京")
        self.service.record_collection(profile, 'wechat', 'test_wx')
        assert profile.wechat == 'test_wx'
        assert profile.wechat_collected == True
