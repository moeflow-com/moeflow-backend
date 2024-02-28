from marshmallow import fields, post_load, validates_schema

from app.exceptions import ProjectSetNotExistError, LanguageNotExistError
from app.models.project import Project, ProjectSet
from app.models.language import Language
from app.constants.project import ProjectStatus
from app.constants.role import RoleType
from app.constants.output import OutputTypes
from app.validators.custom_message import required_message
from app.validators.custom_validate import (
    ProjectSetValidate,
    ProjectValidate,
    need_in,
    object_id,
)
from app.validators.custom_schema import DefaultSchema
from marshmallow.exceptions import ValidationError


class ProjectSetsSchema(DefaultSchema):
    name = fields.Str(
        required=True,
        validate=[ProjectSetValidate.name_length],
        error_messages={**required_message},
    )


class SearchTeamProjectSchema(DefaultSchema):
    """搜索团队下项目验证器"""

    status = fields.List(
        fields.Int(validate=[need_in(ProjectStatus.ids())]), missing=None
    )
    word = fields.Str(missing=None)
    project_set = fields.Str(missing=None)

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        if in_data["project_set"]:
            project_set = ProjectSet.objects(
                id=in_data["project_set"], team=self.context["team"]
            ).first()
            # team下没有此project_set
            if project_set is None:
                raise ProjectSetNotExistError
            in_data["project_set"] = project_set
            return in_data


class SearchUserProjectSchema(DefaultSchema):
    """搜索用户下项目验证器"""

    status = fields.List(
        fields.Int(validate=[need_in(ProjectStatus.ids())]), missing=None
    )
    word = fields.Str(missing=None)


class CreateProjectSchema(DefaultSchema):
    """创建项目验证器"""

    name = fields.Str(
        required=True,
        validate=[ProjectValidate.name_length],
        error_messages={**required_message},
    )
    intro = fields.Str(
        required=True,
        validate=[ProjectValidate.intro_length],
        error_messages={**required_message},
    )
    allow_apply_type = fields.Int(
        required=True,
        validate=[need_in(Project.allow_apply_type_cls.ids())],
        error_messages={**required_message},
    )
    application_check_type = fields.Int(
        required=True,
        validate=[need_in(Project.application_check_type_cls.ids())],
        error_messages={**required_message},
    )
    default_role = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    project_set = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    source_language = fields.Str(
        required=True,
        validate=[need_in(Language.codes)],
        error_messages={**required_message},
    )
    target_languages = fields.List(
        fields.Str(
            required=True,
            validate=[need_in(Language.codes)],
            error_messages={**required_message},
        ),
        required=True,
    )
    labelplus_txt = fields.Str(missing=None)

    @validates_schema
    def verify_default_role(self, data):
        # 角色必须在系统团队的角色中
        need_in(
            [
                str(role.id)
                for role in Project.role_cls.system_roles(without_creator=True)
            ]
        )(data["default_role"], field_name="default_role")

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取默认角色
        in_data["default_role"] = Project.role_cls.by_id(in_data["default_role"])
        # 必须是项目所在团队的项目集
        project_set = (
            self.context["team"]
            .project_sets()
            .filter(id=in_data["project_set"])
            .first()
        )
        if project_set is None:
            raise ProjectSetNotExistError
        in_data["project_set"] = project_set
        # 获取源语言
        try:
            in_data["source_language"] = Language.by_code(in_data["source_language"])
        except LanguageNotExistError as e:
            raise ValidationError(e.message, field_names="source_language")
        # 获取目标语言
        try:
            in_data["target_languages"] = Language.by_codes(in_data["target_languages"])
        except LanguageNotExistError as e:
            raise ValidationError(e.message, field_names="target_languages")
        return in_data


