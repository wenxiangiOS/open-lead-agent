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
"""这是从环境变量里读取网络配置"""
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
2.导入 FastAPI app
3.挂载测试页面 - 尝试挂载一个测试页面（可选）
4.启动服务器 - 使用uvicorn运行FastAPI应用
- 监听0.0.0.0: 8000（允许局域网访问）
- 禁用自动重载（reload = False）"""
def main():
    """Main function to run the application"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # 导入 FastAPI app
    from src.api.app import app

    # 挂载测试页面
    try:
        from test_page import mount_test_page
        mount_test_page(app, project_root)
    except ImportError:
        logger.info("测试页面模块未找到，跳过挂载")

    logger.info(f"Server starting on http://0.0.0.0:8000")

    # 监听所有网络接口，允许局域网/手机访问
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,  # 禁用 reload，避免导入问题
            log_level=settings.log_level.lower()
        )
    except KeyboardInterrupt:
        # Uvicorn 在第二次 Ctrl+C 强制退出时会重新抛出 KeyboardInterrupt；
        # 这里吞掉顶层堆栈，保留正常的停机日志即可。
        logger.info("Server stopped by user")

if __name__ == "__main__":
    main()
