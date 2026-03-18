# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:34:51
- 结束时间: 2026-03-18T17:20:51
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 108
- 通过: 100
- 失败: 8
- 总耗时: 2759.146s
- 平均耗时: 25.548s
- 最长耗时: 64.696s
- Token: 990520 (调用 183 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
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
- `FAIL` `contact_phone_too_long_should_retry` | category=`contact` | tags=`contact_phone, retry`
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
- `FAIL` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_followup_question_should_still_answer` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_success_rate` | category=`faq` | tags=`faq_priority`
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
- `FAIL` `humanlike_user_type_conservative` | category=`humanlike_user_type` | tags=`user_type`
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
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 True，实际 False
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我电话17688654321
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～
  - Turn 2 用户: 不留微信
    AI: 好的～小姐姐，那先这样啦～有需要随时再来找我哦～拜拜👋

### contact_hk_phone_then_wechat_rejected_not_end

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 False，实际 True
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 好的，你的基本情况我都记下来啦，那你对另一半有没有什么具体的要求呀？
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～
  - Turn 3 用户: 微信先不留
    AI: 好的～小姐姐，那先这样啦～有需要随时再来找我哦～拜拜👋

### contact_hk_user_reject_wechat

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=wechat_ask_count profile.wechat_ask_count 期望 1，实际 0
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 好哒，你的基本情况我都记下啦~那你对另一半还有没有别的具体要求呀？
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～
  - Turn 3 用户: 微信不方便
    AI: 好的～小姐姐，那先这样啦～有需要随时再来找我哦～拜拜👋

### contact_phone_too_long_should_retry

- 分类: `contact`
- 标签: `contact_phone, retry`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_falsey] turn=- field=phone profile.phone 期望为空/假值，实际 '17688654321'
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下来啦，除了想找男生之外，你对另一半还有没有其他具体的要求呀？
  - Turn 2 用户: 我电话17688654321123456
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～

### faq_priority_fee

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['年龄']，实际 '咱们匹配是免费的哦，要是需要定制服务的话是可选的，碰到不合适的你完全可以拒绝哒。对啦，你今年大概多大呀，知道年龄我也好先帮你框个合适的匹配范围哦。如果你还有顾虑也可以继续问我。'
- 失败轮次精简回放:
  - Turn 2 用户: 怎么收费
    AI: 咱们匹配是免费的哦，要是需要定制服务的话是可选的，碰到不合适的你完全可以拒绝哒。对啦，你今年大概多大呀，知道年龄我也好先帮你框个合适的匹配范围哦。如果你还有顾虑也可以继续问我。
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 是哒，我们这边本地优质单身资源挺多的，你今年多大呀？知道年龄我先帮你框个大概的匹配范围哦。
  - Turn 2 用户: 怎么收费
    AI: 咱们匹配是免费的哦，要是需要定制服务的话是可选的，碰到不合适的你完全可以拒绝哒。对啦，你今年大概多大呀，知道年龄我也好先帮你框个合适的匹配范围哦。如果你还有顾虑也可以继续问我。

### faq_priority_how_match

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['年龄']，实际 '我们是先根据你的基本情况在线上匹配合适的同城单身朋友，双方初步聊下来觉得合适的话，再帮你们安排线下见面哒。对啦，想问下你今年大概多大呀，我好先帮你筛选符合年龄段的人选哦。如果你还有顾虑也可以继续问我。'
- 失败轮次精简回放:
  - Turn 2 用户: 你们怎么匹配
    AI: 我们是先根据你的基本情况在线上匹配合适的同城单身朋友，双方初步聊下来觉得合适的话，再帮你们安排线下见面哒。对啦，想问下你今年大概多大呀，我好先帮你筛选符合年龄段的人选哦。如果你还有顾虑也可以继续问我。
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 哈哈我这边是专门帮同城朋友牵线的哈，想问下你今年多大呀？我好先帮你筛选下合适年龄段的人选~
  - Turn 2 用户: 你们怎么匹配
    AI: 我们是先根据你的基本情况在线上匹配合适的同城单身朋友，双方初步聊下来觉得合适的话，再帮你们安排线下见面哒。对啦，想问下你今年大概多大呀，我好先帮你筛选符合年龄段的人选哦。如果你还有顾虑也可以继续问我。

### faq_priority_success_rate

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['年龄']，实际 '我们在深圳做了3年牵线啦，已经帮很多小伙伴成功脱单了，不过脱单毕竟是双向选择，我们会尽量给你匹配契合度高的人选，成功率还是挺可观的~对啦，你大概是哪个年龄段呀，知道这个我好先帮你框定合适的匹配范围哦。'
- 失败轮次精简回放:
  - Turn 2 用户: 你们成功率怎么样
    AI: 我们在深圳做了3年牵线啦，已经帮很多小伙伴成功脱单了，不过脱单毕竟是双向选择，我们会尽量给你匹配契合度高的人选，成功率还是挺可观的~对啦，你大概是哪个年龄段呀，知道这个我好先帮你框定合适的匹配范围哦。
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 嗯嗯，我们这边有挺多合适的同城优质单身的~对了，你今年多大呀，我好先帮你筛选对应年龄段的人选哦？
  - Turn 2 用户: 你们成功率怎么样
    AI: 我们在深圳做了3年牵线啦，已经帮很多小伙伴成功脱单了，不过脱单毕竟是双向选择，我们会尽量给你匹配契合度高的人选，成功率还是挺可观的~对啦，你大概是哪个年龄段呀，知道这个我好先帮你框定合适的匹配范围哦。

### humanlike_user_type_conservative

- 分类: `humanlike_user_type`
- 标签: `user_type`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['没关系', '理解', '方便']，实际 '没事哒～说个大概年龄段就可以哦，我好帮你划合适的匹配范围嘛。'
- 失败轮次精简回放:
  - Turn 2 用户: 这个不方便说
    AI: 没事哒～说个大概年龄段就可以哦，我好帮你划合适的匹配范围嘛。
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 哈喽呀，想找对象的话我先帮你筛筛合适的人选哦，你今年多大啦？
  - Turn 2 用户: 这个不方便说
    AI: 没事哒～说个大概年龄段就可以哦，我好帮你划合适的匹配范围嘛。
