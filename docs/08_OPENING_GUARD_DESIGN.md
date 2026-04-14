# 08 开场保护层设计

## 约束前提

本次优化**严格只做开场保护层，不新增独立 AI 请求，不改整体对话策略**。

也就是说：

- 不重构现有决策系统
- 不额外发起一条新的开场分类 AI 请求
- 不改字段收集优先级
- 不改联系方式推进策略
- 不改开场之外的主流程
- 只在开场窗口内，让规则和当前 AI 调用共同完成更稳的分流

## 最终核心原则

**规则已经能稳定识别的开场，不走 AI；只有规则判不稳的开场，才利用当前这次 AI 调用顺带完成意图识别。**

同时：

- **不开新的 AI 请求**
- **不改整体对话策略**
- **不重构主生成逻辑**
- **只把模糊 case 留给当前 AI**

## 关键现实约束

当前主模型链路 prompt 较重，且远程调用存在波动。把所有开场都交给当前 AI，会放大：

- 首轮时延
- 超时概率
- no-AI fallback 压力

因此最终方案必须是：

- **规则强前置**
- **当前 AI 只处理模糊 case**
- **fallback 补强**
- **一致性校验兜底**

## 方案目标

把开场识别做成一套稳定、低成本、可控的分流层。

最终效果：

- 确定性高的开场，规则直接处理
- 模糊开场、混合开场，才交给当前 AI 调用识别
- AI 超时或失败时，fallback 也不会掉回 `sex`
- 开场识别有明确开始条件和结束条件，不会越界干扰主线

## 总体结构

```text
用户输入
-> 开场硬规则判断
-> 若规则已稳定命中，则直接走现有执行链路
-> 若规则判不稳，再进入当前 AI 调用内的开场意图识别
-> 输出开场意图
-> 映射到现有 TurnDecision / 现有执行链路
-> 继续走现有生成逻辑
```

## 资料桥接追问

当用户在开场早期直接给出资料，且系统下一步主目标已经落到 `occupation`、同时 `monthly_income` 仍可主动追问时，不能只做“字段提取成功”，还要把这些刚给出的资料接到下一问里。

这层优化采用：

- **程序提供桥接约束**
- **AI 自然生成表达**
- **不写死模板话术**

具体要求：

- 用户刚给了 `location / marital_status` 这类资料时，下一问必须顺着这些信息继续聊
- `occupation + monthly_income` 默认绑定一起问
- 但表达必须自然口语化，不能退回泛化并列问法
- 禁止忽略用户刚给的信息，直接裸问“平时是做什么工作的？你现在收入大概在哪个范围……”

也就是说：

- 程序只负责告诉模型“本轮必须顺着什么信息去问、工作和月薪要绑定”
- 具体怎么说，仍然交给当前 AI 自然生成

补充约束：

- 如果当前计划追问字段是 `occupation`，且用户已给出 `location`，则优先使用“带地点承接”的职业追问
- 不能退化成脱离上下文的泛问，例如只问“你现在主要做哪方面工作呀？”
- 如果当前计划追问字段已经刷新成 `contact`，则本轮不能继续问择偶要求、兴趣爱好或其他未建模话题

## 计划追问优先于漂移回复

为了避免模型自由发挥把状态带偏，系统需要遵守下面两条：

- `turn_decision.ask_field` 是本轮主目标的第一真相
- 只要回复里仍然存在明确问句，本轮状态记录优先沿用计划字段，而不是被漂移后的文本问题反向改写

这条规则主要用于防止两类回归：

- 本轮原计划问 `contact`，模型却继续问“另一半要求 / 兴趣爱好”
- 本轮原计划问 `occupation`，模型却退回到更生硬的泛化问法，或者顺手问到别的字段

## 开场识别开始条件

只在下面条件满足时运行开场识别：

- `message_count <= 2`
- 当前未进入联系方式上下文
- 当前未进入投诉/修复上下文
- 当前未进入结束态

建议第一版严格使用：

**只在前 2 轮运行开场识别。**

## 开场识别结束条件

满足任一条件，立即停止开场识别：

- 已进入资料主线
- 已进入 FAQ 主线
- 已进入边界/拒绝主线
- 已进入联系方式上下文
- 已进入投诉/修复主线
- 已进入广告/无效流量处理
- `message_count > 2`

一句话：

