# 真实 AI 回归报告

- 开始时间: 2026-04-08T12:33:58
- 结束时间: 2026-04-08T12:41:53
- 场景源: `/tmp/real_ai_all_qlajv_6v`
- 总场景: 10
- 通过: 6
- 失败: 4
- 总耗时: 474.375s
- 平均耗时: 47.438s
- 最长耗时: 83.882s
- Token: 162269 (调用 23 次)

## 失败归因汇总

- `response_content`: 4

## 结果概览

- `PASS` `field_multi_sentence_extract` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `listener_first_multi_profile_no_mechanical_repeat` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, multi_profile`
- `FAIL` `listener_first_matchmaking_then_multi_profile_stays_contextual` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, multi_profile`
- `PASS` `policy_opening_multi_field_shadow_profile_skips_location_age` | category=`policy_opening` | tags=`critical, opening, shadow_profile, multi_field`
- `FAIL` `humanlike_no_repeat_age_question_within_cooldown` | category=`humanlike_queue` | tags=`humanlike, pending, cooldown, critical`
- `PASS` `humanlike_no_premature_skip_without_explicit_refusal` | category=`humanlike_queue` | tags=`humanlike, pending, skip_guard, critical`
- `PASS` `humanlike_burst_input_preference_and_city_captured_first_reply` | category=`humanlike_queue` | tags=`humanlike, pending, burst, critical`
- `PASS` `humanlike_single_main_question_per_turn_after_burst` | category=`humanlike_queue` | tags=`humanlike, pending, single_question`
- `PASS` `humanlike_skip_guard_enabled_debug_info_not_show_skip` | category=`humanlike_queue` | tags=`humanlike, pending, skip_guard`
- `FAIL` `humanlike_cooldown_then_field_can_be_asked_again` | category=`humanlike_queue` | tags=`humanlike, pending, cooldown`

## 失败详情

### listener_first_multi_profile_no_mechanical_repeat

- 场景文件: `/tmp/real_ai_all_qlajv_6v/scenarios__humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, multi_profile`
- 描述: 用户首轮主动给多个资料点时，应顺着继续，不要回头重问已给字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_qlajv_6v/scenarios__humanlike_listener_first_regression.json --scenario-id listener_first_multi_profile_no_mechanical_repeat --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['学历', '单身', '婚况', '年龄段']，实际 '现在主要是做IT。 好，那你具体是90几年的呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 90后，深圳，做IT
    AI: 现在主要是做IT。 好，那你具体是90几年的呀？
- 对话回放:
  - Turn 1 用户: 90后，深圳，做IT
    AI: 现在主要是做IT。 好，那你具体是90几年的呀？

### listener_first_matchmaking_then_multi_profile_stays_contextual

- 场景文件: `/tmp/real_ai_all_qlajv_6v/scenarios__humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, intent, multi_profile`
- 描述: 用户先表达找对象，再主动给多个资料点时，AI应顺着已给信息继续，不回头重问城市或工作。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_qlajv_6v/scenarios__humanlike_listener_first_regression.json --scenario-id listener_first_matchmaking_then_multi_profile_stays_contextual --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['学历', '单身', '婚况', '年龄段']，实际 '在深圳做IT应该挺忙的吧，你具体是90几年出生的呀？'
- 失败轮次精简回放:
  - Turn 2 用户: 90后，深圳，做IT
    AI: 在深圳做IT应该挺忙的吧，你具体是90几年出生的呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好呀，既然是认真找对象，你可以先简单说说自己的情况哦，我顺嘴问下，你是男生还是女生呀？
  - Turn 2 用户: 90后，深圳，做IT
    AI: 在深圳做IT应该挺忙的吧，你具体是90几年出生的呀？

### humanlike_no_repeat_age_question_within_cooldown

- 场景文件: `/tmp/real_ai_all_qlajv_6v/scenarios_pending__humanlike_queue_regression.json`
- 分类: `humanlike_queue`
- 标签: `humanlike, pending, cooldown, critical`
- 描述: 同字段（年龄）在冷却窗口内不应连续追问
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_qlajv_6v/scenarios_pending__humanlike_queue_regression.json --scenario-id humanlike_no_repeat_age_question_within_cooldown --verbose`
- 失败摘要:
  - [final_response_not_contains_any] turn=3 final_response 不应包含关键词 ['今年多大']，实际 '原来是想找深圳的女生呀，你今年多大啦？'
- 失败轮次精简回放:
  - Turn 3 用户: 喜欢深圳的女生
    AI: 原来是想找深圳的女生呀，你今年多大啦？
- 对话回放:
  - Turn 1 用户: 你好，我找对象
    AI: 你好呀～我了解啦，你可以先简单介绍下自己哦，你是男生还是女生呀？
  - Turn 2 用户: 我是男的
    AI: 好的，那你现在常住哪个城市呀？要是方便的话也可以说下大概的月收入范围哦。
  - Turn 3 用户: 喜欢深圳的女生
    AI: 原来是想找深圳的女生呀，你今年多大啦？

### humanlike_cooldown_then_field_can_be_asked_again

- 场景文件: `/tmp/real_ai_all_qlajv_6v/scenarios_pending__humanlike_queue_regression.json`
- 分类: `humanlike_queue`
- 标签: `humanlike, pending, cooldown`
- 描述: 超过冷却轮次后，系统应继续自然推进，不应卡在同字段冷却提示
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_qlajv_6v/scenarios_pending__humanlike_queue_regression.json --scenario-id humanlike_cooldown_then_field_can_be_asked_again --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=4 final_response 需要包含任一关键词 ['学历', '年龄', '多大', '城市', '工作', '电话', '微信']，实际 '嗯嗯，那你是几几年的呀？'
- 失败轮次精简回放:
  - Turn 4 用户: 嗯
    AI: 嗯嗯，那你是几几年的呀？
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，你也可以先简单介绍下自己，我先了解下你的情况。
  - Turn 2 用户: 我是男的
    AI: 现在主要是做男的。 我再确认一下，你现在主要在哪个城市生活呀？ 我再轻问一句，你月收入大概在哪个区间？
  - Turn 3 用户: 我在深圳
    AI: 深圳挺多不错的适龄年轻人的，你是什么学历呀，顺便问下你现在感情状态怎么样？
  - Turn 4 用户: 嗯
    AI: 嗯嗯，那你是几几年的呀？
