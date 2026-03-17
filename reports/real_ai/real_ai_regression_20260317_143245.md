# 真实 AI 回归报告

- 开始时间: 2026-03-17T14:32:36
- 结束时间: 2026-03-17T14:32:45
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 1
- 通过: 0
- 失败: 1
- 总耗时: 9.379s
- 平均耗时: 9.379s
- 最长耗时: 9.379s
- Token: 4890 (调用 1 次)

## 结果概览

- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`

## 失败详情

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['朋友', '家人', '直接来和我聊']，实际 '你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～'
- 失败轮次精简回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 你先帮着了解当然可以，不过如果真要往下匹配，还是让本人直接来跟我说会更准确些哦～