**开场识别只负责完成开场分流，一旦主线明确，就停止。**

## 开场意图分类

最终统一成这些意图，但不是每类都交给 AI。

### A. 规则优先类

这些只要规则能稳定判断，就不走 AI：

1. `opening_greeting`
2. `opening_clarify`
3. `opening_profile_provided`
4. `opening_boundary_or_contact_refusal`
5. `opening_spam_or_promo`
6. 时间问候纠正
7. 明显 FAQ

典型例子：

- `你好呀，在吗呀呀呀？` -> `opening_greeting`
- `你好呀，在吗在吗呀呀呀？` -> `opening_greeting`
- `你好呀，坏呼叫` -> `opening_clarify`
- `男，深圳，90后` -> `opening_profile_provided`
- `不给电话行不行` -> `opening_boundary_or_contact_refusal`
- `怎么收费` -> `opening_faq`

### B. AI 识别类

这些是规则判不稳、容易混合、确实需要语义判断的场景：

1. `explicit_matchmaking_opening`
2. `low_pressure_opening`
3. `opening_light_consult`
4. `opening_mixed_intent`
5. `opening_emotional_or_defensive`
6. `opening_reverse_question`
7. `opening_proxy_inquiry`
8. `opening_eligibility_concern`
9. `opening_resource_request`
10. `opening_ambiguous_short`
11. `opening_test_or_playful`
12. `opening_hybrid_promo_real`

典型例子：

- `找对象`
- `先了解下呢`
- `我问问你情况呢`
- `就是想先问问情况呢`
- `找对象，怎么收费`
- `离异的能聊吗`

## 规则层负责什么

规则层不是简单词库匹配，而是：

**归一化 + 去语气词 + 去重复 + 组合识别**

例如：

- `你好呀，在吗在吗呀呀呀？`
  归一化后仍识别为 `opening_greeting`

- `你好呀，坏呼叫`
  识别为 `opening_clarify`

- `我问问你情况呢`
  如果规则层已能稳定判定，就直接落 `low_pressure_opening`
  如果判不稳，再交给当前 AI

一句话：

**规则层负责能用语言模式稳定归类的部分，而不是只认固定整句。**

## 当前 AI 调用如何承载识别

不开新请求。

只在开场窗口内、且规则层没能稳定归类时，才在当前 AI 调用里加结构化要求。

建议输出格式：

```json
{
  "opening_intent": "low_pressure_opening",
  "confidence": 0.92,
  "secondary_intent": null,
  "response": "可以呀，那我们先轻松聊聊。你方便的话，先简单介绍下自己就行。"
}
```

重点：

- 继续只有一次 AI 调用
- 让当前 AI 把它本来就在做的“理解”显式输出出来
- 不把所有开场都拖进重模型

## 映射到现有执行链路

- `opening_greeting` -> 现有 `opening_probe`
- `opening_clarify` -> 现有 `opening_clarify`
- `explicit_matchmaking_opening` -> 现有 `opening_self_intro`
- `low_pressure_opening` -> 现有 `opening_self_intro`，并强制 `ask_field=None`
- `opening_light_consult` -> 现有 `opening_probe` 或 `opening_self_intro`
- `opening_faq` -> 现有 FAQ 优先逻辑
- `opening_profile_provided` -> 现有字段提取 + 主线推进
- `opening_boundary_or_contact_refusal` -> 现有 `boundary pause / soft hold / contact refusal`
- `opening_spam_or_promo` -> 现有拦截/低响应/结束逻辑

其他模糊类：

- 按最接近的现有链路映射
- 不新造大流程

## 行为约束

### 对 `explicit_matchmaking_opening`

- 允许进入主线
- 但首轮不机械问 `sex`
- 优先给开放自述入口

### 对 `low_pressure_opening`

- 禁止直接问 `sex/age/location/education/occupation/contact`
- 优先邀请用户介绍自己

### 对 `opening_faq`

- 先答问题
- 不同时追问资料

### 对 `opening_profile_provided`

- 先接住资料
- 不重复问已给字段

### 对 `opening_boundary_or_contact_refusal`

- 先接住边界
- 禁止顶着推进电话/微信/资料

## 新增工程保障项

### 1. 结构化输出失败恢复策略

如果当前 AI 没按约定输出结构化结果，比如：

- JSON 不完整
- 字段缺失
- 混入自然语言导致解析失败
- 根本没有 `opening_intent`

