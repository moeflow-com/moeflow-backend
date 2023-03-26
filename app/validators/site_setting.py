from marshmallow import Schema, fields

from app.validators.custom_message import required_message, email_invalid_message


class SiteSettingSchema(Schema):
    enable_whitelist = fields.Boolean(
        required=True, error_messages={**required_message}
    )
    whitelist_emails = fields.List(
        fields.Email(),
        required=True,
        error_messages={**required_message},
    )
