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

## 长自我介绍回归样本集（新增）

下面这 6 条长句，作为后续真实 AI / 离线 FakeAI 的重点回归样本。核心检查点不是固定文案，而是：

- 能否拆出哪些是用户自己的资料
- 能否拆出哪些是择偶要求
- 能否识别联系方式与 FAQ
- 当前轮回复是否还会回头追问已经明确给过的字段

样本：

1. `94年，湖南女生在深圳南山，外贸行业工作，深户，港硕，E人，感情经历简单，喜欢做饭旅游，原生家庭幸福美满关系简单，期待遇见同在深圳工作发展90后男生，积极阳光，三观正，到时候可以微信联系我13426689341。`
2. `可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92可以直接电话联系这边13526783627对啦怎么收费呢先了解一下。`
3. `90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地。`
4. `98年女生，本科学历，从事外贸工作，未婚单身，年新在20左右，深圳本地，想着90后男生，喜欢运动，情绪稳定就行，其他没有要求，也可以加我微信联系 13423674892微信和电话同号。`
5. `找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就怎么多了。`
6. `可以啊 96深圳坪山在编教师，湖北人 不高150，105左右，想找能接受身高差，最好深圳有房有车，一样本科或者以上，不要92暂时就这么多了有合适不。`

建议回归时单独记录以下观测：

- `ai_semantic_trigger` 是否命中 `sync_dense_intro` 或 `dense_intro_async_backfill_only`
- `turn_mode` 是否为 `dense_intro`
- `no_reask_fields` 是否覆盖用户已经明确说过的关键信息
- 最终回复是否只追 1 个主字段，没有重新追问年龄/地区/职业等已知信息

## 说明

- 默认离线模式使用 FakeAI，不校验固定文案，只校验行为和状态
- 真实 AI 场景下偶发超时会返回空回复，测试里已做有限自动重试
- 如果模型回复发生自然变体，优先调整“意图断言”，不要回退成精确文案匹配
- 某些场景会因为当前主流程“先回复、后提取再影响下一轮”的时序，表现为要到下一轮才完全稳定；测试断言已按真实架构收敛
- 微信单留、双拒联系方式、高信息量输入这类场景，当前都已按真实 AI 行为收敛过断言
