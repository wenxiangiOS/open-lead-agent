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

## 对话配置 / Conversation

`conversation` 控制 AI 每轮怎么回答、怎么追问，以及回复长度。

```yaml
conversation:
  # 单轮回复里最多主动追问几个字段。建议保持 1，避免一次问太多让用户有压力。
  max_questions_per_turn: 1
  # 用户先问问题时，是否先回答用户问题，再继续收集字段。
  answer_question_before_collection: true
  # AI 回复的最大字数。设置短一点可以让客服回复更像聊天，而不是长篇说明。
  response_max_chars: 220
  # 是否允许在对话中提示转人工、预约顾问或后续人工跟进。
  allow_handoff: true
```

字段说明：

- `max_questions_per_turn`：每轮最多主动问几个资料字段。线索收集场景建议为 `1`。
- `answer_question_before_collection`：用户问价格、流程、服务内容时，是否先回答问题再收集资料。
- `response_max_chars`：单条回复最大字数，用来控制回复不要太长。
- `allow_handoff`：是否允许模板或后续逻辑引导人工跟进。

## 字段分层配置 / Tiered Template Fields

字段配置决定 AI 要收集哪些用户信息。推荐使用 `field_groups` 按收集优先级分层。

Field configuration defines what user information the agent should collect. The recommended
format is `field_groups`, grouped by collection priority.

```yaml
field_groups:
  core:
    - key: age
      label: 年龄
      type: number
      ask: "你今年多大了？"

  medium:
    - key: monthly_income
      label: 月收入
      type: enum
      options: ["5千以下", "5千-1万", "1万-2万", "2万-5万", "5万以上", "暂不透露"]
      ask: "如果方便的话，也可以了解一下你的月收入区间。"

  low:
    - key: height
      label: 身高
      type: number
```

分层含义：

- `core`：核心字段，默认必填，默认最多主动问 2 次
- `medium`：中等字段，默认选填，默认最多主动问 1 次
- `low`：低等字段，被动收集，默认不主动问

字段含义：

- `key`：字段唯一标识
- `label`：展示名称
- `type`：字段类型，如 `text`、`number`、`enum`、`phone`
- `options`：枚举选项
- `ask`：默认问法
- `required`、`priority`、`ask_limit`：可选覆盖项，用于单独调整字段行为

Field meanings:

- `key`: unique field identifier
- `label`: display label
- `type`: field type, such as `text`, `number`, `enum`, or `phone`
- `options`: enum options
- `ask`: default question text
- `required`, `priority`, `ask_limit`: optional overrides for custom field behavior

兼容说明：旧版平铺 `fields` 仍然可用；如果同时配置了 `fields` 和 `field_groups`，运行时优先使用 `fields`。

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
