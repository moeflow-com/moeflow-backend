from marshmallow import fields

from app.models.file import File
from app.validators.custom_validate import indexes_in, object_id
from app.validators.custom_schema import DefaultSchema


class FileSearchSchema(DefaultSchema):
    word = fields.Str(missing=None)
    parent_id = fields.Str(missing=None, validate=[object_id])
    only_folder = fields.Bool(missing=False)
    only_file = fields.Bool(missing=False)
    order_by = fields.List(fields.Str(), missing=None, validate=[indexes_in(File)])
    target = fields.Str(missing=None, validate=[object_id])


class FileGetSchema(DefaultSchema):
    target = fields.Str(missing=None, validate=[object_id])


class FileUploadSchema(DefaultSchema):
    parent_id = fields.Str(missing=None, validate=[object_id])


class AdminFileSearchSchema(DefaultSchema):
    safe_status = fields.List(fields.Int(), missing=[])
