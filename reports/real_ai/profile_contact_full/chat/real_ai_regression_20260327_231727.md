# 真实 AI 回归报告

- 开始时间: 2026-03-27T20:36:39
- 结束时间: 2026-03-27T23:17:27
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 101
- 通过: 85
- 失败: 16
- 总耗时: 9647.212s
- 平均耗时: 95.517s
- 最长耗时: 2309.603s
- Token: 290712 (调用 47 次)

## 失败归因汇总

- `profile_or_state`: 1
- `response_content`: 18

## 结果概览

- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `FAIL` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `PASS` `ending_spam_user_variant` | category=`ending` | tags=`spam_user`
- `PASS` `ending_spam_user_aggressive` | category=`ending` | tags=`spam_user`
- `PASS` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `FAIL` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
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
- `PASS` `listener_first_opening_boundary_contact_refusal_no_push` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary, contact`
- `FAIL` `listener_first_opening_profile_provided_no_repeat_field` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, profile`
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
- `FAIL` `listener_first_boundary_opening_no_collection` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary`
- `PASS` `listener_first_latest_location_prefers_occupation` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, contextual_followup`
- `FAIL` `humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot` | category=`humanlike_mainline` | tags=`critical, humanlike, divorce, mainline`
- `FAIL` `humanlike_resume_profile_collection_does_not_jump_to_contact` | category=`humanlike_mainline` | tags=`critical, humanlike, resume_mainline, contact_guard`
- `FAIL` `humanlike_phone_refusal_wechat_followup_has_complete_sentence` | category=`humanlike_mainline` | tags=`critical, humanlike, contact, delivery`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `FAIL` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `PASS` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `PASS` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_no_large_repeat_profile` | category=`humanlike_memory` | tags=`memory`
- `FAIL` `matchmaker_boundary_not_convenient_field` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary`
- `FAIL` `matchmaker_boundary_questioned_too_much` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary, complaint`
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
- `FAIL` `policy_mixed_location_and_boundary` | category=`policy_mixed` | tags=`mixed, boundary`

## 失败详情

### ending_after_conversation_ended_followup

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json`
- 分类: `ending`
- 标签: `critical, ending_gate`
- 描述: 对话已结束后用户再次发消息，应只给简短告别，不再继续收集。
- 断言通过: 2/3
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json --scenario-id ending_after_conversation_ended_followup --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['先这样', '再来找我', '拜拜', '下次再聊']，实际 '行，那先聊到这儿'
- 失败轮次精简回放:
  - Turn 2 用户: 你好，还在吗
    AI: 行，那先聊到这儿
- 对话回放:
  - Turn 1 用户: 我现在还在分居中
    AI: 嗯嗯理解～分居中的话暂时还不符合我们的服务条件呢～等手续都办妥了再来找我吧，祝你顺利～
  - Turn 2 用户: 你好，还在吗
    AI: 行，那先聊到这儿

### ending_fake_info_pattern

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json`
- 分类: `ending`
- 标签: `ending_gate, fake_info`
- 描述: 用户提供明显虚假信息时，应识别并收尾。
- 断言通过: 0/2
- 建议修改方向: 优先检查字段提取、状态更新、收尾状态机或后处理覆盖。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/ending_regression.json --scenario-id ending_fake_info_pattern --verbose`
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['有意思', '认真对待', '真实信息']，实际 '好，你这边是女生。 你也太会玩啦，1000岁的小仙女可还行~对啦，你现在主要在哪个城市生活呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 好，你这边是女生。 你也太会玩啦，1000岁的小仙女可还行~对啦，你现在主要在哪个城市生活呀？
- 对话回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 好，你这边是女生。 你也太会玩啦，1000岁的小仙女可还行~对啦，你现在主要在哪个城市生活呀？

### faq_priority_can_add_wechat

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json`
- 分类: `faq`
- 标签: `critical, faq_priority`
- 描述: 用户问能不能直接加对方微信时，应先说明由牵线同事安排互换。
- 断言通过: 2/3
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/faq_regression.json --scenario-id faq_priority_can_add_wechat --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['直接', '不会', '沟通', '确认']，实际 '对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。'
- 失败轮次精简回放:
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 对，刚刚是在说微信这块。你要是愿意的话，留个常用微信就行，不想留也没关系。

### listener_first_opening_profile_provided_no_repeat_field

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, profile`
- 描述: 开场直接给出性别和城市时，应先接住已给资料，不能重复问同字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_opening_profile_provided_no_repeat_field --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['男生', '深圳', '这边', '知道了']，实际 '平时是做什么工作的？ 你现在收入大概在哪个范围，也可以一起说说。'
- 失败轮次精简回放:
  - Turn 2 用户: 男的，深圳
    AI: 平时是做什么工作的？ 你现在收入大概在哪个范围，也可以一起说说。
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，在的。 你是想认真聊聊，还是先问问情况呀？
  - Turn 2 用户: 男的，深圳
    AI: 平时是做什么工作的？ 你现在收入大概在哪个范围，也可以一起说说。

