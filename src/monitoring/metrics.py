"""
指标收集器

提供四种标准指标类型：Counter, Gauge, Histogram, Summary
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 指标类型
# ============================================================================

class MetricType:
    """指标类型"""
    COUNTER = "counter"    # 计数器（只增不减）
    GAUGE = "gauge"        # 仪表盘（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布统计）
    SUMMARY = "summary"    # 摘要（分位数统计）


# ============================================================================
# 指标标签
# ============================================================================

@dataclass
class LabelSet:
    """
    标签集合

    用于给指标添加维度标签
    """
    labels: Dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ", ".join(parts) + "}"

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.labels.items())))

    def __eq__(self, other) -> bool:
        if not isinstance(other, LabelSet):
            return False
        return self.labels == other.labels


# ============================================================================
# 指标基类
# ============================================================================

class Metric:
    """
    指标基类

    所有指标的父类
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ):
        """
        初始化指标

        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签名称列表
        """
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._created_at = time.time()
        self._lock = threading.RLock()

    def get_type(self) -> str:
        """获取指标类型"""
        raise NotImplementedError

    def get_value(self, labels: LabelSet = None) -> Any:
        """获取指标值"""
        raise NotImplementedError

    def reset(self):
        """重置指标"""
        raise NotImplementedError


# ============================================================================
# Counter 计数器
# ============================================================================

class Counter(Metric):
    """
    计数器

    只能递增的数值，用于记录事件发生次数
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ):
        super().__init__(name, description, labels)
        self._values: Dict[LabelSet, float] = defaultdict(float)

    def get_type(self) -> str:
        return MetricType.COUNTER

    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """
        增加计数

        Args:
            value: 增加的值（必须 >= 0）
            labels: 标签字典
        """
        if value < 0:
            raise ValueError(f"Counter 只能增加非负值，收到: {value}")

        label_set = LabelSet(labels or {})
        with self._lock:
            self._values[label_set] += value

    def get_value(self, labels: LabelSet = None) -> float:
        """
        获取计数值

        Args:
            labels: 标签集合

        Returns:
            当前计数值
        """
        label_set = labels or LabelSet()
        return self._values.get(label_set, 0)

    def get_all_values(self) -> Dict[LabelSet, float]:
        """获取所有标签组合的值"""
        return dict(self._values)

    def reset(self):
        """重置所有计数"""
        with self._lock:
            self._values.clear()


# ============================================================================
# Gauge 仪表盘
# ============================================================================

class Gauge(Metric):
    """
    仪表盘

    可以增减的数值，用于记录当前状态
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ):
        super().__init__(name, description, labels)
        self._values: Dict[LabelSet, float] = {}

    def get_type(self) -> str:
        return MetricType.GAUGE

    def set(self, value: float, labels: Dict[str, str] = None):
        """
        设置值

        Args:
            value: 要设置的值
            labels: 标签字典
        """
        label_set = LabelSet(labels or {})
        with self._lock:
            self._values[label_set] = value

    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """增加值"""
        label_set = LabelSet(labels or {})
        with self._lock:
            self._values[label_set] = self._values.get(label_set, 0) + value

    def dec(self, value: float = 1.0, labels: Dict[str, str] = None):
        """减少值"""
        label_set = LabelSet(labels or {})
        with self._lock:
            current = self._values.get(label_set, 0)
            self._values[label_set] = current - value

    def get_value(self, labels: LabelSet = None) -> Optional[float]:
        """获取值"""
        label_set = labels or LabelSet()
        return self._values.get(label_set)

    def get_all_values(self) -> Dict[LabelSet, float]:
        """获取所有标签组合的值"""
        return dict(self._values)

    def reset(self):
        """重置所有值"""
        with self._lock:
            self._values.clear()


# ============================================================================
# Histogram 直方图
# ============================================================================

class Histogram(Metric):
    """
    直方图

    记录值的分布情况，用于统计响应时间等
    """

    # 默认桶边界
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

    def __init__(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None
    ):
        super().__init__(name, description, labels)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._counts: Dict[LabelSet, List[float]] = defaultdict(list)
        self._sums: Dict[LabelSet, float] = defaultdict(float)

    def get_type(self) -> str:
        return MetricType.HISTOGRAM

    def observe(self, value: float, labels: Dict[str, str] = None):
        """
        观察一个值

        Args:
            value: 要观察的值
            labels: 标签字典
        """
        if value < 0:
            raise ValueError(f"Histogram 值必须非负，收到: {value}")

        label_set = LabelSet(labels or {})
        with self._lock:
            self._counts[label_set].append(value)
            self._sums[label_set] += value

    def get_value(self, labels: LabelSet = None) -> Dict[str, Any]:
        """
        获取直方图统计

        Returns:
            包含 count, sum, bucket 统计的字典
        """
        label_set = labels or LabelSet()
        values = self._counts.get(label_set, [])

        # 计算桶统计
        bucket_counts = {}
        for bucket in self.buckets:
            count = sum(1 for v in values if v <= bucket)
            bucket_counts[str(bucket)] = count

        # +Inf 桶
        bucket_counts["+Inf"] = len(values)

        return {
            "count": len(values),
            "sum": self._sums.get(label_set, 0),
            "buckets": bucket_counts
        }

    def get_all_values(self) -> Dict[LabelSet, Dict[str, Any]]:
        """获取所有标签组合的统计"""
        result = {}
        for label_set in self._counts.keys():
            result[label_set] = self.get_value(label_set)
        return result

    def reset(self):
        """重置所有统计"""
        with self._lock:
            self._counts.clear()
            self._sums.clear()


