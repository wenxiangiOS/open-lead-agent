# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:42:49
- 结束时间: 2026-03-18T16:43:37
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 10
- 通过: 8
- 失败: 2
- 总耗时: 48.076s
- 平均耗时: 4.808s
- 最长耗时: 9.591s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_phone_refused_then_wechat_fallback` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_phone_with_spaces_should_collect` | category=`contact` | tags=`contact_phone, normalization`
- `FAIL` `contact_confirm_word_after_phone_prompt` | category=`contact` | tags=`critical, contact_confirm, contact_phone`
- `FAIL` `contact_confirm_word_then_wechat_fallback` | category=`contact` | tags=`critical, contact_confirm`
- `PASS` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `PASS` `contact_user_questions_privacy_before_phone` | category=`contact` | tags=`critical, contact_phone, faq_priority`
- `PASS` `contact_user_says_no_contact_at_all` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_user_explicit_wechat_preference` | category=`contact` | tags=`critical, contact_wechat, contact_preference`
- `PASS` `contact_wechat_invalid_format_retry` | category=`contact` | tags=`contact_wechat, retry, normalization`
- `PASS` `contact_phone_too_long_should_retry` | category=`contact` | tags=`contact_phone, retry`

## 失败详情

### contact_confirm_word_after_phone_prompt

- 分类: `contact`
- 标签: `critical, contact_confirm, contact_phone`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['电话', '号码', '联系']，实际 '啊呀，小姐姐是不是手机不小心碰到啦～发的内容我没太看明白'
- 失败轮次精简回放:
  - Turn 2 用户: 好
    AI: 啊呀，小姐姐是不是手机不小心碰到啦～发的内容我没太看明白
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 好
    AI: 啊呀，小姐姐是不是手机不小心碰到啦～发的内容我没太看明白

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
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 好
    AI: 嗯...小姐姐是不是不小心输错啦～我看到的内容有点看不懂呢
  - Turn 3 用户: 嗯
    AI: 小姐姐你是想说什么呢？我刚才看到的消息有点奇怪呢～
