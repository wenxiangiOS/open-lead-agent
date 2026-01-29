"""Configuration settings module"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, BaseModel


class Settings(BaseModel):
    """Application settings with environment variable support"""

    # API Configuration
    api_key: str = Field(default="", description="Doubao API Key")
    model_name: str = Field(default="doubao-seed-1-8-251228", description="Model name")
    base_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3", description="Base URL")

    # Volcengine Configuration
    volc_access_key: Optional[str] = Field(default=None, description="Volc access key")
    volc_secret_key: Optional[str] = Field(default=None, description="Volc secret key")

    # Application Configuration
    app_name: str = Field(default="小缘AI红娘服务", description="App name")
    app_version: str = Field(default="2.0.0", description="App version")
    debug: bool = Field(default=False, description="Debug mode")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Host")
    port: int = Field(default=8000, description="Port")
    reload: bool = Field(default=False, description="Auto reload")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Rate limiting enabled")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests")
    rate_limit_window: int = Field(default=60, description="Rate limit window")

    def model_post_init(self, ctx: dict) -> None:
        """Load environment variables after model initialization"""
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        # Override with environment values
        if os.getenv('ARK_API_KEY'):
            self.api_key = os.getenv('ARK_API_KEY')
        if os.getenv('MODEL_NAME'):
            self.model_name = os.getenv('MODEL_NAME')
        if os.getenv('HOST'):
            self.host = os.getenv('HOST')
        if os.getenv('PORT'):
            try:
                self.port = int(os.getenv('PORT'))
            except ValueError:
                pass
        if os.getenv('DEBUG'):
            self.debug = os.getenv('DEBUG').lower() in ('true', '1', 'yes')

        # Load optional settings
        if os.getenv('VOLC_ACCESS_KEY'):
            self.volc_access_key = os.getenv('VOLC_ACCESS_KEY')
        if os.getenv('VOLC_SECRET_KEY'):
            self.volc_secret_key = os.getenv('VOLC_SECRET_KEY')


# Global settings instance
settings = Settings()
settings.model_post_init({})  # Load environment variables after initialization
