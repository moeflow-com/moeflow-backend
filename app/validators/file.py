from marshmallow import Schema, fields

from app.models.file import File
from app.validators.custom_validate import indexes_in, object_id


class FileSearchSchema(Schema):
    word = fields.Str(missing=None)
    parent_id = fields.Str(missing=None, validate=[object_id])
    only_folder = fields.Bool(missing=False)
    only_file = fields.Bool(missing=False)
    order_by = fields.List(fields.Str(), missing=None, validate=[indexes_in(File)])
    target = fields.Str(missing=None, validate=[object_id])


class FileGetSchema(Schema):
    target = fields.Str(missing=None, validate=[object_id])


class FileUploadSchema(Schema):
    parent_id = fields.Str(missing=None, validate=[object_id])


class AdminFileSearchSchema(Schema):
    safe_status = fields.List(fields.Int(), missing=[])
