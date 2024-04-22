import os

from celery import Celery
from flask import Flask, g, request
from flask_apikit import APIKit
from flask_babel import Babel

from app.constants.locale import Locale
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.services.google_storage import GoogleStorage
from app.services.oss import OSS
from app.utils.logging import configure_logger, logger

from .apis import register_apis
import app.config as _app_config

app_config = {
    k: getattr(_app_config, k) for k in dir(_app_config) if not k.startswith("_")
}

# 基本路径
APP_PATH = os.path.abspath(os.path.dirname(__file__))
FILE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "files"))  # 一般文件
TMP_PATH = os.path.abspath(os.path.join(FILE_PATH, "tmp"))  # 临时文件存放地址
STORAGE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "storage"))  # 储存地址
# 插件
babel = Babel()
oss = OSS()
gs_vision = GoogleStorage()
apikit = APIKit()

config_path_env = "CONFIG_PATH"


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
    app = Flask(__name__)
    app.config.from_mapping(app_config)
    configure_logger(app)  # 配置日志记录(放在最前,会被下面调用)

    logger.info("-" * 50)
    # 连接数据库
    from app.models import connect_db

    connect_db(app.config)
    # 注册api蓝本
    register_apis(app)
    # 初始化插件
    babel.init_app(app)
    apikit.init_app(app)

    logger.info("-" * 50)
    logger.info("站点支持语言: " + str([str(i) for i in babel.list_translations()]))
    oss.init(app.config)  # 文件储存

    return app


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


def create_celery() -> Celery:
    # 为celery创建app
    app = Flask(__name__)
    app.config.from_mapping(app_config)
    # 通过app配置创建celery实例
    created = Celery(
        app.name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_BACKEND_URL"],
        mongodb_backend_settings=app.config["CELERY_MONGODB_BACKEND_SETTINGS"],
    )
    created.conf.update({"app_config": app.config})
    created.autodiscover_tasks(
        packages=[
            "app.tasks.email",
            "app.tasks.file_parse",
            "app.tasks.output_team_projects",
            "app.tasks.output_project",
            "app.tasks.ocr",
            "app.tasks.import_from_labelplus",
            "app.tasks.thumbnail",
        ],
        related_name=None,
    )
    created.conf.task_routes = {
        "tasks.ocr_task": {"queue": "ocr"},
        "tasks.output_project_task": {"queue": "output"},
        "tasks.import_from_labelplus_task": {"queue": "output"},
    }
    return created


celery = create_celery()


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
