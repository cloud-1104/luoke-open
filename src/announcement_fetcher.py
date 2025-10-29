"""
多线程公告列表获取器
高频请求公告列表,成功后立即停止所有线程
"""

import threading
import time
from typing import Optional, Dict, Any, Callable
from src.api_client import APIClient
from src.logger import LoggerManager
from src.exceptions import InvalidSessionError


class AnnouncementFetcher:
    """公告获取器 - 使用多线程高频请求,成功后停止所有线程"""

    def __init__(self, api_client: APIClient, thread_count: int = 10):
        """
        初始化公告获取器

        Args:
            api_client: API客户端实例
            thread_count: 线程数量
        """
        self.api_client = api_client
        self.thread_count = thread_count
        self.logger = LoggerManager().get_logger()

        # 线程控制
        self.stop_flag = threading.Event()  # 停止标志
        self.success_flag = threading.Event()  # 成功标志
        self.result_lock = threading.Lock()  # 结果锁
        self.result: Optional[Dict[str, Any]] = None  # 存储成功的结果
        self.error: Optional[Exception] = None  # 存储错误信息

    def _fetch_worker(self, worker_id: int, progress_callback: Optional[Callable] = None) -> None:
        """
        单个工作线程的逻辑

        Args:
            worker_id: 线程ID
            progress_callback: 进度回调函数(用于GUI更新)
        """
        while not self.stop_flag.is_set():
            try:
                # 请求公告列表
                data = self.api_client.get_announcement_list()

                if data:
                    # 请求成功,设置成功标志并停止所有线程
                    with self.result_lock:
                        if not self.success_flag.is_set():
                            self.result = data
                            self.success_flag.set()
                            self.stop_flag.set()
                            self.logger.info(f"线程{worker_id}成功获取公告列表,停止所有请求")
                            if progress_callback:
                                progress_callback(f"成功获取公告列表")
                    break
                else:
                    # 请求失败,继续重试
                    self.logger.debug(f"线程{worker_id}请求失败,继续重试...")
                    if progress_callback:
                        progress_callback(f"线程{worker_id}正在重试...")

            except InvalidSessionError as e:
                # 登录会话无效,停止所有线程并记录错误
                with self.result_lock:
                    if self.error is None:
                        self.error = e
                        self.stop_flag.set()
                        self.logger.error(f"线程{worker_id}检测到登录会话失效,停止所有请求")
                        if progress_callback:
                            progress_callback(f"检测到登录会话失效")
                break
            except Exception as e:
                self.logger.error(f"线程{worker_id}发生异常: {e}")

            # 短暂延迟,避免过于频繁
            time.sleep(0.1)

    def fetch_announcement_list(
        self,
        keyword: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[int]:
        """
        多线程获取包含关键字的公告ID(无超时限制,持续重试直到成功)

        Args:
            keyword: 公告标题关键字(如"Day1")
            progress_callback: 进度回调函数

        Returns:
            成功返回公告ID,失败返回None
        """
        # 重置状态
        self.stop_flag.clear()
        self.success_flag.clear()
        self.result = None
        self.error = None

        self.logger.info(f"开始多线程获取公告列表(线程数: {self.thread_count}, 关键字: {keyword})")
        if progress_callback:
            progress_callback(f"启动{self.thread_count}个线程请求公告列表...")

        # 创建并启动线程
        threads = []
        for i in range(self.thread_count):
            thread = threading.Thread(
                target=self._fetch_worker,
                args=(i + 1, progress_callback),
                daemon=True
            )
            thread.start()
            threads.append(thread)

        # 无限等待直到成功或出错(移除超时限制,避免高峰期请求失败导致程序停摆)
        while not self.success_flag.is_set() and not self.stop_flag.is_set():
            time.sleep(0.1)

        # 停止所有线程
        self.stop_flag.set()

        # 等待所有线程结束
        for thread in threads:
            thread.join(timeout=1)

        # 检查是否有错误
        if self.error:
            raise self.error

        # 解析公告列表,查找匹配关键字的公告
        if self.result:
            announcement_list = self.result.get('announcementList', {}).get('list', [])

            for announcement in announcement_list:
                title = announcement.get('title', '')
                if keyword in title:
                    announcement_id = announcement.get('id')
                    self.logger.info(f"找到匹配公告: {title} (ID: {announcement_id})")
                    if progress_callback:
                        progress_callback(f"找到目标公告: {title}")
                    return announcement_id

            self.logger.warning(f"未找到包含关键字 '{keyword}' 的公告")
            if progress_callback:
                progress_callback(f"未找到包含关键字 '{keyword}' 的公告")
            return None

        return None
