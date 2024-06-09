import logging
from celery import Celery
from flask import Flask
from flask_apikit import APIKit
from flask_babel import Babel
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.services.google_storage import GoogleStorage
import app.config as _app_config
from app.services.oss import OSS
from .apis import register_apis

from app.models import connect_db

logger = logging.getLogger(__name__)

# singleton modules
babel = Babel()
apikit = APIKit()
oss = OSS()
gs_vision = GoogleStorage()

app_config = {
    k: getattr(_app_config, k) for k in dir(_app_config) if not k.startswith("_")
}


def create_flask_app(app: Flask) -> Flask:
    app.config.from_mapping(app_config)
    connect_db(app.config)
    # print("WTF", app.logger.level)
    # WTF: why is logging so fuking hard in py ecosystem?
    # prevent flask from duplicating logs
    # app.logger.removeHandler(flask_default_handler)
    # app.logger.propagate = False
    return app


def init_flask_app(app: Flask):
    register_apis(app)
    babel.init_app(app)
    apikit.init_app(app)
    logger.info("-" * 50)
    logger.info("站点支持语言: " + str([str(i) for i in babel.list_translations()]))
    oss.init(app.config)  # 文件储存


def create_celery(app: Flask) -> Celery:
    # 通过app配置创建celery实例
    created = Celery(
        app.name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_BACKEND_URL"],
        **app.config["CELERY_BACKEND_SETTINGS"],
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
            "app.tasks.mit",  # only included for completeness's sake. its impl is in other repo.
        ],
        related_name=None,
    )
    created.conf.task_routes = (
        [
            # TODO 'output' should be named better.
            #  its original purpose was cpu-intensive jobs that may block light ones.
            ("tasks.output_project_task", {"queue": "output"}),
            ("tasks.import_from_labelplus_task", {"queue": "output"}),
            ("tasks.mit.*", {"queue": "mit"}),
            ("*", {"queue": "default"}),  # default queue for all other tasks
        ],
    )
    return created


def create_or_override_default_admin(app: Flask):
    """创建或覆盖默认管理员"""
    from app.models.user import User

    admin_user = User.get_by_email(app.config["ADMIN_EMAIL"])
    if admin_user:
        if admin_user.admin is False:
            admin_user.admin = True
            admin_user.save()
            logger.debug("已将 {} 设置为管理员".format(app.config["ADMIN_EMAIL"]))
    else:
        admin_user = User.create(
            name="Admin",
            email=app.config["ADMIN_EMAIL"],
            password="123123",
        )
        admin_user.admin = True
        admin_user.save()
        logger.debug(
            "已创建管理员 {}, 默认密码为 123123，请及时修改！".format(admin_user.email)
        )
    return admin_user


def create_default_team(admin_user):
    from app.models.team import Team, TeamRole
    from app.models.site_setting import SiteSetting

    if Team.objects().count() == 0:
        logger.debug("已建立默认团队")
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
        logger.debug("已有团队，跳过建立默认团队")


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
