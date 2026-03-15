"""
配置管理模块

采用分层配置架构，提高可维护性和可测试性
"""

import os
from pathlib import Path
from typing import Optional, Callable
from pydantic import BaseModel, ValidationError, Field, ConfigDict
from dotenv import load_dotenv

from .components import (
    BaseConfig,
    AIConfig,
    RedisConfig,
    ServerConfig,
    SecurityConfig,
    LoggingConfig,
)

# 🔴 重要：在创建任何配置之前，先加载 .env 文件
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)


class Settings(BaseModel):
    """
    应用配置聚合器

    整合所有配置组件，提供统一的配置访问接口
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # 配置组件 - 使用 default_factory 延迟创建，确保在 load_dotenv() 之后
    app: BaseConfig = Field(default_factory=BaseConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # 兼容旧版本的单层配置属性（逐步废弃）
    @property
    def api_key(self) -> str:
        """兼容属性：API 密钥"""
        return self.ai.api_key

    @property
    def model_name(self) -> str:
        """兼容属性：模型名称"""
        return self.ai.model_name

    @property
    def base_url(self) -> str:
        """兼容属性：API 基础 URL"""
        return self.ai.base_url

    @property
    def app_name(self) -> str:
        """兼容属性：应用名称"""
        return self.app.app_name

    @property
    def app_version(self) -> str:
        """兼容属性：应用版本"""
        return self.app.app_version

    @property
    def debug(self) -> bool:
        """兼容属性：调试模式"""
        return self.app.debug

    @property
    def log_level(self) -> str:
        """兼容属性：日志级别"""
        return self.logging.level

    @property
    def host(self) -> str:
        """兼容属性：监听地址"""
        return self.server.host

    @property
    def port(self) -> int:
        """兼容属性：监听端口"""
        return self.server.port

    @property
    def reload(self) -> bool:
        """兼容属性：自动重载"""
        return self.server.reload

    @property
    def rate_limit_enabled(self) -> bool:
        """兼容属性：限流启用"""
        return self.server.rate_limit_enabled

    @property
    def rate_limit_requests(self) -> int:
        """兼容属性：限流请求数"""
        return self.server.rate_limit_requests

    @property
    def rate_limit_window(self) -> int:
        """兼容属性：限流时间窗口"""
        return self.server.rate_limit_window

    @property
    def redis_enabled(self) -> bool:
        """兼容属性：Redis 启用"""
        return self.redis.enabled

    @property
    def redis_host(self) -> str:
        """兼容属性：Redis 主机"""
        return self.redis.host

    @property
    def redis_port(self) -> int:
        """兼容属性：Redis 端口"""
        return self.redis.port

    @property
    def redis_db(self) -> int:
        """兼容属性：Redis 数据库"""
        return self.redis.db

    @property
    def redis_password(self) -> Optional[str]:
        """兼容属性：Redis 密码"""
        return self.redis.password

    @property
    def redis_prefix(self) -> str:
        """兼容属性：Redis 键前缀"""
        return self.redis.key_prefix

    @property
    def redis_ttl(self) -> int:
        """兼容属性：Redis TTL"""
        return self.redis.default_ttl

    @property
    def http_connections(self) -> int:
        """兼容属性：HTTP 连接数"""
        return self.redis.max_connections

    @property
    def http_max_keepalive(self) -> int:
        """兼容属性：HTTP Keep-Alive 连接数"""
        return self.server.keepalive

    @property
    def volc_access_key(self) -> Optional[str]:
        """兼容属性：火山引擎 Access Key"""
        return self.ai.volc_access_key

    @property
    def volc_secret_key(self) -> Optional[str]:
        """兼容属性：火山引擎 Secret Key"""
        return self.ai.volc_secret_key


def load_settings(env_file: Optional[str] = None) -> Settings:
    """
    加载配置

    Args:
        env_file: 环境变量文件路径（可选）

    Returns:
        Settings: 配置实例

    Raises:
        ValidationError: 配置验证失败
    """
    # 加载 .env 文件
    if env_file is None:
        env_path = Path(__file__).parent.parent.parent / ".env"
    else:
        env_path = Path(env_file)

    if env_path.exists():
        load_dotenv(env_path, override=True)

    # 创建配置实例
    try:
        settings = Settings()
        return settings
    except ValidationError as e:
        print(f"❌ 配置验证失败: {e}")
        raise


# 全局配置实例
settings = load_settings()


def get_settings() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 全局配置实例
    """
    return settings


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """
    重新加载配置（用于测试或热更新）

    Args:
        env_file: 环境变量文件路径（可选）

    Returns:
        Settings: 新的配置实例
    """
    global settings
    settings = load_settings(env_file)
    return settings


