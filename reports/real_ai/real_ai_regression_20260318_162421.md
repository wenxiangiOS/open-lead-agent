# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:24:00
- 结束时间: 2026-03-18T16:24:21
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 5
- 通过: 4
- 失败: 1
- 总耗时: 20.32s
- 平均耗时: 4.064s
- 最长耗时: 7.448s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `FAIL` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`

## 失败详情

### ending_normal_complete

- 分类: `ending`
- 标签: `critical, normal_complete`
- 断言通过: 2/3
- 失败摘要:
  - [profile_field_equals] turn=- field=conversation_ended profile.conversation_ended 期望 True，实际 False
- 失败轮次精简回放:
- 对话回放:
  - Turn 1 用户: 我是女生，90后，在深圳，本科，运营，单身，想找男生
    AI: 
  - Turn 2 用户: 我的电话是17688654321，微信是wx123456
    AI: 
