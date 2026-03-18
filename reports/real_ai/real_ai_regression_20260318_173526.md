# 真实 AI 回归报告

- 开始时间: 2026-03-18T17:28:48
- 结束时间: 2026-03-18T17:35:26
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 108
- 通过: 57
- 失败: 51
- 总耗时: 398.154s
- 平均耗时: 3.687s
- 最长耗时: 10.672s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `FAIL` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `FAIL` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `FAIL` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_invalid_then_valid` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_with_spaces_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `FAIL` `contact_hk_phone_then_wechat` | category=`contact` | tags=`critical, contact_hk`
- `PASS` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_confirm_word_after_phone_prompt` | category=`contact` | tags=`critical, contact_confirm, contact_phone`
- `PASS` `contact_confirm_word_then_wechat_fallback` | category=`contact` | tags=`critical, contact_confirm`
- `PASS` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `PASS` `contact_user_questions_privacy_before_phone` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_phone_after_privacy_question` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_wechat_after_phone_prompt` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_says_no_contact_at_all` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_hk_user_provides_wechat_only` | category=`contact` | tags=`critical, contact_hk, contact_wechat, contact_phone`
- `PASS` `contact_phone_with_text_prefix_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `FAIL` `contact_hk_user_reject_wechat` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
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
- `FAIL` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `FAIL` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `PASS` `ending_spam_user_variant` | category=`ending` | tags=`spam_user`
- `PASS` `ending_spam_user_aggressive` | category=`ending` | tags=`spam_user`
- `PASS` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
- `PASS` `ending_gay_user_variant` | category=`ending` | tags=`ending_gate, lgbt`
- `PASS` `ending_divorce_incomplete_variant` | category=`ending` | tags=`divorce`
- `PASS` `ending_proxy_user_variant` | category=`ending` | tags=`ending_gate, proxy_user`
- `FAIL` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `FAIL` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_followup_question_should_still_answer` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_success_rate` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_service_area` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_time_required` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_reliable` | category=`faq` | tags=`critical, faq_reliable`
- `FAIL` `faq_priority_safety` | category=`faq` | tags=`faq_safety`
- `PASS` `field_occupation_placeholder_guard` | category=`field_collection` | tags=`smoke, critical, extract_guard`
- `FAIL` `field_multi_info_extract_basic` | category=`field_collection` | tags=`critical, extract_basic`
- `FAIL` `field_age_parse_90s` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `field_age_parse_birth_year` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `field_location_extract_shenzhen` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `field_partner_requirement_should_not_override_location` | category=`field_collection` | tags=`critical, extract_guard`
- `FAIL` `field_education_extract_master` | category=`field_collection` | tags=`extract_basic`
- `FAIL` `field_occupation_extract_programmer` | category=`field_collection` | tags=`extract_basic, extract_guard`
- `FAIL` `field_multi_sentence_extract` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_phone_should_not_pollute_occupation` | category=`field_collection` | tags=`extract_guard, contact_phone`
- `PASS` `field_wechat_should_not_pollute_location` | category=`field_collection` | tags=`extract_guard, contact_wechat`
- `PASS` `field_greeting_should_not_fill_profile` | category=`field_collection` | tags=`extract_guard, smoke`
- `FAIL` `field_sex_extract_male` | category=`field_collection` | tags=`extract_basic, sex`
- `FAIL` `field_age_variants_85s` | category=`field_collection` | tags=`extract_basic, age`
- `FAIL` `field_occupation_variants_teacher` | category=`field_collection` | tags=`extract_basic, occupation`
- `FAIL` `field_marital_status_single` | category=`field_collection` | tags=`extract_basic, marital_status`
- `FAIL` `field_marital_status_divorced` | category=`field_collection` | tags=`extract_basic, marital_status`
- `FAIL` `field_height_extract_cm` | category=`field_collection` | tags=`extract_basic, height`
- `FAIL` `field_income_extract_monthly` | category=`field_collection` | tags=`extract_basic, income`
- `PASS` `humanlike_reception_hesitant_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `FAIL` `humanlike_reception_joking_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `FAIL` `humanlike_reception_defensive_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `PASS` `humanlike_reception_evasive_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `FAIL` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `PASS` `humanlike_light_interaction_after_fields` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `PASS` `humanlike_light_interaction_short_feedback` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `FAIL` `humanlike_user_type_cooperative` | category=`humanlike_user_type` | tags=`user_type, critical`
- `PASS` `humanlike_user_type_conservative` | category=`humanlike_user_type` | tags=`user_type`
- `FAIL` `humanlike_user_type_conversational` | category=`humanlike_user_type` | tags=`user_type`
- `FAIL` `humanlike_memory_reuse_location` | category=`humanlike_memory` | tags=`memory, critical`
- `FAIL` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `FAIL` `humanlike_memory_reuse_preference` | category=`humanlike_memory` | tags=`memory, critical`
- `FAIL` `humanlike_emotion_recognition_relaxed` | category=`humanlike_emotion` | tags=`emotion`
- `FAIL` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_emotion_recognition_joking_response` | category=`humanlike_emotion` | tags=`emotion`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_low_priority_never_ask` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `FAIL` `humanlike_medium_field_timing_after_age` | category=`humanlike_field_timing` | tags=`field_timing, medium_field`
- `FAIL` `humanlike_medium_field_timing_income_optional` | category=`humanlike_field_timing` | tags=`field_timing, medium_field`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `FAIL` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_no_large_repeat_profile` | category=`humanlike_memory` | tags=`memory`

