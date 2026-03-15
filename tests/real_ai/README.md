# 真实 AI 场景回归

这套测试用于跑真实 `AIService + ChatService` 端到端链路，不 mock 模型回复。

快速上手请先看：

- `tests/real_ai/QUICKSTART.md`

## 目录结构

- `tests/real_ai/scenario_runner.py`
  统一场景执行器、断言器、报告输出。
- `tests/real_ai/scenarios/*.json`
  场景定义文件，建议按专题拆分维护。
- `scripts/run_real_ai_regression.py`
  命令行入口。

## 运行

列出所有场景：

```bash
python3 scripts/run_real_ai_regression.py --list
```

默认模式：

- 只显示场景开始、通过/失败、耗时和首条失败断言
- 适合日常快速回归

详细模式：

```bash
python3 scripts/run_real_ai_regression.py --verbose
```

- 实时打印每轮用户输入、AI 回复、已收集信息
- 失败场景会自动在终端展开完整 transcript
- 适合排查拟人化、回复自然度和具体跑偏轮次

运行全部场景：

```bash
python3 scripts/run_real_ai_regression.py
```

只跑某个分类：

```bash
python3 scripts/run_real_ai_regression.py --category contact
```

只跑某个场景：

```bash
python3 scripts/run_real_ai_regression.py --scenario-id faq_priority_mediator
```

遇到失败就停：

```bash
python3 scripts/run_real_ai_regression.py --stop-on-failure
```

## 场景格式

每个 JSON 文件结构：

```json
{
  "scenarios": [
    {
      "id": "faq_priority_fee",
      "category": "faq",
      "description": "用户问收费时先答疑",
      "messages": ["找对象", "怎么收费"],
      "assertions": [
        { "type": "response_contains_any", "turn": 2, "values": ["免费", "收费"] },
        { "type": "response_not_contains_any", "turn": 2, "values": ["电话", "微信"] }
      ]
    }
  ]
}
```

## 当前支持的断言

- `response_contains_any`
- `response_not_contains_any`
- `final_response_contains_any`
- `final_response_not_contains_any`
- `profile_field_equals`
- `profile_field_not_equals`
- `profile_field_truthy`
- `profile_field_falsey`

## 建议的扩展顺序

1. `contact`：电话、微信、拒绝、香港用户、无效号码
2. `ending`：分居、离异手续未办妥、双拒绝收尾
3. `field_collection`：多字段提取、模糊表达、占位词污染保护
4. `faq`：收费、门店、牵线、照片、联系方式疑问
