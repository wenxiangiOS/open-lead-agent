# 联系方式收集功能文档

## 2026-04-14 Root Cause Guardrails

- 无效手机号/微信重试文案改为规则直出，不再依赖 AI 自由生成。
- 短号、长号、格式错、香港号地区不一致都必须按校验结果给出对应引导，不能把“输错号码”误说成“有顾虑”。
- 本轮一旦成功收到了有效 `phone/wechat/contact`，禁止通用的 `force_progress_followup` 再把问题打回 `contact`。
- 联系方式补追问只能走专门的联系方式流；如果已经收到了电话，再追问时要明确追微信，不能退化成泛化的“再留个手机号”。
- 对“我不是已经留过电话了吗，为什么还问”这类质疑，单独识别为 repeated-contact FAQ，不能落回通用的资料收集用途解释。

## 一、功能概述

本功能负责在对话过程中自然地收集用户的联系方式（电话和微信），支持以下场景：
- 用户主动提供联系方式
- AI 主动询问联系方式
- 用户拒绝提供联系方式
- 香港用户与非香港用户的差异化处理

---

## 二、核心文件

| 文件 | 职责 |
|-----|------|
| `src/services/collection/contact_collection_service.py` | 核心业务逻辑（决策、拒绝检测、状态管理） |
| `src/models/user_profile.py` | 数据模型（字段定义、简单状态方法） |
| `src/services/core/dialogue_manager.py` | 调用服务构建对话提示词 |
| `src/services/core/chat_service.py` | 调用服务处理拒绝检测 |
| `tests/test_contact_collection_service.py` | 50 个单元测试 |

---

## 三、数据模型

### UserProfile 相关字段

```python
class UserProfile:
    # 联系方式值
    phone: Optional[str]           # 电话号码
    wechat: Optional[str]          # 微信号

    # 收集状态
    phone_collected: bool          # 电话是否已收集
    wechat_collected: bool         # 微信是否已收集

    # 询问次数（用于判断是否达到上限）
    phone_ask_count: int           # 电话询问次数 (0-2)
    wechat_ask_count: int          # 微信询问次数 (0-2)
    phone_effective_ask_count: int # 电话有效询问次数（流程完成判断）
    wechat_effective_ask_count: int# 微信有效询问次数（流程完成判断）
    phone_invalid_input_retry_count: int   # 电话无效输入重试次数
    wechat_invalid_input_retry_count: int  # 微信无效输入重试次数
    phone_invalid_input_closed: bool       # 电话是否因无效输入关闭主动追问
    wechat_invalid_input_closed: bool      # 微信是否因无效输入关闭主动追问
    contact_complete: bool                 # 联系方式流程是否已完成

    # 拒绝状态
    rejected_phone: bool           # 用户是否最终拒绝电话
    rejected_wechat: bool          # 用户是否最终拒绝微信

    # 用户类型
    is_hongkong_user: Optional[bool]  # 是否香港用户（缓存）
```

### 状态显示

| 状态 | 显示字符串 |
|-----|-----------|
| 都未开始 | `"未留"` |
| 正在询问电话 | `"电话争取中"` |
| 正在询问微信 | `"微信争取中"` |
| 已收集电话 | `"电话: xxx"` |
| 已收集微信 | `"微信: xxx"` |
| 都已收集 | `"电话: xxx, 微信: xxx"` |
| 拒绝电话 | `"不愿留电话"` |
| 拒绝微信 | `"不愿留微信"` |
| 有电话，正在问微信 | `"电话: xxx, 微信争取中"` |
| 电话被拒，有微信 | `"不愿留电话, 微信: xxx"` |
| 都被拒 | `"不愿留电话, 不愿留微信"` |

---

## 四、业务规则

### 4.0 上下游边界（新增）

`ContactCollectionService` 只负责：

- 电话 / 微信流程状态机
- 联系方式拒绝检测
- 联系方式下一步动作（`ASK_PHONE / ASK_WECHAT / PERSUADE_* / END_CONVERSATION / NONE`）

它**不单独决定**“这一轮是否真的允许切到联系方式”。

真正的进入时机由上游资料收集策略控制，统一经过：

- Coverage Gate
- Profile Sufficiency Gate
- Turn Quality Gate
- Cost Control Gate

所以必须区分两件事：

