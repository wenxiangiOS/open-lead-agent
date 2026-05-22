# 配置说明 / Configuration

`open-lead-agent` 的核心原则是：用户应该通过配置改变业务行为，而不是改代码。

The core principle of `open-lead-agent`: users should change business behavior through configuration, not by editing code.

如果你是第一次配置模板，建议先看更短的上手路线：[新用户 10 分钟配置一个行业助手](getting-started-template.md)。这份文档更适合做完整参考。

## 环境变量 / Environment

项目根目录的 `.env.example` 已经按分组写了中英文备注。新用户建议先复制它：

The root `.env.example` includes bilingual comments. New users should start by copying it:

```bash
cp .env.example .env
```

核心变量如下：

```env
# 当前启用的业务模板 / Active business template
ACTIVE_TEMPLATE=matchmaking

# 模板目录 / Template directory
TEMPLATES_DIR=./templates

# 大模型供应商 / LLM provider
LLM_PROVIDER=openai_compatible

# 模型 API Key，留空会使用本地 fallback 回复 / API key; empty means local fallback replies
LLM_API_KEY=

# 模型名称 / Model id
LLM_MODEL=doubao-seed-2-0-pro-260215

# OpenAI-compatible 接口地址 / OpenAI-compatible base URL
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

## 先选配置模式 / Choose a Mode First

配置模板前，先判断你要做哪一种 AI 客服。

| 你想做什么 | 怎么配置 | 结果 |
| --- | --- | --- |
| 只做 AI 智能客服，不收集资料 | 不配置字段，关闭联系方式 | 只回答问题，不追问资料，不提取字段 |
| 做线索收集客服 | 配置资料字段和联系方式字段 | 会从聊天里提取字段，也会按优先级主动追问缺失字段 |
| 只被动记录资料，不主动追问 | 字段保留 `extract: true`，设置 `ask_limit: 0` | 用户主动说了就记录，但 AI 不主动问 |
| 只想关掉某个字段的提取 | 给该字段设置 `extract: false` | 即使用户说了，系统也不会自动提取这个字段 |
| 行业提取规则很复杂 | 配置 `extraction.prompt_file` | 在字段白名单基础上增加行业消歧规则 |

最重要的规则：

- `配置字段`：表示这个字段可以被系统识别和保存
- `extract: true`：允许从用户自然语言里被动提取，默认就是 `true`
- `ask_limit > 0`：允许 AI 主动追问这个字段
- `ask_limit: 0`：不主动问，但仍可被动提取
- `contact.enabled: false`：不主动问联系方式，也不处理联系方式收集流程
- `field_routing.mode: auto`：用户只配置字段，系统自动选择更自然的下一问
- `compliance.rules`：配置命中后要礼貌结束或停止推进的业务边界
- `closing`：配置联系方式完成或没有下一步动作时怎么自然收尾

字段分组会影响主动询问节奏：

- `field_groups.core`：核心主线字段，优先主动询问
- `field_groups.medium`：中等字段，会在和核心字段或用户刚说的信息足够相近时轻量顺带
- `field_groups.low`：低优字段，默认只被动提取，不主动追问

## 单轮理解主链 / Turn Understanding Pipeline

字段提取不是直接把 LLM 输出写进档案。运行时会先经过一层统一理解：

```text
用户消息
  -> TurnSemanticFrame：本轮意图、字段观察、FAQ 意图、合规信号
  -> Field Governance：根据 FAQ、联系方式、短答上下文过滤错槽字段
  -> PersistencePlan：accepted / provisional / pending / rejected
  -> TurnDecision：答疑、问字段、问联系方式、合规结束或收尾
  -> ResponsePlan：承接用户重点，生成自然回复
