# 11 AI话术统一生成设计

## 目标

新增一个独立模块，模块名定义为：

- `ai话术统一生成`

该模块的核心原则只有一句：

**AI 生成什么，就向用户展示什么。**

在这一原则下：

- 保留现有核心字段 / 中等字段 / 联系方式 / 收尾的业务决策逻辑
- 保留现有字段提取、profile 刷新、turn decision 刷新、状态更新、计数器更新
- 禁止生成后的规则层继续改写、截断、压缩、替换 AI 正文

本设计的目标不是先追求“最稳妥的话术控制”，而是先彻底解决两个现存问题：

1. AI 原本生成得像人，最终发给用户时话术被改掉
2. AI 原文经常在后处理阶段被截断一截

## 适用范围

本模块只管理：

- 普通业务回复的最终用户可见正文
- AI 正文生成后的最小安全清洗
- AI 正文生成后的校验与记录
- AI 正文不可用时的最小兜底策略

本模块不负责：

- 单轮语义识别
- 字段提取规则
- profile 写回规则
- turn decision 构建
- 联系方式状态机本身
- 核心字段 / 中等字段推进策略本身

也就是说：

- `10_UNIFIED_TURN_UNDERSTANDING_PIPELINE_DESIGN.md` 继续负责“用户这句话是什么意思”
- `11_AI_RESPONSE_UNIFIED_GENERATION_DESIGN.md` 负责“最终给用户看的正文怎么生成、怎么交付”

## 明确约束

本方案落地时，必须满足以下硬约束：

### 1. 不改变现有业务决策口径

不能改掉这些逻辑：

- 核心字段 / 中等字段优先级
- 联系方式推进逻辑
- 收尾逻辑
- repair / resume / bridge_back 的业务判断
- 字段提取逻辑
- collection progress 逻辑

### 2. 不改变现有字段提取和状态流转

即使最终正文完全由 AI 原样展示，后台仍必须继续执行：

- 字段提取
- profile 刷新
- turn decision 刷新
- 会话状态更新
- runtime counter 更新
- contact ask record 更新

### 3. 禁止规则层继续改正文

在 `ai话术统一生成` 模块启用后，生成后的用户可见正文必须遵守：

- 不允许规则层重写正文
- 不允许规则层替换正文
- 不允许规则层截断正文
- 不允许规则层基于“觉得这句话不理想”而改用本地 fallback

### 4. 允许最小安全清洗

唯一允许保留的是最小安全清洗，例如：

- 去除首尾空白
- 合并多余空白
- 去除明显非法调试块
- 去除极少量明确坏碎片

但不允许保留这种逻辑：

- 语义压缩
- 去模板腔改写
- 问句后半句裁切
- 为了“更像产品风格”而重写正文

## 当前问题全景

当前项目里的最终回复并不是“AI 生成后直接展示”，而是：

1. AI 生成初稿
2. 生成后第一轮 postprocess 改写
3. finalize 阶段大量 guard / followup / handoff 改写
4. 不可投递时直接丢弃 AI 原文，换成本地 fallback
5. 文本清洗阶段继续截断和压缩

当前最主要的问题点有：

### 1. postprocess 直接改正文

当前链路中，AI 生成后还会进入：

- `postprocess_generated_ai_response(...)`

这里仍然可能做：

- opening intent block 解析后改写
- style stabilize
- short answer ack transition
- profile bridge rewrite

这些都属于“生成后再改正文”。

### 2. finalize 大量规则继续改正文

当前 finalize 链中，大量：

- guard
- followup
- handoff
- contact policy
- terminal response policy

仍会对最终正文进行覆盖或局部重写。

### 3. non-delivery fallback 直接替换掉 AI 原文

当规则层认为 AI 正文“不适合投递”时，当前链路会直接走：

- `_build_no_ai_response(...)`

这会导致用户看到的内容和 AI 原文完全不是一回事。

### 4. cleanup 会截掉一段正文

当前 cleanup 链中仍然有这类逻辑：

- 压缩多动作回复
- 裁掉问句后的解释尾巴
- 去掉被判断为碎片的内容

这正是“AI 明明说得很好，最后像被截了一截”的直接来源。

## 新模块定义

新增独立模块目录建议：

- `src/modules/ai_response_unified_generation/`

模块的产品名称与设计名称统一为：

- `ai话术统一生成`

### 目录建议

- `src/modules/ai_response_unified_generation/domain/models.py`
- `src/modules/ai_response_unified_generation/domain/response_draft_service.py`
- `src/modules/ai_response_unified_generation/domain/response_validation_service.py`
- `src/modules/ai_response_unified_generation/domain/response_safe_cleanup_service.py`
- `src/modules/ai_response_unified_generation/domain/response_delivery_service.py`
- `src/modules/ai_response_unified_generation/domain/response_observability_service.py`

第一阶段不要求一次性把所有旧代码搬空，但要求：

