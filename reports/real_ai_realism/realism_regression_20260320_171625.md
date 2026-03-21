# 真实用户仿真回归报告

- 会话数: 137
- 总轮次: 498
- 总耗时(墙钟): 476.33s
- 累计会话耗时: 473.13s
- 失败检查数: 440
- 失败分布: turn=223, field=145, policy=72
- 时延 p95: 2.34s
- 时延 p99: 2.762s
- 模板化 Top1 占比: 50.6%
- Token: 0 (调用 0 次)

## 核心结论

- 拟人化收集通过率: 87.1%
- 字段提取综合通过率: 81.1%
- 字段精确匹配通过率: 59.0%
- 字段完整性通过率: 85.8%

## 拟人化收集质量

- 总检查数: 2279
- 失败检查数: 295
- Turn 级失败: 223
- 策略级失败: 72
- 模板化 Top1 占比: 50.6%
- 时延 p95: 2.34s
- 时延 p99: 2.762s
- 高频 turn 失败 reply_too_fast_nonhuman: 220 次
- 高频 turn 失败 invalid_wechat_not_retried: 1 次
- 高频 turn 失败 high_risk_advice_overreach: 1 次
- 高频 turn 失败 abuse_not_deescalated: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 72 次

## 字段提取准确性

- 总检查数: 769
- 失败检查数: 145
- 综合通过率: 81.1%
- 精确匹配检查数: 134
- 精确匹配失败数: 55
- 精确匹配通过率: 59.0%
- 完整性检查数: 635
- 完整性失败数: 90
- 完整性通过率: 85.8%
- 高频字段失败 sex_not_inferred_without_self_declare: 65 次
- 高频字段失败 age_matches_user_stated: 32 次
- 高频字段失败 location_truthy: 13 次
- 高频字段失败 location_matches_user_stated: 13 次
- 高频字段失败 partner_requirement_when_mentioned: 9 次
- 高频字段失败 occupation_truthy: 3 次
- 高频字段失败 occupation_matches_user_stated: 3 次
- 高频字段失败 phone_matches_user_stated: 2 次
- 高频字段失败 marital_status_matches_user_stated: 2 次
- 高频字段失败 partner_requirement_matches_user_stated: 2 次

## 对话自然度指标

- 情绪承接命中率: 61.2% (52/85)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 意图 photo: 模板多样性=18.2%, Top1=90.9%, 样本=11
- 意图 reliability: 模板多样性=12.5%, Top1=100.0%, 样本=8
- 意图 match: 模板多样性=33.3%, Top1=83.3%, 样本=6
- 意图 fee: 模板多样性=20.0%, Top1=100.0%, 样本=5
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 88.9% (24/27)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 46.7% (7/15)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 56.8%
- 动作一致性分: 85.7%

## 隔离质量

- 会话数: 137
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.994
- p95 连续提问轮次: 5.0
- 最长连续提问轮次: 6
- 会话中出现>=3连问占比: 31.4% (43/137)

## 提取诊断

- 字段冲突修复率: 100.0% (1/1)
- 证据链覆盖率: 78.0% (142/182)
- 失败类型 context_pollution: 65 次
- 失败类型 wrong_value_or_normalization: 32 次
- 失败类型 missed_stated_field: 23 次
- 失败类型 missing_extraction: 16 次
- 失败类型 other: 9 次

## 联系方式质量专项

- 联系方式成功率: 20.0% (8/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 1 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.6016s
- response_build: 0.5646s
- rule_check: 0.0796s
- ai_call: 0.0049s
- context_load: 0.0041s
- other: 0.0018s
- profile_save: 0.0006s
- extract_collect: 0.0005s
- profile_load: 0.0003s

## 意图分桶时延

- general: avg=0.496s p95=2.318s max=3.012s n=465
- photo: avg=1.982s p95=2.231s max=2.254s n=11
- reliability: avg=2.12s p95=2.349s max=2.388s n=8
- match: avg=2.316s p95=2.595s max=2.65s n=6
- fee: avg=1.985s p95=2.311s max=2.399s n=5
- safety: avg=2.155s p95=2.338s max=2.36s n=3
- 秒回率(<1s): 71.1%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': '这个为啥要问', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.012, 'perf': {'profile_load': 0.0001, 'context_load': 0.0032, 'rule_check': 0.0009, 'profile_save': 0.0004, 'ai_call': 0.0046, 'extract_collect': 0.0002, 'response_build': 0.0003, 'other': 0.0021, 'total': 0.0118}}
  - {'turn': 4, 'user': '你看得懂吗', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.012, 'perf': {'profile_load': 0.0001, 'context_load': 0.0036, 'rule_check': 0.0013, 'profile_save': 0.0004, 'ai_call': 0.0041, 'extract_collect': 0.0002, 'response_build': 0.0003, 'other': 0.0018, 'total': 0.0118}}
  - {'turn': 4, 'user': '问得挺细啊', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.009, 'perf': {'profile_load': 0.0, 'context_load': 0.0028, 'rule_check': 0.0008, 'profile_save': 0.0003, 'ai_call': 0.0026, 'extract_collect': 0.0001, 'response_build': 0.0003, 'other': 0.0015, 'total': 0.0085}}
- invalid_wechat_not_retried
  - {'turn': 8, 'user': '我微信wx123456', 'assistant': '好的呀～那你等好消息啦，一般1到2天内会有初步匹配消息，牵线同事联系前会提前约时间，不会打扰你的～', 'latency_s': 0.011, 'perf': {'profile_load': 0.0, 'context_load': 0.0038, 'rule_check': 0.0012, 'profile_save': 0.0006, 'ai_call': 0.0029, 'extract_collect': 0.0001, 'response_build': 0.0003, 'other': 0.0022, 'total': 0.0113}}
- high_risk_advice_overreach
  - {'turn': 6, 'user': '这个情况在法律上怎么办', 'assistant': '', 'latency_s': 0.002, 'perf': {'profile_load': 0.0, 'context_load': 0.0018, 'response_build': 0.0005, 'rule_check': 0.001, 'other': 0.0, 'total': 0.002}}
- abuse_not_deescalated
  - {'turn': 3, 'user': '你是不是傻', 'assistant': '', 'latency_s': 0.002, 'perf': {'profile_load': 0.0, 'context_load': 0.002, 'response_build': 0.0005, 'rule_check': 0.001, 'other': 0.0, 'total': 0.0022}}
### field
- sex_not_inferred_without_self_declare
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_e7ae5902', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_56fd487a', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_ba91b8de', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
- age_matches_user_stated
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_e7ae5902', 'expected': '90后', 'actual': 36, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_56fd487a', 'expected': '90后', 'actual': 36, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_ba91b8de', 'expected': '90后', 'actual': 36, 'note': ''}
- location_truthy
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_17718f3d', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_62_6d20d1b7', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_4ac4c868', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_17718f3d', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_contact_why_phone', 'session_id': 'realism_62_6d20d1b7', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_4ac4c868', 'expected': '深圳', 'actual': None, 'note': ''}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_f06e7eb8', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_86484de5', 'expected': '17688654321', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_phone_should_not_pollute_occupation', 'session_id': 'realism_85_a5ba3e08', 'expected': '17688654321', 'actual': None, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_nonsense_gibberish_multi_turn', 'session_id': 'realism_1_bb4cde62', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_a78823a6', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_50660f61', 'expected': 0, 'actual': 1, 'note': ''}

