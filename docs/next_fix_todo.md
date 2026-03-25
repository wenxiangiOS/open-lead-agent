# Next Fix TODO

- 更新时间: 2026-03-25 13:53:00
- global_gate: PASS

## 项目级约束

- 当前阶段不把 token / 调用成本作为优化约束
- 短答允许继续走重模型
- 优先目标是拟人化、自然度、重复追问控制、动作一致性、时延体验和门禁表现

## Top 待修复项

1. `latency_p95_seconds` value=16.339 target=8.0
2. `baseline_degradation::extraction_pass_rate` value=0.9274 target=0.9443
3. `baseline_degradation::latency_p95` value=16.339 target=11.891

## 建议改动文件

- `src/services/prompts/prompts.py`
- `src/services/core/dialogue_manager.py`
- `src/services/core/chat_service.py`
- `src/modules/conversation/application/process_chat_turn.py`
- `src/modules/profile_collection/domain/extraction_service.py`

## 执行规格

- 资料对话拟人化专项优化说明: `docs/conversation_humanlike_execution_spec.md`
- 第一阶段最小落地清单: `docs/conversation_humanlike_phase1_minimum.md`

## 复测命令

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```
