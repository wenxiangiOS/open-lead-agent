"""
打包后的可执行文件配置读取模块
"""
import os
import json
from pathlib import Path

# 配置文件路径（与可执行文件同级）
CONFIG_FILE = "xiaoyuan_config.json"


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / CONFIG_FILE

    # 默认配置
    default_config = {
        "ARK_API_KEY": "",
        "MODEL_NAME": "doubao-seed-1-8-251228",
        "BASE_URL": "https://ark.cn-beijing.volces.com/api/v3"
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except Exception:
            pass

    return default_config


def save_config(config):
    """保存配置文件"""
    config_path = Path(__file__).parent / CONFIG_FILE
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def setup_config():
    """首次运行时创建配置文件"""
    config_path = Path(__file__).parent / CONFIG_FILE

    if not config_path.exists():
        print("=" * 50)
        print("欢迎使用小缘AI红娘！")
        print("=" * 50)
        print("\n首次运行，请配置API密钥：")
        api_key = input("请输入豆包API密钥: ").strip()

        if not api_key:
            print("\n错误：API密钥不能为空！")
            return False

        config = {
            "ARK_API_KEY": api_key,
            "MODEL_NAME": "doubao-seed-1-8-251228",
            "BASE_URL": "https://ark.cn-beijing.volces.com/api/v3"
        }

        save_config(config)
        print("\n配置已保存！现在可以开始使用了。")
        return True

    return True
