import os
import logging

from flask import Flask, g, request

from .factory import (
    app_config,
    create_celery,
    create_flask_app,
    init_flask_app,
    babel,
    oss,
    gs_vision,
)

from app.constants.locale import Locale
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.utils.logging import configure_root_logger, configure_extra_logs

configure_root_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 基本路径
APP_PATH = os.path.abspath(os.path.dirname(__file__))
FILE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "files"))  # 一般文件
TMP_PATH = os.path.abspath(os.path.join(FILE_PATH, "tmp"))  # 临时文件存放地址
STORAGE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "storage"))  # 储存地址

flask_app = create_flask_app(Flask(__name__))
configure_extra_logs(flask_app)
celery = create_celery(flask_app)
init_flask_app(flask_app)


def create_default_team(admin_user):
    from app.models.team import Team, TeamRole
    from app.models.site_setting import SiteSetting

    logger.info("-" * 50)
    if Team.objects().count() == 0:
        logger.info("已建立默认团队")
        team = Team.create(
            name="默认团队",
            creator=admin_user,
        )
        team.intro = "所有新用户会自动加入此团队，如不需要，站点管理员可以在“站点管理-自动加入的团队 ID”中删除此团队 ID。"
        team.allow_apply_type = AllowApplyType.ALL
        team.application_check_type = ApplicationCheckType.ADMIN_CHECK
        team.default_role = TeamRole.by_system_code("member")
        team.save()
        site_setting = SiteSetting.get()
        site_setting.auto_join_team_ids = [team.id]
        site_setting.save()
    else:
        logger.info("已有团队，跳过建立默认团队")


def create_or_override_default_admin(app):
    """创建或覆盖默认管理员"""
    from app.models.user import User

    admin_user = User.get_by_email(app.config["ADMIN_EMAIL"])
    if admin_user:
        if admin_user.admin is False:
            admin_user.admin = True
            admin_user.save()
            logger.info("-" * 50)
            logger.info("已将 {} 设置为管理员".format(app.config["ADMIN_EMAIL"]))
    else:
        admin_user = User.create(
            name="Admin",
            email=app.config["ADMIN_EMAIL"],
            password="123123",
        )
        admin_user.admin = True
        admin_user.save()
        logger.info(
            "已创建管理员 {}, 默认密码为 123123，请及时修改！".format(admin_user.email)
        )
    return admin_user


def create_app():
    return flask_app


def init_db(app: Flask):
    # 初始化角色，语言
    from app.models.language import Language
    from app.models.project import ProjectRole
    from app.models.team import TeamRole
    from app.models.site_setting import SiteSetting

    TeamRole.init_system_roles()
    ProjectRole.init_system_roles()
    Language.init_system_languages()
    SiteSetting.init_site_setting()
    admin_user = create_or_override_default_admin(app)
    create_default_team(admin_user)


@babel.localeselector
def get_locale():
    current_user = g.get("current_user")
    if (
        current_user
        and current_user.locale
        and current_user.locale != "auto"
        and current_user.locale in Locale.ids()
    ):
        return current_user.locale
    return request.accept_languages.best_match(["zh_CN", "zh_TW", "zh", "en_US", "en"])


# @babel.timezoneselector
# def get_timezone():
#     # TODO 弄清 timezone 是什么东西
#     current_user = g.get('current_user')
#     if current_user:
#         if current_user.timezone:
#             return current_user.timezone
