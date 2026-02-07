"""
数据库迁移系统

管理数据库 schema 变更
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import os

from .connection import DatabaseConnection, DatabaseConfig
from .models import (
    User, UserConfig, Conversation, UserProfile,
    SystemConfig, AuditLog
)

logger = logging.getLogger(__name__)


# ============================================================================
# 迁移记录
# ============================================================================

@dataclass
class Migration:
    """
    数据库迁移

    Attributes:
        version: 迁移版本
        name: 迁移名称
        description: 迁移描述
        up_sql: 升级 SQL
        down_sql: 降级 SQL（可选）
    """
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str = ""

    def __str__(self) -> str:
        return f"{self.version}_{self.name}"


# ============================================================================
# 迁移管理器
# ============================================================================

class MigrationManager:
    """
    迁移管理器

    管理数据库 schema 迁移
    """

    def __init__(self, connection: DatabaseConnection):
        """
        初始化迁移管理器

        Args:
            connection: 数据库连接
        """
        self._conn = connection
        self._migrations: Dict[str, Migration] = {}
        self._applied_migrations: Dict[str, datetime] = {}

    def register(self, migration: Migration):
        """
        注册迁移

        Args:
            migration: 迁移对象
        """
        self._migrations[migration.version] = migration
        logger.info(f"注册迁移: {migration}")

    def get_pending_migrations(self) -> List[Migration]:
        """
        获取待执行的迁移

        Returns:
            待执行的迁移列表（按版本排序）
        """
        return [
            m for version, m in sorted(self._migrations.items())
            if version not in self._applied_migrations
        ]

    async def initialize(self) -> bool:
        """
        初始化迁移系统

        创建迁移记录表

        Returns:
            是否成功
        """
        query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            await self._conn.execute(query)
            await self._load_applied_migrations()
            return True
        except Exception as e:
            logger.error(f"初始化迁移系统失败: {e}")
            return False

    async def _load_applied_migrations(self):
        """加载已应用的迁移"""
        query = "SELECT version, applied_at FROM schema_migrations ORDER BY version"
        results = await self._conn.execute(query, fetch=True)

        if results:
            self._applied_migrations = {
                row["version"]: datetime.fromisoformat(row["applied_at"])
                for row in results
            }

    async def migrate(self, target_version: str = None) -> bool:
        """
        执行迁移

        Args:
            target_version: 目标版本（None 表示迁移到最新版本）

        Returns:
            是否成功
        """
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            logger.info("没有待执行的迁移")
            return True

        logger.info(f"准备执行 {len(pending)} 个迁移...")

        for migration in pending:
            try:
                logger.info(f"执行迁移: {migration}")

                # 执行迁移 SQL
                success = await self._conn.execute_script(migration.up_sql)

                if not success:
                    logger.error(f"迁移失败: {migration}")
                    return False

                # 记录迁移
                await self._record_migration(migration)

                logger.info(f"✅ 迁移成功: {migration}")

            except Exception as e:
                logger.error(f"迁移失败 {migration}: {e}")
                return False

        logger.info("✅ 所有迁移执行成功")
        return True

    async def rollback(self, version: str) -> bool:
        """
        回滚到指定版本

        Args:
            version: 目标版本

        Returns:
            是否成功
        """
        # 获取需要回滚的迁移（从高到低）
        to_rollback = [
            (v, m) for v, m in reversed(sorted(self._migrations.items()))
            if v > version and v in self._applied_migrations and m.down_sql
        ]

        if not to_rollback:
            logger.info("没有需要回滚的迁移")
            return True

        logger.info(f"准备回滚 {len(to_rollback)} 个迁移...")

        for v, migration in to_rollback:
            try:
                logger.info(f"回滚迁移: {migration}")

                # 执行回滚 SQL
                success = await self._conn.execute_script(migration.down_sql)

                if not success:
                    logger.error(f"回滚失败: {migration}")
                    return False

                # 删除迁移记录
                await self._remove_migration_record(v)

                logger.info(f"✅ 回滚成功: {migration}")

            except Exception as e:
                logger.error(f"回滚失败 {migration}: {e}")
                return False

        logger.info("✅ 所有回滚执行成功")
        return True

    async def _record_migration(self, migration: Migration):
        """记录已执行的迁移"""
        query = """
        INSERT INTO schema_migrations (version, name)
        VALUES (?, ?)
        """
        await self._conn.execute(query, (migration.version, migration.name))
        self._applied_migrations[migration.version] = datetime.now()

    async def _remove_migration_record(self, version: str):
        """删除迁移记录"""
        query = "DELETE FROM schema_migrations WHERE version = ?"
        await self._conn.execute(query, (version,))
        if version in self._applied_migrations:
            del self._applied_migrations[version]

    def get_status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        return {
            "total_migrations": len(self._migrations),
            "applied_migrations": len(self._applied_migrations),
            "pending_migrations": len(self.get_pending_migrations()),
            "applied_versions": sorted(self._applied_migrations.keys()),
            "pending_versions": [m.version for m in self.get_pending_migrations()]
        }


# ============================================================================
# 预定义迁移
# ============================================================================

def get_initial_migrations(db_type: str = "sqlite") -> List[Migration]:
    """
    获取初始迁移列表

    Args:
        db_type: 数据库类型

    Returns:
        迁移列表
    """
    return [
        Migration(
            version="001",
            name="create_users_table",
            description="创建用户表",
            up_sql=User.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS users;"
        ),
        Migration(
            version="002",
            name="create_user_config_table",
            description="创建用户配置表",
            up_sql=UserConfig.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS user_config;"
        ),
        Migration(
            version="003",
            name="create_conversations_table",
            description="创建对话历史表",
            up_sql=Conversation.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS conversations;"
        ),
        Migration(
            version="004",
            name="create_user_profiles_table",
            description="创建用户资料表",
            up_sql=UserProfile.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS user_profiles;"
        ),
        Migration(
            version="005",
            name="create_system_config_table",
            description="创建系统配置表",
            up_sql=SystemConfig.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS system_config;"
        ),
        Migration(
            version="006",
            name="create_audit_logs_table",
            description="创建操作日志表",
            up_sql=AuditLog.get_create_table_sql(db_type),
            down_sql="DROP TABLE IF EXISTS audit_logs;"
        ),
    ]


async def setup_database(
    config: DatabaseConfig,
    migrate: bool = True
) -> bool:
    """
    设置数据库

    Args:
        config: 数据库配置
        migrate: 是否执行迁移

    Returns:
        是否成功
    """
    from .connection import DatabaseConnection, default_pool

    # 创建连接
    conn = DatabaseConnection(config)

    if not await conn.connect():
        logger.error("数据库连接失败")
        return False

    # 添加到连接池
    default_pool.add_connection("default", config, set_as_default=True)

    # 执行迁移
    if migrate:
        manager = MigrationManager(conn)
        await manager.initialize()

        # 注册迁移
        for migration in get_initial_migrations(config.db_type):
            manager.register(migration)

        # 执行迁移
        if not await manager.migrate():
            logger.error("数据库迁移失败")
            return False

        # 打印状态
        status = manager.get_status()
        logger.info(f"数据库迁移完成: {status['applied_migrations']}/{status['total_migrations']}")

    logger.info("✅ 数据库设置成功")
    return True
