# 真实用户仿真回归报告

- 会话数: 137
- 总轮次: 498
- 总耗时(墙钟): 5549.21s
- 累计会话耗时: 5548.2s
- 失败检查数: 157
- 失败分布: turn=2, field=123, policy=32
- 时延 p95: 18.044s
- 时延 p99: 59.451s
- 模板化 Top1 占比: 10.2%
- Token: 1773273 (调用 316 次)

## 核心结论

- 拟人化收集通过率: 98.5%
- 字段提取综合通过率: 84.0%
- 字段精确匹配通过率: 88.8%
- 字段完整性通过率: 83.0%

## 拟人化收集质量

- 总检查数: 2279
- 失败检查数: 34
- Turn 级失败: 2
- 策略级失败: 32
- 模板化 Top1 占比: 10.2%
- 时延 p95: 18.044s
- 时延 p99: 59.451s
- 高频 turn 失败 high_risk_advice_overreach: 1 次
- 高频 turn 失败 abuse_not_deescalated: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 28 次
- 高频策略失败 core_ask_limit_location: 2 次
- 高频策略失败 low_priority_never_ask_height: 1 次
- 高频策略失败 income_question_soft_tone: 1 次

## 字段提取准确性

- 总检查数: 769
- 失败检查数: 123
- 综合通过率: 84.0%
- 精确匹配检查数: 134
- 精确匹配失败数: 15
- 精确匹配通过率: 88.8%
- 完整性检查数: 635
- 完整性失败数: 108
- 完整性通过率: 83.0%
- 高频字段失败 sex_not_inferred_without_self_declare: 65 次
- 高频字段失败 age_reasonable_if_present: 32 次
- 高频字段失败 location_truthy: 6 次
- 高频字段失败 location_matches_user_stated: 6 次
- 高频字段失败 partner_requirement_when_mentioned: 4 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 marital_status_matches_user_stated: 2 次
- 高频字段失败 partner_requirement_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次
- 高频字段失败 age_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 90.6% (77/85)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 意图 photo: 模板多样性=18.2%, Top1=90.9%, 样本=11
- 意图 reliability: 模板多样性=12.5%, Top1=100.0%, 样本=8
- 意图 match: 模板多样性=33.3%, Top1=83.3%, 样本=6
- 意图 fee: 模板多样性=20.0%, Top1=100.0%, 样本=5
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 96.3% (26/27)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 46.7% (7/15)
- 异常恢复率: 100.0% (5/5)
- 人设一致性分: 50.9%
- 动作一致性分: 71.4%

## 隔离质量

- 会话数: 137
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.87
- p95 连续提问轮次: 4.0
- 最长连续提问轮次: 6
- 会话中出现>=3连问占比: 27.0% (37/137)

## 提取诊断

- 字段冲突修复率: 100.0% (1/1)
- 证据链覆盖率: 75.7% (153/202)
- 失败类型 context_pollution: 65 次
- 失败类型 other: 36 次
- 失败类型 missed_stated_field: 11 次
- 失败类型 missing_extraction: 7 次
- 失败类型 wrong_value_or_normalization: 4 次

## 联系方式质量专项

