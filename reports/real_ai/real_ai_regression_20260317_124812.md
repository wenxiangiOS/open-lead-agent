# 真实 AI 回归报告

- 开始时间: 2026-03-17T12:30:46
- 结束时间: 2026-03-17T12:48:12
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 50
- 通过: 47
- 失败: 3
- 总耗时: 1046.521s
- 平均耗时: 20.93s
- 最长耗时: 53.072s
- Token: 450408 (调用 84 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `FAIL` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
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
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `FAIL` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `PASS` `faq_priority_followup_question_should_still_answer` | category=`faq` | tags=`faq_priority`
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

## 失败详情

### contact_phone_invalid_should_retry

- 分类: `contact`
- 标签: `critical, contact_phone, retry`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['电话', '确认', '重新']，实际 '好的，号码我已经记下啦，后续有符合你要求的合适人选我会及时联系你的~'
- 失败轮次精简回放:
  - Turn 2 用户: 我电话12345
    AI: 好的，号码我已经记下啦，后续有符合你要求的合适人选我会及时联系你的~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下来啦，那你对另一半有没有什么大致的要求呀？
  - Turn 2 用户: 我电话12345
    AI: 好的，号码我已经记下啦，后续有符合你要求的合适人选我会及时联系你的~

### ending_both_contact_refused

- 分类: `ending`
- 标签: `critical, ending_gate, contact_phone, contact_wechat`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 你的基本情况我都记下来啦，那你对另一半有没有什么大概的要求呀？
  - Turn 2 用户: 不留电话
    AI: 你放心哦，电话只是用于系统登记，后续有合适的适配人选才能联系到你，我们不会私下随意打扰你的~
  - Turn 3 用户: 还是不留电话
    AI: 没关系呀，要是微信方便的话留一个就好，后面有合适的人选我好及时联系你呀～
  - Turn 4 用户: 微信也不留
    AI: 好的，那你之后要是有脱单相关的需求随时和我说就可以哦。
  - Turn 5 用户: 还是不留微信
    AI: 微信主要是方便后续有合适的优质男嘉宾第一时间通知你哦，我们平时绝对不会随便发消息打扰你的~

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['朋友', '家人', '直接来和我聊']，实际 '可以理解你是替TA来关心这件事呀～不过这种情况还是本人直接来聊会更合适一点，这样我这边也更方便判断需求～'
- 失败轮次精简回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 可以理解你是替TA来关心这件事呀～不过这种情况还是本人直接来聊会更合适一点，这样我这边也更方便判断需求～
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 可以理解你是替TA来关心这件事呀～不过这种情况还是本人直接来聊会更合适一点，这样我这边也更方便判断需求～
