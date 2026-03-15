# 联系方式收集功能文档

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

### 4.1 询问次数上限

| 用户类型 | 场景 | 电话上限 | 微信上限 |
|---------|------|---------|---------|
| 香港用户 | 任意 | 2 次 | 2 次 |
| 非香港用户 | 电话已收集 | - | 1 次 |
| 非香港用户 | 电话未收集/被拒绝 | 2 次 | 2 次 |

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

### 4.3 香港用户判断

```python
def is_hongkong_user(location: str) -> bool:
    if not location:
        return False
    location_lower = location.lower()
    return '香港' in location_lower or 'hk' in location_lower
```

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
    │    收集完成         │  │   检查是否结束      │
    │ (电话+微信都有)     │  │ (双方都被拒绝?)    │
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
    ├─ DialogueManager.build_main_dialogue_prompt()  # 构建提示词
    │   │
    │   └─ ContactCollectionService.build_instruction()
    │       ├─ get_next_action() → 决定下一步动作
    │       └─ 返回 (instruction, next_action)
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
