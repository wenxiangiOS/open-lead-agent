"""
数据仓库

使用仓库模式实现数据访问层
"""

import logging
import json
from typing import Optional, Dict, Any, List, TypeVar, Type
from datetime import datetime, timedelta

from .connection import DatabaseConnection, DatabasePool, default_pool
from .models import (
    User, UserConfig, Conversation, UserProfile,
    SystemConfig, AuditLog,
    UserStatus, ConversationRole
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=type)


# ============================================================================
# 基础仓库
# ============================================================================

class BaseRepository:
    """
    基础仓库类

    提供通用的数据访问方法
    """

    def __init__(self, connection: DatabaseConnection = None):
        """
        初始化仓库

        Args:
            connection: 数据库连接（None 表示使用默认连接）
        """
        self._conn = connection

    @property
    def conn(self) -> DatabaseConnection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = default_pool.get_connection()
        return self._conn

    async def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """执行查询"""
        return await self.conn.execute(query, params, fetch)

    def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def _deserialize_value(self, value: str, value_type: str) -> Any:
        """反序列化值"""
        if value is None:
            return None

        if value_type == "json":
            return json.loads(value)
        elif value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return value.lower() == "true"
        else:
            return value


# ============================================================================
# 用户仓库
# ============================================================================

class UserRepository(BaseRepository):
    """
    用户数据仓库

    管理用户数据的增删改查
    """

    async def create(
        self,
        account_id: str,
        username: str,
        phone: str = None,
        email: str = None,
        status: UserStatus = UserStatus.ACTIVE
    ) -> Optional[User]:
        """
        创建用户

        Args:
            account_id: 账号 ID
            username: 用户名
            phone: 手机号
            email: 邮箱
            status: 用户状态

        Returns:
            创建的用户对象
        """
        query = """
        INSERT INTO users (account_id, username, phone, email, status)
        VALUES (?, ?, ?, ?, ?)
        """

        await self.execute_query(
            query,
            (account_id, username, phone, status.value)
        )

        return await self.get_by_account_id(account_id)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        query = "SELECT * FROM users WHERE id = ?"
        results = await self.execute_query(query, (user_id,), fetch=True)

        if results:
            return self._row_to_user(results[0])
        return None

    async def get_by_account_id(self, account_id: str) -> Optional[User]:
        """根据账号 ID 获取用户"""
        query = "SELECT * FROM users WHERE account_id = ?"
        results = await self.execute_query(query, (account_id,), fetch=True)

        if results:
            return self._row_to_user(results[0])
        return None

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        query = "SELECT * FROM users WHERE phone = ?"
        results = await self.execute_query(query, (phone,), fetch=True)

        if results:
            return self._row_to_user(results[0])
        return None

    async def update(
        self,
        user_id: int,
        username: str = None,
        phone: str = None,
        email: str = None,
        status: UserStatus = None
    ) -> bool:
        """更新用户信息"""
        updates = []
        params = []

        if username is not None:
            updates.append("username = ?")
            params.append(username)

        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)

        if email is not None:
            updates.append("email = ?")
            params.append(email)

        if status is not None:
            updates.append("status = ?")
            params.append(status.value)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        await self.execute_query(query, tuple(params))
        return True

    async def delete(self, user_id: int) -> bool:
        """删除用户"""
        query = "DELETE FROM users WHERE id = ?"
        await self.execute_query(query, (user_id,))
        return True

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        status: UserStatus = None
    ) -> List[User]:
        """获取用户列表"""
        query = "SELECT * FROM users"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        results = await self.execute_query(query, tuple(params), fetch=True)
        return [self._row_to_user(row) for row in results]

    def _row_to_user(self, row: Dict[str, Any]) -> User:
        """将数据库行转换为 User 对象"""
        return User(
            id=row.get("id"),
            account_id=row.get("account_id"),
            username=row.get("username"),
            phone=row.get("phone"),
            email=row.get("email"),
            status=UserStatus(row.get("status", "active")),
            metadata=json.loads(row.get("metadata", "{}")),
            created_at=datetime.fromisoformat(row.get("created_at")) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row.get("updated_at")) if row.get("updated_at") else None
        )


