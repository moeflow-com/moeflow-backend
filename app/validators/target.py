from marshmallow import fields

from app.validators.custom_schema import DefaultSchema


class TargetSearchSchema(DefaultSchema):
    word = fields.Str(missing=None)
