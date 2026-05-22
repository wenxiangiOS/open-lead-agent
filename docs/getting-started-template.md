# 新用户 10 分钟配置一个行业助手

这份文档给第一次使用 `open-lead-agent` 的用户看。你不需要先理解全部源码，只要先改模板配置，就可以跑出一个能开场、答疑、收集资料、收集联系方式并收尾的 AI 客服。

## 先理解 4 个配置块

一个模板主要改这 4 块：

| 配置块 | 解决什么问题 | 新手要不要先改 |
| --- | --- | --- |
| `opening` | 用户首次进入时说什么 | 要 |
| `field_groups` | 需要收集哪些资料 | 要 |
| `contact` | 什么时候收集电话、微信、邮箱等联系方式 | 要 |
| `faq` | 用户中途问收费、门店、隐私等问题时怎么答 | 要 |

其他配置比如 `humanization`、`compliance`、`closing` 可以先用模板默认值，后面再细调。

## 方式一：复制当前主模板

项目当前主线是婚恋线索模板，可以先直接运行：

```bash
ACTIVE_TEMPLATE=matchmaking t --validate-template
ACTIVE_TEMPLATE=matchmaking t
```

模板位置：

```text
templates/matchmaking/template.yaml
```

你可以复制一份再改：

```bash
cp -R templates/matchmaking templates/my-template
```

然后把 `templates/my-template/template.yaml` 里的 `template.id` 改成 `my-template`，再运行：

```bash
ACTIVE_TEMPLATE=my-template t --validate-template
ACTIVE_TEMPLATE=my-template t
```

## 方式二：用脚手架生成模板

如果你想从空模板开始：

```bash
t --init-template my-edu --template-name "我的教培咨询助手" --scenario education
ACTIVE_TEMPLATE=my-edu t --validate-template
ACTIVE_TEMPLATE=my-edu t
```

脚手架会生成：

```text
templates/my-edu/template.yaml
templates/my-edu/knowledge/README.md
templates/my-edu/prompts/README.md
```

## 方式三：回答几个问题自动生成模板

如果你不想手写 YAML，可以直接使用新手配置向导：

```bash
t --guided-template my-agent --template-name "我的咨询助手"
```

它会依次问你：

```text
1. 你是什么行业/场景？
2. 你要收集哪些字段？
3. 要收集哪些联系方式？
4. 常见问题怎么答？
5. 开场白可选
```

示例回答：

```text
行业/场景：教培
收集字段：学生年级, 科目, 学习问题
联系方式：手机号, 微信
常见问题：怎么收费=收费会根据年级、科目和班型不同而变化。
```

生成后验证并试聊：

```bash
ACTIVE_TEMPLATE=my-agent t --validate-template
ACTIVE_TEMPLATE=my-agent t
```

## 第一步：配置开场白

开场白的目标不是问一堆资料，而是降低用户开口成本。

```yaml
opening:
  enabled: true
  message: "你好呀，我是课程顾问。你是想给孩子了解课程，还是自己想了解学习规划？"
  greeting_response: "你好呀，你可以先简单说下想了解的情况，我先了解一下。"
  quick_replies:
    - 给孩子了解
    - 自己想了解
    - 先问下收费
```

建议：

- 开场白短一点，像真人打招呼。
- `greeting_response` 用来处理用户看完开场白后只回“你好”的场景，先低压承接，不要立刻像表单一样追问字段。
- 可以给 2-3 个快捷回复，让用户容易继续。
- 不要一上来就连续问年级、科目、电话。

## 第二步：配置要收集的资料

新手优先使用 `field_groups`，不用自己设计复杂顺序。

```yaml
field_groups:
  core:
    - key: student_grade
      label: 学生年级
      type: text
      description: 学生当前年级，例如小学三年级、初二、高一。
      ask: "孩子现在读几年级呀？"

    - key: subject
      label: 咨询科目
      type: text
      description: 用户主要想咨询的科目或课程方向。
      ask: "主要想了解哪门课呢？"

  medium:
    - key: learning_problem
      label: 学习问题
      type: text
      description: 当前想解决的学习困难、目标或咨询原因。
      ask: "目前主要想解决什么学习问题呀？"

  low:
    - key: parent_name
      label: 称呼
      type: text
      ask_limit: 0
```

字段分组含义：

| 分组 | 含义 |
| --- | --- |
| `core` | 核心字段，会优先收集，通常决定能不能进入联系方式 |
| `medium` | 有价值但不是必须，问过一定次数后可以跳过 |
| `low` | 低优字段，适合被动提取，比如称呼、身高、备注 |

系统会尽量自动做拟人化追问。例如用户刚说“我在深圳”，下一步更可能顺着问“主要想了解哪门课”，而不是死板按表单顺序重复。

