# 真实用户仿真回归报告

- 会话数: 6
- 总轮次: 17
- 总耗时(墙钟): 14.42s
- 累计会话耗时: 11.4s
- 失败检查数: 20
- 失败分布: turn=8, field=11, policy=1
- 时延 p95: 1.748s
- 时延 p99: 2.014s
- 模板化 Top1 占比: 17.6%
- Token: 0 (调用 0 次)
- 阈值配置: ack_overuse<=0.35, core_streak<=3

## 核心结论

- 拟人化收集通过率: 91.6%
- 字段提取综合通过率: 87.4%
- 字段精确匹配通过率: 90.6%
- 字段完整性通过率: 85.5%

## 拟人化收集质量

- 总检查数: 107
- 失败检查数: 9
- Turn 级失败: 8
- 策略级失败: 1
- 模板化 Top1 占比: 17.6%
- 时延 p95: 1.748s
- 时延 p99: 2.014s
- 高频 turn 失败 reply_too_fast_nonhuman: 8 次
- 高频策略失败 ack_overuse: 1 次

## 字段提取准确性

- 总检查数: 87
- 失败检查数: 11
- 综合通过率: 87.4%
- 精确匹配检查数: 32
- 精确匹配失败数: 3
- 精确匹配通过率: 90.6%
- 完整性检查数: 55
- 完整性失败数: 8
- 完整性通过率: 85.5%
- 高频字段失败 partner_requirement_when_mentioned: 5 次
- 高频字段失败 location_truthy: 2 次
- 高频字段失败 location_matches_user_stated: 2 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 unexpected_conversation_end: 1 次

## 对话自然度指标

- 情绪承接命中率: 0.0% (0/1)
- FAQ 非复读率: 100.0% (0/0)
- FAQ 回主线转场自然率: 100.0% (0/0)
- 复述过度率: 5.9% (1/17)
- 联系方式突兀转场次数: 0

## 质量护栏指标

- 字段稳定性分数: 100.0% (改写 0/0)
- 拒绝后尊重率: 0.0% (0/4)
- 记忆回用准确率: 100.0% (0/0)
- 收尾自然度: 100.0% (1/1)
- 异常恢复率: 100.0% (0/0)
- 人设一致性分: 18.2%
- 动作一致性分: 0.0%

## 隔离质量

- 会话数: 6
- 账号串线数: 0
- 隔离通过率: 100.0%

## 提问压迫感

- 平均连续提问轮次: 1
- p95 连续提问轮次: 1.0
- 最长连续提问轮次: 1
- 会话中出现>=3连问占比: 0.0% (0/6)

## 提取诊断

- 字段冲突修复率: 100.0% (0/0)
- 证据链覆盖率: 80.0% (24/30)
- 失败类型 other: 6 次
- 失败类型 missed_stated_field: 3 次
- 失败类型 missing_extraction: 2 次

## 联系方式质量专项

- 联系方式成功率: 20.0% (1/5)
- 无效电话未重试: 0 次
- 无效微信未重试: 0 次

## 时延异常 Top20


## 分阶段耗时均值

- total: 0.3221s
- response_build: 0.2997s
- rule_check: 0.2211s
- ai_call: 0.0132s
- context_load: 0.0036s
- other: 0.0025s
- extract_collect: 0.0023s
- profile_save: 0.0008s
- profile_load: 0.0003s

## 意图分桶时延

- general: avg=0.322s p95=1.748s max=2.08s n=17
- 秒回率(<1s): 82.3%
- FAQ秒回率(<1s): 0.0%
- 超慢回复率(>20s): 0.0%

## 失败样本（自动抽样）

### turn
- reply_too_fast_nonhuman
  - {'turn': 2, 'user': '你别装了', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.012, 'perf': {'profile_load': 0.0, 'context_load': 0.0035, 'rule_check': 0.0009, 'profile_save': 0.0004, 'ai_call': 0.0045, 'extract_collect': 0.0003, 'response_build': 0.0004, 'other': 0.0022, 'total': 0.0121}}
  - {'turn': 3, 'user': '你回答啊', 'assistant': '我先不重复追问电话啦，你也可以先说说你更在意的匹配条件。', 'latency_s': 0.013, 'perf': {'profile_load': 0.0, 'context_load': 0.0068, 'rule_check': 0.0011, 'profile_save': 0.0003, 'ai_call': 0.0029, 'extract_collect': 0.0002, 'response_build': 0.0002, 'other': 0.0015, 'total': 0.013}}
  - {'turn': 4, 'user': '你是不是在骗我', 'assistant': '方便留个电话吗？后续有合适的人选时联系你～', 'latency_s': 0.017, 'perf': {'profile_load': 0.0, 'context_load': 0.0045, 'rule_check': 0.0008, 'profile_save': 0.0007, 'ai_call': 0.0037, 'extract_collect': 0.0042, 'response_build': 0.0003, 'other': 0.0026, 'total': 0.0168}}
