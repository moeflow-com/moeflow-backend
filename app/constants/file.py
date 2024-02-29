from flask_babel import lazy_gettext
from app.constants.base import IntType


class FileType(IntType):
    UNKNOWN = 0  # 未知
    FOLDER = 1  # 文件夹
    IMAGE = 2  # 图片
    TEXT = 3  # 纯文本

    SUPPORTED = (IMAGE,)  # 支持用于翻译的格式，在上传时检查
    TEST_SUPPORTED = (IMAGE, TEXT)  # 支持用于翻译的格式，在上传时检查（用于测试环境）

    @staticmethod
    def by_suffix(suffix):
        # 后缀名转suffix对照表
        suffix_type_map = {
            "jpg": FileType.IMAGE,
            "jpeg": FileType.IMAGE,
            "png": FileType.IMAGE,
            "bmp": FileType.IMAGE,
            "gif": FileType.IMAGE,
            "txt": FileType.TEXT,
        }
        t = suffix_type_map.get(suffix.lower(), FileType.UNKNOWN)
        return t


class FileNotExistReason:
    """源文件不存在的原因"""

    UNKNOWN = 0  # 未知
    NOT_UPLOAD = 1  # 还没有上传
    FINISH = 2  # 因为完结被删除
    # 3 还未使用
    BLOCK = 4  # 因为屏蔽被删除


class FileSafeStatus:
    """安全检查状态"""

    # 第一步
    NEED_MACHINE_CHECK = 0  # 需要机器检测
    QUEUING = 1  # 机器检测排队中
    WAIT_RESULT = 2  # 机器检测等待结果
    # 第二步（根据机器检测结果）
    NEED_HUMAN_CHECK = 3  # 需要人工检查
    # 第三步
    SAFE = 4  # 已检测安全
    BLOCK = 5  # 文件被删除屏蔽，需要重新上传


class ParseStatus(IntType):
    NOT_START = 0  # 未开始
    QUEUING = 1  # 排队中
    PARSING = 2  # 解析中
    PARSE_FAILED = 3  # 解析失败
    PARSE_SUCCEEDED = 4  # 解析成功

    details = {
        "NOT_START": {"name": lazy_gettext("解析未开始")},
        "QUEUING": {"name": lazy_gettext("解析排队中")},
        "PARSING": {"name": lazy_gettext("解析中")},
        "PARSE_FAILED": {"name": lazy_gettext("解析失败")},
        "PARSE_SUCCEEDED": {"name": lazy_gettext("解析成功")},
    }


class ImageParseStatus(ParseStatus):
    details = {
        "NOT_START": {"name": lazy_gettext("自动标记未开始")},
        "QUEUING": {"name": lazy_gettext("排队中")},
        "PARSING": {"name": lazy_gettext("自动标记中")},
        "PARSE_FAILED": {"name": lazy_gettext("自动标记失败")},
        "PARSE_SUCCEEDED": {"name": lazy_gettext("自动标记完成")},
    }


class ParseErrorType(IntType):
    UNKNOWN = 0  # 其他错误
    TEXT_UNKNOWN_CHARSET = 1  # 未知字符集
    FILE_CAN_NOT_READ = 2  # 文件无法读取，请确认文件完好或尝试重新上传
    IMAGE_PARSE_ALONE_ERROR = 3  # 图片单独处理时读取失败
    IMAGE_CAN_NOT_DOWNLOAD_FROM_OSS = 4  # 图片无法从 OSS 下载
    IMAGE_TOO_LARGE = 5  # 图片超过 20MB 无法 OCR
    IMAGE_OCR_SERVER_DISCONNECT = 6  # 连接 OCR 服务器失败，请稍后重试

    details = {
        "UNKNOWN": {"name": lazy_gettext("其他错误")},
        "TEXT_UNKNOWN_CHARSET": {"name": lazy_gettext("未知字符集")},
        "FILE_CAN_NOT_READ": {
            "name": lazy_gettext("文件无法读取，请确认文件完好或尝试重新上传")
        },
        "IMAGE_PARSE_ALONE_ERROR": {
            "name": lazy_gettext("图片读取失败，请稍后再试（1）")
        },
        "IMAGE_CAN_NOT_DOWNLOAD_FROM_OSS": {
            "name": lazy_gettext("图片读取失败，请稍后再试（2）")
        },
        "IMAGE_TOO_LARGE": {"name": lazy_gettext("图片超过 20MB 无法标记")},
        "IMAGE_OCR_SERVER_DISCONNECT": {
            "name": lazy_gettext("自动标记服务离线，请稍后再试")
        },
    }


class ImageOCRPercent(IntType):
    QUEUING = 0
    WAITING_PARSE_ALONE = 1  # 等待单独OCR
    DOWALOADING = 10  # 下载图片
    MERGING = 20  # 已下载，合并中
    OCRING = 55  # 已合并，OCR中
    LABELING = 90  # 已OCR，标记中
    FINISHED = 100

    details = {
        "QUEUING": {"name": lazy_gettext("已加入队列")},
        "WAITING_PARSE_ALONE": {"name": lazy_gettext("重试中")},
        "DOWALOADING": {"name": lazy_gettext("翻找图片中")},
        "MERGING": {"name": lazy_gettext("整理数据中")},
        "OCRING": {"name": lazy_gettext("图片识别中")},
        "LABELING": {"name": lazy_gettext("标记中")},
        "FINISHED": {"name": lazy_gettext("自动标记完成")},
    }


class FindTermsStatus:
    QUEUING = 0  # 排队中
    FINDING = 1  # 寻找中
    FINISHED = 2  # 解析成功
