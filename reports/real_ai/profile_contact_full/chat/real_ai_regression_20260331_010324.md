# 真实 AI 回归报告

- 开始时间: 2026-03-31T00:14:33
- 结束时间: 2026-03-31T01:03:24
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 114
- 通过: 102
- 失败: 12
- 总耗时: 2930.322s
- 平均耗时: 25.705s
- 最长耗时: 246.872s
- Token: 710535 (调用 123 次)

## 失败归因汇总

- `profile_or_state`: 1
- `response_content`: 14

## 结果概览

- `PASS` `contact_phone_collected_wechat_rejected_resumes_profile_mainline` | category=`contact` | tags=`critical, contact, mainline_resume, humanlike`
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_both_contact_refused_without_contact_no_promise` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat, no_contact`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `PASS` `ending_spam_user_variant` | category=`ending` | tags=`spam_user`
- `PASS` `ending_spam_user_aggressive` | category=`ending` | tags=`spam_user`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
- `PASS` `ending_gay_user_variant` | category=`ending` | tags=`ending_gate, lgbt`
- `PASS` `ending_divorce_incomplete_variant` | category=`ending` | tags=`divorce`
- `PASS` `ending_proxy_user_variant` | category=`ending` | tags=`ending_gate, proxy_user`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_contact_why_phone` | category=`faq` | tags=`critical, faq_priority, contact_why`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_timeline_natural_opening` | category=`faq` | tags=`critical, faq_priority, timeline, paraphrase`
- `FAIL` `faq_priority_timeline_mid_profile_resume_field` | category=`faq` | tags=`critical, faq_priority, timeline, resume_profile`
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
- `FAIL` `listener_first_preference_ack_city` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, preference`
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
- `PASS` `listener_first_service_confirmation_uses_open_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, faq, open_self_intro`
- `FAIL` `humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot` | category=`humanlike_mainline` | tags=`critical, humanlike, divorce, mainline`
- `FAIL` `humanlike_resume_profile_collection_does_not_jump_to_contact` | category=`humanlike_mainline` | tags=`critical, humanlike, resume_mainline, contact_guard`
- `PASS` `humanlike_phone_refusal_wechat_followup_has_complete_sentence` | category=`humanlike_mainline` | tags=`critical, humanlike, contact, delivery`
- `FAIL` `humanlike_service_confirmation_mid_conversation_resumes_mainline` | category=`humanlike_mainline` | tags=`critical, humanlike, mainline, faq, resume_mainline`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `PASS` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
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
- `PASS` `policy_contact_trigger_sufficient_fields` | category=`policy_contact` | tags=`critical, contact_trigger`
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
- `FAIL` `policy_withdraw_after_contact_collected_closes_immediately` | category=`policy_withdraw` | tags=`critical, withdraw, contact_complete`
- `PASS` `policy_mixed_location_and_boundary` | category=`policy_mixed` | tags=`mixed, boundary`

## 失败详情

### ending_normal_complete

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json`
- 分类: `ending`
- 标签: `critical, normal_complete`
- 描述: 所有信息收集完成，正常收尾流程。
- 断言通过: 2/3
- 建议修改方向: 优先检查字段提取、状态更新、收尾状态机或后处理覆盖。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json --scenario-id ending_normal_complete --verbose`
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 你在深圳做运营这块是吧，留个手机号会更方便一点，后面有合适的我也好联系上你。
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 像运营这类工作，你现在月收入大概在哪一档呀？

### faq_priority_timeline_mid_profile_resume_field

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json`
- 分类: `faq`
- 标签: `critical, faq_priority, timeline, resume_profile`
- 描述: 用户在资料收集中途问多久联系时，应先答疑，再回当前资料主线，而不是回开场或承诺马上联系。
- 断言通过: 2/3
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json --scenario-id faq_priority_timeline_mid_profile_resume_field --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['单身', '婚况', '另一半', '看重', '收入']，实际 '按你现在的情况，常见是1-2天会有推进，不过也得先把你的基本情况聊清楚，再看后面怎么往下走'
- 失败轮次精简回放:
  - Turn 2 用户: 你们多久会联系我呀
    AI: 按你现在的情况，常见是1-2天会有推进，不过也得先把你的基本情况聊清楚，再看后面怎么往下走
- 对话回放:
  - Turn 1 用户: 我是男生，深圳，90后，本科，IT
    AI: 我是男生，深圳，90后，本科，IT这个阶段的话，你找对象时会更看重哪方面？
  - Turn 2 用户: 你们多久会联系我呀
    AI: 按你现在的情况，常见是1-2天会有推进，不过也得先把你的基本情况聊清楚，再看后面怎么往下走

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
    AI: 你好呀，在的。 你是想找对象，还是先问问情况都可以
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
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['可以', '不强求', '不留也行', '先聊']，实际 '男生，我大概清楚了。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来'
- 失败轮次精简回放:
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 男生，我大概清楚了。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，在呢。 你先告诉我，你这边是想认真聊聊，还是先看看情况
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 男生，我大概清楚了。 这块你要是现在不想展开，我们就先不追问。 行，我明白你这会儿不太方便。 这块我先不追问，我们先顺着你舒服一点的节奏来

