from marshmallow import Schema, fields

from app.validators.custom_message import required_message
from app.validators.custom_validate import object_id


class AdminStatusSchema(Schema):
    user_id = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    status = fields.Bool(
        required=True,
        error_messages={**required_message},
    )
