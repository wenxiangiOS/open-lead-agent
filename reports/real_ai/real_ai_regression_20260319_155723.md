# 真实 AI 回归报告

- 开始时间: 2026-03-19T15:57:20
- 结束时间: 2026-03-19T15:57:23
- 场景源: `/tmp/real_ai_all_3lf8ezhc`
- 总场景: 1
- 通过: 0
- 失败: 1
- 总耗时: 3.458s
- 平均耗时: 3.458s
- 最长耗时: 3.458s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_wechat_contaminated_mixed_token_retry` | category=`contact` | tags=`contact_wechat, retry, normalization, critical`

## 失败详情

### contact_wechat_contaminated_mixed_token_retry

- 分类: `contact`
- 标签: `contact_wechat, retry, normalization, critical`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['微信', '确认', '重新']，实际 '方便留个电话吗？后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 微信wx72378让3
    AI: 方便留个电话吗？后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 深圳那边的资源我们这边一直在做筛选更新，我会优先按同城给你匹配～方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 微信wx72378让3
    AI: 方便留个电话吗？后续有合适的人选时联系你～
