"""
当前主链路官方示例：小红书异步 ingest 接口

用途：
- 演示如何调用 `/api/xiaohongshu/messages/ingest`
- 适用于正式异步入站链路调试

说明：
- 该接口只返回 accepted/queued 等状态
- 不会同步返回 AI 回复文本
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from urllib import request


BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/api/xiaohongshu/messages/ingest"


def build_payload() -> dict:
    tz = timezone(timedelta(hours=8))
    return {
        "accountId": "example_xhs_user_001",
        "dialogId": "example_xhs_dialog_001",
        "message": "她是哪里人呀",
        "platformMsgId": "example_xhs_msg_001",
        "timestamp": datetime.now(tz).isoformat(),
        "sex": "男",
    }


def main() -> None:
    payload = build_payload()
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=f"{BASE_URL}{API_PATH}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")

    print("POST", f"{BASE_URL}{API_PATH}")
    print("request:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("response:")
    print(body)


if __name__ == "__main__":
    main()
