"""Main application entry point for the refactored Doubao MCP Server"""

import os
import sys
import uvicorn
from importlib import util as import_util
from src.config.settings import settings
from src.config.components.network_config import NetworkConfig
import logging

# ============================================================================
# Python Path Setup
# ============================================================================

project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# ============================================================================
# Network Configuration
# ============================================================================

# Apply network configuration (proxy settings)
network_config = NetworkConfig.from_env()
network_config.apply_to_environment()

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.logging.format
    )

def main():
    """Main function to run the application"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # 直接加载 src/api/routes.py 文件（避开 routes/ 目录冲突）
    routes_path = os.path.join(project_root, 'src/api/routes.py')
    spec = import_util.spec_from_file_location("routes_module", routes_path)
    routes_module = import_util.module_from_spec(spec)
    sys.modules['routes_module'] = routes_module
    spec.loader.exec_module(routes_module)
    app = routes_module.app

    # 挂载测试页面（独立模块，可安全删除整个 test_page/ 文件夹）
    try:
        from test_page import mount_test_page
        mount_test_page(app, project_root)
    except ImportError:
        logger.info("测试页面模块未找到，跳过挂载（如不需要可删除 test_page/ 整个文件夹）")

    # 监听所有网络接口，允许局域网/手机访问
    uvicorn.run(
        app,
        host="0.0.0.0",  # 允许外部访问
        port=8000,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
