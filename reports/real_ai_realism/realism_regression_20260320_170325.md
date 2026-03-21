# 真实用户仿真回归报告

- 会话数: 137
- 总轮次: 498
- 总耗时(墙钟): 4638.8s
- 累计会话耗时: 4637.89s
- 失败检查数: 191
- 失败分布: turn=33, field=116, policy=42
- 时延 p95: 17.386s
- 时延 p99: 26.312s
- 模板化 Top1 占比: 5.4%
- Token: 1890259 (调用 334 次)

## 核心结论

- 拟人化收集通过率: 96.7%
- 字段提取综合通过率: 84.9%
- 字段精确匹配通过率: 88.1%
- 字段完整性通过率: 84.2%

## 拟人化收集质量

- 总检查数: 2279
- 失败检查数: 75
- Turn 级失败: 33
- 策略级失败: 42
- 模板化 Top1 占比: 5.4%
- 时延 p95: 17.386s
- 时延 p99: 26.312s
- 高频 turn 失败 reply_too_fast_nonhuman: 31 次
- 高频 turn 失败 high_risk_advice_overreach: 1 次
- 高频 turn 失败 abuse_not_deescalated: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 38 次
- 高频策略失败 core_ask_limit_age: 1 次
- 高频策略失败 low_priority_never_ask_last_name: 1 次
- 高频策略失败 core_ask_limit_location: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次

## 字段提取准确性

- 总检查数: 769
- 失败检查数: 116
- 综合通过率: 84.9%
- 精确匹配检查数: 134
- 精确匹配失败数: 16
- 精确匹配通过率: 88.1%
- 完整性检查数: 635
- 完整性失败数: 100
- 完整性通过率: 84.2%
- 高频字段失败 sex_not_inferred_without_self_declare: 65 次
- 高频字段失败 age_reasonable_if_present: 28 次
- 高频字段失败 age_matches_user_stated: 5 次
- 高频字段失败 location_truthy: 4 次
- 高频字段失败 location_matches_user_stated: 4 次
- 高频字段失败 partner_requirement_when_mentioned: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 marital_status_matches_user_stated: 2 次
- 高频字段失败 partner_requirement_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 84.7% (72/85)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 意图 photo: 模板多样性=18.2%, Top1=90.9%, 样本=11
- 意图 reliability: 模板多样性=12.5%, Top1=100.0%, 样本=8
- 意图 match: 模板多样性=33.3%, Top1=83.3%, 样本=6
- 意图 fee: 模板多样性=20.0%, Top1=100.0%, 样本=5
- 意图 safety: 模板多样性=33.3%, Top1=100.0%, 样本=3

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 1/1)
- 拒绝后尊重率: 81.5% (22/27)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 33.3% (5/15)
- 异常恢复率: 100.0% (3/3)
- 人设一致性分: 64.4%
- 动作一致性分: 71.4%

## 隔离质量

- 会话数: 137
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 2.311
- p95 连续提问轮次: 5.0
- 最长连续提问轮次: 6
- 会话中出现>=3连问占比: 38.0% (52/137)

## 提取诊断

- 字段冲突修复率: 100.0% (1/1)
- 证据链覆盖率: 74.6% (156/209)
- 失败类型 context_pollution: 65 次
- 失败类型 other: 31 次
- 失败类型 wrong_value_or_normalization: 8 次
- 失败类型 missed_stated_field: 8 次
- 失败类型 missing_extraction: 4 次

## 联系方式质量专项