```

这条链路的开源设计目标是：

- 新用户只配置字段，不需要懂提示词工程
- 模板字段是白名单，没配置的字段不会被保存
- 用户一句话说多个信息时，可以并行识别多个字段
- 短答会结合上一轮目标字段理解，比如上一轮问年龄，用户回“28”
- 行业规则放在 `prompts/extraction/rules.md`，不写死在代码里
- 字段权限可以用 `field_permissions` 做模板级配置，避免行业错槽
- 字段必须先进入提交计划，只有 `accepted` 才会写入 profile

`src/extraction` 目前保留为兼容旧接口的门面；正式语义入口在 `src/understanding`。

### 字段权限治理 / Field Permissions

默认情况下，新用户不用配置 `field_permissions`。系统会自动处理几类通用错槽风险：

- 用户只问 FAQ / 顾虑时，不把模型误提取的资料字段写入档案。
- 正在收集联系方式时，优先保留联系方式字段，避免数字被误提成年龄或收入。
- 用户短答时，优先绑定上一轮实际追问字段。

行业专属错槽规则可以放进模板配置，例如婚恋里“择偶要求”不能写成用户本人学历：

```yaml
field_permissions:
  enabled: true
  rules:
    - name: partner_preference_scope
      intents:
        - partner_preference
      allow_fields:
        - partner_requirement
      allow_mixed_answer: false
      reason: partner_preference_only
```

其它行业也可以用同一套机制。例如教培模板可以把课程需求意图限制到年级、科目、学习目标；招聘模板可以把求职意向限制到期望薪资、目标城市等字段。

### 字段风险与提交状态 / Risk and Persistence

字段通过权限治理后，还会按 `risk`、`min_confidence`、`write_mode` 和格式校验进入不同状态：

| 状态 | 含义 |
| --- | --- |
| `accepted` | 确认度足够，写入 profile |
| `pending` | 需要用户确认，例如高风险低置信、软确认、和旧值冲突 |
| `provisional` | 普通低风险字段暂存，不直接写主档 |
| `rejected` | 模板外字段、格式非法、空值或权限拦截 |

```yaml
field_groups:
  core:
    - key: age
      label: 年龄
      type: number
      risk: high
      min_confidence: 0.8

  low:
    - key: remark
      label: 备注
      type: text
      risk: low
      ask_limit: 0
```

支持的 `risk` 建议值：

- `low`：低风险，适合备注、称呼、补充说明
- `normal`：普通风险，默认值
- `medium`：中等风险，适合有一定误写成本的字段
- `high` / `strict`：高风险，适合年龄、收入、联系方式等敏感或容易误写的字段

### 密集自我介绍 / Dense Intro

当用户一轮里同时说出多个资料、联系方式、需求或 FAQ，理解层会把这一轮标记为 `dense_intro`。

模板作者通常不用配置它。系统会：

- 在提取提示词里要求模型并行提取多个已配置字段。
- 在 debug understanding 里返回 `turn_mode=dense_intro`。
- 在 `no_reask_fields` 里记录本轮已观察字段，方便后续避免重复追问。

这套机制仍然遵守模板字段白名单、字段权限治理和风险仲裁。也就是说，多提取不等于直接乱入档。

### 混合输入优先级 / Mixed Turn Priority

用户可能一上来就把资料、需求、联系方式和问题混在一起说。系统会并行提取字段，但前台回复按公共优先级处理：

1. 合规/风险边界
2. 待确认字段
3. FAQ、问题、顾虑
4. 已满足条件后的自然收尾
5. 联系方式收集
6. 普通资料收集

这个优先级是引擎公共能力，不需要模板作者逐条配置。模板作者只需要配置字段、FAQ、联系方式触发条件和收尾文案。

例如用户说：

```text
男，30岁，深圳做运营，想找稳定点的女生，怎么收费，会不会泄露隐私？微信 abc123
```

系统会尝试提取性别、年龄、城市、职业、需求和微信；但回复会先回答收费和隐私，再根据联系方式是否满足 `contact.trigger` 决定继续收集、确认或收尾，不会机械回头问已经说过的字段。

下面按场景给出配置方式。

## 模板校验 / Template Validation

改完模板后，建议先跑校验命令：

```bash
t --validate-template --template matchmaking
```

校验器会检查这些容易踩坑的地方：

- 字段 key 是否重复，资料字段和联系方式字段是否冲突
- 联系方式触发条件是否引用了不存在的字段
- 合规规则是否引用了不存在的字段，操作符是否支持
- FAQ 是否缺关键词或答案
- RAG 开启后知识库路径是否存在
- 主动追问字段是否缺少 `ask` 示例话术
- 提取提示词是否缺少 `{user_message}` / `{configured_fields}` 等关键占位符

输出里 `ERROR` 表示模板可能无法按预期运行，建议先修复；`WARN` 表示可以运行，但对新用户或真实业务可能不够稳。

这一步不会调用大模型，也不会启动服务，适合放进 CI 或发布前检查。

## 创建新模板 / Create a New Template

最适合新手的方式是使用配置向导：

```bash
t --guided-template my-agent --template-name "我的咨询助手"
```

它只会问行业、字段、联系方式、FAQ，然后生成可运行模板。

如果你只是想快速新建一个行业模板，不需要从零写 YAML：

```bash
t --init-template dental --template-name "口腔咨询助手" --scenario lead
```

这会生成：

```text
templates/dental/template.yaml
templates/dental/knowledge/README.md
templates/dental/prompts/README.md
```

然后先跑一次校验：

```bash
ACTIVE_TEMPLATE=dental t --validate-template
```

`--scenario` 目前有三种：

- `lead`：线索收集模板，包含基础需求、城市、预算、手机号、FAQ、收尾、人性化配置
- `support`：纯客服模板，不主动收集资料，适合只做 FAQ/RAG 问答
- `education`：教培咨询模板，包含学生年级、科目、学习问题、联系方式、FAQ、收尾、人性化配置

脚手架只生成起点，不锁死业务。你可以继续改：

- `agent`：客服名字、人设、语气、边界
- `field_groups`：要收集哪些字段
- `contact.trigger`：收集到哪些字段后才问联系方式
- `faq`：常见问题
- `rag.knowledge_base_path`：知识库目录
- `prompts/`：行业专属提示词

## 场景一：纯 AI 智能客服，不收集资料

适合：官网客服、产品问答、知识库问答、售后咨询。

配置重点：

- `fields: []`
- `field_groups` 为空
- `contact.enabled: false`
- 可以配置 `faq` 和 `rag`

```yaml
template:
  id: support
  name: 智能客服
  description: 只回答用户问题，不收集资料。