- `next_action = ASK_PHONE`
  只表示联系方式服务认为“下一步如果进入联系方式流程，应先问电话”
- `allow_contact_push = true`
  才表示上游策略允许这轮真正切到联系方式

如果上游 gate 未通过，即使 `next_action` 已经是 `ASK_PHONE`，提示词层也必须继续压制联系方式提示。

### 4.1 询问次数上限

| 用户类型 | 场景 | 电话上限 | 微信上限 |
|---------|------|---------|---------|
| 香港用户 | 任意 | 2 次 | 2 次 |
| 非香港用户 | 电话已收集 | - | 1 次 |
| 非香港用户 | 电话未收集/被拒绝 | 2 次 | 2 次 |

### 4.1.1 有效询问次数定义（新增）

`phone_ask_count / wechat_ask_count` 是当前兼容实现里的原始询问计数；  
真正用于流程完成判断的统一口径，应以 **有效询问次数** 为准。

#### 什么叫有效询问

一轮联系方式询问只有同时满足以下条件，才计入 `effective_ask_count`：

- 这一轮系统明确在问电话或微信
- 用户获得了稳定回答机会
- 这一轮没有被以下事件打断：
  - FAQ
  - boundary / 拒答
  - complaint
  - 风险话题
  - 跑题
  - 乱码 / 手滑 / 错误输入
  - 后处理把原本的联系方式追问改没了

#### 什么不算有效询问

- 刚问微信，用户发了一串乱码
- 刚问电话，用户转去问收费
- 刚问电话，用户说“为什么要问这个”
- 本轮原本在问联系方式，但最终发给用户的话术已经不是联系方式追问

### 4.1.2 无效输入重试定义（新增）

联系方式阶段要额外区分 **无效输入重试次数**：

- `phone_invalid_input_retry_count`
- `wechat_invalid_input_retry_count`

用途：

- 无效输入 / 乱码 **不直接计入有效询问次数**
- 但会计入无效输入重试次数
- 连续达到关闭上限后，停止主动追问该联系方式

当前建议口径：

- 第 1 次错误输入：轻提醒，请直接重发
- 第 2 次错误输入：再次简短提醒，请直接重发
- 第 3 次错误输入：关闭主动追问

关闭后：

- 不再围绕该联系方式继续重复索要
- 只有用户后续主动发出看起来像真实联系方式的内容时，才再次尝试识别

### 4.1.3 无效联系方式重试回复的展示约束（新增）

无效手机号 / 微信号命中验证重试时，验证反馈必须视为 **最终展示回复**，不能被 raw mode 或首轮 AI 原文覆盖。

也就是说：

- 联系方式验证层一旦产出“请重发正确联系方式”的回复
- 这一轮最终发给用户的话术必须使用该回复
- 不能继续保留模型原本生成的闲聊、偏好追问、爱好追问或其他主线问题

这样做的原因是：

- 用户当前轮的主任务已经变成“纠正联系方式”
- 如果还把模型原话继续发出去，会造成流程状态和用户感知脱节
- 还会污染下一轮的 `last_asked_field / last_question_state`

### 4.1.4 已有资料值也必须算“已收集”（新增）

在联系方式补追问和收尾判断里，不能只依赖 `collection_progress`。

如果 `UserProfile` 上已经有稳定值，例如：

- `sex`
- `age / age_label`
- `location`
- `education`
- `occupation`
- `marital_status`
- `monthly_income`
- `partner_requirement`

那么这些字段在策略层也必须视为已收集；否则会出现：

- 用户画像面板里看起来资料已经齐了
- 但策略层仍误判“资料未完成”
- 收到有效电话后不继续追微信
- 反而回落到泛化的偏好追问或空悬话术

这类判断仍然属于同一套资料状态，不是第二套状态机。

### 4.1.5 contact 目标不能被兴趣爱好/闲聊问题覆盖（新增）

如果这一轮刷新后的主目标已经是 `ask_field=contact`，最终展示回复必须真的体现联系方式推进：

- 问电话时要出现 `电话 / 手机号 / 号码`
- 问微信时要出现 `微信`

不能出现这种情况：

- 决策层已经 `forced_ask_field=contact`
- 但最终展示仍然是“兴趣爱好 / 平时做什么 / 还有什么想补充”

这类回复属于空悬话术，因为它会让用户感知到的话题和系统内部真实状态脱节，导致联系方式流程停滞。

