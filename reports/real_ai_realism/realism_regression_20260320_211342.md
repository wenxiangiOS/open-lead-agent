# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2949.48s
- 累计会话耗时: 2948.54s
- 失败检查数: 108
- 失败分布: turn=7, field=51, policy=50
- 时延 p95: 18.052s
- 时延 p99: 18.074s
- 模板化 Top1 占比: 4.1%
- Token: 1064251 (调用 193 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 97.6%
- 字段提取综合通过率: 96.4%
- 字段精确匹配通过率: 94.2%
- 字段完整性通过率: 97.2%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 57
- Turn 级失败: 7
- 策略级失败: 50
- 模板化 Top1 占比: 4.1%
- 时延 p95: 18.052s
- 时延 p99: 18.074s
- 高频 turn 失败 nonsense_not_guided: 2 次
- 高频 turn 失败 invalid_wechat_not_retried: 2 次
- 高频 turn 失败 preference_triggered_unexpected_ending: 2 次
- 高频 turn 失败 confirm_word_misrouted_to_contact: 1 次
- 高频策略失败 ack_overuse: 46 次
- 高频策略失败 medium_ask_limit_partner_requirement: 2 次
- 高频策略失败 low_priority_never_ask_last_name: 1 次
- 高频策略失败 low_priority_never_ask_height: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 51
- 综合通过率: 96.4%
- 精确匹配检查数: 397
- 精确匹配失败数: 23
- 精确匹配通过率: 94.2%
- 完整性检查数: 1016
- 完整性失败数: 28
- 完整性通过率: 97.2%
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 partner_requirement_when_mentioned: 8 次
- 高频字段失败 location_truthy: 8 次
- 高频字段失败 location_matches_user_stated: 8 次
- 高频字段失败 marital_status_matches_user_stated: 4 次
- 高频字段失败 partner_requirement_matches_user_stated: 4 次
- 高频字段失败 age_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次
- 高频字段失败 occupation_truthy: 1 次

## 对话自然度指标

- 情绪承接命中率: 63.6% (14/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 26.1% (77/295)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=42.9%, Top1=71.4%, 样本=7
- 意图 reliability: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 match: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 safety: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 2/2)
- 拒绝后尊重率: 69.6% (16/23)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 38.1% (8/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 44.5%
- 动作一致性分: 62.5%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.344
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 4.3% (6/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/2)
- 证据链覆盖率: 70.8% (317/448)
- 失败类型 other: 19 次
- 失败类型 missed_stated_field: 14 次
- 失败类型 wrong_value_or_normalization: 9 次
- 失败类型 missing_extraction: 9 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 2 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 12.5663s
- total: 9.6397s
- response_build: 0.4437s
- rule_check: 0.1451s
- extract_collect: 0.0151s
- context_load: 0.0139s
- profile_load: 0.0093s
- profile_save: 0.0081s
- other: 0.0017s

## 意图分桶时延

- general: avg=10.043s p95=18.053s max=20.094s n=280
- fee: avg=2.182s p95=2.39s max=2.447s n=7
- reliability: avg=2.084s p95=2.258s max=2.287s n=4
- match: avg=2.098s p95=2.442s max=2.48s n=2
- photo: avg=1.933s p95=1.933s max=1.933s n=1
- safety: avg=1.919s p95=1.919s max=1.919s n=1
- 秒回率(<1s): 5.8%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.3%

## 失败样本（自动抽样）

### turn
- nonsense_not_guided
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '哈哈不好意思我没看懂你发的内容哦~对啦，想问下你大概是哪个年龄段的呀？知道这个我可以先帮你框定合适的匹配范围哦。', 'latency_s': 8.633, 'perf': {'profile_load': 0.0077, 'context_load': 0.0108, 'rule_check': 0.0028, 'profile_save': 0.0021, 'ai_call': 8.6, 'extract_collect': 0.0055, 'response_build': 0.001, 'other': 0.0028, 'total': 8.6328}}
  - {'turn': 1, 'user': '17688654321', 'assistant': '也可以留一个，后面沟通会更顺手一点～', 'latency_s': 9.225, 'perf': {'profile_load': 0.0107, 'context_load': 0.0188, 'profile_save': 0.0145, 'rule_check': 0.0031, 'ai_call': 9.1633, 'extract_collect': 0.0252, 'response_build': 0.001, 'other': 0.0, 'total': 9.225}}
- invalid_wechat_not_retried
  - {'turn': 3, 'user': '可以，我微信wx123456', 'assistant': '好的呀～那你等好消息啦，一般1到2天内会有初步匹配消息，牵线同事联系前会提前约时间，不会打扰你的～', 'latency_s': 18.06, 'perf': {'profile_load': 0.0081, 'context_load': 0.0187, 'rule_check': 0.0069, 'profile_save': 0.006, 'ai_call': 18.0089, 'extract_collect': 0.0044, 'response_build': 0.0016, 'other': 0.0057, 'total': 18.0603}}
  - {'turn': 3, 'user': '那我微信wx123456', 'assistant': '要是你电话方便的话，也可以留一个，后面联系会更及时些～', 'latency_s': 16.564, 'perf': {'profile_load': 0.0127, 'context_load': 0.0202, 'rule_check': 0.006, 'profile_save': 0.0104, 'ai_call': 16.5002, 'extract_collect': 0.0139, 'response_build': 0.001, 'other': 0.0, 'total': 16.5635}}
- preference_triggered_unexpected_ending
  - {'turn': 1, 'user': '我是les，喜欢女生', 'assistant': '理解你的需求呀～不过我们这边目前主要还是做异性相亲这块，可能不太适合你呢～你可以去看看更对口的平台，祝你顺顺利利遇到合适的人～', 'latency_s': 17.732, 'perf': {'profile_load': 0.0055, 'context_load': 0.0119, 'profile_save': 0.0059, 'rule_check': 0.0031, 'ai_call': 15.4019, 'extract_collect': 0.0079, 'response_build': 2.297, 'other': 0.0, 'total': 17.7315}}
  - {'turn': 1, 'user': '我是gay，喜欢男生', 'assistant': '感谢你的信任～我们专注做异性相亲，可能帮不到你呢～不过现在有很多专业的平台，相信你能找到合适的！祝你幸福～', 'latency_s': 16.876, 'perf': {'profile_load': 0.0053, 'context_load': 0.0086, 'profile_save': 0.0046, 'rule_check': 0.002, 'ai_call': 14.8657, 'extract_collect': 0.0087, 'response_build': 1.987, 'other': 0.0, 'total': 16.8762}}
- confirm_word_misrouted_to_contact
  - {'turn': 2, 'user': '好的', 'assistant': '你这边资料我先整理好了，后续方便联系推进，方便留一下你的电话号码吗？后续有合适的匹配人选我们可以及时联系你哦。', 'latency_s': 7.045, 'perf': {'profile_load': 0.0094, 'context_load': 0.0177, 'rule_check': 0.0051, 'profile_save': 0.0046, 'ai_call': 6.998, 'extract_collect': 0.0054, 'response_build': 0.0009, 'other': 0.0041, 'total': 7.0452}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_8e63f66c', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_46e8fd90', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_6ddb4926', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_d3c9042d', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_3f242b90', 'expected': 'wx72378', 'actual': None, 'note': ''}
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_2a75283f', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'ending_age_under_limit', 'session_id': 'realism_45_3b9df1fe', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_59_45b70d86', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_2a75283f', 'expected': '17688654321', 'actual': None, 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_42_fc258047', 'expected': '离异', 'actual': '离异（手续办理中）', 'note': ''}
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_d3ae89f4', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_1420c153', 'expected': '离婚', 'actual': '离异（手续办理中）', 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_5c77c3aa', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_4d05b921', 'expected': '30', 'actual': 36, 'note': ''}
  - {'scenario_id': 'safety_conflict_info_should_confirm', 'session_id': 'realism_132_a0d1c6d9', 'expected': '35', 'actual': 36, 'note': ''}
