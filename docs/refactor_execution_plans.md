# Refactor Execution Plans

> 创建时间：2026-03-18
> 目标读者：负责执行重构的模型或工程师
> 适用范围：当前仓库的聊天主链路、资料收集、联系方式收集、消息队列、平台接入
> 目标：在不破坏现有业务效果和拟人化表现的前提下，逐步把项目整理成更清晰的模块边界

---

## 一、先读这个文档的人要知道什么

本仓库当前不是“重写”阶段，而是“安全重构”阶段。

执行任何方案前都必须遵守：

1. 默认保持现有 API 不变
2. 默认保持现有业务判断顺序不变
3. 默认不重写 prompt 文案
4. 默认不改变联系方式业务规则语义
5. 默认不改变消息队列主逻辑语义
6. 先做结构抽离，再做策略优化

如果某一步需要突破这些边界，必须在该步骤的交付说明里明确写出。

---

## 二、三档方案总览

本文件定义三套可执行方案：

1. 可落地版
适合 1 天内启动并交付第一版，目标是先把最危险的耦合拆掉。

2. 推荐版
适合按模块化单体重组，目标是让项目进入长期可维护状态。

3. 最佳版
适合在推荐版稳定后继续演进，目标是得到更强的可测试性、可解释性和跨入口一致性。

这三套方案不是互斥关系，而是递进关系：

- 可落地版 = Phase A
- 推荐版 = Phase A + Phase B
- 最佳版 = Phase A + Phase B + Phase C

---

## 三、当前项目的目标边界

### 3.1 当前应拆分的核心业务域

建议按以下业务域理解项目：

1. `conversation`
- 单轮聊天编排
- 用户问题承接
- 欢迎语、结束语、fallback

2. `profile_collection`
- 字段提取
- 字段校验
- 追问次数
- 字段优先级策略
- 字段跳过与冷却

3. `contact_collection`
- 电话/微信收集
- 拒绝与挽留
- 联系方式结束态

4. `message_queue`
- ingest
- debounce
- 单用户串行处理
- stale turn
- outbox
- worker

5. `user_data`
- 用户档案
- 对话历史
- 用户状态
- 存储抽象

6. `platform_xiaohongshu`
- 入站 payload 适配
- 外部发送适配
- 平台鉴权和签名

### 3.2 当前明确不应该先做的事

1. 不要先拆微服务
2. 不要一开始就大规模改目录和 import
3. 不要顺手优化对话策略
4. 不要一边重构一边改 prompt
5. 不要为了重构去重写 `ChatService` 业务语义

---

## 四、当前仓库实际状态

> 状态判断时间：2026-03-18
> 说明：本节用于描述“当前仓库大致已经做到哪里”，不是方案定义本身。
> 如果后续代码继续变化，本节需要同步更新。

### 4.1 当前结论

当前仓库更接近：

- 业务功能层面：消息队列链路已经基本完成
- 架构层面：推荐版尚未开始
- 重构阶段层面：可落地版已经完成第一轮落地

更明确地说：

1. 你已经完成了不少“功能拆分”
例如：
- `services/queue/*`
- `workers/*`
- `services/conversation/*`
- `services/collection/*`

2. 但你之前还没有完成“结构收口”
例如：
- `ChatService` 仍然是聊天主链路里的重编排点
- 规则直返逻辑仍大量停留在 `ChatService`
- 资料收集链路仍没有统一 coordinator
- 还没有显式的 `ProcessChatTurnUseCase`

所以当前最准确的判断是：

**业务功能已经比早期单体清晰很多；截至 2026-03-18，本仓库已完成可落地版 A1-A4 的第一轮实现，但尚未进入推荐版目录重组。**

### 4.2 当前可视为“已存在”的成果

以下内容可以视为当前仓库已经具备：

1. 消息队列子系统已经基本独立
- `src/services/queue/`
- `src/workers/`
- ingest 路由
- outbox sender

2. conversation / collection / contact 相关能力已经有初步拆分
- `src/services/conversation/`
- `src/services/collection/`
- `src/services/refusal_service.py`
- `src/services/field_skip_service.py`

3. FastAPI 路由层已经按功能分开
- chat
- conversation
- user
- system
- health
- xiaohongshu ingest

### 4.3 当前尚未完成的关键重构点

以下内容应视为“已完成第一轮实现”：

