from app.exceptions.base import RequestDataWrongError
from app.validators.custom_message import required_message
from app.validators.custom_validate import object_id
from app.validators.custom_schema import DefaultSchema
from flask_babel import lazy_gettext
from marshmallow import fields, validates_schema


class EditAvatarSchema(DefaultSchema):
    type = fields.Str(
        required=True,
        error_messages={**required_message},
    )
    id = fields.Str(
        missing=None,
        validate=[object_id],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_v_code(self, data):
        if data["type"] not in ["user", "team"]:
            raise RequestDataWrongError(lazy_gettext("不支持的头像类型"))
        if data["type"] != "user" and data["id"] is None:
            raise RequestDataWrongError(lazy_gettext("缺少id"))
