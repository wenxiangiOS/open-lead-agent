# Project Cleanup Audit

## 本轮已清理

这轮优先清理了高置信度的“空壳转发层”，它们本身不承载业务逻辑，只是把一个导入路径转发到另一个实现：

- `src/services/application/process_chat_turn.py`
- `src/modules/conversation/domain/dialogue_manager.py`
- `src/modules/contact_collection/domain/contact_collection_service.py`
- `src/modules/contact_collection/domain/refusal_service.py`
- `src/services/collection/ask_tracking_service.py`
- `src/services/collection/profile_collection_coordinator.py`
- `src/services/collection/profile_collection_policy.py`
- `src/services/conversation/conversation_ending_service.py`
- `src/services/conversation/input_fallback_service.py`
- `src/services/conversation/user_question_service.py`
- `src/modules/message_queue/domain/message_models.py`
- `src/services/field_skip_service.py`

对应引用已经改到真实实现文件，避免后续迁移时同一职责需要维护两套路径。

另外，`ChatService` 内部也开始收缩了一批纯转发 helper facade，调用点已经切到真实 helper service：

- `ChatServiceAckRenderService`
- `ChatServiceSummaryHelperService`
- `ChatServiceBridgeTextService`
- `ChatServiceContactTextService`
- `ChatServiceContactValidationTextService`
- `ChatServiceResponseCleanupService`

这次删除的是 `ChatService` 上那些只做一层转发、不承载状态的同名包装方法。

之前保留的 cleanup 例外 `_is_delivery_viable()` 也已经收掉：

- legacy finalize path 现在改成依赖显式 `response_cleanup_service`
- 子服务测试也从 stub `host._is_delivery_viable` 改成 stub `service.response_cleanup_service`

另外还清掉了一组已经退化成“只被测试访问”的 lazy property：

- `response_cleanup_service`
- `contact_text_service`
- `contact_validation_text_service`
- `bridge_text_service`
- `ack_render_service`
- `summary_helper_service`

它们在 `ChatService` 里已经没有任何生产调用，继续保留只会增加类体积和测试噪音。

另外，`contact flow` 里一段只服务 legacy finalize 的守卫/降压策略，以及同轮联系方式切换/门控逻辑，也已经从 `ChatService` 主类下沉到 rollback-only 目录：

- `src/services/core/legacy_response_rewrite/contact_policy_service.py`
- `src/services/core/legacy_response_rewrite/contact_transition_service.py`
- `src/services/core/legacy_response_rewrite/contact_outcome_service.py`

这部分逻辑现在明确归属 legacy rewrite 链，而不是继续挂在 unified 主路径类上。`ChatService` 上对应的 rollback-only 私有入口也已经继续收缩，只保留主流程仍复用的 terminal/resume 出口。

另外，原先同时被主流程、`preparation_service` 和 rollback-only 链共用的联系方式上下文判断，也已经抽成独立共享 service：

- `src/services/core/chat_service_contact_context_service.py`

目前 `ChatService` 上的 `_has_active_contact_context()` 只是一个薄包装，后续如果继续做类体积收缩，可以再逐步把主类内部调用也切到新 service。

类似地，联系方式完成后的“收尾或回到主资料流”出口也已经抽成独立共享 service：

- `src/services/core/chat_service_contact_resume_service.py`

目前 `ChatService` 上的 `_get_contact_terminal_or_resume_response()` 和 `_build_post_contact_resume_response()` 也都已经降成薄包装，legacy outcome 和 resume guard 都直接依赖新 service。

另外，联系方式输入后的验证与后续分流编排，也已经从 `ChatService` 大方法中抽成独立 flow service：

- `src/services/core/chat_service_contact_validation_flow_service.py`

目前 `ChatService._handle_contact_validation()` 只保留兼容入口，真正的微信/电话验证后续编排已经下沉到该 flow service。

与之配套的联系方式错误恢复逻辑，也已经拆成独立 recovery service：

- `src/services/core/chat_service_validation_recovery_service.py`

目前 `ChatService._build_validation_feedback()`、`_generate_validation_retry_response()`、`_classify_contact_validation_detail()` 都已经降成薄包装，待确认逻辑、静默策略和 AI retry copy 生成统一收口到该 service。

类似地，字段提取后的“收尾检测 + 离异手续门控 + 拒绝字段补标记”也已经抽成独立 postprocess service：

- `src/services/core/chat_service_collection_postprocess_service.py`

目前 `ChatService._process_collection_result()` 只保留“提取 -> 刷新 profile -> 委托 postprocess”这一层编排，不再直接承载那一大段后置状态机逻辑。

另外，confirmation 类短答的 AI fallback 也已经抽成独立 service：

- `src/services/core/chat_service_confirmation_fallback_service.py`

目前 `ChatService._extract_pending_confirmation_targets()`、`_should_use_confirmation_ai_fallback()`、`_apply_confirmation_ai_fallback()` 都已经降成薄包装，避免这类轻量确认回填逻辑继续堆在主类里。

