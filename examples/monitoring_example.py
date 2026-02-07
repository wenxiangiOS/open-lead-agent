"""
监控系统使用示例

演示如何使用指标收集、健康检查和告警功能
"""

import asyncio
import time
import random
from typing import Dict, Any

from src.monitoring import (
    # 指标
    counter, gauge, histogram, summary,
    # 健康检查
    HealthCheckManager, HealthStatus,
    create_database_check, create_redis_check, create_disk_space_check,
    # 告警
    AlertManager, AlertSeverity, AlertRule,
    create_threshold_rule,
)


# ============================================================================
# 示例：API 服务监控
# ============================================================================

class APIServiceMonitor:
    """
    API 服务监控示例

    演示如何监控一个 API 服务
    """

    def __init__(self):
        """初始化监控"""

        # 创建指标
        self.request_count = counter(
            "api_requests_total",
            "API 总请求数",
            labels=["method", "endpoint", "status"]
        )

        self.request_duration = histogram(
            "api_request_duration_seconds",
            "API 请求耗时",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
            labels=["endpoint"]
        )

        self.active_connections = gauge(
            "api_active_connections",
            "活跃连接数"
        )

        self.response_size = summary(
            "api_response_size_bytes",
            "API 响应大小"
        )

        # 创建健康检查管理器
        self.health_manager = HealthCheckManager()

        # 注册健康检查
        self.health_manager.register(
            "api_liveness",
            self._check_liveness,
            critical=True
        )

        self.health_manager.register(
            "api_readiness",
            self._check_readiness,
            critical=True
        )

        # 创建告警管理器
        self.alert_manager = AlertManager()

        # 添加告警规则
        self.alert_manager.add_rule(create_threshold_rule(
            name="high_error_rate",
            metric_value_getter=lambda: self._get_error_rate(),
            threshold=0.05,
            operator="gt",
            severity=AlertSeverity.ERROR
        ))

        self.alert_manager.add_rule(create_threshold_rule(
            name="high_latency",
            metric_value_getter=lambda: self._get_avg_latency(),
            threshold=1.0,
            operator="gt",
            severity=AlertSeverity.WARNING
        ))

        # 服务状态
        self._is_ready = True
        self._is_healthy = True
        self._total_requests = 0
        self._failed_requests = 0
        self._latencies = []

    # ========================================================================
    # 指标记录
    # ========================================================================

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        response_size: int
    ):
        """记录 API 请求"""
        # 更新计数
        self._total_requests += 1
        if status_code >= 400:
            self._failed_requests += 1

        # 记录指标
        self.request_count.inc(
            labels={
                "method": method,
                "endpoint": endpoint,
                "status": "success" if status_code < 400 else "error"
            }
        )

        self.request_duration.observe(
            duration,
            labels={"endpoint": endpoint}
        )

        self.response_size.observe(response_size)

        # 记录延迟用于告警
        self._latencies.append(duration)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-50:]

    # ========================================================================
    # 连接管理
    # ========================================================================

    def connection_opened(self):
        """连接打开"""
        self.active_connections.inc()

    def connection_closed(self):
        """连接关闭"""
        self.active_connections.dec()

    # ========================================================================
    # 健康检查
    # ========================================================================

    async def _check_liveness(self) -> bool:
        """存活检查"""
        return self._is_healthy

    async def _check_readiness(self) -> bool:
        """就绪检查"""
        return self._is_ready

    # ========================================================================
    # 告警辅助
    # ========================================================================

    def _get_error_rate(self) -> float:
        """获取错误率"""
        if self._total_requests == 0:
            return 0
        return self._failed_requests / self._total_requests

    def _get_avg_latency(self) -> float:
        """获取平均延迟"""
        if not self._latencies:
            return 0
        return sum(self._latencies) / len(self._latencies)

    # ========================================================================
    # 服务控制
    # ========================================================================

    def set_healthy(self, healthy: bool):
        """设置健康状态"""
        self._is_healthy = healthy

    def set_ready(self, ready: bool):
        """设置就绪状态"""
        self._is_ready = ready

    # ========================================================================
    # 监控接口
    # ========================================================================

    async def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "request_count": self.request_count.get_all_values(),
            "request_duration": self.request_duration.get_all_values(),
            "active_connections": self.active_connections.get_value(),
            "response_size": self.response_size.get_all_values(),
            "error_rate": self._get_error_rate(),
            "avg_latency": self._get_avg_latency()
        }

    async def get_health(self) -> Dict[str, Any]:
        """获取健康状态"""
        return await self.health_manager.get_health_status()

    async def check_alerts(self) -> list:
        """检查并返回告警"""
        return await self.alert_manager.evaluate_rules()


# ============================================================================
# 模拟 API 服务
# ============================================================================

