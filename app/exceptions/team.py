from flask_babel import lazy_gettext

from .base import MoeError


class TeamRootError(MoeError):
    """
    @apiDefine TeamRootError
    @apiError 3000 团队异常
    """

    code = 3000
    message = lazy_gettext("团队异常")


class TeamNotExistError(TeamRootError):
    """
    @apiDefine TeamNotExistError
    @apiError 3001 团队不存在
    """

    code = 3001
    message = lazy_gettext("团队不存在")


"""错误码 3002 可以使用"""
"""错误码 3003 可以使用"""
"""错误码 3004 可以使用"""


class TeamNameRegexError(TeamRootError):
    """
    @apiDefine TeamNameRegexError
    @apiError 3005 仅可使用中文/日文/韩文/英文/数字/_
    """

    code = 3005
    message = lazy_gettext("仅可使用中文/日文/韩文/英文/数字/_")


class TeamNameRegisteredError(TeamRootError):
    """
    @apiDefine TeamNameRegisteredError
    @apiError 3006 此团队名已被使用,请尝试其他昵称
    """

    code = 3006
    message = lazy_gettext("此团队名已被使用")


class TeamNameLengthError(TeamRootError):
    """
    @apiDefine TeamNameLengthError
    @apiError 3007 长度为2到18个字符
    """

    code = 3007
    message = lazy_gettext("长度为2到18个字符")

class OnlyAllowAdminCreateTeamError(TeamRootError):
    """
    @apiDefine OnlyAllowAdminCreateTeamError
    @apiError 3008 仅站点管理员可创建团队
    """

    code = 3008
    message = lazy_gettext("仅站点管理员可创建团队")