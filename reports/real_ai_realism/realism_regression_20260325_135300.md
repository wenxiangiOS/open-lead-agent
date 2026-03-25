# 真实用户仿真回归报告

- 会话数: 34
- 总轮次: 279
- 总耗时(墙钟): 1153.71s
- 累计会话耗时: 1153.5s
- 失败检查数: 102
- 失败分布: turn=10, field=36, policy=56
- 时延 p95: 16.339s
- 时延 p99: 20.31s
- 模板化 Top1 占比: 12.2%
- Token: 175388 (调用 61 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 92.3%
- 字段提取综合通过率: 92.7%
- 字段精确匹配通过率: 97.0%
- 字段完整性通过率: 89.8%

## 拟人化收集质量

- 总检查数: 863
- 失败检查数: 66
- Turn 级失败: 10
- 策略级失败: 56
- 模板化 Top1 占比: 12.2%
- 时延 p95: 16.339s
- 时延 p99: 20.31s
- 高频 turn 失败 invalid_wechat_not_retried: 9 次
- 高频 turn 失败 faq_not_answered_first: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 27 次
- 高频策略失败 medium_ask_limit_partner_requirement: 11 次
- 高频策略失败 scenario_assertion::profile_field_truthy: 6 次
- 高频策略失败 core_ask_limit_age: 5 次
- 高频策略失败 scenario_assertion::response_contains_any: 4 次
- 高频策略失败 scenario_assertion::profile_field_equals: 2 次

## 字段提取准确性

- 总检查数: 496
- 失败检查数: 36
- 综合通过率: 92.7%
- 精确匹配检查数: 202
- 精确匹配失败数: 6
- 精确匹配通过率: 97.0%
- 完整性检查数: 294
- 完整性失败数: 30
- 完整性通过率: 89.8%
- 高频字段失败 unexpected_conversation_end: 27 次
- 高频字段失败 occupation_matches_user_stated: 2 次
- 高频字段失败 location_truthy: 1 次
- 高频字段失败 education_truthy: 1 次
- 高频字段失败 occupation_truthy: 1 次
- 高频字段失败 location_matches_user_stated: 1 次
- 高频字段失败 education_matches_user_stated: 1 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 marital_status_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 83.3% (10/12)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/279)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 match: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 reliability: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/1)
- 拒绝后尊重率: 100.0% (8/8)
- 记忆回用准确率: 100.0% (8/8)
- 收尾自然度: 85.2% (23/27)
- 收尾链路 already_ended: 通过率=0.0% (0/1)
- 收尾链路 high_risk_ending: 通过率=0.0% (0/3)
- 收尾链路 normal_complete: 通过率=0.0% (0/23)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 78.8%
- 动作一致性分: 0.0%

## 隔离质量

- 会话数: 34
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 2.984
- p95 连续提问轮次: 6.0
- 最长连续提问轮次: 6
- 会话中出现>=3连问占比: 94.1% (32/34)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 73.0% (162/222)
- 失败类型 other: 27 次
- 失败类型 wrong_value_or_normalization: 3 次
- 失败类型 missing_extraction: 3 次
- 失败类型 missed_stated_field: 3 次

## 联系方式质量专项

- 联系方式成功率: 86.7% (26/30)
- 可收集场景成功率: 89.7% (26/29)
- 拒绝/防护场景通过率: 100.0% (1/1)
- 无效电话未重试: 0 次
- 无效微信未重试: 9 次

## 时延异常 Top20

- builtin_full_journey_authenticity_then_complete#T9: 25.839s, user=`wx_auth_ok90`

## 分阶段耗时均值

- ai_call: 13.5474s
- total: 3.7646s
- response_build: 1.5897s
- context_load: 0.0122s
- profile_load: 0.0106s
- extract_collect: 0.0099s
- profile_save: 0.0061s
- other: 0.0026s

## 意图分桶时延

