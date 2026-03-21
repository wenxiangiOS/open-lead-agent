# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 6
- 总耗时(墙钟): 6.32s
- 累计会话耗时: 3.31s
- 失败检查数: 9
- 失败分布: turn=5, field=4, policy=0
- 时延 p95: 1.024s
- 时延 p99: 1.243s
- 模板化 Top1 占比: 33.3%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 76.2%
- 字段提取综合通过率: 63.6%
- 字段精确匹配通过率: 50.0%
- 字段完整性通过率: 71.4%

## 拟人化收集质量

- 总检查数: 21
- 失败检查数: 5
- Turn 级失败: 5
- 策略级失败: 0
- 模板化 Top1 占比: 33.3%
- 时延 p95: 1.024s
- 时延 p99: 1.243s
- 高频 turn 失败 reply_too_fast_nonhuman: 5 次

## 字段提取准确性

- 总检查数: 11
- 失败检查数: 4
- 综合通过率: 63.6%
- 精确匹配检查数: 4
- 精确匹配失败数: 2
- 精确匹配通过率: 50.0%
- 完整性检查数: 7
- 完整性失败数: 2
- 完整性通过率: 71.4%
- 高频字段失败 location_truthy: 1 次
- 高频字段失败 location_matches_user_stated: 1 次
- 高频字段失败 partner_requirement_when_mentioned: 1 次
- 高频字段失败 partner_requirement_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 100.0% (0/0)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 16.7% (1/6)
- 联系方式突兀转场次数: 0

## 质量护栏指标

- 字段稳定性分数: 0.0% (改写 2/2)
- 拒绝后尊重率: 100.0% (0/0)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 0.0%
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

- 字段冲突修复率: 50.0% (1/2)
- 证据链覆盖率: 100.0% (2/2)
- 失败类型 missed_stated_field: 2 次
- 失败类型 missing_extraction: 1 次
- 失败类型 other: 1 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.2568s
- rule_check: 0.2168s
- ai_call: 0.0395s
- context_load: 0.003s
- other: 0.0025s
- extract_collect: 0.001s
- profile_save: 0.0004s
- response_build: 0.0004s
- profile_load: 0.0002s

## 意图分桶时延

- general: avg=0.257s p95=1.024s max=1.298s n=6
- 秒回率(<1s): 83.3%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '我是男的', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.201, 'perf': {'profile_load': 0.0, 'profile_save': 0.0006, 'context_load': 0.0019, 'rule_check': 0.0007, 'ai_call': 0.1889, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0082, 'total': 0.2006}}
  - {'turn': 3, 'user': '90后', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.01, 'perf': {'profile_load': 0.0, 'context_load': 0.002, 'rule_check': 0.0015, 'profile_save': 0.0004, 'ai_call': 0.0016, 'extract_collect': 0.0029, 'response_build': 0.0002, 'other': 0.0015, 'total': 0.0102}}
  - {'turn': 4, 'user': '深圳', 'assistant': '我先不重复追问电话啦，你也可以先说说你更在意的匹配条件。', 'latency_s': 0.011, 'perf': {'profile_load': 0.0, 'context_load': 0.0039, 'rule_check': 0.0014, 'profile_save': 0.0004, 'ai_call': 0.0025, 'extract_collect': 0.0004, 'response_build': 0.0004, 'other': 0.0015, 'total': 0.0106}}
### field
- location_truthy
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_03edb5ae', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_03edb5ae', 'expected': '深圳', 'actual': None, 'note': ''}
- partner_requirement_when_mentioned
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_03edb5ae', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- partner_requirement_matches_user_stated
  - {'scenario_id': 'field_partner_requirement_height_and_age_preference_should_not_end', 'session_id': 'realism_1_03edb5ae', 'expected': '高挑，不要超过30岁', 'actual': None, 'note': ''}
### policy

## 优化建议

- 规则阶段占比偏高：建议规则短路、热点正则预编译。
- 模板化风险偏高：Top1 模板占比 33.3% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 2 次 (33.3%): `方便留个电话吗后续有合适的人选时联系你`
- 2 次 (33.3%): `我先不重复追问电话啦你也可以先说说你更在意的匹配条件`
- 1 次 (16.7%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (16.7%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`

## 字段收集质量

- 总检查数: 11
- 失败检查数: 4
- 通过率: 63.6%
- field_partner_requirement_height_and_age_preference_should_not_end (realism_1_03edb5ae): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- 高频失败 location_truthy: 1 次
- 高频失败 location_matches_user_stated: 1 次
- 高频失败 partner_requirement_when_mentioned: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 0
- 通过率: 100.0%
