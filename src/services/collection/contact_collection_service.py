"""
联系方式收集服务

负责联系方式收集的完整业务逻辑，包括：
1. 决策下一步动作
2. 构建对话指令
3. 检测用户拒绝
4. 管理收集状态

=========================================================================================
⚠️ 联系方式相关的所有内容都在这个文件里 ⚠️
=========================================================================================

【提示词模板】PROMPT_* 常量（第 75-272 行）
【决策逻辑】get_next_action() 方法
【拒绝检测】detect_refusal() 方法
【状态管理】record_* 方法

修改联系方式功能时，只需修改这个文件！
=========================================================================================

"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, List
import logging
import re

from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class NextAction(Enum):
    """下一步动作类型"""
    ASK_PHONE = "ask_phone"           # 询问电话
    ASK_WECHAT = "ask_wechat"         # 询问微信
    PERSUADE_PHONE = "persuade_phone" # 争取电话
    PERSUADE_WECHAT = "persuade_wechat"  # 争取微信
    END_CONVERSATION = "end"          # 结束对话
    NONE = "none"                     # 无需动作


@dataclass
class RefusalResult:
    """拒绝检测结果"""
    contact_type: str      # 'phone' | 'wechat'
    is_refusal: bool       # 是否为拒绝
    is_final: bool         # 是否为最终拒绝（达到上限）
    ask_count_after: int   # 更新后的询问次数


class ContactFlowState(Enum):
    """显式联系方式流程状态。"""
    NO_CONTACT = "no_contact"
    PHONE_REQUESTED = "phone_requested"
    PHONE_PERSUADING = "phone_persuading"
    PHONE_FINAL_REFUSED = "phone_final_refused"
    PHONE_COLLECTED = "phone_collected"
    WECHAT_REQUESTED = "wechat_requested"
    WECHAT_PERSUADING = "wechat_persuading"
    WECHAT_FINAL_REFUSED = "wechat_final_refused"
    WECHAT_COLLECTED = "wechat_collected"
    CONTACT_CLOSED = "contact_closed"
    CONTACT_COLLECTED = "contact_collected"


@dataclass
class ContactFlowSnapshot:
    """联系方式流程的显式快照，用于解释当前状态而不改变现有业务逻辑。"""
    state: ContactFlowState
    next_action: NextAction
    phone_collected: bool
    wechat_collected: bool
    rejected_phone: bool
    rejected_wechat: bool
    phone_ask_count: int
    wechat_ask_count: int
    contact_complete: bool
    should_end_conversation: bool
    is_hongkong_user: bool


class ContactCollectionService:
    """
    联系方式收集服务

    统一管理联系方式收集的业务逻辑
    """

    # ==================== 配置常量 ====================

    # 电话拒绝关键词
    PHONE_REFUSAL_KEYWORDS: List[str] = [
        '不留电话', '不用电话', '不要电话', '拒绝电话',
        '不给电话', '没电话', '没有电话'
    ]

    # 微信拒绝关键词
    WECHAT_REFUSAL_KEYWORDS: List[str] = [
        '不留微信', '不用微信', '不要微信', '拒绝微信',
        '不给微信', '没微信', '没有微信'
    ]

    # 通用拒绝关键词
    GENERAL_REFUSAL_KEYWORDS: List[str] = [
        '不用了', '不需要', '不想留', '不愿意', '不方便',
        '还是算了', '算了吧', '不用留', '不要了', '不留', '不给'
    ]

    # 询问次数上限
    MAX_PHONE_ASKS = 2
    MAX_WECHAT_ASKS_HK = 2                      # 香港用户
    MAX_WECHAT_ASKS_NON_HK_WITH_PHONE = 1       # 非香港用户 + 电话已收集
    MAX_WECHAT_ASKS_NON_HK_WITHOUT_PHONE = 2    # 非香港用户 + 电话未收集
    MAX_INVALID_INPUT_RETRIES = 3               # 第 3 次无效输入后关闭主动追问

    # 微信意图关键词（用户想用微信联系）
    WECHAT_INTENT_KEYWORDS: List[str] = [
        "留微信可以吗", "微信可以", "微信方便", "留微信行吗", "给微信可以吗",
        "我先给微信", "先给微信吧", "留微信吧",
        "用微信联系", "加微信", "微信联系", "用微信", "留个微信",
        "微信可以不", "微信行不", "微信可不可以",
    ]

    # 电话拒绝偏好关键词（用户说电话不方便想用微信）
    PHONE_REFUSAL_PREFERENCE_KEYWORDS: List[str] = [
        "电话不方便", "电话不行", "电话不方便留", "不方便留电话", "电话不好留"
    ]

    # 通用联系方式偏好（用户明确说用某种方式）
    CONTACT_PREFERENCE_KEYWORDS: List[str] = [
        "用微信联系吧", "微信吧", "用微信吧", "加微信吧", "微信也行",
    ]

    PHONE_ONLY_CONTACT_PATTERNS: List[str] = [
        r"电话联系$",
        r"电话联系就好",
        r"电话联系就好了",
        r"说了电话联系",
        r"打电话就行",
        r"电话就行",
        r"电话沟通吧",
        r"有事电话说",
        r"电话说就好",
        r"就电话吧",
        r"直接电话",
        r"电联吧",
        r"电联就行",
    ]

    SOFT_ACK_MESSAGES: List[str] = [
        "嗯", "嗯嗯", "恩", "好", "好的", "好呀", "好的呢", "行", "可以", "ok", "好的哈"
    ]
    # ==================== 提示词模板 ====================

    PROMPT_END_CONVERSATION = """
