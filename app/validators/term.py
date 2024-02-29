from marshmallow import fields, post_load

from app.models.language import Language
from app.validators.custom_message import required_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import (
    TermBankValidate,
    TermValidate,
    object_id,
)


class TermBankSchema(DefaultSchema):
    name = fields.Str(
        required=True,
        validate=[TermBankValidate.name_length],
        error_messages={**required_message},
    )
    tip = fields.Str(
        required=True,
        validate=[TermBankValidate.tip_length],
        error_messages={**required_message},
    )
    source_language_id = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    target_language_id = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取语言模型对象
        in_data["source_language"] = Language.by_id(in_data["source_language_id"])
        in_data["target_language"] = Language.by_id(in_data["target_language_id"])
        return in_data


class TermSchema(DefaultSchema):
    source = fields.Str(
        required=True,
        validate=[TermValidate.source_length],
        error_messages={**required_message},
    )
    target = fields.Str(
        required=True,
        validate=[TermValidate.target_length],
        error_messages={**required_message},
    )
    tip = fields.Str(
        required=True,
        validate=[TermValidate.tip_length],
        error_messages={**required_message},
    )
