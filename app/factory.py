import logging
import celery
from flask import Flask
from flask_apikit import APIKit
from flask_babel import Babel
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.services.google_storage import GoogleStorage
import app.config as _app_config
from app.services.oss import OSS
from .apis import register_apis
from app.translations import get_request_locale

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

_create_flask_app_called = False


def create_flask_app(app: Flask) -> Flask:
    global _create_flask_app_called
    assert not _create_flask_app_called, "create_flask_app should only be called once"
    _create_flask_app_called = True
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
    babel.init_app(
        app,
        locale_selector=get_request_locale,
        default_locale=app_config["BABEL_DEFAULT_LOCALE"],
    )
    apikit.init_app(app)
    logger.info(f"----- build id: {app_config['BUILD_ID']}")
    with app.app_context():
        logger.debug(
            "Server locale translations: "
            + str([str(i) for i in babel.list_translations()])
        )
    oss.init(app.config)  # 文件储存


def create_celery(app: Flask) -> celery.Celery:
    # see https://flask.palletsprojects.com/en/stable/patterns/celery/
    class FlaskTask(celery.Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    created = celery.Celery(
        app.name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_BACKEND_URL"],
        task_cls=FlaskTask,
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
            password=app.config["ADMIN_INITIAL_PASSWORD"],
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
        logger.debug("creating default team")
        team = Team.create(
            name="Default Team",
            creator=admin_user,
        )
        team.intro = """
        All new users will automatically join this team. This can be disabled by site administrator.
        所有新用户会自动加入此团队，如不需要，站点管理员可以在“站点管理-自动加入的团队 ID”中删除此团队 ID。""".strip()
        team.allow_apply_type = AllowApplyType.ALL
        team.application_check_type = ApplicationCheckType.ADMIN_CHECK
        team.default_role = TeamRole.by_system_code("member")
        team.save()
        site_setting = SiteSetting.get()
        site_setting.auto_join_team_ids = [team.id]
        site_setting.save()
    else:
        logger.debug("default team existed")


def init_db(app: Flask):
    """init db models"""
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
