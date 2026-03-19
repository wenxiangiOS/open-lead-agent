# 真实 AI 回归报告

- 开始时间: 2026-03-19T15:50:29
- 结束时间: 2026-03-19T15:50:35
- 场景源: `/tmp/real_ai_all__3ywyiar`
- 总场景: 2
- 通过: 1
- 失败: 1
- 总耗时: 5.475s
- 平均耗时: 2.737s
- 最长耗时: 3.417s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_wechat_contaminated_mixed_token_retry` | category=`contact` | tags=`contact_wechat, retry, normalization, critical`
- `PASS` `faq_priority_contact_why_phone` | category=`faq` | tags=`critical, faq_priority, contact_why`

## 失败详情

### contact_wechat_contaminated_mixed_token_retry

- 分类: `contact`
- 标签: `contact_wechat, retry, normalization, critical`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_falsey] turn=- field=wechat profile.wechat 期望为空/假值，实际 'wx72378'
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['微信', '确认', '重新']，实际 '好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～'
- 失败轮次精简回放:
  - Turn 2 用户: 微信wx72378让3
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 深圳那边的资源我们这边一直在做筛选更新，我会优先按同城给你匹配～方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 微信wx72378让3
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
