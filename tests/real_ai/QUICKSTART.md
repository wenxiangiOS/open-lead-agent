# 真实 AI 回归快速使用

这套测试用于跑真实 `AIService + ChatService` 链路，不 mock 模型回复。

入口脚本：

- `scripts/run_real_ai_regression.py`

场景目录：

- `tests/real_ai/scenarios/`

结果报告：

- `reports/real_ai/latest.md`
- `reports/real_ai/latest.json`

## 日常最常用

改完代码先跑一组核心场景：

```bash
python3 scripts/run_real_ai_regression.py --profile smoke
```

如果你改的是联系方式：

```bash
python3 scripts/run_real_ai_regression.py --category contact
```

如果你改的是收尾或离异：

```bash
python3 scripts/run_real_ai_regression.py --category ending
```

如果你改的是字段提取：

```bash
python3 scripts/run_real_ai_regression.py --category field_collection
```

## 常用命令

查看当前有哪些场景：

```bash
python3 scripts/run_real_ai_regression.py --list
```

查看逐轮用户输入、AI 回复和已收集信息：

```bash
python3 scripts/run_real_ai_regression.py --verbose
```

只跑一个场景：

```bash
python3 scripts/run_real_ai_regression.py --scenario-id faq_priority_mediator
```

只跑某个标签：

```bash
python3 scripts/run_real_ai_regression.py --tag smoke
```

重跑上一次失败的场景：

```bash
python3 scripts/run_real_ai_regression.py --rerun-failed
```

校验场景文件本身：

```bash
python3 scripts/run_real_ai_regression.py --validate --require-tags
```

## 失败后怎么看

先看：

- `reports/real_ai/latest.md`

这个文件会直接告诉你：

- 哪些场景失败
- 第几轮失败
- 用户说了什么
- AI 回了什么
- 哪条断言没过

如果你希望直接看终端里的逐轮对话，不想等报告生成，使用 `--verbose`。
失败场景会在终端自动展开 transcript，便于直接贴日志排查。

## 你以后怎么维护

新增场景时，直接在 `tests/real_ai/scenarios/*.json` 里加。

建议规则：

- 改联系方式相关逻辑，就补 `contact_regression.json`
- 改答疑优先，就补 `faq_regression.json`
- 改收尾逻辑，就补 `ending_regression.json`
- 改提取逻辑，就补 `field_collection_regression.json`

新增场景后，先跑：

```bash
python3 scripts/run_real_ai_regression.py --validate --require-tags
```

再跑对应专题。
