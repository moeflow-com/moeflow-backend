from flask import Blueprint
import os

from app.apis.application import ApplicationAPI, ApplicationListAPI
from app.apis.file import (
    AdminFileListSafeCheckAPI,
    FileAPI,
    FileOCRAPI,
    ProjectFileListAPI,
    AdminFileListAPI,
)
from app.apis.index import PingAPI, DocsAPI, ErrorAPI, UrlListAPI, WarningAPI
from app.apis.invitation import InvitationAPI, InvitationListAPI
from app.apis.group import GroupPublicInfoAPI
from app.apis.me import (
    MeEmailAPI,
    MeInfoAPI,
    MeInvitationListAPI,
    MePasswordAPI,
    MeProjectListAPI,
    MeTeamListAPI,
    MeTokenAPI,
    MeRelatedApplicationListAPI,
)
from app.apis.avatar import AvatarAPI
from app.apis.site_setting import SiteSettingAPI
from app.apis.user import (
    AdminUserAPI,
    AdminUserAdminStatusAPI,
    AdminUserListAPI,
    UserListAPI,
    UserAPI,
)
from app.apis.project import (
    ProjectAPI,
    ProjectDeletePlanAPI,
    ProjectFinishPlanAPI,
    ProjectOCRAPI,
    ProjectOutputListAPI,
    ProjectResumeAPI,
    ProjectTargetListAPI,
    ProjectTargetOutputListAPI,
)
from app.apis.project_set import ProjectSetAPI
from app.apis.role import RoleAPI, RoleListAPI
from app.apis.source import FileSourceListAPI, SourceAPI, SourceRankAPI
from app.apis.team import (
    TeamInsightProjectListAPI,
    TeamInsightProjectUserListAPI,
    TeamInsightUserProjectListAPI,
    TeamListAPI,
    TeamAPI,
    TeamProjectListAPI,
    TeamProjectImportAPI,
    TeamProjectOutputListAPI,
    TeamProjectSetListAPI,
    TeamInsightUserListAPI,
)
from app.apis.member import MemberAPI, MemberListAPI
from app.apis.term import TermAPI, TermBankAPI, TermListAPI
from app.apis.translation import SourceTranslationListAPI, TranslationAPI
from app.apis.type import TypeAPI
from app.apis.v_code import (
    AdminVCodeListAPI,
    CaptchaAPI,
    ConfirmEmailVCodeAPI,
    ResetEmailVCodeAPI,
    ResetPasswordVCodeAPI,
)
from app.apis.language import LanguageListAPI
from app.apis.target import TargetAPI