### listener_first_preference_ack_city

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, preference`
- 描述: 用户直接表达偏好时，下一句应先接住偏好里的城市或择偶重点，再推进主问题。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_preference_ack_city --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['深圳', '女生', '偏向', '同城']，实际 '好，你也可以先简单介绍下自己，我先了解下你的情况'
- 失败轮次精简回放:
  - Turn 1 用户: 我喜欢深圳的女生
    AI: 好，你也可以先简单介绍下自己，我先了解下你的情况
- 对话回放:
  - Turn 1 用户: 我喜欢深圳的女生
    AI: 好，你也可以先简单介绍下自己，我先了解下你的情况

### humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, divorce, mainline`
- 描述: 用户说明离异并确认手续已办妥后，系统应自然回到资料主线，而不是停在空承接或直接切联系方式。
- 断言通过: 2/5
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot --verbose`
- 失败摘要:
  - [response_contains_any] turn=6 turn=6 需要包含任一关键词 ['手续', '办妥', '办好']，实际 '电话这块我再轻轻问一句，你要是方便的话，留个常用手机号就行，后面真有合适的，我们也好联系到你。'
  - [response_not_contains_any] turn=6 turn=6 不应包含关键词 ['电话']，实际 '电话这块我再轻轻问一句，你要是方便的话，留个常用手机号就行，后面真有合适的，我们也好联系到你。'
  - [response_not_contains_any] turn=7 turn=7 不应包含关键词 ['电话']，实际 '你这边要是方便的话，留个电话也行。 你做IT这行的话，收入大概在哪个范围？'
- 失败轮次精简回放:
  - Turn 6 用户: 我离异过呢
    AI: 电话这块我再轻轻问一句，你要是方便的话，留个常用手机号就行，后面真有合适的，我们也好联系到你。
  - Turn 7 用户: 办理好了
    AI: 你这边要是方便的话，留个电话也行。 你做IT这行的话，收入大概在哪个范围？
- 对话回放:
  - Turn 1 用户: 男的
    AI: 你这边是男生。 好，你现在主要在哪个城市生活呀？
  - Turn 2 用户: 90后
    AI: 你最高学历是什么？
  - Turn 3 用户: 深圳
    AI: 现在主要在深圳。 平时是做什么工作的？ 另外你找对象时更在意对方哪方面，也可以一起说说。
  - Turn 4 用户: 本科
    AI: 那你现在大概是90后这个年龄段吗？ 感情状态这边现在是单身吗？
  - Turn 5 用户: 我是做it的
    AI: 聊到这儿，留个手机号方便联系吗？
  - Turn 6 用户: 我离异过呢
    AI: 电话这块我再轻轻问一句，你要是方便的话，留个常用手机号就行，后面真有合适的，我们也好联系到你。
  - Turn 7 用户: 办理好了
    AI: 你这边要是方便的话，留个电话也行。 你做IT这行的话，收入大概在哪个范围？

### humanlike_resume_profile_collection_does_not_jump_to_contact

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, resume_mainline, contact_guard`
- 描述: 当用户催系统继续问资料时，应继续主线资料，不应突然切到手机号或微信。
- 断言通过: 0/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_resume_profile_collection_does_not_jump_to_contact --verbose`
- 失败摘要:
  - [response_contains_any] turn=8 turn=8 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '对，我们先把联系方式这条说清楚，其他信息先不往里插'
  - [response_not_contains_any] turn=8 turn=8 不应包含关键词 ['联系方式']，实际 '对，我们先把联系方式这条说清楚，其他信息先不往里插'
- 失败轮次精简回放:
  - Turn 8 用户: 你不问其他了？
    AI: 对，我们先把联系方式这条说清楚，其他信息先不往里插
- 对话回放:
  - Turn 1 用户: 男的
    AI: 男生这边我先记下了。 好，那你现在主要在哪个城市生活呀？
  - Turn 2 用户: 90后
    AI: 好呀，你大概是什么学历呀？ 这样后面我也更好往相对合适的方向看。
  - Turn 3 用户: 深圳
    AI: 现在主要在深圳。 你现在主要做哪方面工作呀？ 说到这儿，你会更看重对方什么？
  - Turn 4 用户: 本科
    AI: 90后这个年龄段我大概有数了。 你现在是单身吗？
  - Turn 5 用户: 我是做it的
    AI: 那我顺手问你一个，留个手机号方便联系吗？
  - Turn 6 用户: 我离异过呢
    AI: 你要是现在对电话这块还有点顾虑我能理解，我这边只是想留个常用手机号，后面有合适进展也好及时联系你。
  - Turn 7 用户: 办理好了
    AI: 你这边要是方便的话，留个电话也行。 像IT这类工作，你现在月收入大概在哪一档呀？
  - Turn 8 用户: 你不问其他了？
    AI: 对，我们先把联系方式这条说清楚，其他信息先不往里插

### humanlike_service_confirmation_mid_conversation_resumes_mainline

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, mainline, faq, resume_mainline`
- 描述: 已经进入资料主线后，用户中途确认是不是帮忙介绍对象，系统应先答疑，再回当前主线，不要重新拉回开场自我介绍或改问性别。
- 断言通过: 2/3
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_service_confirmation_mid_conversation_resumes_mainline --verbose`
- 失败摘要:
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['工作', '做什么', '做哪方面']，实际 '嗯，我们这边就是先把情况聊清楚，再帮你留意合适方向的。 方便说下你的学历吗？'
- 失败轮次精简回放:
  - Turn 3 用户: 你们帮帮忙介绍对象吗？
    AI: 嗯，我们这边就是先把情况聊清楚，再帮你留意合适方向的。 方便说下你的学历吗？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，你也可以先简单介绍下自己，我先了解下你的情况
  - Turn 2 用户: 我在深圳
    AI: 那你现在在深圳主要做哪方面工作呀？ 收入这块你方便的话说个大概就行，月收入一般在哪个区间呀？
  - Turn 3 用户: 你们帮帮忙介绍对象吗？
    AI: 嗯，我们这边就是先把情况聊清楚，再帮你留意合适方向的。 方便说下你的学历吗？

### policy_memory_reuse_location

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_memory`
- 标签: `memory, reuse`
- 描述: 记忆回用：AI应记住用户已说过的地区信息并在后续回复中自然回用。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_memory_reuse_location --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '那边']，实际 '好，你也可以先简单介绍下自己，我先了解下你的情况'
- 失败轮次精简回放:
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 好，你也可以先简单介绍下自己，我先了解下你的情况
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营
    AI: 我是女生，90后，在深圳，本科，运营这个阶段的话，你找对象时会更看重哪方面？
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 好，你也可以先简单介绍下自己，我先了解下你的情况

