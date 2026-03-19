"""
当前主链路官方示例：同步聊天接口

用途：
- 演示如何调用 `/api/doubao/chat`
- 适用于本地调试、回归验证、应急直连

说明：
- 这是当前主链路示例
- 不是消息队列 ingest 示例
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from urllib import request


BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/api/doubao/chat"


def build_payload() -> dict:
    tz = timezone(timedelta(hours=8))
    return {
        "question": "你好，我想找对象",
        "accountId": "example_chat_user_001",
        "dialogId": "example_dialog_001",
        "sex": "女",
        "timestamp": datetime.now(tz).isoformat(),
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
