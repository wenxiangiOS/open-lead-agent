# open-lead-agent

开源、可配置的 AI 客服与线索收集引擎，支持多模型、行业模板、字段收集、联系方式收集和 RAG 知识库。

Open-source configurable AI customer agent for lead collection, RAG knowledge base, and multi-LLM chat.

## 项目定位 / Positioning

`open-lead-agent` 不是某一个行业的固定机器人，而是一个可以通过配置变成不同业务客服的开源底座。

它可以用于：

- 教培课程咨询
- 红娘/相亲线索收集
- 医美、本地生活、招聘等咨询场景
- 企业知识库问答
- 多渠道 AI 客服接入

`open-lead-agent` is not a fixed chatbot for one industry. It is a configurable open-source foundation for building customer agents across different business scenarios.

It can be used for education consultation, matchmaking leads, local services, recruiting, enterprise knowledge base Q&A, and multi-channel customer support.

## 核心模块 / Core Modules

当前 `src/` 按职责拆成这些模块。表格顺序和 `src/` 目录的字母排序保持一致，方便对照查看：

| 模块 | 作用 |
| --- | --- |
| `api` | FastAPI 应用创建与顶层路由注册 |
| `channels` | HTTP/API 等外部渠道适配 |
| `cli.py` | 本地终端聊天、模板校验、模板脚手架命令 |
| `collection` | 普通资料字段收集、字段状态管理 |
| `contact` | 电话、微信、邮箱等联系方式收集 |
| `conversation` | 主对话编排，把理解、知识、策略、拟人化、LLM 和状态保存串成一轮流程 |
| `extraction` | 兼容旧接口的资料提取门面，内部走 understanding |
| `faq` | 轻量关键词 FAQ 匹配 |
| `humanization` | 拟人化表达计划和回复质量检查 |
| `knowledge` | 聚合 FAQ 与 RAG，形成本轮知识上下文 |
| `llm` | 大模型配置与 OpenAI-compatible 调用 |
| `ops` | 健康检查等运维辅助 |
| `policy` | 本轮动作决策、字段路由、联系方式触发、合规、收尾 |
| `rag` | 文件型知识库检索起步实现 |
| `storage` | 对话资料、历史、询问次数等状态存储 |
| `templates` | 行业模板加载、模板校验、模板脚手架 |
| `understanding` | 单轮理解主链，产出字段观察和字段提交计划 |

The current `src/` package is organized by responsibility. The table follows the alphabetical order of the `src/` directory so it is easy to compare side by side:

| Module | Responsibility |
| --- | --- |
| `api` | FastAPI app factory and top-level route registration |
| `channels` | External channel adapters such as HTTP |
| `cli.py` | Local chat, template validation, and template scaffolding commands |
| `collection` | Profile field collection and field state tracking |
| `contact` | Contact method collection |
| `conversation` | Turn orchestration across understanding, knowledge, policy, humanization, LLM, and state |
| `extraction` | Backward-compatible extraction facade backed by understanding |
| `faq` | Lightweight keyword FAQ matching |
| `humanization` | Expression planning and response quality checks |
| `knowledge` | Unified FAQ and RAG knowledge context |
| `llm` | Model settings and OpenAI-compatible generation |
| `ops` | Operational helpers such as health checks |
| `policy` | Turn decisions, field routing, contact gate, compliance, and closing |
| `rag` | Starter file-based knowledge retrieval |
| `storage` | Conversation state storage |
| `templates` | Template loading, validation, and scaffolding |
| `understanding` | Single-turn understanding, field observations, and persistence plans |

## 快速开始 / Quick Start

```bash
cp .env.example .env
pip install -e .
uvicorn main:app --reload
```

健康检查 / Health check:

```bash
curl http://127.0.0.1:8000/health
```

查看当前模板 / Inspect the active template:

```bash
curl http://127.0.0.1:8000/api/config/template
```

聊天 / Chat:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"你好","accountId":"demo-user"}'
```

获取下一个要收集的字段 / Get the next configured field:

```bash
curl -X POST http://127.0.0.1:8000/api/collection/next-field \
  -H "Content-Type: application/json" \
  -d '{"profile":{"age":28}}'
