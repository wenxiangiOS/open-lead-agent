# 真实 AI 回归报告

- 开始时间: 2026-04-08T11:40:03
- 结束时间: 2026-04-08T12:02:22
- 场景源: `/tmp/real_ai_all_swcl_9sd`
- 总场景: 5
- 通过: 1
- 失败: 4
- 总耗时: 1339.465s
- 平均耗时: 267.893s
- 最长耗时: 972.13s
- Token: 64614 (调用 10 次)

## 失败归因汇总

- `response_content`: 4

## 结果概览

- `PASS` `field_multi_sentence_extract` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `listener_first_multi_profile_no_mechanical_repeat` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, multi_profile`
- `FAIL` `listener_first_matchmaking_then_multi_profile_stays_contextual` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, multi_profile`
- `FAIL` `humanlike_burst_input_preference_and_city_captured_first_reply` | category=`humanlike_queue` | tags=`humanlike, pending, burst, critical`
- `FAIL` `humanlike_single_main_question_per_turn_after_burst` | category=`humanlike_queue` | tags=`humanlike, pending, single_question`

## 失败详情

### listener_first_multi_profile_no_mechanical_repeat

- 场景文件: `/tmp/real_ai_all_swcl_9sd/scenarios__humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, multi_profile`
- 描述: 用户首轮主动给多个资料点时，应顺着继续，不要回头重问已给字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_swcl_9sd/scenarios__humanlike_listener_first_regression.json --scenario-id listener_first_multi_profile_no_mechanical_repeat --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['学历', '单身', '婚况', '年龄段']，实际 '做IT在深圳发展机会还挺多的呀，你具体是90几年出生的呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 90后，深圳，做IT
    AI: 做IT在深圳发展机会还挺多的呀，你具体是90几年出生的呀？
- 对话回放:
  - Turn 1 用户: 90后，深圳，做IT
    AI: 做IT在深圳发展机会还挺多的呀，你具体是90几年出生的呀？

### listener_first_matchmaking_then_multi_profile_stays_contextual

- 场景文件: `/tmp/real_ai_all_swcl_9sd/scenarios__humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, intent, multi_profile`
- 描述: 用户先表达找对象，再主动给多个资料点时，AI应顺着已给信息继续，不回头重问城市或工作。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_swcl_9sd/scenarios__humanlike_listener_first_regression.json --scenario-id listener_first_matchmaking_then_multi_profile_stays_contextual --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['学历', '单身', '婚况', '年龄段']，实际 '在深圳做IT平时工作节奏应该挺快的吧？你具体是哪一年出生的呀？'
- 失败轮次精简回放:
  - Turn 2 用户: 90后，深圳，做IT
    AI: 在深圳做IT平时工作节奏应该挺快的吧？你具体是哪一年出生的呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好呀，我先了解下，你是男生还是女生呀？
  - Turn 2 用户: 90后，深圳，做IT
    AI: 在深圳做IT平时工作节奏应该挺快的吧？你具体是哪一年出生的呀？

### humanlike_burst_input_preference_and_city_captured_first_reply

- 场景文件: `/tmp/real_ai_all_swcl_9sd/scenarios_pending__humanlike_queue_regression.json`
- 分类: `humanlike_queue`
- 标签: `humanlike, pending, burst, critical`
- 描述: 连发偏好+城市后，首轮回复应体现至少一个关键信息承接
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_swcl_9sd/scenarios_pending__humanlike_queue_regression.json --scenario-id humanlike_burst_input_preference_and_city_captured_first_reply --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=4 final_response 需要包含任一关键词 ['深圳', '高', '瘦', '偏好']，实际 ''
- 失败轮次精简回放:
  - Turn 4 用户: 喜欢深圳女生
    AI: 
- 对话回放:
  - Turn 1 用户: 我找对象
    AI: 好呀，那你可以先简单说下自己的情况哦，顺便问下你是男生还是女生呀？
  - Turn 2 用户: 我是男的
    AI: 好嘞，那你现在常住哪个城市呀？方便的话也可以说下大概的收入范围哦。
  - Turn 3 用户: 喜欢高高瘦瘦
    AI: 哈哈原来你偏好高高瘦瘦的类型呀，我记下来啦。你今年多大呀？
  - Turn 4 用户: 喜欢深圳女生
    AI: 

### humanlike_single_main_question_per_turn_after_burst

- 场景文件: `/tmp/real_ai_all_swcl_9sd/scenarios_pending__humanlike_queue_regression.json`
- 分类: `humanlike_queue`
- 标签: `humanlike, pending, single_question`
- 描述: 连发后单轮回复应尽量只推进一个主问题
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /tmp/real_ai_all_swcl_9sd/scenarios_pending__humanlike_queue_regression.json --scenario-id humanlike_single_main_question_per_turn_after_burst --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=3 final_response 需要包含任一关键词 ['学历', '年龄', '多大', '城市', '工作', '电话', '微信']，实际 ''
- 失败轮次精简回放:
  - Turn 3 用户: 喜欢深圳女生
    AI: 
- 对话回放:
  - Turn 1 用户: 我找对象
    AI: 好呀，你可以先简单介绍下自己的情况哦，我顺嘴核对下，你是男生还是女生呀？
  - Turn 2 用户: 男的
    AI: 好嘞，你现在常住哪个城市呀？
  - Turn 3 用户: 喜欢深圳女生
    AI: 
