# 真实 AI 回归报告

- 开始时间: 2026-03-24T20:27:10
- 结束时间: 2026-03-24T20:27:14
- 场景源: `/tmp/real_ai_all_mxcsp87z`
- 总场景: 2
- 通过: 0
- 失败: 2
- 总耗时: 3.79s
- 平均耗时: 1.895s
- 最长耗时: 3.515s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_low_info_okay_should_ask_wechat_without_overpromising` | category=`contact` | tags=`critical, contact_confirm, contact_wechat, humanlike`
- `FAIL` `humanlike_reception_hesitant_user` | category=`humanlike_reception` | tags=`critical, reception, emotion`

## 失败详情

### contact_low_info_okay_should_ask_wechat_without_overpromising

- 分类: `contact`
- 标签: `critical, contact_confirm, contact_wechat, humanlike`
- 断言通过: 2/3
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信', '方便', '沟通']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 好的
    AI: 
- 对话回放:
  - Turn 1 用户: 我是男的，90后，在深圳，本科，IT，单身
    AI: 
  - Turn 2 用户: 好的
    AI: 

### humanlike_reception_hesitant_user

- 分类: `humanlike_reception`
- 标签: `critical, reception, emotion`
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['没关系', '方便', '保密', '不用']，实际 ''
- 失败轮次精简回放:
  - Turn 2 用户: 这个也要说吗
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，深圳，本科
    AI: 
  - Turn 2 用户: 这个也要说吗
    AI: 
