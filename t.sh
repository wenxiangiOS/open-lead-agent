#!/bin/bash
# 兼容入口：统一复用 ./t

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/t" "$@"