### policy
- ack_overuse
  - {'scenario_id': 'abuse_user_rude_language_deescalation', 'session_id': 'realism_3_829ff7b3', 'expected': '<=0.35', 'actual': 0.5, 'note': ''}
  - {'scenario_id': 'abuse_user_profanity_should_stay_composed', 'session_id': 'realism_4_f67c6d5d', 'expected': '<=0.35', 'actual': 0.5, 'note': ''}
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_e6ec4f44', 'expected': '<=0.35', 'actual': 1.0, 'note': ''}
- low_priority_never_ask_last_name
  - {'scenario_id': 'contact_confirm_word_then_wechat_fallback', 'session_id': 'realism_20_4a63fb03', 'expected': '0', 'actual': 1, 'note': ''}
- low_priority_never_ask_height
  - {'scenario_id': 'field_height_extract_cm', 'session_id': 'realism_94_52f61f9d', 'expected': '0', 'actual': 1, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_ddcfea1a', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_134_e0106961', 'expected': '<=1', 'actual': 2, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 12 次 (4.1%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 5 次 (1.7%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 5 次 (1.7%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 4 次 (1.4%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 4 次 (1.4%): `亲你是想说什么呢我刚才看到的消息有点奇怪呢`
- 4 次 (1.4%): `小姐姐这个号码好像位数不对呢能确认下是手机号或微信号吗呀`
- 4 次 (1.4%): `小姐姐这个微信号好像格式不太对呢是字母开头的#-#位字符吗呀`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 51
- 通过率: 96.4%
- contact_phone_and_wechat_same_turn (realism_7_8e63f66c): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_refused_then_user_provides_wechat (realism_11_46e8fd90): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_asks_wechat_instead_of_phone (realism_21_6ddb4926): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_phone_inconvenient_then_wechat (realism_31_d3c9042d): ["wechat_matches_user_stated: expected='abc123', actual='wxabc123'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_3f242b90): ["wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_dc9cea9d): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_too_long_should_retry (realism_41_2a75283f): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "phone_matches_user_stated: expected='17688654321', actual=None"]
- ending_divorce_incomplete_should_end (realism_42_fc258047): ["marital_status_matches_user_stated: expected='离异', actual='离异（手续办理中）'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_44_deb533be): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_age_under_limit (realism_45_3b9df1fe): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 partner_requirement_when_mentioned: 8 次
- 高频失败 location_truthy: 8 次
- 高频失败 location_matches_user_stated: 8 次
- 高频失败 marital_status_matches_user_stated: 4 次
- 高频失败 partner_requirement_matches_user_stated: 4 次
- 高频失败 age_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次
- 高频失败 occupation_truthy: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 50
- 通过率: 97.6%
- abuse_user_rude_language_deescalation (realism_3_829ff7b3): ["ack_overuse: expected='<=0.35', actual=0.5"]
- abuse_user_profanity_should_stay_composed (realism_4_f67c6d5d): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_phone_then_wechat_prompt (realism_6_e6ec4f44): ["ack_overuse: expected='<=0.35', actual=1.0"]
- contact_phone_and_wechat_same_turn (realism_7_8e63f66c): ["ack_overuse: expected='<=0.35', actual=1.0"]
- contact_wechat_rejection_should_not_end (realism_8_26c6a3fe): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_phone_invalid_then_valid (realism_15_25c58cd1): ["ack_overuse: expected='<=0.35', actual=0.6667"]
- contact_phone_with_spaces_should_collect (realism_16_4e0afd09): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_hk_phone_then_wechat (realism_17_e316dad8): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_confirm_word_after_phone_prompt (realism_19_ff22fa8d): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_confirm_word_then_wechat_fallback (realism_20_4a63fb03): ["low_priority_never_ask_last_name: expected='0', actual=1"]
- 高频失败 ack_overuse: 46 次
- 高频失败 medium_ask_limit_partner_requirement: 2 次
- 高频失败 low_priority_never_ask_last_name: 1 次
- 高频失败 low_priority_never_ask_height: 1 次