class ImportProjectSchema(DefaultSchema):
    """创建项目验证器"""

    name = fields.Str(
        required=True,
        validate=[ProjectValidate.name_length],
        error_messages={**required_message},
    )
    intro = fields.Str(
        required=True,
        validate=[ProjectValidate.intro_length],
        error_messages={**required_message},
    )
    allow_apply_type = fields.Int(
        required=True,
        validate=[need_in(Project.allow_apply_type_cls.ids())],
        error_messages={**required_message},
    )
    application_check_type = fields.Int(
        required=True,
        validate=[need_in(Project.application_check_type_cls.ids())],
        error_messages={**required_message},
    )
    default_role = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    project_set = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )
    source_language = fields.Str(
        required=True,
        validate=[need_in(Language.codes)],
        error_messages={**required_message},
    )
    output_language = fields.Str(
        required=True,
        validate=[need_in(Language.codes)],
        error_messages={**required_message},
    )
    labelplus_txt = fields.Str(missing=None)

    @validates_schema
    def verify_default_role(self, data):
        # 角色必须在系统团队的角色中
        need_in(
            [
                str(role.id)
                for role in Project.role_cls.system_roles(without_creator=True)
            ]
        )(data["default_role"], field_name="default_role")

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取默认角色
        in_data["default_role"] = Project.role_cls.by_id(in_data["default_role"])
        # 必须是项目所在团队的项目集
        project_set = (
            self.context["team"]
            .project_sets()
            .filter(id=in_data["project_set"])
            .first()
        )
        if project_set is None:
            raise ProjectSetNotExistError
        in_data["project_set"] = project_set
        # 获取源语言
        try:
            in_data["source_language"] = Language.by_code(in_data["source_language"])
        except LanguageNotExistError as e:
            raise ValidationError(e.message, field_names="source_language")
        # 获取目标语言
        try:
            in_data["output_language"] = Language.by_code(in_data["output_language"])
        except LanguageNotExistError as e:
            raise ValidationError(e.message, field_names="output_language")
        return in_data


class EditProjectSchema(DefaultSchema):
    """修改项目验证器"""

    name = fields.Str(
        validate=[ProjectValidate.name_length],
        error_messages={**required_message},
    )
    intro = fields.Str(
        validate=[ProjectValidate.intro_length],
        error_messages={**required_message},
    )
    allow_apply_type = fields.Int(
        validate=[need_in(Project.allow_apply_type_cls.ids())]
    )
    application_check_type = fields.Int(
        validate=[need_in(Project.application_check_type_cls.ids())]
    )
    default_role = fields.Str(validate=[object_id])
    project_set = fields.Str(validate=[object_id])

    @validates_schema
    def verify_default_role(self, data):
        # 角色必须在团队的角色中
        if "default_role" in data:
            need_in(
                [
                    str(role.id)
                    for role in self.context["project"].roles(
                        type=RoleType.ALL, without_creator=True
                    )
                ]
            )(data["default_role"], field_name="default_role")

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        # 获取默认角色
        if "default_role" in in_data:
            in_data["default_role"] = Project.role_cls.by_id(in_data["default_role"])
        if "project_set" in in_data:
            # 必须是项目所在团队的项目集
            project_set = (
                self.context["project"]
                .team.project_sets()
                .filter(id=in_data["project_set"])
                .first()
            )
            if project_set is None:
                raise ProjectSetNotExistError
            in_data["project_set"] = project_set
        return in_data


class ChangeProjectUserSchema(DefaultSchema):
    """修改项目用户验证器"""

    role = fields.Str(
        required=True,
        validate=[object_id],
        error_messages={**required_message},
    )


class CreateProjectTargetSchema(DefaultSchema):
    """创建项目目标验证器"""

    language = fields.Str(
        required=True,
        validate=[need_in(Language.codes)],
        error_messages={**required_message},
    )

    @post_load
    def to_model(self, in_data):
        """通过id获取模型，以供直接使用"""
        in_data["language"] = Language.by_code(in_data["language"])
        return in_data


class CreateOutputSchema(DefaultSchema):
    """创建导出内容验证器"""

    type = fields.Int(
        required=True,
        validate=[need_in(OutputTypes.ids())],
        error_messages={**required_message},
    )
    file_ids_include = fields.List(fields.Str(validate=[object_id]), missing=None)
    file_ids_exclude = fields.List(fields.Str(validate=[object_id]), missing=None)


class TeamInsightUserListSchema(DefaultSchema):
    word = fields.Str(missing=None)


class TeamInsightProjectListSchema(DefaultSchema):
    word = fields.Str(missing=None)
