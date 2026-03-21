# 真实用户仿真回归报告

- 会话数: 60
- 总轮次: 135
- 总耗时(墙钟): 155.47s
- 累计会话耗时: 152.39s
- 失败检查数: 104
- 失败分布: turn=39, field=65, policy=0
- 时延 p95: 2.213s
- 时延 p99: 2.441s
- 模板化 Top1 占比: 23.0%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 96.2%
- 字段提取综合通过率: 90.1%
- 字段精确匹配通过率: 91.9%
- 字段完整性通过率: 89.4%

## 拟人化收集质量

- 总检查数: 1035
- 失败检查数: 39
- Turn 级失败: 39
- 策略级失败: 0
- 模板化 Top1 占比: 23.0%
- 时延 p95: 2.213s
- 时延 p99: 2.441s
- 高频 turn 失败 reply_too_fast_nonhuman: 38 次
- 高频 turn 失败 nonsense_not_guided: 1 次

## 字段提取准确性

- 总检查数: 659
- 失败检查数: 65
- 综合通过率: 90.1%
- 精确匹配检查数: 198
- 精确匹配失败数: 16
- 精确匹配通过率: 91.9%
- 完整性检查数: 461
- 完整性失败数: 49
- 完整性通过率: 89.4%
- 高频字段失败 partner_requirement_when_mentioned: 31 次
- 高频字段失败 location_truthy: 12 次
- 高频字段失败 location_matches_user_stated: 12 次
- 高频字段失败 unexpected_conversation_end: 6 次
- 高频字段失败 partner_requirement_matches_user_stated: 2 次
- 高频字段失败 occupation_matches_user_stated: 1 次
- 高频字段失败 marital_status_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 50.0% (7/14)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/135)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 reliability: 模板多样性=66.7%, Top1=66.7%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 64.7% (11/17)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 28.6% (2/7)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 46.7%
- 动作一致性分: 33.3%

## 隔离质量

- 会话数: 60
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.179
- p95 连续提问轮次: 2.0
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 1.7% (1/60)

## 提取诊断

- 字段冲突修复率: 100.0% (1/1)
- 证据链覆盖率: 78.9% (153/194)
- 失败类型 other: 37 次
- 失败类型 missed_stated_field: 15 次
- 失败类型 missing_extraction: 12 次
- 失败类型 wrong_value_or_normalization: 1 次

## 联系方式质量专项

- 联系方式成功率: 66.7% (14/21)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.7702s
- response_build: 0.6743s
- rule_check: 0.167s
- ai_call: 0.0905s
- context_load: 0.003s
- other: 0.0018s
- extract_collect: 0.0011s
- profile_load: 0.0005s
- profile_save: 0.0005s

## 意图分桶时延

- general: avg=0.694s p95=2.192s max=2.54s n=128
- fee: avg=2.165s p95=2.46s max=2.496s n=4
- reliability: avg=2.173s p95=2.329s max=2.335s n=3
- 秒回率(<1s): 62.2%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.105, 'perf': {'profile_load': 0.0, 'context_load': 0.0029, 'rule_check': 0.0014, 'profile_save': 0.0003, 'ai_call': 0.0988, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0013, 'total': 0.1049}}
  - {'turn': 4, 'user': '你看得懂吗', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.098, 'perf': {'profile_load': 0.0, 'context_load': 0.0032, 'rule_check': 0.0018, 'profile_save': 0.0005, 'ai_call': 0.0902, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0021, 'total': 0.0981}}
  - {'turn': 3, 'user': '好的', 'assistant': '收到，你刚这句我先接住。我们先按你在意的点继续聊，不急着留联系方式。', 'latency_s': 0.103, 'perf': {'profile_load': 0.0001, 'context_load': 0.0039, 'rule_check': 0.0015, 'profile_save': 0.0004, 'ai_call': 0.0948, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0017, 'total': 0.1027}}
