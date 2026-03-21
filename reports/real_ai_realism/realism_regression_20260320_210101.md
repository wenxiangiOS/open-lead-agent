# 真实用户仿真回归报告

- 会话数: 138
- 总轮次: 295
- 总耗时(墙钟): 2915.65s
- 累计会话耗时: 2914.74s
- 失败检查数: 122
- 失败分布: turn=5, field=53, policy=64
- 时延 p95: 18.051s
- 时延 p99: 18.081s
- 模板化 Top1 占比: 3.4%
- Token: 1078186 (调用 195 次)
- 阈值配置: ack_overuse<=0.25, core_streak<=2

## 核心结论

- 拟人化收集通过率: 97.1%
- 字段提取综合通过率: 96.2%
- 字段精确匹配通过率: 94.7%
- 字段完整性通过率: 96.9%

## 拟人化收集质量

- 总检查数: 2365
- 失败检查数: 69
- Turn 级失败: 5
- 策略级失败: 64
- 模板化 Top1 占比: 3.4%
- 时延 p95: 18.051s
- 时延 p99: 18.081s
- 高频 turn 失败 preference_triggered_unexpected_ending: 2 次
- 高频 turn 失败 invalid_wechat_not_retried: 1 次
- 高频 turn 失败 nonsense_not_guided: 1 次
- 高频 turn 失败 confirm_word_misrouted_to_contact: 1 次
- 高频策略失败 ack_overuse: 53 次
- 高频策略失败 field_interleaving_quality: 5 次
- 高频策略失败 low_priority_never_ask_last_name: 3 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次
- 高频策略失败 income_question_soft_tone: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次

## 字段提取准确性

