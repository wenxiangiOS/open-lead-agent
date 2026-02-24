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
"""1.将项目根目录和src / 目录加入Python的搜索路径，确保可以正确导入项目模块。"""
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# ============================================================================
# Network Configuration
# ============================================================================
"""2.网络配置 (第 23-25 行)"""
# Apply network configuration (proxy settings)
network_config = NetworkConfig.from_env()
network_config.apply_to_environment()
"""3.日志设置(第27 - 32行)"""
def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.logging.format
    )
"""4.主函数main()(第40 - 72行)
1.初始化日志 - 记录应用启动信息
2.动态导入FastAPIapp - 使用importlib从src / api / routes.py导入app，避免模块冲突
3.挂载测试页面 - 尝试挂载一个测试页面（可选）
4.启动服务器 - 使用uvicorn运行FastAPI应用
- 监听0.0.0.0: 8000（允许局域网访问）
- 禁用自动重载（reload = False）"""
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
