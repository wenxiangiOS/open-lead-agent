# 真实用户仿真回归报告

- 会话数: 34
- 总轮次: 279
- 总耗时(墙钟): 3045.49s
- 累计会话耗时: 3045.27s
- 失败检查数: 87
- 失败分布: turn=29, field=27, policy=31
- 时延 p95: 20.134s
- 时延 p99: 23.303s
- 模板化 Top1 占比: 10.0%
- Token: 1128281 (调用 255 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 92.9%
- 字段提取综合通过率: 94.6%
- 字段精确匹配通过率: 97.0%
- 字段完整性通过率: 92.9%

## 拟人化收集质量

- 总检查数: 842
- 失败检查数: 60
- Turn 级失败: 29
- 策略级失败: 31
- 模板化 Top1 占比: 10.0%
- 时延 p95: 20.134s
- 时延 p99: 23.303s
- 高频 turn 失败 contact_transition_abrupt: 26 次
- 高频 turn 失败 reply_too_fast_nonhuman: 1 次
- 高频 turn 失败 faq_not_answered_first: 1 次
- 高频 turn 失败 invalid_wechat_not_retried: 1 次
- 高频策略失败 field_interleaving_quality: 11 次
- 高频策略失败 scenario_assertion::profile_field_truthy: 6 次
- 高频策略失败 scenario_assertion::response_contains_any: 6 次
- 高频策略失败 scenario_assertion::profile_field_equals: 4 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 496
- 失败检查数: 27
- 综合通过率: 94.6%
- 精确匹配检查数: 202
- 精确匹配失败数: 6
- 精确匹配通过率: 97.0%
- 完整性检查数: 294
- 完整性失败数: 21
- 完整性通过率: 92.9%
- 高频字段失败 unexpected_conversation_end: 18 次
- 高频字段失败 phone_matches_user_stated: 1 次
- 高频字段失败 location_truthy: 1 次
- 高频字段失败 education_truthy: 1 次
- 高频字段失败 occupation_truthy: 1 次
- 高频字段失败 location_matches_user_stated: 1 次
- 高频字段失败 education_matches_user_stated: 1 次
- 高频字段失败 occupation_matches_user_stated: 1 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 marital_status_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 83.3% (10/12)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.4% (1/279)
- 联系方式突兀转场次数: 26
- 意图 fee: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 match: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 reliability: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/1)
- 拒绝后尊重率: 100.0% (8/8)
- 记忆回用准确率: 100.0% (4/4)
- 收尾自然度: 55.6% (10/18)
- 收尾链路 high_risk_ending: 通过率=0.0% (0/3)
- 收尾链路 normal_complete: 通过率=0.0% (0/15)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 55.9%
- 动作一致性分: 0.0%

## 隔离质量

- 会话数: 34
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 2.843
- p95 连续提问轮次: 7.0
- 最长连续提问轮次: 8
- 会话中出现>=3连问占比: 85.3% (29/34)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 73.0% (162/222)
- 失败类型 other: 18 次
- 失败类型 missed_stated_field: 4 次
- 失败类型 missing_extraction: 3 次
- 失败类型 wrong_value_or_normalization: 2 次

## 联系方式质量专项

- 联系方式成功率: 90.0% (27/30)
- 可收集场景成功率: 93.1% (27/29)
- 拒绝/防护场景通过率: 100.0% (1/1)
- 无效电话未重试: 0 次
- 无效微信未重试: 1 次

## 时延异常 Top20

- builtin_full_journey_short_answers_wechat#T8: 33.535s, user=`wx_cdyy95`

## 分阶段耗时均值

- ai_call: 11.0266s
- total: 10.54s
- response_build: 0.1023s
- context_load: 0.0121s
- profile_load: 0.0116s
- extract_collect: 0.0108s
- profile_save: 0.0076s
- other: 0.0035s

## 意图分桶时延

