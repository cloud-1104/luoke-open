"""
Cookie池管理模块
处理多个Cookie的并发兑换,每个Cookie维护独立的Session和验证码
"""

import threading
from typing import List, Dict, Optional, Callable
from src.api_client import APIClient
from src.captcha_handler import CaptchaHandler
from src.logger import LoggerManager


class CookieRedeemer:
    """单个Cookie的兑换器 - 每个Cookie独立维护Session和验证码"""

    def __init__(self, cookie_id: int, miniapp_auth: str, web_cookie: str,
                 use_ocr: bool, ocr_max_retries: int, timeout: int,
                 use_proxy: bool = False, proxy_host: str = "", proxy_port: int = 0):
        """
        初始化Cookie兑换器

        Args:
            cookie_id: Cookie编号(从1开始)
            miniapp_auth: 小程序Authorization
            web_cookie: 网页端Cookie
            use_ocr: 是否使用OCR
            ocr_max_retries: OCR最大重试次数
            timeout: 请求超时时间
            use_proxy: 是否使用代理
            proxy_host: 代理主机地址
            proxy_port: 代理端口
        """
        self.cookie_id = cookie_id
        self.logger = LoggerManager().get_logger()

        # 每个Cookie独立的API客户端(维护独立Session)
        self.api_client = APIClient(
            miniapp_auth=miniapp_auth,
            web_cookie=web_cookie,
            timeout=timeout,
            use_proxy=use_proxy,
            proxy_host=proxy_host,
            proxy_port=proxy_port
        )

        # 每个Cookie独立的验证码处理器
        self.captcha_handler = CaptchaHandler(
            api_client=self.api_client,
            use_ocr=use_ocr,
            max_retries=ocr_max_retries
        )

        self.status = "待命"  # 当前状态
        self.result = None  # 兑换结果

    def redeem(self, password: str, poll_interval: float,
               progress_callback: Optional[Callable[[int, str], None]] = None,
               captcha_callback: Optional[Callable[[bytes, str], str]] = None,
               stop_flag: Optional[threading.Event] = None) -> Dict:
        """
        执行兑换操作(持续重试直到成功或停止)

        Args:
            password: 兑换口令
            poll_interval: 轮询间隔
            progress_callback: 进度回调函数(cookie_id, message)
            captcha_callback: 验证码回调函数
            stop_flag: 停止标志

        Returns:
            兑换结果字典
        """
        import time

        attempt = 0
        self.status = "兑换中"

        while True:
            # 检查停止标志
            if stop_flag and stop_flag.is_set():
                self.status = "已停止"
                return {"success": False, "message": "用户取消执行"}

            attempt += 1
            self._update_progress(progress_callback, f"第{attempt}次尝试获取验证码...")

            # 获取验证码图片
            captcha_image = self.api_client.get_captcha_image()
            if not captcha_image:
                self.logger.error(f"[Cookie{self.cookie_id}] 获取验证码图片失败,{poll_interval}秒后重试...")
                self._update_progress(progress_callback, f"获取验证码失败,{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue

            # 识别或手动输入验证码
            captcha = self.captcha_handler.get_captcha_with_image(
                captcha_image=captcha_image,
                manual_input_callback=captcha_callback,
                progress_callback=lambda msg: self._update_progress(progress_callback, msg)
            )

            if not captcha:
                self.logger.error(f"[Cookie{self.cookie_id}] 获取验证码失败,{poll_interval}秒后重试...")
                self._update_progress(progress_callback, f"获取验证码失败,{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue

            self.logger.info(f"[Cookie{self.cookie_id}] 第{attempt}次尝试 - 验证码: {captcha}")
            self._update_progress(progress_callback, f"第{attempt}次尝试 - 验证码: {captcha}")

            # 提交兑换
            self._update_progress(progress_callback, f"提交兑换: 口令={password}, 验证码={captcha}")
            self.logger.info(f"[Cookie{self.cookie_id}] 提交兑换: 口令={password}, 验证码={captcha}")

            result = self.api_client.redeem_code(password=password, captcha=captcha)

            # 解析结果
            ret_code = result.get("ret", -1)
            message = result.get("sMsg", "未知错误")

            # 成功
            if ret_code == 0:
                self.logger.info(f"[Cookie{self.cookie_id}] ✓ 兑换成功!")
                self.status = "成功"
                self._update_progress(progress_callback, "✓ 兑换成功!")
                return {"success": True, "message": "兑换成功!", "data": result}

            # 已有资格(消息检测) - 视为成功,停止重试
            if "已有测试资格" in message or "无需重复兑换" in message:
                self.logger.info(f"[Cookie{self.cookie_id}] ✓ 已有测试资格,无需兑换")
                self.status = "已有资格"
                self._update_progress(progress_callback, "✓ 已有测试资格,无需兑换")
                return {"success": True, "message": "已有测试资格", "data": result}

            # 达到限量(错误码100001)
            if ret_code == 100001:
                self.logger.warning(f"[Cookie{self.cookie_id}] 兑换码已达到限量")
                self.status = "限量"
                self._update_progress(progress_callback, f"兑换失败: {message} (兑换码已抢完)")
                return {"success": False, "message": f"兑换失败: {message} (兑换码已抢完)", "data": result}

            # 未登录(错误码101) - Cookie已失效,直接停止
            if ret_code == 101:
                self.logger.error(f"[Cookie{self.cookie_id}] Cookie已失效,需要重新登录")
                self.status = "未登录"
                self._update_progress(progress_callback, f"Cookie已失效: {message}")
                return {"success": False, "message": f"Cookie已失效: {message}", "data": result}

            # 验证码错误(错误码120001),继续重试
            if ret_code == 120001:
                self.logger.warning(f"[Cookie{self.cookie_id}] 第{attempt}次验证码错误,{poll_interval}秒后重试...")
                self._update_progress(progress_callback, f"验证码错误,{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue

            # 其他错误(请求频繁、网络错误等),回到循环开头重新获取验证码
            self.logger.warning(f"[Cookie{self.cookie_id}] 兑换失败: {message} (错误码: {ret_code})")
            self._update_progress(progress_callback, f"兑换失败: {message},将重新获取验证码")
            time.sleep(poll_interval)
            continue  # 回到while循环开头,重新获取新的验证码图片

    def _update_progress(self, callback: Optional[Callable[[int, str], None]], message: str):
        """更新进度"""
        if callback:
            callback(self.cookie_id, message)


class CookiePool:
    """Cookie池管理器 - 管理多个Cookie并发兑换"""

    def __init__(self, miniapp_auth: str, web_cookies: List[str],
                 use_ocr: bool, ocr_max_retries: int, timeout: int,
                 use_proxy: bool = False, proxy_host: str = "", proxy_port: int = 0):
        """
        初始化Cookie池

        Args:
            miniapp_auth: 小程序Authorization
            web_cookies: Cookie列表
            use_ocr: 是否使用OCR
            ocr_max_retries: OCR最大重试次数
            timeout: 请求超时时间
            use_proxy: 是否使用代理
            proxy_host: 代理主机地址
            proxy_port: 代理端口
        """
        self.logger = LoggerManager().get_logger()

        # 创建所有Cookie的兑换器
        self.redeemers = []
        for i, cookie in enumerate(web_cookies, start=1):
            redeemer = CookieRedeemer(
                cookie_id=i,
                miniapp_auth=miniapp_auth,
                web_cookie=cookie,
                use_ocr=use_ocr,
                ocr_max_retries=ocr_max_retries,
                timeout=timeout,
                use_proxy=use_proxy,
                proxy_host=proxy_host,
                proxy_port=proxy_port
            )
            self.redeemers.append(redeemer)

        self.logger.info(f"Cookie池初始化完成,共{len(self.redeemers)}个Cookie")

    def execute_concurrent(self, password: str, poll_interval: float,
                           progress_callback: Optional[Callable[[int, str], None]] = None,
                           captcha_callback: Optional[Callable[[bytes, str], str]] = None,
                           stop_flag: Optional[threading.Event] = None) -> List[Dict]:
        """
        并发执行所有Cookie的兑换

        Args:
            password: 兑换口令
            poll_interval: 轮询间隔
            progress_callback: 进度回调函数(cookie_id, message)
            captcha_callback: 验证码回调函数
            stop_flag: 停止标志

        Returns:
            所有Cookie的兑换结果列表
        """
        self.logger.info(f"开始并发兑换,共{len(self.redeemers)}个Cookie")

        threads = []
        results = [None] * len(self.redeemers)

        def redeem_worker(index: int, redeemer: CookieRedeemer):
            """工作线程"""
            results[index] = redeemer.redeem(
                password=password,
                poll_interval=poll_interval,
                progress_callback=progress_callback,
                captcha_callback=captcha_callback,
                stop_flag=stop_flag
            )

        # 启动所有线程
        for i, redeemer in enumerate(self.redeemers):
            thread = threading.Thread(
                target=redeem_worker,
                args=(i, redeemer),
                daemon=True
            )
            threads.append(thread)
            thread.start()
            self.logger.info(f"Cookie{redeemer.cookie_id} 兑换线程已启动")

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        self.logger.info("所有Cookie兑换完成")
        return results
