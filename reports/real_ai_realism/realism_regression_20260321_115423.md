# 真实用户仿真回归报告

- 会话数: 36
- 总轮次: 76
- 总耗时(墙钟): 588.29s
- 累计会话耗时: 588.06s
- 失败检查数: 22
- 失败分布: turn=0, field=20, policy=2
- 时延 p95: 17.223s
- 时延 p99: 18.148s
- 模板化 Top1 占比: 5.3%
- Token: 143887 (调用 42 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.7%
- 字段提取综合通过率: 94.2%
- 字段精确匹配通过率: 92.4%
- 字段完整性通过率: 94.9%

## 拟人化收集质量

- 总检查数: 616
- 失败检查数: 2
- Turn 级失败: 0
- 策略级失败: 2
- 模板化 Top1 占比: 5.3%
- 时延 p95: 17.223s
- 时延 p99: 18.148s
- 高频策略失败 low_priority_never_ask_last_name: 1 次
- 高频策略失败 field_interleaving_quality: 1 次

## 字段提取准确性

- 总检查数: 345
- 失败检查数: 20
- 综合通过率: 94.2%
- 精确匹配检查数: 92
- 精确匹配失败数: 7
- 精确匹配通过率: 92.4%
- 完整性检查数: 253
- 完整性失败数: 13
- 完整性通过率: 94.9%
- 高频字段失败 location_truthy: 5 次
- 高频字段失败 location_matches_user_stated: 5 次
- 高频字段失败 unexpected_conversation_end: 4 次
- 高频字段失败 partner_requirement_when_mentioned: 4 次
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

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 50.0% (6/12)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 60.0% (3/5)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 37.5%
- 动作一致性分: 33.3%

## 隔离质量

- 会话数: 36
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.346
- p95 连续提问轮次: 2.75
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 5.6% (2/36)

## 提取诊断

- 字段冲突修复率: 0.0% (0/1)
- 证据链覆盖率: 72.2% (70/97)
- 失败类型 other: 8 次
- 失败类型 missed_stated_field: 6 次
- 失败类型 missing_extraction: 5 次
- 失败类型 wrong_value_or_normalization: 1 次

## 联系方式质量专项

- 联系方式成功率: 66.7% (4/6)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 11.2742s
- total: 7.3756s
- response_build: 0.759s
- rule_check: 0.1944s
- context_load: 0.0143s
- extract_collect: 0.0133s
- profile_load: 0.0086s
- profile_save: 0.0074s
- other: 0.0021s

## 意图分桶时延

- general: avg=7.9s p95=17.23s max=18.17s n=69
- fee: avg=2.263s p95=2.543s max=2.579s n=4
- reliability: avg=2.127s p95=2.242s max=2.245s n=3
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_f31d2167', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_9_a2173601', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_5b2000f4', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_5b2000f4', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_28daa39f', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_53f76612', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_5b2000f4', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_28daa39f', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_53f76612', 'expected': '深圳', 'actual': None, 'note': ''}
- partner_requirement_when_mentioned
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_5b2000f4', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_12_88c6847e', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_53f76612', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_0c01a7a6', 'expected': '30', 'actual': 36, 'note': ''}
- partner_requirement_matches_user_stated
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_53f76612', 'expected': '个成熟稳重的 有什么推荐吗', 'actual': None, 'note': ''}
### policy
- low_priority_never_ask_last_name
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_355974c3', 'expected': '0', 'actual': 1, 'note': ''}
- field_interleaving_quality
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_0c01a7a6', 'expected': '<=3 core asks streak', 'actual': 4, 'note': ''}

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.942 baseline=1.0
- latency_p95: current=17.223 baseline=14.91

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: FAIL
- P0失败数: 2
- P1失败数: 2
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.5 target=0.9
- [P0] baseline_degradation::extraction_pass_rate: value=0.942 target=1.0
- [P1] latency_p95_seconds: value=17.223 target=8.0
- [P1] field_stability_score: value=0.0 target=0.9

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_PASS
- ai_dialog_policy::field_interleaving_quality => COVERED_FAIL
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

- 持续退化指标: extraction_pass_rate, latency_p95
- 2026-03-21T11:54:23 humanlike=0.9968 extraction=0.942 latency_p95=17.223
- 2026-03-21T10:10:45 humanlike=0.9688 extraction=1.0 latency_p95=14.91
- 2026-03-21T03:37:43 humanlike=0.9772 extraction=0.9547 latency_p95=927.432
- 2026-03-21T02:43:05 humanlike=0.9801 extraction=0.9639 latency_p95=919.51
- 2026-03-20T21:13:42 humanlike=0.9759 extraction=0.9639 latency_p95=18.052
- 2026-03-20T21:11:07 humanlike=0.9688 extraction=1.0 latency_p95=16.596
- 2026-03-20T21:06:58 humanlike=0.9159 extraction=0.8736 latency_p95=1.748

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
- 失败项数量: 5
- 严重失败项数量: 1
- [major] latency_p95_seconds: value=17.223 target=8.0
- [critical] refusal_respect_rate: value=0.5 target=0.9
- [major] field_stability_score: value=0.0 target=0.9
- [major] baseline_degradation::extraction_pass_rate: value=0.942 target=1.0
- [major] baseline_degradation::latency_p95: value=17.223 target=14.91

## 模板化风险 Top10

- 4 次 (5.3%): `收到啦那你现在主要在哪个城市工作生活呀`
- 3 次 (4.0%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 2 次 (2.6%): `亲你是想说什么呢我刚才看到的消息有点奇怪呢`
- 2 次 (2.6%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 2 次 (2.6%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配知道啦那你这边是什么学历呀`
- 2 次 (2.6%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`

## 字段收集质量

- 总检查数: 345
- 失败检查数: 20
- 通过率: 94.2%
- contact_phone_and_wechat_same_turn (realism_6_f31d2167): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_divorce_incomplete_should_end (realism_9_a2173601): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_11_5b2000f4): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_age_under_limit (realism_12_88c6847e): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- field_partner_requirement_should_not_override_location (realism_19_28daa39f): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- field_partner_requirement_height_and_age_preference_should_not_end (realism_20_0c01a7a6): ["age_matches_user_stated: expected='30', actual=36"]
- humanlike_memory_reuse_preference (realism_26_53f76612): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- humanlike_answer_question_then_resume (realism_32_976e9dd7): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- robustness_age_boundary_just_adult (realism_34_6267524b): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- robustness_privacy_data_probe (realism_35_4a64fa88): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- 高频失败 location_truthy: 5 次
- 高频失败 location_matches_user_stated: 5 次
- 高频失败 unexpected_conversation_end: 4 次
- 高频失败 partner_requirement_when_mentioned: 4 次
- 高频失败 age_matches_user_stated: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 540
- 失败检查数: 2
- 通过率: 99.6%
- abuse_repeated_ack_should_not_loop_contact (realism_2_355974c3): ["low_priority_never_ask_last_name: expected='0', actual=1"]
- field_partner_requirement_height_and_age_preference_should_not_end (realism_20_0c01a7a6): ["field_interleaving_quality: expected='<=3 core asks streak', actual=4"]
- 高频失败 low_priority_never_ask_last_name: 1 次
- 高频失败 field_interleaving_quality: 1 次
