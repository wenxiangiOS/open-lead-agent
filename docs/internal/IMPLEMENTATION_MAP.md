# 需求到实现映射

本文档用于快速查找：某个需求对应哪些配置、代码模块和测试。

## 总表

| 需求 | 配置入口 | 主要实现模块 | 主要测试 |
| --- | --- | --- | --- |
| R001 开场白 | `opening` | `src/cli.py`, `src/templates/config.py`, `src/policy/opening.py`, `src/conversation/engine.py` | `tests/test_cli.py`, `tests/test_conversation_language.py`, `tests/test_matchmaking_regression.py` |
| R002 资料收集 | `field_groups`, `fields` | `src/collection`, `src/policy/field_routing.py`, `src/understanding` | `tests/test_collection_engine.py`, `tests/test_field_routing_policy.py`, `tests/test_extraction_engine.py` |
| R003 有效询问 | `ask_limit` | `src/collection/effective_ask.py`, `src/conversation/engine.py`, `src/collection/state.py` | `tests/test_effective_ask.py`, `tests/test_field_state.py` |
| R004 FAQ/疑虑 | `faq`, `rag` | `src/faq`, `src/rag`, `src/knowledge`, `src/policy/decision.py` | `tests/test_faq_engine.py`, `tests/test_knowledge_engine.py`, `tests/test_semantic_decision.py` |
| R005 联系方式 | `contact` | `src/contact/engine.py`, `src/policy/contact_gate.py`, `src/policy/closing.py` | `tests/test_semantic_decision.py`, `tests/test_closing_policy.py`, `tests/test_http_api.py` |
| R006 合规边界 | `compliance` | `src/policy/compliance.py`, `src/policy/decision.py`, `src/understanding` | `tests/test_semantic_decision.py`, `tests/test_conversation_language.py` |
| R007 拟人化 | `humanization`, `dialogue_policy` | `src/humanization/expression.py`, `src/humanization/quality.py`, `src/conversation/response_builder.py` | `tests/test_response_quality.py`, `tests/test_response_consistency.py`, `tests/test_conversation_language.py` |
| R008 统一理解链路 | `extraction`, `field_permissions`, 字段配置 | `src/understanding`, `src/extraction` | `tests/test_understanding_engine.py`, `tests/test_extraction_engine.py` |
| R009 收尾 | `closing` | `src/policy/closing.py`, `src/policy/decision.py` | `tests/test_closing_policy.py` |
| R010 新手配置向导 | CLI 参数 | `src/templates/guided.py`, `src/templates/scaffold.py`, `src/cli.py` | `tests/test_template_scaffold.py`, `tests/test_cli.py` |
| R011 单轮优先级 | 公共策略，无需普通用户配置 | `src/policy/turn_priority.py`, `src/policy/decision.py` | `tests/test_turn_priority.py`, `tests/test_semantic_decision.py`, `tests/test_closing_policy.py` |

## 维护规则

每新增一个复杂需求，至少补充：

- 需求编号
- 配置入口
- 实现模块
- 测试文件
- 当前状态

如果某个需求还没有测试，要在表格里写明“待补测试”，不要假装已经覆盖。
