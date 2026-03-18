# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:21:11
- 结束时间: 2026-03-18T16:21:51
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 9
- 通过: 4
- 失败: 5
- 总耗时: 39.309s
- 平均耗时: 4.368s
- 最长耗时: 7.395s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `FAIL` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `FAIL` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_phone_with_86_prefix` | category=`contact` | tags=`contact_phone, normalization`
- `FAIL` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `FAIL` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`

## 失败详情

### contact_phone_after_wechat_rejection_should_not_end

- 分类: `contact`
- 标签: `critical, contact_phone, contact_wechat`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
  - Turn 2 用户: 不留电话
    AI: 

### contact_wechat_only_then_phone_refusal

- 分类: `contact`
- 标签: `contact_wechat, contact_phone`
- 断言通过: 1/2
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生，我微信wx123456
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～
  - Turn 2 用户: 电话先不留
    AI: 

### contact_wechat_mobile_format

- 分类: `contact`
- 标签: `contact_wechat, normalization`
- 断言通过: 0/1
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 微信就是手机号17688654321
    AI: 好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～

### ending_normal_complete

- 分类: `ending`
- 标签: `critical, normal_complete`
- 断言通过: 1/3
- 失败摘要:
  - [profile_field_truthy] turn=- field=wechat profile.wechat 期望为真值，实际 None
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 好的呀～你的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～

### ending_fake_info_pattern

- 分类: `ending`
- 标签: `ending_gate, fake_info`
- 断言通过: 0/2
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
  - [final_response_contains_any] turn=1 final_response 需要包含任一关键词 ['有意思', '认真对待', '真实信息']，实际 ''
- 失败轮次精简回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 
- 对话回放:
  - Turn 1 用户: 我是女生，今年1000岁，身高3米
    AI: 
