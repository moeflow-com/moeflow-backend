from app.constants.base import IntType


class MessageType(IntType):
    USER = 0  # 用户
    SYSTEM = 1  # 系统
    INVITE = 2  # 邀请
    APPLY = 3  # 申请
