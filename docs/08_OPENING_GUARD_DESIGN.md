# 08 开场保护层设计

## 约束前提

本次优化**严格只做开场保护层，不新增独立 AI 请求，不改整体对话策略**。

也就是说：

- 不重构现有决策系统
- 不额外发起一条新的开场分类 AI 请求
- 不改字段收集优先级
- 不改联系方式推进策略
- 不改开场之外的主流程
- 只在开场窗口内，让当前 AI 调用显式输出开场意图

## 核心原则

**利用当前 AI 调用完成开场意图识别，不新增独立 AI 请求；识别结果接入现有生成链路，但不改整体对话策略。**

同时：

**时间问候纠正、乱码、明显资料输入、明显边界/广告等确定性强的场景，继续由硬规则优先处理。**

## 优化目标

把“开场”从现在的：

- 关键词命中
- 主模型边理解边生成
- 个别 case 靠补规则

升级成：

**在现有 AI 调用里显式完成开场意图判断，然后按现有链路执行。**

## 总体结构

```text
用户输入
-> 开场硬规则判断
-> 若未命中硬规则，再进入当前 AI 调用内的开场意图识别
-> 输出开场意图
-> 映射到现有 TurnDecision / 现有执行链路
-> 继续走现有生成逻辑
```

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

**开场识别只负责完成“开场分流”，一旦分流完成，就停止。**

## 开场意图分类

最终统一成 18 类。

### 第一组：核心主分类

1. `opening_greeting`
2. `opening_light_consult`
3. `explicit_matchmaking_opening`
4. `low_pressure_opening`
5. `opening_faq`
6. `opening_spam_or_promo`
7. `opening_clarify`
8. `opening_profile_provided`
9. `opening_boundary_or_contact_refusal`

### 第二组：补充细分类

10. `opening_mixed_intent`
11. `opening_emotional_or_defensive`
12. `opening_reverse_question`
13. `opening_proxy_inquiry`
14. `opening_eligibility_concern`
15. `opening_resource_request`
16. `opening_ambiguous_short`
17. `opening_test_or_playful`
18. `opening_hybrid_promo_real`

## 规则层负责什么

硬规则继续优先处理：

- 时间问候纠正
- 纯 greeting
- 明显乱码 / 异常输入
- 明显资料输入
- 明显边界 / 联系方式拒绝
- 明显广告 / 垃圾流量

一句话：

**确定性高的问题继续让规则先判，AI 不抢这部分。**

## 当前 AI 调用如何承载识别

在开场窗口内，不新增 AI 请求，而是在当前 AI 调用里增加结构化输出要求。

建议输出格式：

```json
{
  "opening_intent": "low_pressure_opening",
  "confidence": 0.92,
  "secondary_intent": null,
  "response": "可以呀，那我们先轻松聊聊。你方便的话，先简单介绍下自己就行。"
}
```

重点是：

- 不额外多开一次请求
- 让当前 AI 把它本来就在做的“理解”显式输出出来

## 映射到现有执行链路

- `opening_greeting` -> 现有 `opening_probe`
- `opening_light_consult` -> 现有 `opening_probe`
- `explicit_matchmaking_opening` -> 现有 `opening_self_intro`
- `low_pressure_opening` -> 现有 `opening_self_intro`，并强制 `ask_field=None`
- `opening_faq` -> 现有 FAQ 优先逻辑
- `opening_spam_or_promo` -> 现有拦截/低响应/结束逻辑
- `opening_clarify` -> 现有 `opening_clarify`
- `opening_profile_provided` -> 现有字段提取 + 主线推进
- `opening_boundary_or_contact_refusal` -> 现有 `boundary pause / soft hold / contact refusal`

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
- 混入大量自然语言导致解析失败
- 根本没有 `opening_intent`

系统必须这样处理：

- 丢弃结构化部分
- 回复正文照常使用
- 开场意图判断回退到硬规则 / 规则兜底
- 记录日志：`opening_intent_parse_failed`

### 2. 回复与意图冲突的一致性校验

如果结构化结果和回复动作冲突，必须以后者为异常，触发修正。

例如：

- `opening_intent = low_pressure_opening`
- 但回复正文里出现 `你是男生还是女生`

则必须：

- 优先以后处理修正文案
- 或降级替换为安全回复

一句话：

**结构化标签必须真正约束最终回复。**

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

## 最终结论

最终正确方案不是：

- 继续补词库
- 也不是额外再发一次 AI 分类请求

而是：

**利用当前 AI 调用，在开场窗口内显式输出开场意图；硬规则继续优先处理确定性问题；识别结果接入现有生成链路，但不改整体对话策略。**

- `pure_greeting_opening`
- `opening_clarify`
- `explicit_matchmaking_opening`

这一组逻辑之后、通用 `general` 决策之前。

原因：

- 结构最顺
- 改动最小
- 不影响现有主逻辑

### 6. 后处理防呆

为了防止后处理再次把回复洗成字段追问，建议增加一条保护：

如果当前轮：

- `intent == opening_self_intro`
  或
- `followup_topic == opening_self_intro`

则后处理禁止补成：

- `你是男生还是女生`
- `你多大`
- `你在哪个城市`
- `什么学历`
- `做什么工作`

这是为了防止保护逻辑被后续流程覆盖。

## 明确不动的部分

本次优化明确不动：

- 主生成逻辑
- 主 prompt 主体
- 整体对话策略
- 资料收集主链路
- 字段优先级
- 联系方式推进逻辑
- FAQ 主逻辑
- 投诉/修复主逻辑
- 边界暂停主逻辑
- 全项目其他场景

## 测试方案

必须补测试。

建议新增开场保护测试，覆盖：

### 正例

这些必须命中保护：

- `你好 -> 先了解下呢`
- `你好 -> 先看看`
- `你好 -> 先聊聊吧`
- `你好 -> 想先了解一下`
- `你好 -> 先认识一下再说`

断言：

- 不得问 `男生还是女生`
- 不得问 `多大`
- 不得问 `哪个城市`
- 不得问联系方式
- 必须出现“介绍下自己 / 说说自己 / 先轻松聊聊”类表达

### 负例

这些不能误判：

- `你好 -> 我是男生`
- `你好 -> 深圳`
- `你好 -> 本科`
- `你好 -> 你们怎么安排`
- `你好 -> 先别问这个`

断言：

- 不应统一落到“邀请自我介绍”

## 预期收益

本次只优化开场，所以收益主要体现在开场体验。

### 开场场景内预期提升

- 拟人化：`+12% ~ +20%`
- 像真人程度：`+15% ~ +25%`
- 开场对话质量：`+20% ~ +35%`
- 开场误切字段率：`-70% ~ -90%`

### 全项目平均预期提升

因为只改开场，全项目平均提升相对有限：

- 拟人化：`+3% ~ +6%`
- 像真人程度：`+4% ~ +8%`
- 对话质量：`+5% ~ +10%`

说明：

这些是目标区间，不是实测最终值。
最终以开场回归集和人工评测结果为准。

## 最终总结

本次优化不是“加几个开场话术关键词”，也不是“重写对话系统”。

本质上是：

**在不动主生成逻辑、不改整体对话策略的前提下，为开场阶段增加一个低压了解意图保护层。**

这个保护层的作用是：

- 保留旧样例，但把它们从“唯一命中规则”调整为“测试样例 + 兜底样例 + 参考样例”
- 当用户表达“先了解一下”时，阻止系统直接追问资料
- 将动作纠偏为“先邀请用户简单介绍自己”
