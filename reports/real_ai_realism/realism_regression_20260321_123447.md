# 真实用户仿真回归报告

- 会话数: 36
- 总轮次: 76
- 总耗时(墙钟): 99.17s
- 累计会话耗时: 96.12s
- 失败检查数: 55
- 失败分布: turn=17, field=37, policy=1
- 时延 p95: 2.228s
- 时延 p99: 2.259s
- 模板化 Top1 占比: 30.3%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 97.1%
- 字段提取综合通过率: 89.3%
- 字段精确匹配通过率: 87.0%
- 字段完整性通过率: 90.1%

## 拟人化收集质量

- 总检查数: 616
- 失败检查数: 18
- Turn 级失败: 17
- 策略级失败: 1
- 模板化 Top1 占比: 30.3%
- 时延 p95: 2.228s
- 时延 p99: 2.259s
- 高频 turn 失败 reply_too_fast_nonhuman: 16 次
- 高频 turn 失败 nonsense_not_guided: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 345
- 失败检查数: 37
- 综合通过率: 89.3%
- 精确匹配检查数: 92
- 精确匹配失败数: 12
- 精确匹配通过率: 87.0%
- 完整性检查数: 253
- 完整性失败数: 25
- 完整性通过率: 90.1%
- 高频字段失败 partner_requirement_when_mentioned: 12 次
- 高频字段失败 location_truthy: 9 次
- 高频字段失败 location_matches_user_stated: 9 次
- 高频字段失败 unexpected_conversation_end: 4 次
- 高频字段失败 occupation_matches_user_stated: 1 次
- 高频字段失败 age_matches_user_stated: 1 次
- 高频字段失败 partner_requirement_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 58.3% (7/12)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/76)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 reliability: 模板多样性=66.7%, Top1=66.7%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 66.7% (8/12)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 20.0% (1/5)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 52.5%
- 动作一致性分: 50.0%

## 隔离质量

- 会话数: 36
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.286
- p95 连续提问轮次: 2.35
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 2.8% (1/36)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 76.5% (65/85)
- 失败类型 other: 16 次
- 失败类型 missed_stated_field: 10 次
- 失败类型 missing_extraction: 9 次
- 失败类型 wrong_value_or_normalization: 2 次

## 联系方式质量专项

- 联系方式成功率: 66.7% (4/6)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.9044s
- response_build: 0.7936s
- rule_check: 0.2095s
- ai_call: 0.0911s
- context_load: 0.0031s
- other: 0.0016s
- extract_collect: 0.001s
- profile_save: 0.0005s
- profile_load: 0.0004s

## 意图分桶时延

- general: avg=0.776s p95=2.105s max=2.233s n=69
- fee: avg=2.177s p95=2.3s max=2.311s n=4
- reliability: avg=2.155s p95=2.235s max=2.238s n=3
- 秒回率(<1s): 56.6%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.096, 'perf': {'profile_load': 0.0, 'context_load': 0.0028, 'rule_check': 0.0017, 'profile_save': 0.0003, 'ai_call': 0.0878, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0026, 'total': 0.0955}}
  - {'turn': 4, 'user': '你看得懂吗', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.092, 'perf': {'profile_load': 0.0, 'context_load': 0.0027, 'rule_check': 0.0015, 'profile_save': 0.0002, 'ai_call': 0.0868, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0008, 'total': 0.0923}}
  - {'turn': 3, 'user': '好的', 'assistant': '收到，你刚这句我先接住。我们先按你在意的点继续聊，不急着留联系方式。', 'latency_s': 0.097, 'perf': {'profile_load': 0.0, 'context_load': 0.0037, 'rule_check': 0.0018, 'profile_save': 0.0003, 'ai_call': 0.0897, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0009, 'total': 0.0967}}
