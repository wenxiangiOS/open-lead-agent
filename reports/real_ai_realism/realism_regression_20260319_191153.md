# 真实用户仿真回归报告

- 会话数: 1
- 总轮次: 30
- 失败检查数: 10
- 失败分布: turn=0, field=4, policy=6
- 时延 p95: 23.044s
- 时延 p99: 27.689s
- 模板化 Top1 占比: 6.7%
- Token: 124985 (调用 21 次)

## 核心结论

- 拟人化收集通过率: 86.1%
- 字段提取综合通过率: 60.0%
- 字段精确匹配通过率: 50.0%
- 字段完整性通过率: 62.5%

## 拟人化收集质量

- 总检查数: 43
- 失败检查数: 6
- Turn 级失败: 0
- 策略级失败: 6
- 模板化 Top1 占比: 6.7%
- 时延 p95: 23.044s
- 时延 p99: 27.689s
- 高频策略失败 core_ask_limit_age: 1 次
- 高频策略失败 core_ask_limit_education: 1 次
- 高频策略失败 core_ask_limit_location: 1 次
- 高频策略失败 quasi_core_ask_limit_marital_status: 1 次
- 高频策略失败 medium_ask_limit_partner_requirement: 1 次
- 高频策略失败 no_consecutive_same_field_ask: 1 次

## 字段提取准确性

- 总检查数: 10
- 失败检查数: 4
- 综合通过率: 60.0%
- 精确匹配检查数: 2
- 精确匹配失败数: 1
- 精确匹配通过率: 50.0%
- 完整性检查数: 8
- 完整性失败数: 3
- 完整性通过率: 62.5%
- 高频字段失败 sex_not_inferred_without_self_declare: 1 次
- 高频字段失败 education_truthy: 1 次
- 高频字段失败 occupation_truthy: 1 次
- 高频字段失败 partner_requirement_matches_user_stated: 1 次

## 时延异常 Top20


## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 2 次 (6.7%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 2 次 (6.7%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`
- 1 次 (3.3%): `喜欢上进的另一半确实很重要呀对啦你今年大概多大呀我也好帮你匹配年龄合适的人选`
- 1 次 (3.3%): `可以理解你会担心我们是按真人审核和牵线流程来做不是随便对接`
- 1 次 (3.3%): `嗯嗯我记住你希望另一半是上进的啦对了你平时主要在哪个城市工作生活呀我们可以优先筛同城的资源匹配效率更高哦`
- 1 次 (3.3%): `哈哈是这样的知道你所在的城市我可以优先给你筛同城的合适资源后续你们接触起来也更方便对啦顺便问问你是什么学历呀我也好帮你找更契合的人选`
- 1 次 (3.3%): `流程是先线上了解并做匹配筛选双方聊得来再后续有合适人选我会第一时间联系你这样更稳妥你要是还有顾虑也可以继续问我`
- 1 次 (3.3%): `哈哈也是为了帮你筛到更合拍的对象嘛信息越贴合匹配到的人也更合适呀对了你大概是哪个年龄段的呀`
- 1 次 (3.3%): `哈哈不好意思呀要是你不想说年龄也没关系的我主要是想了解下你平时在哪个城市工作生活呀毕竟咱们是做同城脱单匹配的知道你所在的城市才能优先给你推同个地方的合适人选也不`
- 1 次 (3.3%): `没关系呀不方便说就不说哈对了想问下你是什么学历呀知道这个的话我后面给你推合适的人选时也能筛得更贴合你的情况哦`

## 字段收集质量

- 总检查数: 10
- 失败检查数: 4
- 通过率: 60.0%
- random_1 (realism_1_40cbde24): ["sex_not_inferred_without_self_declare: expected='empty/unknown', actual='男' (no explicit self sex in user turns)", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- 高频失败 sex_not_inferred_without_self_declare: 1 次
- 高频失败 education_truthy: 1 次
- 高频失败 occupation_truthy: 1 次
- 高频失败 partner_requirement_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 13
- 失败检查数: 6
- 通过率: 53.8%
- random_1 (realism_1_40cbde24): ["core_ask_limit_age: expected='<=2', actual=3", "core_ask_limit_education: expected='<=2', actual=4", "core_ask_limit_location: expected='<=2', actual=4"]
- 高频失败 core_ask_limit_age: 1 次
- 高频失败 core_ask_limit_education: 1 次
- 高频失败 core_ask_limit_location: 1 次
- 高频失败 quasi_core_ask_limit_marital_status: 1 次
- 高频失败 medium_ask_limit_partner_requirement: 1 次
- 高频失败 no_consecutive_same_field_ask: 1 次
