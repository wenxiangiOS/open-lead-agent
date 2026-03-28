# 真实 AI 回归报告

- 开始时间: 2026-03-28T12:48:30
- 结束时间: 2026-03-28T14:01:36
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 108
- 通过: 97
- 失败: 11
- 总耗时: 4385.647s
- 平均耗时: 40.608s
- 最长耗时: 1172.387s
- Token: 698184 (调用 117 次)

## 失败归因汇总

- `response_content`: 13

## 结果概览

- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `PASS` `ending_spam_user_variant` | category=`ending` | tags=`spam_user`
- `PASS` `ending_spam_user_aggressive` | category=`ending` | tags=`spam_user`
- `PASS` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
- `PASS` `ending_gay_user_variant` | category=`ending` | tags=`ending_gate, lgbt`
- `PASS` `ending_divorce_incomplete_variant` | category=`ending` | tags=`divorce`
- `PASS` `ending_proxy_user_variant` | category=`ending` | tags=`ending_gate, proxy_user`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_contact_why_phone` | category=`faq` | tags=`critical, faq_priority, contact_why`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_reliable` | category=`faq` | tags=`critical, faq_reliable`
- `PASS` `faq_priority_safety` | category=`faq` | tags=`faq_safety`
- `PASS` `field_multi_info_extract_basic` | category=`field_collection` | tags=`critical, extract_basic`
- `PASS` `field_partner_requirement_should_not_override_location` | category=`field_collection` | tags=`critical, extract_guard`
- `PASS` `field_education_extract_master` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_occupation_extract_programmer` | category=`field_collection` | tags=`extract_basic, extract_guard`
- `PASS` `field_greeting_should_not_fill_profile` | category=`field_collection` | tags=`extract_guard, smoke`
- `PASS` `field_marital_status_divorced` | category=`field_collection` | tags=`extract_basic, marital_status`
- `PASS` `field_income_extract_monthly` | category=`field_collection` | tags=`extract_basic, income`
- `PASS` `field_conflict_partner_requirement_change_once` | category=`field_collection` | tags=`stability, conflict, partner_requirement`
- `PASS` `listener_first_greeting_probe_intent` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, greeting`
- `PASS` `listener_first_zaima_probe_intent` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, greeting`
- `PASS` `listener_first_unstable_opening_clarify_probe_intent` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_clarify`
- `PASS` `listener_first_opening_clarify_then_soft_intent_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_clarify, open_self_intro`
- `PASS` `listener_first_noisy_greeting_probe_intent` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_greeting`
- `PASS` `listener_first_noisy_greeting_clarify` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_clarify`
- `PASS` `listener_first_opening_probe_particle_soft_intent_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_clarify, open_self_intro`
- `PASS` `listener_first_opening_probe_xiankan_soft_intent_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, opening_clarify, open_self_intro`
- `PASS` `listener_first_opening_probe_wenwen_qingkuang_prefix_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, open_self_intro`
- `PASS` `listener_first_opening_probe_wo_wenwen_qingkuang_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, open_self_intro`
- `PASS` `listener_first_opening_faq_does_not_collect_fields` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, faq`
- `FAIL` `listener_first_opening_boundary_contact_refusal_no_push` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary, contact`
- `PASS` `listener_first_opening_profile_provided_no_repeat_field` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, profile`
- `PASS` `listener_first_opening_mixed_faq_priority_over_matchmaking` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, mixed, faq`
- `FAIL` `listener_first_opening_mixed_boundary_priority_over_profile` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, mixed, boundary`
- `PASS` `listener_first_preference_ack_city` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, preference`
- `PASS` `listener_first_mixed_answer_and_fee` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, mixed, faq`
- `PASS` `listener_first_boundary_ack_before_pause` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary`
- `PASS` `listener_first_reliability_then_answer` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, reliability`
- `PASS` `listener_first_privacy_then_answer` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, privacy`
- `PASS` `listener_first_explicit_matchmaking_enters_mainline` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent`
- `PASS` `listener_first_explicit_matchmaking_allows_open_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, open_self_intro`
- `PASS` `listener_first_multi_profile_no_mechanical_repeat` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, multi_profile`
- `PASS` `listener_first_matchmaking_then_multi_profile_stays_contextual` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, multi_profile`
- `PASS` `listener_first_mixed_answer_and_boundary` | category=`humanlike_listener_first` | tags=`humanlike, listener_first, mixed, boundary`
- `PASS` `listener_first_boundary_opening_no_collection` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary`
- `PASS` `listener_first_latest_location_prefers_occupation` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, contextual_followup`
- `FAIL` `humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot` | category=`humanlike_mainline` | tags=`critical, humanlike, divorce, mainline`
- `FAIL` `humanlike_resume_profile_collection_does_not_jump_to_contact` | category=`humanlike_mainline` | tags=`critical, humanlike, resume_mainline, contact_guard`
- `FAIL` `humanlike_phone_refusal_wechat_followup_has_complete_sentence` | category=`humanlike_mainline` | tags=`critical, humanlike, contact, delivery`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `FAIL` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `PASS` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `PASS` `humanlike_shadow_profile_location_to_occupation_bridge` | category=`humanlike_memory` | tags=`critical, memory, shadow_profile, bridge`
- `PASS` `humanlike_occupation_income_main_slot_prefers_occupation` | category=`humanlike_transition` | tags=`critical, transition, side_target`
- `PASS` `humanlike_age_collected_then_gender_marital_should_not_reask_age` | category=`humanlike_transition` | tags=`critical, no_repeat, bridge_guard`
- `PASS` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_no_large_repeat_profile` | category=`humanlike_memory` | tags=`memory`
- `PASS` `matchmaker_boundary_not_convenient_field` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary`
- `PASS` `matchmaker_boundary_questioned_too_much` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary, complaint`
- `PASS` `matchmaker_boundary_topic_shift_before_data` | category=`matchmaker_boundary` | tags=`critical, humanlike, topic_shift`
- `PASS` `matchmaker_mixed_answer_fee` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, faq`
- `PASS` `matchmaker_mixed_contact_fee` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, faq, contact`
- `PASS` `matchmaker_mixed_preference_reliability` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, reliability`
- `PASS` `policy_core_field_priority_over_quasi` | category=`policy_priority` | tags=`critical, field_priority, smoke`
- `PASS` `policy_quasi_core_marital_status_once_only` | category=`policy_ask_limit` | tags=`critical, marital_status, ask_limit`
- `PASS` `policy_core_field_twice_max` | category=`policy_ask_limit` | tags=`critical, ask_limit, core_field`
- `PASS` `policy_medium_field_once_max` | category=`policy_ask_limit` | tags=`critical, ask_limit, medium_field`
- `PASS` `policy_multi_field_extract_single_sentence` | category=`policy_extraction` | tags=`critical, multi_extract`
- `PASS` `policy_contact_trigger_insufficient_fields` | category=`policy_contact` | tags=`critical, contact_trigger`
- `FAIL` `policy_contact_trigger_sufficient_fields` | category=`policy_contact` | tags=`critical, contact_trigger`
- `PASS` `policy_faq_answer_then_resume` | category=`policy_faq` | tags=`critical, faq_resume`
- `PASS` `policy_reception_before_ask` | category=`policy_humanlike` | tags=`critical, reception, humanlike`
- `PASS` `policy_transition_between_fields` | category=`policy_humanlike` | tags=`critical, transition, humanlike`
- `PASS` `policy_first_turn_greeting_ack` | category=`policy_first_turn` | tags=`critical, first_turn, greeting`
- `PASS` `policy_cooldown_no_consecutive_same_field` | category=`policy_cooldown` | tags=`critical, cooldown`
- `PASS` `policy_income_soft_ask` | category=`policy_income` | tags=`critical, income, soft_ask`
- `PASS` `policy_partner_requirement_continuous_extract` | category=`policy_extraction` | tags=`critical, partner_requirement`
- `PASS` `policy_emotion_defensive_explain` | category=`policy_emotion` | tags=`emotion, defensive`
- `FAIL` `policy_memory_reuse_location` | category=`policy_memory` | tags=`memory, reuse`
- `PASS` `policy_memory_reuse_preference` | category=`policy_memory` | tags=`memory, reuse`
- `PASS` `policy_low_info_huitouzaishuo_pause` | category=`policy_low_info` | tags=`critical, low_info`
- `PASS` `policy_mixed_answer_and_faq` | category=`policy_mixed` | tags=`critical, mixed, faq`
- `PASS` `policy_opening_location_occupation_prefers_low_pressure_core` | category=`policy_opening` | tags=`critical, opening, contextual_target`
- `PASS` `policy_opening_location_occupation_fee_answers_first` | category=`policy_opening` | tags=`critical, opening, mixed, faq`
- `PASS` `policy_latest_location_followup_prefers_occupation` | category=`policy_opening` | tags=`critical, contextual_target, followup`
- `PASS` `policy_opening_multi_field_shadow_profile_skips_location_age` | category=`policy_opening` | tags=`critical, opening, shadow_profile, multi_field`
- `FAIL` `policy_withdraw_first_time_without_contact_retains_once` | category=`policy_withdraw` | tags=`critical, withdraw, retention`
- `FAIL` `policy_withdraw_second_time_without_contact_soft_closes` | category=`policy_withdraw` | tags=`critical, withdraw, soft_close`
- `PASS` `policy_withdraw_after_contact_collected_closes_immediately` | category=`policy_withdraw` | tags=`critical, withdraw, contact_complete`
- `PASS` `policy_mixed_location_and_boundary` | category=`policy_mixed` | tags=`mixed, boundary`

## 失败详情

### faq_priority_can_add_wechat

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json`
- 分类: `faq`
- 标签: `critical, faq_priority`
- 描述: 用户问能不能直接加对方微信时，应先说明由牵线同事安排互换。
- 断言通过: 2/3
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json --scenario-id faq_priority_can_add_wechat --verbose`
- 失败摘要:
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['加对方微信']，实际 '这个不会一上来就直接加对方微信，前面会先把双方情况沟通清楚；后面如果真要继续，也会先和你确认'
- 失败轮次精简回放:
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 这个不会一上来就直接加对方微信，前面会先把双方情况沟通清楚；后面如果真要继续，也会先和你确认
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 行呀，那你可以先简单说说自己，我顺着了解会更顺一点
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 这个不会一上来就直接加对方微信，前面会先把双方情况沟通清楚；后面如果真要继续，也会先和你确认

### listener_first_opening_boundary_contact_refusal_no_push

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, boundary, contact`
- 描述: 开场直接说不给电话时，应先接住边界，不继续推电话微信，也不切资料字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_opening_boundary_contact_refusal_no_push --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['可以', '不强求', '不留也行', '先聊']，实际 '行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来'
- 失败轮次精简回放:
  - Turn 2 用户: 不给电话行不行
    AI: 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，在的。 你是想认真聊聊，还是先问问情况呀？
  - Turn 2 用户: 不给电话行不行
    AI: 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来