agent:
  name: 小助理
  language: zh-CN
  role: 智能客服
  tone: 友好、专业、简洁。
  persona: |
    你是一位专业的智能客服，负责回答用户关于产品、服务、流程的问题。
    不主动索要用户个人资料。
  welcome_message: "你好，请问有什么可以帮你？"

fields: []

field_groups:
  core: []
  medium: []
  low: []

contact:
  enabled: false
  methods: []

faq:
  - intent: pricing
    keywords: ["价格", "收费", "多少钱"]
    answer: "具体价格会根据服务版本不同而变化，你可以告诉我想了解哪个服务。"
    continue_collection: false

rag:
  enabled: true
  knowledge_base_path: ./knowledge/support
```

这样配置后：

- 不会主动问年龄、城市、手机号这类资料
- 不会做自然语言字段提取
- `/api/chat` 返回里的 `next_field` 会是 `null`
- AI 仍然会根据 `agent`、`faq`、`rag` 回答用户问题

## FAQ 答疑 / FAQ

`faq` 适合配置轻量、稳定、短答案的问题，比如收费、门店、流程、隐私边界。用户命中 FAQ 时，系统会先答疑，再根据 `continue_collection` 决定是否轻轻回到资料收集。

```yaml
faq:
  - intent: pricing
    keywords: ["价格", "收费", "多少钱"]
    answer: "基础了解可以先免费沟通，定制服务会根据具体情况再说明。"
    continue_collection: true
