from flask_babel import lazy_gettext

from .base import MoeError


class TermRootError(MoeError):
    """
    @apiDefine TermRootError
    @apiError 7000 术语库异常
    """

    code = 7000
    message = lazy_gettext("术语库异常")


class TermBankNotExistError(TermRootError):
    """
    @apiDefine TermBankNotExistError
    @apiError 7001 术语库不存在
    """

    code = 7001
    message = lazy_gettext("术语库不存在")


class TermNotExistError(TermRootError):
    """
    @apiDefine TermNotExistError
    @apiError 7002 术语不存在
    """

    code = 7002
    message = lazy_gettext("术语不存在")