- nonsense_not_guided
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.096, 'perf': {'profile_load': 0.0, 'context_load': 0.0028, 'rule_check': 0.0017, 'profile_save': 0.0003, 'ai_call': 0.0878, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0026, 'total': 0.0955}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_5_51bd90e6', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_f8ad6fad', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_7_a52f1c63', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_f8ad6fad', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_9_85e07ec9', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_0d96ef29', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_0d96ef29', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_ad2f0091', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_16_0c1e54c4', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_0d96ef29', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_ad2f0091', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_16_0c1e54c4', 'expected': '深圳', 'actual': None, 'note': ''}
- occupation_matches_user_stated
  - {'scenario_id': 'field_multi_info_extract_basic', 'session_id': 'realism_18_c4078659', 'expected': '运营', 'actual': '做运营的', 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_9c449cec', 'expected': '90后', 'actual': 30, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_ddceda9a', 'expected': 0, 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.8928 baseline=0.9167
- latency_p95: current=2.228 baseline=2.107
- template_top1_ratio: current=0.3026 baseline=0.2

## 优化建议

- 模板化风险偏高：Top1 模板占比 30.3% > 阈值 18.0%，建议扩写多样化话术。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 3
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.6667 target=0.9
- [P1] template_top1_ratio: value=0.3026 target=0.22
- [P1] baseline_degradation::extraction_pass_rate: value=0.8928 target=0.9167
- [P1] baseline_degradation::latency_p95: value=2.228 target=2.107

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => NOT_COVERED (mq checks disabled)

## 根因分桶

- policy_or_routing: 1
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: extraction_pass_rate, latency_p95
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107
- 2026-03-21T12:32:17 humanlike=0.9 extraction=0.9167 latency_p95=1.815
- 2026-03-21T12:31:43 humanlike=0.9 extraction=0.9167 latency_p95=1.758
- 2026-03-21T12:30:33 humanlike=0.9 extraction=0.9167 latency_p95=2.043
- 2026-03-21T12:29:45 humanlike=0.9 extraction=0.9167 latency_p95=1.992
- 2026-03-21T12:25:44 humanlike=0.9968 extraction=0.9275 latency_p95=18.136

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 5
- 严重失败项数量: 1
- [major] template_top1_ratio: value=0.3026 target=0.22
- [critical] refusal_respect_rate: value=0.6667 target=0.9
- [major] baseline_degradation::extraction_pass_rate: value=0.8928 target=0.9167
- [major] baseline_degradation::latency_p95: value=2.228 target=2.107
- [major] baseline_degradation::template_top1_ratio: value=0.3026 target=0.2

## 模板化风险 Top10

- 23 次 (30.3%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 5 次 (6.6%): `方便留个电话吗后续有合适的人选时联系你`
- 4 次 (5.3%): `收到啦那你现在主要在哪个城市工作生活呀`
- 3 次 (4.0%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 3 次 (4.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 2 次 (2.6%): `电话只是留作登记和后面联系不会拿去做别的你要是方便的话发我一个号码就行`
- 2 次 (2.6%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 2 次 (2.6%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`
- 2 次 (2.6%): `我先换个说法继续聊避免重复问你同一个点`

## 字段收集质量

- 总检查数: 345
- 失败检查数: 37
- 通过率: 89.3%
- contact_phone_then_wechat_prompt (realism_5_51bd90e6): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_6_f8ad6fad): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_rejection_should_not_end (realism_7_a52f1c63): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_after_wechat_rejection_should_not_end (realism_8_6b6dbf11): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_divorce_incomplete_should_end (realism_9_85e07ec9): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_11_0d96ef29): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_age_under_limit (realism_12_95d56c4b): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- faq_priority_mediator (realism_13_ad2f0091): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- faq_priority_contact_why_phone (realism_16_0c1e54c4): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- field_multi_info_extract_basic (realism_18_c4078659): ["occupation_matches_user_stated: expected='运营', actual='做运营的'"]
- 高频失败 partner_requirement_when_mentioned: 12 次
- 高频失败 location_truthy: 9 次
- 高频失败 location_matches_user_stated: 9 次
- 高频失败 unexpected_conversation_end: 4 次
- 高频失败 occupation_matches_user_stated: 1 次
- 高频失败 age_matches_user_stated: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 540
- 失败检查数: 1
- 通过率: 99.8%
- abuse_repeated_ack_should_not_loop_contact (realism_2_ddceda9a): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 1 次
