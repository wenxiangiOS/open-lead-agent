"""
数据库抽象层

支持多种数据库的统一接口
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


# ============================================================================
# 数据库配置
# ============================================================================

@dataclass
class DatabaseConfig:
    """
    数据库配置

    Attributes:
        db_type: 数据库类型（sqlite, postgresql, mysql）
        host: 主机地址
        port: 端口
        database: 数据库名
        username: 用户名
        password: 密码
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        pool_timeout: 连接超时时间
        echo: 是否打印 SQL
    """
    db_type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    database: str = "doubao_mcp"
    username: str = ""
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False

    @property
    def connection_url(self) -> str:
        """获取连接 URL"""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.database}.db"
        elif self.db_type == "postgresql":
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "mysql":
            return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")


# ============================================================================
# 数据库连接
# ============================================================================

class DatabaseConnection:
    """
    数据库连接

    管理数据库连接和会话
    """

    def __init__(self, config: DatabaseConfig):
        """
        初始化数据库连接

        Args:
            config: 数据库配置
        """
        self.config = config
        self._engine = None
        self._session_factory = None
        self._is_connected = False

    async def connect(self) -> bool:
        """
        连接数据库

        Returns:
            是否连接成功
        """
        try:
            if self.config.db_type == "sqlite":
                return await self._connect_sqlite()
            elif self.config.db_type == "postgresql":
                return await self._connect_postgresql()
            elif self.config.db_type == "mysql":
                return await self._connect_mysql()
            else:
                logger.error(f"不支持的数据库类型: {self.config.db_type}")
                return False

        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    async def _connect_sqlite(self) -> bool:
        """连接 SQLite"""
        try:
            import aiosqlite

            self._engine = await aiosqlite.connect(
                f"{self.config.database}.db",
                check_same_thread=False
            )
            self._is_connected = True
            logger.info(f"✅ SQLite 连接成功: {self.config.database}.db")
            return True

        except Exception as e:
            logger.error(f"SQLite 连接失败: {e}")
            return False

    async def _connect_postgresql(self) -> bool:
        """连接 PostgreSQL"""
        try:
            import asyncpg

            self._engine = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=self.config.pool_timeout
            )
            self._is_connected = True
            logger.info(f"✅ PostgreSQL 连接成功: {self.config.host}:{self.config.port}/{self.config.database}")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            return False

    async def _connect_mysql(self) -> bool:
        """连接 MySQL"""
        try:
            import aiomysql

            self._engine = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                minsize=1,
                maxsize=self.config.pool_size,
                autocommit=False
            )
            self._is_connected = True
            logger.info(f"✅ MySQL 连接成功: {self.config.host}:{self.config.port}/{self.config.database}")
            return True

        except Exception as e:
            logger.error(f"MySQL 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开数据库连接"""
        if not self._is_connected:
            return

        try:
            if self.config.db_type == "sqlite" and self._engine:
                await self._engine.close()
            elif self.config.db_type in ("postgresql", "mysql") and self._engine:
                self._engine.close()
                await self._engine.wait_closed()

            self._is_connected = False
            logger.info("数据库连接已关闭")

        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    @asynccontextmanager
    async def get_connection(self):
        """
        获取数据库连接

        Yields:
            数据库连接对象
        """
        if not self._is_connected:
            raise RuntimeError("数据库未连接")

        if self.config.db_type == "sqlite":
            async with self._engine.cursor() as cursor:
                yield self._engine
        elif self.config.db_type == "postgresql":
            async with self._engine.acquire() as conn:
                yield conn
        elif self.config.db_type == "mysql":
            async with self._engine.acquire() as conn:
                yield conn

    @asynccontextmanager
    async def get_cursor(self):
        """
        获取数据库游标

        Yields:
            数据库游标对象
        """
        async with self.get_connection() as conn:
            if self.config.db_type == "sqlite":
                yield conn.cursor()
            elif self.config.db_type == "postgresql":
                yield conn.cursor()
            elif self.config.db_type == "mysql":
                yield conn.cursor()

    async def execute(
        self,
        query: str,
        params: tuple = None,
        fetch: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        执行 SQL 查询

        Args:
            query: SQL 查询语句
            params: 查询参数
            fetch: 是否获取结果

        Returns:
            查询结果列表
        """
        async with self.get_connection() as conn:
            async with self.get_cursor() as cursor:
                if self.config.echo:
                    logger.info(f"SQL: {query}")
                    if params:
                        logger.info(f"参数: {params}")

                if self.config.db_type == "sqlite":
                    await cursor.execute(query, params or ())
                    if fetch:
                        columns = [desc[0] for desc in cursor.description]
                        rows = await cursor.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    await conn.commit()

                elif self.config.db_type == "postgresql":
                    await cursor.execute(query, params or ())
                    if fetch:
                        columns = [desc.name for desc in cursor.description]
                        rows = await cursor.fetchall()
                        return [dict(zip(columns, row)) for row in rows]

                elif self.config.db_type == "mysql":
                    await cursor.execute(query, params or ())
                    if fetch:
                        columns = [desc[0] for desc in cursor.description]
                        rows = await cursor.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    await conn.commit()

        return None

    async def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ) -> int:
        """
        批量执行 SQL

        Args:
            query: SQL 查询语句
            params_list: 参数列表

        Returns:
            影响的行数
        """
        async with self.get_connection() as conn:
            async with self.get_cursor() as cursor:
                if self.config.echo:
                    logger.info(f"批量 SQL ({len(params_list)} 行): {query}")

                if self.config.db_type == "sqlite":
                    await cursor.executemany(query, params_list)
                    await conn.commit()
                    return cursor.rowcount

                elif self.config.db_type == "postgresql":
                    await cursor.executemany(query, params_list)
                    return cursor.rowcount

                elif self.config.db_type == "mysql":
                    await cursor.executemany(query, params_list)
                    await conn.commit()
                    return cursor.rowcount

        return 0

    async def execute_script(self, script: str) -> bool:
        """
        执行 SQL 脚本

        Args:
            script: SQL 脚本内容

        Returns:
            是否执行成功
        """
        try:
            if self.config.db_type == "sqlite":
                async with self.get_connection() as conn:
                    await conn.executescript(script)
                    await conn.commit()
            else:
                # 其他数据库需要分割执行
                statements = [s.strip() for s in script.split(";") if s.strip()]
                for statement in statements:
                    await self.execute(statement)

            return True

        except Exception as e:
            logger.error(f"执行 SQL 脚本失败: {e}")
            return False


# ============================================================================
# 数据库连接池
# ============================================================================

class DatabasePool:
    """
    数据库连接池

    管理多个数据库连接
    """

    def __init__(self):
        """初始化连接池"""
        self._connections: Dict[str, DatabaseConnection] = {}
        self._default_name = "default"

    def add_connection(
        self,
        name: str,
        config: DatabaseConfig,
        set_as_default: bool = False
    ) -> bool:
        """
        添加数据库连接

        Args:
            name: 连接名称
            config: 数据库配置
            set_as_default: 是否设为默认连接

        Returns:
            是否添加成功
        """
        try:
            conn = DatabaseConnection(config)
            self._connections[name] = conn

            if set_as_default:
                self._default_name = name

            logger.info(f"添加数据库连接: {name}")
            return True

        except Exception as e:
            logger.error(f"添加数据库连接失败 {name}: {e}")
            return False

    async def connect_all(self) -> bool:
        """
        连接所有数据库

        Returns:
            是否全部连接成功
        """
        success = True

        for name, conn in self._connections.items():
            if not await conn.connect():
                logger.error(f"连接数据库失败: {name}")
                success = False

        return success

    async def disconnect_all(self):
        """断开所有数据库连接"""
        for conn in self._connections.values():
            await conn.disconnect()

    def get_connection(self, name: str = None) -> Optional[DatabaseConnection]:
        """
        获取数据库连接

        Args:
            name: 连接名称（None 表示默认连接）

        Returns:
            数据库连接对象
        """
        name = name or self._default_name
        return self._connections.get(name)

    @asynccontextmanager
    async def get_db(self, name: str = None):
        """
        获取数据库连接上下文管理器

        Args:
            name: 连接名称

        Yields:
            数据库连接对象
        """
        conn = self.get_connection(name)
        if not conn:
            raise RuntimeError(f"数据库连接不存在: {name}")
        yield conn


# ============================================================================
# 全局连接池
# ============================================================================

# 默认数据库连接池
default_pool = DatabasePool()
