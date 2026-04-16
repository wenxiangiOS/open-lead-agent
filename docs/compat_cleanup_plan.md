# Compatibility Cleanup Plan

## 1. Purpose

This document is a cleanup plan for compatibility wrappers introduced during the modular refactor.

Goal:
- identify which files are still runtime-critical
- identify which files are only re-export shells
- define a safe migration order
- prevent other models from deleting wrappers too early

This is not a feature plan.
This is a source-of-truth migration plan.

## 2. Current State

The project has already completed:
- landed refactor plan
- recommended modularization plan
- best-plan protocol and rule/state upgrades

However, the codebase is still in a mixed state:
- some runtime imports already point to `src/modules/...`
- many `src/modules/...` files are only thin wrappers over old `src/services/...`
- some old `src/services/...` files are still the real business source of truth
- some old files are now only compatibility shims
- `conversation_understanding` is a special mixed runtime path:
  - `UnifiedTurnUnderstandingService` is already the official entrypoint
  - but it still depends on `TurnUnderstandingService` helper capabilities and compat projections

Because of that:
- not all old paths can be deleted
- not all module paths are true implementations yet
- cleanup must be phased

## 3. Classification Rules

Use these labels when reviewing files.

### 3.1 `KEEP`

Meaning:
- do not delete
- still used directly at runtime
- or is still the real implementation source

### 3.2 `MIGRATE_FIRST`

Meaning:
- module path exists, but module file is still a wrapper
- true implementation should be moved into the module path first
- old path can only become a compatibility wrapper after migration

### 3.3 `DELETE_LAST`

Meaning:
- file is already only a compatibility shell
- can be removed only after all imports are updated
- removal should happen after regression coverage is acceptable

## 4. Current Inventory

### 4.1 `KEEP`: real implementation still lives here

These files are still the real implementation source and must not be deleted yet.

- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/contact_collection_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/refusal_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/message_orchestrator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/queue_store.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/message_models.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/intent_classifier.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/queue/reply_delivery_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/workers/message_queue_worker.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/workers/reply_sender_worker.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/api/routes/xiaohongshu_ingest.py`

Why:
- runtime behavior still depends on these files directly
- or module-path files still re-export from them

### 4.2 `DELETE_LAST`: old-path shells already exist

These files are now thin compatibility wrappers.
They should not be deleted immediately, but they no longer contain core logic.

- `/Users/eric/Desktop/doubao_mcp_server/src/services/application/process_chat_turn.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_rule_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_coordinator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/models/chat_flow.py`

Why:
- each file only re-exports a module-path implementation

### 4.3 `MIGRATE_FIRST`: module path exists, but implementation still points backward

These module-path files are not true sources yet.
They should become the real implementation location before old files are removed.

#### Conversation / profile / contact

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/field_skip_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection/domain/contact_collection_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/contact_collection/domain/refusal_service.py`

#### Conversation understanding special case

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/unified_turn_understanding_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/semantic_understanding_layer.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/lexical_signal_layer.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/compat/turn_semantic_frame_to_turn_understanding_result_adapter.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/turn_understanding_service.py`

#### Message queue

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/application/message_orchestrator.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/queue_store.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/infrastructure/reply_delivery_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/domain/intent_classifier.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/domain/message_models.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/message_queue_worker.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/message_queue/workers/reply_sender_worker.py`

#### Platform integration

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/interfaces/http/ingest_route.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/platform_xiaohongshu/infrastructure/xhs_reply_client.py`

Why:
- these files currently re-export old-path implementations
- deleting the old implementation now would break runtime or tests

### 4.4 `KEEP`: mixed runtime pair for conversation understanding

These files must currently be treated as a bound pair and must not be “single-stack cleaned” in one step.

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/unified_turn_understanding_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/ai_semantic_extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/semantic_understanding_layer.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation_understanding/domain/lexical_signal_layer.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/turn_understanding_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/services/core/chat_service.py`

Current boundary:

1. `UnifiedTurnUnderstandingService` is the only official runtime entrypoint and should own final turn understanding decisions
2. `TurnUnderstandingService` still acts as helper/fallback library for:
   - lexical and FAQ signals
   - contact extraction
   - deterministic profile extraction
   - lightweight ack helpers
   - asked-field detection
3. `TurnUnderstandingService` must not be treated as a second independent runtime brain
4. cleanup priority is not “delete the old file first”; it is “move helper responsibilities behind unified, then delete compat pieces”

Do not do:

- delete `turn_understanding_service.py` before helper responsibilities are migrated
- let `ChatService` or other downstream code make a second turn-level decision outside unified
- remove compat projection before downstream consumers stop depending on `TurnUnderstandingResult`

## 5. Safe Cleanup Order

Do not clean wrappers in arbitrary order.
Use this order.

### Phase 1: freeze current behavior

Required before cleanup:
- keep prompt semantics unchanged
- keep contact collection rules unchanged
- keep queue behavior unchanged
- keep route protocol unchanged