### 4.1.6 地点字段别名要统一回写到 `location`（新增）

AI 结构化提取里如果出现：

- `location`
- `所在地`
- `居住地`
- `residence`
- `residenceCity`

都必须统一映射到 `location`，不能因为别名未归一而让“深圳/杭州/北京”这类明确城市信息在首轮被丢失。

### 4.1.7 raw mode 也不能吞掉联系方式补追问（新增）

raw mode 默认优先保留模型原句，但联系方式场景要单独加白：

- 如果本轮已经成功收到了有效电话，且下一步状态机是 `ask_wechat / persuade_wechat`
- 或者本轮已经进入 `ask_field=contact` 的联系方式推进

那么最终展示回复必须优先保留联系方式改写结果，至少要继续体现：

- 电话后追微信
- 微信后追电话
- 联系方式格式错误时重发引导

不能因为 raw mode 冻结了模型原句，又退回到：

- 性格偏好追问
- 兴趣爱好追问
- 泛化资料追问

否则就会出现“内部状态已经在联系方式流里，用户看到的却是别的话题”的错位。

### 4.2 拒绝检测规则

```
用户消息
    │
    ├─ 显式拒绝关键词
    │   ├─ 电话: "不留电话"、"不给电话"、"不想留电话"...
    │   └─ 微信: "不留微信"、"不给微信"、"不想留微信"...
    │
    ├─ 通用拒绝词 + 上下文
    │   ├─ 通用词: "不用了"、"不需要"、"不想留"、"不方便"...
    │   └─ 上下文: 上一轮 AI 提到"电话"或"微信"
    │
    └─ 判断逻辑
        ├─ 首次拒绝 → ask_count + 1
        └─ 达到上限 → rejected_xxx = True
```

补充规则：

- 如果用户明确表示电话不方便，但愿意改留微信，例如“电话不方便，留微信可以吗”，当轮应优先切换到微信流程。
- 这类表达不等同于最终拒绝电话，而是联系方式偏好切换；后续在拿到微信后，仍可按现有规则再轻问一次电话。
- 口语化表达如“微信可以不”“微信行不”“微信可不可以”按同一规则处理：
  - 先暂停电话收集
  - 当轮直接切到微信流程
  - 不把电话记为最终拒绝
  - 不额外增加电话有效询问次数
  - 微信收集成功后，再恢复电话流程

### 4.2.1 主动拒绝规则（新增）

除了被 AI 主动询问后的拒绝，还要覆盖用户 **主动拒绝联系方式** 的场景。

#### 主动拒绝电话

例如：

- `不留电话`
- `不给电话`
- `电话不方便`

处理原则：

- 如果是明确拒绝，直接更新电话拒绝状态
- 如果是“电话不方便，但微信可以”，这属于联系方式偏好切换
  - 当轮优先切微信
  - 不等同于电话和微信都结束

#### 主动拒绝微信

例如：

- `不留微信`
- `微信不方便`

处理原则：

- 更新微信拒绝状态
- 是否视为微信流程最终结束，要结合该项的有效询问上限判断

#### 同条消息里同时拒绝两种联系方式

例如：

- `电话微信都不留`

处理原则：

- 电话流程完成
- 微信流程完成
- `contact_complete=True`
- 是否进入整段对话收尾，由上层策略决定

### 4.3 香港用户判断

```python
def is_hongkong_user(location: str) -> bool:
    if not location:
        return False
    location_lower = location.lower()
    return '香港' in location_lower or 'hk' in location_lower
```

### 4.4 联系方式进入前置条件（新增）

联系方式不再要求“前序字段全部收集成功”。

当前统一口径：

#### Coverage Gate

- 核心字段 `sex/age/education/occupation/location`
  - 收集成功，或已主动问满 2 次，即视为已覆盖
- 准核心/中等字段 `marital_status/partner_requirement/monthly_income`
  - 收集成功，或已主动问过 1 次，即视为已覆盖
- 只有全部已覆盖，才有资格进入联系方式判断

#### Profile Sufficiency Gate

- 核心字段成功收集数至少 3 个，才允许进入联系方式

#### Turn Quality Gate

- 当前轮不是答疑优先 / 投诉修复 / 边界收口时，才适合切联系方式

#### Cost Control Gate