1. `A1` 已完成
已新增 `src/models/chat_flow.py`，提供结构化结果模型。

2. `A2` 已完成
已新增 `src/services/conversation/conversation_rule_service.py`，承接早返回规则。

3. `A3` 已完成
已新增 `src/services/collection/profile_collection_coordinator.py`，统一收口资料收集链路。

4. `A4` 已完成
已新增 `src/services/application/process_chat_turn.py`，且 `ChatService.process_chat_request()` 已转为兼容入口，代理到 use case。

以下内容仍应视为“未完成”：

1. 推荐版尚未开始
没有进行模块目录重组，也没有统一 `application / domain / infrastructure`。

2. 最佳版尚未开始
规则链、显式联系方式状态表达、统一 command/result 及跨入口协议已经落地。

### 4.4 当前对应到三档方案的判断

建议按下面方式理解当前状态：

- 可落地版：`已完成`
- 推荐版：`已完成`
- 最佳版：`已完成`

### 4.5 当前建议的实际起点

如果现在继续按本文件执行，建议从：

**已完成三档全部方案**

下一步不应继续做结构性大改，优先做全量回归、稳定性验证和残余兼容层清理。

### 4.6 当前状态建议写法

其他模型接手时，建议把当前状态写成：

```text
Current Phase:
- C4 complete

Runtime Owner:
- ChatService.process_chat_request is still the live chat entry
- live orchestration already delegates to ProcessChatTurnUseCase
- queue is already live through MessageOrchestrator and workers

Completed:
- A1-A4 first-pass refactor completed
- B1 module skeleton completed
- B2 conversation runtime dependencies now load through module paths
- B3 profile collection runtime dependencies now load through module paths
- B4 contact collection runtime dependencies now load through module paths
- B5 message queue runtime dependencies now load through module paths
- B6 Xiaohongshu platform integration paths now load through module paths
- C1 command/result introduced for core chat turn and message ingest paths
- C2 conversation early-return logic refactored into an ordered rule chain
- C3 contact collection state is now surfaced explicitly via ContactFlowState / ContactFlowSnapshot
- C3 keeps ContactCollectionService as the single business source of truth
- C4 sync chat route now constructs ProcessChatTurnCommand and consumes ProcessChatTurnResult
- C4 queue turn execution now prefers ProcessChatTurnCommand / ProcessChatTurnResult
- C4 Xiaohongshu ingest route now constructs IngestMessageCommand and consumes IngestMessageResult
- functional split exists for queue / conversation / collection / routes

Pending:
- full regression validation
- optional cleanup of compatibility wrappers when safe

Do Not Touch:
- prompt semantics
- contact collection business rules
- queue behavior semantics
```

Recent Validation:
- 2026-03-18: focused regression passed
- result: 93 passed, 1 skipped
- covered areas: chat route protocol path, contact collection, message orchestrator, queue worker, reply sender, message queue integration pipeline
- skipped: local HTTP Xiaohongshu delivery e2e may be skipped when environment does not permit local bind

Next Recommended Work:
- prefer compatibility-wrapper cleanup only after broader end-to-end validation
- do not continue structural refactor by default
- prioritize bug fixes, behavior diffs, and test coverage gaps instead

---

## 五、执行前统一检查清单

任何方案开始前，先完成以下检查：

1. 阅读以下文件：
- `src/services/core/chat_service.py`
- `src/services/core/dialogue_manager.py`
- `src/services/collection/contact_collection_service.py`
- `src/services/collection/profile_collection_policy.py`
- `src/services/queue/message_orchestrator.py`
- `src/api/routes/chat.py`
- `src/api/routes/xiaohongshu_ingest.py`

2. 识别以下入口是否仍依赖 `ChatService.process_chat_request()`：
- `/api/doubao/chat`
- `/api/v1/chat`
- message queue worker

3. 确认现有测试中哪些覆盖以下路径：
- 普通聊天
- 资料收集
- 联系方式收集
- 拒绝/结束对话
- 异步队列链路

4. 在进入修改前记录：
- 计划改动文件清单
- 不改动文件清单
- 风险点清单

如果这 4 项没有完成，不要进入重构实施。

---

## 六、方案一：可落地版

### 5.1 适用目标

适用于：

1. 需要在短时间内先把结构风险降下来
2. 需要尽量不动现有逻辑
3. 需要给后续更大规模重构打基础

### 5.2 方案目标

