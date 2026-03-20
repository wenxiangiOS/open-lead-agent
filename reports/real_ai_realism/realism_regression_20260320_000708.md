# 真实用户仿真回归报告

- 会话数: 117
- 总轮次: 435
- 失败检查数: 460
- 失败分布: turn=32, field=387, policy=41
- 时延 p95: 19.993s
- 时延 p99: 971.292s
- 模板化 Top1 占比: 3.5%
- Token: 1726390 (调用 304 次)

## 核心结论

- 拟人化收集通过率: 96.3%
- 字段提取综合通过率: 58.4%
- 字段精确匹配通过率: 76.9%
- 字段完整性通过率: 54.3%

## 拟人化收集质量

- 总检查数: 1956
- 失败检查数: 73
- Turn 级失败: 32
- 策略级失败: 41
- 模板化 Top1 占比: 3.5%
- 时延 p95: 19.993s
- 时延 p99: 971.292s
- 高频 turn 失败 empty_response: 21 次
- 高频 turn 失败 faq_not_answered_first: 6 次
- 高频 turn 失败 confirm_word_misrouted_to_contact: 5 次
- 高频策略失败 no_consecutive_same_field_ask: 36 次
- 高频策略失败 core_ask_limit_age: 2 次
- 高频策略失败 quasi_core_ask_limit_marital_status: 1 次
- 高频策略失败 low_priority_never_ask_height: 1 次
- 高频策略失败 income_question_soft_tone: 1 次

## 字段提取准确性

- 总检查数: 930
- 失败检查数: 387
- 综合通过率: 58.4%
- 精确匹配检查数: 169
- 精确匹配失败数: 39
- 精确匹配通过率: 76.9%
- 完整性检查数: 761
- 完整性失败数: 348
- 完整性通过率: 54.3%
- 高频字段失败 occupation_truthy: 114 次
- 高频字段失败 education_truthy: 92 次
- 高频字段失败 location_truthy: 90 次
- 高频字段失败 sex_not_inferred_without_self_declare: 52 次
- 高频字段失败 age_matches_user_stated: 25 次
- 高频字段失败 sex_matches_user_stated: 4 次
- 高频字段失败 location_matches_user_stated: 4 次
- 高频字段失败 marital_status_matches_user_stated: 3 次
- 高频字段失败 wechat_matches_user_stated: 1 次
- 高频字段失败 occupation_matches_user_stated: 1 次

## 时延异常 Top20

- faq_priority_followup_question_should_still_answer#T1: 1029.686s, user=`找对象`
- field_occupation_placeholder_guard#T1: 997.334s, user=`找对象`
- ending_age_under_limit#T1: 994.851s, user=`我22岁`
- faq_priority_fee#T1: 993.633s, user=`找对象`
- ending_already_married#T1: 971.958s, user=`我已经结婚了`
- humanlike_reception_hesitant_user#T4: 969.999s, user=`本科`
- humanlike_emotion_recognition_joking_response#T2: 966.725s, user=`这是面试吗`
- ending_lgbt_user#T1: 959.299s, user=`我是les`
- humanlike_reception_evasive_user#T1: 953.223s, user=`我是女生`
- humanlike_emotion_recognition_joking_response#T3: 952.466s, user=`问得挺细啊`
- faq_priority_photo_request#T1: 952.459s, user=`找对象`
- faq_priority_can_add_wechat#T1: 947.771s, user=`找对象`
- faq_priority_photo_request#T2: 944.726s, user=`这是面试吗`
- humanlike_light_interaction_after_fields#T2: 810.25s, user=`90后`
- field_occupation_extract_programmer#T1: 456.836s, user=`我做程序员的`

## 优化建议

- LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。

## 模板化风险 Top10

