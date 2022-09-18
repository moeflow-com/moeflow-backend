from flask_babel import lazy_gettext

from .base import MoeError


class AuthRootError(MoeError):
    """
    @apiDefine AuthRootError
    @apiError 1000 验证异常
    """

    code = 1000
    message = lazy_gettext("验证异常")


class EmailNotRegisteredError(AuthRootError):
    """
    @apiDefine EmailNotRegisteredError
    @apiError 1001 此邮箱未注册
    """

    code = 1001
    message = lazy_gettext("此邮箱未注册")


class PasswordWrongError(AuthRootError):
    """
    @apiDefine PasswordWrongError
    @apiError 1002 密码错误
    """

    code = 1002
    message = lazy_gettext("密码错误")


class NeedTokenError(AuthRootError):
    """
    @apiDefine NeedTokenError
    @apiError 1003 需要令牌
    """

    status_code = 401
    code = 1003
    message = lazy_gettext("需要令牌")


class BadTokenError(AuthRootError):
    """
    @apiDefine BadTokenError
    @apiError 1004 无效的令牌: [详细原因]
    """

    status_code = 401
    code = 1004
    message = lazy_gettext("无效的令牌")


class UserNotExistError(AuthRootError):
    """
    @apiDefine UserNotExistError
    @apiError 1005 用户不存在
    """

    code = 1005
    message = lazy_gettext("用户不存在")


class UserBannedError(AuthRootError):
    """
    @apiDefine UserBannedError
    @apiError 1006 用户被封禁
    """

    code = 1006
    message = lazy_gettext("此用户被封禁")


class EmailRegexError(AuthRootError):
    """
    @apiDefine EmailRegexError
    @apiError 1007 邮箱格式不正确
    """

    code = 1007
    message = lazy_gettext("邮箱格式不正确")


class EmailRegisteredError(AuthRootError):
    """
    @apiDefine EmailRegisteredError
    @apiError 1008 此被邮箱已注册，请直接登录或使用其他邮箱
    """

    code = 1008
    message = lazy_gettext("此邮箱已被注册")


class UserNameRegexError(AuthRootError):
    """
    @apiDefine UserNameRegexError
    @apiError 1009 仅可使用中文/日文/韩文/英文/数字/_
    """

    code = 1009
    message = lazy_gettext("仅可使用中文/日文/韩文/英文/数字/_")


class UserNameRegisteredError(AuthRootError):
    """
    @apiDefine UserNameRegisteredError
    @apiError 1010 此昵称已被使用
    """

    code = 1010
    message = lazy_gettext("此昵称已被使用")


class UserNameLengthError(AuthRootError):
    """
    @apiDefine UserNameLengthError
    @apiError 1011 长度为2到18个字符
    """

    code = 1011
    message = lazy_gettext("长度为2到18个字符")
