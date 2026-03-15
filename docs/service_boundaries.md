# 服务边界说明

更新时间：2026-03-14

## 总体原则

当前服务层采用“主编排 + 专项服务”的结构：

- `core/chat_service.py` 负责主流程编排
- 具体业务规则、提示拼装、兜底处理、状态追踪逐步拆到独立 service 中

目标是让 `ChatService` 更接近 orchestrator，而不是继续膨胀成单一大类。

---

## 当前服务边界

### 1. 主编排层

- `src/services/core/chat_service.py`

职责：

- 接收请求
- 串联用户状态、提示词、AI 调用、提取、校验、联系方式、收尾
- 返回统一响应

不再建议继续堆积的内容：

- 打招呼规则
- 匹配时长规则
- 无意义输入兜底
- 追问计数细节

这些都已拆到专项 service。

### 2. 对话与提示组装层

- `src/services/core/dialogue_manager.py`
- `src/services/prompts/prompts.py`

职责：

- 读取上下文
- 组装主 prompt / extraction prompt
- 拼接联系方式、跳过字段、智能追问等指令

### 3. 资料收集策略层

- `src/services/collection/profile_collection_policy.py`

职责：

- 资料字段优先级
- 当前主目标 / 顺带目标
- 什么时候允许进入联系方式

### 4. 联系方式决策层

- `src/services/collection/contact_collection_service.py`

职责：

- 电话/微信下一步动作判断
- 拒绝检测
- 香港 / 非香港差异
- 联系方式状态更新与指令构建

### 5. 收尾场景层

- `src/services/conversation/conversation_ending_service.py`

职责：

- 收尾场景识别
- 收尾配置读取
- 收尾状态更新

### 6. 提取与落档层

- `src/services/data/extraction_service.py`

职责：

- 从 AI 回复提取结构化字段
- 做字段映射
- 更新用户资料

### 7. 字段校验层

- `src/services/data/validation_service.py`

职责：

- 电话、微信、年龄、身高等字段的格式校验

### 8. 存储层

- `src/services/data/user_service.py`
- `src/services/data/redis_service.py`

职责：

- 用户状态与用户档案读写
- Redis / 内存兜底

### 9. 新拆出的专项服务

- `src/services/greeting_service.py`
- `src/services/conversation/greeting_service.py`
  - 纯问候识别
  - 时间问候纠正
  - 开场快捷回复

- `src/services/conversation/expectation_service.py`
  - 匹配时长识别
  - 年龄/学历/月薪阈值判断
  - 匹配时长回复生成

- `src/services/conversation/input_fallback_service.py`
  - 无意义输入检测
  - 确认词计数
  - 弱响应 / fallback 回复

- `src/services/collection/ask_tracking_service.py`
  - AI 提问字段识别
  - 字段追问计数
  - 问两次未答后的自动跳过

- `src/services/prompts/prompts.py`
  - 主 prompt / extraction prompt 中心
  - 保留 `src.services.prompts` 作为兼容导入口

---

## 当前建议

后续新增逻辑时，优先判断它属于哪一类：

- 编排顺序问题 -> `chat_service.py`
- 策略决策问题 -> 对应专项 service
- 提示词表达问题 -> `prompts.py`
- 存储问题 -> `data/user_service.py` / `data/redis_service.py`

如果某类规则已经有独立 service，不要再把同类逻辑写回 `chat_service.py`。
