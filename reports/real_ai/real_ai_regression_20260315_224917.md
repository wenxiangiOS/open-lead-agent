# 真实 AI 回归报告

- 开始时间: 2026-03-15T22:47:45
- 结束时间: 2026-03-15T22:49:17
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 6
- 通过: 0
- 失败: 6
- 总耗时: 92.101s
- 平均耗时: 15.35s
- 最长耗时: 44.984s
- Token: 41783 (调用 8 次)

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
- 断言通过: 1/2
- 失败摘要:
  - [response_contains_any] turn=2 turn=2 需要包含任一关键词 ['微信']，实际 '方便还是留一下电话号码哦，后续有合适的人选联系你会更方便~'
- 失败轮次精简回放:
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 方便还是留一下电话号码哦，后续有合适的人选联系你会更方便~
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 好的，你的基本情况我都记下啦~那你对未来的另一半有没有什么具体的要求呀？
  - Turn 2 用户: 电话不方便，留微信可以吗
    AI: 方便还是留一下电话号码哦，后续有合适的人选联系你会更方便~
  - Turn 3 用户: 可以，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～

### ending_divorce_incomplete_should_end

- 分类: `ending`
- 标签: `smoke, critical, divorce`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我离异，手续还在办
    AI: 不好意思哦，您现在手续还在办理的话暂时没法给您安排匹配哦，等后续手续都办妥之后随时再来找我就好~

### ending_age_under_limit

- 分类: `ending`
- 标签: `critical, ending_gate`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
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
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我已经结婚了
    AI: 不好意思呀，我们这边是专门帮单身朋友牵线脱单的，你已经有家庭的话就不符合我们的服务条件啦，祝你家庭和睦，生活顺心哦。

### ending_proxy_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_equals] turn=- field=proxy_user profile.proxy_user 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是帮朋友问的
    AI: 原来是帮朋友咨询呀~ 方便说下你朋友是男生还是女生吗？我好根据情况给你说匹配的相关内容哦

### ending_lgbt_user

- 分类: `ending`
- 标签: `ending_gate`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['异性相亲', '不太适合', '专业的平台']，实际 '好哒，我了解啦～那你今年多大呀？'
- 失败轮次精简回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 好哒，我了解啦～那你今年多大呀？
- 对话回放:
  - Turn 1 用户: 我是les，喜欢女生
    AI: 好哒，我了解啦～那你今年多大呀？
