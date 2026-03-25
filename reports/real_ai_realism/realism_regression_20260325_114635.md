# 真实用户仿真回归报告

- 会话数: 32
- 总轮次: 263
- 总耗时(墙钟): 2378.79s
- 累计会话耗时: 2378.57s
- 失败检查数: 140
- 失败分布: turn=56, field=26, policy=58
- 时延 p95: 11.891s
- 时延 p99: 17.309s
- 模板化 Top1 占比: 6.1%
- Token: 1119318 (调用 248 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 85.9%
- 字段提取综合通过率: 94.4%
- 字段精确匹配通过率: 97.4%
- 字段完整性通过率: 92.4%

## 拟人化收集质量

- 总检查数: 808
- 失败检查数: 114
- Turn 级失败: 56
- 策略级失败: 58
- 模板化 Top1 占比: 6.1%
- 时延 p95: 11.891s
- 时延 p99: 17.309s
- 高频 turn 失败 contact_transition_abrupt: 26 次
- 高频 turn 失败 reply_too_fast_nonhuman: 14 次
- 高频 turn 失败 faq_reply_too_fast: 9 次
- 高频 turn 失败 invalid_wechat_not_retried: 6 次
- 高频 turn 失败 faq_not_answered_first: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 23 次
- 高频策略失败 field_interleaving_quality: 22 次
- 高频策略失败 scenario_assertion::profile_field_truthy: 7 次
- 高频策略失败 scenario_assertion::response_contains_any: 3 次
- 高频策略失败 scenario_assertion::profile_field_equals: 2 次

## 字段提取准确性

- 总检查数: 467
- 失败检查数: 26
- 综合通过率: 94.4%
- 精确匹配检查数: 190
- 精确匹配失败数: 5
- 精确匹配通过率: 97.4%
- 完整性检查数: 277
- 完整性失败数: 21
- 完整性通过率: 92.4%
- 高频字段失败 unexpected_conversation_end: 18 次
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
- 复述过度率: 4.6% (12/263)
- 联系方式突兀转场次数: 26
- 意图 fee: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3
- 意图 match: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 reliability: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/1)
- 拒绝后尊重率: 50.0% (4/8)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 0.0% (0/18)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 64.9%
- 动作一致性分: 66.7%

## 隔离质量

- 会话数: 32
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 3.685
- p95 连续提问轮次: 8.0
- 最长连续提问轮次: 8
- 会话中出现>=3连问占比: 90.6% (29/32)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 73.9% (153/207)
- 失败类型 other: 18 次
- 失败类型 missing_extraction: 3 次
- 失败类型 missed_stated_field: 3 次
- 失败类型 wrong_value_or_normalization: 2 次

## 联系方式质量专项

- 联系方式成功率: 82.1% (23/28)
- 可收集场景成功率: 85.2% (23/27)
- 拒绝/防护场景通过率: 100.0% (1/1)
- 无效电话未重试: 0 次
- 无效微信未重试: 6 次

## 时延异常 Top20

- builtin_full_journey_photo_request_then_complete#T9: 20.127s, user=`wx_photo_case90`
- builtin_full_journey_match_process_then_complete#T9: 20.123s, user=`wx_match_flow90`
- builtin_full_journey_invalid_wechat_retry_then_complete#T9: 18.69s, user=`微信wx_12`

## 分阶段耗时均值

- ai_call: 9.1252s
- total: 8.6807s
- extract_collect: 0.0119s
- profile_load: 0.0113s
- context_load: 0.011s
- profile_save: 0.0074s
- other: 0.0022s
- response_build: 0.0013s

## 意图分桶时延

- general: avg=8.987s p95=11.903s max=20.127s n=254
- fee: avg=0.026s p95=0.029s max=0.029s n=3
- safety: avg=0.023s p95=0.028s max=0.028s n=3
- match: avg=0.034s p95=0.034s max=0.034s n=1
- photo: avg=0.026s p95=0.026s max=0.026s n=1
- reliability: avg=0.026s p95=0.026s max=0.026s n=1
- 秒回率(<1s): 5.3%
- FAQ秒回率(<1s): 3.4%
- Model秒回率(<1s): 0.0% (0/247)
- NonAI秒回率(<1s): 100.0% (14/14)
- 超慢回复率(>20s): 0.8%

