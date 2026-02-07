# 工具模块使用指南

本文档介绍 `src/utils/` 模块中统一工具函数的使用方法。

## 目录

- [错误处理工具](#错误处理工具)
- [Redis 工具](#redis-工具)
- [日志工具](#日志工具)
- [验证工具](#验证工具)

---

## 错误处理工具

### @safe_execute 装饰器

自动捕获异常并返回默认值。

```python
from src.utils import safe_execute

@safe_execute(default_return={}, context="用户登录")
async def login(username, password):
    return await authenticate_user(username, password)

# 当 authenticate_user 抛出异常时，自动返回 {}
result = await login("user", "pass")
```

### @retry_on_failure 装饰器

自动重试失败的操作，支持指数退避。

```python
from src.utils import retry_on_failure

@retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(ConnectionError,))
async def fetch_data():
    return await database.query()

# 最多重试 3 次，每次延迟翻倍（1秒 -> 2秒 -> 4秒）
result = await fetch_data()
```

### @ignore_errors 装饰器

静默处理异常，适用于非关键操作。

```python
from src.utils import ignore_errors

@ignore_errors(default_return=False, log_level="warning")
async def log_analytics(event):
    await analytics.track(event)

# 失败时记录警告日志，返回 False
await log_analytics("user_action")
```

### @with_error_handling 装饰器

通用错误处理，支持自定义降级逻辑。

```python
from src.utils import with_error_handling

def fallback_error(error):
    return {"error": str(error)}

@with_error_handling((ValueError, TypeError), fallback=fallback_error)
def process_data(data):
    return int(data)

# 发生 ValueError 或 TypeError 时，调用 fallback_error
result = process_data("invalid")
```

### ErrorContext 上下文管理器

自动记录执行时间和错误信息。

```python
from src.utils import ErrorContext

with ErrorContext("用户注册", user_id="123"):
    register_user(username, email)

# 成功: [用户注册] 执行成功 耗时: 123.45ms
# 失败: [用户注册] 执行失败 耗时: 45.67ms, 错误: ...
```

### execute_safely / execute_safely_async

安全执行函数的便捷方法。

```python
from src.utils import execute_safely, execute_safely_async

# 同步函数
result = execute_safely(
    lambda: risky_operation(),
    context="读取配置",
    default_value={}
)

# 异步函数
result = await execute_safely_async(
    lambda: async_risky_operation(),
    context="API 调用",
    default_value=[]
)
```

---

## Redis 工具

### 便捷函数

统一同步/异步调用，自动降级到内存。

```python
from src.utils import redis_get, redis_set, redis_get_json, redis_set_json

# 基本操作
await redis_set("key", "value", ttl=3600)
value = await redis_get("key", default="default")

# JSON 操作
await redis_set_json("user:123", {"name": "张三"}, ttl=3600)
user_data = await redis_get_json("user:123", default={})

# 删除和检查
await redis_delete("key")
exists = await redis_exists("key")
```

### @redis_fallback 装饰器

Redis 不可用时使用默认值。

```python
from src.utils import redis_fallback

@redis_fallback(default_value={})
async def get_user_config(user_id: str):
    return await redis_get_json(f"user:{user_id}")

# Redis 失败时自动返回 {}
config = await get_user_config("123")
```

### RedisOperation 类

更灵活的 Redis 操作包装器。

```python
from src.utils import RedisOperation

redis_op = RedisOperation(sync_fallback=True)

# 执行任意操作
result = await redis_op.execute(
    "set_json",
    "cache:key",
    {"data": "value"},
    ttl=3600,
    default=None
)
```

---

## 日志工具

### StructuredLogger

结构化日志记录器，支持上下文和 JSON 输出。

```python
from src.utils import StructuredLogger

logger = StructuredLogger("my_module")

# 添加上下文
logger.with_context(user_id="123", request_id="abc")

# 记录日志
logger.info("操作成功", extra={"action": "login"})
logger.error("操作失败", extra={"error_code": "AUTH_FAILED"})

# 清空上下文
logger.clear_context()
```

### @log_execution_time 装饰器

记录函数执行时间。

```python
from src.utils import log_execution_time

# 仅当执行超过 100ms 时记录
@log_execution_time(threshold_ms=100)
async def slow_operation():
    return await process_data()

# 记录所有执行，包含参数和返回值
@log_execution_time(threshold_ms=0, log_args=True, log_result=True)
async def debug_operation(data):
    return await process(data)
```

### @log_api_call 装饰器

API 调用日志，自动脱敏敏感字段。

```python
from src.utils import log_api_call

@log_api_call(
    log_request_body=True,
    log_response_body=True,
    sanitize_fields=["password", "token"]
)
async def login(username, password):
    return await auth_service.login(username, password)

# password 字段自动脱敏为 ***
```

### log_performance 上下文管理器

追踪代码块执行时间。

```python
from src.utils import log_performance

with log_performance("数据库查询", threshold_ms=50):
    results = await database.query("SELECT * FROM users")

# 执行超过 50ms 时自动记录日志
```

### 预配置的日志记录器

```python
from src.utils import api_logger, service_logger, db_logger, cache_logger

# API 日志
api_logger.info("API 调用", extra={"endpoint": "/api/users"})

# 服务日志
service_logger.info("服务启动", extra={"port": 8000})

# 数据库日志
db_logger.info("查询执行", extra={"query": "SELECT...", "rows": 10})

# 缓存日志
cache_logger.info("缓存命中", extra={"key": "user:123"})
```

---

## 验证工具

### ValidationResult

验证结果数据类，支持合并。

```python
from src.utils import ValidationResult

result = ValidationResult(is_valid=True)
result.add_error("邮箱格式无效")
result.add_warning("邮箱可能是临时邮箱")

# 合并其他验证结果
result.merge(other_result)

# 转换为字典
data = result.to_dict()
```

### 验证函数

#### 手机号验证

```python
from src.utils import validate_phone_number

result = validate_phone_number("13800138000")

if result.is_valid:
    phone = result.sanitized_data  # 清理后的手机号
else:
    errors = result.errors  # 错误列表
```

#### 邮箱验证

```python
from src.utils import validate_email

result = validate_email("user@example.com", check_domain=False)

if result.is_valid:
    email = result.sanitized_data  # 小写化并去除空格
```

#### 姓名验证

```python
from src.utils import validate_name

result = validate_name("张三", min_length=2, max_length=20)

if result.is_valid:
    name = result.sanitized_data  # 去除首尾空格
```

#### URL 验证

```python
from src.utils import validate_url

result = validate_url("https://example.com", allowed_schemes=["https"])

if result.is_valid:
    url = result.sanitized_data
```

#### JSON 验证

```python
from src.utils import validate_json

result = validate_json('{"key": "value"}')

if result.is_valid:
    data = result.sanitized_data  # 解析后的字典
```

### @validate_params 装饰器

参数验证装饰器，自动验证和清理。

```python
from src.utils import validate_params, validate_phone_number, validate_email

@validate_params(
    phone=validate_phone_number,
    email=validate_email
)
async def register_user(phone, email):
    # phone 和 email 已经验证并清理
    return await user_service.create(phone, email)

# 参数无效时自动抛出 ValueError
```

### SensitiveWordFilter 敏感词过滤

```python
from src.utils import SensitiveWordFilter

# 创建过滤器
filter_obj = SensitiveWordFilter(words=["测试", "敏感"])

# 检查是否包含敏感词
contains = filter_obj.contains_sensitive("这是测试文本")

# 过滤敏感词
filtered, count = filter_obj.filter("这是测试文本", replacement="***")
# filtered = "这是***文本", count = 1

# 验证文本
result = filter_obj.validate("这是测试文本")
if not result.is_valid:
    print(result.errors)
```

### validate_batch 批量验证

```python
from src.utils import validate_batch, validate_phone_number, validate_email

rules = {
    "phone": lambda x: validate_phone_number(x),
    "email": lambda x: validate_email(x),
    "name": lambda x: validate_name(x)
}

user_data = {
    "phone": "13800138000",
    "email": "test@example.com",
    "name": "张三"
}

result = validate_batch(user_data, rules)

if result.is_valid:
    # user_data 已被清理
    print("验证通过")
else:
    print("错误:", result.errors)
    print("警告:", result.warnings)
```

---

## 最佳实践

### 1. 错误处理

```python
# ✅ 推荐：使用装饰器统一处理
@safe_execute(default_return={}, context="获取用户配置")
async def get_config(user_id):
    return await redis_get_json(f"user:{user_id}")

# ❌ 不推荐：重复的 try-except
async def get_config(user_id):
    try:
        return await redis_get_json(f"user:{user_id}")
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return {}
```

### 2. 日志记录

```python
# ✅ 推荐：使用结构化日志
api_logger.with_context(request_id=request_id).info(
    "API 调用",
    extra={"endpoint": "/api/users", "method": "POST"}
)

# ❌ 不推荐：字符串拼接
logger.info(f"API 调用 request_id={request_id} endpoint=/api/users method=POST")
```

### 3. 数据验证

```python
# ✅ 推荐：使用验证装饰器
@validate_params(
    phone=validate_phone_number,
    email=validate_email
)
async def register(phone, email):
    return await create_user(phone, email)

# ❌ 不推荐：手动验证
async def register(phone, email):
    if not validate_phone(phone):
        raise ValueError("手机号无效")
    if not validate_email(email):
        raise ValueError("邮箱无效")
    return await create_user(phone, email)
```

### 4. Redis 操作

```python
# ✅ 推荐：使用统一的 Redis 工具
@redis_fallback(default_value={})
async def get_user_data(user_id):
    return await redis_get_json(f"user:{user_id}")

# ❌ 不推荐：直接调用 Redis
async def get_user_data(user_id):
    try:
        data = await redis.get(f"user:{user_id}")
        return json.loads(data)
    except:
        return {}
```

---

## 配置

日志输出格式可在配置中设置：

```python
# .env
LOGGING_JSON_ENABLED=true    # 启用 JSON 格式日志
LOGGING_LEVEL=INFO          # 日志级别
LOGGING_SAMPLE_RATE=1.0     # 日志采样率（1.0 = 100%）
```

---

## 迁移指南

### 从现有代码迁移

**旧代码：**

```python
async def get_user_config(user_id: str):
    try:
        data = await redis.get(f"user:{user_id}")
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        logger.error(f"Redis 错误: {e}")
        return {}
```

**新代码：**

```python
from src.utils import redis_get_json

@redis_fallback(default_value={})
async def get_user_config(user_id: str):
    return await redis_get_json(f"user:{user_id}")
```

代码量减少 60%，功能完全相同。
