"""Main application entry point for the refactored Doubao MCP Server"""

import os
import sys
import uvicorn
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

    # 导入 FastAPI app（从 routes 文件而不是 routes 包）
    # 使用 sys.modules 避免 routes/ 目录和 routes.py 冲突
    import importlib.util
    routes_path = os.path.join(project_root, 'src/api/routes.py')
    spec = importlib.util.spec_from_file_location("routes_app", routes_path)
    routes_module = importlib.util.module_from_spec(spec)
    sys.modules['routes_app'] = routes_module
    spec.loader.exec_module(routes_module)
    app = routes_module.app

    # 挂载测试页面
    try:
        from test_page import mount_test_page
        mount_test_page(app, project_root)
    except ImportError:
        logger.info("测试页面模块未找到，跳过挂载")

    logger.info(f"Server starting on http://0.0.0.0:8000")

    # 监听所有网络接口，允许局域网/手机访问
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用 reload，避免导入问题
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
