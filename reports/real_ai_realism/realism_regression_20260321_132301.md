# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2200.77s
- 累计会话耗时: 2199.74s
- 失败检查数: 76
- 失败分布: turn=0, field=69, policy=7
- 时延 p95: 16.583s
- 时延 p99: 18.145s
- 模板化 Top1 占比: 8.8%
- Token: 560132 (调用 161 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.7%
- 字段提取综合通过率: 95.1%
- 字段精确匹配通过率: 93.0%
- 字段完整性通过率: 96.0%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 7
- Turn 级失败: 0
- 策略级失败: 7
- 模板化 Top1 占比: 8.8%
- 时延 p95: 16.583s
- 时延 p99: 18.145s
- 高频策略失败 medium_ask_limit_partner_requirement: 4 次
- 高频策略失败 no_consecutive_same_field_ask: 2 次
- 高频策略失败 low_priority_never_ask_height: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 69
- 综合通过率: 95.1%
- 精确匹配检查数: 397
- 精确匹配失败数: 28
- 精确匹配通过率: 93.0%
- 完整性检查数: 1016
- 完整性失败数: 41
- 完整性通过率: 96.0%
- 高频字段失败 partner_requirement_when_mentioned: 15 次
- 高频字段失败 location_truthy: 14 次
- 高频字段失败 location_matches_user_stated: 14 次
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 age_matches_user_stated: 3 次
- 高频字段失败 partner_requirement_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 occupation_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 54.5% (12/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/295)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=42.9%, Top1=71.4%, 样本=7
- 意图 reliability: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 match: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 safety: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 95.7% (22/23)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 19.1% (4/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 46.7%
- 动作一致性分: 37.5%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.368
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 5
- 会话中出现>=3连问占比: 6.5% (9/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/1)
- 证据链覆盖率: 70.3% (312/444)
- 失败类型 other: 26 次
- 失败类型 missed_stated_field: 21 次
- 失败类型 missing_extraction: 15 次
- 失败类型 wrong_value_or_normalization: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 10.8703s
- total: 7.1006s
- response_build: 0.6533s
- rule_check: 0.1392s
- extract_collect: 0.0141s
- context_load: 0.0133s
- profile_load: 0.0094s
- profile_save: 0.0077s
- other: 0.0015s

## 意图分桶时延

- general: avg=7.371s p95=16.953s max=20.367s n=280
- fee: avg=2.003s p95=2.214s max=2.268s n=7
- reliability: avg=2.076s p95=2.313s max=2.365s n=4
- match: avg=1.953s p95=2.256s max=2.29s n=2
- photo: avg=2.301s p95=2.301s max=2.301s n=1
- safety: avg=2.35s p95=2.35s max=2.35s n=1
- 秒回率(<1s): 5.8%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.7%

## 失败样本（自动抽样）

### turn
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_f816b506', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_only_then_ask_phone', 'session_id': 'realism_12_31a2124e', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_invalid_should_retry', 'session_id': 'realism_14_d1f5ad57', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_faf72a4f', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_9f36018e', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_ff361f63', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_1695538a', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_af488dbf', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_e9651938', 'expected': '17688654321', 'actual': None, 'note': ''}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_a3d6a191', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_6b830b53', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_multi_sentence_extract', 'session_id': 'realism_85_c24d1322', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_a3d6a191', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_6b830b53', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_multi_sentence_extract', 'session_id': 'realism_85_c24d1322', 'expected': '深圳', 'actual': None, 'note': ''}
### policy
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_698d511e', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_f8e16cf1', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_134_1886b124', 'expected': '<=1', 'actual': 2, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_698d511e', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'humanlike_burst_input_preference_and_city_captured_first_reply', 'session_id': 'realism_135_09974109', 'expected': 0, 'actual': 1, 'note': ''}
- low_priority_never_ask_height
  - {'scenario_id': 'field_height_extract_cm', 'session_id': 'realism_94_f3d06027', 'expected': '0', 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- humanlike_pass_rate: current=0.997 baseline=1.0
- latency_p95: current=16.583 baseline=16.404
- template_top1_ratio: current=0.0881 baseline=0.0526

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 4
- P2失败数: 0
- [P1] latency_p95_seconds: value=16.583 target=8.0
- [P1] field_stability_score: value=0.0 target=0.9
- [P1] baseline_degradation::humanlike_pass_rate: value=0.997 target=1.0
- [P1] baseline_degradation::latency_p95: value=16.583 target=16.404

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => COVERED_PASS (failed=0)

## 根因分桶

- policy_or_routing: 2
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: humanlike_pass_rate, latency_p95
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107
- 2026-03-21T12:32:17 humanlike=0.9 extraction=0.9167 latency_p95=1.815

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
  - 总耗时: 0.21s
  - 平均耗时: 0.01s
  - 最长耗时: 0.04s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 5
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=16.583 target=8.0
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::humanlike_pass_rate: value=0.997 target=1.0
- [major] baseline_degradation::latency_p95: value=16.583 target=16.404
- [major] baseline_degradation::template_top1_ratio: value=0.0881 target=0.0526

## 模板化风险 Top10

- 26 次 (8.8%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦我先按这个方向给你筛后面有合适的我优先同步你`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 10 次 (3.4%): `这个偏好我先记住啦我先按这个方向给你筛后面有合适的我优先同步你`
- 9 次 (3.0%): `收到啦那你现在主要在哪个城市工作生活呀`
- 8 次 (2.7%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 7 次 (2.4%): `好哒那想问下你今年多大呀`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 6 次 (2.0%): `我先记下来啦顺带问下你是男生还是女生呀`
- 5 次 (1.7%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 69
- 通过率: 95.1%
- contact_phone_then_wechat_prompt (realism_6_f816b506): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_7_faf72a4f): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_refused_then_user_provides_wechat (realism_11_9f36018e): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_only_then_ask_phone (realism_12_31a2124e): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_invalid_should_retry (realism_14_d1f5ad57): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_asks_wechat_instead_of_phone (realism_21_ff361f63): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_no_contact_at_all (realism_25_e263a94f): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_says_phone_inconvenient_then_wechat (realism_31_1695538a): ["wechat_matches_user_stated: expected='abc123', actual='wxabc123'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_af488dbf): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_7147774c): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 partner_requirement_when_mentioned: 15 次
- 高频失败 location_truthy: 14 次
- 高频失败 location_matches_user_stated: 14 次
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 age_matches_user_stated: 3 次
- 高频失败 partner_requirement_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 occupation_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 7
- 通过率: 99.7%
- abuse_persistent_trolling_should_boundary (realism_5_698d511e): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=1']
- field_height_extract_cm (realism_94_f3d06027): ["low_priority_never_ask_height: expected='0', actual=1"]
- robustness_long_session_no_drift (realism_128_f8e16cf1): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2"]
- humanlike_no_premature_skip_without_explicit_refusal (realism_134_1886b124): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2"]
- humanlike_burst_input_preference_and_city_captured_first_reply (realism_135_09974109): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 medium_ask_limit_partner_requirement: 4 次
- 高频失败 no_consecutive_same_field_ask: 2 次
- 高频失败 low_priority_never_ask_height: 1 次
