# 真实 AI 回归报告

- 开始时间: 2026-03-18T18:22:52
- 结束时间: 2026-03-18T19:00:41
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 108
- 通过: 104
- 失败: 4
- 总耗时: 2269.76s
- 平均耗时: 21.016s
- 最长耗时: 58.96s
- Token: 925110 (调用 172 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_invalid_then_valid` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_with_spaces_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_hk_phone_then_wechat` | category=`contact` | tags=`critical, contact_hk`
- `PASS` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_confirm_word_after_phone_prompt` | category=`contact` | tags=`critical, contact_confirm, contact_phone`
- `PASS` `contact_confirm_word_then_wechat_fallback` | category=`contact` | tags=`critical, contact_confirm`
- `PASS` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `PASS` `contact_user_questions_privacy_before_phone` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_phone_after_privacy_question` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_wechat_after_phone_prompt` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_says_no_contact_at_all` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_hk_user_provides_wechat_only` | category=`contact` | tags=`critical, contact_hk, contact_wechat, contact_phone`
- `PASS` `contact_phone_with_text_prefix_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `PASS` `contact_hk_user_reject_wechat` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_non_hk_wechat_first_then_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_says_phone_inconvenient_then_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_invalid_format_retry` | category=`contact` | tags=`contact_wechat, retry, normalization`
- `PASS` `contact_wechat_invalid_then_valid` | category=`contact` | tags=`contact_wechat, retry`
- `PASS` `contact_phone_with_country_code` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_phone_with_86_prefix` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_phone_with_dashes` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_wechat_with_special_chars` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `contact_phone_too_short_should_retry` | category=`contact` | tags=`contact_phone, retry`
- `PASS` `contact_phone_too_long_should_retry` | category=`contact` | tags=`contact_phone, retry`
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
- `PASS` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_followup_question_should_still_answer` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_success_rate` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_service_area` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_time_required` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_reliable` | category=`faq` | tags=`critical, faq_reliable`
- `PASS` `faq_priority_safety` | category=`faq` | tags=`faq_safety`
- `PASS` `field_occupation_placeholder_guard` | category=`field_collection` | tags=`smoke, critical, extract_guard`
- `PASS` `field_multi_info_extract_basic` | category=`field_collection` | tags=`critical, extract_basic`
- `PASS` `field_age_parse_90s` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_age_parse_birth_year` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_location_extract_shenzhen` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_partner_requirement_should_not_override_location` | category=`field_collection` | tags=`critical, extract_guard`
- `PASS` `field_education_extract_master` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_occupation_extract_programmer` | category=`field_collection` | tags=`extract_basic, extract_guard`
- `PASS` `field_multi_sentence_extract` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_phone_should_not_pollute_occupation` | category=`field_collection` | tags=`extract_guard, contact_phone`
- `PASS` `field_wechat_should_not_pollute_location` | category=`field_collection` | tags=`extract_guard, contact_wechat`
- `PASS` `field_greeting_should_not_fill_profile` | category=`field_collection` | tags=`extract_guard, smoke`
- `PASS` `field_sex_extract_male` | category=`field_collection` | tags=`extract_basic, sex`
- `PASS` `field_age_variants_85s` | category=`field_collection` | tags=`extract_basic, age`
- `PASS` `field_occupation_variants_teacher` | category=`field_collection` | tags=`extract_basic, occupation`
- `PASS` `field_marital_status_single` | category=`field_collection` | tags=`extract_basic, marital_status`
- `PASS` `field_marital_status_divorced` | category=`field_collection` | tags=`extract_basic, marital_status`
- `PASS` `field_height_extract_cm` | category=`field_collection` | tags=`extract_basic, height`
- `PASS` `field_income_extract_monthly` | category=`field_collection` | tags=`extract_basic, income`
- `PASS` `humanlike_reception_hesitant_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `FAIL` `humanlike_reception_joking_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `PASS` `humanlike_reception_defensive_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `PASS` `humanlike_reception_evasive_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `PASS` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `PASS` `humanlike_light_interaction_after_fields` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `PASS` `humanlike_light_interaction_short_feedback` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `PASS` `humanlike_user_type_cooperative` | category=`humanlike_user_type` | tags=`user_type, critical`
- `PASS` `humanlike_user_type_conservative` | category=`humanlike_user_type` | tags=`user_type`
- `PASS` `humanlike_user_type_conversational` | category=`humanlike_user_type` | tags=`user_type`
- `FAIL` `humanlike_memory_reuse_location` | category=`humanlike_memory` | tags=`memory, critical`
- `FAIL` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `FAIL` `humanlike_memory_reuse_preference` | category=`humanlike_memory` | tags=`memory, critical`
- `PASS` `humanlike_emotion_recognition_relaxed` | category=`humanlike_emotion` | tags=`emotion`
- `PASS` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_emotion_recognition_joking_response` | category=`humanlike_emotion` | tags=`emotion`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_low_priority_never_ask` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_medium_field_timing_after_age` | category=`humanlike_field_timing` | tags=`field_timing, medium_field`
- `PASS` `humanlike_medium_field_timing_income_optional` | category=`humanlike_field_timing` | tags=`field_timing, medium_field`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_no_large_repeat_profile` | category=`humanlike_memory` | tags=`memory`

## 失败详情

### humanlike_reception_joking_user

- 分类: `humanlike_reception`
- 标签: `reception, emotion`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['了解', '认识', '匹配', '适合']，实际 '实在抱歉让你觉得不舒服啦，方便留个电话号码吗？后续有合适的人选方便及时联系你~'
- 失败轮次精简回放:
  - Turn 2 用户: 你查户口呢问这么细
    AI: 实在抱歉让你觉得不舒服啦，方便留个电话号码吗？后续有合适的人选方便及时联系你~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营
    AI: 好哒，这些基础信息我都记下来啦～对了想问下你现在是单身状态在认真了解脱单吗？
  - Turn 2 用户: 你查户口呢问这么细
    AI: 实在抱歉让你觉得不舒服啦，方便留个电话号码吗？后续有合适的人选方便及时联系你~

### humanlike_memory_reuse_location

- 分类: `humanlike_memory`
- 标签: `memory, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '那边']，实际 '我们这边有不少适配的优质单身资源哦，方便留个电话号码吗？后续有合适的人选会及时联系你~'
- 失败轮次精简回放:
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 我们这边有不少适配的优质单身资源哦，方便留个电话号码吗？后续有合适的人选会及时联系你~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营
    AI: 好哒，你的基本情况我大概有数啦~我顺带确认下，你现在是单身状态在认真了解脱单相关的吗？
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 我们这边有不少适配的优质单身资源哦，方便留个电话号码吗？后续有合适的人选会及时联系你~

### humanlike_memory_reuse_occupation

- 分类: `humanlike_memory`
- 标签: `memory`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['运营', '工作', '忙']，实际 '理解的，你方便留个电话号码吗？后续有合适的人选我们好及时联系到你~'
- 失败轮次精简回放:
  - Turn 2 用户: 我工作比较忙
    AI: 理解的，你方便留个电话号码吗？后续有合适的人选我们好及时联系到你~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营
    AI: 哇，这些基础信息我都记下啦～我顺带确认下，你现在是单身状态在认真了解脱单吗？
  - Turn 2 用户: 我工作比较忙
    AI: 理解的，你方便留个电话号码吗？后续有合适的人选我们好及时联系到你~

### humanlike_memory_reuse_preference

- 分类: `humanlike_memory`
- 标签: `memory, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['成熟', '稳重', '合拍', '推荐']，实际 '当然有呀，不过得先多了解点你的情况才能给你推更适配的人选哦，对啦，你平时是做哪方面工作的呀？'
- 失败轮次精简回放:
  - Turn 2 用户: 有什么推荐吗
    AI: 当然有呀，不过得先多了解点你的情况才能给你推更适配的人选哦，对啦，你平时是做哪方面工作的呀？
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，想找个成熟稳重的
    AI: 哈哈成熟稳重的人相处起来确实很靠谱呀～对了，你是什么学历呀？
  - Turn 2 用户: 有什么推荐吗
    AI: 当然有呀，不过得先多了解点你的情况才能给你推更适配的人选哦，对啦，你平时是做哪方面工作的呀？
