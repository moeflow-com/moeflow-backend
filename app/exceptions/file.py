from flask_babel import lazy_gettext, gettext

from app.exceptions import MoeError


class FileRootError(MoeError):
    """
    @apiDefine FileRootError
    @apiError 8000 文件异常
    """

    code = 8000
    message = lazy_gettext("文件异常")


class FileNotExistError(FileRootError):
    """
    @apiDefine FileNotExistError
    @apiError 8001 文件/文件夹不存在，可能已被删除
    """

    code = 8001
    message = lazy_gettext("文件/文件夹不存在，可能已被删除")


class FolderNotExistError(FileRootError):
    """
    @apiDefine FolderNotExistError
    @apiError 8002 文件夹不存在，可能已被删除
    """

    code = 8002
    message = lazy_gettext("文件夹不存在，可能已被删除")


class SuffixNotInFileTypeError(FileRootError):
    """
    @apiDefine SuffixNotInFileTypeError
    @apiError 8003 后缀名必须属于原文件的文件类型
    """

    code = 8003
    message = lazy_gettext("后缀名必须属于原文件的文件类型")


class SourceFileNotExist(FileRootError):
    """
    @apiDefine SourceFileNotExist
    @apiError 8004 源文件不存在
    """

    code = 8004
    message = lazy_gettext("源文件不存在")

    def __init__(self, file_not_exist_reason=None):
        from app.constants.file import FileNotExistReason

        message = ""
        if file_not_exist_reason == FileNotExistReason.UNKNOWN:
            message = gettext("未知")
        elif file_not_exist_reason == FileNotExistReason.NOT_UPLOAD:
            message = gettext("待上传")
        elif file_not_exist_reason == FileNotExistReason.FINISH:
            message = gettext("用户操作完结时清除")
        elif file_not_exist_reason == FileNotExistReason.BLOCK:
            message = gettext("含有敏感信息已删除")
        if message:
            self.message = f"{self.message}: {message}"


class SourceNotExistError(FileRootError):
    """
    @apiDefine SourceNotExistError
    @apiError 8005 原文不存在，已被删除
    """

    code = 8005
    message = lazy_gettext("原文不存在，已被删除")


class SourceMovingError(FileRootError):
    """
    @apiDefine SourceMovingError
    @apiError 8006 正在移动顺序，请稍后尝试
    """

    code = 8006
    message = lazy_gettext("正在移动顺序，请稍后尝试")


class TranslationNotUniqueError(FileRootError):
    """
    @apiDefine TranslationNotUniqueError
    @apiError 8007 翻译不唯一
    """

    code = 8007
    message = lazy_gettext("翻译不唯一")
