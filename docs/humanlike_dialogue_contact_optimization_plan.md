# 拟人化与对话逻辑最终优化方案

> 更新时间：2026-03-25
> 目标：让项目逻辑严格符合 `06_CONTACT_COLLECTION.md` 与 `ai_dialog_policy.md`，并在此基础上显著提升真人感

---

## 1. 真源文档与总目标

本项目后续所有相关优化，统一以这两份文档为真源：

1. [06_CONTACT_COLLECTION.md](/Users/eric/Desktop/doubao_mcp_server/docs/06_CONTACT_COLLECTION.md)
   - 约束联系方式状态机
   - 约束询问次数、拒绝检测、切换与结束条件

2. [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md)
   - 约束资料收集优先级
   - 约束 FAQ 优先、用户疑问优先、每轮 `1主 + 1顺带`
   - 约束拟人化标准：先听懂、先承接、再推进

最终目标只有两条：

1. 逻辑先完全正确
   - 严格符合上述两份文档
   - 不允许 AI 自由发挥改流程

2. 表达再尽量像真人
   - 回复自然
   - 不像客服、脚本、登记系统、流程广播
   - 但不能以破坏规则为代价

---

## 2. 当前问题总览

结合最新真实对话日志与现有实现，当前问题已经不只是“文案不自然”，而是 5 类问题叠加。

### 2.1 逻辑真源不纯

- 联系方式逻辑没有完全收敛到 [06_CONTACT_COLLECTION.md](/Users/eric/Desktop/doubao_mcp_server/docs/06_CONTACT_COLLECTION.md)
- 资料主线优先级没有完全收敛到 [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md)
- 当前流程被多个层同时改写：
  - [contact_collection_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/collection/contact_collection_service.py)
  - [chat_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py)
  - [dialogue_manager.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/dialogue_manager.py)
  - [process_chat_turn.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/application/process_chat_turn.py)
  - [profile_collection_policy.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py)

### 2.2 一致性层有缺口

- 用户可见回复、`last_response`、history 中记录的回复，不保证完全一致
- 有真实日志表明：
  - 用户看到半句
  - 内部 `last_response` 却是整句
- AI 超时或回复异常时，内部状态仍可能推进

### 2.3 状态语义被污染

- `phone_ask_count / wechat_ask_count` 语义和文档中的“询问次数”不完全一致
- 某些路径里更接近“拒绝后才递增”或“流程推进计数”
- `AskTrackingService` 可能在坏回复、空回复、截断回复下仍然记录“已问字段”

### 2.4 主线优先级不稳

- 用户问问题时，系统不总是先答再回主线
- 用户催继续问资料时，系统仍可能切到联系方式
- FAQ 轮与主线轮的边界不够硬
- 离异确认完成后，不总是自然接回下一问

### 2.5 拟人化表达仍被系统性破坏

- `_sanitize_robotic_tone()` 通过字符串替换制造病句
- 仍有登记腔、流程腔、业务腔
- 有些轮次只回一句空泛确认，不像真人在接话
- 低信息回复、吐槽、催问、口语短答的承接仍不稳

---

## 3. 两份真源文档的落地解释

### 3.1 `06_CONTACT_COLLECTION.md` 的约束边界

这份文档约束的是“联系方式状态机”。

必须严格服从的内容：

- `phone_ask_count / wechat_ask_count` 是询问次数
- 电话 / 微信上限规则
- 显式拒绝与通用拒绝 + 上下文的判断方式
- 非香港 / 香港的上限差异
- 双拒绝才结束
- 用户明确说“电话不方便，留微信可以吗”时，允许切微信，但不等于最终拒绝电话

不允许表达层自行更改的内容：

- 下一步到底是 `ASK_PHONE` 还是 `ASK_WECHAT`
- 是否进入 `PERSUADE_PHONE / PERSUADE_WECHAT`
- 是否到达 `END_CONVERSATION`

### 3.2 `ai_dialog_policy.md` 的约束边界

这份文档约束的是“资料主线调度”和“拟人化策略”。

必须严格服从的内容：

- 用户疑问 > 字段收集
- FAQ 轮先解释，不顺手切主线
- 每轮 `1主 + 1顺带`
- 低优字段永不主动问
- 资料达到阈值后才能进入联系方式
- 首轮要先承接，不要直接抛字段
- 拟人化的核心是：听懂并顺着接上

