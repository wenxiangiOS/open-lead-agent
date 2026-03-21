# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 5
- 总耗时(墙钟): 12.86s
- 累计会话耗时: 9.84s
- 失败检查数: 2
- 失败分布: turn=0, field=1, policy=1
- 时延 p95: 2.107s
- 时延 p99: 2.183s
- 模板化 Top1 占比: 20.0%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 95.0%
- 字段提取综合通过率: 91.7%
- 字段精确匹配通过率: 75.0%
- 字段完整性通过率: 100.0%

## 拟人化收集质量

- 总检查数: 20
- 失败检查数: 1
- Turn 级失败: 0
- 策略级失败: 1
- 模板化 Top1 占比: 20.0%
- 时延 p95: 2.107s
- 时延 p99: 2.183s
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次

## 字段提取准确性

- 总检查数: 12
- 失败检查数: 1
- 综合通过率: 91.7%
- 精确匹配检查数: 4
- 精确匹配失败数: 1
- 精确匹配通过率: 75.0%
- 完整性检查数: 8
- 完整性失败数: 0
- 完整性通过率: 100.0%
- 高频字段失败 age_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 100.0% (0/0)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/5)
- 联系方式突兀转场次数: 0

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 100.0% (0/0)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 75.0%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 1
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 4
- p95 连续提问轮次: 4.0
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 100.0% (1/1)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 60.0% (3/5)
- 失败类型 wrong_value_or_normalization: 1 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 1.6909s
- response_build: 1.3358s
- rule_check: 0.3466s
- context_load: 0.0034s
- extract_collect: 0.003s
- other: 0.0026s
- profile_save: 0.0006s
- profile_load: 0.0001s

## 意图分桶时延

- general: avg=1.691s p95=2.107s max=2.202s n=5
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
### field
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_30ebc79b', 'expected': '90后', 'actual': 30, 'note': ''}
### policy
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_30ebc79b', 'expected': '<=1', 'actual': 2, 'note': ''}

## 基线对比

- 检测到退化指标：
- latency_p95: current=2.107 baseline=1.815

## 优化建议

- 模板化风险偏高：Top1 模板占比 20.0% > 阈值 18.0%，建议扩写多样化话术。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 1
- P2失败数: 0
- [P1] baseline_degradation::latency_p95: value=2.107 target=1.815

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_PASS
- ai_dialog_policy::field_interleaving_quality => COVERED_PASS
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => NOT_COVERED (mq checks disabled)

## 根因分桶

- prompt_or_style: 0
- policy_or_routing: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: latency_p95
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107
- 2026-03-21T12:32:17 humanlike=0.9 extraction=0.9167 latency_p95=1.815
- 2026-03-21T12:31:43 humanlike=0.9 extraction=0.9167 latency_p95=1.758
- 2026-03-21T12:30:33 humanlike=0.9 extraction=0.9167 latency_p95=2.043
- 2026-03-21T12:29:45 humanlike=0.9 extraction=0.9167 latency_p95=1.992
- 2026-03-21T12:25:44 humanlike=0.9968 extraction=0.9275 latency_p95=18.136
- 2026-03-21T12:02:19 humanlike=0.9 extraction=0.9167 latency_p95=1.884

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 1
- 严重失败项数量: 0
- [major] baseline_degradation::latency_p95: value=2.107 target=1.815

## 模板化风险 Top10

- 1 次 (20.0%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (20.0%): `好哒那想问下你今年多大呀`
- 1 次 (20.0%): `收到啦那你现在主要在哪个城市工作生活呀`
- 1 次 (20.0%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 1 次 (20.0%): `这个偏好我先记住啦我先按这个方向给你筛后面有合适的我优先同步你`

## 字段收集质量

- 总检查数: 12
- 失败检查数: 1
- 通过率: 91.7%
- field_partner_requirement_height_and_age_preference_should_not_end (realism_1_30ebc79b): ["age_matches_user_stated: expected='90后', actual=30"]
- 高频失败 age_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 1
- 通过率: 93.3%
- field_partner_requirement_height_and_age_preference_should_not_end (realism_1_30ebc79b): ["medium_ask_limit_partner_requirement: expected='<=1', actual=2"]
- 高频失败 medium_ask_limit_partner_requirement: 1 次
