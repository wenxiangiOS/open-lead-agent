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

    # 微信意图关键词（用户想用微信联系）
    WECHAT_INTENT_KEYWORDS: List[str] = [
        "留微信可以吗", "微信可以", "微信方便", "留微信行吗", "给微信可以吗",
        "我先给微信", "先给微信吧", "留微信吧",
        "用微信联系", "加微信", "微信联系", "用微信", "留个微信",
    ]

    # 电话拒绝偏好关键词（用户说电话不方便想用微信）
    PHONE_REFUSAL_PREFERENCE_KEYWORDS: List[str] = [
        "电话不方便", "电话不行", "电话不方便留", "不方便留电话", "电话不好留"
    ]

    # 通用联系方式偏好（用户明确说用某种方式）
    CONTACT_PREFERENCE_KEYWORDS: List[str] = [
        "用微信联系吧", "微信吧", "用微信吧", "加微信吧", "微信也行",
    ]

    SOFT_ACK_MESSAGES: List[str] = [
        "嗯", "嗯嗯", "恩", "好", "好的", "好呀", "好的呢", "行", "可以", "ok", "好的哈"
    ]
    # ==================== 提示词模板 ====================

    PROMPT_END_CONVERSATION = """

【end_conversation】
【当前任务：结束对话收尾】
用户已拒绝提供微信和电话，现在需要礼貌地结束对话。

回复要求：
• 用自然、友好的方式结束对话
• 表达如果以后有需要可以再联系
• 保持简短，1-2句话即可

参考风格（可灵活调整）：
- "好的呢～那有需要再联系我哈，祝你生活愉快～"
- "嗯嗯好的呀～那先这样哈～有需要随时找我呀～"

禁止行为：
❌ 禁止继续收集任何用户信息
❌ 禁止再问任何问题
"""

    PROMPT_ASK_PHONE_FIRST = """

【⚠️⚠️⚠️立即执行-询问电话⚠️⚠️⚠️】
【当前任务：首次询问电话号码】
用户资料已收集完成，这是首次询问电话，用户还没提供过任何联系方式。

回复要求：
• 用自然、亲切的方式询问用户的电话号码
• 简单说明用途（方便后续联系）
• 保持简短，1-2句话即可

参考风格（可根据语境灵活调整）：
- "方便留个电话吗？后续有合适的人选时联系你～"
- "留个电话号码方便后续联系哦～"

禁止行为：
❌ 禁止提"微信"、"WX"、"weixin"等与微信相关的词
❌ 禁止使用"嗯嗯"、"好的呀"等无意义开场白
❌ 禁止过度解释电话用途
"""

    PROMPT_PERSUADE_PHONE = """

【⚠️⚠️⚠️立即执行-争取电话⚠️⚠️⚠️】
【当前任务：争取电话号码】
用户刚才说不留电话，这是第一次拒绝，需要争取一下。

回复要求：
• 解释电话的用途，打消用户顾虑
• 说明电话只是系统登记用，保护隐私
• 保持简短，1-2句话

参考风格（可灵活调整）：
- "这个电话只是用于系统登记哈，牵线的小伙伴才能对接到你，我们是不能够私下去牵线的～请你放心～"
- "电话只是登记用的哦，有合适的人选才能联系到你，我们不会私下打扰的～"

禁止行为：
❌ 禁止提"微信"、"WX"、"weixin"等与微信相关的词
❌ 禁止使用"没关系哒～"、"那先这样"等放弃语气
❌ 禁止使用"嗯嗯"、"好的呀"等无意义开场白
"""

    PROMPT_ASK_PHONE_AFTER_WECHAT_REJECTED = """

【⚠️⚠️⚠️立即执行-询问电话（微信已拒）⚠️⚠️⚠️】
【当前任务：询问电话号码（微信已拒绝）】
用户已拒绝微信，现在询问电话号码。

回复要求：
• 表示理解，然后询问电话
• 保持简短，1-2句话
• 不要有放弃或结束的语气

参考风格（可灵活调整）：
- "好的那留个电话也可以哦，后续有合适的人选时联系你～"
- "没关系呀～那留个电话也行，后续联系你～"

禁止行为：
❌ 禁止使用"嗯嗯好的呀～那先这样哈～"等结束语气
❌ 禁止使用"祝你早日脱单"、"有需要再联系"等结束对话用语
❌ 禁止提微信
"""

    PROMPT_ASK_PHONE_AFTER_WECHAT_COLLECTED = """

【⚠️⚠️⚠️立即执行-询问电话（微信已收）⚠️⚠️⚠️】
【当前任务：询问电话号码（联系方式已收集）】
用户的联系方式已记录，现在询问电话号码以便更及时联系。

回复要求：
• 确认已记录，然后询问电话
• 保持简短，1-2句话
• 语气自然亲切

参考风格（可灵活调整）：
- "好的呀～记下啦😊 对啦，方便再留个电话号码吗？电话联系会更方便及时呢～"
- "好哒～记下啦😊 对了对了，方便再留个电话吗？电话联系更方便哦～"

禁止行为：
❌ 禁止使用"嗯嗯好的呀～那先这样哈～"等结束语气
❌ 禁止使用"祝你早日脱单"、"有需要再联系"等结束对话用语
❌ 禁止提"微信"、"WX"、"weixin"等词
"""

    PROMPT_ASK_WECHAT_FIRST = """

【⚠️⚠️⚠️立即执行-询问微信⚠️⚠️⚠️】
【当前任务：首次询问微信号】
这是首次询问微信，用户还没提供过任何联系方式。

回复要求：
• 用自然、亲切的方式询问用户的微信号
• 简单说明用途（方便后续联系）
• 保持简短，1-2句话即可

参考风格（可灵活调整）：
- "要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～"
- "如果你微信常用的话，留一个也行，后续联系会方便些～"

禁止行为：
❌ 禁止提"电话"、"手机号"等与电话相关的词
❌ 禁止使用"嗯嗯"、"好的呀"等无意义开场白
"""

    PROMPT_ASK_WECHAT_AFTER_PHONE_REJECTED = """

【⚠️⚠️⚠️立即执行-询问微信（电话已拒）⚠️⚠️⚠️】
【当前任务：询问微信（电话已拒绝）】
用户已拒绝电话，现在询问微信。

回复要求：
• 表示理解，然后询问微信
• 保持简短，1-2句话

参考风格（可灵活调整）：
- "好的，那微信留一个也可以，后面联系会方便一点～"
- "没关系呀，要是微信方便的话，留一个也行～"

禁止行为：
❌ 禁止提电话
❌ 禁止使用"嗯嗯好的呀～那先这样哈～"等结束语气
"""

    PROMPT_ASK_WECHAT_ON_USER_PREFERENCE = """

【⚠️⚠️⚠️立即执行-接住微信方案⚠️⚠️⚠️】
【当前任务：用户主动提出留微信】
用户这轮明确表示微信更方便，你要顺着用户的选择接住微信方案。

回复要求：
• 明确表示微信可以
• 自然请用户直接发微信号
• 保持简短，1-2句话
• 语气要像接住用户的提议，不要像重新发起盘问

参考风格（可灵活调整）：
- "可以呀，那你直接发我微信号就行，我这边先记下来～"
- "没问题呀，你方便的话把微信发过来就好，后面联系也可以～"

禁止行为：
❌ 禁止继续坚持其他联系方式
❌ 禁止转成隐私解释长文
❌ 禁止出现结束对话语气
"""

    PROMPT_PERSUADE_WECHAT = """

【⚠️⚠️⚠️立即执行-争取微信⚠️⚠️⚠️】
【当前任务：争取微信】
用户刚才说不留微信，这是第一次拒绝，需要争取一下。

回复要求：
• 解释微信的用途，打消用户顾虑
• 说明不会随便打扰
• 保持简短，1-2句话

参考风格（可灵活调整）：
- "微信主要是方便后面沟通，我们不会随便打扰你的～"
- "如果你微信方便的话，留一个就行，有合适的情况再联系你～"

禁止行为：
❌ 禁止提"电话"、"手机号"等与电话相关的词
❌ 禁止使用"没关系哒～"、"那先这样"等放弃语气
❌ 禁止使用"嗯嗯"、"好的呀"等无意义开场白
❌ 禁止使用"有需要再联系"等结束对话用语
"""

    PROMPT_HK_ASK_WECHAT = """

【⚠️⚠️⚠️立即执行-询问微信（香港）⚠️⚠️⚠️】
【当前任务：询问微信（香港用户）】
已收集电话号码，现在询问微信号。

回复要求：
• 用自然、亲切的方式询问微信
• 保持简短，1-2句话

参考风格（可灵活调整）：
- "要是你微信方便的话，也可以留一个，后面联系会更顺手一点～"
- "如果你微信常用的话，留一个也行，后续沟通方便些～"
"""

    PROMPT_HK_PERSUADE_WECHAT = """

【⚠️⚠️⚠️立即执行-争取微信（香港）⚠️⚠️⚠️】
【当前任务：争取微信（香港用户）】
香港用户的电话已收集，用户刚才拒绝微信，需要争取一下。

回复要求：
• 解释微信的用途，打消用户顾虑
• 保持简短，1-2句话

参考风格（可灵活调整）：
- "微信主要是方便后面联系你，我们不会随便打扰你的～"
- "如果你微信方便的话，留一个也行，有合适的人选再联系你～"

禁止行为：
❌ 禁止使用"嗯嗯"、"好的呀"等无意义开场白
❌ 禁止使用"那先这样"、"有需要再联系"等结束对话用语
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
        # === 优先级0: 用户主动提出联系方式偏好 ===
        if self.prefers_wechat_over_phone(user_message, profile):
            logger.info("[联系方式偏好] 用户拒绝电话但愿意留微信，切换到微信流程")
            return NextAction.ASK_WECHAT

        is_hk = self.is_hongkong_user(profile)

        if self._should_switch_from_phone_to_wechat(profile, user_message, is_hk):
            logger.info("[联系方式保护] 低信息确认后不继续追问电话，切到微信方案")
            return NextAction.ASK_WECHAT

        if self._should_switch_from_wechat_to_phone(profile, user_message, is_hk):
            logger.info("[联系方式保护] 低信息确认后不继续追问微信，切到电话方案")
            return NextAction.ASK_PHONE

        # 场景1: 双方都被拒绝 → 结束对话
        if profile.rejected_phone and profile.rejected_wechat:
            return NextAction.END_CONVERSATION

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
            should_end_conversation=self.should_end_conversation(profile),
            is_hongkong_user=self.is_hongkong_user(profile),
        )

    # 联系方式已收集，继续收集其他字段的指令
    PROMPT_CONTINUE_OTHER_FIELDS = """