## 失败样本（自动抽样）

### turn
- contact_transition_abrupt
  - {'turn': 7, 'user': '单身', 'assistant': '好，确认你是单身状态啦~后续有合适的匹配方便及时联系你，你方便告知下手机号吗？', 'latency_s': 8.941, 'perf': {'profile_load': 0.0122, 'context_load': 0.0136, 'profile_save': 0.0118, 'ai_call': 8.889, 'extract_collect': 0.0138, 'response_build': 0.0028, 'other': 0.0, 'total': 8.9407}}
  - {'turn': 7, 'user': '单身', 'assistant': '好，知道你现在是单身啦～后续有合适的匹配方便及时联系你，你方便说下手机号码不？', 'latency_s': 11.834, 'perf': {'profile_load': 0.011, 'context_load': 0.0097, 'profile_save': 0.0064, 'ai_call': 11.798, 'extract_collect': 0.0125, 'response_build': 0.001, 'other': 0.0, 'total': 11.8337}}
  - {'turn': 7, 'user': '单身', 'assistant': '好，了解你现在是单身状态啦。 后续有合适的匹配通知起来更方便，你方便留一下你的手机号不？', 'latency_s': 10.903, 'perf': {'profile_load': 0.0106, 'context_load': 0.0128, 'profile_save': 0.0101, 'ai_call': 10.857, 'extract_collect': 0.0127, 'response_build': 0.0012, 'other': 0.0, 'total': 10.9029}}
- invalid_wechat_not_retried
  - {'turn': 9, 'user': '微信是hangzhou_pm88', 'assistant': '行，那先聊到这儿', 'latency_s': 8.67, 'perf': {'profile_load': 0.0117, 'context_load': 0.0124, 'profile_save': 0.0104, 'ai_call': 8.6246, 'extract_collect': 0.0139, 'response_build': 0.001, 'other': 0.0, 'total': 8.6701}}
  - {'turn': 9, 'user': '微信是suzhou_teacher9', 'assistant': '行，那先聊到这儿', 'latency_s': 7.044, 'perf': {'profile_load': 0.0131, 'context_load': 0.0108, 'profile_save': 0.0109, 'ai_call': 6.9969, 'extract_collect': 0.0136, 'response_build': 0.0012, 'other': 0.0, 'total': 7.0437}}
  - {'turn': 9, 'user': 'wx_why_ask90', 'assistant': '我知道你现在对微信这块还有顾虑。 你要是愿意，留一个也行，不想留我们就先往下聊', 'latency_s': 11.915, 'perf': {'profile_load': 0.0139, 'context_load': 0.0108, 'profile_save': 0.006, 'ai_call': 11.8661, 'extract_collect': 0.0117, 'response_build': 0.0014, 'other': 0.0048, 'total': 11.9146}}
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '怎么收费', 'assistant': '咱们基础匹配这部分不收费，后面如果真有你想进一步了解的，再看要不要选定制服务就行', 'latency_s': 0.029, 'perf': {'profile_load': 0.0056, 'context_load': 0.0121, 'response_build': 0.001, 'other': 0.0104, 'total': 0.0291}}
  - {'turn': 2, 'user': '先不聊资料，先说收费', 'assistant': '咱们基础匹配这部分不收费，后面如果真有你想进一步了解的，再看要不要选定制服务就行', 'latency_s': 0.025, 'perf': {'profile_load': 0.0047, 'context_load': 0.0101, 'response_build': 0.0015, 'other': 0.0082, 'total': 0.0246}}
  - {'turn': 2, 'user': '你们会泄露隐私吗', 'assistant': '这块你可以放心，资料和联系方式只会放在当前沟通里用，不会对外乱传，我们会尽量保护你的隐私', 'latency_s': 0.028, 'perf': {'profile_load': 0.004, 'context_load': 0.0114, 'response_build': 0.0018, 'other': 0.0109, 'total': 0.028}}
