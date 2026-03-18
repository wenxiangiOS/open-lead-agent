# 真实 AI 回归报告

- 开始时间: 2026-03-18T16:27:12
- 结束时间: 2026-03-18T16:27:49
- 场景源: `/Users/eric/Desktop/doubao_mcp_server/tests/real_ai/scenarios`
- 总场景: 9
- 通过: 9
- 失败: 0
- 总耗时: 37.331s
- 平均耗时: 4.148s
- 最长耗时: 7.428s
- Token: 0 (调用 0 次)

## 结果概览

- `PASS` `contact_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_wechat`
- `PASS` `contact_phone_after_wechat_rejection_should_not_end` | category=`contact` | tags=`critical, contact_phone, contact_wechat`
- `PASS` `contact_wechat_only_then_phone_refusal` | category=`contact` | tags=`contact_wechat, contact_phone`
- `PASS` `contact_hk_phone_then_wechat_rejected_not_end` | category=`contact` | tags=`critical, contact_hk, contact_wechat`
- `PASS` `contact_phone_with_86_prefix` | category=`contact` | tags=`contact_phone, normalization`
- `PASS` `contact_wechat_mobile_format` | category=`contact` | tags=`contact_wechat, normalization`
- `PASS` `ending_proxy_user` | category=`ending` | tags=`ending_gate`
- `PASS` `ending_normal_complete` | category=`ending` | tags=`critical, normal_complete`
- `PASS` `ending_fake_info_pattern` | category=`ending` | tags=`ending_gate, fake_info`

## 失败详情

无失败场景。