# 联系方式收集 - 速查表

## 一句话总结
> 香港用户：电话2次 + 微信2次
> 非香港用户：电话2次 + 微信1次（电话已收集时）

---

## 快速判断表

### 下一步做什么？
```
rejected_phone && rejected_wechat → 结束对话 ❌
rejected_wechat && !phone_collected → 询问电话 📞
rejected_phone && !wechat_collected → 询问微信 💬
!phone_collected && !rejected_phone → 询问电话 📞
phone_collected && !wechat_collected → 询问微信 💬
```

### 微信最多问几次？
```
香港用户 → 2 次
非香港 + 电话已收集 → 1 次
非香港 + 电话未收集 → 2 次
```

---

## 核心代码位置

```
src/services/contact_collection_service.py
├── get_next_action()      # 决策下一步
├── detect_refusal()       # 检测拒绝
├── build_instruction()    # 构建指令
└── get_status_display()   # 状态显示
```

---

## 状态字段速查

| 字段 | 类型 | 说明 |
|-----|------|------|
| `phone` | str | 电话号码 |
| `wechat` | str | 微信号 |
| `phone_collected` | bool | 电话已收集 |
| `wechat_collected` | bool | 微信已收集 |
| `phone_ask_count` | int | 电话询问次数 |
| `wechat_ask_count` | int | 微信询问次数 |
| `rejected_phone` | bool | 电话被拒绝 |
| `rejected_wechat` | bool | 微信被拒绝 |
| `is_hongkong_user` | bool | 香港用户 |

---

## 状态显示

```
"未留"           → 都没开始
"电话争取中"     → 正在问电话
"微信争取中"     → 正在问微信
"电话: xxx"      → 电话已收集
"微信: xxx"      → 微信已收集
"不愿留电话"     → 电话被拒绝
"不愿留微信"     → 微信被拒绝
```

---

## 测试命令

```bash
# 运行所有联系方式测试
python -m pytest tests/test_contact_collection_*.py -v

# 运行服务测试 (50个)
python -m pytest tests/test_contact_collection_service.py -v

# 运行场景测试 (16个)
python -m pytest tests/test_contact_collection_scenarios.py -v
```