【当前任务：结束对话】
用户已拒绝提供电话和微信。
本轮只做自然收尾，不追问资料，不再索要联系方式。
"""

    PROMPT_ASK_PHONE_FIRST = """
【当前任务：询问电话】
首次询问电话号码。
自然、简短地说明用途并询问电话。
不要提微信，不要写模板腔开场。
"""

    PROMPT_PERSUADE_PHONE = """
【当前任务：争取电话号码】
用户第一次拒绝电话。
先承接顾虑，再轻轻给一次电话选项。
最多两句，避免长解释。
禁止重复强调“不会骚扰 / 不会打扰 / 不会发广告 / 绝对不会”。
禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料”这类承诺。
不要营销感，不要连续说服。
这轮只能继续围绕电话，禁止改问微信，禁止把电话拒绝直接转成要微信。
"""

    PROMPT_ASK_PHONE_AFTER_WECHAT_REJECTED = """
【当前任务：微信拒绝后询问电话】
用户拒绝微信，当前改问电话。
自然承接后简短询问电话，不要结束对话。
"""

    PROMPT_ASK_PHONE_AFTER_WECHAT_COLLECTED = """
【当前任务：微信已收集后补充电话】
用户微信已记录，可继续顺带确认电话。
表达要自然简短，不要套话。
"""

    PROMPT_ASK_WECHAT_FIRST = """
【当前任务：询问微信】
首次询问微信号。
自然简短说明用途并询问微信，不要提电话。
禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料”这类承诺。
"""

    PROMPT_ASK_WECHAT_AFTER_PHONE_REJECTED = """
【当前任务：电话拒绝后询问微信】
用户已经达到电话流程切换条件，当前改问微信。
自然承接后简短询问微信，不要结束语气。
禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料”这类承诺。
"""

    PROMPT_ASK_WECHAT_ON_USER_PREFERENCE = """
【当前任务：接住用户的微信偏好】
用户明确说微信更方便。
直接顺着用户提议，请其提供微信号。
不要转成长解释或继续坚持其他联系方式。
禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料”这类承诺。
"""

    PROMPT_PERSUADE_WECHAT = """
【当前任务：微信拒绝后继续沟通】
用户第一次拒绝微信。
先承接顾虑，再轻轻给一次微信选项。
最多两句，避免长解释。
禁止重复强调“不会骚扰 / 不会打扰 / 不会发广告 / 绝对不会”。
禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料”这类承诺。
不要模板化，不要连续说服。
这轮只能继续围绕微信，禁止改回电话。
"""

    PROMPT_HK_ASK_WECHAT = """
【当前任务：香港用户询问微信】
已收集电话，当前询问微信。
自然、简短询问，不要模板化开场。
"""

    PROMPT_HK_PERSUADE_WECHAT = """
