# Next Fix TODO

- 更新时间: 2026-03-26 04:54:28
- global_gate: PASS

## Top 待修复项

1. `latency_p95_seconds` value=20.134 target=8.0
2. `baseline_degradation::latency_p95` value=20.134 target=16.339

## 建议改动文件

- `src/services/prompts/prompts.py`
- `src/services/core/dialogue_manager.py`
- `src/services/core/chat_service.py`
- `src/modules/conversation/application/process_chat_turn.py`
- `src/modules/profile_collection/domain/extraction_service.py`

## 复测命令

```bash
python3 scripts/run_random_user_simulation.py --cover-scenarios --seed 42 --verbose
```
