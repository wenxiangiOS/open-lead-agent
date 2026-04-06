"""Chat routes"""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from src.config.settings import settings
from src.models.requests import ChatResponse, ErrorResponse, ChatRequest
from src.modules.shared.models.use_case_models import ProcessChatTurnCommand
from src.services.core.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["对话"])

# Service will be injected during app initialization
chat_service: ChatService = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def init_service(service: ChatService):
    """Initialize chat service"""
    global chat_service
    chat_service = service


def _http_detail(error_code: str, error: str, **details: Any) -> Dict[str, Any]:
    return {
        "error": error,
        "error_code": error_code,
        "details": details,
    }


async def _process_chat_via_protocol(request_model: ChatRequest) -> Dict[str, Any]:
    use_case = getattr(chat_service, "process_chat_turn_use_case", None)
    if use_case is not None and hasattr(use_case, "execute_command"):
        result = await use_case.execute_command(
            ProcessChatTurnCommand(
                question=request_model.question,
                account_id=request_model.accountId,
                dialog_id=request_model.dialogId,
                sex=request_model.sex,
                timestamp=request_model.timestamp,
            )
        )
        return result.payload or {
            "success": result.success,
            "response": result.response,
            "dialogId": result.dialog_id,
        }
    return await chat_service.process_chat_request(request_model)


@router.post(
    "/api/doubao/chat",
    summary="AI红娘对话",
    description="""
与AI红娘小缘进行对话，收集用户信息并提供匹配服务。

**功能特性：**
- 智能信息收集：称呼、性别、年龄、身高、地区、婚况、联系方式
- 自然对话流程：根据已收集信息智能调整问题
- 联系方式验证：自动验证手机号格式
- 拒绝检测：识别用户拒绝并切换话题
- 对话历史维护：保持上下文连贯性

**对话流程：**
1. 开场打招呼并询问称呼
2. 询问性别、年龄等基本信息
3. 收集地区、婚况等详细信息
4. 最后询问联系方式（手机号/微信）
5. 完成收集后提示等待匹配
""",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "成功返回AI回复",
        },
        400: {
            "description": "请求参数错误",
            "model": ErrorResponse
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def chat(request: Dict[str, Any]) -> ChatResponse:
    """AI红娘对话端点，处理用户消息并返回AI回复"""
    if chat_service is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("SERVICE_NOT_INITIALIZED", "service_not_initialized", route="chat"),
        )

    try:
        # 将 dict 转换为 ChatRequest 模型
        chat_request = ChatRequest(**request)
        logger.info(f"Processing chat request from user: {chat_request.accountId}")

        # 检查是否需要返回调试信息（仅测试页面使用）
        debug_requested = bool(request.get("debug", False))
        debug_mode = debug_requested and bool(getattr(settings, "debug", False))
        if debug_requested and not debug_mode:
            logger.warning("[DEBUG] debug payload ignored in non-debug mode")
        logger.info(f"[DEBUG] debug_mode={debug_mode}, request keys={list(request.keys())}")

        # 如果是调试模式，先获取追踪前的追问次数（用于判断"已跳过"）
        field_ask_count_before = None
        if debug_mode:
            try:
                profile_result = await chat_service.get_user_profile(chat_request.accountId)
                profile_before = profile_result.get("profile", {})
                field_ask_count_before = profile_before.get("field_ask_count", {})
            except Exception as e:
                logger.warning(f"Failed to get profile before tracking: {e}")

        # Process the chat request（内部会追踪 AI 询问的字段）
        result = await _process_chat_via_protocol(chat_request)

        # 如果是调试模式，获取最新的用户信息（包含刚提取的数据）
        if debug_mode:
            try:
                profile_result = await chat_service.get_user_profile(chat_request.accountId)
                profile_after = profile_result.get("profile", {})
                # 调试：打印 profile 中的联系方式相关字段
                logger.info(f"[DEBUG] profile_after keys: {list(profile_after.keys())}")
                logger.info(f"[DEBUG] wechat_ask_count={profile_after.get('wechat_ask_count')}, rejected_wechat={profile_after.get('rejected_wechat')}")
                logger.info(f"[DEBUG] phone_ask_count={profile_after.get('phone_ask_count')}, rejected_phone={profile_after.get('rejected_phone')}")
                # 使用追踪前的追问次数 + 追踪后的字段值
                # 这样：用户刚提供的信息立即显示，但"已跳过"状态在下一轮才显示
                debug_info = _format_debug_info_with_ask_count(profile_after, field_ask_count_before)
                logger.info(f"[DEBUG] debug_info: {debug_info}")
                result["debug_info"] = debug_info
            except Exception as e:
                logger.warning(f"Failed to get debug info: {e}")
                result["debug_info"] = None

        # Convert to response model
        return ChatResponse(**result)

    except (ValueError, ValidationError) as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail=_http_detail(
                "CHAT_REQUEST_VALIDATION_ERROR",
                "chat_request_validation_failed",
                route="chat",
                message=str(e),
            ),
        )
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("CHAT_PROCESSING_ERROR", "chat_processing_failed", route="chat"),
        )