### listener_first_opening_mixed_boundary_priority_over_profile

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, mixed, boundary`
- 描述: 开场同时说不给电话并给出性别时，应优先接住边界，而不是顺着资料继续追问。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_opening_mixed_boundary_priority_over_profile --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['可以', '不强求', '不留也行', '先聊']，实际 '好，你这边是男生。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来'
- 失败轮次精简回放:
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 好，你这边是男生。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，在的。 你是想认真聊聊，还是先问问情况呀？
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 好，你这边是男生。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来

### humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, divorce, mainline`
- 描述: 用户说明离异并确认手续已办妥后，系统应自然回到资料主线，而不是停在空承接或直接切联系方式。
- 断言通过: 3/5
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot --verbose`
- 失败摘要:
  - [response_contains_any] turn=7 turn=7 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '那就没问题了。 你这边方便留个电话吗？'
  - [response_not_contains_any] turn=7 turn=7 不应包含关键词 ['电话']，实际 '那就没问题了。 你这边方便留个电话吗？'
- 失败轮次精简回放:
  - Turn 7 用户: 办理好了
    AI: 那就没问题了。 你这边方便留个电话吗？
- 对话回放:
  - Turn 1 用户: 男的
    AI: 好，你这边是男生。 好的，那你现在主要在哪个城市生活呀？
  - Turn 2 用户: 90后
    AI: 好，90后我知道了。 好呀，你的学历背景大概是怎样的？
  - Turn 3 用户: 深圳
    AI: 你现在在深圳这边主要做什么呀？ 说到这儿，你会更看重对方哪方面？
  - Turn 4 用户: 本科
    AI: 90后是吧，那你现在是单身状态在了解吗？ 你要是方便，也可以说说你想找个什么样的。
  - Turn 5 用户: 我是做it的
    AI: 你做IT这行的话，收入大概在哪个范围？
  - Turn 6 用户: 我离异过呢
    AI: 可以的，我想先确认一下，你这边离婚手续已经办妥了吗？
  - Turn 7 用户: 办理好了
    AI: 那就没问题了。 你这边方便留个电话吗？

### humanlike_resume_profile_collection_does_not_jump_to_contact

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, resume_mainline, contact_guard`
- 描述: 当用户催系统继续问资料时，应继续主线资料，不应突然切到手机号或微信。
- 断言通过: 0/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_resume_profile_collection_does_not_jump_to_contact --verbose`
- 失败摘要:
  - [response_contains_any] turn=8 turn=8 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '你要是现在不太方便细说也没事。 留个常用手机号就行，后面真有合适的，我们也能继续联系上你'
  - [response_not_contains_any] turn=8 turn=8 不应包含关键词 ['手机号']，实际 '你要是现在不太方便细说也没事。 留个常用手机号就行，后面真有合适的，我们也能继续联系上你'
- 失败轮次精简回放:
  - Turn 8 用户: 你不问其他了？
    AI: 你要是现在不太方便细说也没事。 留个常用手机号就行，后面真有合适的，我们也能继续联系上你
- 对话回放:
  - Turn 1 用户: 男的
    AI: 好，好，你这边是男生。 好的，你现在主要在哪个城市生活呀？
  - Turn 2 用户: 90后
    AI: 好，90后我知道了。 我先接住了。 那我再了解下，你大概是什么学历呀？ 后面我也更好往相对合适的方向帮你看。
  - Turn 3 用户: 深圳
    AI: 你现在在深圳这边主要做什么呀？ 你要是愿意，也可以顺手说说你比较在意对方什么。
  - Turn 4 用户: 本科
    AI: 这个年龄段我知道了，那你现在感情状态是单身吗？ 你要是愿意，也可以顺手说说你比较在意对方什么。
  - Turn 5 用户: 我是做it的
    AI: 你要是方便，也可以说说你想找个什么样的。
  - Turn 6 用户: 我离异过呢
    AI: 可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？
  - Turn 7 用户: 办理好了
    AI: 好，那就行。 要是你愿意，留个电话也行
  - Turn 8 用户: 你不问其他了？
    AI: 你要是现在不太方便细说也没事。 留个常用手机号就行，后面真有合适的，我们也能继续联系上你

### humanlike_phone_refusal_wechat_followup_has_complete_sentence

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, contact, delivery`
- 描述: 电话拒绝后转微信时，回复应是完整句，不能再出现半句尾巴或空截断。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_phone_refusal_wechat_followup_has_complete_sentence --verbose`
- 失败摘要:
  - [response_contains_any] turn=4 turn=4 需要包含任一关键词 ['微信', '不想留我们先往下聊', '不想留也行', '继续聊']，实际 '没关系，这块我先不追问，我们先按你舒服的节奏来'
- 失败轮次精简回放:
  - Turn 4 用户: 不方便留电话
    AI: 没关系，这块我先不追问，我们先按你舒服的节奏来
- 对话回放:
  - Turn 1 用户: 我是男的，90后，深圳，本科，做it的，离异，手续已经办妥了
    AI: 好，这个状态我知道了。 好，这个状态我清楚了。 你会更看重对方哪一点呀？
  - Turn 2 用户: 我想找个年龄别太大的
    AI: <coroutine object ChatService._build_no_ai_response at 0x107b20220>
  - Turn 3 用户: 你不问其他了？
    AI: 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来
  - Turn 4 用户: 不方便留电话
    AI: 没关系，这块我先不追问，我们先按你舒服的节奏来

### humanlike_transition_with_feedback

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_regression.json`
- 分类: `humanlike_transition`
- 标签: `transition`
- 描述: 转场时应包含承接上一句和反馈/认可。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_regression.json --scenario-id humanlike_transition_with_feedback --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['不错', '好的', '了解', '运营', '好哒', '记下', '收到']，实际 '感情状态这边我也顺手确认一下，你现在是单身状态吗？'
- 失败轮次精简回放:
  - Turn 2 用户: 我是做运营的
    AI: 感情状态这边我也顺手确认一下，你现在是单身状态吗？
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，深圳，本科
    AI: 女生，明白了。 那你现在在深圳主要做哪方面工作呀？ 你对另一半大概有什么要求呀？
  - Turn 2 用户: 我是做运营的
    AI: 感情状态这边我也顺手确认一下，你现在是单身状态吗？

