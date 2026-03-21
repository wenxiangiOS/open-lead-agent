# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 19
- 总耗时(墙钟): 158.36s
- 累计会话耗时: 158.35s
- 失败检查数: 6
- 失败分布: turn=2, field=1, policy=3
- 时延 p95: 16.106s
- 时延 p99: 17.664s
- 模板化 Top1 占比: 10.5%
- Token: 64751 (调用 11 次)
- 阈值配置: ack_overuse<=0.25, core_streak<=2

## 核心结论

- 拟人化收集通过率: 85.3%
- 字段提取综合通过率: 91.7%
- 字段精确匹配通过率: 100.0%
- 字段完整性通过率: 85.7%

## 拟人化收集质量

- 总检查数: 34
- 失败检查数: 5
- Turn 级失败: 2
- 策略级失败: 3
- 模板化 Top1 占比: 10.5%
- 时延 p95: 16.106s
- 时延 p99: 17.664s
- 高频 turn 失败 clarification_not_answered: 1 次
- 高频 turn 失败 contact_transition_abrupt: 1 次
- 高频策略失败 core_ask_limit_location: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

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
- FAQ 回主线转场自然率: 0.0% (0/1)
- 复述过度率: 21.1% (4/19)
- 联系方式突兀转场次数: 1
- 意图 fee: 模板多样性=100.0%, Top1=100.0%, 样本=1
- 意图 reliability: 模板多样性=100.0%, Top1=100.0%, 样本=1

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 0.0% (0/1)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (0/0)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 33.3%
- 动作一致性分: 100.0%

## 隔离质量

- 会话数: 1
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1.667
- p95 连续提问轮次: 2.75
- 最长连续提问轮次: 3
- 会话中出现>=3连问占比: 100.0% (1/1)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 57.1% (4/7)
- 失败类型 context_pollution: 1 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- ai_call: 12.3718s
- total: 8.0081s
- response_build: 0.7358s
- rule_check: 0.1736s
- context_load: 0.0133s
- extract_collect: 0.012s
- profile_load: 0.0065s
- profile_save: 0.0063s
- other: 0.0025s

## 意图分桶时延

- general: avg=8.73s p95=16.323s max=18.053s n=17
- fee: avg=1.768s p95=1.768s max=1.768s n=1
- reliability: avg=1.973s p95=1.973s max=1.973s n=1
- 秒回率(<1s): 0.0%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- clarification_not_answered
  - {'turn': 13, 'user': '解释下啊', 'assistant': '我理解你会反复确认，这很正常。你更担心价格、流程，还是隐私安全？', 'latency_s': 2.015, 'perf': {'profile_load': 0.0042, 'context_load': 0.0162, 'rule_check': 0.0066, 'response_build': 1.972, 'other': 0.0157, 'total': 2.0147}}
- contact_transition_abrupt
  - {'turn': 17, 'user': '单身呢', 'assistant': '你这边资料我先整理好了，后续为了方便联系推进，好的了解啦，方便留个电话号码吗？后续有合适的人选时我好及时联系你哦。', 'latency_s': 18.053, 'perf': {'profile_load': 0.01, 'context_load': 0.0132, 'rule_check': 0.0043, 'profile_save': 0.0107, 'ai_call': 18.0089, 'extract_collect': 0.0154, 'response_build': 0.0011, 'other': 0.0, 'total': 18.0535}}
### field
- sex_not_inferred_without_self_declare
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_2339059a', 'expected': 'empty/unknown', 'actual': '男', 'note': 'no explicit self sex in user turns'}
### policy
- core_ask_limit_location
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_2339059a', 'expected': '<=2', 'actual': 4, 'note': ''}
- medium_ask_limit_partner_requirement
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_2339059a', 'expected': '<=1', 'actual': 4, 'note': ''}
- no_consecutive_same_field_ask
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_2339059a', 'expected': 0, 'actual': 1, 'note': ''}

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 2 次 (10.5%): `顺带聊聊你的偏好吧你更看重对方哪几点呀`
- 1 次 (5.3%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (5.3%): `想问下你是男生还是女生呀`
- 1 次 (5.3%): `好哒清楚啦想问下你大概是哪个年龄段的呀知道这个我后续给你匹配的时候也能更精准哦`
- 1 次 (5.3%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们是同城脱单联盟主要做真人牵线匹配不是那种撒网式中介你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们有深圳门店其他城市也有合作服务点匹配到合适阶段会给你发具体定位你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `小哥哥你是想说什么呢我刚才看到的消息有点奇怪呢`
- 1 次 (5.3%): `哈哈谢谢认可呀我们做了三年牵线确实也帮不少朋友找到合适的对象啦对了你平时主要在哪个城市生活工作呀`
- 1 次 (5.3%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配顺带聊聊你的偏好吧你更看重对方哪几点呀`

## 字段收集质量

- 总检查数: 12
- 失败检查数: 1
- 通过率: 91.7%
- golden_long_chain_quality_001 (realism_1_2339059a): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='男' (no explicit self sex in user turns)"]
- 高频失败 sex_not_inferred_without_self_declare: 1 次

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 3
- 通过率: 80.0%
- golden_long_chain_quality_001 (realism_1_2339059a): ["core_ask_limit_location: expected='<=2', actual=4", "medium_ask_limit_partner_requirement: expected='<=1', actual=4", 'no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 core_ask_limit_location: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
- 高频失败 no_consecutive_same_field_ask: 1 次
