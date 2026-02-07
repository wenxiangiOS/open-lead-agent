#!/bin/bash
# 豆包MCP服务启动脚本 - 支持多实例部署

# 默认配置
WORKERS=${WORKERS:-1}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}

echo "========================================"
echo "豆包AI红娘服务启动中..."
echo "========================================"
echo "Worker数量: $WORKERS"
echo "监听地址: $HOST:$PORT"
echo "日志级别: $LOG_LEVEL"
echo ""

# 检查Redis
if [ "$REDIS_ENABLED" = "True" ] || [ "$REDIS_ENABLED" = "true" ]; then
    echo "✓ Redis模式已启用"
    echo "  Redis地址: ${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}"
else
    echo "⚠ 内存模式（仅适合单实例开发）"
    echo "  生产环境请启用Redis：REDIS_ENABLED=true"
fi
echo ""

# 启动服务
if [ "$WORKERS" -gt 1 ]; then
    echo "启动多实例模式..."
    uvicorn src.api.routes:app \
        --host $HOST \
        --port $PORT \
        --workers $WORKERS \
        --log-level $LOG_LEVEL \
        --access-log \
        --no-limit-concurrency
else
    echo "启动单实例模式..."
    uvicorn src.api.routes:app \
        --host $HOST \
        --port $PORT \
        --log-level $LOG_LEVEL \
        --access-log \
        --reload
fi