系统必须这样处理：

- 丢弃结构化部分
- 回复正文照常使用
- 开场意图判断回退到规则层 / 兜底逻辑
- 记录日志：`opening_intent_parse_failed`

一句话：

**结构化输出可以失败，但整轮回复不能因为它失败。**

### 2. 回复与意图冲突的一致性校验

如果结构化意图和回复动作冲突，必须以后者为异常，触发修正。

例如：

- `opening_greeting` 不能直接问 `男生还是女生`
- `low_pressure_opening` 不能直接切字段
- `opening_faq` 不能直接转资料采集
- `opening_boundary_or_contact_refusal` 不能继续推电话/微信/资料

如果冲突：

- 优先以后处理修正文案
- 或降级替换为安全回复

一句话：

**结构化标签必须真正约束最终回复，不是只做记录。**

### 3. mixed intent 优先级表

对于混合开场，必须定义固定优先级，不允许临场漂移。

建议优先级：

`opening_spam_or_promo`
>
`opening_boundary_or_contact_refusal`
>
`opening_clarify`
>
`opening_faq`
>
`opening_profile_provided`
>
`explicit_matchmaking_opening`
>
`low_pressure_opening`
>
`opening_light_consult`
>
`opening_greeting`

典型例子：

- `找对象，怎么收费`
  - 主意图：`opening_faq`
  - 次意图：`explicit_matchmaking_opening`

- `不给电话行不行，我是男的`
  - 主意图：`opening_boundary_or_contact_refusal`
  - 次意图：`opening_profile_provided`

- `先了解下，我在深圳`
  - 主意图：`opening_profile_provided`
  - 次意图：`low_pressure_opening`

## fallback 补强要求

只要当前 AI 超时或失败，就必须由 no-AI fallback 兜住下面这些高频开场，不能掉回 `sex`：

- `你好呀，在吗呀呀呀？`
- `你好呀，在吗在吗呀呀呀？`
- `你好呀，坏呼叫`
- `我问问你情况呢`
- `就是想先问问情况呢`
- `我先看看`

目标：

- greeting 仍然回 `opening_probe`
- noisy greeting 仍然回 `opening_clarify`
- 低压了解仍然回 `opening_self_intro`
- 不再出现 fallback 直接追问 `男生还是女生`

## 超时阈值

默认 AI 超时阈值从原来的 `20s/25s` 提高到：

- `CHAT_AI_TIMEOUT_SECONDS = 45`
- `CHAT_AI_HARD_TIMEOUT_SECONDS = 50`

这样做不是为了让所有开场都更依赖 AI，而是为了在确实进入当前 AI 调用时，减少主模型波动导致的误降级。

## 旧功能如何处理

旧样例继续保留：

- `找对象`
- `想找对象`
- `先了解下`
- `先看看`
- `先聊聊`
- `想先了解一下`

它们以后只做：

- 测试样例
- 规则兜底
- AI 提示参考示例

## 不改的部分

本次明确不改：

- 主模型生成回复逻辑
- 主 prompt 主体
- 整体对话策略
- 字段优先级
- 资料收集主线
- 联系方式状态机
- 开场之外的任何场景

## 测试方案

必须覆盖：

- greeting 稳定性
- greeting + 异常尾巴
- 时间冲突
- 明确找对象
- 低压了解
- FAQ 开场
- 资料开场
- 边界/联系方式拒绝

---

## 相关文档

统一单轮理解的现行架构规范与执行约束，统一维护在：

- [09_TURN_PRIORITY_POLICY_DESIGN.md](/Users/eric/Desktop/doubao_mcp_server/docs/09_TURN_PRIORITY_POLICY_DESIGN.md)
- [10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md](/Users/eric/Desktop/doubao_mcp_server/docs/10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md)

## 最终结论

最终正确方案不是：

- 所有开场都走 AI
- 也不是继续只靠词库

而是：

**规则已经能稳定识别的开场，不走 AI；只有规则判不稳的开场，才利用当前这次 AI 调用顺带完成意图识别。**

再加上：

- fallback 补强
- 结构化失败恢复
- 回复与意图冲突校验
- mixed intent 优先级

一句话总结：

**让规则兜住大多数稳定开场，让当前 AI 只处理真正模糊的开场，让失败时系统也不会掉回“男生还是女生”。**