- 总检查数: 1413
- 失败检查数: 53
- 综合通过率: 96.2%
- 精确匹配检查数: 397
- 精确匹配失败数: 21
- 精确匹配通过率: 94.7%
- 完整性检查数: 1016
- 完整性失败数: 32
- 完整性通过率: 96.9%
- 高频字段失败 partner_requirement_when_mentioned: 13 次
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 location_truthy: 8 次
- 高频字段失败 location_matches_user_stated: 8 次
- 高频字段失败 marital_status_matches_user_stated: 4 次
- 高频字段失败 partner_requirement_matches_user_stated: 4 次
- 高频字段失败 age_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 68.2% (15/22)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 26.8% (79/295)
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
- 收尾自然度: 42.9% (9/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 36.5%
- 动作一致性分: 62.5%

## 隔离质量

- 会话数: 138
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.344
- p95 连续提问轮次: 3.0
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 5.1% (7/138)

## 提取诊断

- 字段冲突修复率: 0.0% (0/2)
- 证据链覆盖率: 72.1% (320/444)
- 失败类型 other: 24 次
- 失败类型 missed_stated_field: 14 次
- 失败类型 missing_extraction: 8 次
- 失败类型 wrong_value_or_normalization: 7 次

## 联系方式质量专项

- 联系方式成功率: 67.5% (27/40)
- 无效电话未重试: 0 次
- 无效微信未重试: 1 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 12.4058s
- total: 9.5251s
- response_build: 0.4484s
- rule_check: 0.1446s
- extract_collect: 0.0152s
- context_load: 0.0139s
- profile_load: 0.0095s
- profile_save: 0.0082s
- other: 0.0017s

## 意图分桶时延

- general: avg=9.92s p95=18.053s max=20.301s n=280
- fee: avg=2.202s p95=2.506s max=2.612s n=7
- reliability: avg=2.174s p95=2.43s max=2.444s n=4
- match: avg=2.163s p95=2.294s max=2.309s n=2
- photo: avg=1.742s p95=1.742s max=1.742s n=1
- safety: avg=2.184s p95=2.184s max=2.184s n=1
- 秒回率(<1s): 6.1%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.7%

## 失败样本（自动抽样）

### turn
- invalid_wechat_not_retried
  - {'turn': 3, 'user': '那我微信wx123456', 'assistant': '要是你电话方便的话，也可以留一个，后面联系会更及时些～', 'latency_s': 13.989, 'perf': {'profile_load': 0.0101, 'context_load': 0.0144, 'rule_check': 0.004, 'profile_save': 0.0096, 'ai_call': 13.9434, 'extract_collect': 0.0134, 'response_build': 0.0009, 'other': 0.0, 'total': 13.9887}}
- preference_triggered_unexpected_ending
  - {'turn': 1, 'user': '我是les，喜欢女生', 'assistant': '谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～', 'latency_s': 20.295, 'perf': {'profile_load': 0.0041, 'context_load': 0.0169, 'profile_save': 0.0043, 'rule_check': 0.003, 'ai_call': 18.0042, 'extract_collect': 0.0054, 'response_build': 2.2586, 'other': 0.0, 'total': 20.2949}}
  - {'turn': 1, 'user': '我是gay，喜欢男生', 'assistant': '感谢你的信任～我们专注做异性相亲，可能帮不到你呢～不过现在有很多专业的平台，相信你能找到合适的！祝你幸福～', 'latency_s': 14.118, 'perf': {'profile_load': 0.0084, 'context_load': 0.0334, 'profile_save': 0.0126, 'rule_check': 0.0235, 'ai_call': 11.569, 'extract_collect': 0.0144, 'response_build': 2.484, 'other': 0.0, 'total': 14.1182}}
- nonsense_not_guided
  - {'turn': 1, 'user': '17688654321', 'assistant': '也可以留一个，后面沟通会更顺手一点～', 'latency_s': 10.715, 'perf': {'profile_load': 0.0097, 'context_load': 0.017, 'profile_save': 0.0143, 'rule_check': 0.0043, 'ai_call': 10.6516, 'extract_collect': 0.0186, 'response_build': 0.0045, 'other': 0.0, 'total': 10.7146}}
- confirm_word_misrouted_to_contact
  - {'turn': 2, 'user': '好的', 'assistant': '你这边资料我先整理好了，后续方便联系推进，方便留个电话吗？后续有合适的同城人选我好及时联系你哦。', 'latency_s': 6.422, 'perf': {'profile_load': 0.0109, 'context_load': 0.0123, 'rule_check': 0.0025, 'profile_save': 0.0024, 'ai_call': 6.385, 'extract_collect': 0.007, 'response_build': 0.0014, 'other': 0.0003, 'total': 6.4217}}
### field
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_bd7279e6', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_a9bdd3e8', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_d27538cb', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_after_wechat_rejection_should_not_end', 'session_id': 'realism_9_6bc4b528', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_d27538cb', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_28_d383ce66', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- location_truthy
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_28_d383ce66', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_59_10c25f13', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_3b9fbb67', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_28_d383ce66', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'faq_priority_mediator', 'session_id': 'realism_59_10c25f13', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_should_not_override_location', 'session_id': 'realism_81_3b9fbb67', 'expected': '深圳', 'actual': None, 'note': ''}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_4efc2ae7', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_6fdbc78c', 'expected': '17688654321', 'actual': None, 'note': ''}
### policy
- low_priority_never_ask_last_name
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_2_e964a83e', 'expected': '0', 'actual': 1, 'note': ''}
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_a68f81ae', 'expected': '0', 'actual': 1, 'note': ''}
  - {'scenario_id': 'contact_confirm_word_then_wechat_fallback', 'session_id': 'realism_20_983e4834', 'expected': '0', 'actual': 1, 'note': ''}
- field_interleaving_quality
  - {'scenario_id': 'abuse_persistent_trolling_should_boundary', 'session_id': 'realism_5_a68f81ae', 'expected': '<=2 core asks streak', 'actual': 3, 'note': ''}
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_82_f7b481cd', 'expected': '<=2 core asks streak', 'actual': 3, 'note': ''}
  - {'scenario_id': 'humanlike_reception_evasive_user', 'session_id': 'realism_101_4837e674', 'expected': '<=2 core asks streak', 'actual': 3, 'note': ''}
- ack_overuse
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_42a13bbd', 'expected': '<=0.25', 'actual': 1.0, 'note': ''}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_bd7279e6', 'expected': '<=0.25', 'actual': 1.0, 'note': ''}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_83b1dd1c', 'expected': '<=0.25', 'actual': 0.5, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_6ecae9fc', 'expected': 0, 'actual': 1, 'note': ''}
- income_question_soft_tone
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_44_6ecae9fc', 'expected': 0, 'actual': 1, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'robustness_long_session_no_drift', 'session_id': 'realism_128_740d6dcd', 'expected': '<=1', 'actual': 2, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 10 次 (3.4%): `小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 9 次 (3.0%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 8 次 (2.7%): `理解你的顾虑这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 6 次 (2.0%): `要是你电话方便的话也可以留一个后面联系会更及时些`
- 5 次 (1.7%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 5 次 (1.7%): `我这边就是负责跟你对接了解情况的小缘呀你要是担心流程隐私或真实性我可以直接跟你说清楚`
- 4 次 (1.4%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 4 次 (1.4%): `小姐姐这个号码好像位数不对呢能确认下是手机号或微信号吗呀`
- 4 次 (1.4%): `小姐姐这个微信号好像格式不太对呢是字母开头的#-#位字符吗呀`
- 4 次 (1.4%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`

## 字段收集质量

- 总检查数: 1413
- 失败检查数: 53
- 通过率: 96.2%
- contact_phone_and_wechat_same_turn (realism_7_bd7279e6): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_after_wechat_rejection_should_not_end (realism_9_6bc4b528): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_a9bdd3e8): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_asks_wechat_instead_of_phone (realism_21_d27538cb): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_user_explicit_wechat_preference (realism_28_d383ce66): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_says_phone_inconvenient_then_wechat (realism_31_7fbeeb73): ['unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_contaminated_mixed_token_retry (realism_33_4efc2ae7): ["wechat_matches_user_stated: expected='wx72378', actual=None"]
- contact_wechat_mobile_format (realism_39_f373dc8b): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_phone_too_short_should_retry (realism_40_5f06bd17): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_too_long_should_retry (realism_41_6fdbc78c): ["phone_matches_user_stated: expected='17688654321', actual=None"]
- 高频失败 partner_requirement_when_mentioned: 13 次
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 location_truthy: 8 次
- 高频失败 location_matches_user_stated: 8 次
- 高频失败 marital_status_matches_user_stated: 4 次
- 高频失败 partner_requirement_matches_user_stated: 4 次
- 高频失败 age_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 2070
- 失败检查数: 64
- 通过率: 96.9%
- abuse_repeated_ack_should_not_loop_contact (realism_2_e964a83e): ["low_priority_never_ask_last_name: expected='0', actual=1"]
- abuse_persistent_trolling_should_boundary (realism_5_a68f81ae): ["low_priority_never_ask_last_name: expected='0', actual=1", "field_interleaving_quality: expected='<=2 core asks streak', actual=3"]
- contact_phone_then_wechat_prompt (realism_6_42a13bbd): ["ack_overuse: expected='<=0.25', actual=1.0"]
- contact_phone_and_wechat_same_turn (realism_7_bd7279e6): ["ack_overuse: expected='<=0.25', actual=1.0"]
- contact_wechat_rejection_should_not_end (realism_8_83b1dd1c): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_phone_invalid_then_valid (realism_15_9ebd5814): ["ack_overuse: expected='<=0.25', actual=0.3333"]
- contact_phone_with_spaces_should_collect (realism_16_05b6f0cf): ["ack_overuse: expected='<=0.25', actual=1.0"]
- contact_hk_phone_then_wechat (realism_17_4ca78ea3): ["ack_overuse: expected='<=0.25', actual=0.5"]
- contact_hk_phone_then_wechat_rejected_not_end (realism_18_fc6cc4e5): ["ack_overuse: expected='<=0.25', actual=0.3333"]
- contact_confirm_word_then_wechat_fallback (realism_20_983e4834): ["low_priority_never_ask_last_name: expected='0', actual=1", "ack_overuse: expected='<=0.25', actual=0.6667"]
- 高频失败 ack_overuse: 53 次
- 高频失败 field_interleaving_quality: 5 次
- 高频失败 low_priority_never_ask_last_name: 3 次
- 高频失败 no_consecutive_same_field_ask: 1 次
- 高频失败 income_question_soft_tone: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