- 连续不配合、连续跑题、开放式补画像多次失败、或成本已偏高时，不再继续主动切联系方式

#### 进入联系方式的最终条件

只有同时满足下面 4 条，才允许真正展示联系方式提示：

- Coverage Gate = 通过
- Profile Sufficiency Gate = 通过
- Turn Quality Gate = 通过
- Cost Control Gate 允许继续推进

补充说明：

- `partner_requirement` 平时应自然穿插问，不抢主线
- 但如果核心字段都已覆盖、联系方式仍被中等字段卡住，则可临时升级为兜底覆盖目标，先问 1 次，再回到联系方式判断

### 4.5 联系方式流程完成定义（新增）

`contact complete` 不表示“电话和微信都已收集成功”，而表示：

- 电话流程已完成
- 且微信流程已完成

其中，每一项联系方式流程“已完成”都满足以下任一条件：

- 收集成功
- 明确拒绝
- 达到该场景下的有效询问上限
- 达到无效输入关闭上限，并停止主动追问

#### 电话流程完成条件

满足任一即可：

- `phone_collected=True`
- `rejected_phone=True`
- `phone_effective_ask_count >= phone_limit`
- `phone_invalid_input_closed=True`

#### 微信流程完成条件

满足任一即可：

- `wechat_collected=True`
- `rejected_wechat=True`
- `wechat_effective_ask_count >= wechat_limit`
- `wechat_invalid_input_closed=True`

#### 非香港用户的特殊口径

1. 如果电话已收集：

- 微信上限为 `1` 次有效询问

所以以下任一都视为微信流程完成：

- 微信已收集
- 微信已拒绝
- 微信已有效询问满 `1` 次
- 微信已连续无效输入达到关闭条件

2. 如果电话未收集成功 / 已被拒绝 / 已问满仍未收集到：

- 微信上限为 `2` 次有效询问

#### 典型成立场景

以下都应视为 `contact complete`：

- 电话收到了，微信也收到了
- 电话收到了，微信拒绝了
- 电话收到了，微信有效问满 1 次但没收上来（非香港用户）
- 电话有效问满 2 次没拿到，微信又有效问满 2 次没拿到
- 电话没收到，微信也没收到，但两边都已达到关闭条件

### 4.6 主动提供规则（新增）

用户主动提供联系方式时，默认不增加有效询问次数。

#### 用户主动提供电话

例如：

- `我电话 13800138000`

处理：

- `phone_collected=True`
- 电话流程直接完成
- 这一轮只做接收确认，不立刻追问微信
- 如果用户同轮还有显式问题/疑虑，先回答问题
- 后续优先继续核心字段与中等字段收集
- 只有在核心/中等字段都已收集完成，或有效询问次数都已达到上限后，才进入微信补采

#### 用户主动提供微信

例如：

- `微信 abc123`

处理：

- `wechat_collected=True`
- 微信流程直接完成
- 这一轮只做接收确认，不立刻追问电话
- 如果用户同轮还有显式问题/疑虑，先回答问题
- 后续优先继续核心字段与中等字段收集
- 只有在核心/中等字段都已收集完成，或有效询问次数都已达到上限后，才进入电话补采

#### 用户一条里同时提供电话和微信

例如：

- `电话 138...，微信 abc123`

处理：

- 两者都收集成功
- 直接 `contact_complete=True`

#### 用户在问电话时主动给微信

例如：

- `电话不方便，微信 abc123`

处理：

- 这是联系方式偏好切换
- 优先接住微信
- 电话不一定立刻视为最终拒绝
- 如果资料阶段还没完成，先回到资料主线
- 只有在核心/中等字段完成或问满后，才按现有电话流程规则决定是否补问电话

#### 主动提供联系方式的统一原则

- 主动提供 `电话/微信` 只表示该联系方式可以直接收下
- 不表示这一轮要立刻切换到“补另一种联系方式”
- `主动提供联系方式` 和 `系统主动追问联系方式` 必须分开处理
- 只有资料收集阶段完成，或字段有效询问预算耗尽后，才允许主动补采另一种联系方式

### 4.7 状态、动作、结束态的区别（新增）

必须严格区分以下概念：

#### `contact_state`

表示联系方式流程当前所处阶段，例如：

- `asking_phone`
- `phone_paused_for_wechat_switch`
- `phone_collected_wechat_pending`
- `asking_wechat`
- `contact_closed`

