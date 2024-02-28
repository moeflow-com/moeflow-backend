from marshmallow import fields, post_load, validates_schema

from app.models.team import Team
from app.constants.role import RoleType
from app.validators.custom_message import required_message
from app.validators.custom_schema import DefaultSchema
from app.validators.custom_validate import TeamValidate, need_in, object_id


class CreateTeamSchema(DefaultSchema):
    """创建团队验证器"""

    name = fields.Str(
        required=True,
        validate=[TeamValidate.valid_new_name],
        error_messages={**required_message},
    )
    intro = fields.Str(
        required=True,
        validate=[TeamValidate.intro_length],
        error_messages={**required_message},
    )
    allow_apply_type = fields.Int(
        required=True, validate=[need_in(Team.allow_apply_type_cls.ids())]
    )
    application_check_type = fields.Int(
        required=True,
        validate=[need_in(Team.application_check_type_cls.ids())],
    )
    default_role = fields.Str(required=True, validate=[object_id])

    @validates_schema
    def verify_default_role(self, data):
        # 角色必须在系统团队的角色中
        need_in(
            [str(role.id) for role in Team.role_cls.system_roles(without_creator=True)]
        )(data["default_role"], field_name="default_role")

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取默认角色
        in_data["default_role"] = Team.role_cls.by_id(in_data["default_role"])
        return in_data


class EditTeamSchema(DefaultSchema):
    """修改团队验证器"""

    name = fields.Str(error_messages={**required_message})
    intro = fields.Str(
        validate=[TeamValidate.intro_length],
        error_messages={**required_message},
    )
    allow_apply_type = fields.Int(validate=[need_in(Team.allow_apply_type_cls.ids())])
    application_check_type = fields.Int(
        validate=[need_in(Team.application_check_type_cls.ids())]
    )
    default_role = fields.Str(validate=[object_id])

    @validates_schema
    def verify_name(self, data):
        # 如果新名字和旧名字不同,检查是否合法
        if "name" in data and data["name"] != self.context["team"].name:
            TeamValidate.valid_new_name(data["name"], field_name="name")

    @validates_schema
    def verify_default_role(self, data):
        # 角色必须在团队的角色中
        if "default_role" in data:
            need_in(
                [
                    str(role.id)
                    for role in self.context["team"].roles(
                        type=RoleType.ALL, without_creator=True
                    )
                ]
            )(data["default_role"], field_name="default_role")

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取默认角色
        if "default_role" in in_data:
            in_data["default_role"] = Team.role_cls.by_id(in_data["default_role"])
        return in_data
