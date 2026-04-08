# 07_MESSAGE_QUEUE_DESIGN.md 真实 AI 回归汇总

- 时间: 2026-04-08T12:41:53
- 方案文档: `docs/07_MESSAGE_QUEUE_DESIGN.md`
- 场景数: `10`
- runner 退出码: `1`

## 场景清单

- `field_multi_sentence_extract`
- `policy_opening_multi_field_shadow_profile_skips_location_age`
- `listener_first_multi_profile_no_mechanical_repeat`
- `listener_first_matchmaking_then_multi_profile_stays_contextual`
- `humanlike_no_repeat_age_question_within_cooldown`
- `humanlike_no_premature_skip_without_explicit_refusal`
- `humanlike_burst_input_preference_and_city_captured_first_reply`
- `humanlike_single_main_question_per_turn_after_burst`
- `humanlike_skip_guard_enabled_debug_info_not_show_skip`
- `humanlike_cooldown_then_field_can_be_asked_again`

## 执行命令

```bash
python3 scripts/run_message_queue_real_ai_regression.py --scenario-pack core10 --verbose
```

报告详见同目录下 `latest.json` / `latest.md`（由 chat runner 生成）。