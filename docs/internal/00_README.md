# 内部文档导航

本文档是 `docs/internal/` 的入口，只给项目维护者和协作 AI 看，不作为对外开源说明。

## 阅读顺序

如果你隔一段时间后回来维护项目，建议按这个顺序看：

1. `01_REQUIREMENTS.md`：项目需求总览，先理解为什么要这样设计。
2. `IMPLEMENTATION_MAP.md`：需求对应到哪些配置、代码和测试。
3. `requirements/R001_OPENING.md`：开场白规则。
4. `requirements/R002_PROFILE_COLLECTION.md`：资料收集主流程。
5. `requirements/R003_EFFECTIVE_ASK.md`：有效询问和 ask_limit 规则。
6. `requirements/R005_CONTACT_COLLECTION.md`：联系方式收集规则。
7. `requirements/R007_HUMANIZATION.md`：拟人化规则。

## 文档分工

| 文档 | 作用 |
| --- | --- |
| `01_REQUIREMENTS.md` | 需求真相文档，记录项目要实现什么、为什么做、当前状态 |
| `IMPLEMENTATION_MAP.md` | 需求到配置、代码、测试的映射 |
| `requirements/*.md` | 单个复杂需求的详细规则和示例 |

## 和对外文档的关系

| 对外文档 | 作用 |
| --- | --- |
| `docs/getting-started-template.md` | 给新手，快速配置一个模板 |
| `docs/configuration.md` | 给模板作者，说明配置项怎么写 |
| `docs/architecture.md` | 给开发者，说明模块边界和主链路 |
| `docs/integration.md` | 给接入方，说明 API 怎么调用 |

内部文档关注的是：

- 当初为什么要这么设计
- 需求规则到底是什么
- 需求落在哪些代码和测试里
- 哪些已经实现，哪些只是后续方向

## 冲突处理

如果文档、代码和测试出现冲突，按下面顺序判断：

1. 当前测试和代码代表真实运行现状。
2. `01_REQUIREMENTS.md` 代表当前需求意图。
3. `requirements/*.md` 代表专题规则细节。
4. 旧讨论、历史备注和未标状态的文字只作为参考。

如果修改了需求行为，必须同步更新：

- `01_REQUIREMENTS.md`
- 对应的 `requirements/Rxxx_*.md`
- `IMPLEMENTATION_MAP.md`
