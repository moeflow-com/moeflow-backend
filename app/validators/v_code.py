from flask_babel import gettext
from marshmallow import ValidationError, fields, validates_schema

from app.exceptions import VCodeRootError
from app.models.user import User
from app.models.v_code import Captcha, VCode
from app.validators.custom_message import (
    email_invalid_message,
    required_message,
)
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import UserValidate


def password_validator(email, password, field_name="password"):
    """
    密码验证器

    :param email: 邮箱
    :param password: 密码
    :param field_name: 验证错误显示字段的名称
    :return:
    """
    # 密码错误
    user = User.get_by_email(email)
    if user is None:
        raise ValidationError(gettext("用户不存在"), [field_name])
    if not user.verify_password(password):
        raise ValidationError(gettext("密码错误"), [field_name])


def captcha_validator(info, content, field_name="captcha"):
    """
    人机验证码验证器

    :param info: 验证码标识符
    :param content: 验证码内容
    :param field_name: 验证错误显示字段的名称
    :return:
    """
    try:
        Captcha.verify(code_info=info, code_content=content)
    except VCodeRootError as e:
        raise ValidationError(e.message, [field_name])


def v_code_validator(
    v_code_type, info, content, field_name="v_code", delete_after_verified=True
):
    """
    验证码验证器

    :param v_code_type: 验证码类型
    :param info: 验证码标识符
    :param content: 验证码内容
    :param field_name: 验证错误显示字段的名称
    :return:
    """
    try:
        VCode.verify(
            code_type=v_code_type,
            code_info=info,
            code_content=content,
            delete_after_verified=delete_after_verified,
        )
    except VCodeRootError as e:
        raise ValidationError(e.message, [field_name])


class ConfirmEmailVCodeSchema(DefaultSchema):
    """发送确认邮箱邮件验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.valid_new_email],
        error_messages={**required_message, **email_invalid_message},
    )
    captcha_info = fields.Str(
        required=True, error_messages={**required_message}
    )
    captcha = fields.Str(required=True, error_messages={**required_message})

    @validates_schema
    def verify_captcha(self, data):
        captcha_validator(data["captcha_info"], data["captcha"])


class ResetPasswordVCodeSchema(DefaultSchema):
    """发送重置密码邮件验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.exist_email],
        error_messages={**required_message, **email_invalid_message},
    )
    captcha_info = fields.Str(
        required=True, error_messages={**required_message}
    )
    captcha = fields.Str(required=True, error_messages={**required_message})

    @validates_schema
    def verify_captcha(self, data):
        captcha_validator(data["captcha_info"], data["captcha"])
