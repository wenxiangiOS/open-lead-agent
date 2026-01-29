"""Main application entry point for the refactored Doubao MCP Server"""

import os
import sys
import uvicorn
from src.api.routes import app
from src.config.settings import settings
import logging

# Disable proxy to avoid network issues
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# Ensure src directory is in Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )

def main():
    """Main function to run the application"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # 使用备用端口 8002 避免冲突
    uvicorn.run(
        app,
        host=settings.host,
        port=8000,  # 使用端口 8002 而不是 8000
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
