"""
当前内部协议对象示例

用途：
- 展示当前主链路使用的 command/result 数据结构
- 供开发和调试时快速理解内部协议

说明：
- 这是本地对象构造示例
- 不是 HTTP 调用示例
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.modules.shared.models.use_case_models import (
    IngestMessageCommand,
    IngestMessageResult,
    ProcessChatTurnCommand,
    ProcessChatTurnResult,
)


def main() -> None:
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).isoformat()

    chat_command = ProcessChatTurnCommand(
        question="你好，我想找对象",
        account_id="protocol_chat_user_001",
        dialog_id="protocol_dialog_001",
        sex="女",
        timestamp=now,
    )

    ingest_command = IngestMessageCommand(
        account_id="protocol_xhs_user_001",
        dialog_id="protocol_xhs_dialog_001",
        message="她是哪里人呀",
        platform_msg_id="protocol_xhs_msg_001",
        timestamp=now,
        sex="男",
    )

    chat_result = ProcessChatTurnResult(
        success=True,
        response="你好呀，可以先跟我说说你的基本情况～",
        dialog_id="protocol_dialog_001",
        payload={
            "success": True,
            "response": "你好呀，可以先跟我说说你的基本情况～",
            "dialogId": "protocol_dialog_001",
        },
    )

    ingest_result = IngestMessageResult(
        success=True,
        accepted=True,
        status="queued",
        session_state="DEBOUNCING",
        seq=1,
        pending=1,
        max_pending=20,
        cancel_like=False,
        force_flush=False,
        payload={
            "success": True,
            "accepted": True,
            "status": "queued",
            "sessionState": "DEBOUNCING",
            "seq": 1,
            "pending": 1,
            "maxPending": 20,
            "cancelLike": False,
            "forceFlush": False,
        },
    )

    print("ProcessChatTurnCommand:")
    print(chat_command)
    print()
    print("ProcessChatTurnResult:")
    print(chat_result)
    print()
    print("IngestMessageCommand:")
    print(ingest_command)
    print()
    print("IngestMessageResult:")
    print(ingest_result)


if __name__ == "__main__":
    main()