- 15 次 (3.5%): `这块可以放心我们是做真人审核和牵线流程把控的整体会以安全和靠谱为优先你要是还有顾虑也可以继续问我`
- 15 次 (3.5%): `这块你可以放心资料和联系方式只用于匹配与牵线不会对外乱传我们会尽量保护你的隐私`
- 14 次 (3.2%): `咱们基础匹配是免费的定制服务是可选项不合适你也可以直接拒绝你要是还有顾虑也可以继续问我`
- 13 次 (3.0%): `流程是先线上了解并做匹配筛选双方聊得来再后续有合适人选我会第一时间联系你这样更稳妥你要是还有顾虑也可以继续问我`
- 13 次 (3.0%): `方便留个电话吗后续有合适的人选时联系你`
- 10 次 (2.3%): `照片通常是双方都觉得合适后再互换这样更尊重彼此隐私你要是还有顾虑也可以继续问我`
- 8 次 (1.8%): `好的呀小姐姐的电话我记下啦😊要是你微信方便的话也可以留一个后面沟通会更顺手一点`
- 6 次 (1.4%): `好的小姐姐那先这样啦有需要随时再来找我哦拜拜👋`
- 4 次 (0.9%): `好的呀我先记下了要是你电话方便的话也可以留一个后面联系会更及时些`
- 3 次 (0.7%): `你好呀在的我可以先快速了解你两三点也可以先听你说想找什么类型你更想先聊哪边`

## 字段收集质量

- 总检查数: 930
- 失败检查数: 387
- 通过率: 58.4%
- contact_phone_then_wechat_prompt (realism_1_6e346962): ["location_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_and_wechat_same_turn (realism_2_d0161a20): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_rejection_should_not_end (realism_3_b6705d9e): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_after_wechat_rejection_should_not_end (realism_4_44675d7b): ["occupation_truthy: expected='non-empty', actual=None", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_refused_then_wechat_fallback (realism_5_bcd2bc2d): ["location_truthy: expected='non-empty', actual=None", "education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_refused_then_user_provides_wechat (realism_6_73b007f3): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_ask_phone (realism_7_25a0df07): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- contact_wechat_only_then_phone_refusal (realism_8_60ceebec): ["occupation_truthy: expected='non-empty', actual=None"]
- contact_phone_invalid_should_retry (realism_9_475e2839): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None", "age_matches_user_stated: expected='90后', actual=36"]
- contact_phone_invalid_then_valid (realism_10_ef8132aa): ["education_truthy: expected='non-empty', actual=None", "occupation_truthy: expected='non-empty', actual=None"]
- 高频失败 occupation_truthy: 114 次
- 高频失败 education_truthy: 92 次
- 高频失败 location_truthy: 90 次
- 高频失败 sex_not_inferred_without_self_declare: 52 次
- 高频失败 age_matches_user_stated: 25 次
- 高频失败 sex_matches_user_stated: 4 次
- 高频失败 location_matches_user_stated: 4 次
- 高频失败 marital_status_matches_user_stated: 3 次
- 高频失败 wechat_matches_user_stated: 1 次
- 高频失败 occupation_matches_user_stated: 1 次

## 对话策略规则质量

- 总检查数: 1521
- 失败检查数: 41
- 通过率: 97.3%
- contact_phone_and_wechat_same_turn (realism_2_d0161a20): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_rejection_should_not_end (realism_3_b6705d9e): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_after_wechat_rejection_should_not_end (realism_4_44675d7b): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_refused_then_user_provides_wechat (realism_6_73b007f3): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_wechat_only_then_ask_phone (realism_7_25a0df07): ["core_ask_limit_age: expected='<=2', actual=3", 'no_consecutive_same_field_ask: expected=0, actual=1']
- contact_wechat_only_then_phone_refusal (realism_8_60ceebec): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_phone_invalid_should_retry (realism_9_475e2839): ['no_consecutive_same_field_ask: expected=0, actual=1']
- contact_hk_phone_then_wechat_rejected_not_end (realism_13_be63d628): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_confirm_word_then_wechat_fallback (realism_15_4e7bcc11): ['no_consecutive_same_field_ask: expected=0, actual=2']
- contact_user_asks_wechat_instead_of_phone (realism_16_f6d7db34): ['no_consecutive_same_field_ask: expected=0, actual=1']
- 高频失败 no_consecutive_same_field_ask: 36 次
- 高频失败 core_ask_limit_age: 2 次
- 高频失败 quasi_core_ask_limit_marital_status: 1 次
- 高频失败 low_priority_never_ask_height: 1 次
- 高频失败 income_question_soft_tone: 1 次
