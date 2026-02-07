"""
示例：使用新工具模块重构后的服务

本示例展示如何使用 src.utils 中的工具函数来简化代码、减少重复
"""

import logging
from typing import Dict, Any, Optional

from src.utils import (
    # 错误处理
    safe_execute,
    retry_on_failure,
    ignore_errors,
    ErrorContext,
    execute_safely_async,
    
    # Redis
    redis_get,
    redis_set,
    redis_get_json,
    redis_set_json,
    redis_fallback,
    
    # 日志
    StructuredLogger,
    log_execution_time,
    log_api_call,
    log_performance,
    
    # 验证
    validate_phone_number,
    validate_email,
    validate_name,
    ValidationResult,
    validate_batch,
    validate_params,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 示例 1: 用户配置服务（使用 Redis 工具）
# ============================================================================

class UserConfigService:
    """
    用户配置服务
    
    使用新的 Redis 工具，自动处理降级和错误
    """
    
    def __init__(self):
        # 使用结构化日志
        self.logger = StructuredLogger("UserConfigService")
    
    @redis_fallback(default_value={})
    async def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户配置
        
        Redis 不可用时自动返回空字典
        """
        return await redis_get_json(f"user_config:{user_id}")
    
    @log_execution_time(threshold_ms=100)
    async def update_user_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """
        更新用户配置
        
        执行时间超过 100ms 时自动记录日志
        """
        self.logger.with_context(user_id=user_id)
        
        success = await redis_set_json(
            f"user_config:{user_id}",
            config,
            ttl=3600
        )
        
        if success:
            self.logger.info("配置更新成功", extra={"config_keys": list(config.keys())})
        
        return success
    
    @safe_execute(default_return=False, context="删除用户配置")
    async def delete_user_config(self, user_id: str) -> bool:
        """
        删除用户配置
        
        发生错误时返回 False
        """
        from src.utils import redis_delete
        return await redis_delete(f"user_config:{user_id}")


# ============================================================================
# 示例 2: 用户注册服务（使用验证工具）
# ============================================================================

class UserRegistrationService:
    """
    用户注册服务
    
    使用新的验证工具，统一处理数据验证
    """
    
    def __init__(self):
        self.logger = StructuredLogger("UserRegistrationService")
    
    @validate_params(
        phone=validate_phone_number,
        email=validate_email,
        name=validate_name
    )
    @log_api_call(
        log_request_body=True,
        log_response_body=False,
        sanitize_fields=["phone", "password"]
    )
    async def register_user(
        self,
        phone: str,
        email: str,
        name: str,
        password: str
    ) -> Dict[str, Any]:
        """
        注册新用户
        
        参数自动验证和清理
        """
        self.logger.with_context(email=email)
        
        # 创建用户（参数已经验证和清理过）
        user_data = {
            "phone": phone,  # 已清理
            "email": email,  # 已清理
            "name": name,    # 已清理
        }
        
        # 保存到数据库/Redis
        await self._save_user(user_data)
        
        self.logger.info("用户注册成功")
        
        return {
            "success": True,
            "user_id": "new_user_123"
        }
    
    async def _save_user(self, user_data: Dict[str, Any]) -> bool:
        """保存用户数据"""
        # 实际实现...
        return True
    
    async def validate_registration_data(
        self,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """
        批量验证注册数据
        
        Returns:
            ValidationResult: 验证结果
        """
        rules = {
            "phone": lambda x: validate_phone_number(x),
            "email": lambda x: validate_email(x),
            "name": lambda x: validate_name(x, min_length=2, max_length=20)
        }
        
        return validate_batch(data, rules)


# ============================================================================
# 示例 3: 外部 API 调用服务（使用重试和错误处理）
# ============================================================================

class ExternalAPIService:
    """
    外部 API 调用服务
    
    使用重试和错误处理工具
    """
    
    def __init__(self):
        self.logger = StructuredLogger("ExternalAPIService")
    
    @retry_on_failure(
        max_attempts=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(ConnectionError, TimeoutError)
    )
    @log_execution_time(threshold_ms=0)
    async def call_external_api(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用外部 API
        
        自动重试 3 次，延迟递增（1秒 -> 2秒 -> 4秒）
        """
        self.logger.info("调用外部 API", extra={"endpoint": endpoint})
        
        # 模拟 API 调用
        # response = await httpx.post(endpoint, json=data)
        # return response.json()
        
        return {"status": "success", "data": {}}
    
    @ignore_errors(default_value={}, log_level="warning")
    async def log_analytics_event(self, event_name: str, properties: Dict[str, Any]):
        """
        记录分析事件（非关键操作）
        
        失败时静默处理，仅记录警告
        """
        # 发送到分析服务
        # await analytics.track(event_name, properties)
        pass


# ============================================================================
# 示例 4: 数据处理服务（综合使用多种工具）
# ============================================================================

class DataProcessingService:
    """
    数据处理服务
    
    综合使用多种工具
    """
    
    def __init__(self):
        self.logger = StructuredLogger("DataProcessingService")
    
    @log_execution_time(threshold_ms=50, log_args=True)
    async def process_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        处理用户数据
        
        综合使用多种工具：
        1. 性能追踪
        2. Redis 缓存
        3. 错误处理
        4. 结构化日志
        """
        self.logger.with_context(user_id=user_id, operation="process_user_data")
        
        # 尝试从缓存获取
        with log_performance("从缓存获取用户数据"):
            cached = await redis_get_json(f"processed:{user_id}")
            if cached:
                self.logger.info("命中缓存")
                return cached
        
        # 缓存未命中，处理数据
        with log_performance("处理用户数据"):
            raw_data = await self._fetch_raw_data(user_id)
        
        processed = await self._transform_data(raw_data)
        
        # 保存到缓存
        @ignore_errors(default_return=None)
        async def save_cache():
            await redis_set_json(f"processed:{user_id}", processed, ttl=3600)
        
        await save_cache()
        
        return processed
    
    @retry_on_failure(max_attempts=2, exceptions=(ConnectionError,))
    async def _fetch_raw_data(self, user_id: str) -> Dict[str, Any]:
        """获取原始数据（带重试）"""
        # 模拟数据获取
        return {"user_id": user_id, "name": "张三"}
    
    @safe_execute(default_return={}, context="数据转换")
    async def _transform_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换数据（带错误处理）"""
        # 模拟数据转换
        return {
            "user_id": raw_data["user_id"],
            "display_name": raw_data.get("name", "").upper(),
            "processed": True
        }


# ============================================================================
# 对比：旧代码 vs 新代码
# ============================================================================

# 旧代码示例（重复的 try-except）
async def get_user_config_old(user_id: str):
    """旧代码：手动处理错误"""
    try:
        from src.services.redis_service import redis_service
        data = redis_service.get_json_sync(f"user_config:{user_id}")
        if data:
            return data
        return {}
    except Exception as e:
        logger.error(f"获取用户配置失败: {e}")
        return {}


# 新代码示例（使用工具）
@redis_fallback(default_value={})
async def get_user_config_new(user_id: str):
    """新代码：使用装饰器"""
    return await redis_get_json(f"user_config:{user_id}")


# ============================================================================
# 使用示例
# ============================================================================

async def main():
    """演示所有工具的使用"""
    
    # 1. 用户配置服务
    config_service = UserConfigService()
    config = await config_service.get_user_config("user_123")
    print(f"用户配置: {config}")
    
    # 2. 用户注册服务
    registration_service = UserRegistrationService()
    result = await registration_service.register_user(
        phone="13800138000",
        email="test@example.com",
        name="张三",
        password="secure_password"
    )
    print(f"注册结果: {result}")
    
    # 3. 外部 API 服务
    api_service = ExternalAPIService()
    api_result = await api_service.call_external_api(
        "https://api.example.com/users",
        {"name": "test"}
    )
    print(f"API 结果: {api_result}")
    
    # 4. 数据处理服务
    data_service = DataProcessingService()
    processed = await data_service.process_user_data("user_123")
    print(f"处理结果: {processed}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