【联系方式已处理完毕】
电话/微信已收集或已拒绝，现在继续收集其他用户信息。
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
            # 收尾逻辑统一由 prompts.py 的【收尾话术】处理
            # 这里不再返回额外指令，避免与 prompts.py 冲突
            # prompts.py 会根据"已留联系"状态自动区分：
            # - 有联系方式 → "那你等好消息啦，祝你早日脱单"
            # - 无联系方式 → "有需要随时找我呀"
            instruction = ""
            logger.info(f"[联系方式指令] 双方都被拒绝，收尾由 prompts.py 统一处理")

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
            # 联系方式已处理完毕（已收集或已拒绝），继续收集其他字段
            # 检查是否有任何联系方式已收集
            has_contact = profile.phone_collected or profile.wechat_collected
            if has_contact:
                instruction = self.PROMPT_CONTINUE_OTHER_FIELDS
                logger.info(f"[联系方式指令] 联系方式已处理完毕，继续收集其他字段")

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
        explicit_contact_preference = any(keyword in user_message for keyword in self.CONTACT_PREFERENCE_KEYWORDS)
        refuses_phone = self._message_indicates_phone_refusal_preference(user_message)
        return wants_wechat and (refuses_phone or explicit_contact_preference)

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
            and not profile.wechat_collected
            and not profile.rejected_wechat
            and not profile.phone_collected
            and not profile.rejected_phone
        )

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
        logger.info(f"[拒绝检测-入口] 消息完整内容='{message}', phone_ask_count={profile.phone_ask_count}, wechat_ask_count={profile.wechat_ask_count}")

        message_lower = message.lower()

        # 检测显式拒绝
        phone_refusal = self._is_explicit_refusal(message_lower, 'phone')
        wechat_refusal = self._is_explicit_refusal(message_lower, 'wechat')
        general_refusal = self._has_general_refusal(message_lower)

        # 详细匹配日志
        logger.info(f"[拒绝检测-分析] 电话拒绝={phone_refusal}, 微信拒绝={wechat_refusal}, 通用拒绝={general_refusal}, last_response={'有' if last_response else '无'}")

        # 如果没有检测到任何拒绝，输出详细信息
        if not phone_refusal and not wechat_refusal and not general_refusal:
            matched_phone = [kw for kw in self.PHONE_REFUSAL_KEYWORDS if kw in message_lower]
            matched_general = [kw for kw in self.GENERAL_REFUSAL_KEYWORDS if kw in message_lower]
            logger.info(f"[拒绝检测-详细] 匹配的电话关键词={matched_phone}, 匹配的通用关键词={matched_general}")

        result = None

        # === 核心逻辑：根据当前状态决定判断优先级 ===
        # 电话已收集 → 优先判断微信拒绝
        # 微信已收集 → 优先判断电话拒绝
        # 都没收集 → 根据 last_response 内容判断

        phone_collected = profile.phone_collected and profile.phone
        wechat_collected = profile.wechat_collected and profile.wechat

        # 检查 last_response 的上下文
        # 调试：打印 last_response 的实际内容
        logger.info(f"[拒绝检测-调试] last_response 内容: '{last_response}'")
        is_about_phone = self._is_context_about(last_response, 'phone')
        is_about_wechat = self._is_context_about(last_response, 'wechat')

        logger.info(f"[拒绝检测-上下文] 电话已收集={phone_collected}, 微信已收集={wechat_collected}, 关于电话={is_about_phone}, 关于微信={is_about_wechat}")

        user_mentions_wechat = any(marker in message_lower for marker in ['微信', 'wx', 'weixin'])
        user_mentions_phone = any(marker in message_lower for marker in ['电话', '手机', '手机号', '号码'])

        # === 情况1：电话已收集，正在询问微信 ===
        if phone_collected and not wechat_collected:
            if wechat_refusal or (general_refusal and (is_about_wechat or user_mentions_wechat)):
                logger.info(f"[拒绝检测] 电话已收集，检测到微信拒绝")
                result = self._handle_refusal(profile, 'wechat', wechat_refusal)

        # === 情况2：微信已收集，正在询问电话 ===
        elif wechat_collected and not phone_collected:
            if phone_refusal or (general_refusal and (is_about_phone or user_mentions_phone)):
                logger.info(f"[拒绝检测] 微信已收集，检测到电话拒绝")
                result = self._handle_refusal(profile, 'phone', phone_refusal)

        # === 情况3：都没收集，根据 last_response 判断 ===
        elif not phone_collected and not wechat_collected:
            # 先检查显式拒绝
            if phone_refusal:
                logger.info(f"[拒绝检测] 检测到显式电话拒绝")
                result = self._handle_refusal(profile, 'phone', True)
            elif wechat_refusal:
                logger.info(f"[拒绝检测] 检测到显式微信拒绝")
                result = self._handle_refusal(profile, 'wechat', True)
            # 再根据上下文判断
            elif general_refusal:
                if user_mentions_wechat:
                    logger.info(f"[拒绝检测] 通用拒绝 + 明确提及微信，按微信拒绝处理")
                    result = self._handle_refusal(profile, 'wechat', False)
                elif user_mentions_phone:
                    logger.info(f"[拒绝检测] 通用拒绝 + 明确提及电话，按电话拒绝处理")
                    result = self._handle_refusal(profile, 'phone', False)
                elif is_about_wechat:
                    logger.info(f"[拒绝检测] 根据上下文检测到微信拒绝")
                    result = self._handle_refusal(profile, 'wechat', False)
                elif is_about_phone:
                    logger.info(f"[拒绝检测] 根据上下文检测到电话拒绝")
                    result = self._handle_refusal(profile, 'phone', False)
                # 通用拒绝 + 已询问过（根据已拒绝状态智能判断）
                elif profile.rejected_phone and not profile.rejected_wechat:
                    # 电话已拒绝，只处理微信
                    if profile.wechat_ask_count >= 1:
                        logger.info(f"[拒绝检测] 电话已拒绝，处理微信拒绝")
                        result = self._handle_refusal(profile, 'wechat', False)
                elif profile.rejected_wechat and not profile.rejected_phone:
                    # 微信已拒绝，只处理电话
                    if profile.phone_ask_count >= 1:
                        logger.info(f"[拒绝检测] 微信已拒绝，处理电话拒绝")
                        result = self._handle_refusal(profile, 'phone', False)
                elif not profile.rejected_phone and not profile.rejected_wechat:
                    # 都没被拒绝，按顺序处理（先电话后微信）
                    if profile.phone_ask_count >= 1:
                        logger.info(f"[拒绝检测] 电话已询问过，处理电话拒绝")
                        result = self._handle_refusal(profile, 'phone', False)
                    elif profile.wechat_ask_count >= 1:
                        logger.info(f"[拒绝检测] 微信已询问过，处理微信拒绝")
                        result = self._handle_refusal(profile, 'wechat', False)
                else:
                    logger.info(f"[拒绝检测] 通用拒绝但无法确定目标")
        else:
            logger.info(f"[拒绝检测] 未匹配任何情况分支")

        if result:
            logger.info(f"[拒绝检测] 检测到拒绝: {result.contact_type}, 最终={result.is_final}, 次数={result.ask_count_after}")
        else:
            logger.info(f"[拒绝检测] 未检测到联系方式拒绝，general_refusal={general_refusal}")

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
                '电话只是', '电话用于', '请你放心', '保护你的隐私', '不会私下'
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

        在检测到拒绝时递增计数器，这样后续 get_next_action 能正确判断
        """
        if contact_type == 'phone':
            # 递增询问次数
            profile.phone_ask_count += 1
            new_count = profile.phone_ask_count
            max_asks = self.get_max_asks(profile, 'phone')

            # 判断是否达到上限
            if new_count >= max_asks:
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
            # 递增询问次数
            profile.wechat_ask_count += 1
            new_count = profile.wechat_ask_count
            max_asks = self.get_max_asks(profile, 'wechat')

            # 判断是否达到上限
            if new_count >= max_asks:
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
            return profile.phone_ask_count
        else:
            profile.wechat_ask_count += 1
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
        else:
            profile.wechat = value
            profile.wechat_collected = True

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
