# 真实 AI 回归报告

- 开始时间: 2026-03-17T11:48:23
- 结束时间: 2026-03-17T11:48:24
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 6
- 通过: 0
- 失败: 6
- 总耗时: 1.042s
- 平均耗时: 0.174s
- 最长耗时: 0.441s
- Token: 0 (调用 0 次)

## 结果概览

- `FAIL` `contact_user_asks_wechat_instead_of_phone` | category=`contact` | tags=`critical, contact_phone, contact_wechat, faq_priority`
- `FAIL` `ending_divorce_incomplete_should_end` | category=`ending` | tags=`smoke, critical, divorce`
- `FAIL` `ending_age_under_limit` | category=`ending` | tags=`critical, ending_gate`
- `FAIL` `ending_already_married` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_lgbt_user` | category=`ending` | tags=`ending_gate`

## 失败详情

### contact_user_asks_wechat_instead_of_phone

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat, faq_priority`
- 断言通过: 0/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信']，实际 ''
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 
  - Turn 3 用户: 可以，我微信wx123456
    AI: 

### ending_divorce_incomplete_should_end

- 分类: `ending`
- 标签: `smoke, critical, divorce`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['办妥', '再来', '顺利']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 
- 对话回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 

### ending_age_under_limit

- 分类: `ending`
- 标签: `critical, ending_gate`
- 断言通过: 0/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [profile_field_equals] turn=- field=age_under_limit profile.age_under_limit 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['24岁', '再来', '成熟']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 
- 对话回放:
  - Turn 1 用户: 我22岁，想找对象
    AI: 

### ending_already_married

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['单身', '家庭幸福', '帮不到']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我已经结婚了
    AI: 
- 对话回放:
  - Turn 1 用户: 我已经结婚了
    AI: 

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=proxy_user profile.proxy_user 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['朋友', '家人', '直接来和我聊']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 

### ending_lgbt_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['异性相亲', '不太适合', '专业的平台']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 
- 对话回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 
