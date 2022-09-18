from flask_babel import lazy_gettext

from .base import MoeError


class LanguageRootError(MoeError):
    """
    @apiDefine LanguageRootError
    @apiError 6000 语言异常
    """

    code = 6000
    message = lazy_gettext("语言异常")


class LanguageNotExistError(LanguageRootError):
    """
    @apiDefine LanguageNotExistError
    @apiError 6001 语言不存在
    """

    code = 6001
    message = lazy_gettext("语言不存在")


class TargetAndSourceLanguageSameError(LanguageRootError):
    """
    @apiDefine TargetAndSourceLanguageSameError
    @apiError 6002 原语言和目标语言不能相同
    """

    code = 6002
    message = lazy_gettext("原语言和目标语言不能相同")


class NeedTargetLanguagesError(LanguageRootError):
    """
    @apiDefine NeedTargetLanguagesError
    @apiError 6003 需要设置目标语言
    """

    code = 6003
    message = lazy_gettext("需要设置目标语言")


class SameTargetLanguageError(LanguageRootError):
    """
    @apiDefine SameTargetLanguageError
    @apiError 6004 已有此目标语言
    """

    code = 6004
    message = lazy_gettext("已有此目标语言")
