#!/usr/bin/env python3
"""
并发模块测试脚本

测试并发管理器的各项功能
"""

import asyncio
import sys
import os

# 确保可以导入 src 模块
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


async def test_concurrency_manager():
    """测试并发管理器"""
    print("=" * 60)
    print("并发模块测试")
    print("=" * 60)

    from src.infrastructure.concurrency import get_concurrency_manager

    # 获取并发管理器
    manager = get_concurrency_manager()
    print("✅ 并发管理器初始化成功")

    # 测试配置
    print("\n📋 并发配置:")
    print(f"  - 用户限流: {manager.config.user_rate_limit} 请求/分钟")
    print(f"  - 最大并发: {manager.config.max_concurrent_requests}")
    print(f"  - Redis 连接池: {manager.config.redis_pool_size}")
    print(f"  - HTTP 连接池: {manager.config.http_pool_size}")

    # 测试限流检查
    print("\n🔒 测试限流检查:")
    result = await manager.check_rate_limit("test_user_001")
    print(f"  - 用户 test_user_001: allowed={result.allowed}, remaining={result.remaining}")

    # 测试用户等级
    print("\n👥 测试用户等级:")
    manager.set_user_tier("test_user_001", "pro")
    print(f"  - 设置 test_user_001 为 pro 等级")
    tier = manager.get_user_tier("test_user_001")
    print(f"  - 用户等级: {tier}")

    # 测试分级限流
    print("\n🔒 测试分级限流:")
    tier_result = await manager.check_user_rate_limit("test_user_001")
    print(f"  - 等级: {tier_result.tier}, 限制: {tier_result.limit} 请求/分钟")

    # 健康检查
    print("\n🏥 健康检查:")
    health = await manager.health_check()
    print(f"  - 配置: {health['config']}")
    print(f"  - 组件状态: {health['components']}")

    # 测试限流器使用情况
    print("\n📊 限流器使用情况:")
    usage = await manager.rate_limiter.get_usage("test_user_001")
    print(f"  - 已使用: {usage['count']}/{usage['limit']}")
    print(f"  - 剩余: {usage['remaining']}")

    # 关闭资源
    await manager.close()
    print("\n✅ 资源已关闭")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_concurrency_manager())
