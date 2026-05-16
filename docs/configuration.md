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

## 人设配置 / Agent Persona

`agent` 控制 AI 客服“是谁、怎么说话、什么能说、什么不能说”。用户配置自己的行业客服时，通常优先改这一段。

```yaml
agent:
  # AI 客服名称，会出现在 system prompt 里。
  name: 小缘
  # 回复语言。中文客服建议使用 zh-CN。
  language: zh-CN
  # 核心身份。用于告诉模型“你是谁”。
  role: 婚恋咨询顾问
  # 说话风格。越具体，模型越稳定。
  tone: 温暖、自然、有分寸，不给用户压力。
  # 核心人设。用于描述这个 AI 客服应该像什么样的人。
  persona: |
    你是一位专业、温暖、有边界感的婚恋咨询顾问。
    你的目标不是强行推销服务，而是先让用户感到被理解，
    再自然收集匹配所需的基本信息。
  # 任务目标。模型会优先围绕这些目标推进对话。
  goals:
    - 了解用户的基础资料，判断是否适合后续服务。
    - 在不冒犯用户的前提下，逐步收集必要字段。
  # 对话规则。用于控制提问节奏、语气和边界感。
  behavior_rules:
    - 每次最多主动问一个问题。
    - 先回应用户的问题或情绪，再自然追问资料。
  # 禁止事项。用于防止模型过度承诺或说不合适的话。
  boundaries:
    - 不承诺一定成功。
    - 不编造未配置的价格、服务承诺或案例。
  welcome_message: "你好呀，我是小缘。你是认真想找对象，还是想先了解一下服务？"
```

字段说明：

- `name`：AI 客服名字
- `language`：回复语言
- `role`：核心身份，比如婚恋咨询顾问、课程顾问、招聘顾问
- `tone`：语气风格
- `persona`：完整人设描述
- `goals`：对话目标
- `behavior_rules`：对话规则
- `boundaries`：禁止事项和安全边界
- `welcome_message`：欢迎语

## 主对话策略 / Dialogue Policy

`dialogue_policy` 控制 AI 在一轮对话里怎么推进、怎么承接、哪些话术要避免。它比 `agent` 更偏“对话执行规则”。

```yaml
dialogue_policy:
  # 本轮对话的总体目标，会进入 system prompt。
  turn_goal: |
    自然聊天中推进资料收集：先承接用户，再推进主目标，不要像填表或审问。

  # 通用策略分组。不同业务可以自由增删 section，不需要改代码。
  sections:
    - title: Dialogue priorities
      rules:
        - 用户提问或顾虑先答清楚。
        - 其余轮次围绕主目标字段推进。

    - title: General principles
      rules:
        - 已收集字段不要重复问。
        - 低优字段只被动记录，不主动盘问。
        - 联系方式只在资料足够或用户主动愿意留时推进。

    - title: 行业专项规则
      rules:
        - 这里可以放婚恋、教培、招聘、医美等行业自己的对话规则。

    - title: 禁止事项
      rules:
        - 禁止一上来直接切新字段，像表单盘问。
        - 禁止把业务说得过满。

  # 表达示例。模型只借鉴风格，不要逐字照抄。
  examples:
    - user: 你们靠谱吗
      better: 你会先顾虑这个很正常，我先把流程和边界跟你说明白，你再决定要不要继续聊。
      worse: 靠谱的，你先说年龄。
```

`sections` 是通用结构。婚恋模板可以写“婚况与分居处理”，教培模板可以写“试听课引导”，招聘模板可以写“岗位匹配规则”，都不需要改 Python 代码。

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
