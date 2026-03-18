"""
内存消息队列

用于异步任务处理，支持：
1. 后台任务执行
2. 任务重试机制
3. 任务状态追踪
"""

import asyncio
import logging
import traceback
from typing import Callable, Optional, Any, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MemoryQueue:
    """
    内存消息队列

    特性：
    1. 异步任务执行
    2. 自动重试机制
    3. 任务优先级
    4. 并发控制
    """

    def __init__(
        self,
        max_workers: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化队列

        Args:
            max_workers: 最大并发工作线程数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 任务队列
        self._pending_tasks: List[Task] = []
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}

        # 工作线程
        self._workers: List[asyncio.Task] = []
        self._running = False

        # 统计
        self._stats = {
            "total_tasks": 0,
            "success_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0
        }

    async def submit(
        self,
        name: str,
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        提交任务到队列

        Args:
            name: 任务名称
            func: 要执行的函数
            *args: 位置参数
            max_retries: 最大重试次数
            **kwargs: 关键字参数

        Returns:
            str: 任务ID
        """
        import uuid
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries or self.max_retries
        )

        self._pending_tasks.append(task)
        self._stats["total_tasks"] += 1

        logger.info(
            "任务已提交: %s (task_id=%s, pending=%d)",
            name,
            task_id,
            len(self._pending_tasks),
        )

        return task_id

    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            timeout: 等待超时（秒）

        Returns:
            Any: 任务结果

        Raises:
            asyncio.TimeoutError: 等待超时
            ValueError: 任务不存在
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # 检查任务是否完成
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                if task.status == TaskStatus.SUCCESS:
                    return task.result
                elif task.status == TaskStatus.FAILED:
                    raise Exception(f"任务失败: {task.error}")

            # 检查超时
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise asyncio.TimeoutError(f"等待任务结果超时: {timeout}秒")

            # 等待一段时间再检查
            await asyncio.sleep(0.1)

    async def start(self):
        """启动队列处理"""
        if self._running:
            return

        self._running = True
        logger.info(f"启动消息队列，工作线程数: {self.max_workers}")

        # 创建工作线程
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker(i))
            self._workers.append(worker_task)

    async def stop(self):
        """停止队列处理"""
        if not self._running:
            return

        self._running = False

        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()

        # 等待所有工作线程完成
        await asyncio.gather(*self._workers, return_exceptions=True)

        logger.info("消息队列已停止")

    async def _worker(self, worker_id: int):
        """
        工作线程

        Args:
            worker_id: 工作线程ID
        """
        logger.info(f"工作线程 {worker_id} 已启动")

        while self._running:
            try:
                # 获取下一个任务
                task = await self._get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue

                # 执行任务
                await self._execute_task(task, worker_id)

            except asyncio.CancelledError:
                logger.info(f"工作线程 {worker_id} 已取消")
                break
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 异常: {e}")
                await asyncio.sleep(1)

    async def _get_next_task(self) -> Optional[Task]:
        """获取下一个待处理任务"""
        if not self._pending_tasks:
            return None

        # 获取第一个任务
        task = self._pending_tasks.pop(0)
        return task

    async def _execute_task(self, task: Task, worker_id: int):
        """
        执行任务

        Args:
            task: 任务对象
            worker_id: 工作线程ID
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self._running_tasks[task.id] = task

        logger.info(
            "开始执行任务: %s (task_id=%s, worker_id=%d)",
            task.name,
            task.id,
            worker_id,
        )

        try:
            # 执行函数
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)

            # 成功
            task.status = TaskStatus.SUCCESS
            task.result = result
            self._stats["success_tasks"] += 1

            logger.info(
                "任务完成: %s (task_id=%s, worker_id=%d)",
                task.name,
                task.id,
                worker_id,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"任务执行失败: {task.name}, 错误: {error_msg}")

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRY
                task.retry_count += 1
                task.error = error_msg

                # 延迟后重试
                await asyncio.sleep(self.retry_delay * (2 ** task.retry_count))

                # 重新加入队列
                self._pending_tasks.append(task)
                self._stats["retried_tasks"] += 1

                logger.info(
                    "任务重试: %s (task_id=%s, retry_count=%d)",
                    task.name,
                    task.id,
                    task.retry_count,
                )
            else:
                # 重试次数用尽，标记为失败
                task.status = TaskStatus.FAILED
                task.error = error_msg
                self._stats["failed_tasks"] += 1

                logger.error(
                    "任务失败（已达最大重试次数）: %s (task_id=%s, error=%s)",
                    task.name,
                    task.id,
                    error_msg,
                )

        finally:
            task.completed_at = datetime.utcnow()
            # 从运行中移到已完成
            self._running_tasks.pop(task.id, None)
            self._completed_tasks[task.id] = task

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            "pending": len(self._pending_tasks),
            "running": len(self._running_tasks),
            "completed": len(self._completed_tasks),
            "stats": self._stats.copy(),
            "is_running": self._running
        }


# 全局队列实例
task_queue = MemoryQueue()
