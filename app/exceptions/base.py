# -*- coding: utf-8 -*-
"""
基础错误1-99为flask-apikit预留的错误code
"""

from flask_apikit.exceptions import APIError
from flask_babel import lazy_gettext

"""
@apiDefine ValidateError
@apiError 2 字段验证错误
"""
"""
@apiDefine QueryError
@apiError 3 Query字符串处理错误
"""


class MoeError(APIError):
    """
    @apiDefine MoeError
    @apiError 100 未定义的错误
    """

    code = 100
    message = lazy_gettext("未定义的错误")


class InvalidObjectIdError(MoeError):
    """
    @apiDefine InvalidObjectIdError
    @apiError 101 错误的ObjectId
    """

    code = 101
    message = lazy_gettext("错误的ObjectId")


class RoleNotExistError(MoeError):
    """
    @apiDefine RoleNotExistError
    @apiError 102 角色不存在
    """

    code = 102
    message = lazy_gettext("角色不存在")


class NoPermissionError(MoeError):
    """
    @apiDefine NoPermissionError
    @apiError 103 没有权限
    """

    code = 103
    message = lazy_gettext("没有权限")

    def __init__(self, message=None):
        """
        :param message: 附加message
        """
        # 如果定义了附加message，则替换
        if message:
            self.message = message


class NotExistError(MoeError):
    """
    @apiDefine NotExistError
    @apiError 104 某种没有定义不存在错误的对象不存在
    """

    code = 104

    def __new__(cls, cls_name):
        # 自动在exceptions中寻找为NotExistError的错误
        exceptions = getattr(__import__("app"), "exceptions")
        try:
            e = getattr(exceptions, cls_name + "NotExistError")
        except AttributeError:
            e = None
        if e:
            return e
        else:
            return super().__new__(cls)


class CommaStrNotAllInt(MoeError):
    """
    @apiDefine CommaStrNotAllInt
    @apiError 105 逗号分割的数字字符串包含非数字
    """

    code = 105
    message = lazy_gettext("逗号分割的数字字符串包含非数字")


class PermissionNotExistError(MoeError):
    """
    @apiDefine PermissionNotExistError
    @apiError 106 权限不存在
    """

    code = 106
    message = lazy_gettext("权限不存在")


class FilenameIllegalError(MoeError):
    """
    @apiDefine FilenameIllegalError
    @apiError 107 文件名错误
    """

    code = 107
    message = lazy_gettext("文件名错误")


class FileTypeNotSupportError(MoeError):
    """
    @apiDefine FileTypeNotSupportError
    @apiError 108 文件类型不支持此操作
    """

    code = 108
    message = lazy_gettext("文件类型不支持此操作")


class UploadFileNotFoundError(MoeError):
    """
    @apiDefine UploadFileNotFoundError
    @apiError 109 上传未包含文件
    """

    code = 109
    message = lazy_gettext("上传未包含文件")


class RequestDataEmptyError(MoeError):
    """
    @apiDefine RequestDataEmptyError
    @apiError 110 请求参数不能为空或没有需要的值
    """

    code = 110
    message = lazy_gettext("请求参数不能为空或没有需要的值")


class RequestDataWrongError(MoeError):
    """
    @apiDefine RequestDataEmptyError
    @apiError 111 请求参数错误
    """

    code = 111
    message = lazy_gettext("请求参数错误")
