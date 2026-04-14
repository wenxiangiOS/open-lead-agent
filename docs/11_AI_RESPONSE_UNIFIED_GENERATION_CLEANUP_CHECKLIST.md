# 11 AI话术统一生成清退清单

## 目的

这份清单服务于 `docs/11_AI_RESPONSE_UNIFIED_GENERATION_DESIGN.md` 的后续收口阶段。

当前第一阶段已经实现：

- `AI_RAW_RESPONSE_MODE` 开启时，普通模型回复走 unified raw-response 主链
- 用户可见正文不再进入旧的 postprocess / finalize / delivery rewrite 链
- 后台字段提取、状态刷新、计数器更新继续保留
- fallback 已收缩到空回复 / 基础设施失败 / 硬异常文本，并使用最小兜底文案

这份文档只回答一件事：

**哪些旧正文干预路径还保留在代码里，但现在已经属于 rollback-only legacy path。**

## 当前统一主链

普通模型回复在 raw 模式下的用户可见正文链路现在是：

1. `ChatServiceGenerationService.generate_turn_response_text`
2. `ResponseDraftService`
3. `ResponseValidationService`
4. `ResponseSafeCleanupService`
5. `ResponseDeliveryService`
6. `ProcessChatTurnUseCase._sync_payload_response`

raw 模式下补充约束：

- `build_enhanced_response_to_clean()` 仍执行联系方式验证副作用，但不再回写用户可见正文
- `finalize` 在 `delivery` 后立刻冻结 `display_response`，后续只允许状态更新
- 观测字段包含 `display_frozen_at / post_freeze_write_attempt / raw_display_diff_reason`

对应代码：

- `src/services/core/chat_service_generation_service.py`
- `src/services/core/chat_service_finalize_service.py`
- `src/services/core/chat_service_delivery_service.py`
- `src/modules/ai_response_unified_generation/domain/`
- `src/modules/conversation/application/process_chat_turn.py`

## Legacy 路径总表

以下能力仍在仓库中保留，但在 `AI_RAW_RESPONSE_MODE` 下不应该再写用户可见正文。

### A. 生成后改写链

入口：

- `src/services/core/chat_service.py::postprocess_generated_ai_response`

内部 legacy 步骤：

- `_extract_opening_intent_block`
- `_stabilize_style_response`
- `_ensure_short_answer_ack_transition`
- `_enforce_profile_bridge_response`

现状：

- raw 模式下已在 `ChatServiceGenerationService` 旁路
- 已拆成 `opening intent detection` 和 `legacy rewrite` 两段显式入口：
  - `_detect_opening_intent_signal()`
  - `_rewrite_postprocessed_ai_response()`
- `ChatService` 已增加显式 legacy facade：
  - `apply_legacy_postprocess_generated_ai_response()`
- generation service 现已优先调用该 legacy facade
- 旧 `postprocess_generated_ai_response()` alias 已删除
- generation service 内对旧 postprocess 名字的 fallback 也已删除

后续动作：

- 第二阶段可把这些函数降级为“仅检测/仅服务非 raw 回滚路径”

### B. finalize 初始 guard 改写链

入口：

- `src/services/core/chat_service_finalize_service.py::_apply_initial_delivery_guards`

包含：

- `_enforce_opening_intent_consistency`
- `_apply_priority_question_guard`
- `_apply_context_ack_policy`
- `_enforce_terminal_response_policy`
- `_apply_contact_persuasion_style_policy`
- `_apply_contact_boundary_softening_policy`
- `_apply_refusal_respect_guard`
- `_apply_contact_action_guard`
- `_apply_contact_context_field_guard`
- `_enforce_contact_outcome_policy`
- `_apply_field_ask_guard`
- `_avoid_reasking_just_collected_field`
- `_avoid_reasking_already_collected_fields`

现状：

- raw 模式下已整体绕过
- 已拆成独立 legacy 入口：
  - `_finalize_via_legacy_rewrite_chain()`
  - `_apply_legacy_initial_delivery_guards()`
  - `_apply_legacy_non_delivery_fallback()`
  - `_finalize_legacy_delivery()`
- 原内部别名 `_apply_initial_delivery_guards()` / `_apply_non_delivery_fallback()` / `_finalize_delivery()`
  已删除，`finalize` 内部已完全切到显式 legacy 命名