## 优化建议

- 模板化风险偏高：Top1 模板占比 50.6% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 252 次 (50.6%): `方便留个电话吗后续有合适的人选时联系你`
- 51 次 (10.2%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 25 次 (5.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配方便留个电话吗后续有合适的人选时联系你`
- 16 次 (3.2%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`
- 15 次 (3.0%): `哈哈不是查户口啦主要是想先多了解你才能更匹配合适的人选方便留个电话吗后续有合适的人选时联系你`
- 11 次 (2.2%): `这个不方便直接给你涉及隐私和合规我们这边都要按流程保护双方信息`
- 10 次 (2.0%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`
- 9 次 (1.8%): `听起来你现在真的很难受先保证安全很重要如果你身边有人先立刻联系家人或朋友陪着你要是已经有伤害自己的想法也请尽快联系当地紧急求助或心理热线你并不孤单`
- 7 次 (1.4%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 7 次 (1.4%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`

## 字段收集质量

- 总检查数: 769
- 失败检查数: 145
- 通过率: 81.1%
- contact_phone_then_wechat_prompt (realism_6_e7ae5902): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_and_wechat_same_turn (realism_7_56fd487a): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_wechat_rejection_should_not_end (realism_8_ba91b8de): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_after_wechat_rejection_should_not_end (realism_9_ace46d38): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_wechat_fallback (realism_10_5e7016a8): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_ce1d278f): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_wechat_only_then_ask_phone (realism_12_a1b83e87): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_wechat_only_then_phone_refusal (realism_13_f71297e9): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_invalid_should_retry (realism_14_3dac79b3): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_invalid_then_valid (realism_15_d8f3912d): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_matches_user_stated: expected='90后', actual=36"]
- 高频失败 sex_not_inferred_without_self_declare: 65 次
- 高频失败 age_matches_user_stated: 32 次
- 高频失败 location_truthy: 13 次
- 高频失败 location_matches_user_stated: 13 次
- 高频失败 partner_requirement_when_mentioned: 9 次
- 高频失败 occupation_truthy: 3 次
- 高频失败 occupation_matches_user_stated: 3 次
- 高频失败 phone_matches_user_stated: 2 次
- 高频失败 marital_status_matches_user_stated: 2 次
- 高频失败 partner_requirement_matches_user_stated: 2 次

## 对话策略规则质量

- 总检查数: 1781
- 失败检查数: 72
- 通过率: 96.0%
- abuse_nonsense_gibberish_multi_turn (realism_1_bb4cde62): ['no_consecutive_same_field_ask: expected=0, actual=1']
- abuse_repeated_ack_should_not_loop_contact (realism_2_a78823a6): ['no_consecutive_same_field_ask: expected=0, actual=1']
- abuse_persistent_trolling_should_boundary (realism_5_50660f61): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_then_wechat_prompt (realism_6_e7ae5902): ['no_consecutive_same_field_ask: expected=0, actual=3']
- contact_phone_and_wechat_same_turn (realism_7_56fd487a): ['no_consecutive_same_field_ask: expected=0, actual=3']
- contact_wechat_rejection_should_not_end (realism_8_ba91b8de): ['no_consecutive_same_field_ask: expected=0, actual=4']
- contact_phone_after_wechat_rejection_should_not_end (realism_9_ace46d38): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_refused_then_wechat_fallback (realism_10_5e7016a8): ['no_consecutive_same_field_ask: expected=0, actual=3']
- contact_phone_refused_then_user_provides_wechat (realism_11_ce1d278f): ['no_consecutive_same_field_ask: expected=0, actual=3']
- contact_wechat_only_then_ask_phone (realism_12_a1b83e87): ['no_consecutive_same_field_ask: expected=0, actual=3']
- 高频失败 no_consecutive_same_field_ask: 72 次