#### `next_action`

表示如果当前轮允许推进联系方式，下一步该做什么，例如：

- `ASK_PHONE`
- `PERSUADE_PHONE`
- `ASK_WECHAT`
- `PERSUADE_WECHAT`
- `NONE`

#### 渠道切换恢复规则（新增）

当电话流程中用户表达：

- `电话不方便，留微信可以吗`
- `微信可以不`
- `微信行不`

按“联系方式渠道切换”处理，而不是电话拒绝：

1. 当前轮暂停电话流程
2. 直接进入 `ASK_WECHAT`
3. `rejected_phone` 保持不变
4. `phone_ask_count / phone_effective_ask_count` 不因这句切换话术额外增加
5. 微信收集成功后，优先恢复一次电话流程
6. 恢复电话时使用“微信已收后的补充电话”问法，而不是继续沿用电话说服态

#### `contact_complete`

表示联系方式流程是否已经走完。

注意：

- `NONE` **不天然等于** `contact_complete=True`
- 只有电话流程和微信流程都已完成，才算 `contact_complete=True`

#### `should_end_conversation`

表示整段对话是否应该进入收尾。

注意：

- `contact_complete=True` 不等于整段对话必须立刻结束
- 例如电话已收、微信流程关闭后，也可能只是停止联系方式追问，而不是立刻结束会话

---

## 五、状态机流程

```
                    ┌─────────────┐
                    │   初始状态   │
                    │ (都未收集)  │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     询问电话 (最多2次)  │
              └────────────┬───────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ 用户提供电话 │  │ 用户拒绝电话 │  │ 继续询问   │
    │ phone=xxx   │  │ rejected    │  │ (未达上限) │
    └──────┬─────┘  └──────┬─────┘  └──────┬─────┘
           │               │               │
           │               │               └──────────┘
           ▼               ▼
    ┌────────────┐  ┌────────────────────────┐
    │ 电话已收集  │  │     询问微信           │
    │            │  │ (香港:2次, 非港:1次)  │
    └──────┬─────┘  └────────────┬───────────┘
           │                     │
           │         ┌───────────┼───────────┐
           │         │           │           │
           │         ▼           ▼           ▼
           │  ┌────────────┐ ┌────────────┐ ┌────────────┐
           │  │ 用户提供微信 │ │ 用户拒绝微信 │ │ 继续询问   │
           │  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
           │         │              │              │
           ▼         ▼              ▼              └──────────┘
    ┌─────────────────────┐  ┌─────────────────────┐
    │    联系方式流程完成   │  │   检查是否结束      │
    │ (电话流程+微信流程都完)│ │ (由上层决定收尾?)  │
    └─────────────────────┘  └──────────┬──────────┘
                                          │
                                          ▼
                                 ┌─────────────────────┐
                                 │   结束对话           │
                                 │ (标记为无效用户)     │
                                 └─────────────────────┘
```

---

## 六、场景示例

```
# 场景1: 用户主动提供电话
用户: "我叫张三，电话13800138000"
系统: phone="13800138000", phone_collected=True
后续: 询问微信（香港用户2次，非香港用户1次）

# 场景2: 用户拒绝电话后提供微信
用户: "不留电话" → "那微信是abc123"
系统: rejected_phone=True, wechat="abc123", wechat_collected=True
状态: "不愿留电话, 微信: abc123"

# 场景3: 双方都被拒绝
用户: "不留电话" → "不留微信"
系统: rejected_phone=True, rejected_wechat=True
动作: 结束对话，标记为无效用户

# 场景6: 电话问满未收集 + 微信问满未收集
用户位置: "北京"
系统: 电话有效询问2次未收集成功 → 微信有效询问2次未收集成功
结果: contact_complete=True

# 场景7: 电话已收集 + 微信连续错误输入
用户位置: "北京"
系统: 电话已收集 → 微信错误输入3次 → 停止主动追问微信
结果: wechat_invalid_input_closed=True, contact_complete=True

# 场景4: 香港用户完整流程
用户位置: "香港"
系统: 电话最多2次 → 微信最多2次

# 场景5: 非香港用户完整流程
用户位置: "北京"
系统: 电话最多2次 → 微信最多1次（电话已收集）
```

---