- general: avg=10.829s p95=20.134s max=33.535s n=270
- fee: avg=1.865s p95=1.972s max=1.983s n=3
- safety: avg=1.878s p95=1.961s max=1.973s n=3
- match: avg=1.849s p95=1.849s max=1.849s n=1
- photo: avg=1.798s p95=1.798s max=1.798s n=1
- reliability: avg=2.017s p95=2.017s max=2.017s n=1
- 秒回率(<1s): 0.4%
- FAQ秒回率(<1s): 0.0%
- Model秒回率(<1s): 0.0% (0/241)
- NonAI秒回率(<1s): 6.2% (1/16)
- 超慢回复率(>20s): 8.6%

## 失败样本（自动抽样）

### turn
- contact_transition_abrupt
  - {'turn': 6, 'user': 'it', 'assistant': '我大概了解得差不多了。留个手机号方便联系吗？', 'latency_s': 9.211, 'perf': {'profile_load': 0.0135, 'context_load': 0.0111, 'profile_save': 0.0105, 'ai_call': 9.1587, 'extract_collect': 0.0157, 'response_build': 0.0024, 'other': 0.0, 'total': 9.2111}}
  - {'turn': 6, 'user': '运营', 'assistant': '我大概了解得差不多了。留个手机号方便联系吗？', 'latency_s': 9.88, 'perf': {'profile_load': 0.0127, 'context_load': 0.0135, 'profile_save': 0.0098, 'ai_call': 9.8297, 'extract_collect': 0.0099, 'response_build': 0.0014, 'other': 0.0028, 'total': 9.8798}}
  - {'turn': 6, 'user': '产品', 'assistant': '我大概了解得差不多了。留个手机号方便联系吗？', 'latency_s': 16.314, 'perf': {'profile_load': 0.0145, 'context_load': 0.0091, 'profile_save': 0.0076, 'ai_call': 16.2709, 'extract_collect': 0.0125, 'response_build': 0.0014, 'other': 0.0, 'total': 16.3144}}
- reply_too_fast_nonhuman
  - {'turn': 9, 'user': '电话17612345678', 'assistant': '行，那先聊到这儿', 'latency_s': 0.025, 'perf': {'profile_load': 0.0062, 'context_load': 0.0076, 'other': 0.0116, 'total': 0.0254}}
- faq_not_answered_first
  - {'turn': 2, 'user': '怎么匹配', 'assistant': '一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定', 'latency_s': 1.849, 'perf': {'profile_load': 0.0079, 'context_load': 0.0146, 'profile_save': 0.0025, 'response_build': 1.8139, 'other': 0.0097, 'total': 1.8485}}