## 失败详情

### contact_phone_then_wechat_prompt

- 分类: `contact`
- 标签: `smoke, critical, contact_phone`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=phone profile.phone 期望为真值，实际 None
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['微信', '留一个', '沟通']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321
    AI: 

### contact_phone_and_wechat_same_turn

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=phone profile.phone 期望为真值，实际 None
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321，微信wx123456
    AI: 

### contact_wechat_rejection_should_not_end

- 分类: `contact`
- 标签: `critical, contact_wechat`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=phone profile.phone 期望为真值，实际 None
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321
    AI: 
  - Turn 2 用户: 不留微信
    AI: 如果电话不方便的话，留个微信也可以，后面沟通会方便一点～

### contact_phone_after_wechat_rejection_should_not_end

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 
  - Turn 2 用户: 不留电话
    AI: 这个电话只是留作登记和后面联系用的，不会私下打扰你。你方便的话发我一个号码就行～

### contact_wechat_only_then_ask_phone

- 分类: `contact`
- 标签: `critical, contact_wechat, contact_phone`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['电话', '号码', '联系']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 

### contact_wechat_only_then_phone_refusal

- 分类: `contact`
- 标签: `contact_wechat, contact_phone`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 
  - Turn 2 用户: 电话先不留
    AI: 这个电话只是留作登记和后面联系用的，不会私下打扰你。你方便的话发我一个号码就行～

### contact_hk_phone_then_wechat

- 分类: `contact`
- 标签: `critical, contact_hk`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=location profile.location 期望 '香港'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～

### contact_hk_user_provides_wechat_only

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat, contact_phone`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['电话', '号码', '联系']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生，我微信wx123456
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生，我微信wx123456
    AI: 

### contact_hk_user_reject_wechat

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～
  - Turn 3 用户: 微信不方便
    AI: 

### ending_divorce_incomplete_should_end

- 分类: `ending`
- 标签: `smoke, critical, divorce`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['办妥', '再来', '顺利']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 
- 对话回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 

### ending_age_under_limit

- 分类: `ending`
- 标签: `critical, ending_gate`
- 断言通过: 0/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [profile_field_equals] turn=- field=age_under_limit profile.age_under_limit 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['24岁', '再来', '成熟']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 
- 对话回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 

### ending_divorce_confirmed_should_continue

- 分类: `ending`
- 标签: `critical, divorce`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=marital_status profile.marital_status 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我离异
    AI: 
  - Turn 2 用户: 已经办妥了
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### faq_priority_mediator

- 分类: `faq`
- 标签: `smoke, critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['同城脱单联盟', '牵线']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你是中介吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 你是中介吗
    AI: 后续有合适的人选时联系你～

