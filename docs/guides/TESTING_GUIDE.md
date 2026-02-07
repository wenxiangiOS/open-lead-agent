# 测试指南

## 概述

本项目包含完整的测试套件，涵盖单元测试、性能测试和负载测试。

---

## 测试结构

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   └── test_services.py      # 单元测试
└── performance/
    ├── __init__.py
    └── test_load.py          # 性能测试
```

---

## 快速开始

### 安装测试依赖

```bash
# 安装所有依赖（包括测试依赖）
pip install -r requirements.txt

# 或者仅安装测试依赖
pip install pytest pytest-asyncio pytest-cov pytest-mock psutil locust
```

### 运行所有测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行性能测试
pytest tests/performance/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

---

## 测试类型

### 1. 单元测试 (`tests/unit/test_services.py`)

**测试覆盖范围:**

| 测试类 | 测试内容 | 测试数量 |
|--------|---------|---------|
| TestValidationService | 验证服务 | 10+ |
| TestRefusalService | 拒绝检测 | 7 |
| TestFieldSkipService | 字段跳过 | 8 |
| TestPhoneValidator | 手机号验证器 | 5 |
| TestWeChatValidator | 微信号验证器 | 5 |
| TestEmailValidator | 邮箱验证器 | 5 |
| TestUserProfile | 用户资料模型 | 3 |
| TestMemoryUserProfileRepository | 用户仓储 | 6 |
| TestErrorHandler | 错误处理 | 4 |
| TestStructuredLogging | 结构化日志 | 2 |
| TestMemoryCache | 内存缓存 | 4 |
| TestMemoryQueue | 内存队列 | 2 |
| TestTieredRateLimiter | 分级限流 | 5 |

**运行单元测试:**

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试类
pytest tests/unit/test_services.py::TestValidationService -v

# 运行特定测试方法
pytest tests/unit/test_services.py::TestValidationService::test_validate_phone_valid -v
```

### 2. 性能测试 (`tests/performance/test_load.py`)

**测试覆盖范围:**

| 测试类 | 测试内容 |
|--------|---------|
| TestConcurrentRequests | 并发请求测试 |
| TestResponseTimeBenchmarks | 响应时间基准 |
| TestMemoryUsage | 内存使用测试 |
| TestCachePerformance | 缓存性能 |
| TestLoadTesting | 负载测试 |
| TestStressTesting | 压力测试 |

**运行性能测试:**

```bash
# 运行所有性能测试
pytest tests/performance/ -v -s

# 运行特定性能测试
pytest tests/performance/test_load.py::TestConcurrentRequests -v -s

# 运行带性能标记的测试
pytest -m performance -v -s
```

---

## 测试命令

### 基础命令

```bash
# 显示详细输出
pytest -v

# 显示print输出
pytest -s

# 显示更短的traceback
pytest --tb=short

# 遇到第一个失败停止
pytest -x

# 运行上次失败的测试
pytest --lf

# 运行所有测试但先运行上次失败的
pytest --ff
```

### 覆盖率报告

```bash
# 终端覆盖率报告
pytest --cov=src --cov-report=term

# HTML覆盖率报告
pytest --cov=src --cov-report=html

# 分支覆盖率
pytest --cov=src --cov-branch

# XML覆盖率（用于CI）
pytest --cov=src --cov-report=xml
```

### 按标记运行

```bash
# 运行单元测试
pytest -m unit

# 运行性能测试
pytest -m performance

# 跳过慢速测试
pytest -m "not slow"

# 运行需要Redis的测试
pytest -m redis
```

---

## 编写测试

### 单元测试示例

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestMyService:
    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        return MyService()

    @pytest.mark.asyncio
    async def test_async_method(self, service):
        """测试异步方法"""
        result = await service.async_method()
        assert result == expected

    def test_sync_method(self, service):
        """测试同步方法"""
        result = service.sync_method()
        assert result == expected
```

### 性能测试示例

```python
@pytest.mark.asyncio
async def test_concurrent_operations():
    """测试并发操作性能"""
    service = MyService()

    # 并发执行
    tasks = [service.method() for _ in range(1000)]
    results = await asyncio.gather(*tasks)

    # 性能断言
    assert len(results) == 1000
    assert execution_time < 1000  # 1秒内完成
```

---

## 测试最佳实践

### 1. 使用 Fixture

```python
@pytest.fixture
async def mock_redis():
    """Mock Redis服务"""
    mock = AsyncMock()
    mock.get.return_value = "value"
    yield mock
    # 清理代码
```

### 2. Mock 外部依赖

```python
@patch('src.services.my_service.redis_service')
async def test_with_mock(mock_redis):
    mock_redis.get.return_value = "mocked_value"
    result = await my_function()
    assert result == "expected"
```

### 3. 测试异常情况

```python
@pytest.mark.asyncio
async def test_error_handling():
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("错误信息")
    assert exc_info.value.message == "错误信息"
```

### 4. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("13800138000", True),
    ("12345678901", False),
    ("invalid", False),
])
def test_phone_validation(input, expected):
    result = PhoneValidator.is_valid(input)
    assert result == expected
```

---

## 性能基准

### 目标性能指标

| 操作 | 目标响应时间 | P95 | P99 |
|------|-------------|-----|-----|
| 手机号验证 | < 10ms | < 20ms | < 50ms |
| 缓存读取 | < 1ms | < 2ms | < 5ms |
| 缓存写入 | < 1ms | < 2ms | < 5ms |
| AI调用 | < 30s | < 35s | < 40s |

### 并发性能目标

| 场景 | 并发数 | 目标QPS | 平均响应时间 |
|------|--------|---------|-------------|
| 正常负载 | 100 | 1000+ | < 100ms |
| 高负载 | 500 | 5000+ | < 200ms |
| 突发流量 | 1000 | 10000+ | < 500ms |

---

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 常见问题

### 1. Redis 连接失败

**问题**: 测试中需要Redis但未启动

**解决**:
```bash
# 启动Redis
docker run -d -p 6379:6379 redis:alpine

# 或跳过Redis测试
pytest -m "not redis"
```

### 2. AI服务测试失败

**问题**: AI服务需要API密钥

**解决**:
```bash
# 设置环境变量
export ARK_API_KEY=your_key_here

# 或Mock AI服务
pytest -m "not ai"
```

### 3. 内存泄漏测试

**问题**: 测试中发现内存增长

**排查**:
```bash
# 使用内存分析工具
pip install memory_profiler
pytest --memprof
```

---

## 测试覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|---------|
| 验证服务 | 90%+ | 待测试 |
| 拒绝检测 | 90%+ | 待测试 |
| 字段跳过 | 90%+ | 待测试 |
| 缓存 | 85%+ | 待测试 |
| 队列 | 85%+ | 待测试 |
| 限流 | 85%+ | 待测试 |
| 整体 | 80%+ | 待测试 |

---

## 有用的测试工具

```bash
# 安装额外工具
pip install pytest-xdist  # 并行测试
pip install pytest-benchmark  # 基准测试
pip install pytest-profiling  # 性能分析

# 并行运行测试（加快速度）
pytest -n auto

# 基准测试
pytest --benchmark-only

# 性能分析
pytest --profiling
```

---

## 更新日志

### 2026-02-06
- ✅ 创建单元测试框架
- ✅ 创建性能测试框架
- ✅ 配置pytest
- ✅ 添加测试依赖

---

**祝测试愉快！** 🧪
