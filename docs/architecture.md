# 架构 / Architecture

`open-lead-agent` 拆成 8 个小模块。每个模块只负责一件事，方便开源用户理解、替换和扩展。

`open-lead-agent` is split into eight small modules. Each module owns one responsibility, making it easier to understand, replace, and extend.

## 1. LLM Provider / 大模型模块

负责模型配置和 OpenAI-compatible 聊天调用。

Responsibilities:

- 读取 `LLM_PROVIDER / LLM_API_KEY / LLM_MODEL / LLM_BASE_URL`
- 调用兼容 OpenAI Chat Completions 的模型服务
- 在未配置 API Key 时提供本地 fallback，方便项目快速启动

Owns model settings, OpenAI-compatible chat calls, and local fallback behavior when no API key is configured.

## 2. Template System / 模板模块

负责从 YAML 加载行业模板。

模板里可以定义：

- 行业名称
- Agent 名称和语气
- 字段收集规则
- 联系方式规则
- FAQ
- RAG 配置

Loads industry behavior from YAML, including agent tone, fields, contact methods, FAQ, and RAG settings.

## 3. Conversation Engine / 对话模块

负责把模板、字段收集、联系方式、RAG、存储和 LLM 组合起来，生成一次完整回复。

Combines template configuration, field collection, contact collection, RAG context, storage, and LLM response generation.

## 4. Collection Engine / 字段收集模块

负责根据模板字段和当前用户画像，找出下一个应该收集的字段。

Finds the next user profile field to collect from configured fields and the current profile state.

## 5. Contact Engine / 联系方式模块

负责在资料收集足够后，推进电话、微信、邮箱等联系方式。

Finds the next configured contact method after profile collection is sufficiently complete.

## 6. RAG Knowledge Base / 知识库模块

负责从配置的知识库中检索资料，再提供给对话模块使用。

当前版本是本地 Markdown/TXT 检索骨架，后续可以接向量数据库。

Provides retrieval context from configured knowledge sources. The first implementation is a local Markdown/TXT search interface and can later evolve into vector-store-backed RAG.

## 7. Channel Integrations / 渠道模块

负责把引擎暴露成 HTTP API。后续其他渠道只需要把各自消息格式适配成统一对话请求。

Exposes the engine through HTTP APIs. Other channels should adapt inbound and outbound payloads into the same conversation request shape.

## 8. Storage & Ops / 存储与运维模块

负责保存用户画像、对话历史，以及提供健康检查等运维接口。

Provides state storage, chat history, health checks, and operational helpers.
