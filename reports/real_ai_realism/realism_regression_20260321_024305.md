# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 19917.2s
- 累计会话耗时: 19916.27s
- 失败检查数: 98
- 失败分布: turn=2, field=51, policy=45
- 时延 p95: 919.51s
- 时延 p99: 989.786s
- 模板化 Top1 占比: 3.7%
- Token: 1054803 (调用 191 次)
- 阈值配置: ack_overuse<=0.25, core_streak<=2

## 核心结论

- 拟人化收集通过率: 98.0%
- 字段提取综合通过率: 96.4%
- 字段精确匹配通过率: 94.7%
- 字段完整性通过率: 97.0%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 47
- Turn 级失败: 2
- 策略级失败: 45
- 模板化 Top1 占比: 3.7%
- 时延 p95: 919.51s
- 时延 p99: 989.786s
- 高频 turn 失败 preference_triggered_unexpected_ending: 2 次
- 高频策略失败 ack_overuse: 39 次
- 高频策略失败 income_question_soft_tone: 2 次
- 高频策略失败 low_priority_never_ask_height: 2 次
- 高频策略失败 medium_ask_limit_partner_requirement: 2 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 51
- 综合通过率: 96.4%
- 精确匹配检查数: 397
- 精确匹配失败数: 21
- 精确匹配通过率: 94.7%
- 完整性检查数: 1016
- 完整性失败数: 30
- 完整性通过率: 97.0%
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 partner_requirement_when_mentioned: 11 次
- 高频字段失败 location_truthy: 7 次
- 高频字段失败 location_matches_user_stated: 7 次
- 高频字段失败 marital_status_matches_user_stated: 4 次
- 高频字段失败 partner_requirement_matches_user_stated: 4 次
- 高频字段失败 age_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 phone_matches_user_stated: 1 次
- 高频字段失败 occupation_truthy: 1 次

## 对话自然度指标

- 情绪承接命中率: 54.5% (12/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 15.9% (47/295)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=42.9%, Top1=71.4%, 样本=7
- 意图 reliability: 模板多样性=50.0%, Top1=75.0%, 样本=4
- 意图 match: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 photo: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 safety: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 2/2)
- 拒绝后尊重率: 65.2% (15/23)
- 记忆回用准确率: 100.0% (1/1)
- 收尾自然度: 28.6% (6/21)
- 异常恢复率: 100.0% (13/13)
- 人设一致性分: 43.1%
- 动作一致性分: 75.0%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.247
- p95 连续提问轮次: 2.0
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 1.5% (2/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/2)
- 证据链覆盖率: 71.6% (318/444)
- 失败类型 other: 22 次
- 失败类型 missed_stated_field: 14 次
- 失败类型 missing_extraction: 8 次
- 失败类型 wrong_value_or_normalization: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 87.5344s
- total: 67.1567s
- response_build: 3.581s
- rule_check: 0.1402s
- context_load: 0.0145s
- extract_collect: 0.0141s
- profile_load: 0.0092s
- profile_save: 0.0083s
- other: 0.0018s

## 意图分桶时延

- general: avg=70.643s p95=922.825s max=1027.597s n=280
- fee: avg=1.962s p95=2.244s max=2.285s n=7
- reliability: avg=1.987s p95=2.139s max=2.155s n=4
- match: avg=2.298s p95=2.331s max=2.335s n=2
- photo: avg=2.326s p95=2.326s max=2.326s n=1
- safety: avg=2.554s p95=2.554s max=2.554s n=1
- 秒回率(<1s): 5.8%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 7.1%

## 失败样本（自动抽样）

### turn
- preference_triggered_unexpected_ending
  - {'turn': 1, 'user': '我是les，喜欢女生', 'assistant': '谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～', 'latency_s': 18.633, 'perf': {'profile_load': 0.0165, 'context_load': 0.0142, 'profile_save': 0.0124, 'rule_check': 0.0047, 'ai_call': 16.0601, 'extract_collect': 0.0257, 'response_build': 2.5204, 'other': 0.0, 'total': 18.633}}
  - {'turn': 1, 'user': '我是gay，喜欢男生', 'assistant': '谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～', 'latency_s': 20.746, 'perf': {'profile_load': 0.006, 'context_load': 0.0154, 'profile_save': 0.0057, 'rule_check': 0.0038, 'ai_call': 18.0027, 'extract_collect': 0.008, 'response_build': 2.7053, 'other': 0.0, 'total': 20.7458}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_9c46e297', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_d290d4fe', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_7e6bb8c2', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_after_wechat_rejection_should_not_end', 'session_id': 'realism_9_88561718', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_4d5e6063', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_mobile_format', 'session_id': 'realism_39_314c5815', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_4d5e6063', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_0a522e0d', 'expected': '17688654321', 'actual': None, 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_incomplete_should_end', 'session_id': 'realism_42_9eaabb15', 'expected': '离异', 'actual': '离异（手续办理中）', 'note': ''}
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_4fee215d', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_353db795', 'expected': '离婚', 'actual': '离异（手续未办妥）', 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_f3e18519', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_4c12e57f', 'expected': '30', 'actual': 36, 'note': ''}
  - {'scenario_id': 'safety_conflict_info_should_confirm', 'session_id': 'realism_132_b4a843c9', 'expected': '35', 'actual': 36, 'note': ''}
