# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 5
- 总耗时(墙钟): 12.77s
- 累计会话耗时: 9.76s
- 失败检查数: 1
- 失败分布: turn=1, field=0, policy=0
- 时延 p95: 2.123s
- 时延 p99: 2.134s
- 模板化 Top1 占比: 40.0%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 95.0%
- 字段提取综合通过率: 100.0%
- 字段精确匹配通过率: 100.0%
- 字段完整性通过率: 100.0%

## 拟人化收集质量

- 总检查数: 20
- 失败检查数: 1
- Turn 级失败: 1
- 策略级失败: 0
- 模板化 Top1 占比: 40.0%
- 时延 p95: 2.123s
- 时延 p99: 2.134s
- 高频 turn 失败 reply_too_fast_nonhuman: 1 次

## 字段提取准确性

- 总检查数: 5
- 失败检查数: 0
- 综合通过率: 100.0%
- 精确匹配检查数: 0
- 精确匹配失败数: 0
- 精确匹配通过率: 100.0%
- 完整性检查数: 5
- 完整性失败数: 0
- 完整性通过率: 100.0%

## 对话自然度指标

- 情绪承接命中率: 0.0% (0/2)
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
- 人设一致性分: 25.0%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 1
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1
- p95 连续提问轮次: 1.0
- 最长连续提问轮次: 1
- 会话中出现>=3连问占比: 0.0% (0/1)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 100.0% (0/0)

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 1.6732s
- rule_check: 1.6251s
- response_build: 1.1974s
- ai_call: 0.2139s
- context_load: 0.0032s
- other: 0.0022s
- profile_save: 0.0003s
- extract_collect: 0.0002s
- profile_load: 0.0001s

## 意图分桶时延

- general: avg=1.673s p95=2.123s max=2.137s n=5
- 秒回率(<1s): 20.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': '好的', 'assistant': '收到，你刚这句我先接住。我们先按你在意的点继续聊，不急着留联系方式。', 'latency_s': 0.23, 'perf': {'profile_load': 0.0, 'context_load': 0.0032, 'rule_check': 0.0011, 'profile_save': 0.0003, 'ai_call': 0.2139, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0112, 'total': 0.2299}}
### field
### policy

## 基线对比

- 检测到退化指标：
- latency_p95: current=2.123 baseline=2.096

## 优化建议

- 规则阶段占比偏高：建议规则短路、热点正则预编译。
- 模板化风险偏高：Top1 模板占比 40.0% > 阈值 18.0%，建议扩写多样化话术。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 2
- P2失败数: 0
- [P1] template_top1_ratio: value=0.4 target=0.22
- [P1] baseline_degradation::latency_p95: value=2.123 target=2.096

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
- 2026-03-21T12:36:50 humanlike=0.95 extraction=1.0 latency_p95=2.123
- 2026-03-21T12:35:56 humanlike=0.9 extraction=1.0 latency_p95=2.096
- 2026-03-21T12:34:47 humanlike=0.9708 extraction=0.8928 latency_p95=2.228
- 2026-03-21T12:33:00 humanlike=0.95 extraction=0.9167 latency_p95=2.107
- 2026-03-21T12:32:17 humanlike=0.9 extraction=0.9167 latency_p95=1.815
- 2026-03-21T12:31:43 humanlike=0.9 extraction=0.9167 latency_p95=1.758
- 2026-03-21T12:30:33 humanlike=0.9 extraction=0.9167 latency_p95=2.043

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 2
- 严重失败项数量: 0
- [major] template_top1_ratio: value=0.4 target=0.22
- [major] baseline_degradation::latency_p95: value=2.123 target=2.096

## 模板化风险 Top10

- 2 次 (40.0%): `这个电话主要是留作后面联系用的我们不会乱打给你你方便的话把号码发我就可以`
- 1 次 (20.0%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (20.0%): `亲你是想说什么呢我刚才看到的消息有点奇怪呢`
- 1 次 (20.0%): `收到你刚这句我先接住我们先按你在意的点继续聊不急着留联系方式`

## 字段收集质量

- 总检查数: 5
- 失败检查数: 0
- 通过率: 100.0%

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 0
- 通过率: 100.0%
