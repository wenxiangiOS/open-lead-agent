# R005 联系方式收集需求

## 1. 文档定位

本文档定义联系方式什么时候收集、收集哪些方式、如何配置，以及收集完成后如何进入收尾。

## 2. 需求

联系方式收集必须后置。

系统只有在资料达到模板配置的触发条件，或用户主动表达愿意留联系方式时，才进入联系方式收集。

联系方式类型必须可配置，不能写死成电话和微信。不同模板可以配置不同方式：

- 婚恋：电话 + 微信
- 教培：电话 + 微信 + QQ
- 招聘：电话 + 邮箱
- 海外服务：WhatsApp + Telegram + Email

## 3. 背景

联系方式是高敏感字段。问得太早会显得压迫，也容易让用户觉得像营销机器人。

开源项目也不能把婚恋模板里的联系方式规则写死到引擎里，否则其他行业会很难复用。

## 4. 核心规则

### 4.1 触发条件

联系方式收集可以由两类情况触发：

1. 资料满足 `contact.trigger` 条件。
2. 用户主动表达愿意留联系方式。

未满足触发条件时，不主动索要联系方式。

### 4.2 联系方式和资料字段分离

联系方式不是普通资料字段。

资料字段用于判断用户画像，联系方式用于后续触达。它们应该分别配置、分别校验、分别进入流程。

### 4.3 联系方式类型可配置

每个联系方式方法应该包含：

- `key`：系统字段名，例如 `phone`、`wechat`、`email`
- `label`：展示名称，例如 手机号、微信、邮箱
- `type`：内置类型，例如 `phone`、`wechat`、`email`
- `required`：是否必须收集
- `validation`：可选校验规则

### 4.4 收集节奏

联系方式收集要低压、自然。

如果用户有顾虑，应先解释用途，再决定是否继续争取。不要重复同一句固定话术。

### 4.5 收集完成后收尾

当联系方式满足模板要求后，系统应该进入收尾流程。

收尾不是继续无休止聊天，而是自然告诉用户后续会再沟通，并停止继续索要资料。

## 5. 配置

```yaml
contact:
  enabled: true
  trigger:
    required_fields:
      - sex
      - age
      - location
      - occupation
    min_collected_core: 3

  privacy_message: "主要是后续沟通更顺一点，不会拿来随便打扰你。"

  methods:
    - key: phone
      label: 手机号
      type: phone
      required: true
      ask: "后续沟通会方便一点，你留个手机号可以吗？"

    - key: wechat
      label: 微信
      type: wechat
      required: false
      ask: "微信也可以，看你哪个更方便。"
```

其他行业可以这样配置：

```yaml
contact:
  methods:
    - key: email
      label: 邮箱
      type: email
      required: true
    - key: telegram
      label: Telegram
      type: text
      required: false
      validation:
        pattern: "^@?[A-Za-z0-9_]{5,32}$"
```

## 6. 示例

### 示例 1：资料不足，不问联系方式

```text
用户：你好
AI：你好呀，我在呢。你这边是男生还是女生呀？
```

结果：

- 资料不足
- 不主动问电话或微信

### 示例 2：资料足够，进入联系方式

```text
用户：我在深圳，做老师，男生，95年
AI：大概情况我有数了。后续沟通会方便一点，你留个手机号或微信可以吗？
```

结果：

- 满足 `contact.trigger`
- 系统自然进入联系方式收集

### 示例 3：用户问为什么留联系方式

```text
用户：为什么要留电话？
AI：主要是后续沟通起来会顺一点，有进展也方便联系你，不是拿来随便打扰你的。
```

结果：

- 先答疑
- 不把疑问当成联系方式拒绝

## 7. 实现位置

- `src/contact/engine.py`：联系方式方法选择和字段提取
- `src/policy/contact_gate.py`：判断是否允许进入联系方式流程
- `src/policy/closing.py`：联系方式完成后的收尾策略
- `src/policy/decision.py`：对话阶段决策
- `src/templates/config.py`：联系方式配置模型

## 8. 测试

- `tests/test_semantic_decision.py`
- `tests/test_closing_policy.py`
- `tests/test_http_api.py`
- `tests/test_matchmaking_regression.py`

## 9. 当前状态

已实现基础版。

当前共识：

- 联系方式必须可配置，不能写死电话和微信。
- 联系方式必须后置，不能一上来就索要。
- 收集完成后应该自然收尾。

后续可增强：

- 多联系方式的优先级、必填组合和替代关系可以继续增强。
- 用户拒绝联系方式后的争取次数和话术去重可以继续细化。
- 不同行业的联系方式校验规则可以沉淀成更多内置类型。