只做四件事：

1. 抽出聊天主流程 use case
2. 抽出规则直返逻辑
3. 收口资料收集链路
4. 给联系方式模块加结构化输出

### 5.3 建议新增文件

- `src/services/application/process_chat_turn.py`
- `src/services/conversation/conversation_rule_service.py`
- `src/services/collection/profile_collection_coordinator.py`
- `src/models/chat_flow.py`

### 5.4 本方案允许的改动范围

可以改：

- `src/services/core/chat_service.py`
- 新增上述 4 个文件
- 必要的单元测试
- 必要的文档

尽量不改：

- `src/services/queue/*`
- `src/workers/*`
- `src/api/routes/*`
- prompt 文案文件

### 5.5 分阶段实施

#### Phase A1：建结果对象

目标：
- 给主流程提供稳定的结构化返回模型

实施内容：

在 `src/models/chat_flow.py` 中新增：

- `RuleCheckResult`
- `ProfileCollectionResult`
- `ContactDecision`

完成标准：

1. 新模型文件存在
2. 类型字段足够覆盖主流程需要
3. 没有改现有 API 协议

如果执行到这里停止，交付状态应写：

```text
可落地版执行到 A1

Done:
- added chat_flow models

Not Done:
- no business logic moved yet

Risk:
- none, only model scaffold
```

#### Phase A2：抽离规则直返逻辑

目标：
- 把 `ChatService` 中所有“命中后直接返回”的规则收口

建议迁出的逻辑：

1. 对话已结束后的告别逻辑
2. 已收集完成且只回复确认词的空响应
3. 确认词但未留联系方式时的快速响应
4. 匹配时长问题快速通道
5. 分居状态快速结束
6. 无意义输入 fallback
7. 不可理解输入固定回复

实施方式：

1. 新增 `ConversationRuleService`
2. 提供统一入口，例如：

```python
class ConversationRuleService:
    async def try_handle(self, request, user_profile, context) -> RuleCheckResult:
        ...
```

3. `ChatService` 先调用该服务
4. 如果 `handled=True`，直接返回

完成标准：

1. `ChatService` 中至少一半以上的规则直返分支已迁出
2. 规则顺序与旧逻辑保持一致
3. 原有测试不回退
4. 新增规则单测

如果执行到这里停止，交付状态应写：

```text
可落地版执行到 A2

Done:
- conversation rule service extracted
- direct-return branches moved out of ChatService

Not Done:
- main orchestration still partially in ChatService
- profile collection chain not yet consolidated

Risk:
- ordering regressions possible if more rules are moved later
```

#### Phase A3：收口资料收集链路

目标：
- 让聊天主流程不再分散调用多个资料收集服务

建议协调的现有服务：

- `ExtractionService`
- `ValidationService`
- `AskTrackingService`
- `ProfileCollectionPolicy`
- `FieldSkipService`

实施方式：

1. 新增 `ProfileCollectionCoordinator`
2. 提供统一入口，例如：

```python
class ProfileCollectionCoordinator:
    async def process(self, request, user_profile, context) -> ProfileCollectionResult:
        ...
```

3. 内部继续复用现有服务，不重写规则
4. `ChatService` 改为只拿协调结果

完成标准：

1. `ChatService` 不再手工串联以上 5 个服务
2. 提取、校验、策略决策仍保持原有顺序
3. 不改字段优先级语义
4. 单测通过

如果执行到这里停止，交付状态应写：

```text
可落地版执行到 A3

Done:
- profile collection chain consolidated

Not Done:
- main orchestration entry still not fully isolated

Risk:
- if hidden side effects existed in old inline sequence, verify behavior carefully
```

#### Phase A4：抽出聊天主流程用例

目标：
- 让聊天主入口从“大类主函数”变成“明确用例”

实施方式：

1. 新增 `ProcessChatTurnUseCase`
2. 将 `ChatService.process_chat_request()` 的主体流程迁入
3. `ChatService` 只保留兼容入口和依赖初始化

建议接口：

```python
class ProcessChatTurnUseCase:
    async def execute(self, request) -> dict:
        ...
```

完成标准：

1. `ChatService.process_chat_request()` 主要成为代理入口
2. route 和 queue 无需修改调用方式
3. 聊天主链路测试不回退
4. 逻辑行为等价

如果执行到这里停止，交付状态应写：