```

## 本地开发 / Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Run the terminal chat:

```bash
t
```

The terminal chat shows compact per-turn test logs by default. Hide them when needed:

```bash
t --quiet-turn
```

Validate a template before running it:

```bash
t --validate-template --template matchmaking
```

Create a starter template:

```bash
t --init-template dental --template-name "口腔咨询助手" --scenario lead
ACTIVE_TEMPLATE=dental t --validate-template
```

Docker:

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

## 配置 / Configuration

按使用场景配置模板：纯 AI 客服、线索收集、只被动提取、联系方式收集等，见 [docs/configuration.md](docs/configuration.md)。

选择行业模板 / Select an industry template:

```env
ACTIVE_TEMPLATE=education
```

配置大模型 / Configure a model:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key
LLM_MODEL=doubao-seed-2-0-pro-260215
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

如果 `LLM_API_KEY` 为空，`/api/chat` 会使用本地 fallback 回复，方便没有模型 Key 的用户也能先跑通项目。

If `LLM_API_KEY` is empty, `/api/chat` uses a local fallback response so the project can run without a paid model key.

## 新用户配置引导 / New User Guide

如果你第一次把项目改成自己的行业助手，建议先看这份 10 分钟配置指南：

[docs/getting-started-template.md](docs/getting-started-template.md)

最短路径：

```bash
ACTIVE_TEMPLATE=matchmaking t --validate-template
ACTIVE_TEMPLATE=matchmaking t
```

最省心的方式是让配置向导问你 4 类问题，然后自动生成模板：

```bash
t --guided-template my-agent --template-name "我的咨询助手"
ACTIVE_TEMPLATE=my-agent t --validate-template
ACTIVE_TEMPLATE=my-agent t
```

或者生成一份自己的教培模板：

```bash
t --init-template my-edu --template-name "我的教培咨询助手" --scenario education
ACTIVE_TEMPLATE=my-edu t --validate-template
ACTIVE_TEMPLATE=my-edu t
```

新用户通常只需要先配置 4 块：`opening` 开场白、`field_groups` 收集字段、`contact` 联系方式、`faq` 常见问题。系统内部负责字段路由、中途答疑后回主线、联系方式触发、拟人化表达和收尾。

## 对话主链 / Turn Pipeline

每一轮用户消息会按这条主链处理：

```text
用户消息
  -> understanding: 理解用户本轮意图，生成字段观察
  -> persistence plan: 判断字段 accepted / provisional / pending / rejected
  -> policy: 决定答疑、合规结束、继续问字段、问联系方式或收尾
  -> humanization: 规划承接方式和自然下一问
  -> LLM / fallback: 生成最终回复
```

模板作者只需要配置“要收集哪些字段、联系方式有哪些、常见问题怎么答、哪些情况要停止”。系统内部负责“怎么理解用户、哪些字段能写入档案、下一步问什么、怎么像真人一样接话”。

## 接入 / Integration

第三方系统通常只需要调用 `/api/chat`，并传入：

- `accountId`：用户唯一 ID
- `dialogId`：会话 ID，可选但推荐
- `question`：用户消息
- `profile`：接入方已知的用户资料

详细说明见 [docs/integration.md](docs/integration.md)。

## 架构 / Architecture

模块边界、单轮理解主链、字段提交计划和配置分层，见 [docs/architecture.md](docs/architecture.md)。

## 模板 / Templates

模板文件位置 / Template location:

```text
templates/<template_id>/template.yaml
```

当前内置示例 / Included examples:

- `matchmaking`
- `education`

每个模板可以配置：

- Agent 名称和语气
- 要收集的字段
- 自然语言资料提取字段说明
- 联系方式类型
- FAQ
- RAG 知识库设置

Each template can configure:

- agent name and tone
- fields to collect
- natural-language extraction hints
- contact methods
- FAQ entries
- RAG knowledge base settings

## 路线图 / Roadmap

- 增加 Redis、Postgres 等持久化存储
- 接入真正的向量数据库 RAG
- 增加 webhook、企微、小红书、网页挂件等渠道
- 增加模板编辑后台
- 增加自定义字段校验器和业务规则插件

Planned work:

- add persistent stores such as Redis and Postgres
- add vector-store-backed RAG
- add webhook, WeChat Work, Xiaohongshu, and web widget adapters
- add an admin UI for editing templates
- add plugin hooks for custom field validators and business rules

## 开源协作 / Open Source

This project is released under the MIT License. See `LICENSE`.

Contributions are welcome. See `.github/CONTRIBUTING.md` for setup and pull request
guidelines, and `.github/SECURITY.md` for vulnerability reporting.
