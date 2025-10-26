"""
兑换逻辑主控制器
整合所有模块,完成完整的兑换流程
"""

import threading
import time
from typing import Optional, Callable
from src.config_manager import ConfigManager
from src.logger import LoggerManager
from src.api_client import APIClient
from src.announcement_fetcher import AnnouncementFetcher
from src.password_extractor import PasswordExtractor
from src.cookie_pool import CookiePool


class RedeemController:
    """兑换控制器 - 整合所有流程的主控制器"""

    def __init__(self, config: ConfigManager):
        """
        初始化兑换控制器

        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.logger = LoggerManager().get_logger()

        # 初始化API客户端(仅用于获取公告,不用于兑换)
        self.api_client = APIClient(
            miniapp_auth=config.get("miniapp_authorization", ""),
            web_cookie="",  # 公告接口不需要Cookie
            timeout=config.get("request_timeout", 5)
        )

        # 初始化公告获取器
        self.announcement_fetcher = AnnouncementFetcher(
            api_client=self.api_client,
            thread_count=config.get("request_threads", 10)
        )

        # 初始化口令提取器
        self.password_extractor = PasswordExtractor()

        # 初始化Cookie池
        web_cookies = config.get("web_cookies", [])
        if web_cookies:
            self.cookie_pool = CookiePool(
                miniapp_auth=config.get("miniapp_authorization", ""),
                web_cookies=web_cookies,
                use_ocr=config.get("use_ocr", False),
                ocr_max_retries=config.get("ocr_max_retries", 3),
                timeout=config.get("request_timeout", 5),
                use_proxy=config.get("use_proxy", False),
                proxy_host=config.get("proxy_host", ""),
                proxy_port=config.get("proxy_port", 0)
            )
        else:
            self.cookie_pool = None

    def execute(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
        captcha_callback: Optional[Callable[[bytes, str], str]] = None,
        stop_flag: Optional[threading.Event] = None
    ) -> dict:
        """
        执行完整的兑换流程

        Args:
            progress_callback: 进度回调函数,用于更新GUI状态
            captcha_callback: 验证码显示和输入回调函数(接收图片字节和OCR结果,返回验证码文本)
            stop_flag: 暂停标志Event对象

        Returns:
            兑换结果字典 {"success": bool, "message": str, "data": dict}
        """
        try:
            # 获取轮询间隔配置
            poll_interval = self.config.get("poll_interval", 1.0)

            # 步骤1: 持续轮询获取公告列表并查找目标公告
            self._update_progress(progress_callback, "正在获取公告列表...")
            self.logger.info("=" * 50)
            self.logger.info("开始执行兑换流程")
            self.logger.info("=" * 50)

            keyword = self.config.get("announcement_keyword", "")
            if not keyword:
                return self._error_result("公告关键字未配置")

            # 持续轮询直到找到目标公告
            announcement_id = None
            poll_attempt = 0

            while announcement_id is None:
                # 检查暂停标志
                if stop_flag and stop_flag.is_set():
                    return self._error_result("用户取消执行")

                poll_attempt += 1
                self.logger.info(f"第{poll_attempt}次轮询公告列表...")
                self._update_progress(
                    progress_callback,
                    f"正在轮询公告列表(第{poll_attempt}次)..."
                )

                announcement_id = self.announcement_fetcher.fetch_announcement_list(
                    keyword=keyword,
                    progress_callback=progress_callback
                )

                if announcement_id:
                    self.logger.info(f"✓ 找到目标公告! (轮询{poll_attempt}次)")
                    break

                # 未找到,等待后继续轮询
                self.logger.warning(f"未找到包含关键字 '{keyword}' 的公告,{poll_interval}秒后重试...")
                self._update_progress(
                    progress_callback,
                    f"未找到目标公告,{poll_interval}秒后继续轮询(已尝试{poll_attempt}次)..."
                )
                time.sleep(poll_interval)  # 使用配置的轮询间隔

            # 步骤2: 持续获取公告详情直到成功
            detail = None
            detail_attempt = 0

            while detail is None:
                # 检查暂停标志
                if stop_flag and stop_flag.is_set():
                    return self._error_result("用户取消执行")

                detail_attempt += 1
                self._update_progress(
                    progress_callback,
                    f"正在获取公告详情(第{detail_attempt}次尝试,ID: {announcement_id})..."
                )
                self.logger.info(f"第{detail_attempt}次尝试获取公告详情,ID: {announcement_id}")

                detail = self.api_client.get_announcement_detail(announcement_id)

                if detail:
                    self.logger.info(f"✓ 成功获取公告详情!")
                    break

                # 获取失败,等待后重试
                self.logger.warning(f"获取公告详情失败,{poll_interval}秒后重试...")
                self._update_progress(
                    progress_callback,
                    f"获取公告详情失败,{poll_interval}秒后重试(已尝试{detail_attempt}次)..."
                )
                time.sleep(poll_interval)

            # 步骤3: 持续提取口令直到成功
            password = None
            extract_attempt = 0

            while password is None:
                # 检查暂停标志
                if stop_flag and stop_flag.is_set():
                    return self._error_result("用户取消执行")

                extract_attempt += 1
                self._update_progress(
                    progress_callback,
                    f"正在提取口令(第{extract_attempt}次尝试)..."
                )
                self.logger.info(f"第{extract_attempt}次尝试提取口令")

                html_content = detail.get("content", {}).get("text", "")
                password = self.password_extractor.extract_password(html_content)

                if password:
                    self.logger.info(f"✓ 成功提取口令: {password}")
                    # 在GUI显示口令
                    self._update_progress(progress_callback, f"✓ 成功提取口令: {password}")
                    break

                # 提取失败,等待后重试
                self.logger.warning(f"提取口令失败,{poll_interval}秒后重试...")
                self._update_progress(
                    progress_callback,
                    f"提取口令失败,{poll_interval}秒后重试(已尝试{extract_attempt}次)..."
                )
                time.sleep(poll_interval)

            # 步骤4: 检查Cookie池
            if not self.cookie_pool:
                return self._error_result("Cookie池未初始化,请添加至少一个Cookie")

            # 步骤5: 并发兑换所有Cookie
            self._update_progress(progress_callback, f"开始并发兑换,共{len(self.cookie_pool.redeemers)}个Cookie")
            self.logger.info(f"开始并发兑换,共{len(self.cookie_pool.redeemers)}个Cookie")

            # 包装progress_callback以支持Cookie ID
            def cookie_progress_wrapper(cookie_id: int, message: str):
                if progress_callback:
                    progress_callback(f"[Cookie{cookie_id}] {message}")

            # 执行并发兑换
            results = self.cookie_pool.execute_concurrent(
                password=password,
                poll_interval=poll_interval,
                progress_callback=cookie_progress_wrapper,
                captcha_callback=captcha_callback,
                stop_flag=stop_flag
            )

            # 统计结果
            success_count = sum(1 for r in results if r and r.get("success"))
            total_count = len(results)

            self.logger.info("="*50)
            self.logger.info(f"兑换完成: 成功{success_count}/{total_count}")
            self.logger.info("="*50)

            if success_count > 0:
                return {
                    "success": True,
                    "message": f"兑换完成: 成功{success_count}/{total_count}个Cookie",
                    "data": {"results": results, "success_count": success_count, "total_count": total_count}
                }
            else:
                return {
                    "success": False,
                    "message": f"所有Cookie兑换失败(共{total_count}个)",
                    "data": {"results": results, "success_count": 0, "total_count": total_count}
                }

        except Exception as e:
            self.logger.error(f"执行兑换流程异常: {e}")
            return self._error_result(f"执行异常: {e}")

    def _update_progress(self, callback: Optional[Callable[[str], None]], message: str) -> None:
        """
        更新进度信息

        Args:
            callback: 回调函数
            message: 进度消息
        """
        if callback:
            callback(message)

    def _error_result(self, message: str) -> dict:
        """
        生成错误结果

        Args:
            message: 错误消息

        Returns:
            错误结果字典
        """
        self.logger.error(message)
        return {
            "success": False,
            "message": message,
            "data": {}
        }