不允许被联系方式逻辑反向破坏的内容：

- 用户明显还想继续聊资料时，不应突然切手机号
- 用户刚问过 FAQ，不应立刻顺势留资
- 用户刚完成离异手续确认，不应直接转销售式收口

---

## 4. 必须新增的三层架构

要彻底收口，必须强制拆成 3 层。

### 4.1 逻辑层

职责：

- 决定本轮动作
- 决定当前主目标
- 决定是否允许进入联系方式

特点：

- 不写文案
- 不做字符串润色
- 只输出结构化动作

### 4.2 表达层

职责：

- 在动作已确定的前提下，把话说得像真人

特点：

- 允许自然变体
- 允许承接
- 允许轻反馈
- 但不能改动作、改计数、改状态

### 4.3 展示层

职责：

- 把最终回复原样给用户
- 把同一份回复写入 history / last_response

特点：

- 不得再做截断
- 不得再另存一份不同版本
- 不得在展示后与内部记忆不一致

---

## 5. 最关键的新增硬约束

这是前几轮方案里最容易漏掉，但必须加上的部分。

### 5.1 用户可见回复一致性

必须保证每轮这三者完全一致：

- 用户实际看到的回复
- 写入 history 的回复
- 下一轮使用的 `last_response`

任何一个不一致，都视为严重 bug。

### 5.2 有效询问才算询问

只有当用户真正看到了该轮询问时，才允许：

- 增加 `phone_ask_count / wechat_ask_count`
- 记录该联系方式已询问过
- 记录资料字段已问过
- 把该轮当作下一轮上下文依据

如果发生以下任一情况，则不能算“有效询问”：

- AI 超时
- 用户可见回复为空
- 展示层截断成坏句 / 半句
- 最终输出与 history 不一致

### 5.3 AskTracking 只能跟踪成功交付的提问

[ask_tracking_service.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/ask_tracking_service.py)
现在会基于 AI 文本识别“问了哪个字段”，但缺少“这句是否成功交付给用户”的保护。

必须新增规则：

- 只有 `final_response` 成功展示给用户，才允许 track asked field
- 如果本轮回复为空、截断、超时 fallback 失败，则不记 ask tracking

### 5.4 当前动作优先于 `last_response`

联系方式拒绝识别不能主要依赖 `last_response`。

必须改成：

1. 先看当前动作
   - 当前动作是 `ASK_PHONE / PERSUADE_PHONE`
   - 当前动作是 `ASK_WECHAT / PERSUADE_WECHAT`

2. 再看用户当前回复
   - 显式拒绝
   - 通用拒绝

3. `last_response` 只兜底，不再做主真源

---

## 6. 联系方式状态机最终方案

### 6.1 状态机真源文件

[contact_collection_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/collection/contact_collection_service.py)

此文件是联系方式状态机唯一真源。

### 6.2 非香港用户标准流程

严格按 [06_CONTACT_COLLECTION.md](/Users/eric/Desktop/doubao_mcp_server/docs/06_CONTACT_COLLECTION.md)：

- 默认先电话
- 电话拒绝后，再微信
- 电话已收集后，再微信
- 双拒绝才结束

### 6.3 香港用户标准流程

- 电话最多 2 次
- 微信最多 2 次

### 6.4 唯一允许保留的扩展

当用户明确说：

- `电话不方便，留微信可以吗`
- `别打电话，加微信吧`

允许：

- 当轮切入微信流程

但不允许：

- 直接把电话永久标记成最终拒绝

### 6.5 必须从主状态机里降级的逻辑

以下逻辑不能继续主导 `get_next_action()`：

- 低信息确认自动切渠道
- 低信息确认自动暂停
- 主要依赖上一轮回复猜拒绝方向

这些逻辑最多可以保留为：

- 表达层保护
- 次级容错

不能再覆盖主文档规则。

### 6.6 询问次数语义修正

文档里定义的是“询问次数”，不是“拒绝次数”。

最终实现必须改成：

- 成功向用户展示一次电话询问 -> `phone_ask_count += 1`
- 成功向用户展示一次微信询问 -> `wechat_ask_count += 1`

