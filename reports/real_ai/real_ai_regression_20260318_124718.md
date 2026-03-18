# 真实 AI 回归报告

- 开始时间: 2026-03-18T11:50:33
- 结束时间: 2026-03-18T12:47:18
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 108
- 通过: 99
- 失败: 9
- 总耗时: 3404.819s
- 平均耗时: 31.526s
- 最长耗时: 945.462s
- Token: 999930 (调用 186 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `FAIL` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `FAIL` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_invalid_then_valid` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_with_spaces_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_hk_phone_then_wechat` | category=`contact` | tags=`critical, contact_hk`
- `FAIL` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
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
- `FAIL` `contact_phone_with_86_prefix` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_phone_with_dashes` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_wechat_with_special_chars` | category=`contact` | tags=`contact_wechat, normalization`
- `FAIL` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `contact_phone_too_short_should_retry` | category=`contact` | tags=`contact_phone, retry`
- `PASS` `contact_phone_too_long_should_retry` | category=`contact` | tags=`contact_phone, retry`
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `PASS` `ending_spam_user_variant` | category=`ending` | tags=`spam_user`
- `PASS` `ending_spam_user_aggressive` | category=`ending` | tags=`spam_user`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `FAIL` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
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
- `PASS` `humanlike_reception_joking_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `PASS` `humanlike_reception_defensive_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `PASS` `humanlike_reception_evasive_user` | category=`humanlike_reception` | tags=`reception, emotion`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `PASS` `humanlike_transition_with_feedback` | category=`humanlike_transition` | tags=`transition`
- `PASS` `humanlike_light_interaction_after_fields` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `PASS` `humanlike_light_interaction_short_feedback` | category=`humanlike_light_interaction` | tags=`light_interaction`
- `PASS` `humanlike_user_type_cooperative` | category=`humanlike_user_type` | tags=`user_type, critical`
- `PASS` `humanlike_user_type_conservative` | category=`humanlike_user_type` | tags=`user_type`
- `PASS` `humanlike_user_type_conversational` | category=`humanlike_user_type` | tags=`user_type`
- `PASS` `humanlike_memory_reuse_location` | category=`humanlike_memory` | tags=`memory, critical`
- `PASS` `humanlike_memory_reuse_occupation` | category=`humanlike_memory` | tags=`memory`
- `PASS` `humanlike_memory_reuse_preference` | category=`humanlike_memory` | tags=`memory, critical`
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

### contact_wechat_rejection_should_not_end

- 分类: `contact`
- 标签: `critical, contact_wechat`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～
  - Turn 2 用户: 不留微信
    AI: 好哒，不留微信没关系的~对了，想问下你目前月收入大概是多少呀，不方便说也没事的哈

### contact_phone_after_wechat_rejection_should_not_end

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
  - Turn 2 用户: 不留电话
    AI: 电话只是系统登记用的哦，有合适的男士才能联系到你，我们不会私下随意打扰的，你放心哈。

### contact_wechat_only_then_phone_refusal

- 分类: `contact`
- 标签: `contact_wechat, contact_phone`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
  - Turn 2 用户: 电话先不留
    AI: 你放心哦，电话只是用来做系统登记的，有合适的男生匹配到了才会联系你，我们绝对不会私下打扰的~

### contact_hk_phone_then_wechat_rejected_not_end

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 好哒，你的基本情况我都记下啦~那你对另一半有没有什么具体的要求呀？比如年龄范围、工作地偏好之类的？
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～
  - Turn 3 用户: 微信先不留
    AI: 你放心哈，微信只是后续有匹配到合适的男生时方便及时通知你，我们不会随便发消息打扰你的~

### contact_phone_with_86_prefix

- 分类: `contact`
- 标签: `contact_phone, normalization`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=phone profile.phone 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好的，你的基本情况我都记下啦~你对另一半有没有什么具体的要求呀？
  - Turn 2 用户: 我电话8617688654321
    AI: 好的，我已经记下你的电话啦，后续有合适的男生人选我会及时联系你哦。

### contact_wechat_mobile_format

- 分类: `contact`
- 标签: `contact_wechat, normalization`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好哒，你说的这些基本情况我都记下啦～那你对未来的另一半有没有什么大致的要求呀？
  - Turn 2 用户: 微信就是手机号17688654321
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['朋友', '家人', '本人直接来聊']，实际 '你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～'
- 失败轮次精简回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～

### ending_normal_complete

- 分类: `ending`
- 标签: `critical, normal_complete`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下啦～那你对另一半有没有什么大致的偏好呀？
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 好的，我已经记下你的联系方式啦，后续有合适的男生会第一时间联系你的~

### ending_fake_info_pattern

- 分类: `ending`
- 标签: `ending_gate, fake_info`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 哈哈你可太有意思啦，咱说正经的哦，你实际年龄大概是多少呀，我好后续帮你筛选适配的人选~
