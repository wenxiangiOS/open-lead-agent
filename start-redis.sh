#!/bin/bash
# 兼容入口：保留根目录命令，实际实现已收口到 scripts/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/scripts/start-redis.sh" "$@"
