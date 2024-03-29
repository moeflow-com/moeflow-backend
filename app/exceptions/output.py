from flask_babel import lazy_gettext

from .base import MoeError


class OutputRootError(MoeError):
    """
    @apiDefine ProjectRootError
    @apiError 9000 导出异常
    """

    code = 9000
    message = lazy_gettext("导出异常")


class OutputNotExistError(OutputRootError):
    """
    @apiDefine OutputNotExistError
    @apiError 9001 导出导出文件不存在
    """

    code = 9001
    message = lazy_gettext("导出导出文件不存在")


class OutputTooFastError(OutputRootError):
    """
    @apiDefine OutputTooFastError
    @apiError 9002 导出过于频繁，请稍后再试
    """

    code = 9002
    message = lazy_gettext("导出过于频繁，请稍后再试")