### faq_priority_fee

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['免费', '收费', '定制']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～

### faq_priority_store_location

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳门店', '服务点', '定位']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 有线下门店吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 有线下门店吗
    AI: 后续有合适的人选时联系你～

### faq_priority_how_match

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['线上', '匹配', '线下安排', '牵线']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们怎么匹配
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们怎么匹配
    AI: 后续有合适的人选时联系你～

### faq_priority_can_add_wechat

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['互换', '牵线', '先搭桥', '双方合适']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### faq_priority_photo_request

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['合适后', '互换照片', '双方觉得合适']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 能先看照片吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 能先看照片吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### faq_priority_followup_question_should_still_answer

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/3
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['免费', '收费', '定制']，实际 '后续有合适的人选时联系你～'
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['定制', '收费', '服务']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～
  - Turn 3 用户: 那定制服务怎么收费
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～
  - Turn 3 用户: 那定制服务怎么收费
    AI: 后续有合适的人选时联系你～

### faq_priority_success_rate

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['成功', '配对', '牵线', '案例']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们成功率怎么样
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们成功率怎么样
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### faq_priority_service_area

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '地区', '范围']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们服务哪些地区
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们服务哪些地区
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### faq_priority_reliable

- 分类: `faq`
- 标签: `critical, faq_reliable`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['靠谱', '安全', '放心', '靠谱的']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们平台靠谱吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们平台靠谱吗
    AI: 后续有合适的人选时联系你～

### faq_priority_safety

- 分类: `faq`
- 标签: `faq_safety`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['安全', '放心', '可靠', '正规', '专业']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们平台安全吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们平台安全吗
    AI: 后续有合适的人选时联系你～

### field_multi_info_extract_basic

- 分类: `field_collection`
- 标签: `critical, extract_basic`
- 断言通过: 1/4
- 失败摘要:
  - [profile_field_equals] turn=- field=location profile.location 期望 '深圳'，实际 None
  - [profile_field_equals] turn=- field=education profile.education 期望 '本科'，实际 None
  - [profile_field_truthy] turn=- field=occupation profile.occupation 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，做运营的
    AI: 

### field_age_parse_90s

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=age profile.age 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是90后
    AI: 

### field_age_parse_birth_year

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=age profile.age 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是1992年的
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### field_location_extract_shenzhen

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_equals] turn=- field=location profile.location 期望 '深圳'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我现在在深圳工作生活
    AI: 

### field_partner_requirement_should_not_override_location

- 分类: `field_collection`
- 标签: `critical, extract_guard`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=partner_requirement profile.partner_requirement 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 想找深圳的男生
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### field_education_extract_master

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_equals] turn=- field=education profile.education 期望 '硕士'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是硕士
    AI: 

### field_occupation_extract_programmer

- 分类: `field_collection`
- 标签: `extract_basic, extract_guard`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=occupation profile.occupation 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我做程序员的
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### field_multi_sentence_extract

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_equals] turn=- field=location profile.location 期望 '深圳'，实际 None
  - [profile_field_equals] turn=- field=education profile.education 期望 '本科'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生。深圳的。本科。做运营。
    AI: 

### field_sex_extract_male

- 分类: `field_collection`
- 标签: `extract_basic, sex`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_equals] turn=- field=sex profile.sex 期望 '男'，实际 '女'
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是男生，想找女生
    AI: 

### field_age_variants_85s

- 分类: `field_collection`
- 标签: `extract_basic, age`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=age profile.age 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是85后的
    AI: 

### field_occupation_variants_teacher

- 分类: `field_collection`
- 标签: `extract_basic, occupation`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=occupation profile.occupation 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是老师
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### field_marital_status_single

- 分类: `field_collection`
- 标签: `extract_basic, marital_status`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_equals] turn=- field=marital_status profile.marital_status 期望 '单身'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我单身，想找对象
    AI: 