- invalid_wechat_not_retried
  - {'turn': 9, 'user': '微信wx_12', 'assistant': '你要是更习惯微信的话，留个常用微信就行，后面沟通也方便一些', 'latency_s': 17.448, 'perf': {'profile_load': 0.0128, 'context_load': 0.0122, 'profile_save': 0.007, 'ai_call': 17.3958, 'extract_collect': 0.0069, 'response_build': 0.0016, 'other': 0.0118, 'total': 17.4481}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'builtin_full_journey_wechat_complete_with_ai_ending', 'session_id': 'realism_4_4d882fea', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_phone_then_wechat_complete', 'session_id': 'realism_5_db10c727', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_wechat_then_phone_complete', 'session_id': 'realism_6_df7a5711', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- phone_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_wechat_then_phone_complete', 'session_id': 'realism_6_df7a5711', 'expected': '17612345678', 'actual': None, 'note': ''}
- location_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_2468ecf2', 'expected': 'non-empty', 'actual': None, 'note': ''}
- education_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_2468ecf2', 'expected': 'non-empty', 'actual': None, 'note': ''}
- occupation_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_2468ecf2', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_2468ecf2', 'expected': '深圳', 'actual': None, 'note': ''}
### policy
- field_interleaving_quality
  - {'scenario_id': 'builtin_full_journey_phone_complete', 'session_id': 'realism_1_ac04108d', 'expected': '<=3 core asks streak', 'actual': 4, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_phone_complete_with_ai_ending', 'session_id': 'realism_3_c1f94370', 'expected': '<=3 core asks streak', 'actual': 5, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_wechat_complete_with_ai_ending', 'session_id': 'realism_4_4d882fea', 'expected': '<=3 core asks streak', 'actual': 5, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_dd86861e', 'expected': 0, 'actual': 1, 'note': ''}
- scenario_assertion::profile_field_truthy
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_dd86861e', 'expected': None, 'actual': 'fail', 'note': 'profile.wechat 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_wechat_then_phone_complete', 'session_id': 'realism_6_df7a5711', 'expected': None, 'actual': 'fail', 'note': 'profile.phone 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_fee_then_complete', 'session_id': 'realism_16_5eb31bd8', 'expected': None, 'actual': 'fail', 'note': 'profile.sex 期望为真值，实际 None'}
- scenario_assertion::profile_field_equals
  - {'scenario_id': 'builtin_full_journey_phone_complete_with_ai_ending', 'session_id': 'realism_3_c1f94370', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
  - {'scenario_id': 'builtin_full_journey_contact_defer_then_end', 'session_id': 'realism_23_05eaf83b', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
  - {'scenario_id': 'builtin_full_journey_both_rejected_terminal_override', 'session_id': 'realism_24_4e1b5d0f', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
- scenario_assertion::response_contains_any
  - {'scenario_id': 'builtin_full_journey_boundary_once_then_complete', 'session_id': 'realism_18_b042e7d4', 'expected': ['理解', '了解', '方便', '主要是', '想多了解'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['理解', '了解', '方便', '主要是', '想多了解']，实际 '好，我们先不碰联系方式了，继续聊别的'"}
  - {'scenario_id': 'builtin_full_journey_human_or_ai_then_complete', 'session_id': 'realism_21_935ca2aa', 'expected': ['现在', '先', '沟通', '帮助', '了解'], 'actual': 'fail', 'note': "turn=2 需要包含任一关键词 ['现在', '先', '沟通', '帮助', '了解']，实际 '这个你不用纠结哦，我主要是帮大家对接交友相关的事宜，你有任何想问的或者需求都可以告诉我哒。 对了，你方便说下自己的年龄吗？'"}
  - {'scenario_id': 'builtin_full_journey_why_keep_asking_then_complete', 'session_id': 'realism_22_d94edd07', 'expected': ['理解', '主要是', '更好', '匹配', '了解'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['理解', '主要是', '更好', '匹配', '了解']，实际 '对，刚才那句是我接得不够好。 这个点我先收住，你想继续聊什么都行'"}

## 基线对比

- 检测到退化指标：
- latency_p95: current=20.134 baseline=16.339

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 2
- P2失败数: 0
- [P1] latency_p95_seconds: value=20.134 target=8.0
- [P1] baseline_degradation::latency_p95: value=20.134 target=16.339

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_FAIL
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_FAIL
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_FAIL
- message_queue_design::mq_ingest_regression => COVERED_PASS (failed=0)

## 根因分桶

- contact_collection: 27
- policy_or_routing: 12
- prompt_or_style: 0
- extraction: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: latency_p95
- 2026-03-26T04:54:28 humanlike=0.9287 extraction=0.9456 latency_p95=20.134
- 2026-03-25T13:53:00 humanlike=0.9235 extraction=0.9274 latency_p95=16.339
- 2026-03-25T11:46:35 humanlike=0.8589 extraction=0.9443 latency_p95=11.891
- 2026-03-24T14:32:37 humanlike=0.992 extraction=0.9592 latency_p95=19.942
- 2026-03-24T13:39:39 humanlike=0.9896 extraction=0.9347 latency_p95=2.56
- 2026-03-24T13:04:29 humanlike=0.9896 extraction=0.962 latency_p95=17.98
- 2026-03-21T19:06:24 humanlike=0.9983 extraction=0.9667 latency_p95=17.478

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
  - 最长耗时: 0.05s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 2
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=20.134 target=8.0
- [major] baseline_degradation::latency_p95: value=20.134 target=16.339

## 模板化风险 Top10

- 28 次 (10.0%): `我明白你要是担心电话不方便我就再轻问一次留个常用手机号就行方便后面联系你`
- 15 次 (5.4%): `我大概了解得差不多了留个手机号方便联系吗`
- 15 次 (5.4%): `这样的话留个手机号方便联系吗`
- 11 次 (3.9%): `那你现在主要在哪个城市生活`
- 11 次 (3.9%): `对了你这边大概是什么学历呀另外你这边找对象时更看重对方哪一点`
- 10 次 (3.6%): `那你现在是在什么城市`
- 9 次 (3.2%): `你好呀方便说下你是男生还是女生吗`
- 8 次 (2.9%): `那工作这块你现在主要在哪个方向另外你这边找对象时更看重对方哪一点`
- 8 次 (2.9%): `那平时是做什么工作的另外你这边找对象时更看重对方哪一点`
- 6 次 (2.1%): `那学历这块你方便说下吗另外你这边找对象时更看重对方哪一点`

## 字段收集质量

- 总检查数: 496
- 失败检查数: 27
- 通过率: 94.6%
- builtin_full_journey_wechat_complete_with_ai_ending (realism_4_4d882fea): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_phone_then_wechat_complete (realism_5_db10c727): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_wechat_then_phone_complete (realism_6_df7a5711): ["phone_matches_user_stated: expected='17612345678', actual=None", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_short_answers_wechat (realism_8_645ca074): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_faq_then_complete (realism_10_782323c3): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_fee_first_then_complete (realism_11_8d8aea68): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_match_process_then_complete (realism_13_727612fd): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_photo_request_then_complete (realism_15_5771938b): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_mixed_info_and_privacy_then_complete (realism_17_2468ecf2): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- builtin_full_journey_boundary_once_then_complete (realism_18_b042e7d4): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 18 次
- 高频失败 phone_matches_user_stated: 1 次
- 高频失败 location_truthy: 1 次
- 高频失败 education_truthy: 1 次
- 高频失败 occupation_truthy: 1 次
- 高频失败 location_matches_user_stated: 1 次
- 高频失败 education_matches_user_stated: 1 次
- 高频失败 occupation_matches_user_stated: 1 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 marital_status_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 585
- 失败检查数: 31
- 通过率: 94.7%
- builtin_full_journey_phone_complete (realism_1_ac04108d): ["field_interleaving_quality: expected='<=3 core asks streak', actual=4"]
- builtin_full_journey_wechat_complete (realism_2_dd86861e): ['no_consecutive_same_field_ask: expected=0, actual=1', 'profile_field_truthy: profile.wechat 期望为真值，实际 None']
- builtin_full_journey_phone_complete_with_ai_ending (realism_3_c1f94370): ["field_interleaving_quality: expected='<=3 core asks streak', actual=5", 'profile_field_equals: profile.conversation_ended 期望 True，实际 False', "final_response_contains_any: final_response 需要包含任一关键词 ['先聊到这儿', '祝你', '顺利', '继续推进', '到这里']，实际 '好，这个手机号我知道了，后续有合适的匹配进展会及时联系你的~'"]
- builtin_full_journey_wechat_complete_with_ai_ending (realism_4_4d882fea): ["field_interleaving_quality: expected='<=3 core asks streak', actual=5"]
- builtin_full_journey_wechat_then_phone_complete (realism_6_df7a5711): ['profile_field_truthy: profile.phone 期望为真值，实际 None']
- builtin_full_journey_short_answers_wechat (realism_8_645ca074): ["field_interleaving_quality: expected='<=3 core asks streak', actual=5"]
- builtin_full_journey_faq_then_complete (realism_10_782323c3): ["field_interleaving_quality: expected='<=3 core asks streak', actual=4"]
- builtin_full_journey_privacy_then_complete (realism_12_004dee29): ["field_interleaving_quality: expected='<=3 core asks streak', actual=4"]
- builtin_full_journey_mixed_info_and_fee_then_complete (realism_16_5eb31bd8): ['profile_field_truthy: profile.sex 期望为真值，实际 None']
- builtin_full_journey_mixed_info_and_privacy_then_complete (realism_17_2468ecf2): ['profile_field_truthy: profile.location 期望为真值，实际 None', 'profile_field_truthy: profile.education 期望为真值，实际 None', 'profile_field_truthy: profile.occupation 期望为真值，实际 None']
- 高频失败 field_interleaving_quality: 11 次
- 高频失败 scenario_assertion::profile_field_truthy: 6 次
- 高频失败 scenario_assertion::response_contains_any: 6 次
- 高频失败 scenario_assertion::profile_field_equals: 4 次
- 高频失败 no_consecutive_same_field_ask: 1 次