拒绝状态单独记录在：

- `rejected_phone`
- `rejected_wechat`

禁止继续使用“用户拒绝时才加 ask_count”的变体语义。

---

## 7. 对话主线最终方案

### 7.1 优先级矩阵

必须写成硬规则，而不是只留在 prompt 里。

优先级从高到低：

1. 合规 / 高风险 / 结束条件
2. 用户显式问题
3. 离异手续确认
4. 用户催继续问资料
5. 正常主线字段
6. 联系方式

这意味着：

- `你不问其他了？` -> 继续资料，不切联系方式
- FAQ -> 先答疑，不顺手切主线或联系方式
- 离异确认未完成 -> 只确认手续

### 7.2 恢复资料主线意图

新增单独意图：

- `resume_profile_collection`

典型触发语：

- `你倒是问啊`
- `你不问其他了？`
- `继续问`
- `还有别的吗`

触发后必须：

- 继续主线字段
- 本轮禁止切联系方式

### 7.3 FAQ 边界

按 [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md)：

- FAQ 轮先解释
- FAQ 轮不要顺手切回资料收集
- FAQ 轮不要顺手切联系方式

### 7.4 联系方式进入条件

不能只看资料数够不够。

必须同时满足：

- 达到 [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md) 的资料阈值
- 当前轮不是 FAQ
- 当前轮不是用户催继续资料
- 当前轮不是刚完成离异确认
- 当前轮不是边界 / 顾虑表达
- 当前轮不是刚发生回复失败或输出异常

否则继续资料主线。

---

## 8. 离异确认链路最终方案

### 8.1 进入条件

用户出现：

- `离异`
- `离异过`
- `离婚了`

则：

- 只确认手续
- 不再继续收其他字段
- 不进入联系方式

### 8.2 已办妥识别

必须稳定支持更自然的表达：

- `办理好了`
- `办完了`
- `都弄好了`
- `手续办好了`
- `恢复单身`
- `离干净了`

同时必须排除：

- `还在办`
- `没办完`
- `没离干净`
- `手续还没办好`

### 8.3 确认完成后直接接主线

这是现在仍然容易漏掉的点。

一旦确认完成：

- 不能只回一句 `好，那我知道了`
- 必须直接自然接下一个主线字段

例如：

- `好，那就行。你现在主要在哪个城市生活？`
- `那就没问题了。你这边是什么学历？`
- `好，那就行。你现在做什么工作？`

### 8.4 已确认后不得重回 pending

一旦：

- `divorce_confirmed=True`
- 或 `marital_status=离异（手续已办妥）`

后续普通消息不能重新进入手续确认。

---

## 9. 拟人化表达最终方案

### 9.1 拟人化的定义

统一按 [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md)：

- 先听懂
- 先接住
- 再推进

不是：

- 多加语气词
- 更可爱
- 更像销售红娘

### 9.2 必须去掉的口吻

禁止继续出现：

- 登记腔
  - `我先按男生记哈`
  - `我记下了`
  - `我先按...`
- 流程广播腔
  - `确认清楚了，我们再往下说`
  - `其他基本信息我都了解得差不多啦`
- 业务推进腔
  - `后续要是有合适的匹配能更顺畅联系到你`
  - `我们平时不会乱发消息打扰的`

### 9.3 后处理层重构

[chat_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py)
中的 `_sanitize_robotic_tone()` 不能继续作为主纠偏器。

最终方案：

- 只保留极少数黑名单整句兜底
- 禁止片段级 `replace()` 改句法
- 主表达控制前移到生成前

因为当前做法已经产生真实病句：

- `好的，我知道了来你是男生啦`
- `好的，我知道了来你是本科学历啦`

### 9.4 重复感控制

要新增“重复感”约束：

- 同类确认句不能连续多轮高度相似
- 联系方式追问不能连续复读同模板
- 离异确认句要有少量自然变体

但变体只作用于表达，不作用于动作。

---

## 10. 稳定性与输出链路最终方案

### 10.1 单一 `final_response`

[process_chat_turn.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/application/process_chat_turn.py)
必须统一只使用一份 `final_response`。

后续链路都只消费这一份：

- 返回给用户
- 写入 history
- 写入 `last_response`
- 供下一轮上下文使用

