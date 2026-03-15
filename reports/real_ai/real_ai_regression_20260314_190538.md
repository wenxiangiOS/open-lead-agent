# 真实 AI 回归报告

- 开始时间: 2026-03-14T18:49:46
- 结束时间: 2026-03-14T19:05:38
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 50
- 通过: 30
- 失败: 20
- 总耗时: 951.848s
- 平均耗时: 19.037s
- 最长耗时: 64.344s
- Token: 336516 (调用 62 次)

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
- `FAIL` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `PASS` `contact_user_questions_privacy_before_phone` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_phone_after_privacy_question` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_wechat_after_phone_prompt` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_says_no_contact_at_all` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_hk_user_provides_wechat_only` | category=`contact` | tags=`critical, contact_hk, contact_wechat, contact_phone`
- `PASS` `contact_phone_with_text_prefix_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `FAIL` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `FAIL` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `FAIL` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_store_location` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `FAIL` `faq_priority_photo_request` | category=`faq` | tags=`faq_priority`
- `FAIL` `faq_priority_followup_question_should_still_answer` | category=`faq` | tags=`faq_priority`
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
- `FAIL` `field_wechat_should_not_pollute_location` | category=`field_collection` | tags=`extract_guard, contact_wechat`
- `PASS` `field_greeting_should_not_fill_profile` | category=`field_collection` | tags=`extract_guard, smoke`

## 失败详情

### contact_user_asks_wechat_instead_of_phone

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信']，实际 '可以的，你提供一下就好，后续有合适的人选方便及时联系你~'
- 失败轮次精简回放:
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 可以的，你提供一下就好，后续有合适的人选方便及时联系你~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好哒，你说的这些基本情况我都记下来啦～那你对另一半有没有什么大致的要求呀？
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 可以的，你提供一下就好，后续有合适的人选方便及时联系你~
  - Turn 3 用户: 可以，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～

### ending_divorce_incomplete_should_end

- 分类: `ending`
- 标签: `smoke, critical, divorce`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 是这样的，你现在手续还没办妥的话我们暂时没法帮你匹配哦，等你后续手续都处理好了随时再来找我就可以哈。

### ending_age_under_limit

- 分类: `ending`
- 标签: `critical, ending_gate`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['24岁', '再来', '成熟']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 
- 对话回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 

### ending_already_married

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我已经结婚了
    AI: 不好意思呀，我们这边是专门帮单身朋友牵线脱单的，已婚的话暂时没办法为你提供服务哦，如果身边有单身的亲友有需要的话也可以推荐过来哒。

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=proxy_user profile.proxy_user 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 原来是帮朋友咨询呀～那你朋友是男生还是女生呀？

### ending_lgbt_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['异性相亲', '不太适合', '专业的平台']，实际 '好哒，我了解啦~对了，你今年多大呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 好哒，我了解啦~对了，你今年多大呀？
- 对话回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 好哒，我了解啦~对了，你今年多大呀？

### faq_priority_store_location

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['深圳门店', '服务点', '定位']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 有线下门店吗
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 
  - Turn 2 用户: 有线下门店吗
    AI: 

### faq_priority_how_match

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['线上', '匹配', '线下安排', '牵线']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 你们怎么匹配
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 
  - Turn 2 用户: 你们怎么匹配
    AI: 

### faq_priority_can_add_wechat

- 分类: `faq`
- 标签: `critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['互换', '牵线', '先搭桥', '双方合适']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 
  - Turn 2 用户: 可以直接加对方微信吗
    AI: 

### faq_priority_photo_request

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['合适后', '互换照片', '双方觉得合适']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 能先看照片吗
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 
  - Turn 2 用户: 能先看照片吗
    AI: 

### faq_priority_followup_question_should_still_answer

- 分类: `faq`
- 标签: `faq_priority`
- 断言通过: 1/3
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['免费', '收费', '定制']，实际 ''
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['定制', '收费', '服务']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 怎么收费
    AI: 
  - Turn 3 用户: 那定制服务怎么收费
    AI: 
- 对话回放:
  - Turn 1 用户: 找对象
    AI: 
  - Turn 2 用户: 怎么收费
    AI: 
  - Turn 3 用户: 那定制服务怎么收费
    AI: 

### field_multi_info_extract_basic

- 分类: `field_collection`
- 标签: `critical, extract_basic`
- 断言通过: 0/4
- 失败摘要:
  - [profile_field_equals] turn=- field=sex profile.sex 期望 '女'，实际 None
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
    AI: 

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
    AI: 

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
    AI: 

### field_multi_sentence_extract

- 分类: `field_collection`
- 标签: `extract_basic`
- 断言通过: 0/3
- 失败摘要:
  - [profile_field_equals] turn=- field=sex profile.sex 期望 '女'，实际 None
  - [profile_field_equals] turn=- field=location profile.location 期望 '深圳'，实际 None
  - [profile_field_equals] turn=- field=education profile.education 期望 '本科'，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生。深圳的。本科。做运营。
    AI: 

### field_wechat_should_not_pollute_location

- 分类: `field_collection`
- 标签: `extract_guard, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我微信wx123456
    AI: 
