# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2340.63s
- 累计会话耗时: 2339.64s
- 失败检查数: 51
- 失败分布: turn=0, field=47, policy=4
- 时延 p95: 17.478s
- 时延 p99: 20.152s
- 模板化 Top1 占比: 4.1%
- Token: 574873 (调用 166 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.8%
- 字段提取综合通过率: 96.7%
- 字段精确匹配通过率: 95.2%
- 字段完整性通过率: 97.2%

## 拟人化收集质量

- 总检查数: 2358
- 失败检查数: 4
- Turn 级失败: 0
- 策略级失败: 4
- 模板化 Top1 占比: 4.1%
- 时延 p95: 17.478s
- 时延 p99: 20.152s
- 高频策略失败 medium_ask_limit_partner_requirement: 3 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 47
- 综合通过率: 96.7%
- 精确匹配检查数: 397
- 精确匹配失败数: 19
- 精确匹配通过率: 95.2%
- 完整性检查数: 1016
- 完整性失败数: 28
- 完整性通过率: 97.2%
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 partner_requirement_when_mentioned: 10 次
- 高频字段失败 location_truthy: 6 次
- 高频字段失败 location_matches_user_stated: 6 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 partner_requirement_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 age_matches_user_stated: 2 次
- 高频字段失败 occupation_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 68.2% (15/22)
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
- 拒绝后尊重率: 91.3% (21/23)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 19.1% (4/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 43.8%
- 动作一致性分: 75.0%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.329
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 5
- 会话中出现>=3连问占比: 5.1% (7/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/1)
- 证据链覆盖率: 70.0% (320/457)
- 失败类型 other: 21 次
- 失败类型 missed_stated_field: 12 次
- 失败类型 wrong_value_or_normalization: 7 次
- 失败类型 missing_extraction: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 11.6359s
- total: 7.5747s
- response_build: 0.6717s
- rule_check: 0.1455s
- context_load: 0.0142s
- extract_collect: 0.014s
- profile_load: 0.0093s
- profile_save: 0.008s
- other: 0.0017s

## 意图分桶时延

- general: avg=7.864s p95=17.566s max=21.696s n=280
- fee: avg=2.06s p95=2.354s max=2.401s n=7
- reliability: avg=2.327s p95=2.51s max=2.515s n=4
- match: avg=2.038s p95=2.054s max=2.056s n=2
- photo: avg=2.214s p95=2.214s max=2.214s n=1
- safety: avg=2.452s p95=2.452s max=2.452s n=1
- 秒回率(<1s): 6.1%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 3.0%

## 失败样本（自动抽样）

### turn
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_50050daf', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_user_says_no_contact_at_all', 'session_id': 'realism_25_8e43fb36', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_non_hk_wechat_first_then_phone', 'session_id': 'realism_30_786a275b', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_5567da56', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_98991508', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_2163a448', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_496f77f2', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_d3f3eb43', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_1df09526', 'expected': '17688654321', 'actual': None, 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_62566326', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_6319f966', 'expected': '离婚', 'actual': '离异（手续未办妥）', 'note': ''}
  - {'scenario_id': 'safety_high_risk_legal_query_guard', 'session_id': 'realism_129_dcebe818', 'expected': '离婚', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_0da419d5', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'safety_conflict_info_should_confirm', 'session_id': 'realism_132_10588d30', 'expected': '35', 'actual': 36, 'note': ''}
### policy
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_a54fbae3', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_19fd3013', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_134_55b02bda', 'expected': '<=1', 'actual': 2, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_a54fbae3', 'expected': 0, 'actual': 2, 'note': ''}

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.9667 baseline=0.9689

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 3
- P2失败数: 0
- [P1] latency_p95_seconds: value=17.478 target=8.0
- [P1] field_stability_score: value=0.0 target=0.9
- [P1] baseline_degradation::extraction_pass_rate: value=0.9667 target=0.9689

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

- policy_or_routing: 1
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: extraction_pass_rate
- 2026-03-21T19:06:24 humanlike=0.9983 extraction=0.9667 latency_p95=17.478
- 2026-03-21T16:29:29 humanlike=0.9979 extraction=0.9689 latency_p95=17.714
- 2026-03-21T15:47:56 humanlike=0.9357 extraction=0.8889 latency_p95=2.065
- 2026-03-21T15:32:36 humanlike=0.9983 extraction=0.9384 latency_p95=14.141
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213
- 2026-03-21T13:23:01 humanlike=0.997 extraction=0.9512 latency_p95=16.583
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404

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
  - 总耗时: 0.26s
  - 平均耗时: 0.013s
  - 最长耗时: 0.04s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 3
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=17.478 target=8.0
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::extraction_pass_rate: value=0.9667 target=0.9689

## 模板化风险 Top10

- 12 次 (4.1%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配好呀这个条件我先记住收下后面会按这个方向优先筛选合适的我尽快同步你`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 8 次 (2.7%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦我会按这个方向优先筛选后面有合适的第一时间跟你同步`
- 8 次 (2.7%): `好哒那想问下你今年多大呀`
- 6 次 (2.0%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 6 次 (2.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配收到这个偏好我先记住并整理好后面我按这个方向优先匹配有进展就及时告诉你`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 6 次 (2.0%): `我先记下来啦顺带问下你是男生还是女生呀`
- 5 次 (1.7%): `好呀这个条件我先记住收下后面会按这个方向优先筛选合适的我尽快同步你`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 47
- 通过率: 96.7%
- contact_phone_then_wechat_prompt (realism_6_50050daf): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_7_5567da56): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_refused_then_user_provides_wechat (realism_11_98991508): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_asks_wechat_instead_of_phone (realism_21_2163a448): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_no_contact_at_all (realism_25_8e43fb36): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_non_hk_wechat_first_then_phone (realism_30_786a275b): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_says_phone_inconvenient_then_wechat (realism_31_496f77f2): ["wechat_matches_user_stated: expected='abc123', actual='wxabc123'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_d3f3eb43): ["wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_657f6bbc): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_too_short_should_retry (realism_40_63425f94): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 partner_requirement_when_mentioned: 10 次
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
- abuse_persistent_trolling_should_boundary (realism_5_a54fbae3): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=2']
- robustness_long_session_no_drift (realism_128_19fd3013): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2"]
- humanlike_no_premature_skip_without_explicit_refusal (realism_134_55b02bda): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2"]
- 高频失败 medium_ask_limit_partner_requirement: 3 次
- 高频失败 no_consecutive_same_field_ask: 1 次
