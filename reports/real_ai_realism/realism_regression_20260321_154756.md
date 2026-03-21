# 真实用户仿真回归报告

- 会话数: 8
- 总轮次: 20
- 总耗时(墙钟): 19.22s
- 累计会话耗时: 16.2s
- 失败检查数: 22
- 失败分布: turn=9, field=13, policy=0
- 时延 p95: 2.065s
- 时延 p99: 2.163s
- 模板化 Top1 占比: 15.0%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 93.6%
- 字段提取综合通过率: 88.9%
- 字段精确匹配通过率: 95.3%
- 字段完整性通过率: 85.1%

## 拟人化收集质量

- 总检查数: 140
- 失败检查数: 9
- Turn 级失败: 9
- 策略级失败: 0
- 模板化 Top1 占比: 15.0%
- 时延 p95: 2.065s
- 时延 p99: 2.163s
- 高频 turn 失败 reply_too_fast_nonhuman: 9 次

## 字段提取准确性

- 总检查数: 117
- 失败检查数: 13
- 综合通过率: 88.9%
- 精确匹配检查数: 43
- 精确匹配失败数: 2
- 精确匹配通过率: 95.3%
- 完整性检查数: 74
- 完整性失败数: 11
- 完整性通过率: 85.1%
- 高频字段失败 partner_requirement_when_mentioned: 5 次
- 高频字段失败 unexpected_conversation_end: 4 次
- 高频字段失败 location_truthy: 2 次
- 高频字段失败 location_matches_user_stated: 2 次

## 对话自然度指标

- 情绪承接命中率: 100.0% (2/2)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/20)
- 联系方式突兀转场次数: 0

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 50.0% (2/4)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 0.0% (0/4)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 58.3%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 8
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1
- p95 连续提问轮次: 1.0
- 最长连续提问轮次: 1
- 会话中出现>=3连问占比: 0.0% (0/8)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 79.5% (35/44)
- 失败类型 other: 9 次
- 失败类型 missing_extraction: 2 次
- 失败类型 missed_stated_field: 2 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (5/5)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.4573s
- response_build: 0.3659s
- ai_call: 0.101s
- context_load: 0.0035s
- other: 0.003s
- rule_check: 0.0019s
- extract_collect: 0.0013s
- profile_save: 0.0007s
- profile_load: 0.0004s

## 意图分桶时延

- general: avg=0.457s p95=2.065s max=2.187s n=20
- 秒回率(<1s): 80.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '不留电话', 'assistant': '这个电话只是留作登记和后面联系用的，不会私下打扰你。你方便的话发我一个号码就行～', 'latency_s': 0.104, 'perf': {'profile_load': 0.0, 'context_load': 0.0026, 'rule_check': 0.0015, 'profile_save': 0.0007, 'ai_call': 0.0954, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0038, 'total': 0.1043}}
  - {'turn': 2, 'user': '不留电话', 'assistant': '这个电话只是留作登记和后面联系用的，不会私下打扰你。你方便的话发我一个号码就行～', 'latency_s': 0.095, 'perf': {'profile_load': 0.0, 'context_load': 0.0034, 'rule_check': 0.0018, 'profile_save': 0.0006, 'ai_call': 0.0862, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0027, 'total': 0.095}}
  - {'turn': 4, 'user': '那我微信wx123456', 'assistant': '没问题～这边就按你的情况去安排，一般1到2天内会有初步匹配消息，后续联系都会提前打招呼，不会突然打扰你～', 'latency_s': 0.105, 'perf': {'profile_load': 0.0, 'context_load': 0.0047, 'rule_check': 0.0028, 'profile_save': 0.0005, 'ai_call': 0.0921, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0041, 'total': 0.1046}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_1_a46d27ec', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_after_wechat_rejection_should_not_end', 'session_id': 'realism_2_8aa29da4', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_3_8e9efced', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_1_a46d27ec', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_3_8e9efced', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_4_f5ee4ec6', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_6_167b6d17', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_burst_input_preference_and_city_captured_first_reply', 'session_id': 'realism_8_b6c94bcc', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_6_167b6d17', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_burst_input_preference_and_city_captured_first_reply', 'session_id': 'realism_8_b6c94bcc', 'expected': '深圳', 'actual': None, 'note': ''}
### policy

## 基线对比

- 检测到退化指标：
- humanlike_pass_rate: current=0.9357 baseline=0.9983
- extraction_pass_rate: current=0.8889 baseline=0.9384
- template_top1_ratio: current=0.15 baseline=0.0508

## 优化建议

- 当前未发现显著单阶段瓶颈。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 2
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.5 target=0.9
- [P1] baseline_degradation::humanlike_pass_rate: value=0.9357 target=0.9983
- [P1] baseline_degradation::extraction_pass_rate: value=0.8889 target=0.9384

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_PASS
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => NOT_COVERED (mq checks disabled)

## 根因分桶

- prompt_or_style: 0
- policy_or_routing: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: humanlike_pass_rate, extraction_pass_rate
- 2026-03-21T15:47:56 humanlike=0.9357 extraction=0.8889 latency_p95=2.065
- 2026-03-21T15:32:36 humanlike=0.9983 extraction=0.9384 latency_p95=14.141
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 4
- 严重失败项数量: 1
- [critical] refusal_respect_rate: value=0.5 target=0.9
- [major] baseline_degradation::humanlike_pass_rate: value=0.9357 target=0.9983
- [major] baseline_degradation::extraction_pass_rate: value=0.8889 target=0.9384
- [major] baseline_degradation::template_top1_ratio: value=0.15 target=0.0508

## 模板化风险 Top10

- 3 次 (15.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 2 次 (10.0%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`
- 2 次 (10.0%): `理解你的感受可以呀那你直接发我微信号就行我这边先记下来`
- 2 次 (10.0%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 1 次 (5.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配行呀那我先帮你推进匹配一般#到#天内会有初步匹配消息有合适的人选会提前和你确认沟通时间`
- 1 次 (5.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配要是你电话方便的话也可以留一个后面联系会更及时些`
- 1 次 (5.0%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 1 次 (5.0%): `没问题这边就按你的情况去安排一般#到#天内会有初步匹配消息后续联系都会提前打招呼不会突然打扰你`
- 1 次 (5.0%): `一般#到#天内会有初步匹配消息后续联系前我们会先跟你约时间`
- 1 次 (5.0%): `行呀那我先帮你推进匹配一般#到#天内会有初步匹配消息有合适的人选会提前和你确认沟通时间`

## 字段收集质量

- 总检查数: 117
- 失败检查数: 13
- 通过率: 88.9%
- contact_phone_and_wechat_same_turn (realism_1_a46d27ec): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_after_wechat_rejection_should_not_end (realism_2_8aa29da4): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_3_8e9efced): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_asks_wechat_instead_of_phone (realism_4_f5ee4ec6): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_phone_inconvenient_then_wechat (realism_5_33c2d228): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- field_partner_requirement_should_not_override_location (realism_6_167b6d17): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- humanlike_burst_input_preference_and_city_captured_first_reply (realism_8_b6c94bcc): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- 高频失败 partner_requirement_when_mentioned: 5 次
- 高频失败 unexpected_conversation_end: 4 次
- 高频失败 location_truthy: 2 次
- 高频失败 location_matches_user_stated: 2 次

## 对话策略规则质量

- 总检查数: 120
- 失败检查数: 0
- 通过率: 100.0%
