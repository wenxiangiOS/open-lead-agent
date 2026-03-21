# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 19
- 总耗时(墙钟): 25.76s
- 累计会话耗时: 22.75s
- 失败检查数: 17
- 失败分布: turn=14, field=3, policy=0
- 时延 p95: 2.306s
- 时延 p99: 2.356s
- 模板化 Top1 占比: 21.1%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.25, core_streak<=2

## 核心结论

- 拟人化收集通过率: 58.8%
- 字段提取综合通过率: 75.0%
- 字段精确匹配通过率: 60.0%
- 字段完整性通过率: 85.7%

## 拟人化收集质量

- 总检查数: 34
- 失败检查数: 14
- Turn 级失败: 14
- 策略级失败: 0
- 模板化 Top1 占比: 21.1%
- 时延 p95: 2.306s
- 时延 p99: 2.356s
- 高频 turn 失败 reply_too_fast_nonhuman: 11 次
- 高频 turn 失败 faq_not_answered_first: 1 次
- 高频 turn 失败 faq_reply_too_fast: 1 次
- 高频 turn 失败 clarification_not_answered: 1 次

## 字段提取准确性

- 总检查数: 12
- 失败检查数: 3
- 综合通过率: 75.0%
- 精确匹配检查数: 5
- 精确匹配失败数: 2
- 精确匹配通过率: 60.0%
- 完整性检查数: 7
- 完整性失败数: 1
- 完整性通过率: 85.7%
- 高频字段失败 location_truthy: 1 次
- 高频字段失败 location_matches_user_stated: 1 次
- 高频字段失败 phone_matches_user_stated: 1 次

## 对话自然度指标

- 情绪承接命中率: 100.0% (0/0)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 0.0% (0/1)
- 复述过度率: 5.3% (1/19)
- 联系方式突兀转场次数: 0
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

- 平均连续提问轮次: 1
- p95 连续提问轮次: 1.0
- 最长连续提问轮次: 1
- 会话中出现>=3连问占比: 0.0% (0/1)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 66.7% (2/3)
- 失败类型 missed_stated_field: 2 次
- 失败类型 missing_extraction: 1 次

## 联系方式质量专项

- 联系方式成功率: 100.0% (0/0)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.8714s
- response_build: 0.7486s
- rule_check: 0.1919s
- ai_call: 0.0192s
- context_load: 0.0051s
- other: 0.0023s
- extract_collect: 0.0019s
- profile_save: 0.0006s
- profile_load: 0.0001s

## 意图分桶时延

- general: avg=0.715s p95=2.051s max=2.369s n=17
- fee: avg=2.106s p95=2.106s max=2.106s n=1
- reliability: avg=2.299s p95=2.299s max=2.299s n=1
- 秒回率(<1s): 57.9%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '我叫青青', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.168, 'perf': {'profile_load': 0.0, 'context_load': 0.0025, 'rule_check': 0.0007, 'profile_save': 0.0002, 'ai_call': 0.1578, 'extract_collect': 0.0002, 'response_build': 0.0001, 'other': 0.0061, 'total': 0.1678}}
  - {'turn': 3, 'user': '男的', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.008, 'perf': {'profile_load': 0.0, 'context_load': 0.0027, 'rule_check': 0.0006, 'profile_save': 0.0003, 'ai_call': 0.0025, 'extract_collect': 0.0003, 'response_build': 0.0002, 'other': 0.0013, 'total': 0.008}}
  - {'turn': 8, 'user': '那你们还是挺强的', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.022, 'perf': {'profile_load': 0.0, 'context_load': 0.0022, 'rule_check': 0.0004, 'profile_save': 0.0004, 'ai_call': 0.0162, 'extract_collect': 0.0004, 'response_build': 0.0002, 'other': 0.0022, 'total': 0.022}}
- faq_not_answered_first
  - {'turn': 12, 'user': '匹配点是啥啊', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.016, 'perf': {'profile_load': 0.0001, 'context_load': 0.006, 'rule_check': 0.0014, 'profile_save': 0.0005, 'ai_call': 0.0041, 'extract_collect': 0.0007, 'response_build': 0.0004, 'other': 0.0026, 'total': 0.0157}}
- faq_reply_too_fast
  - {'turn': 12, 'user': '匹配点是啥啊', 'assistant': '我先不急着推进联系方式，先按你刚说的继续聊会更自然。', 'latency_s': 0.016, 'perf': {'profile_load': 0.0001, 'context_load': 0.006, 'rule_check': 0.0014, 'profile_save': 0.0005, 'ai_call': 0.0041, 'extract_collect': 0.0007, 'response_build': 0.0004, 'other': 0.0026, 'total': 0.0157}}
- clarification_not_answered
  - {'turn': 13, 'user': '解释下啊', 'assistant': '我理解你会反复确认，这很正常。你更担心价格、流程，还是隐私安全？', 'latency_s': 1.917, 'perf': {'profile_load': 0.0, 'context_load': 0.0037, 'rule_check': 0.0007, 'response_build': 1.9105, 'other': 0.0021, 'total': 1.9171}}
### field
- location_truthy
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_38c303c8', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_38c303c8', 'expected': '深圳', 'actual': None, 'note': ''}
- phone_matches_user_stated
  - {'scenario_id': 'golden_long_chain_quality_001', 'session_id': 'realism_1_38c303c8', 'expected': '17688987654', 'actual': None, 'note': ''}
### policy

## 优化建议

- 模板化风险偏高：Top1 模板占比 21.1% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 4 次 (21.1%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 4 次 (21.1%): `方便留个电话吗后续有合适的人选时联系你`
- 2 次 (10.5%): `我先不重复追问电话啦你也可以先说说你更在意的匹配条件`
- 1 次 (5.3%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 1 次 (5.3%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们是同城脱单联盟主要做真人牵线匹配不是那种撒网式中介你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `我们有深圳门店其他城市也有合作服务点匹配到合适阶段会给你发具体定位你要是还有顾虑也可以继续问我`
- 1 次 (5.3%): `嗯...亲是不是不小心输错啦我看到的内容有点看不懂呢`
- 1 次 (5.3%): `我换个直白说法：我说的“匹配点”就是你在意的几个条件比如年龄范围城市工作节奏是否单身和相处感觉`
- 1 次 (5.3%): `你这个问题很好理解：所谓“匹配点”就是你觉得重要的标准比如城市年龄工作状态和相处舒适度`

## 字段收集质量

- 总检查数: 12
- 失败检查数: 3
- 通过率: 75.0%
- golden_long_chain_quality_001 (realism_1_38c303c8): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "phone_matches_user_stated: expected='17688987654', actual=None"]
- 高频失败 location_truthy: 1 次
- 高频失败 location_matches_user_stated: 1 次
- 高频失败 phone_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 15
- 失败检查数: 0
- 通过率: 100.0%