### field
- partner_requirement_when_mentioned
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_2_8a2de460', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_confirm_word_then_wechat_fallback', 'session_id': 'realism_3_701f1320', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_4_89a354dd', 'expected': 'non-empty', 'actual': None, 'note': 'user mentioned preference in turns'}
- location_truthy
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_4_89a354dd', 'expected': 'non-empty', 'actual': None, 'note': ''}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_6_c7db8ed7', 'expected': 'non-empty', 'actual': None, 'note': ''}
- location_matches_user_stated
  - {'scenario_id': 'contact_user_explicit_wechat_preference', 'session_id': 'realism_4_89a354dd', 'expected': '深圳', 'actual': None, 'note': ''}
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_6_c7db8ed7', 'expected': '深圳', 'actual': None, 'note': ''}
- wechat_matches_user_stated
  - {'scenario_id': 'contact_wechat_contaminated_mixed_token_retry', 'session_id': 'realism_5_6cac1808', 'expected': 'wx72378', 'actual': None, 'note': ''}
- unexpected_conversation_end
  - {'scenario_id': 'ending_both_contact_refused', 'session_id': 'realism_6_c7db8ed7', 'expected': False, 'actual': True, 'note': 'profile contains serviceable info and should normally continue collection'}
### policy
- ack_overuse
  - {'scenario_id': 'contact_phone_then_wechat_prompt', 'session_id': 'realism_2_8a2de460', 'expected': '<=0.35', 'actual': 1.0, 'note': ''}

## 优化建议

- 规则阶段占比偏高：建议规则短路、热点正则预编译。

## 模板化风险 Top10

- 3 次 (17.6%): `我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 2 次 (11.8%): `方便留个电话吗后续有合适的人选时联系你`
- 2 次 (11.8%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配你这边资料我先整理好了后续方便联系推进我先不急着推进联系方式先按你刚说的继续聊会更自然`
- 2 次 (11.8%): `小姐姐这个微信号好像格式不太对呢是字母开头的#-#位字符吗呀`
- 1 次 (5.9%): `我先不重复追问电话啦你也可以先说说你更在意的匹配条件`
- 1 次 (5.9%): `深圳那边的资源我们这边一直在做筛选更新我会优先按同城给你匹配小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 1 次 (5.9%): `电话只是留作登记和后面联系不会拿去做别的你要是方便的话发我一个号码就行`
- 1 次 (5.9%): `电话这边主要是方便后面登记和联系你不会私下打扰你的要是你方便的话把号码发我就行`
- 1 次 (5.9%): `小姐姐这个微信号里好像混了多余字符麻烦你重新确认一下微信号哈`
- 1 次 (5.9%): `这个电话只是留作登记和后面联系用的不会私下打扰你你方便的话发我一个号码就行`

## 字段收集质量

- 总检查数: 87
- 失败检查数: 11
- 通过率: 87.4%
- contact_phone_then_wechat_prompt (realism_2_8a2de460): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_confirm_word_then_wechat_fallback (realism_3_701f1320): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_user_explicit_wechat_preference (realism_4_89a354dd): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- contact_wechat_contaminated_mixed_token_retry (realism_5_6cac1808): ["partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)", "wechat_matches_user_stated: expected='wx72378', actual=None"]
- ending_both_contact_refused (realism_6_c7db8ed7): ["location_truthy: expected='non-empty', actual=None", "location_matches_user_stated: expected='深圳', actual=None", "partner_requirement_when_mentioned: expected='non-empty', actual=None (user mentioned preference in turns)"]
- 高频失败 partner_requirement_when_mentioned: 5 次
- 高频失败 location_truthy: 2 次
- 高频失败 location_matches_user_stated: 2 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 unexpected_conversation_end: 1 次

## 对话策略规则质量

- 总检查数: 90
- 失败检查数: 1
- 通过率: 98.9%
- contact_phone_then_wechat_prompt (realism_2_8a2de460): ["ack_overuse: expected='<=0.35', actual=1.0"]
- 高频失败 ack_overuse: 1 次