async def simulate_api_service():
    """模拟 API 服务运行"""

    monitor = APIServiceMonitor()

    print("🚀 模拟 API 服务启动...\n")

    # 模拟运行 100 个请求
    for i in range(100):
        # 模拟连接打开
        monitor.connection_opened()

        # 模拟 API 请求
        method = random.choice(["GET", "POST", "PUT", "DELETE"])
        endpoint = random.choice(["/api/users", "/api/posts", "/api/comments"])
        status_code = random.choices(
            [200, 201, 400, 404, 500],
            weights=[70, 15, 8, 5, 2]
        )[0]

        # 模拟处理时间（大部分正常，偶尔很慢）
        if random.random() < 0.05:
            duration = random.uniform(1.5, 3.0)  # 偶尔很慢
        else:
            duration = random.uniform(0.01, 0.3)

        response_size = random.randint(100, 10000)

        # 记录请求
        monitor.record_request(method, endpoint, status_code, duration, response_size)

        # 模拟连接关闭
        monitor.connection_closed()

        # 每 20 个请求输出一次统计
        if (i + 1) % 20 == 0:
            print(f"📊 已处理 {i + 1} 个请求")

            # 获取指标
            metrics = await monitor.get_metrics()
            print(f"  - 总请求数: {sum(metrics['request_count'].values())}")
            print(f"  - 错误率: {metrics['error_rate']:.2%}")
            print(f"  - 平均延迟: {metrics['avg_latency']:.3f}s")
            print(f"  - 活跃连接: {metrics['active_connections']}")

            # 检查告警
            alerts = await monitor.check_alerts()
            if alerts:
                print(f"\n🚨 触发告警:")
                for alert in alerts:
                    print(f"  - {alert.name}: {alert.message}")
                print()

        # 模拟处理时间
        await asyncio.sleep(0.01)

    # 模拟服务不健康
    print("\n⚠️  模拟服务不健康...")
    monitor.set_healthy(False)

    # 获取健康状态
    health = await monitor.get_health()
    print(f"健康状态: {health['status']}")
    print(f"检查项: {len(health['checks'])} 个")

    return monitor


# ============================================================================
# 主程序
# ============================================================================

async def main():
    """主程序"""

    print("\n" + "=" * 60)
    print("📊 监控系统示例")
    print("=" * 60 + "\n")

    # 运行模拟服务
    monitor = await simulate_api_service()

    print("\n" + "=" * 60)
    print("📈 监控仪表板")
    print("=" * 60 + "\n")

    # 显示最终指标
    metrics = await monitor.get_metrics()

    print("📊 指标统计:")
    print(f"  总请求数: {sum(metrics['request_count'].values())}")
    print(f"  错误率: {metrics['error_rate']:.2%}")
    print(f"  平均延迟: {metrics['avg_latency']:.3f}s")

    # 显示直方图
    duration_stats = metrics['request_duration'].get(LabelSet())
    if duration_stats:
        print(f"\n📊 请求延迟分布:")
        print(f"  总计: {duration_stats['count']} 次请求")
        print(f"  总耗时: {duration_stats['sum']:.3f}s")
        print(f"  桶统计:")
        for bucket, count in duration_stats['buckets'].items():
            pct = count / duration_stats['count'] * 100
            print(f"    ≤{bucket}s: {count} ({pct:.1f}%)")

    # 显示健康状态
    health = await monitor.get_health()
    print(f"\n🏥 健康状态:")
    print(f"  整体状态: {health['status']}")
    print(f"  检查项: {health['total_checks']} 个")
    print(f"  异常项: {health['unhealthy_count']} 个")

    for name, check in health['checks'].items():
        emoji = "✅" if check['status'] == "healthy" else "❌"
        print(f"  {emoji} {name}: {check['status']} ({check['duration_ms']:.1f}ms)")

    # 显示告警统计
    alert_stats = monitor.alert_manager.get_stats()
    print(f"\n🚨 告警统计:")
    print(f"  总告警数: {alert_stats['total_alerts']}")
    print(f"  活跃告警: {alert_stats['active_alerts']}")
    print(f"  规则数: {alert_stats['rules_count']}")

    # 显示活跃告警
    active_alerts = monitor.alert_manager.get_active_alerts()
    if active_alerts:
        print(f"\n  活跃告警:")
        for alert in active_alerts:
            print(f"    - [{alert.severity.value}] {alert.name}: {alert.message}")

    print("\n✅ 示例完成！")


# ============================================================================
# 辅助类
# ============================================================================

class LabelSet:
    """简单的标签集合"""
    def __init__(self, labels: Dict[str, str] = None):
        self.labels = labels or {}


if __name__ == "__main__":
    asyncio.run(main())
