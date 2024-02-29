from marshmallow import fields, validates_schema

from app.models.v_code import VCodeType
from app.constants.locale import Locale
from app.validators.custom_message import (
    email_invalid_message,
    required_message,
)

from .custom_validate import UserValidate, cant_empty, need_in
from .custom_schema import DefaultSchema
from .v_code import captcha_validator, password_validator, v_code_validator


class RegisterSchema(DefaultSchema):
    """注册验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.valid_new_email],
        error_messages={**required_message, **email_invalid_message},
    )
    name = fields.Str(
        required=True,
        validate=[UserValidate.valid_new_name],
        error_messages={**required_message},
    )
    password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )
    # 邮件验证码
    v_code = fields.Str(
        required=True,
        validate=[cant_empty],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_v_code(self, data):
        v_code_validator(VCodeType.CONFIRM_EMAIL, data["email"].lower(), data["v_code"])


class LoginSchema(DefaultSchema):
    """登录验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.exist_email],
        error_messages={**required_message, **email_invalid_message},
    )
    password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )
    captcha_info = fields.Str(required=True, error_messages={**required_message})
    captcha = fields.Str(required=True, error_messages={**required_message})

    @validates_schema
    def verify_captcha_and_password(self, data):
        captcha_validator(data["captcha_info"], data["captcha"])
        # 验证人机验证码后，再验证密码（如果出错不返回密码验证状态）
        password_validator(data["email"], data["password"])


class ChangeInfoSchema(DefaultSchema):
    """修改信息验证"""

    name = fields.Str(required=True, error_messages={**required_message})
    signature = fields.Str(
        required=True,
        validate=[UserValidate.signature_length],
        error_messages={**required_message},
    )
    locale = fields.Str(
        required=True,
        validate=[need_in(Locale.ids())],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_name(self, data):
        # 如果新名字和旧名字不同,检查新名称是否合法
        if data["name"] != self.context["old_name"]:
            UserValidate.valid_new_name(data["name"], field_name="name")


class ChangeEmailSchema(DefaultSchema):
    """修改Email验证"""

    old_email_v_code = fields.Str(required=True, error_messages={**required_message})
    new_email = fields.Email(
        required=True,
        validate=[UserValidate.valid_new_email],
        error_messages={**required_message, **email_invalid_message},
    )
    new_email_v_code = fields.Str(required=True, error_messages={**required_message})

    @validates_schema
    def verify_old_email_v_code(self, data):
        v_code_validator(
            VCodeType.RESET_EMAIL,
            self.context["old_email"].lower(),
            data["old_email_v_code"],
            "old_email_v_code",
            delete_after_verified=False,
        )

    @validates_schema
    def verify_new_email_v_code(self, data):
        v_code_validator(
            VCodeType.CONFIRM_EMAIL,
            data["new_email"].lower(),
            data["new_email_v_code"],
            "new_email_v_code",
            delete_after_verified=False,
        )


class ChangePasswordSchema(DefaultSchema):
    """修改密码验证"""

    old_password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )
    new_password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_password(self, data):
        password_validator(self.context["email"], data["old_password"], "old_password")


class ResetPasswordSchema(DefaultSchema):
    """重置密码验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.exist_email],
        error_messages={**required_message, **email_invalid_message},
    )
    v_code = fields.Str(required=True, error_messages={**required_message})
    password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_v_code(self, data):
        v_code_validator(
            VCodeType.RESET_PASSWORD, data["email"].lower(), data["v_code"]
        )


class AdminRegisterSchema(DefaultSchema):
    """注册验证"""

    email = fields.Email(
        required=True,
        validate=[UserValidate.valid_new_email],
        error_messages={**required_message, **email_invalid_message},
    )
    name = fields.Str(
        required=True,
        validate=[UserValidate.valid_new_name],
        error_messages={**required_message},
    )
    password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )


class AdminEditUserPasswordSchema(DefaultSchema):
    """管理后台修改密码验证"""

    password = fields.Str(
        required=True,
        validate=[UserValidate.password_length],
        error_messages={**required_message},
    )