### 10.2 AI 超时兜底

AI 超时后，不能让用户看到空白。

必须按当前动作给本地兜底：

- 资料主线 -> 本地自然追问
- 离异确认 -> 本地手续确认句
- 联系方式 -> 本地自然联系方式句
- FAQ -> 本地 FAQ 简答

### 10.3 输出失败时状态冻结

如果本轮发生以下任一情况：

- AI 超时且 fallback 失败
- `final_response` 为空
- 展示层输出失败
- 最终输出被截断

则：

- 不得推进依赖该轮回复成立的状态
- 不得把该轮算进有效询问
- 不得让 ask tracking 继续累加

---

## 11. 文件级实施顺序

### 第一阶段：一致性层

先改：

- [process_chat_turn.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/application/process_chat_turn.py)
- [chat_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py)

目标：

- 统一 `final_response`
- 修空回复
- 修半句截断
- 修 `last_response` 与用户可见回复不一致
- 失败时冻结状态推进

### 第二阶段：联系方式状态机

再改：

- [contact_collection_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/collection/contact_collection_service.py)
- [user_profile.py](/Users/eric/Desktop/doubao_mcp_server/src/models/user_profile.py)

目标：

- `get_next_action()` 回归 [06_CONTACT_COLLECTION.md](/Users/eric/Desktop/doubao_mcp_server/docs/06_CONTACT_COLLECTION.md)
- 修 ask_count 语义
- 修拒绝检测为“当前动作优先”

### 第三阶段：资料主线与离异确认

再改：

- [chat_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py)
- [profile_collection_policy.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py)
- [dialogue_manager.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/dialogue_manager.py)

目标：

- 用户疑问优先
- 催继续问资料优先
- 离异确认完整闭环
- 确认完成后直接接回主线

### 第四阶段：表达层收口

最后改：

- [prompts.py](/Users/eric/Desktop/doubao_mcp_server/src/services/prompts/prompts.py)
- [chat_service.py](/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py)
- [user_question_service.py](/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/user_question_service.py)

目标：

- 去登记腔
- 去流程广播腔
- 去业务推进腔
- 保留真人感

---

## 12. 测试与验收红线

### 12.1 单元测试必须新增

- 用户可见回复 == history == `last_response`
- 空回复时不推进状态
- ask tracking 只在成功展示后记录
- 电话场景下 `不方便呢` -> 稳定记电话拒绝
- 微信场景下 `不方便呢` -> 稳定记微信拒绝
- `办理好了` 后直接接主线
- `你不问其他了？` 后继续主线，不切联系方式
- `_sanitize_robotic_tone()` 不得产病句

### 12.2 真实 AI 回归必须新增

新增两套场景：

- `humanlike_dialogue_regression`
- `contact_collection_regression`

必须覆盖：

- 短答链路
- FAQ 插入
- 离异插入
- 办妥确认
- 催继续问资料
- 电话拒绝
- 微信拒绝
- 双拒绝
- AI 超时
- 展示截断一致性

### 12.3 验收红线

以下任一出现，都算未达标：

- 用户看到半句
- 用户看到空白回复
- `last_response` 与用户看到的不一致
- ask_count 与实际有效询问次数不一致
- FAQ 轮顺手切联系方式
- 用户催继续问资料时切联系方式
- 离异确认完成后只回空泛确认
- 病句
- 客服公告腔

---

## 13. 最终结论

这次优化不能再继续按“修一句话、补一条 prompt”推进。

最终最优方案是：

1. 先把 [06_CONTACT_COLLECTION.md](/Users/eric/Desktop/doubao_mcp_server/docs/06_CONTACT_COLLECTION.md) 固化为联系方式逻辑唯一真源
2. 再把 [ai_dialog_policy.md](/Users/eric/Desktop/doubao_mcp_server/docs/ai_dialog_policy.md) 固化为资料主线与拟人化优先级真源
3. 再补上一致性层：
   - 用户看到什么
   - 系统记住什么
   - 状态机以什么为依据
   必须完全一致
4. 最后再做人味表达

一句话概括：

先让系统逻辑只按文档走，再让表达像真人，而不是让 AI 靠随机发挥去“同时兼顾规则和自然”。
