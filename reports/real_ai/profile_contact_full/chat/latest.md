# 真实 AI 回归报告

- 开始时间: 2026-03-26T22:01:39
- 结束时间: 2026-03-27T00:58:01
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 76
- 通过: 58
- 失败: 18
- 总耗时: 10581.366s
- 平均耗时: 139.228s
- 最长耗时: 1075.748s
- Token: 237509 (调用 43 次)

## 结果概览

- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_contact_why_phone` | category=`faq` | tags=`critical, faq_priority, contact_why`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
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
- `PASS` `listener_first_preference_ack_city` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, preference`
- `PASS` `listener_first_mixed_answer_and_fee` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, mixed, faq`
- `PASS` `listener_first_boundary_ack_before_pause` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary`
- `PASS` `listener_first_reliability_then_answer` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, reliability`
- `PASS` `listener_first_privacy_then_answer` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, privacy`
- `PASS` `listener_first_explicit_matchmaking_enters_mainline` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent`
- `PASS` `listener_first_explicit_matchmaking_allows_open_self_intro` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, open_self_intro`
- `PASS` `listener_first_multi_profile_no_mechanical_repeat` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, multi_profile`
- `PASS` `listener_first_matchmaking_then_multi_profile_stays_contextual` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, intent, multi_profile`
- `FAIL` `listener_first_mixed_answer_and_boundary` | category=`humanlike_listener_first` | tags=`humanlike, listener_first, mixed, boundary`
- `FAIL` `listener_first_boundary_opening_no_collection` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, boundary`
- `PASS` `listener_first_latest_location_prefers_occupation` | category=`humanlike_listener_first` | tags=`critical, humanlike, listener_first, contextual_followup`
- `FAIL` `humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot` | category=`humanlike_mainline` | tags=`critical, humanlike, divorce, mainline`
- `FAIL` `humanlike_resume_profile_collection_does_not_jump_to_contact` | category=`humanlike_mainline` | tags=`critical, humanlike, resume_mainline, contact_guard`
- `FAIL` `humanlike_phone_refusal_wechat_followup_has_complete_sentence` | category=`humanlike_mainline` | tags=`critical, humanlike, contact, delivery`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `PASS` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `FAIL` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `PASS` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_no_large_repeat_profile` | category=`humanlike_memory` | tags=`memory`
- `PASS` `matchmaker_boundary_not_convenient_field` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary`
- `FAIL` `matchmaker_boundary_questioned_too_much` | category=`matchmaker_boundary` | tags=`critical, humanlike, boundary, complaint`
- `FAIL` `matchmaker_boundary_topic_shift_before_data` | category=`matchmaker_boundary` | tags=`critical, humanlike, topic_shift`
- `PASS` `matchmaker_mixed_answer_fee` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, faq`
- `FAIL` `matchmaker_mixed_contact_fee` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, faq, contact`
- `PASS` `matchmaker_mixed_preference_reliability` | category=`matchmaker_mixed_intent` | tags=`critical, humanlike, mixed, reliability`
- `PASS` `policy_core_field_priority_over_quasi` | category=`policy_priority` | tags=`critical, field_priority, smoke`
- `PASS` `policy_quasi_core_marital_status_once_only` | category=`policy_ask_limit` | tags=`critical, marital_status, ask_limit`
- `FAIL` `policy_core_field_twice_max` | category=`policy_ask_limit` | tags=`critical, ask_limit, core_field`
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
- `FAIL` `policy_memory_reuse_preference` | category=`policy_memory` | tags=`memory, reuse`
- `PASS` `policy_low_info_huitouzaishuo_pause` | category=`policy_low_info` | tags=`critical, low_info`
- `PASS` `policy_mixed_answer_and_faq` | category=`policy_mixed` | tags=`critical, mixed, faq`
- `PASS` `policy_opening_location_occupation_prefers_low_pressure_core` | category=`policy_opening` | tags=`critical, opening, contextual_target`
- `PASS` `policy_opening_location_occupation_fee_answers_first` | category=`policy_opening` | tags=`critical, opening, mixed, faq`
- `PASS` `policy_latest_location_followup_prefers_occupation` | category=`policy_opening` | tags=`critical, contextual_target, followup`
- `FAIL` `policy_mixed_location_and_boundary` | category=`policy_mixed` | tags=`mixed, boundary`

## 失败详情

### ending_normal_complete

- 分类: `ending`
- 标签: `critical, normal_complete`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 不方便说也没关系。
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 好，电话和微信我都看到了。 还有其他要求的话也可以继续说

### faq_priority_contact_why_phone

- 分类: `faq`
- 标签: `critical, faq_priority, contact_why`
- 断言通过: 2/3
- 失败摘要:
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['方便留个电话']，实际 '方便留个电话吗？ 后面沟通会方便些'
- 失败轮次精简回放:
  - Turn 2 用户: 为什么要留电话呢
    AI: 方便留个电话吗？ 后面沟通会方便些
- 对话回放:
  - Turn 1 用户: 我是男生，90后，深圳，本科，IT，单身，想找女生
    AI: 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更看重哪方面？
  - Turn 2 用户: 为什么要留电话呢
    AI: 方便留个电话吗？ 后面沟通会方便些

### faq_priority_how_match

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 2/3
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['线上', '匹配', '沟通', '了解情况']，实际 '一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定'
- 失败轮次精简回放:
  - Turn 2 用户: 你们怎么匹配
    AI: 一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解
  - Turn 2 用户: 你们怎么匹配
    AI: 一般是先把你的基本情况和要求聊清楚，再看后面怎么继续推进；合不合适你都可以自己决定

### faq_priority_can_add_wechat

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 2/3
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

### listener_first_mixed_answer_and_boundary

- 分类: `humanlike_listener_first`
- 标签: `humanlike, listener_first, mixed, boundary`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['本科', '不太想展开', '不方便', '先不追问']，实际 '你现在主要在哪个城市生活呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你现在主要在哪个城市生活呀？
- 对话回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你现在主要在哪个城市生活呀？

### listener_first_boundary_opening_no_collection

- 分类: `humanlike_listener_first`
- 标签: `critical, humanlike, listener_first, boundary`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['先轻松聊', '不追问', '没关系', '不问那么紧']，实际 '我先认识你一下，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 先别问我这些
    AI: 我先认识你一下，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 先别问我这些
    AI: 我先认识你一下，你这边是男生还是女生呀？

### humanlike_divorce_confirmation_returns_to_mainline_without_contact_pivot

- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, divorce, mainline`
- 断言通过: 3/5
- 失败摘要:
  - [response_contains_any] turn=7 turn=7 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '好，那就行。 要是你愿意，留个电话也行'
  - [response_not_contains_any] turn=7 turn=7 不应包含关键词 ['电话']，实际 '好，那就行。 要是你愿意，留个电话也行'