- 联系方式成功率: 25.0% (10/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20

- faq_priority_mediator#T4: 291.031s, user=`本科`
- ending_normal_complete#T1: 197.205s, user=`我是女生`
- ending_after_conversation_ended_followup#T1: 150.592s, user=`我现在还在分居中`
- ending_proxy_user#T1: 74.442s, user=`我是帮朋友问的`
- ending_both_contact_refused#T7: 70.529s, user=`微信也不留`
- ending_fake_info_pattern#T1: 59.108s, user=`我是女生`

## 分阶段耗时均值

- ai_call: 14.3245s
- total: 10.7913s
- response_build: 0.8622s
- rule_check: 0.3786s
- context_load: 0.0119s
- profile_load: 0.0098s
- extract_collect: 0.0093s
- profile_save: 0.005s
- other: 0.0019s

## 意图分桶时延

- general: avg=11.405s p95=18.046s max=291.031s n=465
- photo: avg=2.048s p95=2.369s max=2.369s n=11
- reliability: avg=2.14s p95=2.357s max=2.39s n=8
- match: avg=2.292s p95=2.636s max=2.644s n=6
- fee: avg=2.298s p95=2.591s max=2.649s n=5
- safety: avg=1.963s p95=2.114s max=2.125s n=3
- 秒回率(<1s): 3.8%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 1.4%

## 失败样本（自动抽样）

### turn
- high_risk_advice_overreach
  - {'turn': 6, 'user': '这个情况在法律上怎么办', 'assistant': '', 'latency_s': 0.007, 'perf': {'profile_load': 0.0024, 'context_load': 0.0039, 'response_build': 0.0013, 'rule_check': 0.0026, 'other': 0.0, 'total': 0.0066}}
- abuse_not_deescalated
  - {'turn': 3, 'user': '你是不是傻', 'assistant': '', 'latency_s': 0.007, 'perf': {'profile_load': 0.0024, 'context_load': 0.0048, 'response_build': 0.0016, 'rule_check': 0.0033, 'other': 0.0, 'total': 0.0075}}
### field
- sex_not_inferred_without_self_declare
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_5227e505', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_6a6c4bcc', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_97682c69', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
- age_reasonable_if_present
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_5227e505', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_6a6c4bcc', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_97682c69', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_395007dd', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_5b23c9ac', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_cd671105', 'expected': '17688654321', 'actual': None, 'note': ''}
- partner_requirement_when_mentioned
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_45_f46aa147', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_b0e30e9f', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'field_marital_status_divorced', 'session_id': 'realism_92_881c1352', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_f5be1932', 'expected': '离婚', 'actual': '离异（手续办理中）', 'note': ''}
  - {'scenario_id': 'safety_high_risk_legal_query_guard', 'session_id': 'realism_128_67632cff', 'expected': '离婚', 'actual': None, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_5227e505', 'expected': 0, 'actual': 2, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_6a6c4bcc', 'expected': 0, 'actual': 2, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_97682c69', 'expected': 0, 'actual': 1, 'note': ''}
- low_priority_never_ask_height
  - {'scenario_id': 'field_height_extract_cm', 'session_id': 'realism_93_0c1c3eab', 'expected': '0', 'actual': 1, 'note': ''}
- income_question_soft_tone
  - {'scenario_id': 'field_income_extract_monthly', 'session_id': 'realism_94_07b313a7', 'expected': 0, 'actual': 1, 'note': ''}
- core_ask_limit_location
  - {'scenario_id': 'humanlike_memory_reuse_location', 'session_id': 'realism_108_6845ae37', 'expected': '<=2', 'actual': 3, 'note': ''}
  - {'scenario_id': 'humanlike_answer_question_then_resume', 'session_id': 'realism_120_28b5214f', 'expected': '<=2', 'actual': 3, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 51 次 (10.2%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 18 次 (3.6%): `方便留个电话吗后续有合适的人选时联系你`
- 11 次 (2.2%): `这个不方便直接给你涉及隐私和合规我们这边都要按流程保护双方信息`
- 10 次 (2.0%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`
- 9 次 (1.8%): `听起来你现在真的很难受先保证安全很重要如果你身边有人先立刻联系家人或朋友陪着你要是已经有伤害自己的想法也请尽快联系当地紧急求助或心理热线你并不孤单`
- 7 次 (1.4%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 7 次 (1.4%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`
- 6 次 (1.2%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 5 次 (1.0%): `我们先按你刚说的继续聊不急着重复问这个`
- 5 次 (1.0%): `流程是先线上了解并做匹配筛选双方聊得来再后续有合适人选我会第一时间联系你这样更稳妥你要是还有顾虑也可以继续问我`

## 字段收集质量

- 总检查数: 769
- 失败检查数: 123
- 通过率: 84.0%
- contact_phone_then_wechat_prompt (realism_6_5227e505): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_and_wechat_same_turn (realism_7_6a6c4bcc): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_wechat_rejection_should_not_end (realism_8_97682c69): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_after_wechat_rejection_should_not_end (realism_9_5be13ebf): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_wechat_fallback (realism_10_df693073): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_673bd673): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_wechat_only_then_ask_phone (realism_12_7da64513): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_wechat_only_then_phone_refusal (realism_13_a9695a05): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_invalid_should_retry (realism_14_6e71d968): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_invalid_then_valid (realism_15_682dad75): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- 高频失败 sex_not_inferred_without_self_declare: 65 次
- 高频失败 age_reasonable_if_present: 32 次
- 高频失败 location_truthy: 6 次
- 高频失败 location_matches_user_stated: 6 次
- 高频失败 partner_requirement_when_mentioned: 4 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 marital_status_matches_user_stated: 2 次
- 高频失败 partner_requirement_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次
- 高频失败 age_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 1781
- 失败检查数: 32
- 通过率: 98.2%
- contact_phone_then_wechat_prompt (realism_6_5227e505): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_phone_and_wechat_same_turn (realism_7_6a6c4bcc): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_wechat_rejection_should_not_end (realism_8_97682c69): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_refused_then_wechat_fallback (realism_10_df693073): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_only_then_phone_refusal (realism_13_a9695a05): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_invalid_then_valid (realism_15_682dad75): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat (realism_17_6a973c3a): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_confirm_word_after_phone_prompt (realism_19_cb7fbe9d): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_user_provides_phone_after_privacy_question (realism_23_e5aee225): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_user_provides_wechat_after_phone_prompt (realism_24_fac7e73d): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 28 次
- 高频失败 core_ask_limit_location: 2 次
- 高频失败 low_priority_never_ask_height: 1 次
- 高频失败 income_question_soft_tone: 1 次
