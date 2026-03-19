# 真实用户仿真回归报告

- 会话数: 114
- 总轮次: 423
- 失败检查数: 349
- 失败分布: turn=10, field=293, policy=46
- 时延 p95: 19.852s
- 时延 p99: 24.704s
- 模板化 Top1 占比: 5.4%
- Token: 1807264 (调用 329 次)

## 时延异常 Top20

- faq_priority_how_match#T1: 45.057s, user=`找对象`
- contact_phone_too_short_should_retry#T3: 45.051s, user=`可以先看照片吗`
- contact_phone_too_short_should_retry#T4: 32.091s, user=`这个为啥要问`
- humanlike_answer_question_then_resume#T3: 30.959s, user=`这个不方便说`

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 23 次 (5.4%): `好的小姐姐那先这样啦有需要随时再来找我哦拜拜👋`
- 20 次 (4.7%): `流程是先线上了解并做匹配筛选双方聊得来再安排线下见面这样更稳妥你要是还有顾虑也可以继续问我`
- 15 次 (3.5%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 15 次 (3.5%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 9 次 (2.1%): `好的呀小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 4 次 (0.9%): `小姐姐这个号码好像位数不对呢能确认下是手机号或微信号吗呀`
- 3 次 (0.7%): `好的呀我先记下了要是你电话方便的话也可以留一个后面联系会更及时些`
- 3 次 (0.7%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 2 次 (0.5%): `电话只是留作登记和后面联系不会拿去做别的你要是方便的话发我一个号码就行`
- 2 次 (0.5%): `方便留个电话吗后续有合适的人选时联系你`

## 字段收集质量

- 总检查数: 805
- 失败检查数: 293
- 通过率: 63.6%
- contact_phone_then_wechat_prompt (realism_1_8d85066d): ["location_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_and_wechat_same_turn (realism_2_c9e6cd7b): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_rejection_should_not_end (realism_3_690c81d0): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_after_wechat_rejection_should_not_end (realism_4_034a1d19): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_refused_then_wechat_fallback (realism_5_50a43d58): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_refused_then_user_provides_wechat (realism_6_87336403): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_ask_phone (realism_7_82aec743): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_phone_refusal (realism_8_57fd6d42): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_invalid_should_retry (realism_9_b69e9d8d): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_invalid_then_valid (realism_10_0e05846f): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]

## 对话策略规则质量

- 总检查数: 1482
- 失败检查数: 46
- 通过率: 96.9%
- contact_phone_after_wechat_rejection_should_not_end (realism_4_034a1d19): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_refused_then_wechat_fallback (realism_5_50a43d58): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_refused_then_user_provides_wechat (realism_6_87336403): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_only_then_ask_phone (realism_7_82aec743): ["core_ask_limit_age: expected='<=2', actual=3", 'no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_only_then_phone_refusal (realism_8_57fd6d42): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_phone_invalid_should_retry (realism_9_b69e9d8d): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_with_spaces_should_collect (realism_11_fc9cb8ad): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat_rejected_not_end (realism_13_8e17586b): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_confirm_word_then_wechat_fallback (realism_15_02d973cb): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_user_asks_wechat_instead_of_phone (realism_16_77c22de6): ['no_consecutive_same_field_ask: expected=0, actual=1']
