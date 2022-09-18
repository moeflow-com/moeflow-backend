from flask_babel import lazy_gettext

from .base import MoeError


class ProjectRootError(MoeError):
    """
    @apiDefine ProjectRootError
    @apiError 4000 项目异常
    """

    code = 4000
    message = lazy_gettext("项目异常")


class ProjectNotExistError(ProjectRootError):
    """
    @apiDefine ProjectNotExistError
    @apiError 4001 项目不存在
    """

    code = 4001
    message = lazy_gettext("项目不存在")


class ProjectFinishedError(ProjectRootError):
    """
    @apiDefine ProjectFinishedError
    @apiError 4002 项目已完结
    """

    code = 4002
    message = lazy_gettext("项目已完结")


class ImageParsingError(ProjectRootError):
    """
    @apiDefine ImageParsingError
    @apiError 4004 图片正在自动标记中，请稍后
    """

    code = 4004
    message = lazy_gettext("图片正在自动标记中，请稍后")


class ImageParseSucceededError(ProjectRootError):
    """
    @apiDefine ImageParseSucceededError
    @apiError 4005 图片已自动标记完成，不能再次自动标记
    """

    code = 4005
    message = lazy_gettext("图片已自动标记完成，不能再次自动标记")


class FileNotExistError(ProjectRootError):
    """
    @apiDefine FileNotExistError
    @apiError 4006 文件不存在
    """

    code = 4006
    message = lazy_gettext("文件不存在")


class FilenameDuplicateError(ProjectRootError):
    """
    @apiDefine FilenameDuplicateError
    @apiError 4007 文件名重复
    """

    code = 4007
    message = lazy_gettext("文件名重复")


class TextParsingError(ProjectRootError):
    """
    @apiDefine TextParsingError
    @apiError 4008 文本正在解析，请稍后
    """

    code = 4008
    message = lazy_gettext("文本正在解析，请稍后")


class TextParseSucceededError(ProjectRootError):
    """
    @apiDefine TextParseSucceededError
    @apiError 4009 文本已解析成功
    """

    code = 4009
    message = lazy_gettext("文本已解析成功")


class TranslationEmptyError(ProjectRootError):
    """
    @apiDefine TranslationEmptyError
    @apiError 4010 翻译不能为空
    """

    code = 4010
    message = lazy_gettext("翻译不能为空")


class TargetIsNotFolderError(ProjectRootError):
    """
    @apiDefine TargetIsNotFolderError
    @apiError 4011 目标必须是文件夹
    """

    code = 4011
    message = lazy_gettext("目标必须是文件夹")


class FileParentIsSelfError(ProjectRootError):
    """
    @apiDefine FileParentIsSelfError
    @apiError 4012 目标文件夹不能是自己本身
    """

    code = 4012
    message = lazy_gettext("目标文件夹不能是自己本身")


class FileParentIsSameError(ProjectRootError):
    """
    @apiDefine FileParentIsSameError
    @apiError 4013 目标文件夹与原父级文件夹相同
    """

    code = 4013
    message = lazy_gettext("目标文件夹与原父级文件夹相同")


class FileParentIsSubFolderError(ProjectRootError):
    """
    @apiDefine FileParentIsSubFolderError
    @apiError 4014 不能移动到自己的子文件夹
    """

    code = 4014
    message = lazy_gettext("不能移动到自己的子文件夹")


class FileNotActivatedError(ProjectRootError):
    """
    @apiDefine FileNotActivatedError
    @apiError 4016 不能操作非激活修订版
    """

    code = 4016
    message = lazy_gettext("不能操作非激活修订版")


class FileIsActivatedError(ProjectRootError):
    """
    @apiDefine FileIsActivatedError
    @apiError 4017 此修订版已激活
    """

    code = 4017
    message = lazy_gettext("此修订版已激活")


class FolderNoVersionError(ProjectRootError):
    """
    @apiDefine FolderNoVersionError
    @apiError 4018 文件夹不能进行修订版操作
    """

    code = 4018
    message = lazy_gettext("文件夹不能进行修订版操作")


class SourceNotEmpty(ProjectRootError):
    """
    @apiDefine SourceNotEmpty
    @apiError 4019 原文已有翻译
    """

    code = 4019
    message = lazy_gettext("原文已有翻译")


# 4020 未用


class TipEmptyError(ProjectRootError):
    """
    @apiDefine TipEmptyError
    @apiError 4021 备注不能为空
    """

    code = 4021
    message = lazy_gettext("备注不能为空")


class ProjectSetNotExistError(ProjectRootError):
    """
    @apiDefine ProjectSetNotExistError
    @apiError 4022 项目集不存在
    """

    code = 4022
    message = lazy_gettext("项目集不存在")


class ProjectNotFinishedError(ProjectRootError):
    """
    @apiDefine ProjectNotFinishedError
    @apiError 4023 项目还没有正式完结
    """

    code = 4023
    message = lazy_gettext("项目还没有正式完结")


class TargetNotExistError(ProjectRootError):
    """
    @apiDefine TargetNotExistError
    @apiError 4024 项目目标语言不存在
    """

    code = 4024
    message = lazy_gettext("项目目标语言不存在")


class ProjectHasDeletePlanError(ProjectRootError):
    """
    @apiDefine ProjectHasDeletePlanError
    @apiError 4025 项目已有销毁计划
    """

    code = 4025
    message = lazy_gettext("项目已有销毁计划")


class ProjectHasFinishPlanError(ProjectRootError):
    """
    @apiDefine ProjectHasFinishPlanError
    @apiError 4026 项目已有完结计划
    """

    code = 4026
    message = lazy_gettext("项目已有完结计划")


class ProjectNoDeletePlanError(ProjectRootError):
    """
    @apiDefine ProjectNoDeletePlanError
    @apiError 4027 项目没有销毁计划
    """

    code = 4027
    message = lazy_gettext("项目没有销毁计划")


class ProjectNoFinishPlanError(ProjectRootError):
    """
    @apiDefine ProjectNoFinishPlanError
    @apiError 4028 项目已完结
    TODO: 删除 plan 系统，并同步修改测试，此项改成 ProjectCanNotFinishError
    """

    code = 4028
    message = lazy_gettext("项目已完结")


class LabelplusParseFailedError(ProjectRootError):
    """
    @apiDefine LabelplusParseFailedError
    @apiError 4029 "翻译数据.txt" 解析失败
    """

    code = 4029
    message = lazy_gettext('"翻译数据.txt" 解析失败')
