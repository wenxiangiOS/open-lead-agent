# 资料策略回归测试

这套资料收集策略回归入口是：

- 默认离线稳定版：
  `python3 tests/integration/test_profile_collection_policy_integration.py`
- 真实 AI 版：
  `bash scripts/run_real_ai_policy_regression.sh`
  或
  `python3 tests/integration/test_profile_collection_policy_integration.py --real-ai`

真实 AI 前置条件：

- `.env` 中已配置 `ARK_API_KEY`
- 当前环境可以访问模型 API
- 如需完整体验，Redis 可用；如果不可用，系统会退回内存模式

## 当前状态

- 当前覆盖场景数：`13`
- 离线默认模式：可本地稳定回归
- 真实 AI 模式：依赖 `ARK_API_KEY` 和可用外网

最近一次完整真实 AI 回归入口仍然是：

```bash
bash scripts/run_real_ai_policy_regression.sh
```

## 运行整套回归

```bash
python3 tests/integration/test_profile_collection_policy_integration.py
```

## 运行真实 AI 回归

```bash
bash scripts/run_real_ai_policy_regression.sh
```

或：

```bash
python3 tests/integration/test_profile_collection_policy_integration.py --real-ai
```

## 只跑单个场景

脚本支持把 `pytest -k` 关键字直接透传进去：

离线模式：

```bash
python3 tests/integration/test_profile_collection_policy_integration.py -k enters_contact_only_after_profile_ready
```

真实 AI 模式：

```bash
bash scripts/run_real_ai_policy_regression.sh enters_contact_only_after_profile_ready
```

## 当前已覆盖的真实 AI 场景

测试文件：

`tests/integration/test_profile_collection_policy_integration.py`

当前场景包括：

1. 未成熟资料时，不主动问低优字段
2. 用户提问后，先答疑，再回主线
3. 资料成熟后，进入联系方式
4. 完整链路从建档到联系方式
5. 用户主动给低优字段时，只被动提取，不被带偏
6. 用户质疑用途/隐私时，先解释，再回主线
7. 用户敷衍回复时，不跳去追问低优字段
8. 用户分居中时，礼貌结束，不继续推进资料收集
9. 双拒联系方式后，礼貌收尾，不继续追问
10. 用户只留微信、不留电话时，不会卡死在联系方式阶段
11. 离异手续已办妥时，确认后回到主线，不误结束
12. 联系方式阶段被质疑用途时，先解释，再回联系方式主线
13. 用户一条消息给出多个字段时，不回头重复盘问已知字段

## 说明

- 默认离线模式使用 FakeAI，不校验固定文案，只校验行为和状态
- 真实 AI 场景下偶发超时会返回空回复，测试里已做有限自动重试
- 如果模型回复发生自然变体，优先调整“意图断言”，不要回退成精确文案匹配
- 某些场景会因为当前主流程“先回复、后提取再影响下一轮”的时序，表现为要到下一轮才完全稳定；测试断言已按真实架构收敛
- 微信单留、双拒联系方式、高信息量输入这类场景，当前都已按真实 AI 行为收敛过断言
