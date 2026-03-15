"""
性能测试和负载测试

测试覆盖:
- 并发请求测试
- 响应时间基准测试
- 内存使用测试
- 缓存性能测试
- Redis连接池测试
- API端点负载测试
"""

import pytest
import asyncio
import time
import psutil
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from src.infrastructure.cache import MemoryCache, RedisCache, HybridCache
from src.infrastructure.queue import MemoryQueue
from src.api.middleware.tiered_rate_limit import TieredRateLimiter
from src.services.data.validation_service import ValidationService


# ============================================================================
# 性能测试配置
# ============================================================================

PERFORMANCE_CONFIG = {
    "concurrent_users": [10, 50, 100, 200],
    "requests_per_user": 10,
    "target_response_time_ms": 2000,
    "target_memory_mb": 500,
    "cache_size": 1000,
    "queue_workers": 10,
}


# ============================================================================
# 辅助函数
# ============================================================================

def get_memory_usage_mb() -> float:
    """获取当前进程内存使用量（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


async def measure_response_time(func, *args, **kwargs) -> float:
    """测量函数执行时间（毫秒）"""
    start_time = time.perf_counter()
    result = await func(*args, **kwargs)
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000


# ============================================================================
# 并发请求测试
# ============================================================================

class TestConcurrentRequests:
    """并发请求测试"""

    @pytest.mark.asyncio
    async def test_concurrent_validation(self):
        """测试并发验证请求"""
        validation_svc = ValidationService()
        phone_numbers = [f"138{str(i).zfill(8)}" for i in range(1000)]

        # 记录开始时间和内存
        start_time = time.perf_counter()
        start_memory = get_memory_usage_mb()

        # 并发执行1000次验证
        tasks = [validation_svc.validate_phone(phone) for phone in phone_numbers]
        results = await asyncio.gather(*tasks)

        # 计算执行时间
        end_time = time.perf_counter()
        end_memory = get_memory_usage_mb()
        total_time = (end_time - start_time) * 1000  # 毫秒

        # 验证结果
        assert len(results) == 1000
        assert total_time < PERFORMANCE_CONFIG["target_response_time_ms"] * 5  # 1000个请求
        memory_increase = end_memory - start_memory
        assert memory_increase < PERFORMANCE_CONFIG["target_memory_mb"]

        print(f"并发验证1000个手机号:")
        print(f"  总耗时: {total_time:.2f}ms")
        print(f"  平均耗时: {total_time / 1000:.2f}ms")
        print(f"  内存增长: {memory_increase:.2f}MB")

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """测试并发缓存操作"""
        cache = MemoryCache(max_size=10000, ttl=60)

        # 并发写入
        start_time = time.perf_counter()
        write_tasks = [cache.set(f"key_{i}", f"value_{i}") for i in range(1000)]
        await asyncio.gather(*write_tasks)
        write_time = (time.perf_counter() - start_time) * 1000

        # 并发读取
        start_time = time.perf_counter()
        read_tasks = [cache.get(f"key_{i}") for i in range(1000)]
        results = await asyncio.gather(*read_tasks)
        read_time = (time.perf_counter() - start_time) * 1000

        # 验证结果
        assert len([r for r in results if r is not None]) == 1000
        assert write_time < 1000  # 写入应在1秒内完成
        assert read_time < 500  # 读取应在0.5秒内完成

        print(f"并发缓存操作:")
        print(f"  写入1000个键值对: {write_time:.2f}ms")
        print(f"  平均写入耗时: {write_time / 1000:.2f}ms")
        print(f"  读取1000个键: {read_time:.2f}ms")
        print(f"  平均读取耗时: {read_time / 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_concurrent_queue_tasks(self):
        """测试并发队列任务"""
        queue = MemoryQueue(max_workers=10)
        await queue.start()

        async def dummy_task(task_id: int):
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            return f"result_{task_id}"

        # 提交100个任务
        start_time = time.perf_counter()
        task_ids = [await queue.submit(f"task_{i}", dummy_task, i) for i in range(100)]

        # 等待所有任务完成
        await asyncio.sleep(1)  # 给足够时间完成

        # 检查结果
        completed_count = 0
        for task_id in task_ids:
            try:
                result = await queue.get_task_result(task_id, timeout=0.1)
                if result:
                    completed_count += 1
            except:
                pass

        total_time = (time.perf_counter() - start_time) * 1000

        await queue.stop()

        # 验证至少完成90%的任务
        assert completed_count >= 90
        assert total_time < 2000  # 应在2秒内完成

        print(f"并发队列任务:")
        print(f"  提交100个任务")
        print(f"  完成{completed_count}个任务")
        print(f"  总耗时: {total_time:.2f}ms")


# ============================================================================
# 响应时间基准测试
# ============================================================================

class TestResponseTimeBenchmarks:
    """响应时间基准测试"""

    @pytest.mark.asyncio
    async def test_validation_service_benchmark(self):
        """验证服务性能基准"""
        validation_svc = ValidationService()

        # 预热
        for _ in range(100):
            await validation_svc.validate_phone("13800138000")

        # 测试1000次
        times = []
        for _ in range(1000):
            time_ms = await measure_response_time(
                validation_svc.validate_phone,
                "13800138000"
            )
            times.append(time_ms)

        # 统计分析
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        p99_time = statistics.quantiles(times, n=100)[98]  # 99th percentile

        print(f"验证服务性能基准 (1000次):")
        print(f"  平均: {avg_time:.2f}ms")
        print(f"  中位数: {median_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        print(f"  P99: {p99_time:.2f}ms")

        # 性能断言
        assert avg_time < 10  # 平均应在10ms内
        assert p95_time < 20  # 95%请求应在20ms内
        assert p99_time < 50  # 99%请求应在50ms内

    @pytest.mark.asyncio
    async def test_cache_benchmark(self):
        """缓存性能基准"""
        cache = MemoryCache(max_size=10000, ttl=60)

        # 预热缓存
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        # 测试写入性能
        write_times = []
        for i in range(1000):
            time_ms = await measure_response_time(
                cache.set,
                f"bench_key_{i}",
                f"bench_value_{i}"
            )
            write_times.append(time_ms)

        # 测试读取性能
        read_times = []
        for i in range(1000):
            time_ms = await measure_response_time(
                cache.get,
                f"bench_key_{i}"
            )
            read_times.append(time_ms)

        # 统计分析
        avg_write = statistics.mean(write_times)
        avg_read = statistics.mean(read_times)
        p95_write = statistics.quantiles(write_times, n=20)[18]
        p95_read = statistics.quantiles(read_times, n=20)[18]

        print(f"缓存性能基准 (1000次):")
        print(f"  写入 - 平均: {avg_write:.2f}ms, P95: {p95_write:.2f}ms")
        print(f"  读取 - 平均: {avg_read:.2f}ms, P95: {p95_read:.2f}ms")

        # 性能断言
        assert avg_write < 1  # 写入应在1ms内
        assert avg_read < 1  # 读取应在1ms内


# ============================================================================
# 内存使用测试
# ============================================================================

class TestMemoryUsage:
    """内存使用测试"""

    @pytest.mark.asyncio
    async def test_cache_memory_usage(self):
        """测试缓存内存使用"""
        initial_memory = get_memory_usage_mb()

        # 创建大容量缓存
        cache = MemoryCache(max_size=100000, ttl=3600)

        # 写入大量数据
        for i in range(10000):
            await cache.set(f"key_{i}", f"value_data_{i}" * 10)  # 约100字节/条

        final_memory = get_memory_usage_mb()
        memory_increase = final_memory - initial_memory

        print(f"缓存内存使用:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  增长: {memory_increase:.2f}MB")
        print(f"  每条数据平均: {memory_increase * 1024 / 10000:.2f}KB")

        # 内存增长应合理（10000条约1MB数据 + 开销）
        assert memory_increase < 100  # 应小于100MB

    @pytest.mark.asyncio
    async def test_queue_memory_usage(self):
        """测试队列内存使用"""
        initial_memory = get_memory_usage_mb()

        queue = MemoryQueue(max_workers=10)
        await queue.start()

        # 提交大量任务
        async def dummy_task(x):
            return x * 2

        for i in range(1000):
            await queue.submit("task", dummy_task, i)

        # 等待部分完成
        await asyncio.sleep(0.5)

        final_memory = get_memory_usage_mb()
        memory_increase = final_memory - initial_memory

        await queue.stop()

        print(f"队列内存使用:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  增长: {memory_increase:.2f}MB")

        # 内存增长应合理
        assert memory_increase < 50  # 应小于50MB


# ============================================================================
# 缓存性能测试
# ============================================================================

class TestCachePerformance:
    """缓存性能测试"""

    @pytest.mark.asyncio
    async def test_lru_eviction_performance(self):
        """测试LRU淘汰性能"""
        cache = MemoryCache(max_size=100, ttl=60)

        # 写入超过容量的数据，触发淘汰
        start_time = time.perf_counter()
        for i in range(1000):
            await cache.set(f"key_{i}", f"value_{i}")
        eviction_time = (time.perf_counter() - start_time) * 1000

        # 验证缓存大小
        stats = cache.get_stats()
        assert stats["size"] <= 100  # 不应超过最大容量

        print(f"LRU淘汰性能:")
        print(f"  写入1000条数据（容量100）: {eviction_time:.2f}ms")
        print(f"  平均每次操作: {eviction_time / 1000:.2f}ms")
        print(f"  最终缓存大小: {stats['size']}")

        # 淘汰性能应足够快
        assert eviction_time < 5000  # 应在5秒内完成

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self):
        """测试缓存命中率"""
        cache = MemoryCache(max_size=1000, ttl=60)

        # 预填充缓存
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        # 模拟访问模式：80%命中缓存，20%未命中
        import random
        hits = 0
        misses = 0

        for _ in range(1000):
            if random.random() < 0.8:  # 80%访问已有缓存
                key = f"key_{random.randint(0, 99)}"
            else:  # 20%访问新键
                key = f"new_key_{random.randint(0, 999)}"

            result = await cache.get(key)
            if result is not None:
                hits += 1
            else:
                misses += 1

        hit_rate = hits / (hits + misses) * 100

        print(f"缓存命中率:")
        print(f"  命中: {hits}")
        print(f"  未命中: {misses}")
        print(f"  命中率: {hit_rate:.2f}%")

        # 命中率应接近预期
        assert hit_rate > 70  # 至少70%命中率


# ============================================================================
# 负载测试
# ============================================================================

class TestLoadTesting:
    """负载测试"""

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """测试持续负载"""
        validation_svc = ValidationService()
        duration_seconds = 10
        requests_per_second = 100

        total_requests = 0
        errors = 0
        response_times = []

        async def send_requests():
            nonlocal total_requests, errors
            while True:
                try:
                    start = time.perf_counter()
                    await validation_svc.validate_phone("13800138000")
                    response_times.append((time.perf_counter() - start) * 1000)
                    total_requests += 1
                except Exception as e:
                    errors += 1
                await asyncio.sleep(1 / requests_per_second)

        # 启动多个并发请求器
        tasks = [asyncio.create_task(send_requests()) for _ in range(10)]

        # 运行指定时长
        await asyncio.sleep(duration_seconds)

        # 停止所有任务
        for task in tasks:
            task.cancel()

        # 等待取消完成
        await asyncio.gather(*tasks, return_exceptions=True)

        # 计算统计
        actual_rps = total_requests / duration_seconds
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0

        print(f"持续负载测试 ({duration_seconds}秒, 目标{requests_per_second} RPS):")
        print(f"  实际RPS: {actual_rps:.2f}")
        print(f"  总请求数: {total_requests}")
        print(f"  错误数: {errors}")
        print(f"  平均响应时间: {avg_response_time:.2f}ms")
        print(f"  P95响应时间: {p95_response_time:.2f}ms")

        # 性能断言
        assert actual_rps >= requests_per_second * 0.9  # 至少90%目标RPS
        assert errors == 0  # 不应有错误
        assert p95_response_time < 100  # 95%请求应在100ms内

    @pytest.mark.asyncio
    async def test_spike_load(self):
        """测试突发负载"""
        cache = MemoryCache(max_size=10000, ttl=60)

        # 模拟突发流量：短时间内大量请求
        spike_sizes = [100, 500, 1000]

        for spike_size in spike_sizes:
            start_time = time.perf_counter()
            start_memory = get_memory_usage_mb()

            # 突发写入
            tasks = [cache.set(f"spike_{i}_{time.time()}", f"value_{i}") for i in range(spike_size)]
            await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            end_memory = get_memory_usage_mb()

            duration_ms = (end_time - start_time) * 1000
            memory_increase = end_memory - start_memory
            rps = spike_size / (duration_ms / 1000)

            print(f"突发负载测试 ({spike_size}个请求):")
            print(f"  耗时: {duration_ms:.2f}ms")
            print(f"  RPS: {rps:.2f}")
            print(f"  内存增长: {memory_increase:.2f}MB")

            # 性能断言
            assert duration_ms < spike_size * 2  # 每个请求应在2ms内
            assert rps > 500  # 至少500 RPS


# ============================================================================
# 压力测试
# ============================================================================

class TestStressTesting:
    """压力测试"""

    @pytest.mark.asyncio
    async def test_max_capacity(self):
        """测试最大容量"""
        cache = MemoryCache(max_size=100000, ttl=60)

        # 持续写入直到接近或达到容量上限
        try:
            for i in range(200000):
                await cache.set(f"stress_key_{i}", f"value_{i}")
                if i % 10000 == 0:
                    stats = cache.get_stats()
                    print(f"已写入{i}条，缓存大小: {stats['size']}")
        except Exception as e:
            print(f"在{i}条时出错: {e}")

        stats = cache.get_stats()
        print(f"最大容量测试:")
        print(f"  最终缓存大小: {stats['size']}")
        print(f"  最大容量: 100000")

        # 缓存大小应不超过最大容量
        assert stats['size'] <= 100000

    @pytest.mark.asyncio
    async def test_memory_pressure(self):
        """测试内存压力"""
        cache = MemoryCache(max_size=100000, ttl=60)

        initial_memory = get_memory_usage_mb()
        large_value = "x" * 10000  # 10KB数据

        # 写入大量大对象
        for i in range(5000):
            await cache.set(f"large_key_{i}", large_value)
            if i % 1000 == 0:
                current_memory = get_memory_usage_mb()
                memory_increase = current_memory - initial_memory
                print(f"已写入{i}条大对象，内存增长: {memory_increase:.2f}MB")

                # 如果内存增长过快，停止测试
                if memory_increase > 200:
                    print(f"内存增长超过200MB，停止测试")
                    break

        final_memory = get_memory_usage_mb()
        memory_increase = final_memory - initial_memory

        print(f"内存压力测试:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  增长: {memory_increase:.2f}MB")

        # 内存增长应在合理范围内
        assert memory_increase < 300  # 应小于300MB


# ============================================================================
# 运行配置
# ============================================================================

def pytest_configure(config):
    """Pytest配置"""
    config.addinivalue_line(
        "markers", "performance: 标记性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([
        __file__,
        "-v",
        "-s",  # 显示print输出
        "-m", "performance",
        "--tb=short"
    ])