## 第三步：配置联系方式

联系方式是一个独立模块，不只支持电话和微信，也可以支持邮箱、QQ、WhatsApp、Telegram 等。

```yaml
contact:
  enabled: true
  trigger:
    mode: coverage_gate
    required_fields:
      - student_grade
      - subject
    optional_fields:
      - learning_problem
    min_required_collected: 2
    require_all_core_covered: true
  privacy_message: "联系方式只会用于后续课程咨询，不会公开展示。"
  methods:
    - key: phone
      label: 手机号
      type: phone
      validation: phone
      ask_limit: 2
      ask: "方便留个手机号吗？课程顾问后续可以按孩子情况给你更具体的建议。"
```

常见联系方式配置：

```yaml
methods:
  - key: phone
    label: 手机号
    type: phone
    validation: phone
    ask: "方便留个手机号吗？"

  - key: wechat
    label: 微信
    type: text
    validation: wechat
    ask: "微信方便留一下吗？后续沟通会顺一点。"

  - key: email
    label: 邮箱
    type: email
    validation: email
    ask: "如果方便，也可以留个邮箱，后续资料发你会更方便。"
```

## 第四步：配置 FAQ

FAQ 用来处理中途打断。用户问“怎么收费”“有门店吗”“靠谱吗”时，系统会先答疑，再根据 `continue_collection` 决定是否回到资料收集主线。

```yaml
faq:
  - intent: pricing
    keywords: ["收费", "价格", "多少钱", "费用", "学费"]
    answer: "收费会和年级、科目、班型有关，可以先了解孩子情况，再给你更具体的说明。"
    continue_collection: true

  - intent: privacy
    keywords: ["隐私", "泄露", "手机号安全吗", "会不会打扰"]
    answer: "你担心这个很正常。联系方式只用于后续课程沟通，不会公开展示，也不会拿来乱发。"
    continue_collection: true
```

行业不同，FAQ 就不同：

| 行业 | 常见 FAQ |
| --- | --- |
| 婚恋 | 收费、门店、隐私、照片、靠谱、为什么问资料 |
| 教培 | 收费、试听、上课方式、校区、师资、退费 |
| 招聘 | 薪资、岗位真实性、面试流程、工作地点 |
| 海外服务 | 费用、周期、材料、成功率、WhatsApp/Telegram 联系 |

## 第五步：配置合规结束

合规规则用于“不能继续收集”的情况，比如未成年人独立咨询、用户明确拒绝、业务不服务某些地区等。

```yaml
compliance:
  enabled: true
  rules:
    - id: underage_without_guardian
      description: 未成年人独立咨询时，停止继续收集个人资料。
      semantic_signals:
        - underage_user_without_guardian
      semantic_min_confidence: 0.75
      action: end
      message: "如果你还未成年，建议让家长一起了解会更合适。这边就先不继续收集你的个人信息啦。"
```

## 第六步：配置收尾

联系方式收集完成后，不应该无限聊下去。可以配置自然收尾：

```yaml
closing:
  enabled: true
  trigger:
    after_contact_collected: true
    after_contact_covered: true
    when_no_next_action: true
  message: "好，我这边先记下了。后续课程顾问会结合你说的情况再沟通。"
```

## 验证和调试

每次改完模板，先跑校验：

```bash
ACTIVE_TEMPLATE=my-edu t --validate-template
```

本地终端测试：

```bash
ACTIVE_TEMPLATE=my-edu t
```

本地终端默认会显示每轮的理解、决策、收集和质量检查摘要，方便调试模板。
如果只想看干净对话，可以关闭测试日志：

```bash
ACTIVE_TEMPLATE=my-edu t --quiet-turn
```

如果模型调用失败，测试工具会尽量说明是超时、连接失败、鉴权失败还是普通异常，并打印当前模型配置摘要。

启动 API：

```bash
uvicorn main:app --reload
```

打开接口调试台：

```text
http://127.0.0.1:8000/docs
```

注意：

- `/docs` 是 FastAPI 自动生成的接口调试台，适合新手点开测试。
- `/api/chat` 是聊天接口，只支持 `POST`，浏览器直接打开会显示不出来或报错。

## 新手推荐改法

第一次接入一个新行业时，只改这些：

1. 改 `template.id`、`template.name`。
2. 改 `agent.name`、`opening.message`。
3. 在 `field_groups.core` 放 2-4 个核心字段。
4. 在 `field_groups.medium` 放 1-4 个可选字段。
5. 在 `contact.methods` 配置你要收集的联系方式。
6. 在 `faq` 放 5-10 个用户最常问的问题。
7. 跑 `t --validate-template`，再用终端聊几轮。

等这个模板跑顺了，再考虑 RAG、独立提示词文件、高级字段校验和渠道接入。
