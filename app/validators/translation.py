from flask_babel import gettext
from marshmallow import fields, validates_schema

from app.validators.custom_message import required_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import object_id
from flask_apikit.exceptions import ValidateError


class CreateTranslationSchema(DefaultSchema):
    content = fields.Str(required=True, error_messages={**required_message})
    target_id = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )


class EditTranslationSchema(DefaultSchema):
    content = fields.Str()
    proofread_content = fields.Str()
    selected = fields.Bool()

    @validates_schema
    def verify_empty(self, data):
        if len(data) == 0:
            raise ValidateError(gettext("没有有效参数"))
