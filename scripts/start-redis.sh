#!/bin/bash
# Redis 启动脚本（本地模拟阿里云环境）

echo "🚀 启动 Redis（模拟阿里云环境）..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker Desktop"
    echo "   下载地址: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 启动 Redis
echo "📦 启动 Redis 容器..."
docker-compose up -d

# 等待 Redis 就绪
echo "⏳ 等待 Redis 启动..."
sleep 3

# 检查 Redis 状态
if docker exec doubao-redis redis-cli ping &> /dev/null; then
    echo "✅ Redis 启动成功！"
    echo "   主机: localhost"
    echo "   端口: 6379"
    echo ""
    echo "📝 常用命令:"
    echo "   查看状态: docker-compose ps"
    echo "   查看日志: docker-compose logs redis"
    echo "   停止服务: docker-compose down"
    echo "   重启服务: docker-compose restart"
    echo "   清空数据: docker-compose down -v"
else
    echo "❌ Redis 启动失败"
    exit 1
fi