### policy_withdraw_first_time_without_contact_retains_once

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_withdraw`
- 标签: `critical, withdraw, retention`
- 描述: 未拿到联系方式时，用户第一次说不聊了，应轻挽留一次，不继续追字段也不推进联系方式。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_withdraw_first_time_without_contact_retains_once --verbose`
- 失败摘要:
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['怎么了', '顾虑', '担心', '不想继续聊', '不想继续']，实际 '我再确认一下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 3 用户: 不聊了
    AI: 我再确认一下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 行呀，那你可以先简单说说自己，我先顺着了解下你的情况
  - Turn 2 用户: 我在深圳，今年29岁
    AI: 现在主要在深圳。 你大概是什么学历呀？
  - Turn 3 用户: 不聊了
    AI: 我再确认一下，你这边是男生还是女生呀？

### policy_withdraw_second_time_without_contact_soft_closes

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_withdraw`
- 标签: `critical, withdraw, soft_close`
- 描述: 未拿到联系方式时，第一次轻挽留后，用户再次表达不想聊，应直接轻收尾，不再二次追问顾虑。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_withdraw_second_time_without_contact_soft_closes --verbose`
- 失败摘要:
  - [response_contains_any] turn=4 turn=4 需要包含任一关键词 ['先这样', '不打扰', '先收住', '想继续聊', '再来找我']，实际 '我再确认一下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 4 用户: 还是先不聊了
    AI: 我再确认一下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解
  - Turn 2 用户: 我在深圳，今年29岁
    AI: 深圳发展机会多，生活也挺便利的~ 你是什么学历呀，现在是单身状态吗？
  - Turn 3 用户: 不聊了
    AI: 我再确认一下，你这边是男生还是女生呀？
  - Turn 4 用户: 还是先不聊了
    AI: 我再确认一下，你这边是男生还是女生呀？

### policy_withdraw_after_contact_collected_closes_immediately

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_withdraw`
- 标签: `critical, withdraw, contact_complete`
- 描述: 已经拿到联系方式后，用户第一次说不聊了，应直接业务收尾，不再挽留或继续问资料。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_withdraw_after_contact_collected_closes_immediately --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['等好消息', '提前约时间', '不打扰', '联系前']，实际 '你做IT这行的话，收入大概在哪个范围？'
- 失败轮次精简回放:
  - Turn 2 用户: 不聊了
    AI: 你做IT这行的话，收入大概在哪个范围？
- 对话回放:
  - Turn 1 用户: 我是男的，90后，在深圳，本科，做IT的，单身，想找温柔点的，我电话17688654321
    AI: 你这边是男生。 我先记下了。 对，刚刚是在说微信这块。 你要是愿意的话，留个常用微信就行，不想留也没关系
  - Turn 2 用户: 不聊了
    AI: 你做IT这行的话，收入大概在哪个范围？
