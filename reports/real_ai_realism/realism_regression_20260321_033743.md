# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 22434.63s
- 累计会话耗时: 22433.68s
- 失败检查数: 118
- 失败分布: turn=4, field=64, policy=50
- 时延 p95: 927.432s
- 时延 p99: 993.242s
- 模板化 Top1 占比: 4.8%
- Token: 798666 (调用 145 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 97.7%
- 字段提取综合通过率: 95.5%
- 字段精确匹配通过率: 93.5%
- 字段完整性通过率: 96.3%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 54
- Turn 级失败: 4
- 策略级失败: 50
- 模板化 Top1 占比: 4.8%
- 时延 p95: 927.432s
- 时延 p99: 993.242s
- 高频 turn 失败 preference_triggered_unexpected_ending: 2 次
- 高频 turn 失败 nonsense_not_guided: 1 次
- 高频 turn 失败 contact_transition_abrupt: 1 次
- 高频策略失败 ack_overuse: 46 次
- 高频策略失败 low_priority_never_ask_last_name: 2 次
- 高频策略失败 field_interleaving_quality: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 64
- 综合通过率: 95.5%
- 精确匹配检查数: 397
- 精确匹配失败数: 26
- 精确匹配通过率: 93.5%
- 完整性检查数: 1016
- 完整性失败数: 38
- 完整性通过率: 96.3%
- 高频字段失败 partner_requirement_when_mentioned: 14 次
- 高频字段失败 location_truthy: 12 次
- 高频字段失败 location_matches_user_stated: 12 次
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 age_matches_user_stated: 3 次
- 高频字段失败 partner_requirement_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 2 次
- 高频字段失败 occupation_matches_user_stated: 2 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 68.2% (15/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 23.7% (70/295)
- 联系方式突兀转场次数: 1
- 意图 fee: 模板多样性=42.9%, Top1=71.4%, 样本=7
- 意图 reliability: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 match: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 safety: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 2/2)
- 拒绝后尊重率: 69.6% (16/23)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 28.6% (6/21)
- 异常恢复率: 100.0% (14/14)
- 人设一致性分: 40.9%
- 动作一致性分: 75.0%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.341
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 5.1% (7/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/2)
- 证据链覆盖率: 70.6% (314/445)
- 失败类型 other: 25 次
- 失败类型 missed_stated_field: 19 次
- 失败类型 missing_extraction: 13 次
- 失败类型 wrong_value_or_normalization: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 122.4359s
- total: 75.6899s
- response_build: 3.8109s
- rule_check: 0.1435s
- context_load: 0.0144s
- extract_collect: 0.0137s
- profile_load: 0.0095s
- profile_save: 0.0083s
- other: 0.0016s

## 意图分桶时延

- general: avg=79.63s p95=927.91s max=1027.567s n=280
- fee: avg=2.105s p95=2.499s max=2.589s n=7
- reliability: avg=2.151s p95=2.413s max=2.452s n=4
- match: avg=2.293s p95=2.305s max=2.306s n=2
- photo: avg=1.985s p95=1.985s max=1.985s n=1
- safety: avg=2.281s p95=2.281s max=2.281s n=1
- 秒回率(<1s): 6.4%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 7.5%

## 失败样本（自动抽样）

### turn
- nonsense_not_guided
  - {'turn': 3, 'user': 'qweqwe123123', 'assistant': '哈哈我没太明白你发的内容是什么意思哦~对了，想问下你大概是哪个年龄段的呀，知道这个我好先帮你筛选适配的匹配范围哦。', 'latency_s': 11.461, 'perf': {'profile_load': 0.007, 'context_load': 0.0136, 'rule_check': 0.0049, 'profile_save': 0.0033, 'ai_call': 11.4225, 'extract_collect': 0.0051, 'response_build': 0.0008, 'other': 0.0034, 'total': 11.4608}}
- preference_triggered_unexpected_ending
  - {'turn': 1, 'user': '我是les，喜欢女生', 'assistant': '谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～', 'latency_s': 17.926, 'perf': {'profile_load': 0.009, 'context_load': 0.0168, 'profile_save': 0.0092, 'rule_check': 0.0061, 'ai_call': 15.0307, 'extract_collect': 0.0134, 'response_build': 2.8477, 'other': 0.0, 'total': 17.9261}}
  - {'turn': 1, 'user': '我是gay，喜欢男生', 'assistant': '谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～', 'latency_s': 14.15, 'perf': {'profile_load': 0.0075, 'context_load': 0.0127, 'profile_save': 0.0075, 'rule_check': 0.0036, 'ai_call': 11.4228, 'extract_collect': 0.0122, 'response_build': 2.6913, 'other': 0.0, 'total': 14.1501}}
- contact_transition_abrupt
  - {'turn': 10, 'user': '单身', 'assistant': '资料我这边先了解得差不多啦～方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 1.849, 'perf': {'profile_load': 0.0105, 'context_load': 0.0135, 'rule_check': 0.0055, 'profile_save': 0.0049, 'extract_collect': 0.0097, 'response_build': 1.8133, 'other': 0.0, 'total': 1.8494}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_00d4ac02', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_41ce6e69', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_invalid_should_retry', 'session_id': 'realism_14_d0458ed3', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_bbf385a6', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_41ce6e69', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_9f4728fe', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_user_says_phone_inconvenient_then_wechat', 'session_id': 'realism_31_d76443c8', 'expected': 'abc123', 'actual': 'wxabc123', 'note': ''}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_1d7c60ea', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_cdc169bb', 'expected': '17688654321', 'actual': None, 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_17ed8305', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_68f36898', 'expected': '离婚', 'actual': None, 'note': ''}
  - {'scenario_id': 'safety_high_risk_legal_query_guard', 'session_id': 'realism_129_a10b24c8', 'expected': '离婚', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_4329c0f4', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_82c3bcb2', 'expected': '30', 'actual': 36, 'note': ''}
  - {'scenario_id': 'safety_conflict_info_should_confirm', 'session_id': 'realism_132_ac8e97f9', 'expected': '35', 'actual': 36, 'note': ''}
