# 真实用户仿真回归报告

- 会话数: 36
- 总轮次: 76
- 总耗时(墙钟): 582.34s
- 累计会话耗时: 582.09s
- 失败检查数: 27
- 失败分布: turn=0, field=25, policy=2
- 时延 p95: 18.136s
- 时延 p99: 18.176s
- 模板化 Top1 占比: 5.3%
- Token: 133028 (调用 39 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.7%
- 字段提取综合通过率: 92.8%
- 字段精确匹配通过率: 91.3%
- 字段完整性通过率: 93.3%

## 拟人化收集质量

- 总检查数: 616
- 失败检查数: 2
- Turn 级失败: 0
- 策略级失败: 2
- 模板化 Top1 占比: 5.3%
- 时延 p95: 18.136s
- 时延 p99: 18.176s
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 345
- 失败检查数: 25
- 综合通过率: 92.8%
- 精确匹配检查数: 92
- 精确匹配失败数: 8
- 精确匹配通过率: 91.3%
- 完整性检查数: 253
- 完整性失败数: 17
- 完整性通过率: 93.3%
- 高频字段失败 partner_requirement_when_mentioned: 7 次
- 高频字段失败 location_truthy: 6 次
- 高频字段失败 location_matches_user_stated: 6 次
- 高频字段失败 unexpected_conversation_end: 4 次
- 高频字段失败 age_matches_user_stated: 1 次
- 高频字段失败 partner_requirement_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 66.7% (8/12)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/76)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 reliability: 模板多样性=66.7%, Top1=66.7%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 91.7% (11/12)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 20.0% (1/5)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 42.5%
- 动作一致性分: 50.0%

## 隔离质量

- 会话数: 36
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.241
- p95 连续提问轮次: 2.6
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 5.6% (2/36)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 74.2% (69/93)
- 失败类型 other: 11 次
- 失败类型 missed_stated_field: 7 次
- 失败类型 missing_extraction: 6 次
- 失败类型 wrong_value_or_normalization: 1 次

## 联系方式质量专项

- 联系方式成功率: 66.7% (4/6)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 11.1726s
- total: 7.2966s
- response_build: 0.7573s
- rule_check: 0.1808s
- context_load: 0.0131s
- extract_collect: 0.0125s
- profile_load: 0.0081s
- profile_save: 0.0071s
- other: 0.0019s

## 意图分桶时延

- general: avg=7.817s p95=18.143s max=18.185s n=69
- fee: avg=2.152s p95=2.423s max=2.453s n=4
- reliability: avg=2.186s p95=2.445s max=2.489s n=3
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_5_06f81197', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_ed3844df', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_17dde8ae', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_ed3844df', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_9_a83348a7', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_17dde8ae', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_17dde8ae', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_a6ee5963', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_697db7c3', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_17dde8ae', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_13_a6ee5963', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_697db7c3', 'expected': '深圳', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_959dbc48', 'expected': '90后', 'actual': 36, 'note': ''}
- partner_requirement_matches_user_stated
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_c95ee083', 'expected': '个成熟稳重的 有什么推荐吗', 'actual': None, 'note': ''}
### policy
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_959dbc48', 'expected': '<=1', 'actual': 2, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_959dbc48', 'expected': 0, 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- latency_p95: current=18.136 baseline=1.884

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 2
- P2失败数: 0
- [P1] latency_p95_seconds: value=18.136 target=8.0
- [P1] baseline_degradation::latency_p95: value=18.136 target=1.884

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

- 持续退化指标: latency_p95
- 2026-03-21T12:25:44 humanlike=0.9968 extraction=0.9275 latency_p95=18.136
- 2026-03-21T12:02:19 humanlike=0.9 extraction=0.9167 latency_p95=1.884
- 2026-03-21T12:01:22 humanlike=0.95 extraction=0.9167 latency_p95=2.223
- 2026-03-21T12:00:38 humanlike=0.95 extraction=0.9412 latency_p95=2.302
- 2026-03-21T11:59:45 humanlike=0.925 extraction=0.9412 latency_p95=2.181
- 2026-03-21T11:54:23 humanlike=0.9968 extraction=0.942 latency_p95=17.223
- 2026-03-21T10:10:45 humanlike=0.9688 extraction=1.0 latency_p95=14.91

## MQ补充检查

- covered=True pass=True
- total=8 passed=8 failed=0 skipped=0
- output_tail:
  - [4/8] RUN mq_ingest_invalid_payload_missing_platform_msg_id (mq)
  -        缺失 platformMsgId 的 payload 应返回 invalid_payload（需 ingest E2E）
  - [4/8] PASS mq_ingest_invalid_payload_missing_platform_msg_id (0.00s)
  - [5/8] RUN mq_ingest_empty_message_ignored (mq)
  -        空 message 应返回 ignored_empty（需 ingest E2E）
  - [5/8] PASS mq_ingest_empty_message_ignored (0.00s)
  - [6/8] RUN mq_ingest_invalid_timestamp_tolerated (mq)
  -        非法 timestamp 不应阻断入队（需 ingest E2E）
  - [6/8] PASS mq_ingest_invalid_timestamp_tolerated (0.01s)
  - [7/8] RUN mq_ingest_queue_full_backpressure (mq)

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 2
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=18.136 target=8.0
- [major] baseline_degradation::latency_p95: value=18.136 target=1.884

## 模板化风险 Top10

- 4 次 (5.3%): `收到啦那你现在主要在哪个城市工作生活呀`
- 3 次 (4.0%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 3 次 (4.0%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦你更看重对方哪几点呀我按你的要求来筛`
- 2 次 (2.6%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 2 次 (2.6%): `这个偏好我先记住啦你更看重对方哪几点呀我按你的要求来筛`
- 2 次 (2.6%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`

## 字段收集质量

- 总检查数: 345
- 失败检查数: 25
- 通过率: 92.8%
- contact_phone_then_wechat_prompt (realism_5_06f81197): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_6_ed3844df): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_divorce_incomplete_should_end (realism_9_a83348a7): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_11_17dde8ae): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_age_under_limit (realism_12_31231728): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- faq_priority_mediator (realism_13_a6ee5963): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- field_partner_requirement_should_not_override_location (realism_19_697db7c3): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- field_partner_requirement_height_and_age_preference_should_not_end (realism_20_959dbc48): ["age_matches_user_stated: expected='90后', actual=36"]
- humanlike_memory_reuse_preference (realism_26_c95ee083): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- humanlike_answer_question_then_resume (realism_32_798b9379): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- 高频失败 partner_requirement_when_mentioned: 7 次
- 高频失败 location_truthy: 6 次
- 高频失败 location_matches_user_stated: 6 次
- 高频失败 unexpected_conversation_end: 4 次
- 高频失败 age_matches_user_stated: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 540
- 失败检查数: 2
- 通过率: 99.6%
- field_partner_requirement_height_and_age_preference_should_not_end (realism_20_959dbc48): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 medium_ask_limit_partner_requirement: 1 次
- 高频失败 no_consecutive_same_field_ask: 1 次