# ============================================================================
# 用户配置仓库
# ============================================================================

class UserConfigRepository(BaseRepository):
    """用户配置仓库"""

    async def set(
        self,
        user_id: int,
        key: str,
        value: Any,
        value_type: str = "string"
    ) -> bool:
        """设置用户配置"""
        serialized_value = self._serialize_value(value)

        query = """
        INSERT INTO user_config (user_id, config_key, config_value, value_type)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, config_key) DO UPDATE SET
            config_value = excluded.config_value,
            value_type = excluded.value_type,
            updated_at = CURRENT_TIMESTAMP
        """

        await self.execute_query(query, (user_id, key, serialized_value, value_type))
        return True

    async def get(self, user_id: int, key: str) -> Optional[Any]:
        """获取用户配置"""
        query = """
        SELECT config_value, value_type FROM user_config
        WHERE user_id = ? AND config_key = ?
        """

        results = await self.execute_query(query, (user_id, key), fetch=True)

        if results:
            row = results[0]
            return self._deserialize_value(row["config_value"], row["value_type"])
        return None

    async def get_all(self, user_id: int) -> Dict[str, Any]:
        """获取用户所有配置"""
        query = "SELECT config_key, config_value, value_type FROM user_config WHERE user_id = ?"
        results = await self.execute_query(query, (user_id,), fetch=True)

        config = {}
        for row in results:
            config[row["config_key"]] = self._deserialize_value(
                row["config_value"],
                row["value_type"]
            )

        return config

    async def delete(self, user_id: int, key: str) -> bool:
        """删除用户配置"""
        query = "DELETE FROM user_config WHERE user_id = ? AND config_key = ?"
        await self.execute_query(query, (user_id, key))
        return True


# ============================================================================
# 对话历史仓库
# ============================================================================

class ConversationRepository(BaseRepository):
    """对话历史仓库"""

    async def add(
        self,
        user_id: int,
        role: ConversationRole,
        content: str,
        tokens: int = 0,
        model: str = ""
    ) -> Optional[int]:
        """添加对话记录"""
        query = """
        INSERT INTO conversations (user_id, role, content, tokens, model)
        VALUES (?, ?, ?, ?, ?)
        """

        await self.execute_query(
            query,
            (user_id, role.value, content, tokens, model)
        )

        # 获取插入的 ID
        result = await self.execute_query(
            "SELECT last_insert_rowid() as id",
            fetch=True
        )

        return result[0]["id"] if result else None

    async def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """获取用户对话记录"""
        query = """
        SELECT * FROM conversations
        WHERE user_id = ?
        ORDER BY created_at ASC
        LIMIT ? OFFSET ?
        """

        results = await self.execute_query(query, (user_id, limit, offset), fetch=True)
        return [self._row_to_conversation(row) for row in results]

    async def get_recent_conversations(
        self,
        user_id: int,
        hours: int = 24
    ) -> List[Conversation]:
        """获取最近的对话记录"""
        cutoff = datetime.now() - timedelta(hours=hours)

        query = """
        SELECT * FROM conversations
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at ASC
        """

        results = await self.execute_query(
            query,
            (user_id, cutoff.isoformat()),
            fetch=True
        )

        return [self._row_to_conversation(row) for row in results]

    async def delete_user_conversations(self, user_id: int) -> bool:
        """删除用户所有对话记录"""
        query = "DELETE FROM conversations WHERE user_id = ?"
        await self.execute_query(query, (user_id,))
        return True

    def _row_to_conversation(self, row: Dict[str, Any]) -> Conversation:
        """将数据库行转换为 Conversation 对象"""
        return Conversation(
            id=row.get("id"),
            user_id=row.get("user_id"),
            role=ConversationRole(row.get("role")),
            content=row.get("content"),
            tokens=row.get("tokens", 0),
            model=row.get("model", ""),
            metadata=json.loads(row.get("metadata", "{}")),
            created_at=datetime.fromisoformat(row.get("created_at")) if row.get("created_at") else None
        )