- nonsense_not_guided
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.105, 'perf': {'profile_load': 0.0, 'context_load': 0.0029, 'rule_check': 0.0014, 'profile_save': 0.0003, 'ai_call': 0.0988, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0013, 'total': 0.1049}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_5_31bec5fb', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_cdeb7271', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_7_3d0c32a7', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_cdeb7271', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_9_8c35f203', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_19f1e804', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_19f1e804', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_9011a364', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_16_197ed73b', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_19f1e804', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_9011a364', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_16_197ed73b', 'expected': '深圳', 'actual': None, 'note': ''}
- occupation_matches_user_stated
  - {'scenario_id': 'field_multi_info_extract_basic', 'session_id': 'realism_18_7f000c65', 'expected': '运营', 'actual': '做运营的', 'note': ''}
- partner_requirement_matches_user_stated
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_375350d7', 'expected': '个成熟稳重的 有什么推荐吗', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_42_48e97442', 'expected': '高高瘦瘦', 'actual': None, 'note': ''}
### policy

## 基线对比

- 检测到退化指标：
- humanlike_pass_rate: current=0.9623 baseline=0.997
- extraction_pass_rate: current=0.9014 baseline=0.9512
- template_top1_ratio: current=0.2296 baseline=0.0881

## 优化建议

- 模板化风险偏高：Top1 模板占比 23.0% > 阈值 18.0%，建议扩写多样化话术。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 4
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.6471 target=0.9
- [P1] template_top1_ratio: value=0.2296 target=0.22
- [P1] field_stability_score: value=0.0 target=0.9
- [P1] baseline_degradation::humanlike_pass_rate: value=0.9623 target=0.997
- [P1] baseline_degradation::extraction_pass_rate: value=0.9014 target=0.9512

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
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 6
- 严重失败项数量: 1
- [major] template_top1_ratio: value=0.2296 target=0.22
- [critical] refusal_respect_rate: value=0.6471 target=0.9
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::humanlike_pass_rate: value=0.9623 target=0.997
- [major] baseline_degradation::extraction_pass_rate: value=0.9014 target=0.9512
- [major] baseline_degradation::template_top1_ratio: value=0.2296 target=0.0881

## 模板化风险 Top10

- 31 次 (23.0%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 14 次 (10.4%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 9 次 (6.7%): `方便留个电话吗后续有合适的人选时联系你`
- 6 次 (4.4%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 5 次 (3.7%): `好哒那想问下你今年多大呀`
- 5 次 (3.7%): `收到啦那你现在主要在哪个城市工作生活呀`
- 5 次 (3.7%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 4 次 (3.0%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`
- 3 次 (2.2%): `这个电话主要是留作后面联系用的我们不会乱打给你你方便的话把号码发我就可以`
- 3 次 (2.2%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配要是你电话方便的话也可以留一个后面联系会更及时些`

## 字段收集质量

- 总检查数: 659
- 失败检查数: 65
- 通过率: 90.1%
- contact_phone_then_wechat_prompt (realism_5_31bec5fb): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_6_cdeb7271): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_rejection_should_not_end (realism_7_3d0c32a7): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_after_wechat_rejection_should_not_end (realism_8_82685f80): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_divorce_incomplete_should_end (realism_9_8c35f203): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_11_19f1e804): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_age_under_limit (realism_12_e931b36e): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- faq_priority_mediator (realism_13_9011a364): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- faq_priority_contact_why_phone (realism_16_197ed73b): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- field_multi_info_extract_basic (realism_18_7f000c65): ["occupation_matches_user_stated: expected='运营', actual='做运营的'"]
- 高频失败 partner_requirement_when_mentioned: 31 次
- 高频失败 location_truthy: 12 次
- 高频失败 location_matches_user_stated: 12 次
- 高频失败 unexpected_conversation_end: 6 次
- 高频失败 partner_requirement_matches_user_stated: 2 次
- 高频失败 occupation_matches_user_stated: 1 次
- 高频失败 marital_status_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 900
- 失败检查数: 0
- 通过率: 100.0%