- 联系方式成功率: 25.0% (10/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20

- humanlike_emotion_recognition_relaxed#T2: 45.058s, user=`我是女生`
- contact_wechat_invalid_then_valid#T3: 45.055s, user=`asdjkl@@@###`
- contact_wechat_invalid_then_valid#T4: 45.051s, user=`本科`
- faq_priority_can_add_wechat#T2: 31.787s, user=`这是面试吗`
- humanlike_transition_natural_field_switch#T3: 28.158s, user=`在深圳`
- field_sex_extract_male#T2: 26.255s, user=`hi，我在SZ，work in IT`

## 分阶段耗时均值

- ai_call: 11.0406s
- total: 8.9636s
- response_build: 0.4091s
- rule_check: 0.0821s
- context_load: 0.012s
- profile_load: 0.0107s
- extract_collect: 0.0089s
- profile_save: 0.0052s
- other: 0.0017s

## 意图分桶时延

- general: avg=9.444s p95=17.531s max=45.058s n=465
- photo: avg=2.064s p95=2.261s max=2.304s n=11
- reliability: avg=2.296s p95=2.553s max=2.558s n=8
- match: avg=2.17s p95=2.419s max=2.458s n=6
- fee: avg=2.28s p95=2.446s max=2.463s n=5
- safety: avg=2.314s p95=2.376s max=2.379s n=3
- 秒回率(<1s): 12.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 2.4%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '90后', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.065, 'perf': {'profile_load': 0.0238, 'context_load': 0.0127, 'rule_check': 0.0064, 'profile_save': 0.0086, 'ai_call': 0.009, 'extract_collect': 0.0192, 'response_build': 0.0011, 'other': 0.0, 'total': 0.0652}}
  - {'turn': 3, 'user': '在深圳', 'assistant': '深圳那边的资源我们这边一直在做筛选更新，我会优先按同城给你匹配～方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.066, 'perf': {'profile_load': 0.0166, 'context_load': 0.0165, 'rule_check': 0.0059, 'profile_save': 0.006, 'ai_call': 0.0101, 'extract_collect': 0.0113, 'response_build': 0.0016, 'other': 0.0, 'total': 0.066}}
  - {'turn': 3, 'user': '在深圳', 'assistant': '深圳那边的资源我们这边一直在做筛选更新，我会优先按同城给你匹配～方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.054, 'perf': {'profile_load': 0.0124, 'context_load': 0.0172, 'rule_check': 0.0097, 'profile_save': 0.0056, 'ai_call': 0.0048, 'extract_collect': 0.0074, 'response_build': 0.0015, 'other': 0.0, 'total': 0.0537}}
- high_risk_advice_overreach
  - {'turn': 6, 'user': '这个情况在法律上怎么办', 'assistant': '', 'latency_s': 0.009, 'perf': {'profile_load': 0.0026, 'context_load': 0.0064, 'response_build': 0.0022, 'rule_check': 0.0042, 'other': 0.0, 'total': 0.0093}}
- abuse_not_deescalated
  - {'turn': 3, 'user': '你是不是傻', 'assistant': '', 'latency_s': 0.01, 'perf': {'profile_load': 0.0031, 'context_load': 0.006, 'response_build': 0.002, 'rule_check': 0.0047, 'other': 0.0, 'total': 0.0095}}
### field
- sex_not_inferred_without_self_declare
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_1caa7135', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_85cb3aee', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_ab7d40c6', 'expected': 'empty/unknown', 'actual': '女', 'note': 'no explicit self sex in user turns'}
- age_reasonable_if_present
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_1caa7135', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_85cb3aee', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_ab7d40c6', 'expected': '18-60 or empty', 'actual': 90, 'note': ''}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_5f365bec', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_9e28fa96', 'expected': 'wx72378', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'contact_phone_with_country_code', 'session_id': 'realism_35_09818435', 'expected': '90后', 'actual': 36, 'note': ''}
  - {'scenario_id': 'contact_wechat_with_special_chars', 'session_id': 'realism_38_3407ace9', 'expected': '90后', 'actual': 36, 'note': ''}
  - {'scenario_id': 'contact_phone_too_short_should_retry', 'session_id': 'realism_40_2e2f0861', 'expected': '90后', 'actual': 36, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_26aa4534', 'expected': '17688654321', 'actual': None, 'note': ''}
- partner_requirement_when_mentioned
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_45_d40bdbc2', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'field_marital_status_divorced', 'session_id': 'realism_92_687bbb9d', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'robustness_age_boundary_just_adult', 'session_id': 'realism_123_664135a3', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_1caa7135', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_85cb3aee', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_ab7d40c6', 'expected': 0, 'actual': 2, 'note': ''}
- core_ask_limit_age
  - {'scenario_id': 'humanlike_transition_with_feedback', 'session_id': 'realism_102_aec83da0', 'expected': '<=2', 'actual': 3, 'note': ''}
- low_priority_never_ask_last_name
  - {'scenario_id': 'humanlike_answer_question_then_resume', 'session_id': 'realism_120_2f89ce7c', 'expected': '0', 'actual': 1, 'note': ''}
- core_ask_limit_location
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_127_3d51421f', 'expected': '<=2', 'actual': 3, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_127_3d51421f', 'expected': '<=1', 'actual': 2, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 27 次 (5.4%): `方便留个电话吗后续有合适的人选时联系你`
- 11 次 (2.2%): `这个不方便直接给你涉及隐私和合规我们这边都要按流程保护双方信息`
- 10 次 (2.0%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`
- 9 次 (1.8%): `听起来你现在真的很难受先保证安全很重要如果你身边有人先立刻联系家人或朋友陪着你要是已经有伤害自己的想法也请尽快联系当地紧急求助或心理热线你并不孤单`
- 8 次 (1.6%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 7 次 (1.4%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 7 次 (1.4%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`
- 6 次 (1.2%): `我理解你现在有点烦没关系我先不追问你要是愿意聊我们可以慢慢说`
- 6 次 (1.2%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`
- 5 次 (1.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配方便留个电话吗后续有合适的人选时联系你`

## 字段收集质量

- 总检查数: 769
- 失败检查数: 116
- 通过率: 84.9%
- contact_phone_then_wechat_prompt (realism_6_1caa7135): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_and_wechat_same_turn (realism_7_85cb3aee): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_wechat_rejection_should_not_end (realism_8_ab7d40c6): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_after_wechat_rejection_should_not_end (realism_9_a83334bc): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_wechat_fallback (realism_10_5aace6e2): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_0bd53780): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_wechat_only_then_ask_phone (realism_12_9f5223ab): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)"]
- contact_wechat_only_then_phone_refusal (realism_13_50269c6c): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_invalid_should_retry (realism_14_6c48a967): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- contact_phone_invalid_then_valid (realism_15_9bad0320): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='女' (no explicit self sex in user turns)", "age_reasonable_if_present: expected='18-60 or empty', actual=90"]
- 高频失败 sex_not_inferred_without_self_declare: 65 次
- 高频失败 age_reasonable_if_present: 28 次
- 高频失败 age_matches_user_stated: 5 次
- 高频失败 location_truthy: 4 次
- 高频失败 location_matches_user_stated: 4 次
- 高频失败 partner_requirement_when_mentioned: 3 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 marital_status_matches_user_stated: 2 次
- 高频失败 partner_requirement_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 1781
- 失败检查数: 42
- 通过率: 97.6%
- contact_phone_then_wechat_prompt (realism_6_1caa7135): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_and_wechat_same_turn (realism_7_85cb3aee): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_rejection_should_not_end (realism_8_ab7d40c6): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_phone_refused_then_user_provides_wechat (realism_11_0bd53780): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_wechat_only_then_ask_phone (realism_12_9f5223ab): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_phone_invalid_then_valid (realism_15_9bad0320): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat (realism_17_6bde7dd4): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat_rejected_not_end (realism_18_3c44f5b1): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_user_asks_wechat_instead_of_phone (realism_21_72e0c0a9): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_user_provides_phone_after_privacy_question (realism_23_bbb26772): ['no_consecutive_same_field_ask: expected=0, actual=2']
- 高频失败 no_consecutive_same_field_ask: 38 次
- 高频失败 core_ask_limit_age: 1 次
- 高频失败 low_priority_never_ask_last_name: 1 次
- 高频失败 core_ask_limit_location: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