```text
可落地版执行到 A4

Done:
- main chat orchestration isolated in use case
- ChatService reduced to compatibility facade

Not Done:
- directories still reflect old layout
- platform and queue boundaries not yet reorganized

Risk:
- import paths and dependency wiring may still be transitional
```

### 5.6 可落地版完成标准

全部完成后，应满足：

1. 新增 `ProcessChatTurnUseCase`
2. 新增 `ConversationRuleService`
3. 新增 `ProfileCollectionCoordinator`
4. 新增结构化 flow models
5. `ChatService` 明显瘦身
6. `/api/doubao/chat` 行为不变
7. queue 调用聊天入口的方式不变
8. 现有拟人化效果原则上不因本次重构而变化

### 5.7 可落地版不应做的事

1. 不要迁移大目录
2. 不要引入新的层级体系到全仓库
3. 不要重写联系方式状态机
4. 不要调整资料收集策略
5. 不要为了“更优雅”而改 prompt

---

## 七、方案二：推荐版

### 6.1 适用目标

适用于：

1. 可落地版已完成并稳定
2. 需要长期维护和多人协作
3. 需要把仓库整理成模块化单体

### 6.2 方案目标

把项目重组为：

- 模块化单体
- 用例层清晰
- `domain / application / infrastructure` 职责明确

### 6.3 推荐目录目标形态

```text
src/
  modules/
    conversation/
      application/
      domain/
      infrastructure/
      interfaces/
    profile_collection/
      application/
      domain/
      infrastructure/
    contact_collection/
      application/
      domain/
      infrastructure/
    message_queue/
      application/
      domain/
      infrastructure/
      workers/
      interfaces/
    user_data/
      application/
      domain/
      infrastructure/
    platform_xiaohongshu/
      interfaces/
      infrastructure/
  shared/
    config/
    errors/
    logging/
    utils/
```

### 6.4 推荐版允许的改动范围

可以改：

- 目录结构
- import 路径
- 应用层与基础设施接线方式
- route 和 worker 的依赖注入方式

尽量不改：

- 业务规则语义
- prompt 内容
- 联系方式决策含义

### 6.5 分阶段实施

#### Phase B1：建立模块目录骨架

目标：
- 建立新目录，但先不做大规模搬迁

实施内容：

1. 新建 `src/modules/`
2. 建立各业务域的 `application/domain/infrastructure/interfaces`
3. 先将新增 use case 和 coordinator 迁入新目录

完成标准：

1. 模块目录存在
2. 新增代码优先落到新模块目录
3. 旧代码仍可正常引用

如果执行到这里停止，交付状态应写：

```text
推荐版执行到 B1

Done:
- module skeleton added
- new orchestration code placed under module layout

Not Done:
- legacy files still dominate runtime path

Risk:
- mixed old/new imports temporarily coexist
```

#### Phase B2：模块内聚合 conversation

目标：
- 把聊天主编排相关代码聚拢到 `conversation`

建议归拢：

- `ProcessChatTurnUseCase`
- `ConversationRuleService`
- `DialogueManager`
- `GreetingService`
- `ConversationEndingService`
- `ExpectationService`
- `InputFallbackService`
- `UserQuestionService`

实施方式：

1. 先迁入新目录
2. 保留薄兼容层或稳定 import 导出
3. 跑聊天主链路测试

完成标准：

1. `conversation` 成为聊天业务主入口模块
2. `ChatService` 不再保存大量业务分支
3. 旧入口仍兼容

#### Phase B3：模块内聚合 profile_collection

目标：
- 让资料收集成为独立业务域

建议归拢：

- `ProfileCollectionCoordinator`
- `ExtractionService`
- `ValidationService`
- `AskTrackingService`
- `ProfileCollectionPolicy`
- `FieldSkipService`

完成标准：

1. 资料收集相关代码集中到同一模块
2. 聊天主流程只拿结果对象
3. 资料收集规则具备独立测试入口

#### Phase B4：模块内聚合 contact_collection

目标：
- 让联系方式收集成为独立业务域

建议归拢：

- `ContactCollectionService`
- `RefusalService`
- 联系方式结果对象

注意：
- 本阶段不重写状态机，只做模块聚合

完成标准：

1. 联系方式逻辑不再散落在 conversation 中
2. 主流程通过统一决策对象调用联系方式模块
3. 联系方式测试仍通过

#### Phase B5：模块内聚合 message_queue

