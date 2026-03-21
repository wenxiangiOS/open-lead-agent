# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 19
- 总耗时(墙钟): 157.61s
- 累计会话耗时: 157.6s
- 失败检查数: 4
- 失败分布: turn=1, field=1, policy=2
- 时延 p95: 13.87s
- 时延 p99: 17.212s
- 模板化 Top1 占比: 15.8%
- Token: 58320 (调用 10 次)
- 阈值配置: ack_overuse<=0.25, core_streak<=2

## 核心结论

- 拟人化收集通过率: 91.2%
- 字段提取综合通过率: 91.7%
- 字段精确匹配通过率: 100.0%
- 字段完整性通过率: 85.7%

## 拟人化收集质量

- 总检查数: 34
- 失败检查数: 3
- Turn 级失败: 1
- 策略级失败: 2
- 模板化 Top1 占比: 15.8%
- 时延 p95: 13.87s
- 时延 p99: 17.212s
- 高频 turn 失败 faq_not_answered_first: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次
- 高频策略失败 ack_overuse: 1 次

## 字段提取准确性

- 总检查数: 12
- 失败检查数: 1
- 综合通过率: 91.7%
- 精确匹配检查数: 5
- 精确匹配失败数: 0
- 精确匹配通过率: 100.0%
- 完整性检查数: 7
- 完整性失败数: 1
- 完整性通过率: 85.7%
- 高频字段失败 sex_not_inferred_without_self_declare: 1 次

## 对话自然度指标

- 情绪承接命中率: 100.0% (0/0)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 26.3% (5/19)
- 联系方式突兀转场次数: 0
- 意图 fee: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 reliability: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 0.0% (0/1)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 22.2%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 1
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.333
- p95 连续提问轮次: 2.0
- 最长连续提问轮次: 2
- 会话中出现>=3连问占比: 0.0% (0/1)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 71.4% (5/7)
- 失败类型 context_pollution: 1 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 12.1882s
- total: 7.9688s
- response_build: 0.787s
- rule_check: 0.1915s
- context_load: 0.0142s
- extract_collect: 0.0124s
- profile_save: 0.0072s
- profile_load: 0.007s
- other: 0.0031s

## 意图分桶时延

- general: avg=8.647s p95=14.334s max=18.048s n=17
- fee: avg=2.089s p95=2.089s max=2.089s n=1
- reliability: avg=2.324s p95=2.324s max=2.324s n=1
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- faq_not_answered_first
  - {'turn': 12, 'user': '匹配点是啥啊', 'assistant': '顺带聊聊你的偏好吧，你更看重对方哪几点呀？', 'latency_s': 12.235, 'perf': {'profile_load': 0.0078, 'context_load': 0.0132, 'rule_check': 0.0033, 'profile_save': 0.0028, 'ai_call': 12.2, 'extract_collect': 0.0053, 'response_build': 0.0008, 'other': 0.0014, 'total': 12.2346}}
### field
- sex_not_inferred_without_self_declare
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_e4a9a9e6', 'expected': 'empty/unknown', 'actual': '男', 'note': 'no explicit self sex in user turns'}
### policy
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_e4a9a9e6', 'expected': '<=1', 'actual': 4, 'note': ''}
- ack_overuse
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_e4a9a9e6', 'expected': '<=0.25', 'actual': 0.2632, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 3 次 (15.8%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 1 次 (5.3%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (5.3%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 1 次 (5.3%): `好哒对了你今年大概多大呀`
- 1 次 (5.3%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们是同城脱单联盟主要做真人牵线匹配不是那种撒网式中介你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们有深圳门店其他城市也有合作服务点匹配到合适阶段会给你发具体定位你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `小哥哥你是想说什么呢我刚才看到的消息有点奇怪呢`
- 1 次 (5.3%): `哈哈还好啦主要是我们做牵线的时候都会优先匹配条件契合的成功率自然高些对了你平时是在哪个城市工作生活呀我可以先帮你看看当地的合适资源哦`
- 1 次 (5.3%): `好哒我会优先帮你留意深圳本地的合适人选哦对了想问下你是什么学历呀这样筛选的时候能更贴合你的需求`

## 字段收集质量

- 总检查数: 12
- 失败检查数: 1
- 通过率: 91.7%
- golden_long_chain_quality_001 (realism_1_e4a9a9e6): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='男' (no explicit self sex in user turns)"]
- 高频失败 sex_not_inferred_without_self_declare: 1 次

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 2
- 通过率: 86.7%
- golden_long_chain_quality_001 (realism_1_e4a9a9e6): ["medium_ask_limit_partner_requirement: expected='<=1', actual=4", "ack_overuse: expected='<=0.25', actual=0.2632"]
- 高频失败 medium_ask_limit_partner_requirement: 1 次
- 高频失败 ack_overuse: 1 次
