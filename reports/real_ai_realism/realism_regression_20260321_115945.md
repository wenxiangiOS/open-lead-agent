# 真实用户仿真回归报告

- 会话数: 2
- 总轮次: 10
- 总耗时(墙钟): 21.65s
- 累计会话耗时: 18.63s
- 失败检查数: 4
- 失败分布: turn=1, field=1, policy=2
- 时延 p95: 2.181s
- 时延 p99: 2.259s
- 模板化 Top1 占比: 20.0%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 92.5%
- 字段提取综合通过率: 94.1%
- 字段精确匹配通过率: 75.0%
- 字段完整性通过率: 100.0%

## 拟人化收集质量

- 总检查数: 40
- 失败检查数: 3
- Turn 级失败: 1
- 策略级失败: 2
- 模板化 Top1 占比: 20.0%
- 时延 p95: 2.181s
- 时延 p99: 2.259s
- 高频 turn 失败 reply_too_fast_nonhuman: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次
- 高频策略失败 field_interleaving_quality: 1 次

## 字段提取准确性

- 总检查数: 17
- 失败检查数: 1
- 综合通过率: 94.1%
- 精确匹配检查数: 4
- 精确匹配失败数: 1
- 精确匹配通过率: 75.0%
- 完整性检查数: 13
- 完整性失败数: 0
- 完整性通过率: 100.0%
- 高频字段失败 age_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 0.0% (0/2)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 0.0% (0/10)
- 联系方式突兀转场次数: 0

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 100.0% (0/0)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 62.5%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 2
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 2.333
- p95 连续提问轮次: 3.8
- 最长连续提问轮次: 4
- 会话中出现>=3连问占比: 50.0% (1/2)

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

- total: 1.5769s
- response_build: 1.3195s
- rule_check: 0.7977s
- ai_call: 0.3011s
- context_load: 0.0031s
- extract_collect: 0.0023s
- other: 0.0015s
- profile_save: 0.0004s
- profile_load: 0.0002s

## 意图分桶时延

- general: avg=1.577s p95=2.181s max=2.278s n=10
- 秒回率(<1s): 20.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': '好的', 'assistant': '收到，你刚这句我先接住。我们先按你在意的点继续聊，不急着留联系方式。', 'latency_s': 0.318, 'perf': {'profile_load': 0.0, 'context_load': 0.0035, 'rule_check': 0.0011, 'profile_save': 0.0003, 'ai_call': 0.3011, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0111, 'total': 0.3175}}
### field
- age_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_2_aa57081e', 'expected': '90后', 'actual': 30, 'note': ''}
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_repeated_ack_should_not_loop_contact', 'session_id': 'realism_1_a0894628', 'expected': 0, 'actual': 1, 'note': ''}
- field_interleaving_quality
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_2_aa57081e', 'expected': '<=3 core asks streak', 'actual': 4, 'note': ''}

## 基线对比

- 检测到退化指标：
- humanlike_pass_rate: current=0.925 baseline=0.9968
- extraction_pass_rate: current=0.9412 baseline=0.942
- template_top1_ratio: current=0.2 baseline=0.0526

## 优化建议

- 模板化风险偏高：Top1 模板占比 20.0% > 阈值 18.0%，建议扩写多样化话术。

## 总门禁

- global_gate: PASS
- P0失败数: 0
- P1失败数: 2
- P2失败数: 0
- [P1] baseline_degradation::humanlike_pass_rate: value=0.925 target=0.9968
- [P1] baseline_degradation::extraction_pass_rate: value=0.9412 target=0.942

## 规则覆盖矩阵

- ai_dialog_policy::ack_overuse_control => COVERED_PASS
- ai_dialog_policy::no_consecutive_same_field_ask => COVERED_FAIL
- ai_dialog_policy::field_interleaving_quality => COVERED_FAIL
- ai_dialog_policy::memory_reuse_accuracy => COVERED_PASS
- contact_collection::contact_transition_natural => COVERED_PASS
- contact_collection::confirm_word_not_misrouted => COVERED_PASS
- contact_collection::invalid_phone_retry => COVERED_PASS
- contact_collection::invalid_wechat_retry => COVERED_PASS
- message_queue_design::mq_ingest_regression => NOT_COVERED (mq checks disabled)

## 根因分桶

- policy_or_routing: 2
- prompt_or_style: 0
- extraction: 0
- contact_collection: 0
- safety_boundary: 0

## 最近7次趋势

- 持续退化指标: humanlike_pass_rate, extraction_pass_rate
- 2026-03-21T11:59:45 humanlike=0.925 extraction=0.9412 latency_p95=2.181
- 2026-03-21T11:54:23 humanlike=0.9968 extraction=0.942 latency_p95=17.223
- 2026-03-21T10:10:45 humanlike=0.9688 extraction=1.0 latency_p95=14.91
- 2026-03-21T03:37:43 humanlike=0.9772 extraction=0.9547 latency_p95=927.432
- 2026-03-21T02:43:05 humanlike=0.9801 extraction=0.9639 latency_p95=919.51
- 2026-03-20T21:13:42 humanlike=0.9759 extraction=0.9639 latency_p95=18.052
- 2026-03-20T21:11:07 humanlike=0.9688 extraction=1.0 latency_p95=16.596

## MQ补充检查

- covered=False pass=False
- reason: mq checks disabled

## 项目健康门禁

- 门禁是否通过: FAIL
- 失败项数量: 3
- 严重失败项数量: 0
- [major] baseline_degradation::humanlike_pass_rate: value=0.925 target=0.9968
- [major] baseline_degradation::extraction_pass_rate: value=0.9412 target=0.942
- [major] baseline_degradation::template_top1_ratio: value=0.2 target=0.0526

## 模板化风险 Top10

- 2 次 (20.0%): `电话只是留作登记和后面联系不会拿去做别的你要是方便的话发我一个号码就行`
- 1 次 (10.0%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (10.0%): `嗯...亲是不是不小心输错啦我看到的内容有点看不懂呢`
- 1 次 (10.0%): `收到你刚这句我先接住我们先按你在意的点继续聊不急着留联系方式`
- 1 次 (10.0%): `你好呀我在呢你是想先说说自己的情况还是我先问你一两个关键点`
- 1 次 (10.0%): `好哒那想问下你今年多大呀`
- 1 次 (10.0%): `收到啦那你现在主要在哪个城市工作生活呀`
- 1 次 (10.0%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配知道啦那你这边是什么学历呀`
- 1 次 (10.0%): `我记下来啦那你现在是单身状态还是离异呢`

## 字段收集质量

- 总检查数: 17
- 失败检查数: 1
- 通过率: 94.1%
- field_partner_requirement_height_and_age_preference_should_not_end (realism_2_aa57081e): ["age_matches_user_stated: expected='90后', actual=30"]
- 高频失败 age_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 30
- 失败检查数: 2
- 通过率: 93.3%
- abuse_repeated_ack_should_not_loop_contact (realism_1_a0894628): ['no_consecutive_same_field_ask: expected=0, actual=1']
- field_partner_requirement_height_and_age_preference_should_not_end (realism_2_aa57081e): ["field_interleaving_quality: expected='<=3 core asks streak', actual=4"]
- 高频失败 no_consecutive_same_field_ask: 1 次
- 高频失败 field_interleaving_quality: 1 次
