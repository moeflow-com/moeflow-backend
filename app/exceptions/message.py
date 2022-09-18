from flask_babel import lazy_gettext

from .base import MoeError


class MessageRootError(MoeError):
    """
    @apiDefine MessageRootError
    @apiError 7000 站内信异常
    """

    code = 7000
    message = lazy_gettext("站内信异常")


class MessageTypeError(MessageRootError):
    """
    @apiDefine MessageTypeError
    @apiError 7001 站内信类型错误
    """

    code = 7001
    message = lazy_gettext("站内信类型错误")