### policy
- low_priority_never_ask_last_name
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_359d1e1e', 'expected': '0', 'actual': 1, 'note': ''}
  - {'scenario_id': 'contact_confirm_word_then_wechat_fallback', 'session_id': 'realism_20_5b3d24f0', 'expected': '0', 'actual': 1, 'note': ''}
- ack_overuse
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_359d1e1e', 'expected': '<=0.35', 'actual': 0.4, 'note': ''}
  - {'scenario_id': 'abuse_user_rude_language_deescalation', 'session_id': 'realism_3_5f8b62a4', 'expected': '<=0.35', 'actual': 0.5, 'note': ''}
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_00d4ac02', 'expected': '<=0.35', 'actual': 1.0, 'note': ''}
- field_interleaving_quality
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_82c3bcb2', 'expected': '<=3 core asks streak', 'actual': 4, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_134_71e1b61e', 'expected': '<=1', 'actual': 2, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 14 次 (4.8%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 10 次 (3.4%): `收到啦那你现在主要在哪个城市工作生活呀`
- 9 次 (3.0%): `我先记下来啦顺带问下你是男生还是女生呀`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 8 次 (2.7%): `好哒那想问下你今年多大呀`
- 7 次 (2.4%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 5 次 (1.7%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 5 次 (1.7%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 64
- 通过率: 95.5%
- contact_phone_then_wechat_prompt (realism_6_00d4ac02): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_7_bbf385a6): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_refused_then_user_provides_wechat (realism_11_41ce6e69): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_invalid_should_retry (realism_14_d0458ed3): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_asks_wechat_instead_of_phone (realism_21_9f4728fe): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_phone_inconvenient_then_wechat (realism_31_d76443c8): ["wechat_matches_user_stated: expected='abc123', actual='wxabc123'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_1d7c60ea): ["wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_invalid_then_valid (realism_34_3d8c7444): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_with_86_prefix (realism_36_a4fe71ed): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_wechat_mobile_format (realism_39_25e1fd41): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 partner_requirement_when_mentioned: 14 次
- 高频失败 location_truthy: 12 次
- 高频失败 location_matches_user_stated: 12 次
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 age_matches_user_stated: 3 次
- 高频失败 partner_requirement_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 2 次
- 高频失败 occupation_matches_user_stated: 2 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 50
- 通过率: 97.6%
- abuse_repeated_ack_should_not_loop_contact (realism_2_359d1e1e): ["low_priority_never_ask_last_name: expected='0', actual=1", "ack_overuse: expected='<=0.35', actual=0.4"]
- abuse_user_rude_language_deescalation (realism_3_5f8b62a4): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_phone_then_wechat_prompt (realism_6_00d4ac02): ["ack_overuse: expected='<=0.35', actual=1.0"]
- contact_wechat_rejection_should_not_end (realism_8_dfd79191): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_phone_with_spaces_should_collect (realism_16_2923f467): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_hk_phone_then_wechat (realism_17_a404843f): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_confirm_word_after_phone_prompt (realism_19_ce83e350): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_confirm_word_then_wechat_fallback (realism_20_5b3d24f0): ["low_priority_never_ask_last_name: expected='0', actual=1"]
- contact_phone_with_text_prefix_should_collect (realism_27_a186c4e4): ["ack_overuse: expected='<=0.35', actual=0.5"]
- contact_user_explicit_wechat_preference (realism_28_84a51b4a): ["ack_overuse: expected='<=0.35', actual=0.5"]
- 高频失败 ack_overuse: 46 次
- 高频失败 low_priority_never_ask_last_name: 2 次
- 高频失败 field_interleaving_quality: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
