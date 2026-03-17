# 真实 AI 回归报告

- 开始时间: 2026-03-17T15:57:15
- 结束时间: 2026-03-17T16:19:24
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 61
- 通过: 55
- 失败: 6
- 总耗时: 1329.681s
- 平均耗时: 21.798s
- 最长耗时: 55.969s
- Token: 556968 (调用 104 次)

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
- `FAIL` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `FAIL` `contact_hk_user_reject_wechat` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_non_hk_wechat_first_then_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_user_says_phone_inconvenient_then_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `FAIL` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`
- `PASS` `ending_gay_user_variant` | category=`ending` | tags=`ending_gate, lgbt`
- `PASS` `ending_divorce_incomplete_variant` | category=`ending` | tags=`divorce`
- `PASS` `ending_proxy_user_variant` | category=`ending` | tags=`ending_gate, proxy_user`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
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
- `PASS` `field_occupation_placeholder_guard` | category=`field_collection` | tags=`smoke, critical, extract_guard`
- `FAIL` `field_multi_info_extract_basic` | category=`field_collection` | tags=`critical, extract_basic`
- `PASS` `field_sex_extract_male` | category=`field_collection` | tags=`extract_basic, sex`
- `PASS` `field_age_variants_85s` | category=`field_collection` | tags=`extract_basic, age`
- `PASS` `field_occupation_variants_teacher` | category=`field_collection` | tags=`extract_basic, occupation`
- `FAIL` `field_multi_sentence_extract` | category=`field_collection` | tags=`extract_basic`
- `PASS` `field_marital_status_single` | category=`field_collection` | tags=`extract_basic, marital_status`
- `PASS` `field_marital_status_divorced` | category=`field_collection` | tags=`extract_basic, marital_status`
- `PASS` `field_height_extract_cm` | category=`field_collection` | tags=`extract_basic, height`
- `PASS` `field_income_extract_monthly` | category=`field_collection` | tags=`extract_basic, income`
- `PASS` `field_location_variants_district` | category=`field_collection` | tags=`extract_basic, location`
- `PASS` `field_education_variants_master` | category=`field_collection` | tags=`extract_basic, education`

## 失败详情

### contact_user_explicit_wechat_preference

- 分类: `contact`
- 标签: `critical, contact_wechat, contact_preference`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信', '可以', '发我']，实际 '方便留一下你的电话号码吗？后续有合适的人选我们好及时联系你哦。'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话号码']，实际 '方便留一下你的电话号码吗？后续有合适的人选我们好及时联系你哦。'
- 失败轮次精简回放:
  - Turn 2 用户: 用微信联系吧
    AI: 方便留一下你的电话号码吗？后续有合适的人选我们好及时联系你哦。
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下来啦~那你对另一半除了是男生之外，还有没有其他具体的要求呀？比如年龄、工作这些方面的偏好都可以说说~
  - Turn 2 用户: 用微信联系吧
    AI: 方便留一下你的电话号码吗？后续有合适的人选我们好及时联系你哦。

### contact_hk_user_reject_wechat

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 好的，你的基本情况我都记下啦~对了，你对心仪的另一半除了性别是男生之外，还有没有其他大概的要求呀？
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～
  - Turn 3 用户: 微信不方便
    AI: 我们留微信只是之后有符合你要求的合适男生时可以第一时间通知你，绝对不会随便发无关消息打扰你的~

### contact_user_says_phone_inconvenient_then_wechat

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_phone profile.rejected_phone 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下啦～那你对另一半有没有什么大致的要求呀？
  - Turn 2 用户: 电话不方便，留微信吧
    AI: 可以呀，那你直接把微信号发我就行，我这边记下来后续好联系你～
  - Turn 3 用户: wxabc123
    AI: 好的呀，我先记下啦，后面有合适的人选会尽快联系你～

### ending_fake_info_pattern

- 分类: `ending`
- 标签: `ending_gate, fake_info`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['有意思', '认真对待', '真实信息']，实际 '哈哈你也太可爱啦，说真的你实际年龄是多大呀，我这边好帮你筛选更适配的人选~'
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 哈哈你也太可爱啦，说真的你实际年龄是多大呀，我这边好帮你筛选更适配的人选~
- 对话回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 哈哈你也太可爱啦，说真的你实际年龄是多大呀，我这边好帮你筛选更适配的人选~

### field_multi_info_extract_basic

- 分类: `field_collection`
- 标签: `critical, extract_basic`
- 断言通过: 4/6
- 失败摘要:
  - [profile_field_truthy] turn=- field=monthly_income profile.monthly_income 期望为真值，实际 None
  - [profile_field_truthy] turn=- field=marital_status profile.marital_status 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，做运营的
    AI: 好的，你的基本情况我都记下啦~我顺带确认下，你现在是单身状态在认真了解脱单的吗？

### field_multi_sentence_extract

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 4/6
- 失败摘要:
  - [profile_field_truthy] turn=- field=monthly_income profile.monthly_income 期望为真值，实际 None
  - [profile_field_truthy] turn=- field=marital_status profile.marital_status 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生。深圳的。本科。做运营的
    AI: 好的呀，这些基础信息我都记下来啦，方便说下你今年多大吗？