- general: avg=3.823s p95=16.855s max=25.839s n=270
- fee: avg=1.887s p95=2.134s max=2.176s n=3
- safety: avg=2.046s p95=2.234s max=2.258s n=3
- match: avg=2.051s p95=2.051s max=2.051s n=1
- photo: avg=2.079s p95=2.079s max=2.079s n=1
- reliability: avg=2.149s p95=2.149s max=2.149s n=1
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- Model秒回率(<1s): 0.0% (0/34)
- NonAI秒回率(<1s): 0.0% (0/244)
- 超慢回复率(>20s): 1.4%

## 失败样本（自动抽样）

### turn
- invalid_wechat_not_retried
  - {'turn': 8, 'user': 'wx_ling233', 'assistant': '好，我知道了你的微信啦，后续有适合你的匹配人选我们会你，祝你早日在广州遇到合拍的另一半呀', 'latency_s': 17.724, 'perf': {'profile_load': 0.0118, 'context_load': 0.01, 'profile_save': 0.0144, 'ai_call': 17.6719, 'extract_collect': 0.0145, 'response_build': 0.001, 'other': 0.0, 'total': 17.7236}}
  - {'turn': 8, 'user': 'wx_hzending95', 'assistant': '好，我已经记下你的微信啦，后续匹配到杭州本地适合你的优质单身人选会及时跟你同步，祝你早日遇到双向奔赴的好缘分呀', 'latency_s': 16.103, 'perf': {'profile_load': 0.0094, 'context_load': 0.0121, 'profile_save': 0.0075, 'ai_call': 16.0585, 'extract_collect': 0.0078, 'response_build': 0.0023, 'other': 0.0053, 'total': 16.103}}
  - {'turn': 8, 'user': 'wx_cdyy95', 'assistant': '好，我已经把你发的微信号记下来啦，后续有适合你的优质匹配资源会你，祝你早日在成都遇到合拍的另一半呀', 'latency_s': 19.56, 'perf': {'profile_load': 0.0113, 'context_load': 0.0118, 'profile_save': 0.0107, 'ai_call': 19.5127, 'extract_collect': 0.0107, 'response_build': 0.0008, 'other': 0.0017, 'total': 19.5598}}
- faq_not_answered_first
  - {'turn': 2, 'user': '怎么匹配', 'assistant': '一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定', 'latency_s': 2.051, 'perf': {'profile_load': 0.0033, 'context_load': 0.0118, 'response_build': 2.0259, 'other': 0.0103, 'total': 2.0513}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'builtin_full_journey_phone_complete', 'session_id': 'realism_1_8368acac', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_e0d9d423', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_phone_complete_with_ai_ending', 'session_id': 'realism_3_d5804b74', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- occupation_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_dense_profile_then_phone', 'session_id': 'realism_9_5d747087', 'expected': '产品', 'actual': '做产品', 'note': ''}
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': '产品', 'actual': None, 'note': ''}
- location_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': 'non-empty', 'actual': None, 'note': ''}
- education_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': 'non-empty', 'actual': None, 'note': ''}
- occupation_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': '深圳', 'actual': None, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'builtin_full_journey_phone_complete', 'session_id': 'realism_1_8368acac', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_e0d9d423', 'expected': 0, 'actual': 2, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_phone_complete_with_ai_ending', 'session_id': 'realism_3_d5804b74', 'expected': 0, 'actual': 2, 'note': ''}
- core_ask_limit_age
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_e0d9d423', 'expected': '<=2', 'actual': 3, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_phone_then_wechat_complete', 'session_id': 'realism_5_2d7f8b9c', 'expected': '<=2', 'actual': 3, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_fee_first_then_complete', 'session_id': 'realism_11_592d2014', 'expected': '<=2', 'actual': 3, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_e0d9d423', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_phone_complete_with_ai_ending', 'session_id': 'realism_3_d5804b74', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_phone_then_wechat_complete', 'session_id': 'realism_5_2d7f8b9c', 'expected': '<=1', 'actual': 2, 'note': ''}
- scenario_assertion::profile_field_truthy
  - {'scenario_id': 'builtin_full_journey_photo_request_then_complete', 'session_id': 'realism_15_906e0a79', 'expected': None, 'actual': 'fail', 'note': 'profile.wechat 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_fee_then_complete', 'session_id': 'realism_16_bc813d3b', 'expected': None, 'actual': 'fail', 'note': 'profile.sex 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_17_e0eebff3', 'expected': None, 'actual': 'fail', 'note': 'profile.location 期望为真值，实际 None'}
