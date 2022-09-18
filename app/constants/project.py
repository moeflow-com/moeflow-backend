from flask_babel import lazy_gettext

from app.constants.base import IntType


class ProjectStatus(IntType):
    """项目状态"""

    WORKING = 0  # 进行中
    FINISHED = 1  # 已完结
    PLAN_FINISH = 2  # 处于完结计划（准备删除这个状态）
    PLAN_DELETE = 3  # 处于销毁计划（准备删除这个状态）
    DELETED = 4  # 已删除（标记删除功能还未实现）

    details = {
        "WORKING": {"name": lazy_gettext("进行中")},
        "FINISHED": {"name": lazy_gettext("已完结")},
        "PLAN_FINISH": {"name": lazy_gettext("等待完结")},
        "PLAN_DELETE": {"name": lazy_gettext("等待销毁")},
        "DELETED": {"name": lazy_gettext("已删除")},
    }


class ImportFromLabelplusStatus(IntType):
    PENDING = 0  # 排队中
    RUNNING = 1  # 进行中
    SUCCEEDED = 2  # 成功
    ERROR = 3  # 错误

    details = {
        "PENDING": {"name": lazy_gettext("排队中")},
        "RUNNING": {"name": lazy_gettext("进行中")},
        "SUCCEEDED": {"name": lazy_gettext("成功")},
        "ERROR": {"name": lazy_gettext("错误")},
    }


class ImportFromLabelplusErrorType(IntType):
    UNKNOWN = 0  # 未知
    NO_TARGET = 1  # 运行时，没有的翻译目标
    NO_CREATOR = 2  # 项目没有创建人
    PARSE_FAILED = 3  # 解析失败

    details = {
        "UNKNOWN": {"name": lazy_gettext("从 Labelplus 文本导入中断，请重试，如仍出现同样错误，请联系开发团队")},
        "NO_TARGET": {"name": lazy_gettext("从 Labelplus 文本导入时，没有有效的翻译目标语言")},
        "NO_CREATOR": {"name": lazy_gettext("从 Labelplus 文本导入时，项目没有创建人")},
        "PARSE_FAILED": {"name": lazy_gettext("Labelplus 文本解析失败，请联系开发团队")},
    }
