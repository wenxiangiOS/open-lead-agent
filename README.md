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

当前项目拆成 8 个核心模块：

1. `llm` - 大模型配置与 OpenAI-compatible 调用
2. `templates` - 从 YAML 加载行业模板
3. `conversation` - 对话编排
4. `collection` - 可配置字段收集
5. `contact` - 联系方式收集
6. `rag` - 知识库检索接口
7. `channels` - HTTP/API 渠道接入
8. `storage` 和 `ops` - 状态存储、健康检查、运维辅助

The project is organized into eight modules:

1. `llm` - model configuration and OpenAI-compatible calls
2. `templates` - YAML-based industry templates
3. `conversation` - chat orchestration
4. `collection` - configurable field collection
5. `contact` - contact method collection
6. `rag` - knowledge retrieval interface
7. `channels` - HTTP/API channel integration
8. `storage` and `ops` - state, health, and operational helpers

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

Docker:

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

## 配置 / Configuration

选择行业模板 / Select an industry template:

```env
ACTIVE_TEMPLATE=education
```

配置大模型 / Configure a model:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key
LLM_MODEL=doubao-seed-1-8-251228
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

如果 `LLM_API_KEY` 为空，`/api/chat` 会使用本地 fallback 回复，方便没有模型 Key 的用户也能先跑通项目。

If `LLM_API_KEY` is empty, `/api/chat` uses a local fallback response so the project can run without a paid model key.

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
- 联系方式类型
- FAQ
- RAG 知识库设置

Each template can configure:

- agent name and tone
- fields to collect
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