def _format_contact_display(profile: Dict[str, Any]) -> str:
    """
    格式化联系方式显示（简化版）

    状态定义：
    - 已留：有值
    - 已拒绝：rejected_xxx=True
    - 争取中：xxx_persuasion_attempted=True 且无值且未拒绝
    - 未问：不显示

    Returns:
        str: 联系方式显示字符串
    """
    parts = []

    # === 微信号部分 ===
    wechat = profile.get("wechat")
    rejected_wechat = profile.get("rejected_wechat", False)
    wechat_ask_count = profile.get("wechat_ask_count", 0)

    if wechat:
        # 已留
        parts.append(f"微信:{wechat}")
    elif rejected_wechat:
        # 已拒绝
        parts.append("不愿留微信")
    elif wechat_ask_count >= 1:
        # 争取中
        parts.append("微信争取中")
    # 未问：不显示

    # === 电话部分 ===
    phone = profile.get("contact")
    rejected_phone = profile.get("rejected_phone", False)
    phone_ask_count = profile.get("phone_ask_count", 0)

    if phone:
        # 已留
        parts.append(f"电话:{phone}")
    elif rejected_phone:
        # 已拒绝
        parts.append("不愿留电话")
    elif phone_ask_count >= 1:
        # 争取中
        parts.append("电话争取中")
    # 未问：不显示

    # === 组合结果 ===
    if parts:
        return ", ".join(parts)
    return "未留"


def _format_debug_info_with_ask_count(profile: Dict[str, Any], field_ask_count_before: Dict[str, int] = None) -> str:
    """
    格式化用户已收集的信息为调试显示字符串

    Args:
        profile: 追踪后的完整 profile（包含刚提取的数据）
        field_ask_count_before: 追踪前的追问次数（用于判断"已跳过"状态）

    设计：
        - 字段值使用追踪后的数据 → 用户刚提供的信息立即显示
        - 追问次数使用追踪前的数据 → "已跳过"状态在下一轮才显示
    """
    # 字段中文名映射（不包含 wechat，联系方式统一显示在 contact）
    field_names = {
        "sex": "性别",
        "last_name": "称呼",
        "age": "年龄",
        "height": "身高",
        "weight": "体重",
        "location": "坐标",
        "education": "学历",
        "marital_status": "婚况",
        "monthly_income": "月薪",
        "occupation": "职业",
        "contact": "联系方式",
        "partner_gender_preference": "择偶性别偏好",
        "partner_requirement": "择偶要求",
    }

    # 使用追踪前的追问次数（如果没有提供，则使用 profile 中的）
    field_ask_count = field_ask_count_before if field_ask_count_before is not None else profile.get("field_ask_count", {})
    skip_guard_enabled = _env_bool("MQ_SKIP_GUARD_ENABLED", True)

    # 使用换行格式显示
    lines = ["\n[已收集信息]"]
    for field, name in field_names.items():
        # 特殊处理 contact 字段：使用简化版显示逻辑
        if field == "contact":
            contact_display = _format_contact_display(profile)
            lines.append(f"  {name}: {contact_display}")
        else:
            value = profile.get(field)
            if value is not None:
                lines.append(f"  {name}: {value}")
            else:
                # 检查是否被跳过（用户明确拒绝）
                skipped = profile.get("skipped_fields", {})
                if skipped.get(field, False):
                    lines.append(f"  {name}: 跳过")
                # 检查是否问了多次未回答（智能追问跳过）- 使用追踪前的追问次数
                elif (not skip_guard_enabled) and field_ask_count.get(field, 0) >= 2:
                    count = field_ask_count.get(field, 0)
                    lines.append(f"  {name}: 已跳过({count}次未答)")
                else:
                    lines.append(f"  {name}: 未留")

    return "\n".join(lines)