【当前任务：香港用户微信拒绝后继续沟通】
用户第一次拒绝微信。
承接顾虑后轻轻再问一次即可。
最多两句，避免长解释。
禁止重复强调“不会骚扰 / 不会打扰 / 不会发广告 / 绝对不会”。
不要结束语气，也不要长篇说服。
"""

    def __init__(self, user_service=None):
        """
        初始化联系方式收集服务

        Args:
            user_service: 用户服务（用于持久化）
        """
        self.user_service = user_service

    # ==================== 核心决策方法 ====================

    def get_next_action(self, profile: UserProfile, user_message: str = "") -> NextAction:
        """
        获取下一步动作

        Args:
            profile: 用户档案
            user_message: 当前用户消息（用于偏好检测）

        Returns:
            NextAction: 下一步动作
        """
        if self.should_end_conversation(profile):
            return NextAction.END_CONVERSATION
        if self.is_contact_complete(profile):
            return NextAction.NONE

        # === 优先级0: 用户主动提出联系方式偏好 ===
        if self.prefers_wechat_over_phone(user_message, profile):
            profile.pending_contact_field = "phone"
            profile.pending_contact_hint = "channel_switch"
            logger.info("[联系方式偏好] 用户拒绝电话但愿意留微信，切换到微信流程")
            return NextAction.ASK_WECHAT

        is_hk = self.is_hongkong_user(profile)

        # 场景1.5: 电话流程中用户切到微信，微信已收后优先恢复电话
        if (
            not is_hk
            and profile.wechat_collected
            and not profile.phone_collected
            and not profile.rejected_phone
            and str(getattr(profile, "pending_contact_field", "") or "").strip() == "phone"
            and str(getattr(profile, "pending_contact_hint", "") or "").strip() == "channel_switch"
        ):
            return NextAction.ASK_PHONE

        # 场景2: 微信被最终拒绝，尝试争取电话
        if profile.rejected_wechat and not profile.rejected_phone and not profile.phone_collected:
            if profile.phone_ask_count == 0:
                return NextAction.ASK_PHONE
            elif profile.phone_ask_count < 2:
                return NextAction.PERSUADE_PHONE

        # 场景3: 电话被最终拒绝，尝试争取微信
        if profile.rejected_phone and not profile.rejected_wechat and not profile.wechat_collected:
            max_wechat = self.get_max_asks(profile, 'wechat')
            if profile.wechat_ask_count == 0:
                return NextAction.ASK_WECHAT
            elif profile.wechat_ask_count < max_wechat:
                return NextAction.PERSUADE_WECHAT

        # 场景4: 微信正在争取中（还没被最终拒绝），继续争取微信
        if not profile.rejected_wechat and not profile.wechat_collected and profile.wechat_ask_count >= 1:
            max_wechat = self.get_max_asks(profile, 'wechat')
            if profile.wechat_ask_count < max_wechat:
                return NextAction.PERSUADE_WECHAT

        # 场景5: 电话正在争取中（还没被最终拒绝），继续争取电话
        if not profile.rejected_phone and not profile.phone_collected and profile.phone_ask_count >= 1:
            if profile.phone_ask_count < 2:
                return NextAction.PERSUADE_PHONE

        # 场景6: 香港用户流程
        if is_hk:
            # 还没收集电话
            if not profile.phone_collected and not profile.rejected_phone:
                if profile.phone_ask_count == 0:
                    return NextAction.ASK_PHONE
                elif profile.phone_ask_count < 2:
                    return NextAction.PERSUADE_PHONE

            # 电话已收集，还需要微信
            if profile.phone_collected and not profile.wechat_collected and not profile.rejected_wechat:
                if profile.wechat_ask_count == 0:
                    return NextAction.ASK_WECHAT
                elif profile.wechat_ask_count < 2:
                    return NextAction.PERSUADE_WECHAT

        # 场景7: 非香港用户流程
        else:
            # === 优先级1: 电话已收集后，询问/争取微信 ===
            if profile.phone_collected and not profile.wechat_collected and not profile.rejected_wechat:
                max_wechat = self.get_max_asks(profile, 'wechat')
                if profile.wechat_ask_count == 0:
                    return NextAction.ASK_WECHAT
                elif profile.wechat_ask_count < max_wechat:
                    return NextAction.PERSUADE_WECHAT

            # === 优先级1.5: 微信已收集后，询问/争取电话 ===
            if profile.wechat_collected and not profile.phone_collected and not profile.rejected_phone:
                if (
                    str(getattr(profile, "pending_contact_field", "") or "").strip() == "phone"
                    and str(getattr(profile, "pending_contact_hint", "") or "").strip() == "channel_switch"
                ):
                    return NextAction.ASK_PHONE
                if profile.phone_ask_count == 0:
                    return NextAction.ASK_PHONE
                elif profile.phone_ask_count < 2:
                    return NextAction.PERSUADE_PHONE

            # === 优先级2: 还没收集电话 ===
            if not profile.phone_collected and not profile.rejected_phone:
                if profile.phone_ask_count == 0:
                    return NextAction.ASK_PHONE
                elif profile.phone_ask_count < 2:
                    return NextAction.PERSUADE_PHONE

        return NextAction.NONE

    def get_flow_state(self, profile: UserProfile, user_message: str = "") -> ContactFlowState:
        """
        返回显式联系方式流程状态。

        说明：
        - 该状态是对现有 `UserProfile` 字段和 `get_next_action()` 结果的派生视图
        - 不引入第二套业务真源
        - 不改变现有动作决策
        """
        next_action = self.get_next_action(profile, user_message)
        phone_collected = bool(profile.phone_collected and profile.phone)
        wechat_collected = bool(profile.wechat_collected and profile.wechat)

        if self.should_end_conversation(profile):
            return ContactFlowState.CONTACT_CLOSED
        if self.is_contact_complete(profile):
            return ContactFlowState.CONTACT_COLLECTED if (phone_collected or wechat_collected) else ContactFlowState.CONTACT_CLOSED
        if phone_collected and wechat_collected:
            return ContactFlowState.CONTACT_COLLECTED
        if next_action == NextAction.ASK_PHONE:
            return ContactFlowState.PHONE_REQUESTED
        if next_action == NextAction.PERSUADE_PHONE:
            return ContactFlowState.PHONE_PERSUADING
        if next_action == NextAction.ASK_WECHAT:
            return ContactFlowState.WECHAT_REQUESTED
        if next_action == NextAction.PERSUADE_WECHAT:
            return ContactFlowState.WECHAT_PERSUADING
        if phone_collected:
            return ContactFlowState.PHONE_COLLECTED
        if wechat_collected:
            return ContactFlowState.WECHAT_COLLECTED
        if profile.rejected_phone and not profile.rejected_wechat:
            return ContactFlowState.PHONE_FINAL_REFUSED
        if profile.rejected_wechat and not profile.rejected_phone:
            return ContactFlowState.WECHAT_FINAL_REFUSED
        return ContactFlowState.NO_CONTACT

    def get_flow_snapshot(self, profile: UserProfile, user_message: str = "") -> ContactFlowSnapshot:
        """返回联系方式流程显式快照。"""
        next_action = self.get_next_action(profile, user_message)
        return ContactFlowSnapshot(
            state=self.get_flow_state(profile, user_message),
            next_action=next_action,
            phone_collected=bool(profile.phone_collected and profile.phone),
            wechat_collected=bool(profile.wechat_collected and profile.wechat),
            rejected_phone=bool(profile.rejected_phone),
            rejected_wechat=bool(profile.rejected_wechat),
            phone_ask_count=int(profile.phone_ask_count),
            wechat_ask_count=int(profile.wechat_ask_count),
            contact_complete=self.is_contact_complete(profile),
            should_end_conversation=self.should_end_conversation(profile),
            is_hongkong_user=self.is_hongkong_user(profile),
        )

    # 联系方式已收集，继续收集其他字段的指令
    PROMPT_CONTINUE_OTHER_FIELDS = """

