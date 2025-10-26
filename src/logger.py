"""
日志管理模块
按日期保存日志文件,支持控制台和文件双输出
"""

import logging
import os
from datetime import datetime
from typing import Optional


class LoggerManager:
    """日志管理器 - 按日期保存日志,支持多级别输出"""

    def __init__(self, log_dir: str = "logs", name: str = "RocKingdom"):
        """
        初始化日志管理器

        Args:
            log_dir: 日志文件保存目录
            name: 日志记录器名称
        """
        self.log_dir = log_dir
        self.logger_name = name
        self.logger: Optional[logging.Logger] = None

        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def get_logger(self) -> logging.Logger:
        """
        获取或创建日志记录器

        Returns:
            日志记录器实例
        """
        if self.logger is not None:
            return self.logger

        # 创建日志记录器
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)

        # 清除已有的处理器(避免重复)
        self.logger.handlers.clear()

        # 创建按日期命名的日志文件
        log_filename = datetime.now().strftime("%Y-%m-%d.log")
        log_filepath = os.path.join(self.log_dir, log_filename)

        # 文件处理器 - 保存所有级别的日志
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # 控制台处理器 - 只显示INFO及以上级别
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        return self.logger

    def info(self, message: str) -> None:
        """记录INFO级别日志"""
        self.get_logger().info(message)

    def debug(self, message: str) -> None:
        """记录DEBUG级别日志"""
        self.get_logger().debug(message)

    def warning(self, message: str) -> None:
        """记录WARNING级别日志"""
        self.get_logger().warning(message)

    def error(self, message: str) -> None:
        """记录ERROR级别日志"""
        self.get_logger().error(message)

    def critical(self, message: str) -> None:
        """记录CRITICAL级别日志"""
        self.get_logger().critical(message)
