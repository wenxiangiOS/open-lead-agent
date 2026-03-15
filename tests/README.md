# Tests Layout

本目录按测试目标分层维护：

- `unit/`
  纯规则、纯服务、小范围逻辑测试。
- `integration/`
  `ChatService` 主链路测试，优先使用 fake/mock AI。
- `real_ai/`
  真实 AI 回归场景，面向端到端回归。
- `manual/`
  手工执行的辅助测试，不纳入常规回归。
- `performance/`
  压测和性能实验，不纳入常规回归。
- `_deprecated/`
  历史遗留测试，仅做归档参考。

当前约定：

- 新的业务规则测试默认放 `unit/`
- 新的主流程自动化测试默认放 `integration/`
- 新的真实模型回归默认放 `real_ai/scenarios/*.json`
- 根目录不再新增业务测试文件

额外说明：

- `tests/scenarios/` 不再承载新的场景测试，仅保留迁移说明
- 旧的脚本式场景测试已归档到 `_deprecated/scenarios/`
- `manual/`、`performance/`、`_deprecated/` 不进入常规 CI