- scenario_assertion::response_contains_any
  - {'scenario_id': 'builtin_full_journey_human_or_ai_then_complete', 'session_id': 'realism_21_aa1b6e3c', 'expected': ['现在', '先', '沟通', '帮助', '了解'], 'actual': 'fail', 'note': "turn=2 需要包含任一关键词 ['现在', '先', '沟通', '帮助', '了解']，实际 '哈哈你不用纠结这个呀，我主要是帮你接住需求和顾虑，能帮到你就好啦。 对了，方便说下你今年多大吗？ 要是有择偶方面的想法也可以随便说说哦'"}
  - {'scenario_id': 'builtin_full_journey_contact_faq_then_phone_complete', 'session_id': 'realism_27_cc475b44', 'expected': ['后续沟通', '方便联系', '进展', '打扰', '匹配'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['后续沟通', '方便联系', '进展', '打扰', '匹配']，实际 '主要是后面需要继续聊的时候，能顺着联系到你，不会拿去乱用'"}
  - {'scenario_id': 'builtin_full_journey_invalid_phone_retry_then_complete', 'session_id': 'realism_30_50eb6cf7', 'expected': ['确认', '重新', '再发', '格式'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['确认', '重新', '再发', '格式']，实际 '资料差不多先了解到了，后续方便联系的话，我知道你现在对微信这块还有顾虑。 你要是愿意，留一个也行，不想留我们就先往下聊'"}
- scenario_assertion::profile_field_equals
  - {'scenario_id': 'builtin_full_journey_contact_defer_then_end', 'session_id': 'realism_23_f06fb6c6', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
  - {'scenario_id': 'builtin_full_journey_both_rejected_terminal_override', 'session_id': 'realism_24_f3a30273', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.9274 baseline=0.9443
- latency_p95: current=16.339 baseline=11.891
- template_top1_ratio: current=0.1219 baseline=0.0608

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 3
- P2失败数: 0
- [P1] latency_p95_seconds: value=16.339 target=8.0
- [P1] baseline_degradation::extraction_pass_rate: value=0.9274 target=0.9443
- [P1] baseline_degradation::latency_p95: value=16.339 target=11.891

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_FAIL
- message_queue_design::mq_ingest_regression => COVERED_PASS (failed=0)

## 根因分桶

- policy_or_routing: 27
- contact_collection: 9
- prompt_or_style: 0
- extraction: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: extraction_pass_rate, latency_p95
- 2026-03-25T13:53:00 humanlike=0.9235 extraction=0.9274 latency_p95=16.339
- 2026-03-25T11:46:35 humanlike=0.8589 extraction=0.9443 latency_p95=11.891
- 2026-03-24T14:32:37 humanlike=0.992 extraction=0.9592 latency_p95=19.942
- 2026-03-24T13:39:39 humanlike=0.9896 extraction=0.9347 latency_p95=2.56
- 2026-03-24T13:04:29 humanlike=0.9896 extraction=0.962 latency_p95=17.98
- 2026-03-21T19:06:24 humanlike=0.9983 extraction=0.9667 latency_p95=17.478
- 2026-03-21T16:29:29 humanlike=0.9979 extraction=0.9689 latency_p95=17.714

## MQ补充检查

- covered=True pass=True
- total=20 passed=20 failed=0 skipped=0
- output_tail:
  - [20/20] RUN mq_dashboard_metrics_funnel_consistency (mq)
  -        mq dashboard 漏斗指标应一致（ingest 入队前置断言）
  - [20/20] PASS mq_dashboard_metrics_funnel_consistency (0.03s)
  - 总场景: 20
  - 通过: 20
  - 失败: 0
  - 跳过: 0
  - 总耗时: 0.3s
  - 平均耗时: 0.015s
  - 最长耗时: 0.05s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 4
- 严重失败项数量: 0
- [major] latency_p95_seconds: value=16.339 target=8.0
- [major] baseline_degradation::extraction_pass_rate: value=0.9274 target=0.9443
- [major] baseline_degradation::latency_p95: value=16.339 target=11.891
- [major] baseline_degradation::template_top1_ratio: value=0.1219 target=0.0608

## 模板化风险 Top10

- 34 次 (12.2%): `我先问个最基础的你是男生还是女生`
- 30 次 (10.8%): `资料差不多先了解到了后续方便联系的话留个电话也行`
- 26 次 (9.3%): `资料差不多先了解到了电话不方便的话微信也可以`
- 10 次 (3.6%): `好那我就按男生来聊我先了解下你今年多大了`
- 9 次 (3.2%): `行那我理解成你是女生我先了解下你今年多大了`
- 8 次 (2.9%): `好那你现在主要在深圳这边你这边现在是什么学历`
- 8 次 (2.9%): `行那年龄这块我理解成#后你这边如果方便也可以先说一个最看重的匹配条件我按这个优先筛`
- 7 次 (2.5%): `好那学历这块我理解成本科先聊下你的偏好吧比如你最在意同城年龄段还是相处感觉`
- 7 次 (2.5%): `好那我就按女生来聊我先了解下你今年多大了`
- 6 次 (2.1%): `你现在在深圳那后面我就按同城思路跟你聊你这边现在是什么学历`

## 字段收集质量

- 总检查数: 496
- 失败检查数: 36
- 通过率: 92.7%
- builtin_full_journey_phone_complete (realism_1_8368acac): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_wechat_complete (realism_2_e0d9d423): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_phone_complete_with_ai_ending (realism_3_d5804b74): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_wechat_complete_with_ai_ending (realism_4_37988b0b): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_phone_then_wechat_complete (realism_5_2d7f8b9c): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_wechat_then_phone_complete (realism_6_4a41ddd6): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_short_answers_phone (realism_7_b0278504): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_short_answers_wechat (realism_8_b4465c95): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_dense_profile_then_phone (realism_9_5d747087): ["occupation_matches_user_stated: expected='产品', actual='做产品'"]
- builtin_full_journey_faq_then_complete (realism_10_fe0e6c1f): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 27 次
- 高频失败 occupation_matches_user_stated: 2 次
- 高频失败 location_truthy: 1 次
- 高频失败 education_truthy: 1 次
- 高频失败 occupation_truthy: 1 次
- 高频失败 location_matches_user_stated: 1 次
- 高频失败 education_matches_user_stated: 1 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 marital_status_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 585
- 失败检查数: 56
- 通过率: 90.4%
- builtin_full_journey_phone_complete (realism_1_8368acac): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_wechat_complete (realism_2_e0d9d423): ["core_ask_limit_age: expected='<=2', actual=3", "medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=2']
- builtin_full_journey_phone_complete_with_ai_ending (realism_3_d5804b74): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=2']
- builtin_full_journey_wechat_complete_with_ai_ending (realism_4_37988b0b): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_phone_then_wechat_complete (realism_5_2d7f8b9c): ["core_ask_limit_age: expected='<=2', actual=3", "medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=2']
- builtin_full_journey_wechat_then_phone_complete (realism_6_4a41ddd6): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_short_answers_phone (realism_7_b0278504): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_short_answers_wechat (realism_8_b4465c95): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_faq_then_complete (realism_10_fe0e6c1f): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_fee_first_then_complete (realism_11_592d2014): ["core_ask_limit_age: expected='<=2', actual=3", "medium_ask_limit_partner_requirement: expected='<=1', actual=2", 'no_consecutive_same_field_ask: expected=0, actual=2']
- 高频失败 no_consecutive_same_field_ask: 27 次
- 高频失败 medium_ask_limit_partner_requirement: 11 次
- 高频失败 scenario_assertion::profile_field_truthy: 6 次
- 高频失败 core_ask_limit_age: 5 次
- 高频失败 scenario_assertion::response_contains_any: 4 次
- 高频失败 scenario_assertion::profile_field_equals: 2 次
