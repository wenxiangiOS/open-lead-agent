# Next Fix TODO

- 更新时间: 2026-03-24 14:32:37
- global_gate: FAIL

## Top 待修复项

1. `refusal_respect_rate` value=0.7917 target=0.9
2. `latency_p95_seconds` value=19.942 target=8.0
3. `field_stability_score` value=0.5714 target=0.9
4. `baseline_degradation::latency_p95` value=19.942 target=2.56

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