```

字段说明：

- `intent`：问题意图，主要用于调试和日志
- `keywords`：命中关键词，大小写不敏感
- `answer`：命中后的答复
- `continue_collection`：答完后是否继续推进下一步字段或联系方式

开源用户可以先用 `faq` 覆盖常见问题，复杂长文档再放到 `rag` 知识库。

运行时系统会把 FAQ 和 RAG 聚合成统一的知识上下文：

- FAQ 命中：可直接用于回答稳定问题
- RAG 结果：作为知识库上下文交给模型参考
- debug 模式会展示 `knowledge_context`，方便你确认本轮为什么先答疑、命中了哪个关键词、检索到了哪些来源

## 场景二：线索收集客服，需要主动问字段

适合：婚恋、教培、医美、本地生活、招聘、CRM 线索收集。

配置重点：

- 在 `field_groups.core` 配核心字段
- 在 `field_groups.medium` 配次要字段
- 在 `field_groups.low` 配只被动收集的字段
- 在 `contact.methods` 配电话、微信、QQ、钉钉等联系方式

```yaml
field_groups:
  core:
    - key: age
      label: 年龄
      type: number
      description: 用户年龄
      examples:
        - 我今年30
        - 30岁
      extract: true
      ask: "你今年多大了？"

    - key: location
      label: 所在城市
      type: text
      description: 用户当前所在城市
      examples:
        - 我在深圳
        - 目前上海
      ask: "你目前在哪个城市？"

  medium:
    - key: monthly_income
      label: 月收入
      type: enum
      options: ["5千以下", "5千-1万", "1万-2万", "2万-5万", "5万以上", "暂不透露"]
      description: 用户月收入区间
      ask: "如果方便的话，也可以了解一下你的月收入区间。"

  low:
    - key: height
      label: 身高
      type: number
      description: 用户身高，单位通常是厘米
```

默认行为：

- `core` 字段默认必填，默认最多主动问 2 次
- `medium` 字段默认选填，默认最多主动问 1 次
- `low` 字段默认不主动问，但用户主动说了会被动提取
- 用户一句话说出多个字段时，会一次性提取多个字段

字段状态：

- `unasked`：还没有主动问过
- `asked`：问过但还没有收集到有效值
- `collected`：已经收集到有效值
- `covered`：虽然没收集到，但已经达到 `ask_limit`，后续不再机械追问
- `skipped`：用户明确说不方便、不想说、不提供，后续不再追问该字段

这套状态的目的，是避免 AI 因为某个字段没答就一直卡住，也让联系方式触发和收尾更自然。

### 什么算有效询问

`ask_limit` 不是“AI 问出口就立刻 +1”。系统会先记录上一轮 AI 问出的主字段，等用户下一轮回应后再判断这次是否消耗一次有效询问。

算有效询问：

- 用户回答了这个字段：字段会被收集，后续不再追问。
- 用户明确拒绝或表示不方便：字段询问次数 +1，并可能标记为 `skipped`。
- 用户只回“嗯 / 好 / ok”等敷衍短答：字段询问次数 +1。
- 用户没有回答当前字段，而是给了其他无关资料：当前字段询问次数 +1，其他资料可被动收集。

不算有效询问：

- 用户插入 FAQ 或业务问题，比如“你们怎么收费？”。
- 用户表达顾虑，比如“为什么要问年龄？”。
- 用户要求先聊别的话题或暂停资料收集。
- 系统自动开场白。
- 用户主动提供信息，但不是 AI 问出来的字段。
- pending confirmation 确认轮次，比如“你刚刚说年龄是30，对吗？”。
- 内部计划的 `side_target`，除非最终回复里真的问出来且用户回答或明确拒绝。

主字段和顺带字段的计数也不同：

- `main_target`：用户没答且没有提问/顾虑打断时，会消耗一次有效询问。
- `side_target`：只有用户回答或明确拒绝时，才消耗一次；用户没理会顺带字段时不消耗。

## 场景三：只被动提取，不主动问

适合：你不希望 AI 像表单一样追问，但希望用户主动说出的资料可以被记录。

配置方式：给字段设置 `ask_limit: 0`，保留 `extract: true`。

```yaml
fields:
  - key: company
    label: 公司名称
    type: text
    extract: true
    ask_limit: 0

  - key: phone
    label: 手机号
    type: phone
    extract: true
    ask_limit: 0
```

这样配置后：

- AI 不会主动问“你公司叫什么”
- AI 不会主动问“方便留手机号吗”
- 用户说“我是某某公司的，手机号是 138...”时，系统会被动提取

## 场景四：联系方式怎么配置

联系方式不要写死在代码里，统一配置在 `contact.methods`。

```yaml
contact:
  enabled: true
  ask_after_required_fields: true
  privacy_message: "联系方式只会用于后续沟通，不会公开展示。"
  methods:
    - key: phone
      label: 手机号
      type: phone
      extract: true
      ask_limit: 2
      ask: "方便留个手机号，后续顾问好跟你沟通吗？"

    - key: wechat
      label: 微信
      type: wechat
      extract: true
      ask_limit: 2
      ask: "如果你更方便微信，也可以留一下微信号。"

    - key: qq
      label: QQ
      type: text
      extract: true
      ask_limit: 0