- faq_reply_too_fast
  - {'turn': 2, 'user': '怎么收费', 'assistant': '咱们基础匹配这部分不收费，后面如果真有你想进一步了解的，再看要不要选定制服务就行', 'latency_s': 0.029, 'perf': {'profile_load': 0.0056, 'context_load': 0.0121, 'response_build': 0.001, 'other': 0.0104, 'total': 0.0291}}
  - {'turn': 2, 'user': '先不聊资料，先说收费', 'assistant': '咱们基础匹配这部分不收费，后面如果真有你想进一步了解的，再看要不要选定制服务就行', 'latency_s': 0.025, 'perf': {'profile_load': 0.0047, 'context_load': 0.0101, 'response_build': 0.0015, 'other': 0.0082, 'total': 0.0246}}
  - {'turn': 2, 'user': '你们会泄露隐私吗', 'assistant': '这块你可以放心，资料和联系方式只会放在当前沟通里用，不会对外乱传，我们会尽量保护你的隐私', 'latency_s': 0.028, 'perf': {'profile_load': 0.004, 'context_load': 0.0114, 'response_build': 0.0018, 'other': 0.0109, 'total': 0.028}}
- faq_not_answered_first
  - {'turn': 2, 'user': '怎么匹配', 'assistant': '一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定', 'latency_s': 0.034, 'perf': {'profile_load': 0.0028, 'context_load': 0.0104, 'response_build': 0.0008, 'other': 0.0202, 'total': 0.0342}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'builtin_full_journey_wechat_complete', 'session_id': 'realism_2_df174621', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_phone_then_wechat_complete', 'session_id': 'realism_3_8e8fedf9', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'builtin_full_journey_wechat_then_phone_complete', 'session_id': 'realism_4_2db4878a', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- location_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_15_d7a52fa8', 'expected': 'non-empty', 'actual': None, 'note': ''}
