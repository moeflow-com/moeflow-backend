from typing import Literal

from app.constants.base import IntType


class VCodeType(IntType):
    CAPTCHA = 1  # 人机验证码
    CONFIRM_EMAIL = 2  # 验证邮箱
    RESET_EMAIL = 3  # 重设邮箱
    RESET_PASSWORD = 4  # 重置密码
    CONFIRM_PHONE = 5  # 验证手机
    RESET_PHONE = 6  # 重设手机


VCodeTypes = Literal[1, 2, 3, 4, 5, 6]


class VCodeContentType(IntType):
    NUMBER = 1  # 纯数字
    LETTER = 2  # 纯字幕
    NUMBER_AND_LETTER = 3  # 数字字幕混合


VCodeContentTypes = Literal[1, 2, 3]
VCodeAddressTypes = Literal["email", "sms"]
