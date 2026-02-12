"""
测试页面功能模块

独立的测试页面功能，可安全删除整个文件夹而不影响主项目。

配置：在 .env 中设置 ENABLE_TEST_PAGE=true

使用方式：
    from test_page import mount_test_page
    mount_test_page(app, project_root)

删除方式：
    rm -rf test_page/
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def mount_test_page(
    app: FastAPI,
    project_root: str,
    enabled: Optional[bool] = None
) -> bool:
    """
    挂载测试页面到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
        project_root: 项目根目录路径
        enabled: 是否启用（None 时从环境变量读取）

    Returns:
        bool: 是否成功挂载
    """
    # 从环境变量读取配置（如果没有显式传入）
    if enabled is None:
        enabled = os.getenv("ENABLE_TEST_PAGE", "false").lower() in ("true", "1", "yes", "on")

    if not enabled:
        logger.info("测试页面功能已禁用 (ENABLE_TEST_PAGE=false)")
        return False

    # 构建静态文件完整路径（test_page/static）
    static_dir = os.path.join(project_root, "test_page", "static")

    # 检查目录是否存在
    if not os.path.exists(static_dir):
        logger.warning(f"测试页面目录不存在: {static_dir}")
        return False

    # 挂载静态文件
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"✅ 测试页面已启用: /static -> {static_dir}")

        # 获取本机IP用于显示访问地址
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "你的IP"

        logger.info(f"📱 访问地址:")
        logger.info(f"   - 本地: http://localhost:8000/static/mobile_final.html")
        logger.info(f"   - 局域网: http://{local_ip}:8000/static/mobile_final.html")

        return True

    except Exception as e:
        logger.error(f"挂载测试页面失败: {e}")
        return False