### policy_contact_trigger_sufficient_fields

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_contact`
- 标签: `critical, contact_trigger`
- 描述: 联系方式触发条件：拿到4个及以上核心/准核心字段后，可进入联系方式逻辑。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_contact_trigger_sufficient_fields --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['电话', '微信', '联系']，实际 '做运营的话，收入这块大概在什么区间呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 做运营的话，收入这块大概在什么区间呀？
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 做运营的话，收入这块大概在什么区间呀？

### policy_memory_reuse_location

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_memory`
- 标签: `memory, reuse`
- 描述: 记忆回用：AI应记住用户已说过的地区信息并在后续回复中自然回用。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_memory_reuse_location --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '那边']，实际 '行呀，那你可以先简单说说自己，我顺着了解会更顺一点'
- 失败轮次精简回放:
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 行呀，那你可以先简单说说自己，我顺着了解会更顺一点
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营
    AI: 好，女生是吧。 说到这儿，你会更看重对方哪方面？
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 行呀，那你可以先简单说说自己，我顺着了解会更顺一点

### policy_withdraw_first_time_without_contact_retains_once

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_withdraw`
- 标签: `critical, withdraw, retention`
- 描述: 未拿到联系方式时，用户第一次说不聊了，应轻挽留一次，不继续追字段也不推进联系方式。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_withdraw_first_time_without_contact_retains_once --verbose`
- 失败摘要:
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['怎么了', '顾虑', '担心', '不想继续聊', '不想继续']，实际 '我顺手确认下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 3 用户: 不聊了
    AI: 我顺手确认下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，你也可以先简单介绍下自己，我顺着了解会更自然一点
  - Turn 2 用户: 我在深圳，今年29岁
    AI: 我先接住了。 哈哈在深圳生活节奏还是挺快的对吧~ 你目前的最高学历是什么呀？
  - Turn 3 用户: 不聊了
    AI: 我顺手确认下，你这边是男生还是女生呀？

### policy_withdraw_second_time_without_contact_soft_closes

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_withdraw`
- 标签: `critical, withdraw, soft_close`
- 描述: 未拿到联系方式时，第一次轻挽留后，用户再次表达不想聊，应直接轻收尾，不再二次追问顾虑。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_withdraw_second_time_without_contact_soft_closes --verbose`
- 失败摘要:
  - [response_contains_any] turn=4 turn=4 需要包含任一关键词 ['先这样', '不打扰', '先收住', '想继续聊', '再来找我']，实际 '我顺手确认下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 4 用户: 还是先不聊了
    AI: 我顺手确认下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，你也可以先简单介绍下自己，我顺着了解会更自然一点
  - Turn 2 用户: 我在深圳，今年29岁
    AI: 好，好，深圳这边我知道了。 挺好的，我都记下啦，你目前是什么学历呀？
  - Turn 3 用户: 不聊了
    AI: 你这边是男生还是女生呀？
  - Turn 4 用户: 还是先不聊了
    AI: 我顺手确认下，你这边是男生还是女生呀？
