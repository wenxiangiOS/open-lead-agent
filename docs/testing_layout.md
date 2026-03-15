# 测试目录约定

更新时间：2026-03-14

## 目标

统一测试文件的放置规则，避免测试再次散落到仓库根目录。

---

## 当前目录分工

```text
tests/
  unit/         # 纯单元测试
  integration/  # 集成测试
  e2e/          # 端到端测试
  performance/  # 性能/压测
  scenarios/    # 业务场景脚本
  manual/       # 手工运行脚本
  _deprecated/  # 已过期、待重写测试
```

---

## 放置规则

### `tests/unit/`

放：

- 不依赖真实外部服务
- 依赖可以被 mock
- 运行速度快

不放：

- 真实 AI 测试
- Redis/网络强依赖测试

### `tests/integration/`

放：

- 模块协同测试
- 需要真实 service 组合的测试
- 可选真实 AI 回归入口

### `tests/e2e/`

放：

- 从接口入口到最终输出的完整链路测试

### `tests/performance/`

放：

- 压测
- 并发测试
- 性能基准测试

说明：

- 手工压测脚本可带 `_manual` 后缀

### `tests/scenarios/`

放：

- 业务场景脚本
- 面向规则回归的长流程测试
- 不一定严格符合 pytest 单元测试风格的脚本

### `tests/manual/`

放：

- 开发阶段手工执行的辅助测试脚本
- 不保证持续集成自动跑

### `tests/_deprecated/`

放：

- 已过期但暂时保留参考价值的测试
- 当前不应进入默认测试集

规则：

- 新测试不要再放回这里
- 进入这里的文件要么重写，要么最终删除

---

## 命名建议

- 单元/集成/端到端测试：`test_*.py`
- 手工脚本：`*_manual.py`
- 过期测试：保留原名，放入 `_deprecated/`

---

## 当前约定

- 根目录不再新增 `test_*.py`
- 新测试统一放到 `tests/` 内
- 手工脚本优先放 `tests/manual/` 或 `tests/scenarios/`