### field_marital_status_divorced

- 分类: `field_collection`
- 标签: `extract_basic, marital_status`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_equals] turn=- field=marital_status profile.marital_status 期望 '离异'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我离异，想找个合适的
    AI: 

### field_height_extract_cm

- 分类: `field_collection`
- 标签: `extract_basic, height`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=height profile.height 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我身高168cm
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### field_income_extract_monthly

- 分类: `field_collection`
- 标签: `extract_basic, income`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=monthly_income profile.monthly_income 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我月收入一万左右
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_reception_joking_user

- 分类: `humanlike_reception`
- 标签: `reception, emotion`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['了解', '认识', '匹配', '适合']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你查户口呢问这么细
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营
    AI: 
  - Turn 2 用户: 你查户口呢问这么细
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_reception_defensive_user

- 分类: `humanlike_reception`
- 标签: `critical, reception, emotion`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['靠谱', '安全', '放心', '正规', '专业']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们靠谱吗，干嘛问这个
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们靠谱吗，干嘛问这个
    AI: 后续有合适的人选时联系你～

### humanlike_transition_with_feedback

- 分类: `humanlike_transition`
- 标签: `transition`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['不错', '好的', '了解', '运营']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 我是做运营的
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，深圳，本科
    AI: 
  - Turn 2 用户: 我是做运营的
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_user_type_cooperative

- 分类: `humanlike_user_type`
- 标签: `user_type, critical`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=location profile.location 期望为真值，实际 None
  - [profile_field_truthy] turn=- field=education profile.education 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 

### humanlike_user_type_conversational

- 分类: `humanlike_user_type`
- 标签: `user_type`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['踏实', '经历', '理解']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 我之前谈过两个，一个太花心一个太粘人，现在想找个踏实的
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 我之前谈过两个，一个太花心一个太粘人，现在想找个踏实的
    AI: 

### humanlike_memory_reuse_location

- 分类: `humanlike_memory`
- 标签: `memory, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳', '那边']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营
    AI: 
  - Turn 2 用户: 那边有什么好的相亲资源吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_memory_reuse_occupation

- 分类: `humanlike_memory`
- 标签: `memory`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['运营', '工作', '忙']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 我工作比较忙
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营
    AI: 
  - Turn 2 用户: 我工作比较忙
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_memory_reuse_preference

- 分类: `humanlike_memory`
- 标签: `memory, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['成熟', '稳重', '合拍', '推荐']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 有什么推荐吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，想找个成熟稳重的
    AI: 
  - Turn 2 用户: 有什么推荐吗
    AI: 方便留个电话吗？后续有合适的人选时联系你～

### humanlike_emotion_recognition_relaxed

- 分类: `humanlike_emotion`
- 标签: `emotion`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=location profile.location 期望为真值，实际 None
  - [profile_field_truthy] turn=- field=occupation profile.occupation 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 你好呀，我是女生，今年28岁，在深圳工作，本科毕业，做运营的，单身，想找个合适的男生
    AI: 

### humanlike_emotion_recognition_defensive_explanation

- 分类: `humanlike_emotion`
- 标签: `emotion, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['靠谱', '安全', '放心', '正规', '专业']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你们靠谱吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你们靠谱吗
    AI: 后续有合适的人选时联系你～

### humanlike_medium_field_timing_after_age

- 分类: `humanlike_field_timing`
- 标签: `field_timing, medium_field`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=1 turn=1 需要包含任一关键词 ['找', '要求', '期待', '喜欢', '城市', '工作生活']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，28岁
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，28岁
    AI: 

### humanlike_medium_field_timing_income_optional

- 分类: `humanlike_field_timing`
- 标签: `field_timing, medium_field`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=occupation profile.occupation 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 

### humanlike_answer_question_then_resume

- 分类: `humanlike_rules`
- 标签: `rules, critical`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['免费', '收费', '定制']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 怎么收费
    AI: 后续有合适的人选时联系你～
  - Turn 3 用户: 好的，那我是女生，90后，深圳
    AI: 
