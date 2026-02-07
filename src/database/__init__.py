"""
数据库模块

提供数据库持久化功能
"""

from .connection import (
    DatabaseConfig,
    DatabaseConnection,
    DatabasePool,
    default_pool
)

from .models import (
    User,
    UserConfig,
    Conversation,
    UserProfile,
    SystemConfig,
    AuditLog,
    UserStatus,
    ConversationRole
)

from .repositories import (
    BaseRepository,
    UserRepository,
    UserConfigRepository,
    ConversationRepository,
    SystemConfigRepository,
    AuditLogRepository,
    RepositoryManager,
    default_repositories
)

from .migrations import (
    Migration,
    MigrationManager,
    get_initial_migrations,
    setup_database
)

__all__ = [
    # 连接
    'DatabaseConfig',
    'DatabaseConnection',
    'DatabasePool',
    'default_pool',

    # 模型
    'User',
    'UserConfig',
    'Conversation',
    'UserProfile',
    'SystemConfig',
    'AuditLog',
    'UserStatus',
    'ConversationRole',

    # 仓库
    'BaseRepository',
    'UserRepository',
    'UserConfigRepository',
    'ConversationRepository',
    'SystemConfigRepository',
    'AuditLogRepository',
    'RepositoryManager',
    'default_repositories',

    # 迁移
    'Migration',
    'MigrationManager',
    'get_initial_migrations',
    'setup_database',
]
