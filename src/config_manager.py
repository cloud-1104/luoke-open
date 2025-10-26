"""
配置管理模块
负责读取、保存和验证配置文件
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理器 - 处理配置文件的读取、保存和默认值"""

    DEFAULT_CONFIG = {
        "miniapp_authorization": "",  # 小程序Authorization token
        "web_cookies": [],  # 网页端Cookie列表,支持多个Cookie并发兑换
        "announcement_keyword": "Day1",  # 公告关键字(如Day1, Day2...)
        "use_ocr": False,  # 是否使用OCR识别验证码
        "ocr_max_retries": 3,  # OCR识别最大重试次数
        "redeem_max_retries": 5,  # 兑换接口最大重试次数(验证码错误时)
        "request_threads": 10,  # 请求公告列表的线程数
        "request_timeout": 5,  # HTTP请求超时时间(秒)
        "poll_interval": 1.0,  # 轮询间隔时间(秒),支持小数如0.1, 0.5, 1.0
        "use_proxy": False,  # 是否使用代理(仅用于网页端请求:验证码、兑换)
        "proxy_host": "",  # 代理主机地址(如: u985.kdltps.com)
        "proxy_port": 0  # 代理端口(如: 15818)
    }

    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """
        加载配置文件,如果不存在则创建默认配置

        Returns:
            配置字典
        """
        if not os.path.exists(self.config_path):
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
            return self.config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 合并默认配置,确保所有字段都存在
                self.config = self.DEFAULT_CONFIG.copy()
                self.config.update(loaded_config)
                return self.config
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")

    def save(self) -> None:
        """
        保存当前配置到文件

        Raises:
            Exception: 保存失败时抛出异常
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值

        Args:
            key: 配置项键名
            default: 默认值

        Returns:
            配置项的值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置项的值

        Args:
            key: 配置项键名
            value: 配置项的值
        """
        self.config[key] = value

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        验证配置是否完整

        Returns:
            (是否有效, 错误信息)
        """
        # 检查必填字段
        if not self.config.get("miniapp_authorization"):
            return False, "小程序Authorization未配置"

        web_cookies = self.config.get("web_cookies", [])
        if not web_cookies or len(web_cookies) == 0:
            return False, "至少需要添加一个网页端Cookie"

        if not self.config.get("announcement_keyword"):
            return False, "公告关键字未配置"

        return True, None