【联系方式流程已完成】
电话/微信流程已结束，现在继续收集其他用户信息。
不要再询问联系方式，专注于继续完善重要资料（如性别、年龄、工作地、学历、职业、婚况等）。
不要主动追问身高、体重、称呼这类低优先级字段。
"""

    def build_instruction(self, profile: UserProfile, user_message: str = "") -> Tuple[str, NextAction]:
        """
        构建联系方式指令

        Args:
            profile: 用户档案
            user_message: 当前用户消息（用于偏好检测）

        Returns:
            Tuple[str, NextAction]: (指令字符串, 下一步动作)
        """
        action = self.get_next_action(profile, user_message)
        prefers_wechat = self.prefers_wechat_over_phone(user_message, profile)

        instruction = ""
        is_hk = self.is_hongkong_user(profile)

        if action == NextAction.END_CONVERSATION:
            instruction = self.PROMPT_END_CONVERSATION
            logger.info("[联系方式指令] 双方都被拒绝，进入显式收尾提示")

        elif action == NextAction.ASK_PHONE:
            # 判断是否是微信被拒后询问电话
            if profile.rejected_wechat:
                instruction = self.PROMPT_ASK_PHONE_AFTER_WECHAT_REJECTED
            # 判断是否是微信已收集后询问电话
            elif profile.wechat_collected:
                instruction = self.PROMPT_ASK_PHONE_AFTER_WECHAT_COLLECTED
            else:
                instruction = self.PROMPT_ASK_PHONE_FIRST

        elif action == NextAction.PERSUADE_PHONE:
            instruction = self.PROMPT_PERSUADE_PHONE

        elif action == NextAction.ASK_WECHAT:
            # 判断是否是电话被拒后询问微信
            if prefers_wechat:
                instruction = self.PROMPT_ASK_WECHAT_ON_USER_PREFERENCE
            elif profile.rejected_phone:
                instruction = self.PROMPT_ASK_WECHAT_AFTER_PHONE_REJECTED
            elif is_hk:
                instruction = self.PROMPT_HK_ASK_WECHAT
            else:
                instruction = self.PROMPT_ASK_WECHAT_FIRST

        elif action == NextAction.PERSUADE_WECHAT:
            if is_hk:
                instruction = self.PROMPT_HK_PERSUADE_WECHAT
            else:
                instruction = self.PROMPT_PERSUADE_WECHAT

        elif action == NextAction.NONE:
            # 只有联系方式流程真的完成后，才继续收集其他字段。
            has_contact = profile.phone_collected or profile.wechat_collected
            if has_contact and self.is_contact_complete(profile):
                instruction = self.PROMPT_CONTINUE_OTHER_FIELDS
                logger.info(f"[联系方式指令] 联系方式流程已完成，继续收集其他字段")

        return (instruction, action)

    def prefers_wechat_over_phone(self, user_message: str, profile: UserProfile) -> bool:
        """
        判断用户是否明确表示电话不方便，但愿意留微信。

        这是联系方式流程内的当轮偏好覆盖，不改变整体状态机顺序，
        只用于本轮把默认电话流程切到微信流程。
        """
        if not user_message or profile.wechat_collected:
            return False

        wants_wechat = any(keyword in user_message for keyword in self.WECHAT_INTENT_KEYWORDS)
        if not wants_wechat:
            return False

        explicit_contact_preference = any(keyword in user_message for keyword in self.CONTACT_PREFERENCE_KEYWORDS)
        refuses_phone = self._message_indicates_phone_refusal_preference(user_message)
        in_phone_flow = (
            profile.phone_ask_count >= 1
            and not profile.phone_collected
            and not profile.rejected_phone
            and not profile.wechat_collected
        )
        return refuses_phone or explicit_contact_preference or in_phone_flow

    def _is_soft_ack_without_contact(self, user_message: str) -> bool:
        message = (user_message or "").strip().lower()
        if not message:
            return False
        if re.search(r"\d", message):
            return False
        return message in self.SOFT_ACK_MESSAGES

    def _should_switch_from_phone_to_wechat(
        self,
        profile: UserProfile,
        user_message: str,
        is_hk: bool,
    ) -> bool:
        if is_hk or not self._is_soft_ack_without_contact(user_message):
            return False
        return (
            profile.phone_ask_count >= 1
            and profile.wechat_ask_count == 0
            and not profile.phone_collected
            and not profile.rejected_phone
            and not profile.wechat_collected
            and not profile.rejected_wechat
        )

    def _should_switch_from_wechat_to_phone(
        self,
        profile: UserProfile,
        user_message: str,
        is_hk: bool,
    ) -> bool:
        if is_hk or not self._is_soft_ack_without_contact(user_message):
            return False
        return (
            profile.wechat_ask_count >= 1
            and profile.phone_ask_count == 0
            and not profile.wechat_collected
            and not profile.rejected_wechat
            and not profile.phone_collected
            and not profile.rejected_phone
        )

    def _should_pause_after_repeated_contact_soft_ack(
        self,
        profile: UserProfile,
        user_message: str,
        is_hk: bool,
    ) -> bool:
        if is_hk or not self._is_soft_ack_without_contact(user_message):
            return False
        if profile.phone_collected or profile.wechat_collected:
            return False
        return profile.phone_ask_count >= 1 and profile.wechat_ask_count >= 1

    def _message_indicates_phone_refusal_preference(self, user_message: str) -> bool:
        """判断用户是否表达了“电话不方便，优先微信”的拒绝偏好。"""
        if not user_message:
            return False
        return any(keyword in user_message for keyword in self.PHONE_REFUSAL_PREFERENCE_KEYWORDS)

    def should_end_conversation(self, profile: UserProfile) -> bool:
        """
        判断是否应该结束对话

        Args:
            profile: 用户档案

        Returns:
            bool: 是否结束对话
        """
        # 只有在“电话和微信都最终拒绝，且当前没有任何可用联系方式”时才结束。
        # 这样可以避免“已留电话 + 拒绝微信”被误判为结束。
        has_any_contact = bool(
            (profile.phone_collected and profile.phone)
            or (profile.wechat_collected and profile.wechat)
        )
        return profile.rejected_phone and profile.rejected_wechat and not has_any_contact

    def is_contact_type_complete(self, profile: UserProfile, contact_type: str) -> bool:
        """单项联系方式流程是否完成。"""
        max_asks = self.get_max_asks(profile, contact_type)
        if contact_type == 'phone':
            effective_count = int(getattr(profile, "phone_effective_ask_count", profile.phone_ask_count) or 0)
            invalid_closed = bool(getattr(profile, "phone_invalid_input_closed", False))
            return bool(profile.phone_collected) or bool(profile.rejected_phone) or effective_count >= max_asks or invalid_closed

        effective_count = int(getattr(profile, "wechat_effective_ask_count", profile.wechat_ask_count) or 0)
        invalid_closed = bool(getattr(profile, "wechat_invalid_input_closed", False))
        return bool(profile.wechat_collected) or bool(profile.rejected_wechat) or effective_count >= max_asks or invalid_closed

    def is_contact_complete(self, profile: UserProfile) -> bool:
        """联系方式流程是否完成：电话流程和微信流程都已完成。"""
        complete = self.is_contact_type_complete(profile, 'phone') and self.is_contact_type_complete(profile, 'wechat')
        profile.contact_complete = complete
        return complete

    def clear_pending_request_state(self, profile: UserProfile, contact_type: str) -> None:
        """
        清理未兑现的联系方式询问状态。

        适用于：
        - 系统刚问过 A，但用户明确切去 B，此时 A 的询问不应占用一次有效 ask
        - 用户主动提供某联系方式，导致上一轮预问的另一联系方式应视为未兑现
        """
        if contact_type == 'phone':
            if str(getattr(profile, "last_contact_request_type", "") or "").strip() == "phone":
                profile.last_contact_request_type = None
            return

        if str(getattr(profile, "last_contact_request_type", "") or "").strip() == "wechat":
            profile.last_contact_request_type = None

    def clear_contact_context_state(self, profile: UserProfile) -> None:
        """联系方式主流程结束后，清理残留的联系方式上下文。"""
        profile.last_contact_request_type = None
        profile.pending_contact_candidate = None
        profile.pending_contact_field = None
        profile.pending_contact_hint = None

    def record_invalid_input(self, profile: UserProfile, contact_type: str) -> int:
        """记录联系方式无效输入；达到上限后关闭主动追问。"""
        if contact_type == 'phone':
            profile.phone_invalid_input_retry_count += 1
            if profile.phone_invalid_input_retry_count >= self.MAX_INVALID_INPUT_RETRIES:
                profile.phone_invalid_input_closed = True
            return profile.phone_invalid_input_retry_count

        profile.wechat_invalid_input_retry_count += 1
        if profile.wechat_invalid_input_retry_count >= self.MAX_INVALID_INPUT_RETRIES:
            profile.wechat_invalid_input_closed = True
        return profile.wechat_invalid_input_retry_count

    def reset_invalid_input(self, profile: UserProfile, contact_type: str) -> None:
        """成功收集后清空无效输入重试状态。"""
        if contact_type == 'phone':
            profile.phone_invalid_input_retry_count = 0
            profile.phone_invalid_input_closed = False
            if str(getattr(profile, "pending_contact_field", "") or "").strip() == "phone":
                profile.pending_contact_field = None
                if str(getattr(profile, "pending_contact_hint", "") or "").strip() == "channel_switch":
                    profile.pending_contact_hint = None
            return
        profile.wechat_invalid_input_retry_count = 0
        profile.wechat_invalid_input_closed = False
        if str(getattr(profile, "pending_contact_field", "") or "").strip() == "wechat":
            profile.pending_contact_field = None
            if str(getattr(profile, "pending_contact_hint", "") or "").strip() == "channel_switch":
                profile.pending_contact_hint = None

    # ==================== 拒绝检测方法 ====================

    def detect_refusal(
        self,
        message: str,
        profile: UserProfile,
        last_response: Optional[str] = None
    ) -> Optional[RefusalResult]:
        """
        检测用户拒绝

        Args:
            message: 用户消息
            profile: 用户档案
            last_response: 上一轮AI回复（用于上下文检测）

        Returns:
            Optional[RefusalResult]: 拒绝结果，无拒绝返回 None
        """
        # === 入口日志（INFO级别，便于调试）===
        logger.debug(f"[拒绝检测-入口] 消息完整内容='{message}', phone_ask_count={profile.phone_ask_count}, wechat_ask_count={profile.wechat_ask_count}")

        message_lower = message.lower()

        # 检测显式拒绝
        phone_refusal = self._is_explicit_refusal(message_lower, 'phone')
        wechat_refusal = self._is_explicit_refusal(message_lower, 'wechat')
        general_refusal = self._has_general_refusal(message_lower)
        if self._is_phone_only_contact_preference(message_lower, profile):
            wechat_refusal = True

        # 详细匹配日志
        logger.debug(f"[拒绝检测-分析] 电话拒绝={phone_refusal}, 微信拒绝={wechat_refusal}, 通用拒绝={general_refusal}, last_response={'有' if last_response else '无'}")

        # 如果没有检测到任何拒绝，输出详细信息
        if not phone_refusal and not wechat_refusal and not general_refusal:
            matched_phone = [kw for kw in self.PHONE_REFUSAL_KEYWORDS if kw in message_lower]
            matched_general = [kw for kw in self.GENERAL_REFUSAL_KEYWORDS if kw in message_lower]
            logger.debug(f"[拒绝检测-详细] 匹配的电话关键词={matched_phone}, 匹配的通用关键词={matched_general}")

        result = None

        phone_collected = profile.phone_collected and profile.phone
        wechat_collected = profile.wechat_collected and profile.wechat
        logger.debug(f"[拒绝检测-调试] last_response 内容: '{last_response}'")
        is_about_phone = self._is_context_about(last_response, 'phone')
        is_about_wechat = self._is_context_about(last_response, 'wechat')
        logger.debug(f"[拒绝检测-上下文] 电话已收集={phone_collected}, 微信已收集={wechat_collected}, 关于电话={is_about_phone}, 关于微信={is_about_wechat}")

        user_mentions_wechat = any(marker in message_lower for marker in ['微信', 'wx', 'weixin'])
        user_mentions_phone = any(marker in message_lower for marker in ['电话', '手机', '手机号', '号码'])
        last_requested_type = str(getattr(profile, "last_contact_request_type", "") or "").strip()
        current_action = self.get_next_action(profile, "")
        action_value = getattr(current_action, "value", str(current_action))
        current_phone_context = last_requested_type == "phone" or is_about_phone or action_value in {NextAction.ASK_PHONE.value, NextAction.PERSUADE_PHONE.value}
        current_wechat_context = last_requested_type == "wechat" or is_about_wechat or action_value in {NextAction.ASK_WECHAT.value, NextAction.PERSUADE_WECHAT.value}
        has_active_contact_request_context = bool(
            last_requested_type in {"phone", "wechat"}
            or is_about_phone
            or is_about_wechat
            or int(getattr(profile, "phone_ask_count", 0) or 0) > 0
            or int(getattr(profile, "wechat_ask_count", 0) or 0) > 0
        )

        # 用户在电话语境里说“已经留了微信了/有微信了”，本质是在拒绝继续留电话，
        # 不是在拒绝已提供的微信。
        if (
            general_refusal
            and user_mentions_wechat
            and wechat_collected
            and not phone_collected
            and current_phone_context
            and any(marker in message_lower for marker in ("已经留了微信", "已经有微信", "都留微信", "留了微信", "有微信了"))
        ):
            wechat_refusal = False
            phone_refusal = True

        # 用户在电话语境里说“微信就可以/微信就行/留微信就好”，
        # 本质也是拒绝继续留电话，而不是拒绝微信。
        if (
            user_mentions_wechat
            and wechat_collected
            and not phone_collected
            and current_phone_context
            and (
                general_refusal
                or any(
                    marker in message_lower
                    for marker in (
                        "微信就可以",
                        "微信就行",
                        "微信就好",
                        "微信可以",
                        "留微信就好",
                        "留微信就行",
                        "微信联系就行",
                        "微信联系就好",
                        "微信就可以了",
                        "微信就行了",
                    )
                )
            )
        ):
            wechat_refusal = False
            phone_refusal = True

        if phone_refusal:
            logger.info("[拒绝检测] 检测到显式电话拒绝")
            if (
                not user_mentions_wechat
                and not wechat_collected
                and not profile.rejected_wechat
                and (last_requested_type == 'wechat' or is_about_wechat)
            ):
                logger.debug("[拒绝检测] 用户主动切回电话分支，清理未兑现的微信询问计数")
                self.clear_pending_request_state(profile, 'wechat')
            result = self._handle_refusal(profile, 'phone', True)
        elif wechat_refusal:
            logger.info("[拒绝检测] 检测到显式微信拒绝")
            if (
                not user_mentions_phone
                and not phone_collected
                and not profile.rejected_phone
                and (last_requested_type == 'phone' or is_about_phone)
            ):
                logger.debug("[拒绝检测] 用户主动切回微信分支，清理未兑现的电话询问计数")
                self.clear_pending_request_state(profile, 'phone')
            result = self._handle_refusal(profile, 'wechat', True)
        elif general_refusal:
            if user_mentions_wechat:
                logger.debug("[拒绝检测] 通用拒绝 + 明确提及微信，按微信拒绝处理")
                result = self._handle_refusal(profile, 'wechat', False)
            elif user_mentions_phone:
                logger.debug("[拒绝检测] 通用拒绝 + 明确提及电话，按电话拒绝处理")
                result = self._handle_refusal(profile, 'phone', False)
            elif current_phone_context:
                logger.debug("[拒绝检测] 使用最近一次真实展示的电话请求类型优先归因")
                result = self._handle_refusal(profile, 'phone', False)
            elif current_wechat_context:
                logger.debug("[拒绝检测] 使用最近一次真实展示的微信请求类型优先归因")
                result = self._handle_refusal(profile, 'wechat', False)
            elif has_active_contact_request_context and action_value in {NextAction.ASK_PHONE.value, NextAction.PERSUADE_PHONE.value}:
                logger.debug("[拒绝检测] 当前动作是电话流程，按电话拒绝处理")
                result = self._handle_refusal(profile, 'phone', False)
            elif has_active_contact_request_context and action_value in {NextAction.ASK_WECHAT.value, NextAction.PERSUADE_WECHAT.value}:
                logger.debug("[拒绝检测] 当前动作是微信流程，按微信拒绝处理")
                result = self._handle_refusal(profile, 'wechat', False)
            elif has_active_contact_request_context and is_about_wechat:
                logger.debug("[拒绝检测] 当前动作未知，按上一轮微信上下文兜底")
                result = self._handle_refusal(profile, 'wechat', False)
            elif has_active_contact_request_context and is_about_phone:
                logger.debug("[拒绝检测] 当前动作未知，按上一轮电话上下文兜底")
                result = self._handle_refusal(profile, 'phone', False)
            else:
                logger.debug("[拒绝检测] 通用拒绝但无法确定联系方式类型")

        if result:
            logger.info(f"[拒绝检测] 检测到拒绝: {result.contact_type}, 最终={result.is_final}, 次数={result.ask_count_after}")
        else:
            logger.debug(f"[拒绝检测] 未检测到联系方式拒绝，general_refusal={general_refusal}")

        return result

    def _is_explicit_refusal(self, message_lower: str, contact_type: str) -> bool:
        """判断是否显式拒绝"""
        keywords = (
            self.PHONE_REFUSAL_KEYWORDS
            if contact_type == 'phone'
            else self.WECHAT_REFUSAL_KEYWORDS
        )
        if any(kw in message_lower for kw in keywords):
            return True

        contact_markers = ['电话', '手机', '手机号', '号码'] if contact_type == 'phone' else ['微信', 'wx', 'weixin']
        return any(marker in message_lower for marker in contact_markers) and self._has_general_refusal(message_lower)

    def _has_general_refusal(self, message_lower: str) -> bool:
        """判断是否包含通用拒绝词"""
        if any(kw in message_lower for kw in self.GENERAL_REFUSAL_KEYWORDS):
            return True
        # 口语与轻微噪声鲁棒匹配：不太方便 / 不方便啊 / 先不留 / 暂时不留 等
        soft_patterns = [
            r'不.{0,2}方便',
            r'先不留',
            r'暂时不留',
            r'不想留',
            r'不太想留',
            r'不.{0,2}给',
        ]
        return any(re.search(pattern, message_lower) for pattern in soft_patterns)

    def _is_phone_only_contact_preference(self, message_lower: str, profile: UserProfile) -> bool:
        """电话已收后，识别用户明确表示只接受电话联系。"""
        if not message_lower:
            return False
        if not bool(profile.phone_collected and profile.phone):
            return False
        in_wechat_context = bool(
            str(getattr(profile, "last_contact_request_type", "") or "").strip() == "wechat"
            or int(getattr(profile, "wechat_ask_count", 0) or 0) > 0
            or int(getattr(profile, "wechat_effective_ask_count", 0) or 0) > 0
        )
        if not in_wechat_context:
            return False
        if "微信" in message_lower and self._has_general_refusal(message_lower):
            return True
        if any(re.search(pattern, message_lower) for pattern in self.PHONE_ONLY_CONTACT_PATTERNS):
            return True

        phone_priority_patterns = [
            r"(电话|手机|手机号|号码).{0,4}(联系|沟通|说|聊|打)",
            r"(联系|沟通|说|聊|打).{0,4}(电话|手机|手机号|号码)",
            r"电联",
        ]
        return any(re.search(pattern, message_lower) for pattern in phone_priority_patterns)

    def _is_context_about(self, last_response: Optional[str], contact_type: str) -> bool:
        """
        判断上一轮回复是否关于特定联系方式

        使用更精确的匹配逻辑，避免"联系方式"等词干扰
        """
        if not last_response:
            return False

        response_lower = last_response.lower()

        if contact_type == 'phone':
            # 检查是否明确询问电话
            # 排除"联系方式"这个干扰词
            # 检查模式：
            # - 询问模式："电话号码"、"留电话"、"个电话"、"电话吗"
            # - 争取模式："电话只是"、"电话用于"、"请你放心"、"保护你的隐私"
            phone_patterns = [
                '电话号码', '留电话', '个电话', '电话吗', '电话~', '电话哈',
                '电话只是', '电话用于', '请你放心', '保护你的隐私', '不会私下',
                '手机号', '手机号码', '号码', '手机号不', '手机号吗', '号码不', '号码吗'
            ]
            return any(p in response_lower for p in phone_patterns)
        else:
            # 检查是否明确询问微信
            wechat_patterns = [
                '微信号', '留微信', '个微信', '微信吗', '微信~', '微信哈', '留个微信',
                '微信方便的话', '你微信方便的话', '微信方便', '后面沟通', '后面联系', '留一个',
            ]
            if any(p in response_lower for p in wechat_patterns):
                return True

            return '微信' in response_lower and any(
                marker in response_lower for marker in ['方便', '留一个', '留个', '联系', '沟通']
            )

    def _handle_refusal(
        self,
        profile: UserProfile,
        contact_type: str,
        is_explicit: bool
    ) -> RefusalResult:
        """
        处理拒绝

        询问次数在“真实展示给用户”时由 record_ask 记录。
        这里不重复递增，避免一次询问 + 一次拒绝被双重计数。
        但如果用户在系统尚未明确询问前就主动显式拒绝某种联系方式，
        该拒绝视为该联系方式流程的第一次拒绝。
        """
        if contact_type == 'phone':
            new_count = profile.phone_ask_count
            if is_explicit and new_count == 0:
                new_count = 1
                profile.phone_ask_count = 1
                profile.phone_effective_ask_count = max(1, int(getattr(profile, "phone_effective_ask_count", 0) or 0))
            max_asks = self.get_max_asks(profile, 'phone')
            effective_count = int(getattr(profile, "phone_effective_ask_count", new_count) or new_count or 0)

            # 判断是否达到上限
            if effective_count >= max_asks:
                profile.rejected_phone = True
                return RefusalResult(
                    contact_type='phone',
                    is_refusal=True,
                    is_final=True,
                    ask_count_after=new_count
                )
            else:
                return RefusalResult(
                    contact_type='phone',
                    is_refusal=True,
                    is_final=False,
                    ask_count_after=new_count
                )
        else:  # wechat
            new_count = profile.wechat_ask_count
            if is_explicit and new_count == 0:
                new_count = 1
                profile.wechat_ask_count = 1
                profile.wechat_effective_ask_count = max(1, int(getattr(profile, "wechat_effective_ask_count", 0) or 0))
            max_asks = self.get_max_asks(profile, 'wechat')
            effective_count = int(getattr(profile, "wechat_effective_ask_count", new_count) or new_count or 0)

            # 判断是否达到上限
            if effective_count >= max_asks:
                profile.rejected_wechat = True
                return RefusalResult(
                    contact_type='wechat',
                    is_refusal=True,
                    is_final=True,
                    ask_count_after=new_count
                )
            else:
                return RefusalResult(
                    contact_type='wechat',
                    is_refusal=True,
                    is_final=False,
                    ask_count_after=new_count
                )

    # ==================== 状态管理方法 ====================

    def record_ask(self, profile: UserProfile, contact_type: str) -> int:
        """
        记录询问

        Args:
            profile: 用户档案
            contact_type: 'phone' | 'wechat'

        Returns:
            int: 更新后的询问次数
        """
        if contact_type == 'phone':
            profile.phone_ask_count += 1
            profile.phone_effective_ask_count += 1
            profile.last_contact_request_type = 'phone'
            return profile.phone_ask_count
        else:
            profile.wechat_ask_count += 1
            profile.wechat_effective_ask_count += 1
            profile.last_contact_request_type = 'wechat'
            return profile.wechat_ask_count

    def record_rejection(self, profile: UserProfile, contact_type: str) -> None:
        """
        记录拒绝

        Args:
            profile: 用户档案
            contact_type: 'phone' | 'wechat'
        """
        if contact_type == 'phone':
            profile.rejected_phone = True
        else:
            profile.rejected_wechat = True

    def record_collection(
        self,
        profile: UserProfile,
        contact_type: str,
        value: str
    ) -> None:
        """
        记录收集成功

        Args:
            profile: 用户档案
            contact_type: 'phone' | 'wechat'
            value: 联系方式值
        """
        if contact_type == 'phone':
            profile.phone = value
            profile.phone_collected = True
            self.reset_invalid_input(profile, 'phone')
        else:
            profile.wechat = value
            profile.wechat_collected = True
            self.reset_invalid_input(profile, 'wechat')

    # ==================== 辅助方法 ====================

    def is_hongkong_user(self, profile: UserProfile) -> bool:
        """
        判断是否香港用户

        Args:
            profile: 用户档案

        Returns:
            bool: 是否香港用户
        """
        # 优先使用缓存值
        if profile.is_hongkong_user is not None:
            return profile.is_hongkong_user

        if not profile.location:
            return False

        location_lower = profile.location.lower()
        is_hk = '香港' in location_lower or 'hk' in location_lower

        # 缓存结果
        profile.is_hongkong_user = is_hk
        return is_hk

    def get_max_asks(self, profile: UserProfile, contact_type: str) -> int:
        """
        获取最大询问次数

        Args:
            profile: 用户档案
            contact_type: 'phone' | 'wechat'

        Returns:
            int: 最大询问次数
        """
        if contact_type == 'phone':
            return self.MAX_PHONE_ASKS

        is_hk = self.is_hongkong_user(profile)

        if is_hk:
            return self.MAX_WECHAT_ASKS_HK
        elif profile.phone_collected:
            return self.MAX_WECHAT_ASKS_NON_HK_WITH_PHONE
        else:
            return self.MAX_WECHAT_ASKS_NON_HK_WITHOUT_PHONE

    def get_status_display(self, profile: UserProfile) -> str:
        """
        获取联系方式状态显示

        Args:
            profile: 用户档案

        Returns:
            str: 状态显示字符串
        """
        # 判断是否正在询问
        phone_asking = (
            profile.phone_ask_count > 0
            and not profile.phone_collected
            and not profile.rejected_phone
        )
        wechat_asking = (
            profile.wechat_ask_count > 0
            and not profile.wechat_collected
            and not profile.rejected_wechat
        )

        # 构建状态列表
        phone_status = None
        wechat_status = None

        # 电话状态
        if profile.phone_collected and profile.phone:
            phone_status = f"电话: {profile.phone}"
        elif profile.rejected_phone:
            phone_status = "不愿留电话"
        elif phone_asking:
            if wechat_asking or profile.wechat_collected:
                phone_status = "电话暂缓"
            else:
                phone_status = "电话争取中"

        # 微信状态
        if profile.wechat_collected and profile.wechat:
            wechat_status = f"微信: {profile.wechat}"
        elif profile.rejected_wechat:
            wechat_status = "不愿留微信"
        elif wechat_asking:
            wechat_status = "微信争取中"

        # 组合状态
        if phone_status and wechat_status:
            return f"{phone_status}, {wechat_status}"
        elif phone_status:
            return phone_status
        elif wechat_status:
            return wechat_status
        else:
            return "未留"

    def get_action_dict(self, action: NextAction) -> dict:
        """
        将 NextAction 转换为字典格式（兼容旧代码）

        Args:
            action: 下一步动作

        Returns:
            dict: 动作字典
        """
        return {
            'ask_phone': action in (NextAction.ASK_PHONE, NextAction.PERSUADE_PHONE),
            'ask_wechat': action in (NextAction.ASK_WECHAT, NextAction.PERSUADE_WECHAT),
            'end': action == NextAction.END_CONVERSATION
        }