# ============================================================================
# Summary 摘要
# ============================================================================

class Summary(Metric):
    """
    摘要

    记录值的分位数统计
    """

    DEFAULT_OBJECTIVES = [0.5, 0.9, 0.95, 0.99]

    def __init__(
        self,
        name: str,
        description: str,
        objectives: Optional[List[float]] = None,
        labels: Optional[List[str]] = None
    ):
        super().__init__(name, description, labels)
        self.objectives = sorted(objectives or self.DEFAULT_OBJECTIVES)
        self._values: Dict[LabelSet, List[float]] = defaultdict(list)

    def get_type(self) -> str:
        return MetricType.SUMMARY

    def observe(self, value: float, labels: Dict[str, str] = None):
        """
        观察一个值

        Args:
            value: 要观察的值
            labels: 标签字典
        """
        if value < 0:
            raise ValueError(f"Summary 值必须非负，收到: {value}")

        label_set = LabelSet(labels or {})
        with self._lock:
            self._values[label_set].append(value)

    def get_value(self, labels: LabelSet = None) -> Dict[str, Any]:
        """
        获取摘要统计

        Returns:
            包含 count, sum, quantiles 的字典
        """
        label_set = labels or LabelSet()
        values = sorted(self._values.get(label_set, []))

        if not values:
            return {
                "count": 0,
                "sum": 0,
                "quantiles": {}
            }

        # 计算分位数
        quantiles = {}
        for q in self.objectives:
            index = int(q * len(values))
            if index >= len(values):
                index = len(values) - 1
            quantiles[str(q)] = values[index]

        return {
            "count": len(values),
            "sum": sum(values),
            "quantiles": quantiles
        }

    def get_all_values(self) -> Dict[LabelSet, Dict[str, Any]]:
        """获取所有标签组合的统计"""
        result = {}
        for label_set in self._values.keys():
            result[label_set] = self.get_value(label_set)
        return result

    def reset(self):
        """重置所有统计"""
        with self._lock:
            self._values.clear()


# ============================================================================
# 指标注册表
# ============================================================================

class MetricRegistry:
    """
    指标注册表

    管理所有指标的注册和查询
    """

    def __init__(self):
        """初始化注册表"""
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.RLock()

    def register(self, metric: Metric) -> bool:
        """
        注册指标

        Args:
            metric: 指标实例

        Returns:
            是否注册成功
        """
        with self._lock:
            if metric.name in self._metrics:
                logger.warning(f"指标已存在: {metric.name}")
                return False

            self._metrics[metric.name] = metric
            logger.info(f"注册指标: {metric.name} ({metric.get_type()})")
            return True

    def unregister(self, name: str) -> bool:
        """
        取消注册指标

        Args:
            name: 指标名称

        Returns:
            是否取消成功
        """
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                logger.info(f"取消注册指标: {name}")
                return True
            return False

    def get(self, name: str) -> Optional[Metric]:
        """获取指标"""
        return self._metrics.get(name)

    def get_all(self) -> Dict[str, Metric]:
        """获取所有指标"""
        return dict(self._metrics)

    def get_by_type(self, metric_type: str) -> List[Metric]:
        """获取指定类型的所有指标"""
        return [
            m for m in self._metrics.values()
            if m.get_type() == metric_type
        ]

    def clear(self):
        """清空所有指标"""
        with self._lock:
            for metric in self._metrics.values():
                metric.reset()
            logger.info("清空所有指标")


# ============================================================================
# 全局默认注册表
# ============================================================================

# 默认指标注册表
default_registry = MetricRegistry()


# ============================================================================
# 便捷函数
# ============================================================================

def counter(
    name: str,
    description: str,
    labels: Optional[List[str]] = None,
    registry: MetricRegistry = None
) -> Counter:
    """
    创建并注册计数器

    Usage:
        requests_total = counter("requests_total", "总请求数")
        requests_total.inc(labels={"endpoint": "/api/users"})
    """
    metric = Counter(name, description, labels)
    (registry or default_registry).register(metric)
    return metric


def gauge(
    name: str,
    description: str,
    labels: Optional[List[str]] = None,
    registry: MetricRegistry = None
) -> Gauge:
    """
    创建并注册仪表盘

    Usage:
        active_connections = gauge("active_connections", "活跃连接数")
        active_connections.set(10)
    """
    metric = Gauge(name, description, labels)
    (registry or default_registry).register(metric)
    return metric


def histogram(
    name: str,
    description: str,
    buckets: Optional[List[float]] = None,
    labels: Optional[List[str]] = None,
    registry: MetricRegistry = None
) -> Histogram:
    """
    创建并注册直方图

    Usage:
        request_duration = histogram("request_duration", "请求耗时")
        request_duration.observe(0.123)
    """
    metric = Histogram(name, description, buckets, labels)
    (registry or default_registry).register(metric)
    return metric


def summary(
    name: str,
    description: str,
    objectives: Optional[List[float]] = None,
    labels: Optional[List[str]] = None,
    registry: MetricRegistry = None
) -> Summary:
    """
    创建并注册摘要

    Usage:
        response_size = summary("response_size", "响应大小")
        response_size.observe(1024)
    """
    metric = Summary(name, description, objectives, labels)
    (registry or default_registry).register(metric)
    return metric
