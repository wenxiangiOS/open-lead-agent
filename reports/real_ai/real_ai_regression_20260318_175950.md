# 真实 AI 回归报告

- 开始时间: 2026-03-18T17:59:45
- 结束时间: 2026-03-18T17:59:50
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 5
- 通过: 4
- 失败: 1
- 总耗时: 5.554s
- 平均耗时: 1.111s
- 最长耗时: 3.366s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_phone_then_wechat_prompt` | category=`contact` | tags=`smoke, critical, contact_phone`
- `PASS` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `FAIL` `faq_priority_mediator` | category=`faq` | tags=`smoke, critical, faq_priority`
- `PASS` `field_occupation_placeholder_guard` | category=`field_collection` | tags=`smoke, critical, extract_guard`
- `PASS` `field_greeting_should_not_fill_profile` | category=`field_collection` | tags=`extract_guard, smoke`

## 失败详情

### faq_priority_mediator

- 分类: `faq`
- 标签: `smoke, critical, faq_priority`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['同城脱单联盟', '牵线']，实际 '后续有合适的人选时联系你～'
- 失败轮次精简回放:
  - Turn 2 用户: 你是中介吗
    AI: 后续有合适的人选时联系你～
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科，运营，单身，想找男生
    AI: 方便留个电话吗？后续有合适的人选时联系你～
  - Turn 2 用户: 你是中介吗
    AI: 后续有合适的人选时联系你～