- 这条模块成为普通业务回复的唯一新主链
- 旧链路只保留兼容与 fallback

## 模块职责拆分

### 1. `response_draft_service.py`

职责：

- 调用 `AIResponseGenerator`
- 基于已有的 `ResponsePlan` 生成 AI 初稿
- 返回 `raw_ai_response`

输入：

- `turn_understanding_result`
- `turn_decision`
- `response_plan`
- `profile_summary`
- `prompt_context`

输出：

```json
{
  "raw_ai_response": "......",
  "generation_source": "ai",
  "response_plan_id": "..."
}
```

### 2. `response_validation_service.py`

职责：

- 只校验，不改正文
- 判定当前 AI 初稿是否存在业务风险或投递风险
- 给出 `violations` 和 `delivery_status`

禁止：

- 直接改正文
- 直接重写正文
- 直接换成本地 fallback

输出示例：

```json
{
  "delivery_status": "deliverable",
  "violations": [],
  "warnings": ["missing_field_push"],
  "should_fallback": false
}
```

### 3. `response_safe_cleanup_service.py`

职责：

- 只做最小安全清洗

允许：

- trim
- 合并多余空白
- 去调试块
- 去极少量明确非法前缀/后缀

禁止：

- 裁掉问句解释尾巴
- 压缩多动作语义
- 改语气
- 改模板腔
- 改字段问法

### 4. `response_delivery_service.py`

职责：

- 固定最终用户可见正文
- 确保后续字段提取、状态刷新继续执行
- 但不允许这些后台步骤回写正文

输出示例：

```json
{
  "display_response": "最终展示给用户的正文",
  "raw_ai_response": "AI 初稿",
  "delivery_status": "delivered"
}
```

### 5. `response_observability_service.py`

职责：

- 完整记录每轮正文在各阶段的变化
- 明确标记“哪里改了正文”

第一阶段至少要记录：

- `raw_ai_response`
- `validated_response`
- `cleaned_response`
- `final_display_response`
- `delivery_status`
- `violations`
- `fallback_triggered`

## 第一阶段执行原则

第一阶段不引入“AI 重写一次”的复杂链，只做最直接的版本：

### 1. AI 草稿就是最终正文候选

流程：

1. 生成 `raw_ai_response`
2. 做 validation
3. 做最小 safe cleanup
4. 直接展示

### 2. validation 只记录，不改写

即使 validation 认为：

- 少了一点字段推进
- 风格不够理想
- 联系方式承接不够强

第一阶段也只允许：

- 记录日志
- 标记 warning

不允许：

- 改正文
- 截正文
- 替换正文

### 3. fallback 极度收缩

第一阶段为了贯彻“AI 生成啥就显示啥”，普通业务场景下：

- 不允许因为 `delivery_viable=false` 就直接丢弃 AI 原文

只有这些场景允许 fallback：

- AI 完全空回复
- AI 回复是明确异常文本
- AI 回复命中安全风险硬拦截
- AI 调用失败

除此之外，一律先展示 AI 原文。

## 旧链路中需要被旁路或停用的部分

以下逻辑不是要永久删除，而是第一阶段必须从“用户可见正文链路”里旁路掉。

### A. 停掉生成后正文改写

以下能力必须改成：

- 只做检测
- 不改正文

包括但不限于：

- opening intent block 改写
- style stabilize
- short answer ack transition
- profile bridge rewrite

### B. 停掉 finalize 对正文的继续改写

以下逻辑继续保留运行，但不能再写 `final_response`：

- guard
- followup
- contact policy
- ending policy
- field ask enforcement
- handoff/transition

这些逻辑可以继续：

- 记录 violation
- 更新状态
- 更新计数器
- 刷新 decision

但不允许再改正文。

### C. 停掉 non-delivery fallback 覆盖正文

以下行为必须停用：

- 因为“模型回复不理想”而直接改用 `_build_no_ai_response(...)`

第一阶段只允许：

- AI 回复为空
- AI 回复异常
- 安全风险

这三类触发 fallback。

### D. 停掉 aggressive cleanup

以下类型逻辑必须从正文链路移除：

- 压多动作
- 裁尾巴
- 去模板腔重写
- 去掉“多余解释”

## 后台逻辑保留清单

以下逻辑虽然继续执行，但不得再回写正文：

- 字段提取
- profile 刷新
- turn decision 刷新
- active ask 更新
- collection progress 更新
- contact flow 更新
- repair / resume 状态更新
- bridge_back 状态更新
- runtime progress counters 更新

可以把这条原则写成硬规范：

**后台状态更新允许继续跑，但一旦 `display_response` 冻结，就不允许任何后台逻辑再改用户可见正文。**

## 统一数据结构

建议新增：

### `AIGenerationDraft`

```json
{
  "raw_ai_response": "......",
  "response_plan": {},
  "generation_source": "ai"
}
```

