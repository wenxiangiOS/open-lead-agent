# 真实用户仿真回归报告

- 会话数: 197
- 总轮次: 372
- 总耗时(墙钟): 526.58s
- 累计会话耗时: 523.28s
- 失败检查数: 153
- 失败分布: turn=1, field=117, policy=35
- 时延 p95: 2.56s
- 时延 p99: 2.908s
- 模板化 Top1 占比: 14.8%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 99.0%
- 字段提取综合通过率: 93.5%
- 字段精确匹配通过率: 91.5%
- 字段完整性通过率: 94.1%

## 拟人化收集质量

- 总检查数: 3458
- 失败检查数: 36
- Turn 级失败: 1
- 策略级失败: 35
- 模板化 Top1 占比: 14.8%
- 时延 p95: 2.56s
- 时延 p99: 2.908s
- 高频 turn 失败 preference_triggered_unexpected_ending: 1 次
- 高频策略失败 scenario_assertion::response_contains_any: 11 次
- 高频策略失败 scenario_assertion::profile_field_truthy: 7 次
- 高频策略失败 no_consecutive_same_field_ask: 4 次
- 高频策略失败 scenario_assertion::profile_field_equals: 2 次

## 字段提取准确性

- 总检查数: 1791
- 失败检查数: 117
- 综合通过率: 93.5%
- 精确匹配检查数: 426
- 精确匹配失败数: 36
- 精确匹配通过率: 91.5%
- 完整性检查数: 1365
- 完整性失败数: 81
- 完整性通过率: 94.1%
- 高频字段失败 partner_requirement_when_mentioned: 54 次
- 高频字段失败 location_matches_user_stated: 13 次
- 高频字段失败 location_truthy: 12 次
- 高频字段失败 unexpected_conversation_end: 11 次
- 高频字段失败 partner_requirement_matches_user_stated: 7 次
- 高频字段失败 occupation_matches_user_stated: 6 次
- 高频字段失败 occupation_truthy: 4 次
- 高频字段失败 phone_matches_user_stated: 3 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 age_matches_user_stated: 2 次

## 对话自然度指标

- 情绪承接命中率: 37.9% (11/29)
- FAQ 非复读率: 100.0% (1/1)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/372)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=46.2%, Top1=46.2%, 样本=13
- 意图 reliability: 模板多样性=50.0%, Top1=66.7%, 样本=6
- 意图 match: 模板多样性=50.0%, Top1=50.0%, 样本=4
- 意图 photo: 模板多样性=100.0%, Top1=50.0%, 样本=2
- 意图 safety: 模板多样性=100.0%, Top1=50.0%, 样本=2

## 质量护栏指标

- 字段稳定性分数: 57.1% (改写 6/14)
- 拒绝后尊重率: 62.5% (15/24)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (21/21)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 36.6%
- 动作一致性分: 50.0%

## 隔离质量

- 会话数: 197
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.224
- p95 连续提问轮次: 2.0
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 0.5% (1/197)

## 提取诊断

- 字段冲突修复率: 62.5% (5/8)
- 证据链覆盖率: 77.2% (336/435)
- 失败类型 other: 65 次
- 失败类型 missed_stated_field: 26 次
- 失败类型 missing_extraction: 16 次
- 失败类型 wrong_value_or_normalization: 10 次

## 联系方式质量专项

- 联系方式成功率: 63.6% (28/44)
- 可收集场景成功率: 79.3% (23/29)
- 拒绝/防护场景通过率: 73.3% (11/15)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 1.0515s
- response_build: 0.9712s
- rule_check: 0.199s
- ai_call: 0.0911s
- context_load: 0.0047s
- extract_collect: 0.0026s
- other: 0.0016s
- profile_load: 0.0012s
- profile_save: 0.0006s

## 意图分桶时延