目标：
- 让队列成为独立子系统

建议归拢：

- `message_orchestrator.py`
- `queue_store.py`
- `intent_classifier.py`
- `reply_delivery_service.py`
- `message_queue_worker.py`
- `reply_sender_worker.py`
- ingest route

完成标准：

1. queue 目录职责清晰
2. queue 只依赖稳定聊天入口
3. 不理解 profile/contact 细节

#### Phase B6：平台接入分离

目标：
- 平台协议适配从核心业务中拆出

建议新增：

- `XiaohongshuIngressAdapter`
- `XiaohongshuReplyClient`

完成标准：

1. 小红书字段适配在平台模块内
2. 核心业务尽量只处理内部对象
3. 后续增加新平台不会直接污染核心模块

### 6.6 推荐版完成标准

全部完成后，应满足：

1. 项目按业务域分模块
2. `application / domain / infrastructure` 角色清晰
3. route 和 worker 调用 use case，而不是直接揉业务逻辑
4. queue、conversation、profile_collection、contact_collection 边界清晰
5. 平台接入层从核心业务层中解耦

### 6.7 推荐版停止点交付格式

任意阶段停止时，必须按以下格式交付：

```text
推荐版执行到 Bx

Changed:
- files / directories moved
- interfaces introduced

Runtime Path:
- which old entry points still exist
- which new module is already active

Pending:
- next module not yet migrated

Compatibility:
- note whether old imports remain valid

Risk:
- list concrete transitional risks
```

---

## 八、方案三：最佳版

### 7.1 适用目标

适用于：

1. 推荐版已经完成并稳定运行
2. 需要更强的可测试性和可解释性
3. 需要更稳定地支持多个入口、多平台、多 worker

### 7.2 方案目标

在推荐版基础上继续升级为：

1. 规则链
2. 显式状态机
3. 统一 command/result

### 7.3 最佳版允许的改动范围

可以改：

- 内部规则组织方式
- 业务内部对象模型
- 联系方式状态表达方式
- 各入口之间的 command/result 统一

需要谨慎：

- 行为顺序可能更容易被改动
- 必须用测试锁住语义

### 7.4 分阶段实施

#### Phase C1：统一 command/result

目标：
- 各用例不再直接大量传 `dict`

建议引入：

- `ProcessChatTurnCommand`
- `ProcessChatTurnResult`
- `IngestPlatformMessageCommand`
- `RunQueuedTurnCommand`
- `DeliverReplyCommand`

完成标准：

1. 主要 use case 有明确输入输出对象
2. route / worker / adapter 都依赖 command/result
3. `dict` 在核心路径中的使用显著减少

如果执行到这里停止，交付状态应写：

```text
最佳版执行到 C1

Done:
- commands and results introduced

Not Done:
- rules and states still partly implicit

Risk:
- adapters may still convert between old dicts and new objects
```

#### Phase C2：把规则直返升级为规则链

目标：
- 让特殊分支变成显式、可插拔、可排序的规则

建议形态：

```python
class ConversationRule:
    async def apply(...) -> RuleCheckResult:
        ...
```

建议规则：

- `ConversationEndedRule`
- `AffirmativeSilentRule`
- `UncollectedContactConfirmRule`
- `MatchingTimelineRule`
- `SeparationStatusRule`
- `NonsenseInputRule`
- `UnclearInputRule`

实施方式：

1. 先保留旧 `ConversationRuleService`
2. 内部改成顺序执行多个 rule handler
3. 严格保持原先顺序

完成标准：

1. 规则顺序显式
2. 每个规则可独立测试
3. 新增规则不再需要改大段主流程

#### Phase C3：联系方式模块显式状态机化

目标：
- 让联系方式流程从“隐式 if/else”升级为显式状态流转

注意：
- 本仓库现有 `ContactCollectionService` 是业务真源
- 本阶段不是“另起炉灶再造一套”
- 必须在保留当前业务真源的前提下，把状态和转移显式化

建议状态：

- `NO_CONTACT`
- `PHONE_REQUESTED`
- `PHONE_REFUSED_ONCE`
- `PHONE_FINAL_REFUSED`
- `WECHAT_REQUESTED`
- `WECHAT_REFUSED_ONCE`
- `WECHAT_FINAL_REFUSED`
- `CONTACT_CLOSED`
- `CONTACT_COLLECTED`

实施方式：

