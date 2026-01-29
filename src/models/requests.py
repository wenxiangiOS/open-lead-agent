"""Request models for the API"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class ChatRequest(BaseModel):
    """Chat request model"""

    question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    accountId: str = Field(..., min_length=1, max_length=100, description="用户ID")
    dialogId: Optional[str] = Field(None, description="对话ID")
    sex: str = Field("女", description="用户性别")
    timestamp: Optional[str] = Field(None, description="时间戳")

    @validator('question')
    def validate_question(cls, v):
        """Validate question"""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

    @validator('accountId')
    def validate_account_id(cls, v):
        """Validate account ID"""
        if not v or not v.strip():
            raise ValueError("Account ID cannot be empty")
        return v.strip()

    @validator('sex')
    def validate_sex(cls, v):
        """Validate sex"""
        valid_values = ["男", "女", "other", "unknown"]
        if v not in valid_values:
            raise ValueError(f"Sex must be one of: {valid_values}")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp"""
        if v:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("Invalid timestamp format")
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserPreferenceRequest(BaseModel):
    """User preference update request model"""

    user_id: str = Field(..., description="用户ID")
    preference_key: str = Field(..., description="偏好键")
    preference_value: str = Field(..., description="偏好值")


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="服务状态")
    message: str = Field(..., description="状态消息")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(default_factory=datetime.now().isoformat, description="时间戳")


class ChatResponse(BaseModel):
    """Chat response model"""

    success: bool = Field(..., description="是否成功")
    response: str = Field(..., description="AI回复")
    dialogId: Optional[str] = Field(None, description="对话ID")
    timestamp: str = Field(default_factory=datetime.now().isoformat, description="时间戳")
    error: Optional[str] = Field(None, description="错误信息")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度")


class UserProfileRequest(BaseModel):
    """User profile request model"""

    user_id: str = Field(..., description="用户ID")
    age: Optional[int] = Field(None, ge=18, le=100, description="年龄")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    occupation: Optional[str] = Field(None, max_length=100, description="职业")
    interests: Optional[list] = Field(None, description="兴趣爱好")


class ConversationHistoryRequest(BaseModel):
    """Conversation history request model"""

    user_id: str = Field(..., description="用户ID")
    limit: Optional[int] = Field(10, ge=1, le=50, description="返回记录数量")
    offset: Optional[int] = Field(0, ge=0, description="偏移量")


class ConversationHistoryResponse(BaseModel):
    """Conversation history response model"""

    user_id: str = Field(..., description="用户ID")
    conversations: list = Field(..., description="对话历史")
    total_count: int = Field(..., description="总记录数")
    limit: int = Field(..., description="限制数量")
    offset: int = Field(..., description="偏移量")


class UserInsightsResponse(BaseModel):
    """User insights response model"""

    user_id: str = Field(..., description="用户ID")
    insights: dict = Field(..., description="用户洞察")
    preferences: dict = Field(..., description="用户偏好")
    conversation_summary: dict = Field(..., description="对话摘要")


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: str = Field(default_factory=datetime.now().isoformat, description="时间戳")
    details: Optional[dict] = Field(None, description="错误详情")


class RateLimitResponse(BaseModel):
    """Rate limit response model"""

    success: bool = Field(..., description="是否成功")
    remaining_requests: int = Field(..., description="剩余请求数")
    reset_time: str = Field(..., description="重置时间")
    limit: int = Field(..., description="限制数量")


class SystemInfoResponse(BaseModel):
    """System info response model"""

    service_name: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本")
    environment: str = Field(..., description="环境")
    uptime: str = Field(..., description="运行时间")
    memory_usage: dict = Field(..., description="内存使用")
    cpu_usage: float = Field(..., description="CPU使用率")