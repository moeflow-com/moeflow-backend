from flask_babel import lazy_gettext

from .base import MoeError


class JoinProcessRootError(MoeError):
    """
    @apiDefine JoinProcessRootError
    @apiError 5000 加入流程异常
    """

    code = 5000
    message = lazy_gettext("加入流程异常")


class GroupTypeNotSupportError(JoinProcessRootError):
    """
    @apiDefine GroupTypeNotSupportError
    @apiError 5001 不支持此团体类型
    """

    code = 5001
    message = lazy_gettext("不支持此团体类型")


class UserAlreadyJoinedError(JoinProcessRootError):
    """
    @apiDefine UserAlreadyJoinedError
    @apiError 5003 此用户已经加入了
    """

    code = 5003

    def __init__(self, name):
        self.message = lazy_gettext("用户已经在 “{name}” 中").format(name=name)


class InvitationAlreadyExistError(JoinProcessRootError):
    """
    @apiDefine InvitationAlreadyExistError
    @apiError 5004 已邀请此用户，请等待用户确认
    """

    code = 5004
    message = lazy_gettext("已邀请此用户，请等待用户确认")


class ApplicationAlreadyExistError(JoinProcessRootError):
    """
    @apiDefine ApplicationAlreadyExistError
    @apiError 5005 您已经申请，请等待管理员确认
    """

    code = 5005
    message = lazy_gettext("您已经申请，请等待管理员确认")


class InvitationNotExistError(JoinProcessRootError):
    """
    @apiDefine InvitationNotExistError
    @apiError 5006 邀请不存在
    """

    code = 5006
    message = lazy_gettext("邀请不存在")


class ApplicationNotExistError(JoinProcessRootError):
    """
    @apiDefine ApplicationNotExistError
    @apiError 5007 申请不存在
    """

    code = 5007
    message = lazy_gettext("邀请不存在")


class AllowApplyTypeNotExistError(JoinProcessRootError):
    """
    @apiDefine AllowApplyTypeNotExistError
    @apiError 5008 允许申请类型不存在
    """

    code = 5008
    message = lazy_gettext("允许申请类型不存在")


class ApplicationCheckTypeNotExistError(JoinProcessRootError):
    """
    @apiDefine ApplicationCheckTypeNotExistError
    @apiError 5009 申请审核类型不存在
    """

    code = 5009
    message = lazy_gettext("申请审核类型不存在")


class InvitationFinishedError(JoinProcessRootError):
    """
    @apiDefine InvitationFinishedError
    @apiError 5010 无法修改此邀请
    """

    code = 5010
    message = lazy_gettext("无法修改此邀请")


class ApplicationFinishedError(JoinProcessRootError):
    """
    @apiDefine InvitationFinishedError
    @apiError 5011 此申请不能进行操作
    """

    code = 5011
    message = lazy_gettext("无法修改此申请")


class TargetIsFullError(JoinProcessRootError):
    """
    @apiDefine TargetIsFullError
    @apiError 5012 已满员，不可申请加入或邀请新成员
    """

    code = 5012
    message = lazy_gettext("已满员，不可申请加入或邀请新成员")


class CreatorCanNotLeaveError(JoinProcessRootError):
    """
    @apiDefine CreatorCanNotLeaveError
    @apiError 5013 创建者无法退出团体，请转移创建者权限后操作
    """

    code = 5013
    message = lazy_gettext("创建者无法退出团体，请转移创建者权限后操作")


class GroupNotOpenError(JoinProcessRootError):
    """
    @apiDefine GroupNotOpenError
    @apiError 5014 此团体不向公众开放
    """

    code = 5014
    message = lazy_gettext("此团体不向公众开放")
