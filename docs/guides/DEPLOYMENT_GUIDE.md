# 生产环境部署指南

## 部署架构

```
                    ┌─────────────┐
                    │   Nginx/Caddy  │ (反向代理 + SSL)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Gunicorn  │ (WSGI服务器)
                    │  (多进程)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  FastAPI    │
                    │  (4核8进程)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌───────┐          ┌───────┐          ┌──────────┐
    │Redis  │          │ MySQL │          │  日志    │
    │(缓存) │          │(可选) │          │  (文件)  │
    └───────┘          └───────┘          └──────────┘
```

---

## 环境准备

### 系统要求

**最小配置**（测试/开发）：
- CPU: 2核
- 内存: 2GB
- 磁盘: 20GB
- Python: 3.10+

**推荐配置**（生产）：
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 50GB+ SSD

**操作系统**：
- Ubuntu 20.04+ / CentOS 8+
- macOS 12+

### 软件依赖

```bash
# 系统包
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip nginx redis-server

# Python 版本管理（可选）
curl https://pyenv.run | bash
pyenv install 3.11.7
pyenv global 3.11.7
```

---

## 快速部署

### 1. 准备代码

```bash
# 克隆代码
git clone <your-repo>
cd doubao_mcp_server

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
cp .env.example .env
vi .env  # 修改配置
```

### 2. 配置环境变量

```bash
# .env 配置示例
ARK_API_KEY=your_api_key_here
MODEL_NAME=doubao-seed-1-8-251228
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_TTL=86400

# 应用配置
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

### 3. 使用 Gunicorn 部署

```bash
# 安装 Gunicorn
pip install gunicorn uvicorn[standard]

# 启动服务（4进程，8线程）
gunicorn src.api.routes:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keepalive 5 \
    --bind 0.0.0.0:8000
```

### 4. 使用 Systemd 服务（推荐）

创建服务文件：

```bash
sudo vi /etc/systemd/system/doubao.service
```

```ini
[Unit]
Description=Doubao AI Matchmaker Service
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/doubao_mcp_server
Environment="PATH=/var/www/doubao_mcp_server/venv/bin"
ExecStart=/var/www/doubao_mcp_server/venv/bin/gunicorn \
    src.api.routes:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --timeout 120 \
    --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable doubao
sudo systemctl start doubao
sudo systemctl status doubao
```

---

## Nginx 反向代理配置

```nginx
# /etc/nginx/sites-available/doubao

upstream doubao_backend {
    server 127.0.0.1:8000;
    # 多个实例负载均衡
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name your-domain.com;

    # 强制 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;

    # SSL 优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 日志
    access_log /var/log/nginx/doubao-access.log;
    error_log /var/log/nginx/doubao-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # 超时配置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://doubao_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API v1 路由
    location /api/v1/ {
        proxy_pass http://doubao_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Redis 配置优化

```bash
# /etc/redis/redis.conf

# 最大内存限制
maxmemory 1gb

# 淘汰策略
maxmemory-policy allkeys-lru

# 持久化（可选）
save 900 1
save 300 10
save 60 10000

# AOF
appendonly yes
appendfsync everysec

# 重写压缩
aof-use-rdb-preamble yes
```

---

## 监控和日志

### 日志轮转

```bash
sudo vi /etc/logrotate.d/doubao
```

```
/var/log/doubao/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload doubao > /dev/null 2>&1 || true
    endscript
}
```

### 监控端点

```bash
# 健康检查
curl http://localhost:8000/health

# 服务状态
curl http://localhost:8000/api/v1/stats

# Redis 健康
redis-cli ping
```

---

## 部署检查清单

### 启动前检查

- [ ] 环境变量已配置（ARK_API_KEY 必填）
- [ ] Redis 服务已启动
- [ ] 日志目录已创建并可写
- [ ] 数据库连接正常（如果使用）
- [ ] SSL 证书已配置（HTTPS）

### 功能测试

- [ ] 健康检查端点正常
- [ ] API 文档可访问
- [ ] 对话功能正常
- [ ] Redis 连接正常
- [ ] 错误处理正常

### 性能检查

- [ ] 响应时间 < 2s
- [ ] 并发支持（1000 QPS+）
- [ ] 内存稳定
- [ ] CPU 使用率 < 80%

---

## 常见问题排查

### 1. Redis 连接失败

```bash
# 检查 Redis 状态
sudo systemctl status redis

# 检查 Redis 日志
sudo journalctl -u redis -f

# 测试连接
redis-cli ping
```

### 2. API 超时

```bash
# 检查进程状态
systemctl status doubao

# 查看日志
journalctl -u doubao -f
```

### 3. 内存不足

```bash
# 查看内存使用
free -h

# 查看 Gunicorn 内存
ps aux | grep gunicorn

# 增加交换空间（临时）
sudo dd if=/dev/zero of=/swapfile bs=1G count=2
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 备份策略

### 数据备份

```bash
# Redis 备份
redis-cli BGSAVE

# 备份到远程
redis-cli --rdb /tmp/dump.rdb
scp /tmp/dump.rdb backup:/redis/
```

### 应用备份

```bash
# 代码备份
tar -czf doubao-backup-$(date +%Y%m%d).tar.gz .

# 数据库备份（如果有）
mysqldump -u root -p databasename > backup.sql
```

---

## 更新部署

### 滚动更新（零停机）

```bash
# 1. 备份当前版本
cp -r doubao_mcp_server doubao_mcp_server.backup

# 2. 拉取新代码
git pull

# 3. 安装新依赖
pip install -r requirements.txt

# 4. 重启服务（逐个重启）
# 先重启 worker 1
systemctl reload doubao@1
sleep 5
# 重启 worker 2
systemctl reload doubao@2
```

---

## 安全检查

### SSL/TLS 配置

```bash
# 检查 SSL 证书
openssl x509 -in /etc/ssl/certs/your-domain.crt -text -noout

# 检查 SSL 配置
nginx -t
```

### 防火墙配置

```bash
# 开放必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

---

## 环境变量检查清单

```bash
# 必须配置
ARK_API_KEY=xxx           # AI模型密钥（必填）
MODEL_NAME=doubao-...     # 模型名称

# 可选配置
REDIS_ENABLED=true        # 启用Redis
REDIS_HOST=localhost      # Redis主机
REDIS_PORT=6379          # Redis端口
REDIS_PASSWORD=xxx       # Redis密码
REDIS_TTL=86400           # 数据过期时间

# 应用配置
HOST=0.0.0.0              # 监听地址
PORT=8000                 # 监听端口
DEBUG=false               # 调试模式
LOG_LEVEL=INFO             # 日志级别
```

---

完成部署后访问：
- API 文档：`https://your-domain.com/docs`
- 健康检查：`https://your-domain.com/health`
- API 信息：`https://your-domain.com/api`