另外，`_process_collection_result()` 前半段的提取编排也已经拆成独立 service：

- `src/services/core/chat_service_collection_extraction_service.py`

目前 `ChatService._process_collection_result()` 已经进一步压缩成“两段委托”：先走 extraction service，再走 postprocess service，不再自己承载提取前 guard 和 profile 刷新细节。

另外，use-ai 收尾文案生成也已经抽成独立 service：

- `src/services/core/chat_service_ending_generation_service.py`

目前 `ChatService._generate_ai_ending_response()` 只保留兼容入口，真正的收尾 prompt 组装、fallback 处理和清洗都已经下沉到该 service。

另外，本地兜底回复和 preset payload 装配这两块也已经抽成独立 service：

- `src/services/core/chat_service_no_ai_response_service.py`
- `src/services/core/chat_service_preset_response_service.py`

目前 `ChatService._build_no_ai_response()` 和 `maybe_build_preset_response_payload()` 都只保留薄包装，不再把整段 no-AI 路由和 preset 状态更新逻辑继续堆在主类里。

另外，模型生成 prompt 编排也已经拆出独立 service：

- `src/services/core/chat_service_generation_prompt_service.py`

目前 `build_generation_prompt()` 和 `_build_response_plan_generation_instruction()` 都已经降成薄包装，主类不再自己承载 response plan + prompt assembly 这段生成前编排。

另外，文本清洗策略里最重的三块也已经抽成独立 service：

- `src/services/core/chat_service_text_cleanup_service.py`

目前 `_sanitize_robotic_tone()`、`_apply_refusal_respect_guard()`、`_prevent_no_repeat_hold_from_blocking_progress()` 都已经降成兼容入口，不再把整段文本清洗/联系拒绝守卫继续堆在主类里。

另外，turn 后置文本结构策略也已经抽成独立 service：

- `src/services/core/chat_service_turn_text_policy_service.py`

目前 `_apply_humanlike_turn_structure_policy()` 已经降成薄包装，主类不再继续承载“重复追问去重 + interleaving side target”这段后置文本策略编排。

另外，field followup prompt helper 这组也已经抽成独立 service：

- `src/services/core/chat_service_followup_prompt_service.py`

目前 `_build_local_field_fallback_prompt()`、`_build_policy_field_prompt()`、`_build_followup_seed_for_model_rewrite()` 都已经降成薄包装，主类不再继续承载这组三层 prompt helper。

## 当前确认的冗余模式

### 1. 迁移期桥接层

项目目前同时存在 `src/services/*` 和 `src/modules/*` 两套命名空间。大量冗余不是逻辑重复，而是迁移期兼容层重复：

- 一部分 wrapper 已经删除。
- 仍保留的 wrapper 主要是包级兼容导出，例如 `src/services/__init__.py` 和 `src/services/data/__init__.py`。

这些兼容导出还在测试覆盖面内，暂时不建议直接删除。

### 2. rollback-only legacy 链

`src/services/core/legacy_response_rewrite/` 是有意保留的回滚目录。这里看起来和 unified 主链存在重复职责，但它当前属于隔离后的 legacy 分支，不属于“误保留的死代码”。

现阶段建议：

- 不再往该目录新增主路径能力。
- 继续把主链依赖收缩到 unified 路径。
- 等确认无回滚需求后，再整目录下线。

### 3. 包级惰性导出仍然偏冗余

下面两处还属于兼容性冗余：

- `src/services/__init__.py`
- `src/services/data/__init__.py`

它们仍然有测试覆盖和历史导入面，短期应保留；但后续如果统一了外部导入路径，可以继续收缩。

其中已经完成的一步是：

- `src/services/__init__.py` 不再导出无人使用的 `FieldSkipService`

### 4. ChatService 内部 facade 仍然偏多

`ChatService` 里还有不少方法本质上只是把参数转给独立 helper service。这类代码不会带来行为价值，但会扩大主类体积、增加测试入口数量。

这轮已经先清掉了一批最简单的 facade，后续仍建议继续沿这个方向收缩。

## 本轮没有直接删除的区域

以下区域虽然带有兼容/历史包袱，但当前还不适合直接删：

- `src/services/__init__.py`
- `src/services/data/__init__.py`
- `src/services/core/legacy_response_rewrite/`

原因分别是：

- 仍有测试或历史导入依赖。
- 属于 rollback-only 路径，需要和 unified 主链分阶段下线。

## 建议的下一轮清理顺序

1. 盘点 `src/services/__init__.py` 和 `src/services/data/__init__.py` 的真实外部使用面。
2. 为 `legacy_response_rewrite/` 增加明确下线条件，再决定何时整目录移除。
3. 继续清理 `ChatService` 内部剩余的 facade/wrapper，优先删纯转发 helper。
4. 如果要进一步做“重复代码治理”，重点应转向 `ChatService` 超大类内部的职责切分，而不是继续做路径搬运。
