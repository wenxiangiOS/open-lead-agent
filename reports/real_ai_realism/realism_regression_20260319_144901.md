# 真实用户仿真回归报告

- 会话数: 114
- 总轮次: 423
- 失败检查数: 11
- 时延 p95: 18.443s
- 时延 p99: 28.577s
- 模板化 Top1 占比: 5.4%
- Token: 1803081 (调用 328 次)

## 时延异常 Top20

- contact_confirm_word_after_phone_prompt#T4: 1025.488s, user=`本科`
- contact_user_says_no_contact_at_all#T4: 1011.79s, user=`可以先看照片吗`
- contact_confirm_word_then_wechat_fallback#T3: 970.044s, user=`在深圳`
- contact_phone_with_text_prefix_should_collect#T1: 644.911s, user=`我是女生`
- humanlike_medium_field_timing_income_optional#T3: 28.614s, user=`深圳`
- humanlike_burst_input_preference_and_city_captured_first_reply#T4: 28.446s, user=`喜欢深圳女生`

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 23 次 (5.4%): `好的小姐姐那先这样啦有需要随时再来找我哦拜拜👋`
- 21 次 (5.0%): `流程是先线上了解并做匹配筛选双方聊得来再安排线下见面这样更稳妥你要是还有顾虑也可以继续问我`
- 17 次 (4.0%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 16 次 (3.8%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 9 次 (2.1%): `好的呀小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 4 次 (0.9%): `小姐姐这个号码好像位数不对呢能确认下是手机号或微信号吗呀`
- 3 次 (0.7%): `好的呀我先记下了要是你电话方便的话也可以留一个后面联系会更及时些`
- 3 次 (0.7%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`
- 2 次 (0.5%): `方便留个电话吗后续有合适的人选时联系你`
- 2 次 (0.5%): `电话只是留作登记和后面联系不会拿去做别的你要是方便的话发我一个号码就行`

## 字段收集质量

- 总检查数: 805
- 失败检查数: 320
- 通过率: 60.2%
- contact_phone_then_wechat_prompt (realism_1_6b9346b8): ["sex_equals_persona: expected='男', actual='女'", "location_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_and_wechat_same_turn (realism_2_b846545d): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_rejection_should_not_end (realism_3_14be61f6): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_after_wechat_rejection_should_not_end (realism_4_d575c8ea): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_refused_then_wechat_fallback (realism_5_e203938a): ["sex_equals_persona: expected='男', actual='女'", "location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None"]
- contact_phone_refused_then_user_provides_wechat (realism_6_796dbc6d): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_ask_phone (realism_7_f0cacb15): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_phone_refusal (realism_8_f3abd857): ["sex_equals_persona: expected='男', actual='女'", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_invalid_should_retry (realism_9_ae6925a5): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_invalid_then_valid (realism_10_1111d64d): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]

## 对话策略规则质量

- 总检查数: 1482
- 失败检查数: 45
- 通过率: 97.0%
- contact_phone_and_wechat_same_turn (realism_2_b846545d): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_after_wechat_rejection_should_not_end (realism_4_d575c8ea): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_phone_refused_then_user_provides_wechat (realism_6_796dbc6d): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_wechat_only_then_ask_phone (realism_7_f0cacb15): ["core_ask_limit_age: expected='<=2', actual=3", 'no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_only_then_phone_refusal (realism_8_f3abd857): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat_rejected_not_end (realism_13_a4070420): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_confirm_word_after_phone_prompt (realism_14_e9f75fbb): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_confirm_word_then_wechat_fallback (realism_15_ac08d4e7): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_user_questions_privacy_before_phone (realism_17_3d400019): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_user_provides_phone_after_privacy_question (realism_18_f58c0c3b): ['no_consecutive_same_field_ask: expected=0, actual=1']