- `ChatServiceFinalizeService` 内部依赖名也已显式 legacy 化，使用 `legacy_followup_service`
- legacy finalize 主路径已提取到独立 `LegacyChatServiceFinalizePathService`
- `ChatServiceFinalizeService` 现在主要负责 unified/raw 与 legacy path 的分流
- `LegacyChatServiceFinalizePathService` 已抽到
  `src/services/core/legacy_response_rewrite/finalize_path_service.py`
- `legacy_response_rewrite/` 目录已建立，可继续承接剩余 legacy rewrite service
- `LegacyChatServiceFollowupService` /
  `LegacyChatServiceFieldFollowupService` /
  `LegacyChatServiceContactFollowupService`
  也已归入 `legacy_response_rewrite/` 目录
- `LegacyChatServiceFieldTransitionService` /
  `LegacyChatServiceFieldGuardService` /
  `LegacyChatServiceContactHandoffService` /
  `LegacyChatServiceContactGuardService`
  也已归入 `legacy_response_rewrite/` 目录
- 目前 legacy rewrite 链从 finalize 到 followup 到底层 helper，已基本形成完整目录级隔离
- 当前建议把 `legacy_response_rewrite/` 整体视为 rollback-only 目录，不再承接新能力开发

后续动作：

- 按“只读检测”和“仍用于 quick path/非 raw path”重新分类

### C. non-delivery fallback 覆盖链

入口：

- `src/services/core/chat_service_finalize_service.py::_apply_non_delivery_fallback`

问题性质：

- 会直接放弃 AI 原文，改用 `_build_no_ai_response(...)`

现状：

- raw 模式下已停用

后续动作：

- 保留为 rollback-only path
- 如果继续收口，可把它限定为统一 validation 的 fallback executor，而不是旧 finalize 自己决定

### D. followup / handoff / transition 改写链

入口：

- `src/services/core/chat_service_followup_service.py::apply_followup_enrichment`
- `src/services/core/chat_service_field_followup_service.py::apply_field_followup`
- `src/services/core/chat_service_contact_followup_service.py::apply_contact_and_handoff_followup`
- `src/services/core/chat_service_field_transition_service.py::apply_field_transitions`
- `src/services/core/chat_service_field_guard_service.py::apply_field_guards`
- `src/services/core/chat_service_contact_handoff_service.py::apply_contact_handoffs`
- `src/services/core/chat_service_contact_guard_service.py::apply_contact_guards`

问题性质：

- 会继续拼接、替换或推进用户可见正文

现状：

- raw 模式下已不进入这条链
- 已增加显式 legacy 入口：
  - `apply_legacy_followup_enrichment()`
  - `apply_legacy_field_followup()`
  - `apply_legacy_contact_and_handoff_followup()`
  - `apply_legacy_field_transitions()`
  - `apply_legacy_field_guards()`
  - `apply_legacy_contact_handoffs()`
  - `apply_legacy_contact_guards()`
- `followup` 主编排内部已直接调用显式 `legacy_*` 子入口
- 旧名字 `apply_followup_enrichment()` / `apply_field_followup()` /
  `apply_contact_and_handoff_followup()` / `apply_field_transitions()` /
  `apply_field_guards()` / `apply_contact_handoffs()` / `apply_contact_guards()`
  已删除
- 相关 service 类名也开始显式 legacy 化：
  `LegacyChatServiceFollowupService` /
  `LegacyChatServiceFieldFollowupService` /
  `LegacyChatServiceContactFollowupService` /
  `LegacyChatServiceFieldTransitionService` /
  `LegacyChatServiceFieldGuardService` /
  `LegacyChatServiceContactHandoffService` /
  `LegacyChatServiceContactGuardService`

后续动作：

- 第二阶段可把这些服务明确改名为 `legacy_*`，避免误接回主路径

### E. aggressive cleanup 链

入口：

- `src/services/core/chat_service.py::_clean_response`

内部包含：

- `_strip_broken_edge_fragments`
- `_normalize_redundant_confirmation_phrasing`
- `_soften_awkward_age_question`
- `_compress_multi_action_response`

问题性质：

- 不只是 safe cleanup，还会改语义和压缩正文

现状：

- raw 模式下已不用于普通模型回复主链
- `ChatServiceFinalizeService` legacy 链已优先调用 `_legacy_clean_response()`
- `_clean_response()` alias 已删除，只保留 `_legacy_clean_response()`
- `finalize` 内对旧 `_clean_response()` 名字的 fallback 也已删除
- style retry / rewrite prompt 这类只做文本比较和上下文拼接的内部 helper，已开始改用 `_safe_clean_response()`
- 短答承接 `_ensure_short_answer_ack_transition()` 这类检测/拼接逻辑，也已改用 `_safe_clean_response()`
- `ChatService` 内部真正需要 legacy 输出清洗的剩余调用点，已显式切到 `_legacy_clean_response()`
- 当前 `ChatService` 内已无业务逻辑通过旧 `_clean_response()` 名字访问 legacy cleanup
- 单测主基线也已迁到显式 `legacy_*` 入口

