from flask_babel import lazy_gettext

from app.constants.base import IntType


class OutputStatus(IntType):
    """项目导出状态"""

    QUEUING = 0  # 排队中
    DOWNLOADING = 1  # 源文件整理中
    TRANSLATION_OUTPUTING = 2  # 翻译整理中
    ZIPING = 3  # 压缩中
    SUCCEEDED = 4  # 已完成
    ERROR = 5  # 导出错误，请重试

    details = {
        "QUEUING": {"name": lazy_gettext("排队中")},
        "TRANSLATION_OUTPUTING": {"name": lazy_gettext("翻译整理中")},
        "DOWNLOADING": {"name": lazy_gettext("源文件整理中")},
        "ZIPING": {"name": lazy_gettext("压缩中")},
        "SUCCEEDED": {"name": lazy_gettext("已完成")},
        "ERROR": {"name": lazy_gettext("导出错误，请重试")},
    }


class OutputTypes(IntType):
    """项目导出类型"""

    ALL = 0  # 所有内容
    ONLY_TEXT = 1  # 仅文本
