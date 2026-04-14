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
        profile.phone = "13800138000"
        assert self.service.get_next_action(profile) == NextAction.ASK_WECHAT

    def test_detect_refusal_does_not_pollute_contact_state_when_only_next_action_is_contact(self):
        """问学历时的通用拒绝不应仅因潜在 next_action=ask_phone 被算成电话拒绝。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.sex = "女"
        profile.age = 28
        profile.education = None
        profile.occupation = "IT"
        profile.location = "深圳"
        profile.monthly_income = "5万"
        profile.marital_status = "单身"

        result = self.service.detect_refusal("不方便说", profile, "你是什么学历呀？")

        assert result is None
        assert profile.phone_ask_count == 0
        assert profile.rejected_phone is False

    def test_get_next_action_non_hk_phone_collected_wechat_asked(self):
        """下一步动作 - 非香港用户电话已收集，微信已问过"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_collected = True
        profile.phone = "13800138000"
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.NONE

    def test_is_contact_complete_non_hk_after_phone_collected_and_wechat_asked_once(self):
        """非香港用户电话已收后，微信有效问满1次即视为联系方式流程完成。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1

        assert self.service.is_contact_complete(profile) is True

    def test_is_contact_complete_when_both_channels_maxed_without_collection(self):
        """电话和微信都有效问满时，即使都未收集也应视为联系方式流程完成。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.wechat_ask_count = 2
        profile.wechat_effective_ask_count = 2

        assert self.service.is_contact_complete(profile) is True

    def test_get_next_action_none_when_wechat_invalid_input_closed_after_phone_collected(self):
        """电话已收且微信因连续无效输入关闭后，不应继续主动追微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_invalid_input_closed = True

        assert self.service.get_next_action(profile) == NextAction.NONE

    def test_get_next_action_prefers_wechat_over_phone(self):
        """下一步动作 - 用户明确想用微信替代电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile, "电话不方便，留微信可以吗") == NextAction.ASK_WECHAT
        assert profile.pending_contact_field == "phone"
        assert profile.pending_contact_hint == "channel_switch"

    def test_get_next_action_prefers_wechat_over_phone_with_colloquial_phrase(self):
        """下一步动作 - `微信可以不` 也应识别为渠道切换，不是继续劝电话。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile, "微信可以不") == NextAction.ASK_WECHAT
        assert profile.pending_contact_field == "phone"
        assert profile.pending_contact_hint == "channel_switch"

    def test_get_next_action_after_phone_attempt_keeps_persuade_phone_for_non_hk(self):
        """下一步动作 - 非香港用户电话首次询问后，继续第二次电话追问"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_PHONE

    def test_get_next_action_after_both_contact_attempts_continues_wechat_persuasion(self):
        """下一步动作 - 双渠道都推进过后，仍按状态机继续微信流程"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        profile.wechat_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_WECHAT

    def test_get_next_action_hk_phone_flow_keeps_persuade_phone(self):
        """下一步动作 - 香港用户电话流程保持电话优先"""
        profile = UserProfile(account_id="test", location="香港")
        profile.phone_ask_count = 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_PHONE

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
        assert "结束对话" in instruction
        assert "不再索要联系方式" in instruction

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

    def test_get_next_action_resumes_phone_after_wechat_collected_from_channel_switch(self):
        """渠道切换先收微信后，应恢复电话，不继续停留在微信分支。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        profile.wechat = "abc123"
        profile.wechat_collected = True
        profile.pending_contact_field = "phone"
        profile.pending_contact_hint = "channel_switch"

        assert self.service.get_next_action(profile) == NextAction.ASK_PHONE

    def test_build_instruction_resumes_phone_after_wechat_collected_from_channel_switch(self):
        """渠道切换恢复电话时，应使用微信已收后的补充电话提示。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        profile.wechat = "abc123"
        profile.wechat_collected = True
        profile.pending_contact_field = "phone"
        profile.pending_contact_hint = "channel_switch"

        instruction, action = self.service.build_instruction(profile)
        assert action == NextAction.ASK_PHONE
        assert "补充电话" in instruction or "电话" in instruction

    def test_build_instruction_after_phone_attempt_keeps_phone_prompt(self):
        """构建指令 - 电话首次推进后，仍应继续电话追问而不是提前切微信"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1

        instruction, action = self.service.build_instruction(profile, "好的")

        assert action == NextAction.PERSUADE_PHONE
        assert "电话" in instruction

    def test_build_instruction_none_without_contact_complete_keeps_empty_instruction(self):
        """NONE 只有在联系方式流程真的完成后才视为已处理完毕。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True

        instruction, action = self.service.build_instruction(profile)
        assert action == NextAction.ASK_WECHAT
        assert instruction

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

    def test_detect_refusal_phone_only_preference_counts_as_wechat_refusal_after_phone_collected(self):
        """已收电话后说“电话联系就好了”，应视为拒绝微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        profile.last_contact_request_type = "wechat"

        result = self.service.detect_refusal("电话联系就好了", profile, "方便给下你的微信不")

        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_final is True
        assert profile.rejected_wechat is True

    def test_detect_refusal_repeated_phone_only_preference_counts_as_wechat_refusal(self):
        """已收电话后说“说了电话联系”，也应视为拒绝微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        profile.last_contact_request_type = "wechat"

        result = self.service.detect_refusal("说了电话联系", profile, "要是方便的话可以留个微信")

        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_final is True
        assert profile.rejected_wechat is True

    def test_detect_refusal_short_phone_contact_preference_counts_as_wechat_refusal(self):
        """已收电话且正在要微信时，短句“电话联系”也应视为拒绝微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        profile.last_contact_request_type = "wechat"

        result = self.service.detect_refusal("电话联系", profile, "你方便留个微信不")

        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_final is True
        assert profile.rejected_wechat is True

    def test_detect_refusal_dianlian_variant_counts_as_wechat_refusal(self):
        """已收电话后说“电联吧”，也应视为拒绝微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone = "13800138000"
        profile.phone_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        profile.last_contact_request_type = "wechat"

        result = self.service.detect_refusal("电联吧", profile, "后面联系更顺手些，你方便留个微信不")

        assert result is not None
        assert result.contact_type == 'wechat'
        assert result.is_final is True
        assert profile.rejected_wechat is True

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

    def test_detect_refusal_general_prefers_current_phone_action_over_last_response(self):
        """拒绝检测 - 当前动作问电话时，通用拒绝优先记电话"""
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat = "wx_123456"
        profile.wechat_collected = True
        result = self.service.detect_refusal(
            "不方便呢",
            profile,
            "微信这块你要是愿意就留一个，不想留我们先往下聊也行。",
        )
        assert result is not None
        assert result.contact_type == 'phone'

    def test_detect_refusal_general_prefers_last_delivered_request_type_over_shifted_action(self):
        """拒绝检测 - 优先按最近一次真实展示给用户的联系方式类型归因。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        profile.last_contact_request_type = "phone"

        result = self.service.detect_refusal(
            "不留",
            profile,
            "我知道你现在对微信这块还有顾虑。你要是愿意，留一个也行，不想留我们就先往下聊。",
        )

        assert result is not None
        assert result.contact_type == 'phone'

    def test_detect_refusal_general_prefers_current_wechat_action_over_last_response(self):
        """拒绝检测 - 当前动作问微信时，通用拒绝优先记微信"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        result = self.service.detect_refusal(
            "不方便呢",
            profile,
            "方便留个电话吗？",
        )
        assert result is not None
        assert result.contact_type == 'wechat'

    def test_detect_refusal_no_refusal(self):
        """拒绝检测 - 无拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        result = self.service.detect_refusal("好的，我叫张三", profile, None)
        assert result is None

    def test_detect_refusal_updates_ask_count(self):
        """拒绝检测 - 拒绝时不重复递增已展示的询问次数"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        result = self.service.detect_refusal("不留电话", profile, None)
        assert profile.phone_ask_count == 1
        assert result is not None
        assert result.is_refusal == True
        assert result.is_final == False

    def test_detect_refusal_marks_final_rejection(self):
        """拒绝检测 - 标记最终拒绝"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2  # 已达到上限
        result = self.service.detect_refusal("不留电话", profile, None)
        assert result.is_final == True
        assert profile.rejected_phone == True

    def test_first_phone_refusal_keeps_phone_flow_until_second_attempt(self):
        """首次拒绝电话后，仍应保持电话流程，直到第二次电话询问后才终拒"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1

        result = self.service.detect_refusal("不留电话", profile, None)

        assert result is not None
        assert result.contact_type == "phone"
        assert result.is_final is False
        assert profile.rejected_phone is False
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_PHONE

    def test_second_phone_refusal_switches_to_wechat(self):
        """第二次电话询问后再次拒绝，才进入微信流程"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2

        result = self.service.detect_refusal("不留电话", profile, None)

        assert result is not None
        assert result.contact_type == "phone"
        assert result.is_final is True
        assert profile.rejected_phone is True
        assert self.service.get_next_action(profile) == NextAction.ASK_WECHAT

    def test_detect_refusal_keeps_phone_effective_ask_when_switching_to_wechat(self):
        """切换到微信流程时，已经真实问过的电话次数仍应计入有效询问上限。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 1
        profile.phone_effective_ask_count = 1
        profile.last_contact_request_type = "phone"

        result = self.service.detect_refusal(
            "不留微信",
            profile,
            "方便留个电话吗？后面沟通会方便些",
        )

        assert result is not None
        assert result.contact_type == "wechat"
        assert profile.phone_ask_count == 1
        assert profile.phone_effective_ask_count == 1
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_WECHAT

    def test_clear_pending_request_state_only_clears_request_context(self):
        """清理 pending 状态不应回退已真实展示的询问计数。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.last_contact_request_type = "phone"

        self.service.clear_pending_request_state(profile, "phone")

        assert profile.phone_ask_count == 2
        assert profile.phone_effective_ask_count == 2
        assert profile.last_contact_request_type is None

    def test_rollback_pending_request_state_rolls_back_one_unfulfilled_phone_ask(self):
        """回滚 pending 状态时，应同步回退一轮未兑现的电话询问计数。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.last_contact_request_type = "phone"

        self.service.rollback_pending_request_state(profile, "phone")

        assert profile.phone_ask_count == 1
        assert profile.phone_effective_ask_count == 1
        assert profile.last_contact_request_type is None

    def test_is_contact_complete_false_after_wechat_collected_with_only_one_phone_effective_ask(self):
        """先收微信后第一次拒电话时，电话流程未完成，不应误判联系方式已完成。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat = "abc123"
        profile.wechat_collected = True
        profile.phone_ask_count = 1
        profile.phone_effective_ask_count = 1

        assert self.service.is_contact_complete(profile) is False
        assert self.service.get_next_action(profile) == NextAction.PERSUADE_PHONE

    def test_detect_refusal_treats_already_left_wechat_as_phone_refusal_in_phone_context(self):
        """用户在电话语境中说“已经留了微信了”时，应归因为拒绝电话而不是拒绝微信。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat = "abc123"
        profile.wechat_collected = True
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.last_contact_request_type = "phone"

        result = self.service.detect_refusal(
            "不方便了，已经留了微信了",
            profile,
            "微信我看到了。你要是方便的话，也可以补个常用手机号。",
        )

        assert result is not None
        assert result.contact_type == "phone"
        assert result.is_final is True
        assert profile.rejected_phone is True
        assert profile.rejected_wechat is False

    def test_detect_refusal_treats_asr_jiu_variant_as_phone_final_refusal_after_wechat_collected(self):
        profile = UserProfile(account_id="test", location="北京")
        profile.wechat = "abc123"
        profile.wechat_collected = True
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.last_contact_request_type = "phone"

        result = self.service.detect_refusal(
            "微信久可以了",
            profile,
            "你方便留个手机号吗？",
        )

        assert result is not None
        assert result.contact_type == "phone"
        assert result.is_final is True
        assert profile.rejected_phone is True

    def test_get_effective_contact_ask_count_prefers_effective_counter(self):
        """有效询问次数应优先读取 effective_ask_count，而不是原始 ask_count。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 1

        assert self.service.get_effective_contact_ask_count(profile, "phone") == 1

    def test_is_contact_type_final_refused_reads_rejection_state(self):
        """最终拒绝态应统一由 helper 判定。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True

        assert self.service.is_contact_type_final_refused(profile, "phone") is True
        assert self.service.is_contact_type_final_refused(profile, "wechat") is False

    def test_should_end_conversation_uses_final_refusal_helper(self):
        """结束对话应依赖统一 final refusal 判定，而不是散落地直接读字段。"""
        profile = UserProfile(account_id="test", location="北京")
        profile.rejected_phone = True
        profile.rejected_wechat = True

        assert self.service.should_end_conversation(profile) is True

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

    def test_replay_phone_to_wechat_then_final_refuse_phone_completes_contact_flow(self):
        """真实链路回归：电话 -> 微信 -> 用户坚持只留微信，应完成联系方式流程。"""
        profile = UserProfile(account_id="test", location="深圳")

        # 第一轮先问电话后，用户要求切微信
        profile.phone_ask_count = 1
        profile.phone_effective_ask_count = 1
        assert self.service.get_next_action(profile, "微信可以吗") == NextAction.ASK_WECHAT

        # 用户已留微信，系统后续进行第二次电话争取
        profile.wechat = "wuweifuwej"
        profile.wechat_collected = True
        profile.wechat_ask_count = 1
        profile.wechat_effective_ask_count = 1
        profile.phone_ask_count = 2
        profile.phone_effective_ask_count = 2
        profile.last_contact_request_type = "phone"

        result = self.service.detect_refusal(
            "微信就可以了",
            profile,
            "微信我看到了。你要是方便的话，也可以补个常用手机号。",
        )

        assert result is not None
        assert result.contact_type == "phone"
        assert result.is_final is True
        assert profile.rejected_phone is True
        assert self.service.get_next_action(profile) == NextAction.NONE
        assert self.service.is_contact_complete(profile) is True

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

    def test_record_invalid_input_closes_wechat_after_three_attempts(self):
        """连续三次微信无效输入后，应关闭主动微信追问。"""
        profile = UserProfile(account_id="test", location="北京")
        assert self.service.record_invalid_input(profile, 'wechat') == 1
        assert self.service.record_invalid_input(profile, 'wechat') == 2
        assert self.service.record_invalid_input(profile, 'wechat') == 3
        assert profile.wechat_invalid_input_closed is True
