from marshmallow import Schema


class DefaultSchema(Schema):
    # marshmallow的默认配置
    class Meta:
        unknown = 'EXCLUDE' # required to ignore unknown fields, since marshmallow 3.0.0rc9
