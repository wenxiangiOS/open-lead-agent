"""
当前主链路官方示例：小红书 replies 拉取接口

用途：
- 演示如何调用 `GET /api/xiaohongshu/messages/replies`
- 适用于异步投递结果轮询
"""

from __future__ import annotations

import json
from urllib import parse, request


BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/api/xiaohongshu/messages/replies"


def build_url(account_id: str, after: int = 0, limit: int = 20) -> str:
    query = parse.urlencode(
        {
            "accountId": account_id,
            "after": after,
            "limit": limit,
        }
    )
    return f"{BASE_URL}{API_PATH}?{query}"


def main() -> None:
    url = build_url(account_id="example_xhs_user_001", after=0, limit=20)
    req = request.Request(url=url, method="GET")

    with request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    print("GET", url)
    print("response:")
    print(json.dumps(body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
