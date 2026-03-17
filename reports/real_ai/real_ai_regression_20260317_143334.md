# 真实 AI 回归报告

- 开始时间: 2026-03-17T14:33:23
- 结束时间: 2026-03-17T14:33:34
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 1
- 通过: 0
- 失败: 1
- 总耗时: 10.885s
- 平均耗时: 10.885s
- 最长耗时: 10.885s
- Token: 4832 (调用 1 次)

## 结果概览

- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`

## 失败详情

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