### listener_first_opening_mixed_boundary_priority_over_profile

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, mixed, boundary`
- 描述: 开场同时说不给电话并给出性别时，应优先接住边界，而不是顺着资料继续追问。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_opening_mixed_boundary_priority_over_profile --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['可以', '不强求', '不留也行', '先聊']，实际 '不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你'
- 失败轮次精简回放:
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你
- 对话回放:
  - Turn 1 用户: 你好
    AI: 你好呀，我在呢。 你这边是想找对象，还是先了解下呀？
  - Turn 2 用户: 不给电话行不行，我是男的
    AI: 不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你

### listener_first_preference_ack_city

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, preference`
- 描述: 用户直接表达偏好时，下一句应先接住偏好里的城市或择偶重点，再推进主问题。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_preference_ack_city --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['深圳', '女生', '偏向', '同城']，实际 '好，那你先简单讲讲你现在的大概情况，我顺着了解'
- 失败轮次精简回放:
  - Turn 1 用户: 我喜欢深圳的女生
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解
- 对话回放:
  - Turn 1 用户: 我喜欢深圳的女生
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解

### listener_first_boundary_opening_no_collection

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json`
- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, boundary`
- 描述: 用户首轮先划边界时，应先降压，不继续采字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_listener_first_regression.json --scenario-id listener_first_boundary_opening_no_collection --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['先轻松聊', '不追问', '没关系', '不问那么紧']，实际 '好，那就先顺着你现在更想聊的这个来'
- 失败轮次精简回放:
  - Turn 1 用户: 先别问我这些
    AI: 好，那就先顺着你现在更想聊的这个来
- 对话回放:
  - Turn 1 用户: 先别问我这些
    AI: 好，那就先顺着你现在更想聊的这个来

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
    AI: 好，你这边是男生。 好哒，你现在主要在哪个城市生活呀？
  - Turn 2 用户: 90后
    AI: 那我再了解下，你大概是什么学历呀？ 后面我也更好往相对合适的方向帮你看。
  - Turn 3 用户: 深圳
    AI: 你现在主要做哪方面工作呀？ 顺着这个聊，你对另一半会更看重哪一点？
  - Turn 4 用户: 本科
    AI: 我顺手确认一下，你现在是单身状态吗？
  - Turn 5 用户: 我是做it的
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 这样我后面更好往条件相近的方向留意。 不方便说也没关系。
  - Turn 6 用户: 我离异过呢
    AI: 可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？
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
  - [response_contains_any] turn=8 turn=8 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你'
  - [response_not_contains_any] turn=8 turn=8 不应包含关键词 ['手机号']，实际 '不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你'
- 失败轮次精简回放:
  - Turn 8 用户: 你不问其他了？
    AI: 不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你
- 对话回放:
  - Turn 1 用户: 男的
    AI: 好，男生是吧。 那我再问你一个，你现在是在什么城市生活呀？
  - Turn 2 用户: 90后
    AI: 顺着聊到这儿，方便说下你的学历吗？
  - Turn 3 用户: 深圳
    AI: 你现在主要做哪方面工作呀？ 顺着这个聊，你对另一半会更看重哪一点？
  - Turn 4 用户: 本科
    AI: 我顺手确认一下，你现在是单身状态吗？ 这个点先对齐了，后面就不容易聊岔。
  - Turn 5 用户: 我是做it的
    AI: 你继续说，我先顺着听
  - Turn 6 用户: 我离异过呢
    AI: 可以的，我先确认下，你现在离婚手续是不是已经办妥了？
  - Turn 7 用户: 办理好了
    AI: 那就没问题了。 你这边方便留个电话吗？
  - Turn 8 用户: 你不问其他了？
    AI: 不想留太多也没关系。 给个常用手机号就行，后面要是真有合适的方向，我们也能联系上你

