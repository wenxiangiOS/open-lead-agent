# 真实用户仿真回归报告

- 会话数: 2
- 总轮次: 9
- 总耗时(墙钟): 16.06s
- 累计会话耗时: 13.04s
- 失败检查数: 4
- 失败分布: turn=3, field=0, policy=1
- 时延 p95: 2.028s
- 时延 p99: 2.063s
- 模板化 Top1 占比: 44.4%
- Token: 0 (调用 0 次)

## 核心结论

- 拟人化收集通过率: 88.6%
- 字段提取综合通过率: 100.0%
- 字段精确匹配通过率: 100.0%
- 字段完整性通过率: 100.0%

## 拟人化收集质量

- 总检查数: 35
- 失败检查数: 4
- Turn 级失败: 3
- 策略级失败: 1
- 模板化 Top1 占比: 44.4%
- 时延 p95: 2.028s
- 时延 p99: 2.063s
- 高频 turn 失败 reply_too_fast_nonhuman: 3 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 8
- 失败检查数: 0
- 综合通过率: 100.0%
- 精确匹配检查数: 0
- 精确匹配失败数: 0
- 精确匹配通过率: 100.0%
- 完整性检查数: 8
- 完整性失败数: 0
- 完整性通过率: 100.0%

## 对话自然度指标

- 情绪承接命中率: 50.0% (2/4)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 意图 reliability: 模板多样性=50.0%, Top1=100.0%, 样本=2

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 100.0% (0/0)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 28.6%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 2
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.25
- p95 连续提问轮次: 1.85
- 最长连续提问轮次: 2
- 会话中出现>=3连问占比: 0.0% (0/2)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 100.0% (0/0)

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 1.1052s
- response_build: 0.8523s
- rule_check: 0.6206s
- ai_call: 0.0707s
- context_load: 0.004s
- other: 0.0017s
- profile_save: 0.0005s
- profile_load: 0.0003s
- extract_collect: 0.0003s

## 意图分桶时延

- general: avg=0.844s p95=1.945s max=1.957s n=7
- reliability: avg=2.018s p95=2.067s max=2.072s n=2
- 秒回率(<1s): 44.4%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 3, 'user': '这个为啥要问', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.015, 'perf': {'profile_load': 0.0, 'context_load': 0.004, 'rule_check': 0.0012, 'profile_save': 0.0004, 'ai_call': 0.0061, 'extract_collect': 0.0002, 'response_build': 0.0004, 'other': 0.0023, 'total': 0.0146}}
  - {'turn': 4, 'user': '你看得懂吗', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.016, 'perf': {'profile_load': 0.0001, 'context_load': 0.0051, 'rule_check': 0.0014, 'profile_save': 0.0007, 'ai_call': 0.0053, 'extract_collect': 0.0003, 'response_build': 0.0006, 'other': 0.0024, 'total': 0.016}}
  - {'turn': 4, 'user': '问得挺细啊', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.017, 'perf': {'profile_load': 0.0001, 'context_load': 0.0031, 'rule_check': 0.0008, 'profile_save': 0.0005, 'ai_call': 0.0089, 'extract_collect': 0.0005, 'response_build': 0.0005, 'other': 0.0028, 'total': 0.0172}}
### field
### policy
- no_consecutive_same_field_ask
  - {'scenario_id': 'abuse_nonsense_gibberish_multi_turn', 'session_id': 'realism_1_af81fdd3', 'expected': 0, 'actual': 1, 'note': ''}

## 优化建议

- 模板化风险偏高：Top1 模板占比 44.4% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 4 次 (44.4%): `方便留个电话吗后续有合适的人选时联系你`
- 2 次 (22.2%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 1 次 (11.1%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (11.1%): `嗯...亲是不是不小心输错啦我看到的内容有点看不懂呢`
- 1 次 (11.1%): `电话这边主要是方便后面登记和联系你不会私下打扰你的要是你方便的话把号码发我就行`

## 字段收集质量

- 总检查数: 8
- 失败检查数: 0
- 通过率: 100.0%

## 对话策略规则质量

- 总检查数: 26
- 失败检查数: 1
- 通过率: 96.2%
- abuse_nonsense_gibberish_multi_turn (realism_1_af81fdd3): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 1 次
