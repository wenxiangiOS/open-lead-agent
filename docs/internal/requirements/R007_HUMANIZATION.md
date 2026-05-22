# R007 拟人化需求

## 1. 文档定位

本文档定义“足够拟人化”在项目里的含义、规则、配置入口和实现位置。

## 2. 需求

AI 要能代替人工完成线索沟通，但不能像表单机器人。

用户应该感觉系统在认真接话，而不是机械执行字段顺序。

## 3. 背景

拟人化不是多加“呀、呢、嗯嗯”，也不是每轮都夸用户。

真正影响体验的是：

1. 上下文感知
2. 承接式表达
3. 节奏控制

这三点决定了对话像不像真人。

## 4. 核心规则

### 4.1 上下文感知

系统要根据用户刚说的内容决定下一问。

例如用户说：

```text
用户：我来自深圳
```

更自然的下一问是：

```text
AI：深圳发展机会还挺多的呀，你现在是做什么工作的呀？
```

而不是机械回到固定顺序：

```text
AI：你是男生还是女生？
```

### 4.2 承接式表达

回复开头要接住用户当前主落点。

如果用户在表达顾虑，先接顾虑；如果用户在提供资料，先顺着资料；如果用户在提问，先回答问题。

不能只说“知道了”“收到”，然后马上切字段。

### 4.3 节奏控制

每轮最多推进一个核心主字段。

可以顺带一个相近中等字段，但必须轻量自然，不能让用户感觉被连环盘问。

FAQ、顾虑、换话题优先处理，处理完再回主线。

## 5. 禁止行为

- 不要像表单一样按固定字段顺序机械发问。
- 不要每轮重复同一句起手式。
- 不要空泛承接后立刻追问敏感字段。
- 不要刚回答完用户顾虑，就马上索要电话、微信或敏感资料。
- 不要暴露内部策略，例如“现在按优先级问你字段”“这个字段问了两次所以跳过”。
- 不要承诺过满，例如保证成功、马上安排见面、马上发对方资料。

## 6. 配置

拟人化由模板配置和引擎策略共同完成。

```yaml
persona:
  name: 小缘
  role: 同城相亲了解助手
  tone: 自然、亲切、低压

humanization:
  enabled: true
  acknowledge_user_message: true
  avoid_repeated_opening: true
  max_core_questions_per_turn: 1
  allow_related_side_question: true

dialogue_policy:
  answer_question_first: true
  avoid_internal_strategy_exposure: true
  avoid_overpromising: true
```

模板作者只需要配置风格方向和行业边界，不应该被迫手写每一种话术。

## 7. 示例

### 示例 1：顺着用户主动信息

```text
用户：我来自深圳
AI：深圳这边机会确实多，你现在主要做什么工作呀？
```

这里先收集 `location=深圳`，再顺着 location 找相近核心字段 `occupation`。

### 示例 2：先答疑，再回主线

```text
AI：你今年大概多大呀？
用户：你们怎么收费？
AI：收费这块你应该也想先问清楚，基础匹配是免费的。定制服务一般是可选的，不合适也可以拒绝。
```

这里不消耗 `age` 的有效询问次数。

### 示例 3：联系方式低压推进

```text
AI：大概情况我有数了。后续沟通会方便一点，你留个手机号或微信可以吗？
```

这里先做自然过渡，再进入联系方式，而不是硬切：

```text
AI：请提供手机号。
```

## 8. 实现位置

- `src/humanization/expression.py`：表达策略和措辞辅助
- `src/humanization/quality.py`：回复质量检查
- `src/conversation/response_builder.py`：组织最终回复
- `src/policy/field_routing.py`：上下文字段路由
- `src/policy/decision.py`：FAQ、联系方式、合规等阶段决策
- `templates/matchmaking/prompts/`：婚恋模板提示词

## 9. 测试

- `tests/test_response_quality.py`
- `tests/test_response_consistency.py`
- `tests/test_conversation_language.py`
- `tests/test_field_routing_policy.py`

## 10. 当前状态

已实现基础版。

当前共识：

- 拟人化由上下文感知、承接式表达、节奏控制共同构成。
- 主线字段不能机械按配置顺序一路问到底。
- 用户主动提供的信息可以成为下一问的上下文锚点。
- 用户疑问和顾虑优先于资料收集。

后续可增强：

- 继续沉淀更多行业无关的表达质量检查。
- 支持模板配置更细的口吻禁用词和高频句式去重。
- 对 LLM 输出做更强的后处理，避免暴露内部策略。