- 失败轮次精简回放:
  - Turn 7 用户: 办理好了
    AI: 好，那就行。 要是你愿意，留个电话也行
- 对话回放:
  - Turn 1 用户: 男的
    AI: 男生，明白了。 顺着聊到这儿，你平时主要在哪边生活？
  - Turn 2 用户: 90后
    AI: 那我再问你一个，你现在主要在哪个城市生活呀？
  - Turn 3 用户: 深圳
    AI: 平时是做什么工作的？ 你现在收入大概在哪个范围，也可以一起说说。
  - Turn 4 用户: 本科
    AI: 我顺手确认一下，你现在是单身状态吗？
  - Turn 5 用户: 我是做it的
    AI: 你继续说，我先顺着听
  - Turn 6 用户: 我离异过呢
    AI: 可以，我先问清楚一个点，你这边离婚手续现在已经办妥了吗？
  - Turn 7 用户: 办理好了
    AI: 好，那就行。 要是你愿意，留个电话也行

### humanlike_resume_profile_collection_does_not_jump_to_contact

- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, resume_mainline, contact_guard`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=8 turn=8 需要包含任一关键词 ['另一半', '偏好', '要求', '月收入', '收入', '看重']，实际 '我明白，你要是担心电话不方便，我就再轻问一次。 留个常用手机号就行，方便后面联系你'
  - [response_not_contains_any] turn=8 turn=8 不应包含关键词 ['电话', '手机号']，实际 '我明白，你要是担心电话不方便，我就再轻问一次。 留个常用手机号就行，方便后面联系你'
- 失败轮次精简回放:
  - Turn 8 用户: 你不问其他了？
    AI: 我明白，你要是担心电话不方便，我就再轻问一次。 留个常用手机号就行，方便后面联系你
- 对话回放:
  - Turn 1 用户: 男的
    AI: 男生，明白了。 顺着聊到这儿，你平时主要在哪边生活？
  - Turn 2 用户: 90后
    AI: 好呀，你现在是在什么城市生活呀？
  - Turn 3 用户: 深圳
    AI: 你现在主要做哪方面工作呀？ 如果方便的话，收入区间也说个大概就行。
  - Turn 4 用户: 本科
    AI: 我顺手确认一下，你现在是单身状态吗？
  - Turn 5 用户: 我是做it的
    AI: 你继续说，我先顺着听
  - Turn 6 用户: 我离异过呢
    AI: 可以的，我想先确认一下，你这边离婚手续已经办妥了吗？
  - Turn 7 用户: 办理好了
    AI: 好，那就行。 要是你愿意，留个电话也行
  - Turn 8 用户: 你不问其他了？
    AI: 我明白，你要是担心电话不方便，我就再轻问一次。 留个常用手机号就行，方便后面联系你

### humanlike_phone_refusal_wechat_followup_has_complete_sentence

- 分类: `humanlike_mainline`
- 标签: `critical, humanlike, contact, delivery`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=4 turn=4 需要包含任一关键词 ['微信', '不想留我们先往下聊', '不想留也行', '继续聊']，实际 '行，电话这块你现在不方便也没事。 等你哪天觉得方便了再说，按你方便的方式来就行'
- 失败轮次精简回放:
  - Turn 4 用户: 不方便留电话
    AI: 行，电话这块你现在不方便也没事。 等你哪天觉得方便了再说，按你方便的方式来就行
- 对话回放:
  - Turn 1 用户: 我是男的，90后，深圳，本科，做it的，离异，手续已经办妥了
    AI: 你对另一半大概有什么要求呀？ 比如年龄、城市、性格这些，你会更看重哪方面？
  - Turn 2 用户: 我想找个年龄别太大的
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 不方便说也没关系
  - Turn 3 用户: 你不问其他了？
    AI: 嗯，我知道了，我们先顺着你这句聊
  - Turn 4 用户: 不方便留电话
    AI: 行，电话这块你现在不方便也没事。 等你哪天觉得方便了再说，按你方便的方式来就行

### humanlike_memory_reuse_occupation

- 分类: `humanlike_memory`
- 标签: `memory`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['运营', '工作', '忙']，实际 '你对另一半大概有什么要求呀？'
- 失败轮次精简回放:
  - Turn 2 用户: 我工作比较忙
    AI: 你对另一半大概有什么要求呀？
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营
    AI: 我顺手确认一下，你现在是单身状态吗？
  - Turn 2 用户: 我工作比较忙
    AI: 你对另一半大概有什么要求呀？

### matchmaker_boundary_questioned_too_much

- 分类: `matchmaker_boundary`
- 标签: `critical, humanlike, boundary, complaint`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['问细', '慢慢来', '先不追', '没关系']，实际 '是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说'
- 失败轮次精简回放:
  - Turn 1 用户: 你问得太细了
    AI: 是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说
- 对话回放:
  - Turn 1 用户: 你问得太细了
    AI: 是，刚才那样问确实容易让人烦。 这个我收住，你想接着聊什么就顺着说

### matchmaker_boundary_topic_shift_before_data

- 分类: `matchmaker_boundary`
- 标签: `critical, humanlike, topic_shift`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['先顺着', '先聊', '你更想聊']，实际 '先随便聊聊，你这边是男生还是女生呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 先不聊资料
    AI: 先随便聊聊，你这边是男生还是女生呀？
- 对话回放:
  - Turn 1 用户: 先不聊资料
    AI: 先随便聊聊，你这边是男生还是女生呀？

### matchmaker_mixed_contact_fee

- 分类: `matchmaker_mixed_intent`
- 标签: `critical, humanlike, mixed, faq, contact`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['微信', '收费', '免费', '定制']，实际 '没关系，我再轻问一次。 你要是方便的话，留个常用手机号就行，后面联系你也顺一点'
- 失败轮次精简回放:
  - Turn 1 用户: 电话不方便，我可以留微信，你们收费吗
    AI: 没关系，我再轻问一次。 你要是方便的话，留个常用手机号就行，后面联系你也顺一点
- 对话回放:
  - Turn 1 用户: 电话不方便，我可以留微信，你们收费吗
    AI: 没关系，我再轻问一次。 你要是方便的话，留个常用手机号就行，后面联系你也顺一点

### policy_core_field_twice_max

- 分类: `policy_ask_limit`
- 标签: `critical, ask_limit, core_field`
- 断言通过: 0/1
- 失败摘要:
  - [response_not_contains_any] turn=4 turn=4 不应包含关键词 ['今年']，实际 '顺着聊到这儿，方便说下你今年多大吗？ 这样我心里会更有数一点'
- 失败轮次精简回放:
  - Turn 4 用户: 真的不想说
    AI: 顺着聊到这儿，方便说下你今年多大吗？ 这样我心里会更有数一点
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 好，那你先简单讲讲你现在的大概情况，我顺着了解
  - Turn 2 用户: 不想说年龄
    AI: 我先认识你一下，你这边是男生还是女生呀？
  - Turn 3 用户: 还是不想说
    AI: 那我再问你一个，你现在主要在哪个城市生活呀？
  - Turn 4 用户: 真的不想说
    AI: 顺着聊到这儿，方便说下你今年多大吗？ 这样我心里会更有数一点

### policy_contact_trigger_sufficient_fields

- 分类: `policy_contact`
- 标签: `critical, contact_trigger`
- 断言通过: 0/1
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['电话', '微信', '联系']，实际 '如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 我心里也更好有个大概范围。 不方便说也没关系。'
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 我心里也更好有个大概范围。 不方便说也没关系。
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 如果你方便的话，我再轻问一句，你月收入大概在哪个区间？ 我心里也更好有个大概范围。 不方便说也没关系。

### policy_memory_reuse_location

- 分类: `policy_memory`
- 标签: `memory, reuse`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '那边']，实际 '好，你也可以先简单介绍下自己，我顺着了解会更自然一点'
- 失败轮次精简回放:
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 好，你也可以先简单介绍下自己，我顺着了解会更自然一点
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营
    AI: 我顺手确认一下，你现在是单身状态吗？
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 好，你也可以先简单介绍下自己，我顺着了解会更自然一点

### policy_memory_reuse_preference

- 分类: `policy_memory`
- 标签: `memory, reuse`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['成熟', '稳重', '合拍', '推荐']，实际 '你大概是什么学历呀？ 这样我对你的情况会更有数一点。'
- 失败轮次精简回放:
  - Turn 2 用户: 有什么推荐吗
    AI: 你大概是什么学历呀？ 这样我对你的情况会更有数一点。
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，想找个成熟稳重的
    AI: 平时是做什么工作的？ 你现在收入大概在哪个范围，也可以一起说说。
  - Turn 2 用户: 有什么推荐吗
    AI: 你大概是什么学历呀？ 这样我对你的情况会更有数一点。

### policy_mixed_location_and_boundary

- 分类: `policy_mixed`
- 标签: `mixed, boundary`
- 断言通过: 0/1
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['本科', '不太想展开', '不方便', '先不追问']，实际 '你平时主要在哪边生活？'
- 失败轮次精简回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你平时主要在哪边生活？
- 对话回放:
  - Turn 1 用户: 本科，不过这个先不太方便说
    AI: 你平时主要在哪边生活？