```

这里的意思是：

- 电话、微信可以主动问
- QQ 不主动问，但用户主动说了可以记录
- 后续要加钉钉、邮箱、小红书号，也只需要继续加 `methods`

## 场景五：某些字段不允许自动提取

适合：内部备注、客服标签、风控字段、只允许系统写入的字段。

```yaml
fields:
  - key: internal_note
    label: 内部备注
    type: text
    extract: false
    ask_limit: 0
```

这样配置后：

- AI 不会主动问这个字段
- 自然语言提取不会包含这个字段
- 即使模型返回了这个字段，程序也会过滤掉

## 场景六：配置行业专属提取提示词

适合：婚恋、招聘、医疗咨询等字段容易歧义的场景。

默认情况下，系统会根据字段配置自动生成提取提示词。如果你需要更强的行业规则，可以把提示词放到模板自己的 `prompts/` 目录里：

```yaml
extraction:
  enabled: true
  prompt_file: prompts/extraction/rules.md
```

`prompts/extraction/rules.md` 可以写行业消歧规则，例如婚恋里的“我是深圳的”和“想找深圳的”不能提取到同一个字段。

可用占位符：

- `{user_message}`：用户本轮消息
- `{known_profile}`：已知资料 JSON
- `{configured_fields}`：当前模板允许提取的字段列表
- `{reply_language}`：模板配置的回复语言

开源原则：

- 提示词放在模板目录下，不写死在 Python 代码里
- 不同模板可以配置不同的提取规则
- 即使提示词写错，程序仍会过滤模板外字段
- `extract: false` 的字段不会进入提取 prompt，也不会被接受

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
      description: 用户年龄，也可以从出生年份推断
      examples:
        - 我今年30
        - 95年的
      extract: true
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
- `description`：字段说明，会提供给自然语言提取模块理解这个字段
- `examples`：用户可能表达这个字段的例子，会提供给自然语言提取模块参考
- `extract`：是否允许从用户自然语言里被动提取，默认 `true`
- `ask`：默认问法
- `required`、`priority`、`ask_limit`：可选覆盖项，用于单独调整字段行为

Field meanings:

- `key`: unique field identifier
- `label`: display label
- `type`: field type, such as `text`, `number`, `enum`, or `phone`
- `options`: enum options
- `description`: field description used by natural-language extraction
- `examples`: example user phrases used by natural-language extraction
- `extract`: whether the field can be passively extracted from user messages; defaults to `true`
- `ask`: default question text
- `required`, `priority`, `ask_limit`: optional overrides for custom field behavior

兼容说明：旧版平铺 `fields` 仍然可用；如果同时配置了 `fields` 和 `field_groups`，运行时优先使用 `fields`。

## 自然语言资料提取 / Natural-Language Extraction

自然语言提取是模板驱动的，不写死婚恋、教培或其他行业字段。

运行时系统会读取当前模板里的 `fields`、`field_groups` 和 `contact.methods`，只尝试提取这些配置过的字段。比如婚恋模板配置了 `sex`、`age`、`location`，用户说“男的，30岁，在深圳”，系统会提取这些字段；教培模板配置了 `student_grade`、`subject`，用户说“孩子初二，想补数学”，系统会提取教培字段。

默认情况下，不需要单独写提取提示词。系统会根据字段的 `key`、`label`、`type`、`options`、`description`、`examples` 自动生成提取提示词。

如果某个行业需要更强的消歧规则，可以配置自定义提取提示词：

```yaml
extraction:
  enabled: true
  prompt_file: prompts/extraction/rules.md
