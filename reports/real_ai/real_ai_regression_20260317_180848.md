# 真实 AI 回归报告

- 开始时间: 2026-03-17T17:48:14
- 结束时间: 2026-03-17T18:08:48
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 51
- 通过: 46
- 失败: 5
- 总耗时: 1234.209s
- 平均耗时: 24.2s
- 最长耗时: 52.031s
- Token: 543195 (调用 100 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `PASS` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_invalid_then_valid` | category=`contact` | tags=`critical, contact_phone, retry`
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
- `FAIL` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `FAIL` `contact_hk_user_reject_wechat` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_non_hk_wechat_first_then_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_user_says_phone_inconvenient_then_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `PASS` `ending_separation_should_end` | category=`ending` | tags=`critical, ending_gate, divorce`
- `PASS` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`
- `PASS` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_divorce_confirmed_should_continue` | category=`ending` | tags=`critical, divorce`
- `PASS` `ending_after_conversation_ended_followup` | category=`ending` | tags=`critical, ending_gate`
- `PASS` `ending_spam_user` | category=`ending` | tags=`critical, spam_user`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `PASS` `faq_priority_fee` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_how_match` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_can_add_wechat` | category=`faq` | tags=`critical, faq_priority`
- `PASS` `faq_priority_reliable` | category=`faq` | tags=`critical, faq_reliable`
- `PASS` `field_occupation_placeholder_guard` | category=`field_collection` | tags=`smoke, critical, extract_guard`
- `PASS` `field_multi_info_extract_basic` | category=`field_collection` | tags=`critical, extract_basic`
- `PASS` `field_partner_requirement_should_not_override_location` | category=`field_collection` | tags=`critical, extract_guard`
- `PASS` `humanlike_reception_hesitant_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `PASS` `humanlike_reception_defensive_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`
- `PASS` `humanlike_transition_natural_field_switch` | category=`humanlike_transition` | tags=`transition, critical`
- `PASS` `humanlike_user_type_cooperative` | category=`humanlike_user_type` | tags=`user_type, critical`
- `PASS` `humanlike_memory_reuse_location` | category=`humanlike_memory` | tags=`memory, critical`
- `FAIL` `humanlike_memory_reuse_preference` | category=`humanlike_memory` | tags=`memory, critical`
- `PASS` `humanlike_emotion_recognition_defensive_explanation` | category=`humanlike_emotion` | tags=`emotion, critical`
- `PASS` `humanlike_ask_limit_core_field_2_times` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_medium_field_1_time` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_ask_limit_low_priority_never_ask` | category=`humanlike_ask_limit` | tags=`ask_limit, critical`
- `PASS` `humanlike_no_consecutive_same_field_ask` | category=`humanlike_rules` | tags=`rules, critical`
- `PASS` `humanlike_answer_question_then_resume` | category=`humanlike_rules` | tags=`rules, critical`

## 失败详情

### contact_user_explicit_wechat_preference

- 分类: `contact`
- 标签: `critical, contact_wechat, contact_preference`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信', '可以', '发我']，实际 '方便留一下你的电话号码吗？后续有合适的人选方便联系你哦。'
  - [response_not_contains_any] turn=2 turn=2 不应包含关键词 ['电话号码']，实际 '方便留一下你的电话号码吗？后续有合适的人选方便联系你哦。'
- 失败轮次精简回放:
  - Turn 2 用户: 用微信联系吧
    AI: 方便留一下你的电话号码吗？后续有合适的人选方便联系你哦。
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好的，你说的这些基本情况我都记下来啦～那你对另一半有没有什么具体的要求呀，比如年龄、工作这些都可以说说哦。
  - Turn 2 用户: 用微信联系吧
    AI: 方便留一下你的电话号码吗？后续有合适的人选方便联系你哦。

### contact_hk_user_reject_wechat

- 分类: `contact`
- 标签: `critical, contact_hk, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_wechat profile.rejected_wechat 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，28岁，在香港，本科，文员，单身，想找男生
    AI: 好哒，你的基本情况我都了解啦～你对未来的另一半除了是男生之外，还有没有其他大致的要求呀？
  - Turn 2 用户: 电话56789012
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～
  - Turn 3 用户: 微信不方便
    AI: 我们平时不会随便打扰你，就是后续有合适的匹配人选时发对方资料用微信更方便，实在不方便也没关系哒。

### contact_user_says_phone_inconvenient_then_wechat

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=rejected_phone profile.rejected_phone 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 好哒，你的基本情况我都记下来啦～那你对另一半有没有什么大致的要求呀？
  - Turn 2 用户: 电话不方便，留微信吧
    AI: 可以呀，你直接发微信号就行，我这边先记下来~
  - Turn 3 用户: wxabc123
    AI: 好的呀，我先记下啦，后面有合适的人选会尽快联系你～

### ending_normal_complete

- 分类: `ending`
- 标签: `critical, normal_complete`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 你的基本情况我都记下来啦～那你对另一半有没有什么具体的偏好呀？比如年龄范围、工作地这类的要求都可以说说哦。
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 好的，我已经记下你的联系方式啦，后续有合适的人选会第一时间联系你哦。

### humanlike_memory_reuse_preference

- 分类: `humanlike_memory`
- 标签: `memory, critical`
- 断言通过: 0/1
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['成熟', '稳重']，实际 '我们得先了解下你的基本情况才能给你匹配合适的人选哦~对啦，你大概是什么学历呀，知道这个我给你筛推荐的时候也能更贴合你的情况哒。'
- 失败轮次精简回放:
  - Turn 2 用户: 有什么推荐吗
    AI: 我们得先了解下你的基本情况才能给你匹配合适的人选哦~对啦，你大概是什么学历呀，知道这个我给你筛推荐的时候也能更贴合你的情况哒。
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，想找个成熟稳重的
    AI: 好哒，成熟稳重的另一半相处起来确实很让人安心~想问下你是什么学历呀？
  - Turn 2 用户: 有什么推荐吗
    AI: 我们得先了解下你的基本情况才能给你匹配合适的人选哦~对啦，你大概是什么学历呀，知道这个我给你筛推荐的时候也能更贴合你的情况哒。
