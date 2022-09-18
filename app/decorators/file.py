from functools import wraps

from app.exceptions import (
    FileNotActivatedError,
    FileTypeNotSupportError,
    gettext,
)
from app.constants.file import FileType


def need_activated(func):
    """必须激活的File才能进行操作"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.activated:
            raise FileNotActivatedError
        return func(self, *args, **kwargs)

    return wrapper


def only(file_type):
    def decorator(func):
        """只允许某类型使用的函数，供File模型使用"""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.type != file_type:
                raise FileTypeNotSupportError(str(func))
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def only_file(func):
    """只允许非FOLDER使用的函数，供File模型使用"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.type == FileType.FOLDER:
            raise FileTypeNotSupportError(gettext("不能对文件夹执行 ") + func.__name__)
        return func(self, *args, **kwargs)

    return wrapper


def only_folder(func):
    """只允许FOLDER使用的函数，供File模型使用"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.type != FileType.FOLDER:
            raise FileTypeNotSupportError(gettext("不能对文件执行 ") + str(func))
        return func(self, *args, **kwargs)

    return wrapper