```

`prompts/extraction/rules.md` 可以使用这些占位符：

- `{user_message}`：用户本轮消息
- `{known_profile}`：已知资料 JSON
- `{configured_fields}`：当前模板允许提取的字段列表
- `{reply_language}`：模板配置的回复语言

自定义提示词只负责补充行业规则。底层仍然会强制字段白名单和 JSON 解析，模板外字段、`extract: false` 字段、空值、已有字段都会被过滤。

默认规则：

- 没有配置任何字段时，提取会跳过，适合纯 AI 客服
- 配置了字段，默认就允许被动提取：`extract: true`
- `ask_limit > 0` 表示允许主动追问
- `ask_limit: 0` 表示不主动问，但仍然可以被动提取
- 如果某个字段只给内部系统用，不希望从用户话里提取，可以设置 `extract: false`

提取结果会经过程序二次过滤：

- 模板没有配置的字段会被丢弃
- `extract: false` 的字段会被丢弃
- 空值会被丢弃
- 已有资料默认不覆盖；如果新值和旧值冲突，会进入 `pending`，等待后续确认
- `enum` 字段必须匹配 `options`
- 联系方式会按 `type` 或 `validation` 做格式校验
- 没有配置大模型 Key 时，会跳过自然语言提取，仍可通过 `profile` 显式传入资料

提交计划的含义：

- `accepted`：确定性足够，写入 profile
- `pending`：需要用户确认，比如和旧值冲突、低置信度、`soft_confirm`
- `rejected`：模板外字段、格式非法、空值等，不写入 profile
- `provisional`：预留给后续更复杂的临时值/异步补档机制

当字段进入 `pending` 后，系统会优先确认这个字段。比如旧档案里年龄是 29，用户又说“30岁”，系统会先问“现在是要改成 30 吗？”，用户确认后才更新 profile。

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
      validation: phone
      extract: true
      required: true
      ask_limit: 2
      ask: "Could you share a phone number for follow-up?"
```

如果希望更细地控制“什么时候才能问联系方式”，可以使用 `contact.trigger`：

```yaml
contact:
  enabled: true
  trigger:
    mode: coverage_gate
    required_fields:
      - age
      - location
      - occupation
    optional_fields:
      - budget
      - requirement
    min_required_collected: 2
    require_all_core_covered: true
  methods:
    - key: phone
      label: 手机号
      type: phone
      validation: phone
      ask_limit: 2
      ask: "方便留个手机号，后续好跟你沟通吗？"
```

联系方式支持用 `validation` 指定校验类型。未配置时默认使用 `type`：

| validation/type | 用途 |
| --- | --- |
| `phone` | 电话或手机号，保留 7-15 位数字，可带 `+` 国际区号 |
| `whatsapp` | WhatsApp，按电话格式校验 |
| `email` | 邮箱，会转成小写 |
| `wechat` | 微信号，支持字母、数字、下划线、中划线 |
| `qq` | QQ，5-12 位数字 |
| `telegram` | Telegram 用户名，统一保存为 `@username` |
| `text` | 普通文本，不做专门格式校验 |

字段和联系方式都可以配置风险等级：

```yaml
field_groups:
  core:
    - key: age
      label: 年龄
      type: number
      risk: high
      min_confidence: 0.8

contact:
  methods:
    - key: email
      label: 邮箱
      type: email
      validation: email
      risk: high
      min_confidence: 0.8
```

- `risk: high`：高风险字段，低置信度时不会直接写入 profile
- `min_confidence`：LLM 观察结果低于这个置信度时进入 `pending`
- 联系方式默认就是高风险字段

这里的含义是：

- 至少收集到 2 个核心字段后，才允许进入联系方式
- `require_all_core_covered: true` 表示没有收集到的核心字段，如果已经问满次数，也算覆盖
- 联系方式不会过早出现，也不会因为某个选填字段一直没答而卡死
- 收尾规则也会尊重这个 gate：如果用户过早提供联系方式，但核心资料还不够，系统不会立刻结束对话

## 自动字段规划 / Field Routing

新用户通常只知道“我要收集哪些信息”，不一定知道“哪些字段应该连着问”。所以默认建议使用：

```yaml
field_routing:
  mode: auto
```

`auto` 模式下，系统会根据字段的 `key`、`label`、`description` 和本轮刚收集到的信息，自动选择更自然的下一问。

例如模板配置了：

```yaml
field_groups:
  core:
    - key: location
      label: 所在城市
    - key: occupation
      label: 职业
```

用户说“我在深圳”后，系统会优先顺着问职业，而不是机械地按字段顺序跳到别的问题。

