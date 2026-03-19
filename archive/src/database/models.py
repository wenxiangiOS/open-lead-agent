"""
数据库模型

定义所有数据表的 ORM 模型
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# 枚举类型
# ============================================================================

class UserStatus(Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class ConversationRole(Enum):
    """对话角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============================================================================
# 基础模型
# ============================================================================

@dataclass
class BaseModel:
    """基础模型"""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, Enum):
                value = value.value
            result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """从字典创建实例"""
        return cls(**data)


# ============================================================================
# 用户模型
# ============================================================================

@dataclass
class User(BaseModel):
    """
    用户模型

    存储用户基本信息
    """
    account_id: str = ""
    username: str = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 表名
    TABLE_NAME = "users"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'active',
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                account_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'active',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:  # mysql
            return """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_id VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255),
                status VARCHAR(20) DEFAULT 'active',
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """


# ============================================================================
# 用户配置模型
# ============================================================================

@dataclass
class UserConfig(BaseModel):
    """
    用户配置模型

    存储用户的配置信息
    """
    user_id: int = 0
    config_key: str = ""
    config_value: Any = None
    value_type: str = "string"  # string, int, float, bool, json

    TABLE_NAME = "user_config"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS user_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT,
                value_type TEXT DEFAULT 'string',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, config_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS user_config (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT,
                value_type TEXT DEFAULT 'string',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, config_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        else:
            return """
            CREATE TABLE IF NOT EXISTS user_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                config_key VARCHAR(255) NOT NULL,
                config_value TEXT,
                value_type VARCHAR(20) DEFAULT 'string',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_config (user_id, config_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """


# ============================================================================
# 对话历史模型
# ============================================================================

@dataclass
class Conversation(BaseModel):
    """
    对话历史模型

    存储用户与 AI 的对话记录
    """
    user_id: int = 0
    role: ConversationRole = ConversationRole.USER
    content: str = ""
    tokens: int = 0
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    TABLE_NAME = "conversations"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                model TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                model TEXT DEFAULT '',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
            """
        else:
            return """
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                tokens INT DEFAULT 0,
                model VARCHAR(100) DEFAULT '',
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """


# ============================================================================
# 用户资料模型
# ============================================================================

@dataclass
class UserProfile(BaseModel):
    """
    用户资料模型

    存储用户的详细信息（红娘服务相关）
    """
    user_id: int = 0
    real_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[int] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    income: Optional[str] = None
    hobbies: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    collection_progress: float = 0.0
    skipped_fields: List[str] = field(default_factory=list)

    TABLE_NAME = "user_profiles"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                real_name TEXT,
                age INTEGER,
                gender TEXT,
                height INTEGER,
                location TEXT,
                occupation TEXT,
                education TEXT,
                income TEXT,
                hobbies TEXT DEFAULT '[]',
                requirements TEXT DEFAULT '{}',
                collection_progress REAL DEFAULT 0,
                skipped_fields TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                real_name TEXT,
                age INTEGER,
                gender TEXT,
                height INTEGER,
                location TEXT,
                occupation TEXT,
                education TEXT,
                income TEXT,
                hobbies TEXT DEFAULT '[]',
                requirements JSONB DEFAULT '{}',
                collection_progress REAL DEFAULT 0,
                skipped_fields TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        else:
            return """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT UNIQUE NOT NULL,
                real_name VARCHAR(100),
                age INT,
                gender VARCHAR(10),
                height INT,
                location VARCHAR(255),
                occupation VARCHAR(255),
                education VARCHAR(100),
                income VARCHAR(100),
                hobbies JSON,
                requirements JSON,
                collection_progress FLOAT DEFAULT 0,
                skipped_fields JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """


# ============================================================================
# 系统配置模型
# ============================================================================

@dataclass
class SystemConfig(BaseModel):
    """
    系统配置模型

    存储系统级配置
    """
    config_key: str = ""
    config_value: Any = None
    value_type: str = "string"
    description: str = ""
    is_public: bool = False  # 是否可公开访问

    TABLE_NAME = "system_config"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                value_type TEXT DEFAULT 'string',
                description TEXT DEFAULT '',
                is_public INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS system_config (
                id SERIAL PRIMARY KEY,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                value_type TEXT DEFAULT 'string',
                description TEXT DEFAULT '',
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:
            return """
            CREATE TABLE IF NOT EXISTS system_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_key VARCHAR(255) UNIQUE NOT NULL,
                config_value TEXT,
                value_type VARCHAR(20) DEFAULT 'string',
                description TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """


# ============================================================================
# 操作日志模型
# ============================================================================

@dataclass
class AuditLog(BaseModel):
    """
    操作日志模型

    记录系统操作日志
    """
    user_id: Optional[int] = None
    action: str = ""
    resource_type: str = ""
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    TABLE_NAME = "audit_logs"

    @classmethod
    def get_create_table_sql(cls, db_type: str = "sqlite") -> str:
        """获取创建表的 SQL"""
        if db_type == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details TEXT DEFAULT '{}',
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
            """
        elif db_type == "postgresql":
            return """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details JSONB DEFAULT '{}',
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
            """
        else:
            return """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(100) NOT NULL,
                resource_id VARCHAR(255),
                details JSON,
                ip_address VARCHAR(50),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_action (action),
                INDEX idx_created_at (created_at),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