- general: avg=0.945s p95=2.4s max=3.027s n=345
- fee: avg=2.475s p95=3.143s max=3.313s n=13
- reliability: avg=2.488s p95=2.816s max=2.864s n=6
- match: avg=2.318s p95=2.919s max=2.946s n=4
- photo: avg=1.924s p95=1.957s max=1.961s n=2
- safety: avg=2.449s p95=2.749s max=2.782s n=2
- 秒回率(<1s): 50.8%
- FAQ秒回率(<1s): 0.0%
- Model秒回率(<1s): 0.0% (0/0)
- NonAI秒回率(<1s): 1.1% (2/178)
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- preference_triggered_unexpected_ending
  - {'turn': 1, 'user': '我22岁，想找对象', 'assistant': '好呀，这个条件我先记住收下，后面会按这个方向优先筛选，合适的我尽快同步你。有需要再来找我。', 'latency_s': 1.864, 'perf': {'profile_load': 0.0009, 'context_load': 0.0034, 'profile_save': 0.0006, 'rule_check': 0.0008, 'extract_collect': 0.0014, 'response_build': 1.856, 'other': 0.0009, 'total': 1.864}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_6_d8a5b46a', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_421efc76', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_wechat_rejection_should_not_end', 'session_id': 'realism_8_1ad3074f', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- unexpected_conversation_end
  - {'scenario_id': 'contact_phone_and_wechat_same_turn', 'session_id': 'realism_7_421efc76', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_phone_refused_then_user_provides_wechat', 'session_id': 'realism_11_69f48870', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
  - {'scenario_id': 'contact_user_asks_wechat_instead_of_phone', 'session_id': 'realism_21_8d3168d4', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_33_1a1a1921', 'expected': 'wx72378', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'contact_phone_too_long_should_retry', 'session_id': 'realism_41_58f2b3f2', 'expected': '17688654321', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_phone_should_not_pollute_occupation', 'session_id': 'realism_86_5e5e5c1a', 'expected': '17688654321', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_conflict_phone_change_once', 'session_id': 'realism_112_068f49af', 'expected': '17688650001', 'actual': '17688654321', 'note': ''}
- marital_status_matches_user_stated
  - {'scenario_id': 'ending_divorce_confirmed_should_continue', 'session_id': 'realism_49_6940aff4', 'expected': '离异', 'actual': '离异（手续已办妥）', 'note': ''}
  - {'scenario_id': 'ending_divorce_incomplete_variant', 'session_id': 'realism_57_032a2995', 'expected': '离婚', 'actual': None, 'note': ''}
  - {'scenario_id': 'safety_high_risk_legal_query_guard', 'session_id': 'realism_188_a5cf5c50', 'expected': '离婚', 'actual': None, 'note': ''}
- age_matches_user_stated
  - {'scenario_id': 'ending_fake_info_pattern', 'session_id': 'realism_55_ad702ab9', 'expected': '00', 'actual': None, 'note': ''}
  - {'scenario_id': 'field_conflict_age_change_once', 'session_id': 'realism_107_0c29beb4', 'expected': '28', 'actual': 29, 'note': ''}
### policy
- scenario_assertion::response_contains_any
  - {'scenario_id': 'abuse_nonsense_gibberish_multi_turn', 'session_id': 'realism_1_f77da6c0', 'expected': ['可以', '方便', '说说', '我没太看懂'], 'actual': 'fail', 'note': "turn=1 需要包含任一关键词 ['可以', '方便', '说说', '我没太看懂']，实际 '我先不急着推进联系方式，先按你刚说的继续聊会更自然。'"}
  - {'scenario_id': 'abuse_nonsense_gibberish_multi_turn', 'session_id': 'realism_1_f77da6c0', 'expected': ['看得懂', '你可以', '我们可以'], 'actual': 'fail', 'note': "turn=4 需要包含任一关键词 ['看得懂', '你可以', '我们可以']，实际 '方便留个电话吗？后续有合适的人选时联系你～'"}
  - {'scenario_id': 'abuse_user_profanity_should_stay_composed', 'session_id': 'realism_4_4f239e83', 'expected': ['理解', '我们可以', '你方便', '先说'], 'actual': 'fail', 'note': "turn=2 需要包含任一关键词 ['理解', '我们可以', '你方便', '先说']，实际 '我先不急着推进联系方式，先按你刚说的继续聊会更自然。'"}
- scenario_assertion::profile_field_truthy
  - {'scenario_id': 'field_age_parse_birth_year', 'session_id': 'realism_79_76d431fa', 'expected': None, 'actual': 'fail', 'note': 'profile.age 期望为真值，实际 None'}
  - {'scenario_id': 'field_occupation_extract_programmer', 'session_id': 'realism_84_3a6b5676', 'expected': None, 'actual': 'fail', 'note': 'profile.occupation 期望为真值，实际 None'}
  - {'scenario_id': 'field_height_extract_cm', 'session_id': 'realism_94_76f4886b', 'expected': None, 'actual': 'fail', 'note': 'profile.height 期望为真值，实际 None'}
- scenario_assertion::profile_field_equals
  - {'scenario_id': 'field_multi_sentence_extract', 'session_id': 'realism_85_3ee4b64f', 'expected': '深圳', 'actual': 'fail', 'note': "profile.location 期望 '深圳'，实际 None"}
  - {'scenario_id': 'field_last_name_extract_single_surname', 'session_id': 'realism_97_13a16c4f', 'expected': '李', 'actual': 'fail', 'note': "profile.last_name 期望 '李'，实际 None"}
- no_consecutive_same_field_ask
  - {'scenario_id': 'field_stability_education_repeat_same', 'session_id': 'realism_99_7ef22e2f', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'field_stability_marital_repeat_same', 'session_id': 'realism_100_b1f8a7c5', 'expected': 0, 'actual': 1, 'note': ''}
  - {'scenario_id': 'field_stability_education_repeat_same_master', 'session_id': 'realism_103_fa4907ac', 'expected': 0, 'actual': 1, 'note': ''}

## 基线对比

- 检测到退化指标：
- extraction_pass_rate: current=0.9347 baseline=0.962
- template_top1_ratio: current=0.1478 baseline=0.0323

## 优化建议

- 当前未发现显著单阶段瓶颈。

## 总门禁

- global_gate: FAIL
- P0失败数: 1
- P1失败数: 2
- P2失败数: 0
- [P0] refusal_respect_rate: value=0.625 target=0.9
- [P1] field_stability_score: value=0.5714 target=0.9
- [P1] baseline_degradation::extraction_pass_rate: value=0.9347 target=0.962

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => NOT_COVERED (mq endpoint unreachable: http://127.0.0.1:8000)

## 根因分桶

- policy_or_routing: 4
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: extraction_pass_rate
- 2026-03-24T13:39:39 humanlike=0.9896 extraction=0.9347 latency_p95=2.56
- 2026-03-24T13:04:29 humanlike=0.9896 extraction=0.962 latency_p95=17.98
- 2026-03-21T19:06:24 humanlike=0.9983 extraction=0.9667 latency_p95=17.478
- 2026-03-21T16:29:29 humanlike=0.9979 extraction=0.9689 latency_p95=17.714
- 2026-03-21T15:47:56 humanlike=0.9357 extraction=0.8889 latency_p95=2.065
- 2026-03-21T15:32:36 humanlike=0.9983 extraction=0.9384 latency_p95=14.141
- 2026-03-21T14:54:33 humanlike=0.9623 extraction=0.9014 latency_p95=2.213

## MQ补充检查

- covered=False pass=False
- reason: mq endpoint unreachable: http://127.0.0.1:8000

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 4
- 严重失败项数量: 1
- [critical] refusal_respect_rate: value=0.625 target=0.9
- [major] field_stability_score: value=0.5714 target=0.9
- [major] baseline_degradation::extraction_pass_rate: value=0.9347 target=0.962
- [major] baseline_degradation::template_top1_ratio: value=0.1478 target=0.0323

## 模板化风险 Top10

- 55 次 (14.8%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 15 次 (4.0%): `深圳这块我先记住后续会优先按本地匹配给你推进你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 15 次 (4.0%): `深圳那边的资源我们一直在筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 13 次 (3.5%): `我先换个说法继续聊避免重复问你同一个点`
- 12 次 (3.2%): `好的亲那先这样啦有需要随时再来找我哦拜拜👋`
- 12 次 (3.2%): `这边我先不继续追问啦有需要再来找我`
- 11 次 (3.0%): `方便留个电话吗后续有合适的人选时联系你`
- 10 次 (2.7%): `你提到深圳我先按同城方向优先帮你看更匹配的人选你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 8 次 (2.1%): `好这块你现在不太想展开也正常这轮我先不追问资料你要是想先确认流程隐私或真实性我可以先跟你讲清楚`
- 7 次 (1.9%): `要是你电话方便的话也可以留一个后面联系会更及时些`

## 字段收集质量

- 总检查数: 1791
- 失败检查数: 117
- 通过率: 93.5%
- contact_phone_then_wechat_prompt (realism_6_d8a5b46a): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_and_wechat_same_turn (realism_7_421efc76): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_rejection_should_not_end (realism_8_1ad3074f): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_after_wechat_rejection_should_not_end (realism_9_18b8c787): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_wechat_fallback (realism_10_2d4c81b6): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_refused_then_user_provides_wechat (realism_11_69f48870): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", 'unexpected_conversation_end: expected=False, actual=True (profile contains serviceable info and should normally continue collection)']
- contact_wechat_only_then_ask_phone (realism_12_d9b13944): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_wechat_only_then_phone_refusal (realism_13_5b86e975): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_invalid_should_retry (realism_14_c65176d9): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_phone_invalid_then_valid (realism_15_5666f29d): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- 高频失败 partner_requirement_when_mentioned: 54 次
- 高频失败 location_matches_user_stated: 13 次
- 高频失败 location_truthy: 12 次
- 高频失败 unexpected_conversation_end: 11 次
- 高频失败 partner_requirement_matches_user_stated: 7 次
- 高频失败 occupation_matches_user_stated: 6 次
- 高频失败 occupation_truthy: 4 次
- 高频失败 phone_matches_user_stated: 3 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 age_matches_user_stated: 2 次

## 对话策略规则质量

- 总检查数: 3280
- 失败检查数: 35
- 通过率: 98.9%
- abuse_nonsense_gibberish_multi_turn (realism_1_f77da6c0): ["response_contains_any: turn=1 需要包含任一关键词 ['可以', '方便', '说说', '我没太看懂']，实际 '我先不急着推进联系方式，先按你刚说的继续聊会更自然。'", "response_contains_any: turn=4 需要包含任一关键词 ['看得懂', '你可以', '我们可以']，实际 '方便留个电话吗？后续有合适的人选时联系你～'"]
- abuse_user_profanity_should_stay_composed (realism_4_4f239e83): ["response_contains_any: turn=2 需要包含任一关键词 ['理解', '我们可以', '你方便', '先说']，实际 '我先不急着推进联系方式，先按你刚说的继续聊会更自然。'"]
- abuse_persistent_trolling_should_boundary (realism_5_02af71a6): ["response_contains_any: turn=4 需要包含任一关键词 ['先把问题说清楚', '我们可以', '你最关心', '我先回答']，实际 '方便留个电话吗？后续有合适的人选时联系你～'"]
- contact_phone_then_wechat_prompt (realism_6_d8a5b46a): ["final_response_contains_any: final_response 需要包含任一关键词 ['微信', '留一个', '沟通']，实际 '深圳这块我先记住，后续会优先按本地匹配给你推进。我先换个说法继续聊，避免重复问你同一个点。'"]
- contact_phone_refused_then_wechat_fallback (realism_10_2d4c81b6): ["response_contains_any: turn=3 需要包含任一关键词 ['微信']，实际 '好，这块你现在不太想展开也正常。这轮我先不追问资料。你要是想先确认流程、隐私或真实性，我可以先跟你讲清楚。'"]
- contact_hk_phone_then_wechat (realism_17_ef144def): ["final_response_contains_any: final_response 需要包含任一关键词 ['微信', '留一个']，实际 '我先换个说法继续聊，避免重复问你同一个点。'"]
- contact_user_says_no_contact_at_all (realism_25_774eb906): ["response_contains_any: turn=3 需要包含任一关键词 ['微信', '电话', '联系']，实际 '我先换个说法继续聊，避免重复问你同一个点。'"]
- faq_identity_are_you_ai (realism_73_4ea57c42): ["response_contains_any: turn=2 需要包含任一关键词 ['红娘', '同城脱单联盟', '牵线']，实际 '我这边就是负责跟你对接了解情况的小缘呀，你要是担心流程、隐私或真实性，我可以直接跟你说清楚。'"]
- faq_identity_are_you_robot (realism_74_79440099): ["response_contains_any: turn=2 需要包含任一关键词 ['红娘', '牵线', '同城']，实际 '我这边就是负责跟你对接了解情况的小缘呀，你要是担心流程、隐私或真实性，我可以直接跟你说清楚。'"]
- field_age_parse_birth_year (realism_79_76d431fa): ['profile_field_truthy: profile.age 期望为真值，实际 None']
- 高频失败 scenario_assertion::response_contains_any: 11 次
- 高频失败 scenario_assertion::profile_field_truthy: 7 次
- 高频失败 no_consecutive_same_field_ask: 4 次
- 高频失败 scenario_assertion::profile_field_equals: 2 次
