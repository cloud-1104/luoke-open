"""
验证码处理模块
获取验证码图片并使用OCR识别或手动输入
"""

import io
from typing import Optional, Callable
from PIL import Image
from src.api_client import APIClient
from src.logger import LoggerManager


class CaptchaHandler:
    """验证码处理器 - 支持OCR自动识别和手动输入"""

    def __init__(self, api_client: APIClient, use_ocr: bool = False, max_retries: int = 3):
        """
        初始化验证码处理器

        Args:
            api_client: API客户端实例
            use_ocr: 是否使用OCR识别
            max_retries: OCR最大重试次数
        """
        self.api_client = api_client
        self.use_ocr = use_ocr
        self.max_retries = max_retries
        self.logger = LoggerManager().get_logger()

        # 延迟导入OCR库(避免未使用OCR时的依赖问题)
        self.ocr = None
        if self.use_ocr:
            self._init_ocr()

    def _init_ocr(self) -> None:
        """初始化OCR识别器"""
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            self.logger.info("OCR识别器初始化成功")
        except ImportError:
            self.logger.error("未安装ddddocr库,请运行: pip install ddddocr")
            self.use_ocr = False
        except Exception as e:
            self.logger.error(f"OCR初始化失败: {e}")
            self.use_ocr = False

    def get_captcha_with_image(
        self,
        captcha_image: bytes,
        manual_input_callback: Optional[Callable[[bytes, str], str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        处理已下载的验证码图片(OCR识别或手动输入)
        - OCR模式:直接返回识别结果,不显示图片
        - 手动模式:显示图片窗口,等待用户输入

        Args:
            captcha_image: 验证码图片字节数据
            manual_input_callback: 手动输入回调函数,接收图片字节数据和OCR结果,返回用户输入的验证码
            progress_callback: 进度回调函数,用于更新GUI状态

        Returns:
            成功返回验证码文本,失败返回None
        """
        # 使用OCR识别(每张图片只识别1次,识别失败由外层循环重新获取新图片)
        if self.use_ocr and self.ocr:
            try:
                self.logger.info("使用OCR识别验证码...")
                if progress_callback:
                    progress_callback("OCR识别中...")

                # OCR识别
                result = self.ocr.classification(captcha_image)
                captcha = result.strip()

                # 验证识别结果(通常验证码为4位字母数字)
                if captcha and len(captcha) >= 4:
                    self.logger.info(f"✓ OCR识别成功: {captcha}")
                    if progress_callback:
                        progress_callback(f"✓ OCR识别成功: {captcha}")
                    # OCR模式直接返回,不显示图片
                    return captcha
                else:
                    # 识别结果异常,返回None让外层重新获取新图片
                    self.logger.warning(f"OCR识别结果异常: {captcha} (长度{len(captcha)}),需要重新获取验证码")
                    if progress_callback:
                        progress_callback(f"OCR识别结果异常: {captcha},需要重新获取验证码")
                    return None

            except Exception as e:
                self.logger.error(f"OCR识别异常: {e},需要重新获取验证码")
                if progress_callback:
                    progress_callback(f"OCR识别异常: {e}")
                return None

        # 手动输入(显示图片)
        if manual_input_callback:
            self.logger.info("等待手动输入验证码...")
            if progress_callback:
                progress_callback("等待手动输入验证码...")
            user_captcha = manual_input_callback(captcha_image, "")
            if user_captcha and progress_callback:
                progress_callback(f"✓ 手动输入验证码: {user_captcha}")
            return user_captcha

        self.logger.error("无法获取验证码:未提供手动输入回调")
        return None

    def get_captcha(
        self,
        manual_input_callback: Optional[Callable[[bytes], str]] = None
    ) -> Optional[str]:
        """
        获取验证码(OCR识别或手动输入) - 旧版本方法,保持向后兼容

        Args:
            manual_input_callback: 手动输入回调函数,接收图片字节数据,返回用户输入的验证码

        Returns:
            成功返回验证码文本,失败返回None
        """
        # 获取验证码图片
        image_data = self.api_client.get_captcha_image()
        if not image_data:
            self.logger.error("获取验证码图片失败")
            return None

        self.logger.info("成功获取验证码图片")

        # 使用OCR识别
        if self.use_ocr and self.ocr:
            return self._ocr_recognize(image_data, manual_input_callback)

        # 手动输入
        if manual_input_callback:
            return manual_input_callback(image_data)

        self.logger.error("无法获取验证码:未配置OCR且未提供手动输入回调")
        return None

    def _ocr_recognize(
        self,
        image_data: bytes,
        manual_input_callback: Optional[Callable[[bytes], str]] = None
    ) -> Optional[str]:
        """
        使用OCR识别验证码,失败后降级到手动输入

        Args:
            image_data: 验证码图片字节数据
            manual_input_callback: 手动输入回调函数

        Returns:
            验证码文本
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"OCR识别第{attempt}次尝试...")

                # OCR识别
                result = self.ocr.classification(image_data)
                captcha = result.strip()

                # 验证识别结果(通常验证码为4位字母数字)
                if captcha and len(captcha) >= 4:
                    self.logger.info(f"OCR识别成功: {captcha}")
                    return captcha
                else:
                    self.logger.warning(f"OCR识别结果异常: {captcha}")

            except Exception as e:
                self.logger.error(f"OCR识别异常: {e}")

        # OCR失败,降级到手动输入
        self.logger.warning(f"OCR识别失败{self.max_retries}次,切换到手动输入模式")

        if manual_input_callback:
            return manual_input_callback(image_data)

        return None

    @staticmethod
    def save_captcha_image(image_data: bytes, save_path: str = "captcha.png") -> bool:
        """
        保存验证码图片到文件(用于调试或手动识别)

        Args:
            image_data: 图片字节数据
            save_path: 保存路径

        Returns:
            是否保存成功
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            image.save(save_path)
            return True
        except Exception as e:
            print(f"保存验证码图片失败: {e}")
            return False
