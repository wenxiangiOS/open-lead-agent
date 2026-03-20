# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 6
- 失败检查数: 6
- 失败分布: turn=2, field=3, policy=1
- 时延 p95: 2.366s
- 时延 p99: 2.504s
- 模板化 Top1 占比: 50.0%
- Token: 0 (调用 0 次)

## 核心结论

- 拟人化收集通过率: 84.2%
- 字段提取综合通过率: 50.0%
- 字段精确匹配通过率: 0.0%
- 字段完整性通过率: 60.0%

## 拟人化收集质量

- 总检查数: 19
- 失败检查数: 3
- Turn 级失败: 2
- 策略级失败: 1
- 模板化 Top1 占比: 50.0%
- 时延 p95: 2.366s
- 时延 p99: 2.504s
- 高频 turn 失败 reply_too_fast_nonhuman: 2 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 6
- 失败检查数: 3
- 综合通过率: 50.0%
- 精确匹配检查数: 1
- 精确匹配失败数: 1
- 精确匹配通过率: 0.0%
- 完整性检查数: 5
- 完整性失败数: 2
- 完整性通过率: 60.0%
- 高频字段失败 sex_not_inferred_without_self_declare: 1 次
- 高频字段失败 partner_requirement_when_mentioned: 1 次
- 高频字段失败 partner_requirement_matches_user_stated: 1 次

## 时延异常 Top20


## 优化建议

- 模板化风险偏高：Top1 模板占比 50.0% > 阈值 18.0%，建议扩写多样化话术。

## 模板化风险 Top10

- 3 次 (50.0%): `方便留个电话吗后续有合适的人选时联系你`
- 1 次 (16.7%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 1 次 (16.7%): `可以理解你会担心我们是按真人审核和牵线流程来做不是随便对接`
- 1 次 (16.7%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`

## 字段收集质量

- 总检查数: 6
- 失败检查数: 3
- 通过率: 50.0%
- random_1 (realism_1_07495537): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='男' (no explicit self sex in user turns)", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "partner_requirement_matches_user_stated: expected='上进 你们靠谱吗 你们靠谱吗', actual=None"]
- 高频失败 sex_not_inferred_without_self_declare: 1 次
- 高频失败 partner_requirement_when_mentioned: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 13
- 失败检查数: 1
- 通过率: 92.3%
- random_1 (realism_1_07495537): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 1 次
