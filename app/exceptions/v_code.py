from flask_babel import lazy_gettext

from .base import MoeError


class VCodeRootError(MoeError):
    """
    @apiDefine VCodeRootError
    @apiError 2000 验证码异常
    """

    code = 2000
    message = lazy_gettext("验证码异常")


class VCodeExpiredError(VCodeRootError):
    """
    @apiDefine VCodeExpiredError
    @apiError 2001 验证码过期，请重新输入
    """

    code = 2001
    message = lazy_gettext("验证码过期，请重新输入")


class VCodeWrongError(VCodeRootError):
    """
    @apiDefine VCodeWrongError
    @apiError 2002 验证码错误
    """

    code = 2002
    message = lazy_gettext("验证码错误")


class VCodeNotExistError(VCodeRootError):
    """
    @apiDefine VCodeNotExistError
    @apiError 2003 验证码不存在或已失效
    """

    code = 2003
    message = lazy_gettext("验证码失效，请重新获取")


class VCodeCoolingError(VCodeRootError):
    """
    @apiDefine VCodeCoolingError
    @apiError 2004 验证码冷却中,请稍后再试
    """

    code = 2004

    def __init__(self, seconds):
        self.message = {
            "wait": seconds,
            "tip": lazy_gettext("请等候{seconds}秒后再试").format(seconds=seconds),
        }