# ============================================================================
# 系统配置仓库
# ============================================================================

class SystemConfigRepository(BaseRepository):
    """系统配置仓库"""

    async def set(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str = "",
        is_public: bool = False
    ) -> bool:
        """设置系统配置"""
        serialized_value = self._serialize_value(value)

        query = """
        INSERT INTO system_config (config_key, config_value, value_type, description, is_public)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(config_key) DO UPDATE SET
            config_value = excluded.config_value,
            value_type = excluded.value_type,
            description = excluded.description,
            is_public = excluded.is_public,
            updated_at = CURRENT_TIMESTAMP
        """

        await self.execute_query(
            query,
            (key, serialized_value, value_type, description, int(is_public))
        )
        return True

    async def get(self, key: str) -> Optional[Any]:
        """获取系统配置"""
        query = "SELECT config_value, value_type FROM system_config WHERE config_key = ?"
        results = await self.execute_query(query, (key,), fetch=True)

        if results:
            row = results[0]
            return self._deserialize_value(row["config_value"], row["value_type"])
        return None

    async def get_all_public(self) -> Dict[str, Any]:
        """获取所有公开配置"""
        query = """
        SELECT config_key, config_value, value_type
        FROM system_config
        WHERE is_public = 1
        """

        results = await self.execute_query(query, fetch=True)

        config = {}
        for row in results:
            config[row["config_key"]] = self._deserialize_value(
                row["config_value"],
                row["value_type"]
            )

        return config


# ============================================================================
# 操作日志仓库
# ============================================================================

class AuditLogRepository(BaseRepository):
    """操作日志仓库"""

    async def log(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: str = None,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """记录操作日志"""
        query = """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        await self.execute_query(
            query,
            (
                user_id,
                action,
                resource_type,
                resource_id,
                self._serialize_value(details or {}),
                ip_address,
                user_agent
            )
        )
        return True

    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户操作日志"""
        query = """
        SELECT * FROM audit_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """

        results = await self.execute_query(query, (user_id, limit), fetch=True)
        return results

    async def get_recent_logs(
        self,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """获取最近的操作日志"""
        cutoff = datetime.now() - timedelta(hours=hours)

        query = """
        SELECT * FROM audit_logs
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT ?
        """

        results = await self.execute_query(
            query,
            (cutoff.isoformat(), limit),
            fetch=True
        )
        return results


# ============================================================================
# 仓库管理器
# ============================================================================

class RepositoryManager:
    """
    仓库管理器

    提供所有仓库的统一访问接口
    """

    def __init__(self, connection: DatabaseConnection = None):
        """
        初始化仓库管理器

        Args:
            connection: 数据库连接
        """
        self._conn = connection
        self._users: UserRepository = None
        self._user_config: UserConfigRepository = None
        self._conversations: ConversationRepository = None
        self._system_config: SystemConfigRepository = None
        self._audit_logs: AuditLogRepository = None

    @property
    def users(self) -> UserRepository:
        """获取用户仓库"""
        if self._users is None:
            self._users = UserRepository(self._conn)
        return self._users

    @property
    def user_config(self) -> UserConfigRepository:
        """获取用户配置仓库"""
        if self._user_config is None:
            self._user_config = UserConfigRepository(self._conn)
        return self._user_config

    @property
    def conversations(self) -> ConversationRepository:
        """获取对话仓库"""
        if self._conversations is None:
            self._conversations = ConversationRepository(self._conn)
        return self._conversations

    @property
    def system_config(self) -> SystemConfigRepository:
        """获取系统配置仓库"""
        if self._system_config is None:
            self._system_config = SystemConfigRepository(self._conn)
        return self._system_config

    @property
    def audit_logs(self) -> AuditLogRepository:
        """获取操作日志仓库"""
        if self._audit_logs is None:
            self._audit_logs = AuditLogRepository(self._conn)
        return self._audit_logs


# ============================================================================
# 全局仓库管理器
# ============================================================================

# 默认仓库管理器
default_repositories = RepositoryManager()