### humanlike_phone_refusal_wechat_followup_has_complete_sentence

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json`
- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, contact, delivery`
- 描述: 电话拒绝后转微信时，回复应是完整句，不能再出现半句尾巴或空截断。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_mainline_recovery_regression.json --scenario-id humanlike_phone_refusal_wechat_followup_has_complete_sentence --verbose`
- 失败摘要:
  - [response_contains_any] turn=4 turn=4 需要包含任一关键词 ['微信', '不想留我们先往下聊', '不想留也行', '继续聊']，实际 '没关系，我们先按你舒服的节奏来'
- 失败轮次精简回放:
  - Turn 4 用户: 不方便留电话
    AI: 没关系，我们先按你舒服的节奏来
- 对话回放:
  - Turn 1 用户: 我是男的，90后，深圳，本科，做it的，离异，手续已经办妥了
    AI: 好，你这边是男生。 你现在大概什么年龄段？ 你要是方便，也可以说说你想找个什么样的。
  - Turn 2 用户: 我想找个年龄别太大的
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 不方便说也没关系
  - Turn 3 用户: 你不问其他了？
    AI: 我们先顺着你这句聊
  - Turn 4 用户: 不方便留电话
    AI: 没关系，我们先按你舒服的节奏来

### humanlike_transition_with_feedback

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_regression.json`
- 分类: `humanlike_transition`
- 标签: `transition`
- 描述: 转场时应包含承接上一句和反馈/认可。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/humanlike_regression.json --scenario-id humanlike_transition_with_feedback --verbose`
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['不错', '好的', '了解', '运营', '好哒', '记下', '收到']，实际 '好呀，你今年大概多大呀？ 你要是方便，也可以说说你想找个什么样的。'
- 失败轮次精简回放:
  - Turn 2 用户: 我是做运营的
    AI: 好呀，你今年大概多大呀？ 你要是方便，也可以说说你想找个什么样的。
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，深圳，本科
    AI: 好，女生是吧。 平时是做什么工作的？ 另外你找对象时更在意对方哪方面，也可以一起说说。
  - Turn 2 用户: 我是做运营的
    AI: 好呀，你今年大概多大呀？ 你要是方便，也可以说说你想找个什么样的。

### matchmaker_boundary_not_convenient_field

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/matchmaker_boundary_regression.json`
- 分类: `matchmaker_boundary`
- 标签: `critical, humanlike, boundary`
- 描述: 用户说不方便时，应先接边界，不继续追字段。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/matchmaker_boundary_regression.json --scenario-id matchmaker_boundary_not_convenient_field --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['不方便', '先不追问', '没关系', '不太想展开']，实际 '我顺手确认下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 这个不太方便说
    AI: 我顺手确认下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 这个不太方便说
    AI: 我顺手确认下，你这边是男生还是女生呀？

### matchmaker_boundary_questioned_too_much

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/matchmaker_boundary_regression.json`
- 分类: `matchmaker_boundary`
- 标签: `critical, humanlike, boundary, complaint`
- 描述: 用户说问得太细时，应先降压，不要继续盘问。
- 断言通过: 1/2
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/matchmaker_boundary_regression.json --scenario-id matchmaker_boundary_questioned_too_much --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['问细', '慢慢来', '先不追', '没关系']，实际 '是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说'
- 失败轮次精简回放:
  - Turn 1 用户: 你问得太细了
    AI: 是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说
- 对话回放:
  - Turn 1 用户: 你问得太细了
    AI: 是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说

### policy_contact_trigger_sufficient_fields

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_contact`
- 标签: `critical, contact_trigger`
- 描述: 联系方式触发条件：拿到4个及以上核心/准核心字段后，可进入联系方式逻辑。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_contact_trigger_sufficient_fields --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['电话', '微信', '联系']，实际 '好，女生是吧。 你现在大概什么年龄段？ 这样我心里会更有数一点。 说到这儿，你会更看重对方哪方面？'
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好，女生是吧。 你现在大概什么年龄段？ 这样我心里会更有数一点。 说到这儿，你会更看重对方哪方面？
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好，女生是吧。 你现在大概什么年龄段？ 这样我心里会更有数一点。 说到这儿，你会更看重对方哪方面？

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
    AI: 好，女生是吧。 你现在大概什么年龄段？ 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更在意哪方面？
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 行呀，那你可以先简单说说自己，我顺着了解会更顺一点

### policy_mixed_location_and_boundary

- 场景文件: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json`
- 分类: `policy_mixed`
- 标签: `mixed, boundary`
- 描述: 用户同句给出字段并表达边界时，应先接住已给字段，再尊重边界。
- 断言通过: 0/1
- 建议修改方向: 优先检查提示词、固定话术模板、规则改写和响应清洗。
- 单场景重跑: `python3 scripts/run_real_ai_regression.py --scenario-file /Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios/policy_comprehensive_regression.json --scenario-id policy_mixed_location_and_boundary --verbose`
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['本科', '不太想展开', '不方便', '先不追问']，实际 '你平时主要在哪边生活？'
- 失败轮次精简回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你平时主要在哪边生活？
- 对话回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你平时主要在哪边生活？
