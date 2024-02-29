from marshmallow import fields, validates_schema

from app.validators.custom_message import required_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import RoleValidate


class RoleSchema(DefaultSchema):
    name = fields.Str(
        required=True,
        validate=[RoleValidate.name_length],
        error_messages={**required_message},
    )
    level = fields.Int(required=True, error_messages={**required_message})
    permissions = fields.List(
        fields.Int(), required=True, error_messages={**required_message}
    )
    intro = fields.Str(
        required=True,
        validate=[RoleValidate.intro_length],
        error_messages={**required_message},
    )

    @validates_schema
    def verify_level(self, data):
        # 等级不能高于当前用户角色等级
        RoleValidate.valid_level(
            data["level"],
            max=self.context["current_user_role"].level,
            field_name="level",
        )