1. 先在 `ContactCollectionService` 内显式定义状态和转移
2. 不要在仓库别处新建第二套联系方式状态机
3. 保持 ask count 与拒绝语义不变

完成标准：

1. 联系方式状态流转可追踪
2. 行为更可解释
3. 现有联系方式测试继续通过
4. 状态表达仍以 `ContactCollectionService` 为单一业务真源

#### Phase C4：统一跨入口的编排协议

目标：
- 同步聊天入口、异步 queue 入口、平台入口都调用同一套核心协议

实施方式：

1. route 构造 command
2. worker 构造 command
3. adapter 只做协议转换
4. 核心用例统一执行

完成标准：

1. 多入口共享同一业务编排协议
2. 入口层基本不再承载业务判断
3. 平台扩展成本进一步下降

### 7.5 最佳版完成标准

全部完成后，应满足：

1. 主要 use case 都有 command/result
2. 规则系统显式可排序
3. 联系方式状态显式可测试
4. route / worker / adapter 共享统一业务入口
5. 新增业务规则和新平台的成本显著下降

### 7.6 最佳版停止点交付格式

任意阶段停止时，必须按以下格式交付：

```text
最佳版执行到 Cx

Done:
- new protocol / rule / state capabilities added

Semantic Guarantee:
- which old behavior is intentionally preserved

Not Done:
- what is still transitional

Risk:
- where regression is most likely

Test Status:
- unit / integration coverage state
```

---

## 九、三套方案的实施顺序建议

推荐顺序：

1. 先完成可落地版
2. 稳定后进入推荐版
3. 最后视收益决定是否进入最佳版

不推荐的顺序：

1. 跳过可落地版，直接做最佳版
2. 一边做推荐版一边改 prompt
3. 一边做最佳版一边修改联系方式业务规则

---

## 十、各阶段公共测试要求

每完成一个阶段，至少验证以下内容：

1. 聊天主链路仍可正常工作
2. 资料收集结果没有明显回退
3. 联系方式收集路径不回退
4. 拒绝和结束语路径不回退
5. queue 调用聊天入口不回退

建议最低测试集合：

- 聊天主链路单测
- 联系方式相关单测
- queue 单测
- 至少一条 queue 集成测试

如果测试不全，交付时必须明确写：

```text
Unverified:
- exact paths not tested
- risk remains in these branches
```

---

## 十一、如何给其他模型交接

任何模型或工程师在接手时，都应在交付中明确三件事：

1. 现在执行到哪一步
例如：
- `A2`
- `B4`
- `C1`

2. 当前运行时真正生效的是旧路径还是新路径
例如：
- `ChatService` 仍是运行时主入口，但内部已代理到 `ProcessChatTurnUseCase`
- queue 仍走旧 import，但逻辑已使用新用例

3. 下一步唯一应该做什么
例如：
- “下一步只做 A3，不做目录迁移”
- “下一步只迁移 conversation 模块，不碰 queue”

建议统一交接模板：

```text
Current Phase:
- A/B/C + step id

Runtime Owner:
- which class/function currently owns the live path

Completed:
- exact extracted modules / migrated files

Pending:
- next single step only

Do Not Touch:
- files or behaviors frozen for this step

Verification:
- tests run / tests not run
```

---

## 十二、推荐的实际决策

如果当前目标是“尽快安全推进”，建议执行：

1. 先做可落地版到 `A4`
2. 观察一轮稳定性
3. 再进入推荐版 `B1-B4`
4. queue 和平台接入最后迁

如果当前目标是“准备长期维护”，建议执行：

1. 完成可落地版
2. 直接进入推荐版
3. 最佳版只在推荐版稳定后再评估

如果当前目标是“多模型并行协作”，建议执行：

1. 先按本文件明确当前阶段
2. 每次只推进一个 phase
3. 不要同时修改同一业务域的核心文件

---

## 十三、最终提醒

最容易做错的点有 6 个：

1. 把结构重构变成策略重写
2. 抽模块时顺手改 prompt
3. 直接大搬目录导致回归面过大
4. 推荐版还没稳定就引入最佳版复杂度
5. 没写清楚当前执行到哪一步
6. 交接时没写清楚“运行时究竟走的是旧路径还是新路径”

这个文档的用途不是展示“理想架构”，而是让不同模型可以在任何阶段接手并继续推进，不需要重新猜上下文。
