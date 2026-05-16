# 配置说明 / Configuration

`open-lead-agent` 的核心原则是：用户应该通过配置改变业务行为，而不是改代码。

The core principle of `open-lead-agent`: users should change business behavior through configuration, not by editing code.

## 环境变量 / Environment

```env
ACTIVE_TEMPLATE=matchmaking
TEMPLATES_DIR=./templates

LLM_PROVIDER=openai_compatible
LLM_API_KEY=
LLM_MODEL=doubao-seed-1-8-251228
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

说明：

- `ACTIVE_TEMPLATE`：当前启用的行业模板
- `TEMPLATES_DIR`：模板目录
- `LLM_PROVIDER`：模型供应商，当前默认使用 OpenAI-compatible 接口
- `LLM_API_KEY`：模型 API Key
- `LLM_MODEL`：模型名称
- `LLM_BASE_URL`：模型 API 地址

Notes:

- `ACTIVE_TEMPLATE`: active industry template
- `TEMPLATES_DIR`: template directory
- `LLM_PROVIDER`: model provider, currently OpenAI-compatible by default
- `LLM_API_KEY`: model API key
- `LLM_MODEL`: model name
- `LLM_BASE_URL`: model API base URL

## 字段配置 / Template Fields

字段配置决定 AI 要收集哪些用户信息。

Field configuration defines what user information the agent should collect.

```yaml
fields:
  - key: age
    label: Age
    type: number
    required: true
    priority: 20
    ask_limit: 2
    ask: "How old are you?"
```

字段含义：

- `key`：字段唯一标识
- `label`：展示名称
- `type`：字段类型，如 `text`、`number`、`enum`、`phone`
- `required`：是否必填
- `priority`：收集优先级，数字越小越靠前
- `ask_limit`：最多主动询问次数
- `ask`：默认问法

Field meanings:

- `key`: unique field identifier
- `label`: display label
- `type`: field type, such as `text`, `number`, `enum`, or `phone`
- `required`: whether the field is required
- `priority`: collection priority, smaller numbers go first
- `ask_limit`: maximum ask attempts
- `ask`: default question text

## 联系方式配置 / Contact Methods

联系方式配置独立于普通资料字段，方便业务控制什么时候问电话、微信或邮箱。

Contact methods are separate from normal profile fields, making it easier to control when to ask for phone, WeChat, email, or other contact information.

```yaml
contact:
  enabled: true
  ask_after_required_fields: true
  methods:
    - key: phone
      label: Phone
      type: phone
      required: true
      ask_limit: 2
      ask: "Could you share a phone number for follow-up?"
```

## RAG 配置 / RAG

RAG 配置用于企业知识库问答。

RAG configuration is used for business knowledge base Q&A.

```yaml
rag:
  enabled: true
  knowledge_base_path: ./knowledge/education
  top_k: 5
  score_threshold: 0.65
  require_citation: true
```

当前版本提供本地文件检索骨架。后续可以接入 Chroma、Qdrant、Milvus、pgvector 等向量数据库。

The current version provides a local file retrieval skeleton. It can later integrate vector stores such as Chroma, Qdrant, Milvus, or pgvector.
