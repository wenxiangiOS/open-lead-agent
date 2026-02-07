# 并发配置说明

## 概述

本项目使用统一的并发管理模块来控制高并发场景：

```
src/infrastructure/concurrency/
├── __init__.py           # 模块入口
├── config.py             # 并发配置
├── manager.py            # 并发管理器（统一入口）
├── rate_limiter.py       # 统一限流器
└── connection_pool.py    # 连接池管理器
```

## 配置项

### 1. 连接池配置

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| `redis_pool_size` | 50 | Redis 连接池大小 |
| `http_pool_size` | 50 | HTTP 连接池大小（AI API） |
| `http_max_keepalive` | 10 | HTTP Keep-Alive 连接数 |
| `http_timeout` | 60 | HTTP 请求超时（秒） |

### 2. 限流配置

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| `rate_limit_enabled` | True | 是否启用限流 |
| `user_rate_limit` | 100 | 每个用户每分钟请求数 |
| `global_rate_limit` | 1000 | 全局每分钟请求数 |
| `ip_rate_limit` | 200 | 每个 IP 每分钟请求数 |

### 3. 分级限流

| 等级 | 限制 | 说明 |
|-----|------|------|
| `free` | 10/分钟 | 免费用户 |
| `basic` | 50/分钟 | 基础用户 |
| `pro` | 100/分钟 | 专业用户 |
| `enterprise` | 1000/分钟 | 企业用户 |

## 使用方法

### 1. 在服务中使用并发管理器

```python
from src.infrastructure.concurrency import get_concurrency_manager

async def my_service_function(user_id: str):
    # 获取并发管理器
    manager = get_concurrency_manager()

    # 检查限流
    result = await manager.check_user_rate_limit(user_id)
    if not result.allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 获取 HTTP 客户端
    http_client = await manager.get_http_client()

    # 获取 Redis 客户端
    redis_client = await manager.get_redis_async_client()

    # ... 业务逻辑
```

### 2. 设置用户等级

```python
from src.infrastructure.concurrency import get_concurrency_manager

manager = get_concurrency_manager()

# 设置用户为 pro 等级（100 请求/分钟）
manager.set_user_tier("user_123", "pro")
```

### 3. 使用限流器

```python
from src.infrastructure.concurrency import get_rate_limiter

limiter = get_rate_limiter()

# 检查限流
result = await limiter.is_allowed("ip:192.168.1.1", limit=200, window=60)

if result.allowed:
    # 处理请求
    pass
else:
    # 返回 429
    pass
```

## 并发能力

### 当前配置支持

| 指标 | 值 |
|-----|-----|
| 理论并发 | 50 个连接 |
| 实际 QPS | ~8-10 请求/秒 |
| 日处理量 | ~700,000 请求/天 |
| 适用场景 | 10-50 用户同时使用 |

### 如何提升并发

1. **增加连接池大小**（在 `ConcurrencyConfig` 中修改）：
   - `redis_pool_size`: 50 → 100
   - `http_pool_size`: 50 → 100

2. **启用多进程**（在 `main.py` 中修改）：
   ```python
   uvicorn.run(app, workers=4)
   ```

3. **使用负载均衡**：
   - 使用 Nginx 反向代理
   - 部署多个实例

## 健康检查

```bash
curl http://localhost:8000/health/concurrency
```

返回：
```json
{
  "config": {
    "rate_limit_enabled": true,
    "user_rate_limit": 100,
    "max_concurrent_requests": 50
  },
  "components": {
    "http_client": true,
    "redis_async": true,
    "redis_sync": true
  }
}
```

## 迁移指南

### 从旧限流器迁移

**旧代码**：
```python
from src.api.middleware.rate_limit import rate_limiter

await rate_limiter.check_rate_limit(client_id)
```

**新代码**：
```python
from src.infrastructure.concurrency import get_concurrency_manager

manager = get_concurrency_manager()
await manager.check_rate_limit(client_id)
```

### 从旧连接池迁移

**旧代码**：
```python
import httpx

client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=50)
)
```

**新代码**：
```python
from src.infrastructure.concurrency import get_concurrency_manager

manager = get_concurrency_manager()
client = await manager.get_http_client()
```

## 注意事项

1. **向后兼容**：旧的限流器仍然可用，但推荐使用新的并发管理器
2. **配置优先级**：环境变量 > 配置文件 > 默认值
3. **降级策略**：Redis 不可用时自动降级到内存模式
4. **资源清理**：应用关闭时会自动清理所有连接池