系统还会把这个路由结果转成“表达计划”交给模型，例如：

```json
{
  "action": "ask_field",
  "acknowledge_required": true,
  "acknowledge_focus": "用户本轮刚提供了：所在城市。",
  "target_key": "occupation",
  "target_label": "职业",
  "guidance": "顺着城市聊工作，不要像表单跳问。",
  "avoid_phrases": ["收到", "请提供", "方便说下"],
  "max_active_questions": 1
}
```

表达计划由系统内部自动生成，用户不用配置。它的作用是让模型知道“怎么自然接话”，但不会把内部策略暴露给最终用户。

高级用户可以覆盖默认衔接：

```yaml
field_routing:
  mode: auto
  overrides:
    - from: location
      to: occupation
      weight: 50
      hint: 用户刚说城市时，可以顺着问工作
```

如果你的业务就是固定表单流程，可以关闭自然规划：

```yaml
field_routing:
  mode: ordered
```

## 合规与结束 / Compliance

`compliance.rules` 用来配置不能继续推进资料收集的情况。比如未成年、地区不服务、状态不适合继续咨询等。

```yaml
compliance:
  enabled: true
  rules:
    - id: underage
      description: 未成年人不继续收集资料
      semantic_signals:
        - underage
      semantic_min_confidence: 0.75
      when:
        field: age
        operator: lt
        value: 18
      action: end
      message: |
        这个我得先说明一下，我们这边只面向成年人提供服务。
```

合规规则支持两种触发方式：

- `when.field`：基于已经写入 profile 的结构化字段判断，例如 `age < 18`
- `semantic_signals`：基于单轮理解层输出的高风险语义信号判断，例如用户说“我还没成年”

`semantic_signals` 只有模板显式配置后才会生效；模型输出一个未配置的信号，不会直接结束对话。`semantic_min_confidence` 用来控制语义信号的最低置信度，低于该值会被忽略。

当前支持的常用 `operator`：

- `equals` / `not_equals`
- `in`
- `contains`
- `lt` / `lte` / `gt` / `gte`

## 收尾 / Closing

线索收集不是无限聊天。收完联系方式、联系方式问满次数，或没有下一步动作时，可以配置自然收尾：

```yaml
closing:
  enabled: true
  trigger:
    after_contact_collected: true
    after_contact_covered: true
    when_no_next_action: true
  message: |
    好的，我这边先帮你记下了。后续如果有合适进展，会再跟你沟通。
```

触发口径：

- `after_contact_collected`：已经满足联系方式触发条件，并且本轮收到了电话、微信、邮箱等联系方式
- `after_contact_covered`：已经满足联系方式触发条件，并且所有联系方式都已收集或问满次数
- `when_no_next_action`：没有资料字段、联系方式或 FAQ 后续动作时收尾

如果用户很早就主动提供联系方式，但核心资料还没达到 `contact.trigger` 的条件，系统会先继续正常了解资料，而不是过早结束。

## 拟人化 / Humanization

拟人化不是让 AI 冒充真人，而是减少机器人味：先接住用户，再推进业务；少重复、少表单感、每轮少问。

```yaml
humanization:
  enabled: true
  avoid_repeated_openings: true
  max_active_questions_per_turn: 1
  prefer_contextual_followup: true
  avoid_script_like_questions: true
  recent_phrase_window: 5
```

这组配置会影响字段规划和提示词里的表达建议。默认目标是让 AI 像自然客服一样承接，而不是像脚本机器人一样逐项填表。

运行时系统会根据 `humanization` 生成结构化表达计划，控制：

- 是否必须先承接用户刚说的话
- 承接重点是什么
- 本轮目标字段是什么
- 哪些高频模板句要避免
- 本轮最多主动问几个问题

系统还会做轻量回复质量检查，用于调试拟人化效果。当前检查会标记：

- 是否用了表达计划里要求避免的高频模板句
- 是否一轮问了太多问题
- 是否问字段时没有体现目标字段
- 是否泄露了内部策略、字段路由、debug 信息

第一版质量检查只在 debug 信息里报告问题，不会自动改写模型回复。这样更适合开源用户先观察、调模板，后续再按需要开启自动重生成或规则兜底。

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
