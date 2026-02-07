"""Network Configuration Component"""

import os
from typing import Optional
from pydantic import Field, BaseModel


class NetworkConfig(BaseModel):
    """
    网络配置

    统一管理代理等网络相关配置
    """

    # 是否禁用代理
    disable_proxy: bool = Field(
        default=True,
        description="是否禁用代理（推荐在服务器环境中禁用以避免网络问题）"
    )

    # HTTP 代理地址（如果启用代理）
    http_proxy: Optional[str] = Field(
        default=None,
        description="HTTP 代理地址"
    )

    # HTTPS 代理地址（如果启用代理）
    https_proxy: Optional[str] = Field(
        default=None,
        description="HTTPS 代理地址"
    )

    # NO_PROXY 配置
    no_proxy: Optional[str] = Field(
        default="*",
        description="不使用代理的地址列表"
    )

    @classmethod
    def from_env(cls) -> "NetworkConfig":
        """从环境变量加载网络配置"""
        disable_proxy = os.getenv("DISABLE_PROXY", "True").lower() in ("true", "1", "yes")

        return cls(
            disable_proxy=disable_proxy,
            http_proxy=os.getenv("HTTP_PROXY"),
            https_proxy=os.getenv("HTTPS_PROXY"),
            no_proxy=os.getenv("NO_PROXY", "*")
        )

    def apply_to_environment(self) -> None:
        """
        将网络配置应用到环境变量

        这应该在应用启动时调用，确保所有网络请求使用正确的配置
        """
        import os as _os

        if self.disable_proxy:
            # 禁用代理
            _os.environ['NO_PROXY'] = self.no_proxy or '*'
            _os.environ['HTTP_PROXY'] = ''
            _os.environ['HTTPS_PROXY'] = ''
        else:
            # 启用代理
            if self.http_proxy:
                _os.environ['HTTP_PROXY'] = self.http_proxy
            if self.https_proxy:
                _os.environ['HTTPS_PROXY'] = self.https_proxy
            if self.no_proxy:
                _os.environ['NO_PROXY'] = self.no_proxy
