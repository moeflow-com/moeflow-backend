from flask_babel import gettext
from marshmallow import Schema, fields, validates_schema
from marshmallow.validate import Range

from app.validators.custom_message import required_message
from app.validators.custom_validate import need_in, object_id
from flask_apikit.exceptions import ValidateError
from app.constants.source import SourcePositionType


class SourceSearchSchema(Schema):
    paging = fields.Bool(missing=True)
    target_id = fields.Str(required=True, validate=[object_id])


class CreateImageSourceSchema(Schema):
    content = fields.Str(missing="")
    x = fields.Float(missing=0, validate=Range(min=0, max=1))
    y = fields.Float(missing=0, validate=Range(min=0, max=1))
    position_type = fields.Int(
        missing=SourcePositionType.IN, validate=[need_in(SourcePositionType.ids())]
    )


class BatchSelectTranslationSchema(Schema):
    source_id = fields.Str(required=True, validate=[object_id])
    translation_id = fields.Str(required=True, validate=[object_id])


class EditImageSourceSchema(Schema):
    content = fields.Str()
    x = fields.Float(validate=Range(min=0, max=1))
    y = fields.Float(validate=Range(min=0, max=1))
    vertices = fields.List(fields.Float())
    position_type = fields.Int(validate=[need_in(SourcePositionType.ids())])

    @validates_schema
    def verify_empty(self, data):
        if len(data) == 0:
            raise ValidateError(gettext("没有有效参数"))


class EditImageSourceRankSchema(Schema):
    next_source_id = fields.Str(required=True, error_messages={**required_message})

    @validates_schema
    def verify_object_id(self, data):
        # 如果不是'end'则必须是object_id
        if data["next_source_id"] != "end":
            object_id(data["next_source_id"])