- education_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_15_d7a52fa8', 'expected': 'non-empty', 'actual': None, 'note': ''}
- occupation_truthy
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_15_d7a52fa8', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_15_d7a52fa8', 'expected': '深圳', 'actual': None, 'note': ''}
- education_matches_user_stated
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_privacy_then_complete', 'session_id': 'realism_15_d7a52fa8', 'expected': '本科', 'actual': None, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'builtin_full_journey_phone_complete', 'session_id': 'realism_1_9f23fd67', 'expected': 0, 'actual': 2, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_wechat_then_phone_complete', 'session_id': 'realism_4_2db4878a', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_short_answers_phone', 'session_id': 'realism_5_947b5fa5', 'expected': 0, 'actual': 2, 'note': ''}
- field_interleaving_quality
  - {'scenario_id': 'builtin_full_journey_phone_complete', 'session_id': 'realism_1_9f23fd67', 'expected': '<=3 core asks streak', 'actual': 7, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_short_answers_phone', 'session_id': 'realism_5_947b5fa5', 'expected': '<=3 core asks streak', 'actual': 7, 'note': ''}
  - {'scenario_id': 'builtin_full_journey_short_answers_wechat', 'session_id': 'realism_6_69533823', 'expected': '<=3 core asks streak', 'actual': 7, 'note': ''}
- scenario_assertion::profile_field_truthy
  - {'scenario_id': 'builtin_full_journey_match_process_then_complete', 'session_id': 'realism_11_ddecba1e', 'expected': None, 'actual': 'fail', 'note': 'profile.wechat 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_photo_request_then_complete', 'session_id': 'realism_13_f65b7dc8', 'expected': None, 'actual': 'fail', 'note': 'profile.wechat 期望为真值，实际 None'}
  - {'scenario_id': 'builtin_full_journey_mixed_info_and_fee_then_complete', 'session_id': 'realism_14_9fa2a0ac', 'expected': None, 'actual': 'fail', 'note': 'profile.sex 期望为真值，实际 None'}
- scenario_assertion::profile_field_equals
  - {'scenario_id': 'builtin_full_journey_contact_defer_then_end', 'session_id': 'realism_21_3f341055', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
  - {'scenario_id': 'builtin_full_journey_both_rejected_terminal_override', 'session_id': 'realism_22_a64999de', 'expected': True, 'actual': 'fail', 'note': 'profile.conversation_ended 期望 True，实际 False'}
- scenario_assertion::response_contains_any
  - {'scenario_id': 'builtin_full_journey_contact_faq_then_phone_complete', 'session_id': 'realism_25_55c8f58f', 'expected': ['后续沟通', '方便联系', '进展', '打扰', '匹配'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['后续沟通', '方便联系', '进展', '打扰', '匹配']，实际 '主要是后面需要继续聊的时候，能顺着联系到你，不会拿去乱用'"}
  - {'scenario_id': 'builtin_full_journey_invalid_phone_retry_then_complete', 'session_id': 'realism_28_e7bb174b', 'expected': ['确认', '重新', '再发', '格式'], 'actual': 'fail', 'note': "turn=8 需要包含任一关键词 ['确认', '重新', '再发', '格式']，实际 '后续有合适的匹配的话，微信上通知你也更方便，不会随便打扰你的，你方便的话可以告诉我你的微信哦？'"}
  - {'scenario_id': 'builtin_full_journey_invalid_wechat_retry_then_complete', 'session_id': 'realism_29_7fbd4a26', 'expected': ['确认', '重新', '再发', '格式'], 'actual': 'fail', 'note': "turn=9 需要包含任一关键词 ['确认', '重新', '再发', '格式']，实际 '我知道你现在对微信这块还有顾虑。 你要是愿意，留一个也行，不想留我们就先往下聊'"}

## 基线对比

- 检测到退化指标：
- humanlike_pass_rate: current=0.8589 baseline=0.992
- extraction_pass_rate: current=0.9443 baseline=0.9592
- template_top1_ratio: current=0.0608 baseline=0.0323

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 3
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.5 target=0.9
- [P1] latency_p95_seconds: value=11.891 target=8.0
- [P1] baseline_degradation::humanlike_pass_rate: value=0.8589 target=0.992
- [P1] baseline_degradation::extraction_pass_rate: value=0.9443 target=0.9592

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

- policy_or_routing: 45
- contact_collection: 32
- prompt_or_style: 0
- extraction: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: humanlike_pass_rate, extraction_pass_rate
- 2026-03-25T11:46:35 humanlike=0.8589 extraction=0.9443 latency_p95=11.891
- 2026-03-24T14:32:37 humanlike=0.992 extraction=0.9592 latency_p95=19.942
- 2026-03-24T13:39:39 humanlike=0.9896 extraction=0.9347 latency_p95=2.56
- 2026-03-24T13:04:29 humanlike=0.9896 extraction=0.962 latency_p95=17.98
- 2026-03-21T19:06:24 humanlike=0.9983 extraction=0.9667 latency_p95=17.478
- 2026-03-21T16:29:29 humanlike=0.9979 extraction=0.9689 latency_p95=17.714
- 2026-03-21T15:47:56 humanlike=0.9357 extraction=0.8889 latency_p95=2.065

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
  - 最长耗时: 0.04s

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 5
- 严重失败项数量: 1
- [major] latency_p95_seconds: value=11.891 target=8.0
- [critical] refusal_respect_rate: value=0.5 target=0.9
- [major] baseline_degradation::humanlike_pass_rate: value=0.8589 target=0.992
- [major] baseline_degradation::extraction_pass_rate: value=0.9443 target=0.9592
- [major] baseline_degradation::template_top1_ratio: value=0.0608 target=0.0323

## 模板化风险 Top10

- 16 次 (6.1%): `行那先聊到这儿`
- 14 次 (5.3%): `你好呀方便说下你是男生还是女生吗`
- 8 次 (3.0%): `你好呀想问下你是男生还是女生呀`
- 4 次 (1.5%): `好本科学历我知道了啦方便说下你现在是做什么工作的吗`
- 4 次 (1.5%): `好你是男生啦方便说下你今年多大吗`
- 4 次 (1.5%): `没事电话这块你不方便我明白微信要是也不想聊我们就先不碰联系方式`
- 3 次 (1.1%): `原来是#后呀对了你现在在哪个城市生活呀`
- 3 次 (1.1%): `好你是女生啦方便说下你今年多大吗`
- 3 次 (1.1%): `咱们基础匹配这部分不收费后面如果真有你想进一步了解的再看要不要选定制服务就行`
- 3 次 (1.1%): `这块你可以放心资料和联系方式只会放在当前沟通里用不会对外乱传我们会尽量保护你的隐私`

## 字段收集质量

- 总检查数: 467
- 失败检查数: 26
- 通过率: 94.4%
- builtin_full_journey_wechat_complete (realism_2_df174621): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_phone_then_wechat_complete (realism_3_8e8fedf9): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_wechat_then_phone_complete (realism_4_2db4878a): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_short_answers_wechat (realism_6_69533823): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_faq_then_complete (realism_8_aaf102d4): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_fee_first_then_complete (realism_9_b041c356): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_mixed_info_and_privacy_then_complete (realism_15_d7a52fa8): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- builtin_full_journey_boundary_once_then_complete (realism_16_3bccc0b4): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_contact_privacy_concern_then_complete (realism_17_cd27b223): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- builtin_full_journey_authenticity_then_complete (realism_18_42045e10): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 18 次
- 高频失败 location_truthy: 1 次
- 高频失败 education_truthy: 1 次
- 高频失败 occupation_truthy: 1 次
- 高频失败 location_matches_user_stated: 1 次
- 高频失败 education_matches_user_stated: 1 次
- 高频失败 occupation_matches_user_stated: 1 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 marital_status_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 547
- 失败检查数: 58
- 通过率: 89.4%
- builtin_full_journey_phone_complete (realism_1_9f23fd67): ['no_consecutive_same_field_ask: expected=0, actual=2', "field_interleaving_quality: expected='<=3 core asks streak', actual=7"]
- builtin_full_journey_wechat_then_phone_complete (realism_4_2db4878a): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_short_answers_phone (realism_5_947b5fa5): ['no_consecutive_same_field_ask: expected=0, actual=2', "field_interleaving_quality: expected='<=3 core asks streak', actual=7"]
- builtin_full_journey_short_answers_wechat (realism_6_69533823): ['no_consecutive_same_field_ask: expected=0, actual=2', "field_interleaving_quality: expected='<=3 core asks streak', actual=7"]
- builtin_full_journey_faq_then_complete (realism_8_aaf102d4): ['no_consecutive_same_field_ask: expected=0, actual=1', "field_interleaving_quality: expected='<=3 core asks streak', actual=5"]
- builtin_full_journey_fee_first_then_complete (realism_9_b041c356): ['no_consecutive_same_field_ask: expected=0, actual=1']
- builtin_full_journey_privacy_then_complete (realism_10_8f2f82f2): ['no_consecutive_same_field_ask: expected=0, actual=2', "field_interleaving_quality: expected='<=3 core asks streak', actual=6"]
- builtin_full_journey_match_process_then_complete (realism_11_ddecba1e): ['no_consecutive_same_field_ask: expected=0, actual=1', "field_interleaving_quality: expected='<=3 core asks streak', actual=5", 'profile_field_truthy: profile.wechat 期望为真值，实际 None']
- builtin_full_journey_store_then_complete (realism_12_24616e09): ['no_consecutive_same_field_ask: expected=0, actual=1', "field_interleaving_quality: expected='<=3 core asks streak', actual=5"]
- builtin_full_journey_photo_request_then_complete (realism_13_f65b7dc8): ['no_consecutive_same_field_ask: expected=0, actual=1', "field_interleaving_quality: expected='<=3 core asks streak', actual=5", 'profile_field_truthy: profile.wechat 期望为真值，实际 None']
- 高频失败 no_consecutive_same_field_ask: 23 次
- 高频失败 field_interleaving_quality: 22 次
- 高频失败 scenario_assertion::profile_field_truthy: 7 次
- 高频失败 scenario_assertion::response_contains_any: 3 次
- 高频失败 scenario_assertion::profile_field_equals: 2 次