Verification baseline:
- chat route tests pass
- contact collection tests pass
- message queue tests pass
- integration pipeline tests pass

### Phase 2: move true source into module paths

Recommended order:

1. `conversation/profile_collection`
2. `contact_collection`
3. `platform_xiaohongshu`
4. `message_queue`

Reason:
- `message_queue` and contact flow are higher-risk
- profile/conversation wrappers are easier to migrate first

For each migrated file:

1. copy real implementation into module path
2. update runtime imports to use module path directly
3. convert old path into a wrapper
4. rerun focused regression tests

Do not:
- delete old file in the same step
- rewrite business logic while moving it

Special rule for conversation understanding:

1. do not try to collapse to a single file in one batch
2. first enforce runtime boundary:
   - unified = sole entrypoint / sole decision owner
   - legacy turn understanding = helper library only
3. then migrate helper families one by one:
   - FAQ and lexical probes
   - contact helpers
   - deterministic extraction guards
   - lightweight ack helpers
4. only after downstream no longer depends on `TurnUnderstandingResult` compat behavior, remove projection adapters and legacy result coupling

### Phase 3: remove internal backward dependencies

This phase is complete only when:
- module files do not import old service files
- runtime code no longer depends on old path wrappers
- tests no longer import old path wrappers except explicitly deprecated tests

### Phase 4: delete wrappers

Only after Phase 3 is complete.

Delete candidates at that point:
- old-path wrappers under `src/services/application`
- old-path wrappers under `src/services/conversation`
- old-path wrapper model files such as `src/models/chat_flow.py`

Delete only after:
- imports are updated
- regression tests are green
- no active runtime path still references the wrapper

## 6. Execution Checklist

Use this checklist for each cleanup batch.

1. choose one module family only
2. identify current real implementation file
3. identify all imports to old path and module path
4. move implementation without semantic changes
5. convert previous real source into wrapper only if still needed
6. run focused tests
7. update this document or the execution log

## 7. Recommended First Batch

Best first cleanup batch:

- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/extraction_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/validation_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/ask_tracking_service.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py`
- `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/field_skip_service.py`

Why:
- lower risk than queue
- already conceptually grouped
- helps remove backward imports from chat-side code

Do not start with:
- queue store
- queue workers
- contact collection source-of-truth service

### Current Status

- 2026-03-18: first `profile_collection` source-of-truth migration completed
- migrated true sources into module paths:
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/extraction_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/validation_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/ask_tracking_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/profile_collection_policy.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/profile_collection/domain/field_skip_service.py`
- previous old paths are now compatibility wrappers:
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/data/extraction_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/data/validation_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/ask_tracking_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/collection/profile_collection_policy.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/field_skip_service.py`
- focused validation after migration:
  - `29 passed`

Next recommended batch:
- migrate `conversation` true sources or clean runtime imports that still point to old wrappers
- do not move `message_queue` true sources next unless a larger regression window is available

- 2026-03-18: `conversation` service-family source migration completed for user-facing domain services
- migrated true sources into module paths:
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/greeting_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/conversation_ending_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/expectation_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/input_fallback_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/modules/conversation/domain/user_question_service.py`
- previous old paths are now compatibility wrappers:
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/greeting_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/conversation_ending_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/expectation_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/input_fallback_service.py`
  - `/Users/eric/Desktop/doubao_mcp_server/src/services/conversation/user_question_service.py`
- focused validation after migration:
  - `73 passed`

Updated next recommended batch:
- either migrate `dialogue_manager` true source with extra caution
- or pause structural cleanup and focus on runtime import cleanup and broader regression
- still avoid `message_queue` true-source migration as the immediate next step

- 2026-04-15: conversation understanding remains intentionally mixed
- current decision:
  - keep `UnifiedTurnUnderstandingService` as sole official understanding entrypoint
  - keep `TurnUnderstandingService` as helper/fallback library during this phase
  - do not attempt immediate single-stack removal
- current optimization focus is runtime behavior, not wrapper deletion:
  - long-sentence chunking
  - sync AI timeout degradation
  - hard-field vs summary split
  - no-reask stability
- removal precondition for legacy turn understanding is upgraded:
  - FAQ/contact/ack/deterministic helper responsibilities must first be absorbed behind unified
  - downstream code must stop treating legacy result shapes as the default truth

## 8. Stop Conditions

Stop immediately if any of the following happens:

- prompt output changes unexpectedly
- contact collection tests regress
- queue integration behavior changes
- a migrated module starts importing both old and new sources in a circular way
- route behavior changes without an explicit API migration task

## 9. Handoff Format

If another model continues cleanup, it should report status like this:

```text
Compatibility cleanup phase:
- inventory complete / migration in progress / wrapper deletion phase

Current batch:
- module family being migrated

Completed:
- files migrated
- old wrappers created or retained
- focused tests run

Still blocked by:
- runtime imports still pointing to old path
- module files still re-exporting old path

Do not touch:
- prompt semantics
- contact collection business source of truth
- queue behavior semantics
```
