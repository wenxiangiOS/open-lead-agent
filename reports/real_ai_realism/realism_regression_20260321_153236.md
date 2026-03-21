# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2202.61s
- 累计会话耗时: 2201.67s
- 失败检查数: 91
- 失败分布: turn=0, field=87, policy=4
- 时延 p95: 14.141s
- 时延 p99: 14.244s
- 模板化 Top1 占比: 5.1%
- Token: 476883 (调用 138 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.8%
- 字段提取综合通过率: 93.8%
- 字段精确匹配通过率: 91.9%
- 字段完整性通过率: 94.6%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 4
- Turn 级失败: 0
- 策略级失败: 4
- 模板化 Top1 占比: 5.1%
- 时延 p95: 14.141s
- 时延 p99: 14.244s
- 高频策略失败 ack_overuse: 1 次
- 高频策略失败 income_question_soft_tone: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 87
- 综合通过率: 93.8%
- 精确匹配检查数: 397
- 精确匹配失败数: 32
- 精确匹配通过率: 91.9%
- 完整性检查数: 1016
- 完整性失败数: 55
- 完整性通过率: 94.6%
- 高频字段失败 partner_requirement_when_mentioned: 24 次
- 高频字段失败 location_truthy: 19 次
- 高频字段失败 location_matches_user_stated: 19 次
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 occupation_matches_user_stated: 3 次
- 高频字段失败 partner_requirement_matches_user_stated: 3 次
- 高频字段失败 age_matches_user_stated: 2 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 59.1% (13/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.3% (1/295)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=42.9%, Top1=71.4%, 样本=7
- 意图 reliability: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 match: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 safety: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 82.6% (19/23)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 23.8% (5/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 39.4%
- 动作一致性分: 50.0%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.268
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 5.8% (8/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/1)
- 证据链覆盖率: 71.2% (306/430)
- 失败类型 other: 35 次
- 失败类型 missed_stated_field: 25 次
- 失败类型 missing_extraction: 20 次
- 失败类型 wrong_value_or_normalization: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 10.907s
- total: 7.1079s
- response_build: 0.6768s
- rule_check: 0.1487s
- context_load: 0.0127s
- extract_collect: 0.0127s
- profile_load: 0.0085s
- profile_save: 0.0074s
- other: 0.0015s

## 意图分桶时延

- general: avg=7.371s p95=14.142s max=16.773s n=280
- fee: avg=2.172s p95=2.461s max=2.47s n=7
- reliability: avg=2.317s p95=2.501s max=2.516s n=4
- match: avg=2.072s p95=2.315s max=2.342s n=2
- photo: avg=1.883s p95=1.883s max=1.883s n=1
- safety: avg=2.531s p95=2.531s max=2.531s n=1
- 秒回率(<1s): 6.1%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_b113af8f', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_234ef0ea', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_eb2b19f7', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_after_wechat_rejection_should_not_end', 'session_id': 'realism_9_58e30623', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_234ef0ea', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_with_spaces_should_collect', 'session_id': 'realism_16_598167b4', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_85d95040', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_5cf90541', 'expected': '17688654321', 'actual': None, 'note': ''}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_1fa21a01', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_64ea72d9', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_multi_sentence_extract', 'session_id': 'realism_85_dc0b9fcc', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_1fa21a01', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_64ea72d9', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_multi_sentence_extract', 'session_id': 'realism_85_dc0b9fcc', 'expected': '深圳', 'actual': None, 'note': ''}
### policy
- ack_overuse
  - {'scenario_id': 'field_income_extract_monthly', 'session_id': 'realism_95_8b44ffcd', 'expected': '<=0.35', 'actual': 1.0, 'note': ''}
- income_question_soft_tone
  - {'scenario_id': 'humanlike_no_repeat_age_question_within_cooldown', 'session_id': 'realism_133_4a9521b3', 'expected': 0, 'actual': 1, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'humanlike_burst_input_preference_and_city_captured_first_reply', 'session_id': 'realism_135_13379a5f', 'expected': '<=1', 'actual': 2, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'humanlike_burst_input_preference_and_city_captured_first_reply', 'session_id': 'realism_135_13379a5f', 'expected': 0, 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- latency_p95: current=14.141 baseline=2.213

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 3
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.8261 target=0.9
- [P1] latency_p95_seconds: value=14.141 target=8.0
- [P1] field_stability_score: value=0.0 target=0.9
- [P1] baseline_degradation::latency_p95: value=14.141 target=2.213

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_FAIL
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => COVERED_PASS (failed=0)

## 根因分桶

- prompt_or_style: 1
- policy_or_routing: 1
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: latency_p95
- 2026-03-21T15:32:36 humanlike=0.9983 extraction=0.9384 latency_p95=14.141
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228

## MQ补充检查

- covered=True pass=True
- total=20 passed=20 failed=0 skipped=0
- output_tail:
  - [20/20] RUN mq_dashboard_metrics_funnel_consistency (mq)
  -        mq dashboard 漏斗指标应一致（ingest 入队前置断言）
  - [20/20] PASS mq_dashboard_metrics_funnel_consistency (0.01s)
  - 总场景: 20
  - 通过: 20
  - 失败: 0
  - 跳过: 0
  - 总耗时: 0.22s
  - 平均耗时: 0.011s
  - 最长耗时: 0.04s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 4
- 严重失败项数量: 1
- [major] latency_p95_seconds: value=14.141 target=8.0
- [critical] refusal_respect_rate: value=0.8261 target=0.9
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::latency_p95: value=14.141 target=2.213

## 模板化风险 Top10

- 15 次 (5.1%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 10 次 (3.4%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 10 次 (3.4%): `收到啦那你现在主要在哪个城市工作生活呀`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 7 次 (2.4%): `好哒那想问下你今年多大呀`
- 6 次 (2.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配收到这个偏好我先帮你记好后面我按这个方向优先匹配有进展就及时告诉你`
- 6 次 (2.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦我会按这个方向优先筛选后面有合适的第一时间跟你同步`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 6 次 (2.0%): `我先记下来啦顺带问下你是男生还是女生呀`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 87
- 通过率: 93.8%
- contact_phone_and_wechat_same_turn (realism_7_b113af8f): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_after_wechat_rejection_should_not_end (realism_9_58e30623): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_234ef0ea): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_with_spaces_should_collect (realism_16_598167b4): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_asks_wechat_instead_of_phone (realism_21_eb2b19f7): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_questions_privacy_before_phone (realism_22_612735c1): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_provides_wechat_after_phone_prompt (realism_24_9eb860b1): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_with_text_prefix_should_collect (realism_27_8cc38d72): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_says_phone_inconvenient_then_wechat (realism_31_215e5420): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_85d95040): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "wechat_matches_user_stated: expected='wx72378', actual=None"]
- 高频失败 partner_requirement_when_mentioned: 24 次
- 高频失败 location_truthy: 19 次
- 高频失败 location_matches_user_stated: 19 次
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 occupation_matches_user_stated: 3 次
- 高频失败 partner_requirement_matches_user_stated: 3 次
- 高频失败 age_matches_user_stated: 2 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 4
- 通过率: 99.8%
- field_income_extract_monthly (realism_95_8b44ffcd): ["ack_overuse: expected='<=0.35', actual=1.0"]
- humanlike_no_repeat_age_question_within_cooldown (realism_133_4a9521b3): ['income_question_soft_tone: expected=0, actual=1']
- humanlike_burst_input_preference_and_city_captured_first_reply (realism_135_13379a5f): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 ack_overuse: 1 次
- 高频失败 income_question_soft_tone: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
- 高频失败 no_consecutive_same_field_ask: 1 次
