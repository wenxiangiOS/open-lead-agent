# 真实用户仿真回归报告

- 会话数: 36
- 总轮次: 76
- 总耗时(墙钟): 593.09s
- 累计会话耗时: 592.86s
- 失败检查数: 18
- 失败分布: turn=0, field=18, policy=0
- 时延 p95: 16.404s
- 时延 p99: 18.133s
- 模板化 Top1 占比: 5.3%
- Token: 139355 (调用 41 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 100.0%
- 字段提取综合通过率: 94.8%
- 字段精确匹配通过率: 93.5%
- 字段完整性通过率: 95.3%

## 拟人化收集质量

- 总检查数: 616
- 失败检查数: 0
- Turn 级失败: 0
- 策略级失败: 0
- 模板化 Top1 占比: 5.3%
- 时延 p95: 16.404s
- 时延 p99: 18.133s

## 字段提取准确性

- 总检查数: 345
- 失败检查数: 18
- 综合通过率: 94.8%
- 精确匹配检查数: 92
- 精确匹配失败数: 6
- 精确匹配通过率: 93.5%
- 完整性检查数: 253
- 完整性失败数: 12
- 完整性通过率: 95.3%
- 高频字段失败 partner_requirement_when_mentioned: 4 次
- 高频字段失败 unexpected_conversation_end: 4 次
- 高频字段失败 location_truthy: 4 次
- 高频字段失败 location_matches_user_stated: 4 次
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
- 收尾自然度: 40.0% (2/5)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 35.0%
- 动作一致性分: 33.3%

## 隔离质量

- 会话数: 36
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.192
- p95 连续提问轮次: 2.0
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 2.8% (1/36)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 72.5% (71/98)
- 失败类型 other: 8 次
- 失败类型 missing_extraction: 4 次
- 失败类型 missed_stated_field: 4 次
- 失败类型 wrong_value_or_normalization: 2 次

## 联系方式质量专项

- 联系方式成功率: 66.7% (4/6)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 11.3217s
- total: 7.4389s
- response_build: 0.8138s
- rule_check: 0.1817s
- context_load: 0.013s
- extract_collect: 0.0129s
- profile_load: 0.0078s
- profile_save: 0.0074s
- other: 0.0018s

## 意图分桶时延

- general: avg=7.965s p95=17.082s max=18.134s n=69
- fee: avg=2.281s p95=2.408s max=2.411s n=4
- reliability: avg=2.212s p95=2.29s max=2.3s n=3
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_5_f6d9a2b3', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_after_wechat_rejection_should_not_end', 'session_id': 'realism_8_c6e08517', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_12_3fd7462b', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_6_7e8f326b', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_9_6a60be3e', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_11_b4a58587', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_ed0d5230', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_reception_hesitant_user', 'session_id': 'realism_21_fd2f3c21', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_answer_question_then_resume', 'session_id': 'realism_32_5dcb1620', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_19_ed0d5230', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_reception_hesitant_user', 'session_id': 'realism_21_fd2f3c21', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'humanlike_answer_question_then_resume', 'session_id': 'realism_32_5dcb1620', 'expected': '深圳', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_20_1a836786', 'expected': '90后', 'actual': 36, 'note': ''}
- partner_requirement_matches_user_stated
  - {'scenario_id': 'humanlike_memory_reuse_preference', 'session_id': 'realism_26_71331c25', 'expected': '个成熟稳重的 有什么推荐吗', 'actual': '成熟稳重', 'note': ''}
### policy

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.9478 baseline=1.0
- latency_p95: current=16.404 baseline=2.123

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 3
- P2失败数: 0
- [P1] latency_p95_seconds: value=16.404 target=8.0
- [P1] baseline_degradation::extraction_pass_rate: value=0.9478 target=1.0
- [P1] baseline_degradation::latency_p95: value=16.404 target=2.123

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_PASS
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => COVERED_PASS (failed=0)

## 根因分桶

- prompt_or_style: 0
- policy_or_routing: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: extraction_pass_rate, latency_p95
- 2026-03-21T12:49:35 humanlike=1.0 extraction=0.9478 latency_p95=16.404
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107
- 2026-03-21T12:32:17 humanlike=0.9 extraction=0.9167 latency_p95=1.815
- 2026-03-21T12:31:43 humanlike=0.9 extraction=0.9167 latency_p95=1.758

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
- 失败项数量: 3
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=16.404 target=8.0
- [major] baseline_degradation::extraction_pass_rate: value=0.9478 target=1.0
- [major] baseline_degradation::latency_p95: value=16.404 target=2.123

## 模板化风险 Top10

- 4 次 (5.3%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配这个偏好我先记住啦我先按这个方向给你筛后面有合适的我优先同步你`
- 4 次 (5.3%): `这个偏好我先记住啦我先按这个方向给你筛后面有合适的我优先同步你`
- 4 次 (5.3%): `收到啦那你现在主要在哪个城市工作生活呀`
- 3 次 (4.0%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 3 次 (4.0%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 2 次 (2.6%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 2 次 (2.6%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 2 次 (2.6%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 2 次 (2.6%): `这个不方便直接给你涉及隐私和合规我们这边都要按流程保护双方信息`

## 字段收集质量

- 总检查数: 345
- 失败检查数: 18
- 通过率: 94.8%
- contact_phone_then_wechat_prompt (realism_5_f6d9a2b3): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_6_7e8f326b): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_after_wechat_rejection_should_not_end (realism_8_c6e08517): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- ending_divorce_incomplete_should_end (realism_9_6a60be3e): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_11_b4a58587): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_age_under_limit (realism_12_3fd7462b): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- field_partner_requirement_should_not_override_location (realism_19_ed0d5230): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- field_partner_requirement_height_and_age_preference_should_not_end (realism_20_1a836786): ["age_matches_user_stated: expected='90后', actual=36"]
- humanlike_reception_hesitant_user (realism_21_fd2f3c21): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None"]
- humanlike_memory_reuse_preference (realism_26_71331c25): ["partner_requirement_matches_user_stated: expected='个成熟稳重的 有什么推荐吗', actual='成熟稳重'"]
- 高频失败 partner_requirement_when_mentioned: 4 次
- 高频失败 unexpected_conversation_end: 4 次
- 高频失败 location_truthy: 4 次
- 高频失败 location_matches_user_stated: 4 次
- 高频失败 age_matches_user_stated: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 540
- 失败检查数: 0
- 通过率: 100.0%
