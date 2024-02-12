from marshmallow import fields

from app.validators.custom_message import required_message, email_invalid_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import object_id


class SiteSettingSchema(DefaultSchema):
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
    homepage_html = fields.Str()
    homepage_css = fields.Str()
