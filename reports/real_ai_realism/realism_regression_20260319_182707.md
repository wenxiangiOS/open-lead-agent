# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 2
- 失败检查数: 4
- 失败分布: turn=0, field=4, policy=0
- 时延 p95: 2.31s
- 时延 p99: 2.396s
- 模板化 Top1 占比: 50.0%
- Token: 0 (调用 0 次)

## 核心结论

- 拟人化收集通过率: 100.0%
- 字段提取综合通过率: 50.0%
- 字段精确匹配通过率: 100.0%
- 字段完整性通过率: 42.9%

## 拟人化收集质量

- 总检查数: 15
- 失败检查数: 0
- Turn 级失败: 0
- 策略级失败: 0
- 模板化 Top1 占比: 50.0%
- 时延 p95: 2.31s
- 时延 p99: 2.396s

## 字段提取准确性

- 总检查数: 8
- 失败检查数: 4
- 综合通过率: 50.0%
- 精确匹配检查数: 1
- 精确匹配失败数: 0
- 精确匹配通过率: 100.0%
- 完整性检查数: 7
- 完整性失败数: 4
- 完整性通过率: 42.9%
- 高频字段失败 sex_not_inferred_without_self_declare: 1 次
- 高频字段失败 location_truthy: 1 次
- 高频字段失败 education_truthy: 1 次
- 高频字段失败 occupation_truthy: 1 次

## 时延异常 Top20


## 优化建议

- 模板化风险偏高：Top1 模板占比 50.0% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 1 次 (50.0%): `方便留个电话吗后续有合适的人选时联系你`
- 1 次 (50.0%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`

## 字段收集质量

- 总检查数: 8
- 失败检查数: 4
- 通过率: 50.0%
- ending_divorce_confirmed_should_continue (realism_1_bbf9a83b): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='男' (no explicit self sex in user turns)", "location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None"]
- 高频失败 sex_not_inferred_without_self_declare: 1 次
- 高频失败 location_truthy: 1 次
- 高频失败 education_truthy: 1 次
- 高频失败 occupation_truthy: 1 次

## 对话策略规则质量

- 总检查数: 13
- 失败检查数: 0
- 通过率: 100.0%
