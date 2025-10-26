"""
HTML内容解析模块
从公告详情HTML中提取口令文本
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
from src.logger import LoggerManager


class PasswordExtractor:
    """口令提取器 - 从HTML中提取资格码"""

    def __init__(self):
        """初始化口令提取器"""
        self.logger = LoggerManager().get_logger()

    def extract_password(self, html_content: str) -> Optional[str]:
        """
        从HTML内容中提取口令

        策略1(优先): 查找特定样式的span标签(color: rgb(231, 95, 51) + font-size: 24px)
        策略2(降级): 正则匹配"今日资格码:"后的内容
        策略3(兜底): 查找所有大字号红色文本

        Args:
            html_content: HTML内容字符串

        Returns:
            成功返回口令文本,失败返回None
        """
        if not html_content:
            self.logger.error("HTML内容为空")
            return None

        # 策略1: BeautifulSoup解析,查找特定样式
        password = self._extract_by_style(html_content)
        if password:
            self.logger.info(f"策略1成功提取口令: {password}")
            return password

        # 策略2: 正则匹配
        password = self._extract_by_regex(html_content)
        if password:
            self.logger.info(f"策略2成功提取口令: {password}")
            return password

        # 策略3: 查找所有可能的目标文本
        password = self._extract_by_fallback(html_content)
        if password:
            self.logger.info(f"策略3成功提取口令: {password}")
            return password

        self.logger.error("所有策略均未能提取口令")
        return None

    def _extract_by_style(self, html_content: str) -> Optional[str]:
        """
        策略1: 通过CSS样式查找(精确匹配)

        查找: color: rgb(231, 95, 51) 且 font-size: 24px 的span标签
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 查找所有span标签
            spans = soup.find_all('span')

            for span in spans:
                style = span.get('style', '')
                # 检查是否包含目标样式
                if 'rgb(231, 95, 51)' in style or 'rgb(231,95,51)' in style:
                    if '24px' in style:
                        text = span.get_text(strip=True)
                        if text:
                            return text

        except Exception as e:
            self.logger.debug(f"策略1解析异常: {e}")

        return None

    def _extract_by_regex(self, html_content: str) -> Optional[str]:
        """
        策略2: 正则表达式匹配

        匹配模式: 今日资格码[:\s]*<.*?>([^<]+)
        """
        try:
            # 移除HTML中的换行和多余空格,便于正则匹配
            clean_html = re.sub(r'\s+', ' ', html_content)

            # 匹配 "今日资格码:" 后面的第一个标签内容
            pattern = r'今日资格码[:\s]*<[^>]*>([^<]+)'
            match = re.search(pattern, clean_html)

            if match:
                text = match.group(1).strip()
                if text:
                    return text

        except Exception as e:
            self.logger.debug(f"策略2解析异常: {e}")

        return None

    def _extract_by_fallback(self, html_content: str) -> Optional[str]:
        """
        策略3: 兜底策略

        查找所有包含目标颜色或大字号的文本,返回最有可能的结果
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 查找所有strong标签中的大字号或红色文本
            candidates = []

            for tag in soup.find_all(['span', 'strong']):
                style = tag.get('style', '')
                text = tag.get_text(strip=True)

                # 检查是否包含目标特征
                if text and len(text) > 2:  # 过滤太短的文本
                    # 红色文本或大字号
                    if 'rgb(231, 95, 51)' in style or 'font-size: 24px' in style:
                        candidates.append(text)

            # 返回第一个候选(假设最先出现的是目标)
            if candidates:
                return candidates[0]

        except Exception as e:
            self.logger.debug(f"策略3解析异常: {e}")

        return None
