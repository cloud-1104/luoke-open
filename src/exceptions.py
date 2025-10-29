"""
自定义异常类
"""


class InvalidSessionError(Exception):
    """小程序登录会话无效异常"""
    pass


class CaptchaError(Exception):
    """验证码相关异常"""
    pass