def _format_debug_info(profile: Dict[str, Any]) -> str:
    """格式化用户已收集的信息为调试显示字符串"""
    # 字段中文名映射（不包含 wechat，联系方式统一显示在 contact）
    field_names = {
        "sex": "性别",
        "last_name": "称呼",
        "age": "年龄",
        "height": "身高",
        "weight": "体重",
        "location": "坐标",
        "education": "学历",
        "marital_status": "婚况",
        "monthly_income": "月薪",
        "occupation": "职业",
        "contact": "联系方式",
        "partner_gender_preference": "择偶性别偏好",
        "partner_requirement": "择偶要求",
    }

    # 获取追问次数（用于显示"已跳过(N次未答)"）
    field_ask_count = profile.get("field_ask_count", {})
    skip_guard_enabled = _env_bool("MQ_SKIP_GUARD_ENABLED", True)

    # 使用换行格式显示
    lines = ["\n[已收集信息]"]
    for field, name in field_names.items():
        # 特殊处理 contact 字段：使用简化版显示逻辑
        if field == "contact":
            contact_display = _format_contact_display(profile)
            lines.append(f"  {name}: {contact_display}")
        else:
            value = profile.get(field)
            if value is not None:
                lines.append(f"  {name}: {value}")
            else:
                # 检查是否被跳过（用户明确拒绝）
                skipped = profile.get("skipped_fields", {})
                if skipped.get(field, False):
                    lines.append(f"  {name}: 跳过")
                # 检查是否问了多次未回答（智能追问跳过）
                elif (not skip_guard_enabled) and field_ask_count.get(field, 0) >= 2:
                    count = field_ask_count.get(field, 0)
                    lines.append(f"  {name}: 已跳过({count}次未答)")
                else:
                    lines.append(f"  {name}: 未留")

    return "\n".join(lines)


@router.post(
    "/api/doubao/welcome",
    summary="生成欢迎消息",
    description="为新用户生成欢迎消息，重置对话状态并开始新的信息收集流程",
    responses={
        200: {
            "description": "成功生成欢迎消息",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "你好呀～我是同城脱单联盟的小缘，帮男生女生脱单牵线的～方便告诉我怎么称呼你呢，称呼你小哥哥还是小姐姐呀哒~",
                        "conversation_reset": True
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def welcome(user_id: str) -> Dict[str, Any]:
    """为新用户生成欢迎消息"""
    if chat_service is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("SERVICE_NOT_INITIALIZED", "service_not_initialized", route="welcome"),
        )

    try:
        logger.info(f"Generating welcome for user: {user_id}")

        # Generate welcome message
        result = await chat_service.generate_welcome_message(user_id)

        return result

    except Exception as e:
        logger.error(f"Welcome generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("WELCOME_GENERATION_ERROR", "welcome_generation_failed", route="welcome"),
        )


@router.post(
    "/api/doubao/feedback",
    summary="用户反馈",
    description="收集用户对AI回复的反馈，用于改进服务质量",
    responses={
        200: {
            "description": "成功处理反馈",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "感谢您的反馈！",
                        "feedback_recorded": True
                    }
                }
            }
        },
        400: {
            "description": "反馈参数错误",
            "model": ErrorResponse
        },
        500: {
            "description": "服务器内部错误",
            "model": ErrorResponse
        }
    }
)
async def feedback(
    user_id: str,
    message: str,
    rating: int,
    feedback_type: str = "response"
) -> Dict[str, Any]:
    """处理用户反馈"""
    if chat_service is None:
        raise HTTPException(
            status_code=500,
            detail=_http_detail("SERVICE_NOT_INITIALIZED", "service_not_initialized", route="feedback"),
        )

    try:
        logger.info(f"Processing feedback from user: {user_id}")

        # Process feedback
        result = await chat_service.process_user_feedback(
            user_id, message, rating, feedback_type
        )

        return result

    except Exception as e:
        logger.error(f"Feedback processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_http_detail("FEEDBACK_PROCESSING_ERROR", "feedback_processing_failed", route="feedback"),
        )
