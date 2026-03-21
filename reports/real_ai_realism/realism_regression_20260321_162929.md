# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2376.28s
- 累计会话耗时: 2375.31s
- 失败检查数: 49
- 失败分布: turn=1, field=44, policy=4
- 时延 p95: 17.714s
- 时延 p99: 24.0s
- 模板化 Top1 占比: 4.4%
- Token: 583605 (调用 168 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.8%
- 字段提取综合通过率: 96.9%
- 字段精确匹配通过率: 95.2%
- 字段完整性通过率: 97.5%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 5
- Turn 级失败: 1
- 策略级失败: 4
- 模板化 Top1 占比: 4.4%
- 时延 p95: 17.714s
- 时延 p99: 24.0s
- 高频 turn 失败 reply_too_fast_nonhuman: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 3 次
- 高频策略失败 income_question_soft_tone: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 44
- 综合通过率: 96.9%
- 精确匹配检查数: 397
- 精确匹配失败数: 19
- 精确匹配通过率: 95.2%
- 完整性检查数: 1016
- 完整性失败数: 25
- 完整性通过率: 97.5%
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 partner_requirement_when_mentioned: 7 次
- 高频字段失败 location_truthy: 6 次
- 高频字段失败 location_matches_user_stated: 6 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 partner_requirement_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 age_matches_user_stated: 2 次
- 高频字段失败 occupation_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 72.7% (16/22)
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
- 拒绝后尊重率: 87.0% (20/23)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 19.1% (4/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 38.0%
- 动作一致性分: 50.0%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.207
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 4.3% (6/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/1)
- 证据链覆盖率: 69.6% (320/460)
- 失败类型 other: 18 次
- 失败类型 missed_stated_field: 12 次
- 失败类型 wrong_value_or_normalization: 7 次
- 失败类型 missing_extraction: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 11.8744s
- total: 7.6964s
- response_build: 0.6638s
- rule_check: 0.1323s
- extract_collect: 0.015s
- context_load: 0.0137s
- profile_load: 0.0097s
- profile_save: 0.0083s
- other: 0.0016s

## 意图分桶时延

- general: avg=7.993s p95=17.982s max=25.157s n=280
- fee: avg=2.149s p95=2.413s max=2.417s n=7
- reliability: avg=2.315s p95=2.503s max=2.515s n=4
- match: avg=1.96s p95=2.136s max=2.156s n=2
- photo: avg=1.827s p95=1.827s max=1.827s n=1
- safety: avg=2.323s p95=2.323s max=2.323s n=1
- 秒回率(<1s): 7.1%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 2.7%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': '喜欢高高瘦瘦', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.739, 'perf': {'profile_load': 0.0079, 'context_load': 0.0331, 'rule_check': 0.0081, 'profile_save': 0.0044, 'ai_call': 0.6827, 'extract_collect': 0.0024, 'response_build': 0.0005, 'other': 0.0, 'total': 0.7387}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_da5419fb', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_b69e8424', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_24acda0b', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_wechat_only_then_phone_refusal', 'session_id': 'realism_13_df28130d', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_user_says_no_contact_at_all', 'session_id': 'realism_25_8f55af02', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_45_b184335d', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_b497a184', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_e2e9277a', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_920869cc', 'expected': '17688654321', 'actual': None, 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_8db1242c', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_f6e6629b', 'expected': '离婚', 'actual': '离异，手续未办完', 'note': ''}
  - {'scenario_id': 'safety_high_risk_legal_query_guard', 'session_id': 'realism_129_2c759b76', 'expected': '离婚', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_b8f35b17', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'safety_conflict_info_should_confirm', 'session_id': 'realism_132_67a20fda', 'expected': '35', 'actual': 36, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_52d1c1be', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'humanlike_ask_limit_core_field_2_times', 'session_id': 'realism_115_00a98128', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_6b357bf9', 'expected': 0, 'actual': 1, 'note': ''}
- income_question_soft_tone
  - {'scenario_id': 'field_income_extract_monthly', 'session_id': 'realism_95_579feef6', 'expected': 0, 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- latency_p95: current=17.714 baseline=2.065

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 3
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.8696 target=0.9
- [P1] latency_p95_seconds: value=17.714 target=8.0
- [P1] field_stability_score: value=0.0 target=0.9
- [P1] baseline_degradation::latency_p95: value=17.714 target=2.065

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

- policy_or_routing: 3
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: latency_p95
- 2026-03-21T16:29:29 humanlike=0.9979 extraction=0.9689 latency_p95=17.714
- 2026-03-21T15:47:56 humanlike=0.9357 extraction=0.8889 latency_p95=2.065
- 2026-03-21T15:32:36 humanlike=0.9983 extraction=0.9384 latency_p95=14.141
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123

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
  - 总耗时: 0.25s
  - 平均耗时: 0.013s
  - 最长耗时: 0.05s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 4
- 严重失败项数量: 1
- [major] latency_p95_seconds: value=17.714 target=8.0
- [critical] refusal_respect_rate: value=0.8696 target=0.9
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::latency_p95: value=17.714 target=2.065

## 模板化风险 Top10

- 13 次 (4.4%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配收到这个偏好我先记住并整理好后面我按这个方向优先匹配有进展就及时告诉你`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 8 次 (2.7%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配好呀这个条件我先记住收下后面会按这个方向优先筛选合适的我尽快同步你`
- 7 次 (2.4%): `我先记下来啦顺带问下你是男生还是女生呀`
- 7 次 (2.4%): `好哒那想问下你今年多大呀`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 6 次 (2.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦我会按这个方向优先筛选后面有合适的第一时间跟你同步`
- 5 次 (1.7%): `收到这个偏好我先记住并整理好后面我按这个方向优先匹配有进展就及时告诉你`
- 5 次 (1.7%): `这个偏好我先记住啦我会按这个方向优先筛选后面有合适的第一时间跟你同步`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 44
- 通过率: 96.9%
- contact_phone_and_wechat_same_turn (realism_7_da5419fb): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_refused_then_user_provides_wechat (realism_11_b69e8424): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_only_then_phone_refusal (realism_13_df28130d): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_asks_wechat_instead_of_phone (realism_21_24acda0b): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_no_contact_at_all (realism_25_8f55af02): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_says_phone_inconvenient_then_wechat (realism_31_b497a184): ["wechat_matches_user_stated: expected='abc123', actual='wxabc123'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_e2e9277a): ["wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_79e15158): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_too_long_should_retry (realism_41_920869cc): ["phone_matches_user_stated: expected='17688654321', actual=None"]
- ending_divorce_incomplete_should_end (realism_42_d84d4156): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 partner_requirement_when_mentioned: 7 次
- 高频失败 location_truthy: 6 次
- 高频失败 location_matches_user_stated: 6 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 partner_requirement_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 age_matches_user_stated: 2 次
- 高频失败 occupation_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 4
- 通过率: 99.8%
- abuse_persistent_trolling_should_boundary (realism_5_52d1c1be): ['no_consecutive_same_field_ask: expected=0, actual=1']
- field_income_extract_monthly (realism_95_579feef6): ['income_question_soft_tone: expected=0, actual=1']
- humanlike_ask_limit_core_field_2_times (realism_115_00a98128): ['no_consecutive_same_field_ask: expected=0, actual=1']
- robustness_long_session_no_drift (realism_128_6b357bf9): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 3 次
- 高频失败 income_question_soft_tone: 1 次
