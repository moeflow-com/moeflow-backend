from app.constants.base import IntType


class RoleType(IntType):
    """角色类型，用于获取角色"""

    ALL = 0  # 所有角色
    SYSTEM = 1  # 系统角色
    CUSTOM = 2  # 定制角色
