from app.exceptions import RoleNotExistError, UserNotExistError
from app.exceptions.base import RequestDataWrongError
from app.models.user import User
from app.validators.custom_message import required_message
from app.validators.custom_validate import JoinValidate, object_id
from flask_babel import lazy_gettext
from marshmallow import Schema, fields, validates_schema


class EditAvatarSchema(Schema):
    type = fields.Str(required=True, error_messages={**required_message},)
    id = fields.Str(
        missing=None, validate=[object_id], error_messages={**required_message},
    )

    @validates_schema
    def verify_v_code(self, data):
        if data["type"] not in ["user", "team"]:
            raise RequestDataWrongError(lazy_gettext("不支持的头像类型"))
        if data["type"] != "user" and data["id"] is None:
            raise RequestDataWrongError(lazy_gettext("缺少id"))
