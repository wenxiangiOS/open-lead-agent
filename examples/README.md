# Examples 导航

本目录下的示例不是全都对应当前主链路。

请按下面方式理解：

## 1. 当前结论

当前 `examples/` 目录里：

- 已补充主链路官方示例
- 同时保留若干独立子系统演示
- 明显过时的示例已经移到 `examples/archive/`

如果你要看当前项目真实状态，请优先参考：

- `/Users/eric/Desktop/doubao_mcp_server/docs/project_status_summary.md`
- `/Users/eric/Desktop/doubao_mcp_server/docs/refactor_execution_plans.md`
- `/Users/eric/Desktop/doubao_mcp_server/docs/compat_cleanup_plan.md`

## 2. 当前保留示例

### 当前主链路官方示例

- `/Users/eric/Desktop/doubao_mcp_server/examples/chat_api_example.py`
  - `/api/doubao/chat` 调用示例
  - 适用于本地调试、回归验证、应急直连

- `/Users/eric/Desktop/doubao_mcp_server/examples/xhs_ingest_example.py`
  - `/api/xiaohongshu/messages/ingest` 调用示例
  - 适用于异步入站链路调试

- `/Users/eric/Desktop/doubao_mcp_server/examples/xhs_replies_example.py`
  - `GET /api/xiaohongshu/messages/replies` 调用示例
  - 适用于异步投递结果轮询

- `/Users/eric/Desktop/doubao_mcp_server/examples/use_case_protocol_example.py`
  - `ProcessChatTurnCommand` / `IngestMessageCommand` 协议对象示例
  - 适用于开发和调试时理解内部协议

说明：

- 这两个文件优先级高于旧的 examples
- 如果你要看当前项目怎么接接口，先看这两个

### 子系统演示

- `/Users/eric/Desktop/doubao_mcp_server/examples/database_example.py`
  - 数据库子系统示例
  - 非当前主链路官方示例

- `/Users/eric/Desktop/doubao_mcp_server/examples/monitoring_example.py`
  - 监控子系统示例
  - 非当前主链路官方示例

- `/Users/eric/Desktop/doubao_mcp_server/examples/plugin_system_example.py`
  - 插件系统示例
  - 非当前主链路官方示例

## 3. 已归档示例

这些文件因为明显过时或与当前代码路径不一致，已经移到 `examples/archive/`：

- `/Users/eric/Desktop/doubao_mcp_server/examples/archive/get_user_example.py`
- `/Users/eric/Desktop/doubao_mcp_server/examples/archive/with_utils_example.py`

原因：

- import 路径与当前代码结构不一致
- 调用方式与当前服务实际接口不一致
- 容易误导为当前推荐写法

## 4. 当前仍可补充

当前目录还可以继续补的示例：

- debug 模式请求示例（`/api/doubao/chat` + `debug=true`）
- 小红书签名请求示例（带 `X-Timestamp` / `X-Signature`）
- 更完整的端到端串联示例
