from marshmallow import fields

from app.validators.custom_message import required_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import object_id


class ChangeMemberSchema(DefaultSchema):
    """修改团队用户验证器"""

    role = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