v1_prefix = "/v1"
# api主页
index = Blueprint("index", __name__, static_folder="static")
index.add_url_rule(
    "/ping", methods=["GET", "OPTIONS"], view_func=PingAPI.as_view("ping")
)
index.add_url_rule(
    "/docs/<path:path>",
    methods=["GET", "OPTIONS"],
    view_func=DocsAPI.as_view("docs"),
)
index.add_url_rule(
    "/urls", methods=["GET", "OPTIONS"], view_func=UrlListAPI.as_view("url_list")
)
index.add_url_rule(
    "/warning",
    methods=["GET", "OPTIONS"],
    view_func=WarningAPI.as_view("warning"),
)
index.add_url_rule(
    "/error", methods=["GET", "OPTIONS"], view_func=ErrorAPI.as_view("error")
)
# type模块
type = Blueprint("type", __name__, url_prefix=v1_prefix + "/types")
type.add_url_rule(
    "/<type_name>",
    methods=["GET", "OPTIONS"],
    view_func=TypeAPI.as_view("type"),
)
# 用户模块
user = Blueprint("user", __name__, url_prefix=v1_prefix + "/users")
user.add_url_rule(
    "/<name>",
    methods=["GET", "OPTIONS"],
    view_func=UserAPI.as_view("user_by_name"),
)
user.add_url_rule(
    "", methods=["GET", "OPTIONS"], view_func=UserListAPI.as_view("user_list")
)
user.add_url_rule("", methods=["POST", "OPTIONS"], view_func=UserAPI.as_view("user"))
# Me模块
me = Blueprint("me", __name__, url_prefix=v1_prefix + "/user")
me.add_url_rule(
    "/info",
    methods=["GET", "PUT", "OPTIONS"],
    view_func=MeInfoAPI.as_view("me_info"),
)
me.add_url_rule(
    "/email",
    methods=["PUT", "OPTIONS"],
    view_func=MeEmailAPI.as_view("me_email"),
)
me.add_url_rule(
    "/password",
    methods=["PUT", "OPTIONS"],
    view_func=MePasswordAPI.as_view("me_password"),
)
me.add_url_rule(
    "/invitations",
    methods=["GET", "OPTIONS"],
    view_func=MeInvitationListAPI.as_view("me_invitation_list"),
)
me.add_url_rule(
    "/related-applications",
    methods=["GET", "OPTIONS"],
    view_func=MeRelatedApplicationListAPI.as_view("me_related_applications_list"),
)
me.add_url_rule(
    "/token",
    methods=["POST", "OPTIONS"],
    view_func=MeTokenAPI.as_view("me_token"),
)
me.add_url_rule(
    "/password",
    methods=["DELETE", "OPTIONS"],
    view_func=MePasswordAPI.as_view("me_reset_password"),
)
me.add_url_rule(
    "/projects",
    methods=["GET", "OPTIONS"],
    view_func=MeProjectListAPI.as_view("me_project_list"),
)
me.add_url_rule(
    "/teams",
    methods=["GET", "OPTIONS"],
    view_func=MeTeamListAPI.as_view("me_team_list"),
)
# 验证码模块
v_code = Blueprint("v_code", __name__, url_prefix=v1_prefix)
v_code.add_url_rule(
    "/captchas",
    methods=["POST", "OPTIONS"],
    view_func=CaptchaAPI.as_view("captcha"),
)
v_code.add_url_rule(
    "/confirm-email-codes",
    methods=["POST", "OPTIONS"],
    view_func=ConfirmEmailVCodeAPI.as_view("confirm_email_v_code"),
)
v_code.add_url_rule(
    "/reset-email-codes",
    methods=["POST", "OPTIONS"],
    view_func=ResetEmailVCodeAPI.as_view("reset_email_v_code"),
)
v_code.add_url_rule(
    "/reset-password-codes",
    methods=["POST", "OPTIONS"],
    view_func=ResetPasswordVCodeAPI.as_view("reset_password_v_code"),
)
# 团队模块
team = Blueprint("team", __name__, url_prefix=v1_prefix + "/teams")
team.add_url_rule(
    "", methods=["GET", "POST", "OPTIONS"], view_func=TeamListAPI.as_view("team_list")
)
team.add_url_rule(
    "/<team_id>",
    methods=["GET", "PUT", "DELETE", "OPTIONS"],
    view_func=TeamAPI.as_view("team"),
)
# 团队挂载模块 团队项目、团队项目集等
team.add_url_rule(
    "/<team_id>/projects",
    methods=["GET", "POST", "OPTIONS"],
    view_func=TeamProjectListAPI.as_view("team_project_list"),
)
team.add_url_rule(
    "/<team_id>/outputs",
    methods=["POST", "OPTIONS"],
    view_func=TeamProjectOutputListAPI.as_view("team_project_output_list"),
)
team.add_url_rule(
    "/<team_id>/project-sets/<project_set_id>/project-zips",
    methods=["GET", "POST", "OPTIONS"],
    view_func=TeamProjectImportAPI.as_view("team_project_import"),
)
team.add_url_rule(
    "/<team_id>/project-sets",
    methods=["GET", "POST", "OPTIONS"],
    view_func=TeamProjectSetListAPI.as_view("team_project_set_list"),
)
team.add_url_rule(
    "/<team_id>/term-banks",
    methods=["GET", "POST", "OPTIONS"],
    view_func=TermBankAPI.as_view("term_bank"),
)
team.add_url_rule(
    "/<team_id>/insight/users",
    methods=["GET", "OPTIONS"],
    view_func=TeamInsightUserListAPI.as_view("user_insights"),
)
team.add_url_rule(
    "/<team_id>/insight/projects",
    methods=["GET", "OPTIONS"],
    view_func=TeamInsightProjectListAPI.as_view("project_insights"),
)
team.add_url_rule(
    "/<team_id>/insight/users/<user_id>/projects",
    methods=["GET", "OPTIONS"],
    view_func=TeamInsightUserProjectListAPI.as_view("user_insights_projects"),
)
team.add_url_rule(
    "/<team_id>/insight/projects/<project_id>/users",
    methods=["GET", "OPTIONS"],
    view_func=TeamInsightProjectUserListAPI.as_view("project_insights_users"),
)
# 项目集模块
project_set = Blueprint("project_set", __name__, url_prefix=v1_prefix + "/project-sets")
project_set.add_url_rule(
    "/<project_set_id>",
    methods=["GET", "PUT", "DELETE", "OPTIONS"],
    view_func=ProjectSetAPI.as_view("team_project_set"),
)
# 术语库模块
term_bank = Blueprint("term_bank", __name__, url_prefix=v1_prefix + "/term-banks")
term_bank.add_url_rule(
    "/<term_bank_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=TermBankAPI.as_view("term_bank"),
)
term_bank.add_url_rule(
    "/<term_bank_id>/terms",
    methods=["GET", "POST", "OPTIONS"],
    view_func=TermListAPI.as_view("term_list"),
)
term = Blueprint("term", __name__, url_prefix=v1_prefix + "/terms")
term.add_url_rule(
    "/<term_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=TermAPI.as_view("term"),
)
# 项目模块
project = Blueprint("project", __name__, url_prefix=v1_prefix + "/projects")
project.add_url_rule(
    "/<project_id>",
    methods=["GET", "PUT", "DELETE", "OPTIONS"],
    view_func=ProjectAPI.as_view("project"),
)
# 项目挂载模块 项目文件等
project.add_url_rule(  # TODO：准备删除
    "/<project_id>/delete-plan",
    methods=["POST", "DELETE", "OPTIONS"],
    view_func=ProjectDeletePlanAPI.as_view("project_delete_plan"),
)
project.add_url_rule(  # TODO：准备删除
    "/<project_id>/finish-plan",
    methods=["POST", "DELETE", "OPTIONS"],
    view_func=ProjectFinishPlanAPI.as_view("project_finish_plan"),
)
project.add_url_rule(
    "/<project_id>/resume",
    methods=["POST", "OPTIONS"],
    view_func=ProjectResumeAPI.as_view("project_resume"),
)
project.add_url_rule(
    "/<project_id>/files",
    methods=["GET", "POST", "OPTIONS"],
    view_func=ProjectFileListAPI.as_view("project_file_list"),
)
project.add_url_rule(
    "/<project_id>/targets",
    methods=["GET", "POST", "OPTIONS"],
    view_func=ProjectTargetListAPI.as_view("project_target_list"),
)
project.add_url_rule(
    "/<project_id>/outputs",
    methods=["POST", "OPTIONS"],
    view_func=ProjectOutputListAPI.as_view("project_output_all_list"),
)
project.add_url_rule(
    "/<project_id>/targets/<target_id>/outputs",
    methods=["GET", "POST", "OPTIONS"],
    view_func=ProjectTargetOutputListAPI.as_view("project_output_list"),
)
project.add_url_rule(
    "/<project_id>/ocr",
    methods=["POST", "OPTIONS"],
    view_func=ProjectOCRAPI.as_view("project_ocr"),
)
# 文件模块
file = Blueprint("file", __name__, url_prefix=v1_prefix + "/files")
file.add_url_rule(
    "/<file_id>",
    methods=["GET", "PUT", "DELETE", "OPTIONS"],
    view_func=FileAPI.as_view("file"),
)
file.add_url_rule(
    "/<file_id>/sources",
    methods=["GET", "POST", "PATCH", "OPTIONS"],
    view_func=FileSourceListAPI.as_view("file_source_list"),
)
file.add_url_rule(
    "/<file_id>/ocr",
    methods=["POST", "OPTIONS"],
    view_func=FileOCRAPI.as_view("file_ocr"),
)
# 原文模块
source = Blueprint("source", __name__, url_prefix=v1_prefix + "/sources")
source.add_url_rule(
    "/<source_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=SourceAPI.as_view("source"),
)
source.add_url_rule(
    "/<source_id>/rank",
    methods=["PUT", "OPTIONS"],
    view_func=SourceRankAPI.as_view("source_rank"),
)
source.add_url_rule(
    "/<source_id>/translations",
    methods=["POST", "OPTIONS"],
    view_func=SourceTranslationListAPI.as_view("source_translation"),
)
# 翻译模块
translation = Blueprint("translation", __name__, url_prefix=v1_prefix + "/translations")
translation.add_url_rule(
    "/<translation_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=TranslationAPI.as_view("translation"),
)
# 团队和项目公用的模块
group = Blueprint("group", __name__, url_prefix=v1_prefix)
group.add_url_rule(
    "/<group_type>/<group_id>/public-info",
    methods=["GET", "OPTIONS"],
    view_func=GroupPublicInfoAPI.as_view("group_public_info"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/invitations",
    methods=["GET", "POST", "OPTIONS"],
    view_func=InvitationListAPI.as_view("invitation_list"),
)
group.add_url_rule(
    "/invitations/<invitation_id>",
    methods=["PUT", "DELETE", "PATCH", "OPTIONS"],
    view_func=InvitationAPI.as_view("invitation"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/applications",
    methods=["GET", "POST", "OPTIONS"],
    view_func=ApplicationListAPI.as_view("application_list"),
)
group.add_url_rule(
    "/applications/<application_id>",
    methods=["PUT", "DELETE", "PATCH", "OPTIONS"],
    view_func=ApplicationAPI.as_view("application"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/roles",
    methods=["GET", "POST", "OPTIONS"],
    view_func=RoleListAPI.as_view("role_list"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/roles/<role_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=RoleAPI.as_view("role"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/users",
    methods=["GET", "OPTIONS"],
    view_func=MemberListAPI.as_view("member_list"),
)
group.add_url_rule(
    "/<group_type>/<group_id>/users/<user_id>",
    methods=["PUT", "DELETE", "OPTIONS"],
    view_func=MemberAPI.as_view("member"),
)
# 目标
target = Blueprint("target", __name__, url_prefix=v1_prefix + "/targets")
target.add_url_rule(
    "/<target_id>",
    methods=["DELETE", "OPTIONS"],
    view_func=TargetAPI.as_view("target"),
)
# 语言
language = Blueprint("language", __name__, url_prefix=v1_prefix + "/languages")
language.add_url_rule(
    "", methods=["GET", "OPTIONS"], view_func=LanguageListAPI.as_view("languages_list")
)
# 头像
avatar = Blueprint("avatar", __name__, url_prefix=v1_prefix + "/avatar")
avatar.add_url_rule(
    "",
    methods=["PUT", "OPTIONS"],
    view_func=AvatarAPI.as_view("avatar"),
)

# 管理员
admin = Blueprint("admin", __name__, url_prefix=v1_prefix + "/admin")
admin.add_url_rule(
    "/files",
    methods=["GET", "OPTIONS"],
    view_func=AdminFileListAPI.as_view("admin_file_list"),
)
admin.add_url_rule(
    "/files/safe-status",
    methods=["PUT", "OPTIONS"],
    view_func=AdminFileListSafeCheckAPI.as_view("admin_file_list_safe_check"),
)
admin.add_url_rule(
    "/admin-status",
    methods=["PUT", "OPTIONS"],
    view_func=AdminUserAdminStatusAPI.as_view("admin_admin_status"),
)
admin.add_url_rule(
    "/users",
    methods=["GET", "POST", "OPTIONS"],
    view_func=AdminUserListAPI.as_view("admin_user_list"),
)
admin.add_url_rule(
    "/site-setting",
    methods=["GET", "PUT", "OPTIONS"],
    view_func=SiteSettingAPI.as_view("admin_site_setting"),
)
admin.add_url_rule(
    "/users/<user_id>",
    methods=["PUT", "OPTIONS"],
    view_func=AdminUserAPI.as_view("admin_edit_user_password"),
)
admin.add_url_rule(
    "/v-codes",
    methods=["GET", "OPTIONS"],
    view_func=AdminVCodeListAPI.as_view("admin_v_code_list"),
)
