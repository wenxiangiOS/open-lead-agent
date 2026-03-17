# 真实 AI 回归报告

- 开始时间: 2026-03-17T12:26:46
- 结束时间: 2026-03-17T12:27:04
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 2
- 通过: 0
- 失败: 2
- 总耗时: 18.107s
- 平均耗时: 9.053s
- 最长耗时: 10.65s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_phone_invalid_should_retry` | category=`contact` | tags=`critical, contact_phone, retry`
- `FAIL` `ending_both_contact_refused` | category=`ending` | tags=`critical, ending_gate, contact_phone, contact_wechat`

## 失败详情

### contact_phone_invalid_should_retry

- 分类: `contact`
- 标签: `critical, contact_phone, retry`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=2 final_response 需要包含任一关键词 ['电话', '确认', '重新']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 我电话12345
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我电话12345
    AI: 

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
    AI: 
  - Turn 2 用户: 不留电话
    AI: 
  - Turn 3 用户: 还是不留电话
    AI: 
  - Turn 4 用户: 微信也不留
    AI: 
  - Turn 5 用户: 还是不留微信
    AI: 