后续动作：

- 普通模型回复主链继续只保留 `ResponseSafeCleanupService`
- `_clean_response` 仅用于 preset/legacy path，或拆分成更小的显式工具

## 仍允许保留的后台链路

以下能力仍应继续保留，不属于清退对象：

- 字段提取
- profile 刷新
- turn decision 刷新
- active ask 更新
- contact ask record 更新
- runtime counters 更新
- conversation state 更新
- observability 记录

原则：

**可以继续跑后台更新，但不得再回写 `display_response`。**

## 已有保护点

当前仓库里已经有这些保护：

- `ChatService._should_bypass_legacy_response_rewrite_chain()`
- raw 模式下 generation 不进入 `postprocess_generated_ai_response`
- `postprocess_generated_ai_response()` 已拆成 detection 和 legacy rewrite 两段
- raw 模式下 finalize 不进入 `_apply_initial_delivery_guards / _apply_non_delivery_fallback / apply_followup_enrichment`
- `finalize_generated_response()` 已拆成 unified path 和 `_finalize_via_legacy_rewrite_chain()`
- legacy finalize 内部 guard / fallback / delivery 已切到显式 `legacy_*` hook
- `finalize` 内部三个旧别名 `_apply_initial_delivery_guards()` / `_apply_non_delivery_fallback()` / `_finalize_delivery()` 已删除
- followup / field / contact / transition / guard / handoff 旧别名已删除，只保留显式 `legacy_*` 入口
- generation / finalize 主调用点对旧别名的 stub fallback 也已删除
- raw 模式下 delivery 不再让联系方式校验和 terminal policy 覆盖正文
- `ProcessChatTurnUseCase._sync_payload_response()` 最终强制对齐 payload

## 建议的下一步删除顺序

### Phase 2A

- 给 legacy rewrite 服务统一加前缀或注释
- 把 raw 模式相关测试集中到一个测试文件或测试段

### Phase 2B

- 把 `_clean_response` 中的 aggressive rewrite 和真正的 safe cleanup 彻底拆开
- 把 `postprocess_generated_ai_response` 拆成“检测”和“重写”两个概念

当前进度：

- 已拆出 `ChatService._safe_clean_response()`
- `ChatService._clean_response()` 当前仍保留为 legacy alias，方便旧路径逐步迁移

### Phase 2C

- 从 `ChatServiceFinalizeService` 删除 raw 模式下已不可能走到的 legacy 分支依赖
- 将 old rewrite services 改为仅 rollback path 可达

当前进度：

- `finalize` 已完成 unified / legacy 两条显式路径拆分
- `finalize` 内部 guard / fallback / delivery 已切到显式 `legacy_*` hook
- `followup` 已完成 legacy 显式入口补齐
- `finalize.followup_service` 已改为惰性初始化
- `followup.field/contact` 子链已改为惰性初始化
- `field followup` 内部的 `transition/guard` 依赖已改为惰性初始化
- `contact followup` 内部的 `handoff/guard` 依赖已改为惰性初始化
- `ChatService` 内多组 helper / ending / resume 依赖已改为惰性初始化
- 下一步可继续清理 legacy path 内部的死依赖和不可达分支

### Phase 2D

- 视回滚需求决定是否彻底移除旧正文干预链

## 回归检查清单

每次继续删 legacy path 前，至少回归：

```bash
pytest -q tests/unit/test_chat_service_regressions.py -k "generate_turn_response_text_skips_postprocess_in_ai_raw_mode or finalize_generated_response_preserves_ai_text_in_raw_mode or finalize_generated_response_falls_back_only_when_ai_text_is_empty or build_final_turn_payload_keeps_frozen_response_and_exposes_unified_meta_in_raw_mode or build_enhanced_response_to_clean_keeps_ai_response_in_raw_mode or sync_post_delivery_state_skips_terminal_policy_in_raw_mode"
pytest -q tests/unit/test_chat_service_finalize_subservices.py
pytest -q tests/unit/test_process_chat_turn_use_case.py
```

## 一句话结论

第一阶段已经把普通模型回复主链切到了 unified raw-response path。

接下来不是“再证明它能工作”，而是：

**按这份清单逐步删除 legacy 正文干预链。**