### `AIResponseValidationResult`

```json
{
  "delivery_status": "deliverable|warning|fallback_required",
  "violations": [],
  "warnings": [],
  "fallback_reason": null
}
```

### `AIDisplayResponse`

```json
{
  "display_response": "最终展示给用户的正文",
  "raw_ai_response": "AI 原文",
  "safe_cleaned": true,
  "fallback_used": false
}
```

## 新主链

新的普通业务回复主链固定为：

1. `UnifiedTurnUnderstandingService`
2. `ConversationStatePlanner`
3. `ResponsePlanBuilder`
4. `ai话术统一生成.response_draft_service`
5. `ai话术统一生成.response_validation_service`
6. `ai话术统一生成.response_safe_cleanup_service`
7. `ai话术统一生成.response_delivery_service`
8. 后台继续执行字段提取与状态刷新

用户看到的永远是：

- 第 6 步之后的 `display_response`

而不是后台后续步骤重新写出来的文本。

## 和现有系统的衔接方式

第一阶段不要推翻现有生成链，而是旁路式接入。

### 方案

在现有表达主链里加一个显式模式，例如：

- `AI_RAW_RESPONSE_MODE = true`

当该模式开启时：

- 生成后直接进入 `ai话术统一生成` 模块
- 旧 finalize / postprocess / cleanup 中会改正文的逻辑全部旁路
- 后台提取与状态更新仍继续

### 这样做的好处

- 不用一次性删旧链
- 可快速验证“AI 原样展示”效果
- 有问题可以快速回切

## 模块落地顺序

### 第一步：新增文档和模块骨架

新增：

- `11_AI_RESPONSE_UNIFIED_GENERATION_DESIGN.md`
- `src/modules/ai_response_unified_generation/`

### 第二步：冻结正文

在 AI 生成后，立刻保存：

- `raw_ai_response`
- `display_response = raw_ai_response`

后续任何逻辑都不得直接覆盖 `display_response`

### 第三步：抽离 validation

把当前 finalize 中对正文的判断改成：

- 只产 `validation_result`
- 不再直接写正文

### 第四步：抽离最小 safe cleanup

把 cleanup 收缩到：

- 去空白
- 去非法块
- 去明显坏碎片

### 第五步：保留后台状态推进

继续执行：

- 提取
- 刷新
- 更新

但不回写正文。

## 日志与可观测要求

第一阶段必须新增完整观测日志。

每轮至少记录：

- `raw_ai_response`
- `display_response`
- `validation_result`
- `safe_cleanup_applied`
- `fallback_used`
- `fallback_reason`
- `extracted_fields`
- `decision_after_collection`

如果最终显示文本不等于 AI 原文，必须在日志里明确写出原因。

目标是做到：

**没有任何“悄悄改掉 AI 原文”的路径。**

## 验收标准

### 1. 正文一致性

普通业务场景下：

- `display_response` 必须与 `raw_ai_response` 一致

允许差异的唯一情况：

- 仅发生最小安全清洗

### 2. 禁止截断

不能再出现：

- AI 原文后半句被裁掉
- 问句后解释被截断
- 多动作回复被压成半句

### 3. 不影响业务收集

以下必须保持可用：

- 核心字段收集
- 中等字段收集
- 联系方式收集
- 字段提取
- profile 更新
- turn decision 刷新
- collection progress 记录

### 4. fallback 极度收缩

普通业务场景里，不能因为“文案不理想”而 fallback。

只有：

- AI 空回复
- AI 调用失败
- 安全风险

才允许 fallback。

## 未来第二阶段

第一阶段先做到：

- AI 生成啥，就基本显示啥

第二阶段再考虑：

- validation 失败后，不是直接 fallback
- 而是先给 AI 一次 rewrite 机会

第二阶段主链可升级成：

1. AI draft
2. validate
3. AI rewrite once if needed
4. safe cleanup
5. display

但这不是本次文档的第一落地点。

## 执行指令

后续 AI 或研发在按本设计执行时，必须遵守以下执行顺序：

1. 先新增 `ai话术统一生成` 独立模块
2. 先旁路“改正文”的旧链，不先删除“状态更新”的旧链
3. 先确保 `display_response` 冻结
4. 先把 postprocess / finalize / cleanup 的正文改写停掉
5. 再保留字段提取、profile 刷新、turn decision 刷新、状态更新
6. 最后补 observability 和回归测试

禁止反过来做：

- 先删字段提取
- 先删状态更新
- 先把旧链全删光再重建

## 一句话定版

本设计不是要去掉业务收集和状态流转，而是要把：

- **生成后的正文干预链**

从主路径中拿掉，改成：

- **AI 生成正文**
- **正文冻结**
- **后台继续提取和刷新**
- **最终原样展示 AI 正文**

这就是 `ai话术统一生成` 模块的唯一核心职责。
