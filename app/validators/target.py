from marshmallow import Schema, fields


class TargetSearchSchema(Schema):
    word = fields.Str(missing=None)
