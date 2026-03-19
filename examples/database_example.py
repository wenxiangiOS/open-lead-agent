"""
数据库系统使用示例

状态：子系统演示示例，非当前主链路官方示例。
说明：对应 `src.database` 预留/独立子系统，不代表当前线上主业务架构。

演示如何使用数据库持久化功能
"""

import asyncio
from typing import Dict, Any

from src.database import (
    # 配置
    DatabaseConfig, DatabasePool,
    # 模型
    User, UserStatus, ConversationRole,
    # 仓库
    RepositoryManager,
    # 迁移
    setup_database
)


# ============================================================================
# 示例：用户服务
# ============================================================================

class UserService:
    """
    用户服务示例

    演示如何使用仓库进行数据操作
    """

    def __init__(self, repositories: RepositoryManager = None):
        """
        初始化用户服务

        Args:
            repositories: 仓库管理器
        """
        self.repos = repositories or RepositoryManager()

    async def create_user(
        self,
        account_id: str,
        username: str,
        phone: str = None
    ) -> Dict[str, Any]:
        """
        创建用户

        Args:
            account_id: 账号 ID
            username: 用户名
            phone: 手机号

        Returns:
            创建的用户信息
        """
        # 检查用户是否已存在
        existing = await self.repos.users.get_by_account_id(account_id)
        if existing:
            return {"error": "用户已存在", "user": existing.to_dict()}

        # 创建新用户
        user = await self.repos.users.create(
            account_id=account_id,
            username=username,
            phone=phone,
            status=UserStatus.ACTIVE
        )

        if user:
            # 设置默认配置
            await self.repos.user_config.set(user.id, "theme", "light")
            await self.repos.user_config.set(user.id, "language", "zh-CN")

            return {"success": True, "user": user.to_dict()}

        return {"error": "创建用户失败"}

    async def get_user(self, account_id: str) -> Dict[str, Any]:
        """
        获取用户信息

        Args:
            account_id: 账号 ID

        Returns:
            用户信息
        """
        user = await self.repos.users.get_by_account_id(account_id)

        if not user:
            return {"error": "用户不存在"}

        # 获取用户配置
        config = await self.repos.user_config.get_all(user.id)

        return {
            "user": user.to_dict(),
            "config": config
        }

    async def update_user_config(
        self,
        account_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        更新用户配置

        Args:
            account_id: 账号 ID
            key: 配置键
            value: 配置值

        Returns:
            是否成功
        """
        user = await self.repos.users.get_by_account_id(account_id)
        if not user:
            return False

        # 根据值的类型确定 value_type
        value_type = "string"
        if isinstance(value, bool):
            value_type = "bool"
        elif isinstance(value, int):
            value_type = "int"
        elif isinstance(value, float):
            value_type = "float"
        elif isinstance(value, (dict, list)):
            value_type = "json"

        return await self.repos.user_config.set(user.id, key, value, value_type)

    async def add_conversation(
        self,
        account_id: str,
        role: str,
        content: str,
        model: str = ""
    ) -> bool:
        """
        添加对话记录

        Args:
            account_id: 账号 ID
            role: 角色
            content: 内容
            model: 模型名称

        Returns:
            是否成功
        """
        user = await self.repos.users.get_by_account_id(account_id)
        if not user:
            return False

        role_enum = ConversationRole.USER if role == "user" else ConversationRole.ASSISTANT

        await self.repos.conversations.add(
            user_id=user.id,
            role=role_enum,
            content=content,
            model=model
        )

        return True

    async def get_conversation_history(
        self,
        account_id: str,
        limit: int = 20
    ) -> list:
        """
        获取对话历史

        Args:
            account_id: 账号 ID
            limit: 返回数量

        Returns:
            对话记录列表
        """
        user = await self.repos.users.get_by_account_id(account_id)
        if not user:
            return []

        conversations = await self.repos.conversations.get_user_conversations(
            user.id,
            limit=limit
        )

        return [c.to_dict() for c in conversations]


# ============================================================================
# 主程序
# ============================================================================

async def main():
    """主程序"""

    print("\n" + "=" * 60)
    print("💾 数据库系统示例")
    print("=" * 60 + "\n")

    # 1. 设置数据库
    print("📦 设置数据库...")
    from src.database import DatabaseConfig

    config = DatabaseConfig(
        db_type="sqlite",
        database="test_doubao_mcp",
        echo=False
    )

    success = await setup_database(config, migrate=True)

    if not success:
        print("❌ 数据库设置失败")
        return

    print("✅ 数据库设置成功\n")

    # 2. 创建用户服务
    user_service = UserService()

    # 3. 创建用户
    print("👤 创建用户...")
    result = await user_service.create_user(
        account_id="user_12345",
        username="张三",
        phone="13800138000"
    )

    if result.get("success"):
        print(f"✅ 用户创建成功: {result['user']['username']}")
    else:
        print(f"⚠️  {result.get('error')}")

    # 4. 获取用户信息
    print("\n📋 获取用户信息...")
    user_info = await user_service.get_user("user_12345")

    print(f"  用户名: {user_info['user']['username']}")
    print(f"  状态: {user_info['user']['status']}")
    print(f"  配置: {user_info['config']}")

    # 5. 更新用户配置
    print("\n⚙️  更新用户配置...")
    await user_service.update_user_config("user_12345", "theme", "dark")
    await user_service.update_user_config("user_12345", "notifications", True)

    user_info = await user_service.get_info("user_12345")
    print(f"  更新后配置: {user_info['config']}")

    # 6. 添加对话记录
    print("\n💬 添加对话记录...")
    await user_service.add_conversation(
        "user_12345",
        "user",
        "你好，我想找对象"
    )

    await user_service.add_conversation(
        "user_12345",
        "assistant",
        "你好！很高兴为你服务。请告诉我你的基本情况。"
    )

    print("✅ 对话记录添加成功")

    # 7. 获取对话历史
    print("\n📜 获取对话历史...")
    history = await user_service.get_conversation_history("user_12345")

    for conv in history:
        role_icon = "👤" if conv["role"] == "user" else "🤖"
        print(f"  {role_icon} {conv['content']}")

    # 8. 列出所有用户
    print("\n👥 列出所有用户...")
    users = await user_service.repos.users.list_users(limit=10)

    print(f"  共 {len(users)} 个用户:")
    for user in users:
        print(f"    - {user.username} ({user.account_id})")

    # 9. 数据库统计
    print("\n📊 数据库统计...")
    all_users = await user_service.repos.users.list_users(limit=1000)
    print(f"  总用户数: {len(all_users)}")

    # 10. 系统配置
    print("\n⚙️  系统配置...")
    await user_service.repos.system_config.set(
        "maintenance_mode",
        False,
        "bool",
        "维护模式开关",
        is_public=True
    )

    maintenance = await user_service.repos.system_config.get("maintenance_mode")
    print(f"  维护模式: {maintenance}")

    public_config = await user_service.repos.system_config.get_all_public()
    print(f"  公开配置: {list(public_config.keys())}")

    print("\n✅ 示例完成！")


# ============================================================================
# 简化版示例
# ============================================================================

async def simple_example():
    """简化的使用示例"""

    # 设置数据库
    config = DatabaseConfig(
        db_type="sqlite",
        database="simple_test"
    )

    await setup_database(config)

    # 使用仓库
    repos = RepositoryManager()

    # 创建用户
    user = await repos.users.create(
        account_id="test_user",
        username="测试用户"
    )

    print(f"创建用户: {user.username} (ID: {user.id})")

    # 设置配置
    await repos.user_config.set(user.id, "key", "value")

    # 获取配置
    config_value = await repos.user_config.get(user.id, "key")
    print(f"配置值: {config_value}")


if __name__ == "__main__":
    asyncio.run(main())
