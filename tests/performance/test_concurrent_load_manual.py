#!/usr/bin/env python3
"""
并发压测测试

测试并发模块在高并发场景下的表现
"""

import asyncio
import sys
import os
import time
from typing import List

# 确保可以导入 src 模块
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


async def test_concurrent_requests():
    """测试并发请求"""
    print("=" * 60)
    print("并发压测测试")
    print("=" * 60)

    from src.infrastructure.concurrency import get_concurrency_manager

    manager = get_concurrency_manager()
    print("✅ 并发管理器初始化成功")

    # 测试参数
    num_users = 10          # 模拟 10 个用户
    requests_per_user = 5   # 每个用户发送 5 个请求
    total_requests = num_users * requests_per_user

    print(f"\n📊 测试配置:")
    print(f"  - 用户数: {num_users}")
    print(f"  - 每用户请求数: {requests_per_user}")
    print(f"  - 总请求数: {total_requests}")

    # 记录结果
    success_count = 0
    rate_limited_count = 0
    error_count = 0
    results = []

    async def send_request(user_id: str, request_num: int):
        """发送单个请求"""
        try:
            # 检查限流
            result = await manager.check_user_rate_limit(user_id)

            if result.allowed:
                return {"user_id": user_id, "request": request_num, "status": "success", "remaining": result.remaining}
            else:
                return {"user_id": user_id, "request": request_num, "status": "rate_limited", "retry_after": result.reset_time}

        except Exception as e:
            return {"user_id": user_id, "request": request_num, "status": "error", "error": str(e)}

    # 并发发送请求
    print(f"\n🚀 开始并发测试...")
    start_time = time.time()

    tasks = []
    for user_num in range(num_users):
        user_id = f"test_user_{user_num:03d}"
        manager.set_user_tier(user_id, "free")  # 设置为 free 等级（10 请求/分钟）

        for request_num in range(requests_per_user):
            tasks.append(send_request(user_id, request_num))

    # 执行所有任务
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    # 统计结果
    for result in results:
        if isinstance(result, Exception):
            error_count += 1
        elif result["status"] == "success":
            success_count += 1
        elif result["status"] == "rate_limited":
            rate_limited_count += 1

    # 输出结果
    print(f"\n📈 测试结果:")
    print(f"  - 总耗时: {duration:.2f} 秒")
    print(f"  - 成功请求: {success_count}/{total_requests} ({success_count/total_requests*100:.1f}%)")
    print(f"  - 被限流: {rate_limited_count}/{total_requests} ({rate_limited_count/total_requests*100:.1f}%)")
    print(f"  - 错误: {error_count}/{total_requests}")
    print(f"  - QPS: {total_requests/duration:.1f} 请求/秒")

    # 测试不同用户等级
    print(f"\n👥 测试用户等级限流:")
    tiers = ["free", "basic", "pro", "enterprise"]
    for tier in tiers:
        user_id = f"test_{tier}_user"
        manager.set_user_tier(user_id, tier)

        # 连续发送请求直到被限流
        count = 0
        async def test_until_limit():
            nonlocal count
            while count < 100:  # 最多测试 100 次
                result = await manager.check_user_rate_limit(user_id)
                if not result.allowed:
                    break
                count += 1

        await test_until_limit()
        tier_config = manager.rate_limiter.tier_limits.get(tier, {"limit": "unknown"})
        print(f"  - {tier:12s} 等级: {count:3d} 请求后被限流（限制: {tier_config['limit']}）")

    # 关闭资源
    await manager.close()

    print("\n" + "=" * 60)
    print("✅ 并发压测完成！")
    print("=" * 60)


async def test_rate_limiting_accuracy():
    """测试限流准确性"""
    print("\n" + "=" * 60)
    print("限流准确性测试")
    print("=" * 60)

    from src.infrastructure.concurrency import get_concurrency_manager

    manager = get_concurrency_manager()

    # 测试用户
    test_user = "limit_test_user"
    manager.set_user_tier(test_user, "free")  # 10 请求/分钟

    print(f"📋 测试用户: {test_user}")
    print(f"📋 等级: free (限制: {manager.rate_limiter.tier_limits['free']['limit']} 请求/分钟)")
    print(f"📋 时间窗口: {manager.rate_limiter.tier_limits['free']['window']} 秒")

    # 连续发送请求
    print(f"\n🔄 连续发送请求...")
    results = []

    for i in range(15):  # 发送 15 个请求（超过限制的 10 个）
        result = await manager.check_user_rate_limit(test_user)
        results.append({
            "request": i + 1,
            "allowed": result.allowed,
            "remaining": result.remaining,
            "limit": result.limit
        })
        print(f"  - 请求 {i+1:2d}: {'✅ 允许' if result.allowed else '❌ 拒绝'} (剩余: {result.remaining}/{result.limit})")

        if not result.allowed:
            break

        # 短暂延迟，模拟真实请求间隔
        await asyncio.sleep(0.1)

    # 统计
    allowed_count = sum(1 for r in results if r["allowed"])
    print(f"\n📊 统计:")
    print(f"  - 允许请求: {allowed_count}")
    print(f"  - 预期允许: 10")
    print(f"  - 限流准确性: {'✅ 正确' if allowed_count == 10 else '❌ 错误'}")

    await manager.close()


async def main():
    """主测试函数"""
    await test_concurrent_requests()
    await test_rate_limiting_accuracy()


if __name__ == "__main__":
    asyncio.run(main())