### policy
- ack_overuse
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_a97a9b74', 'expected': '<=0.25', 'actual': 0.4, 'note': ''}
  - {'scenario_id': 'abuse_user_rude_language_deescalation', 'session_id': 'realism_3_83df293c', 'expected': '<=0.25', 'actual': 0.5, 'note': ''}
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_efd43a85', 'expected': '<=0.25', 'actual': 0.5, 'note': ''}
- income_question_soft_tone
  - {'scenario_id': 'contact_user_provides_wechat_after_phone_prompt', 'session_id': 'realism_24_671aaa3c', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_28_2a40ee1a', 'expected': 0, 'actual': 1, 'note': ''}
- low_priority_never_ask_height
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_4c12e57f', 'expected': '0', 'actual': 1, 'note': ''}
  - {'scenario_id': 'field_height_extract_cm', 'session_id': 'realism_94_2c78caa0', 'expected': '0', 'actual': 1, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_f527bbda', 'expected': '<=1', 'actual': 2, 'note': ''}
  - {'scenario_id': 'humanlike_no_premature_skip_without_explicit_refusal', 'session_id': 'realism_134_0b7a0099', 'expected': '<=1', 'actual': 2, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 11 次 (3.7%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 5 次 (1.7%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 5 次 (1.7%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 5 次 (1.7%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 4 次 (1.4%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 4 次 (1.4%): `小姐姐这个号码好像位数不对呢能确认下是手机号或微信号吗呀`
- 4 次 (1.4%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 51
- 通过率: 96.4%
- contact_phone_and_wechat_same_turn (realism_7_9c46e297): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_after_wechat_rejection_should_not_end (realism_9_88561718): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_d290d4fe): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_asks_wechat_instead_of_phone (realism_21_7e6bb8c2): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_says_phone_inconvenient_then_wechat (realism_31_98da45c8): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_4d5e6063): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_314c5815): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_too_long_should_retry (realism_41_0a522e0d): ["phone_matches_user_stated: expected='17688654321', actual=None"]
- ending_divorce_incomplete_should_end (realism_42_9eaabb15): ["marital_status_matches_user_stated: expected='离异', actual='离异（手续办理中）'", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- ending_both_contact_refused (realism_44_bfeb0f6c): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 partner_requirement_when_mentioned: 11 次
- 高频失败 location_truthy: 7 次
- 高频失败 location_matches_user_stated: 7 次
- 高频失败 marital_status_matches_user_stated: 4 次
- 高频失败 partner_requirement_matches_user_stated: 4 次
- 高频失败 age_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 phone_matches_user_stated: 1 次
- 高频失败 occupation_truthy: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 45
- 通过率: 97.8%
- abuse_repeated_ack_should_not_loop_contact (realism_2_a97a9b74): ["ack_overuse: expected='<=0.25', actual=0.4"]
- abuse_user_rude_language_deescalation (realism_3_83df293c): ["ack_overuse: expected='<=0.25', actual=0.5"]
- abuse_persistent_trolling_should_boundary (realism_5_efd43a85): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_phone_then_wechat_prompt (realism_6_3c74b250): ["ack_overuse: expected='<=0.25', actual=1.0"]
- contact_wechat_rejection_should_not_end (realism_8_1380848d): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_phone_invalid_then_valid (realism_15_a9148161): ["ack_overuse: expected='<=0.25', actual=0.3333"]
- contact_phone_with_spaces_should_collect (realism_16_459b4bf6): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_hk_phone_then_wechat (realism_17_111d84be): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_hk_phone_then_wechat_rejected_not_end (realism_18_76a5c0a0): ["ack_overuse: expected='<=0.25', actual=0.3333"]
- contact_confirm_word_after_phone_prompt (realism_19_a78500d5): ["ack_overuse: expected='<=0.25', actual=0.5"]
- 高频失败 ack_overuse: 39 次
- 高频失败 income_question_soft_tone: 2 次
- 高频失败 low_priority_never_ask_height: 2 次
- 高频失败 medium_ask_limit_partner_requirement: 2 次
