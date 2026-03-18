# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:36:53
- 结束时间: 2026-03-18T16:39:36
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 35
- 通过: 25
- 失败: 10
- 总耗时: 163.035s
- 平均耗时: 4.658s
- 最长耗时: 8.518s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `contact_phone_and_wechat_same_turn` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_refused_then_user_provides_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_ask_phone` | category=`contact` | tags=`critical, contact_wechat, contact_phone`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `PASS` `contact_phone_invalid_then_valid` | category=`contact` | tags=`critical, contact_phone, retry`
- `FAIL` `contact_phone_with_spaces_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_hk_phone_then_wechat` | category=`contact` | tags=`critical, contact_hk`
- `PASS` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `FAIL` `contact_confirm_word_after_phone_prompt` | category=`contact` | tags=`critical, contact_confirm, contact_phone`
- `FAIL` `contact_confirm_word_then_wechat_fallback` | category=`contact` | tags=`critical, contact_confirm`
- `FAIL` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `FAIL` `contact_user_questions_privacy_before_phone` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_phone_after_privacy_question` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_provides_wechat_after_phone_prompt` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_user_says_no_contact_at_all` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_hk_user_provides_wechat_only` | category=`contact` | tags=`critical, contact_hk, contact_wechat, contact_phone`
- `PASS` `contact_phone_with_text_prefix_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `FAIL` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `PASS` `contact_hk_user_reject_wechat` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_non_hk_wechat_first_then_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_says_phone_inconvenient_then_wechat` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_invalid_format_retry` | category=`contact` | tags=`contact_wechat, retry, normalization`
- `PASS` `contact_wechat_invalid_then_valid` | category=`contact` | tags=`contact_wechat, retry`
- `PASS` `contact_phone_with_country_code` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_phone_with_86_prefix` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_phone_with_dashes` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_wechat_with_special_chars` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `contact_phone_too_short_should_retry` | category=`contact` | tags=`contact_phone, retry`
- `FAIL` `contact_phone_too_long_should_retry` | category=`contact` | tags=`contact_phone, retry`

## 失败详情

### contact_phone_refused_then_wechat_fallback

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['微信']，实际 ''
- 失败轮次精简回放:
  - Turn 3 用户: 还是不想留电话
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 不留电话
    AI: 
  - Turn 3 用户: 还是不想留电话
    AI: 

### contact_phone_with_spaces_should_collect

- 分类: `contact`
- 标签: `contact_phone, normalization`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=phone profile.phone 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我电话 176 8865 4321
    AI: 

### contact_confirm_word_after_phone_prompt

- 分类: `contact`
- 标签: `critical, contact_confirm, contact_phone`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['电话', '号码', '联系']，实际 '嗯...小姐姐是不是不小心输错啦～我看到的内容有点看不懂呢'
- 失败轮次精简回放:
  - Turn 2 用户: 好
    AI: 嗯...小姐姐是不是不小心输错啦～我看到的内容有点看不懂呢
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 好
    AI: 嗯...小姐姐是不是不小心输错啦～我看到的内容有点看不懂呢

### contact_confirm_word_then_wechat_fallback

- 分类: `contact`
- 标签: `critical, contact_confirm`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['微信', '沟通', '联系']，实际 '小姐姐你是想说什么呢？我刚才看到的消息有点奇怪呢～'
- 失败轮次精简回放:
  - Turn 3 用户: 嗯
    AI: 小姐姐你是想说什么呢？我刚才看到的消息有点奇怪呢～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 好
    AI: 啊呀，小姐姐是不是手机不小心碰到啦～发的内容我没太看明白
  - Turn 3 用户: 嗯
    AI: 小姐姐你是想说什么呢？我刚才看到的消息有点奇怪呢～

### contact_user_asks_wechat_instead_of_phone

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 
  - Turn 3 用户: 可以，我微信wx123456
    AI: 好的呀，我先记下啦，后面有合适的人选会尽快联系你～

### contact_user_questions_privacy_before_phone

- 分类: `contact`
- 标签: `critical, contact_phone, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['联系', '登记', '打扰', '放心']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 为什么一定要电话
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 为什么一定要电话
    AI: 

### contact_user_says_no_contact_at_all

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['电话', '微信', '联系']，实际 ''
  - [response_contains_any] turn=3 turn=3 需要包含任一关键词 ['微信', '电话', '联系']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 联系方式都不留
    AI: 
  - Turn 3 用户: 还是都不留
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 联系方式都不留
    AI: 
  - Turn 3 用户: 还是都不留
    AI: 

### contact_user_explicit_wechat_preference

- 分类: `contact`
- 标签: `critical, contact_wechat, contact_preference`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信', '可以', '发我']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 用微信联系吧
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 用微信联系吧
    AI: 

### contact_wechat_invalid_format_retry

- 分类: `contact`
- 标签: `contact_wechat, retry, normalization`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['微信', '确认', '重新']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 我微信abc
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我微信abc
    AI: 

### contact_phone_too_long_should_retry

- 分类: `contact`
- 标签: `contact_phone, retry`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_falsey] turn=- field=phone profile.phone 期望为空/假值，实际 '17688654321'
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我电话17688654321123456
    AI: 好的呀～小姐姐的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～
