from marshmallow import Schema, fields

from app.validators.custom_message import required_message, email_invalid_message
from app.validators.custom_validate import object_id


class SiteSettingSchema(Schema):
    enable_whitelist = fields.Boolean(
        required=True, error_messages={**required_message}
    )
    whitelist_emails = fields.List(
        fields.Email(),
        required=True,
        error_messages={**required_message},
    )
    only_allow_admin_create_team = fields.Boolean(
        required=True, error_messages={**required_message}
    )
    auto_join_team_ids = fields.List(
        fields.Str(
            validate=[object_id],
        ),
        required=True,
        error_messages={**required_message},
    )