## 七、代码调用流程
```
用户发送消息
    │
    ▼
ChatService.process_chat_request()
    │
    ├─ _handle_refusal_detection()           # 拒绝检测
    │   │
    │   └─ ContactCollectionService.detect_refusal()
    │       ├─ 解析用户消息关键词
    │       ├─ 判断显式拒绝 / 上下文拒绝
    │       └─ 更新 ask_count / rejected 标志
    │
    ├─ 上游资料收集策略先判断:
    │   ├─ Coverage / Profile / Turn / Cost gate
    │   └─ 决定本轮是否 allow_contact_push
    │
    ├─ DialogueManager.build_main_dialogue_prompt()  # 构建提示词
    │   │
    │   └─ ContactCollectionService.build_instruction()
    │       ├─ get_next_action() → 决定下一步动作
    │       └─ 返回 (instruction, next_action)
    │
    │   ※ 若 allow_contact_push=False，则联系方式指令会被提示词层压制
    │
    └─ AI 生成回复
```

---

## 八、ContactCollectionService API
```
class ContactCollectionService:
    """联系方式收集服务"""

    # === 核心决策 ===
    get_next_action(profile) → NextAction
        # 返回: ASK_PHONE / ASK_WECHAT / PERSUADE_PHONE / PERSUADE_WECHAT / END_CONVERSATION / NONE

    build_instruction(profile) → (str, NextAction)
        # 返回: (指令字符串, 下一步动作)

    should_end_conversation(profile) → bool
        # 判断: 双方都被拒绝?

    # === 拒绝检测 ===
    detect_refusal(message, profile, last_response) → RefusalResult | None
        # 检测用户是否拒绝联系方式

    # === 状态管理 ===
    record_ask(profile, contact_type)          # 记录询问
    record_rejection(profile, contact_type)    # 记录拒绝
    record_collection(profile, type, value)    # 记录收集成功

    # === 辅助方法 ===
    is_hongkong_user(profile) → bool          # 判断香港用户
    get_max_asks(profile, contact_type) → int  # 获取最大询问次数
    get_status_display(profile) → str          # 获取状态显示
    get_action_dict(action) → dict             # NextAction 转 dict
```

---

## 九、测试覆盖
```
tests/test_contact_collection_service.py (50个测试)
├── is_hongkong_user 测试 (5个)
├── get_max_asks 测试 (4个)
├── get_next_action 测试 (9个)
├── build_instruction 测试 (3个)
├── detect_refusal 测试 (6个)
├── get_status_display 测试 (9个)
├── get_action_dict 测试 (5个)
├── should_end_conversation 测试 (3个)
└── record_* 方法测试 (6个)

tests/test_contact_collection_scenarios.py (16个测试)
├── 场景1: 双方被拒绝 (2个)
├── 场景2: 仅拒绝一种 (4个)
├── 场景3: 用户主动提供 (4个)
└── 场景4: AI主动询问 (3个) + 状态/指令测试 (3个)
```

---

## 十、快速参考

### 如何判断下一步做什么？
```python
from src.services.contact_collection_service import ContactCollectionService

service = ContactCollectionService()
action = service.get_next_action(user_profile)

if action == NextAction.ASK_PHONE:
    # 询问电话
elif action == NextAction.ASK_WECHAT:
    # 询问微信
elif action == NextAction.END_CONVERSATION:
    # 结束对话
```

### 如何检测用户拒绝？
```python
result = service.detect_refusal(
    message="不留电话",
    profile=user_profile,
    last_response="方便留个电话吗？"
)

if result:
    print(f"拒绝了: {result.contact_type}")
    print(f"是否最终拒绝: {result.is_final}")
```

### 如何获取状态显示？
```python
status = service.get_status_display(user_profile)
# 返回: "电话: 13800138000, 微信争取中"
```

---

## 十一、注意事项

1. **不要直接修改 `rejected_xxx` 标志**
   - 应该通过 `detect_refusal()` 方法，它会自动判断是否达到上限

2. **香港用户缓存**
   - `is_hongkong_user` 结果会缓存在 `profile.is_hongkong_user`
   - 首次判断后会复用缓存值

3. **非香港用户微信限制**
   - 电话已收集 → 微信最多 1 次
   - 电话未收集/被拒绝 → 微信最多 2 次

4. **状态显示的优先级**
   - 已收集 > 被拒绝 > 正在争取 > 未留