# ==================== 字段配置 ====================
# 智能追问机制的字段配置（新增字段只需在此处添加）

FIELD_CONFIG = {
    'last_name': {
        'chinese_name': '称呼',
        'keywords': ['怎么称呼', '叫什么', '称呼你', '你的名字', '你叫什么', '称呼'],
        'follow_up_hint': '告诉我名字的话，到时候匹配到合适的人可以方便称呼你～',
        'normal_question': '方便告诉我怎么称呼你呢',
    },
    'sex': {
        'chinese_name': '性别',
        'keywords': ['小哥哥还是小姐姐', '男生还是女生', '男的还是女的', '性别'],
        'follow_up_hint': '知道你的性别才能帮你匹配呀～',
        'normal_question': '我是叫你小哥哥还是小姐姐呀',
    },
    'age': {
        'chinese_name': '年龄',
        'keywords': ['多大', '几岁', '年龄', '哪年的', '出生', '90后', '80后', '00后'],
        'follow_up_hint': '告诉我年龄的话，可以帮你匹配年龄合适的～',
        'normal_question': '今年多大呀',
    },
    'height': {
        'chinese_name': '身高',
        'keywords': ['身高', '多高', 'cm', '厘米'],
        'follow_up_hint': '这样我好帮你匹配身高合适的～',
        'normal_question': '身高多少呀',
    },
    'weight': {
        'chinese_name': '体重',
        'keywords': ['体重', '多重', 'kg', '公斤', '斤'],
        'follow_up_hint': '有些女生会比较在意这个呢～',
        'normal_question': '体重多少呀',
    },
    'location': {
        'chinese_name': '所在地',
        'keywords': ['哪个城市', '在哪里', '坐标', '所在地', '在什么', '住哪', '所在城市', '城市'],
        'follow_up_hint': '知道你的位置才能帮你匹配同城的呢～',
        'normal_question': '在哪个城市呀',
    },
    'education': {
        'chinese_name': '学历',
        'keywords': ['学历', '什么学历', '本科', '硕士', '博士', '大专'],
        'follow_up_hint': '这样匹配的时候可以考虑学历相当的～',
        'normal_question': '学历是什么呀',
    },
    'occupation': {
        'chinese_name': '职业',
        'keywords': ['职业', '做什么', '工作', '干什么'],
        'follow_up_hint': '职业稳定的话会更受欢迎呢～',
        'normal_question': '做什么工作的呀',
    },
    'monthly_income': {
        'chinese_name': '月收入',
        'keywords': ['月收入', '收入', '月薪', '赚多少', '工资', '年薪'],
        'follow_up_hint': '这样我能帮你筛选条件相当的对象～',
        'normal_question': '月收入大概多少呀',
    },
    'marital_status': {
        'chinese_name': '婚况',
        'keywords': ['婚况', '单身', '离异', '感情状态', '结婚没', '已婚'],
        'follow_up_hint': '这样我好帮你匹配节奏一致的人～',
        'normal_question': '感情状态是单身吗',
    },
    'contact': {
        'chinese_name': '联系方式',
        'keywords': ['电话', '联系方式', '微信', '手机号', '号码'],
        'follow_up_hint': '匹配合适的话需要联系你呢～',
        'normal_question': '方便留个电话吗',
    },
    'partner_requirement': {
        'chinese_name': '择偶要求',
        'keywords': ['择偶要求', '找什么样的', '有什么要求', '要求对方', '另一半'],
        'follow_up_hint': '告诉我你的要求，才能帮你精准匹配～',
        'normal_question': '希望找什么样的呢',
    },
}


def get_field_config(field_name: str) -> dict:
    """获取单个字段配置"""
    return FIELD_CONFIG.get(field_name, {})


def get_all_field_names() -> dict:
    """获取所有字段的中文名称映射 {英文名: 中文名}"""
    return {k: v['chinese_name'] for k, v in FIELD_CONFIG.items()}


def get_field_keywords() -> dict:
    """获取所有字段的关键词映射 {英文名: 关键词列表}"""
    return {k: v['keywords'] for k, v in FIELD_CONFIG.items()}
