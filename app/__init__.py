import os

from celery import Celery
from celery.signals import worker_shutting_down
from flask import Flask, g, request, render_template
from flask_apikit import APIKit
from flask_babel import Babel

from app.constants.locale import Locale
from app.services.google_storage import GoogleStorage
from app.services.oss import OSS
from app.utils.logging import configure_logger, logger

from .apis import register_apis

# 基本路径
APP_PATH = os.path.abspath(os.path.dirname(__file__))
FILE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "files"))  # 一般文件
TMP_PATH = os.path.abspath(os.path.join(FILE_PATH, "tmp"))  # 临时文件存放地址
# 插件
babel = Babel()
oss = OSS()
gs_vision = GoogleStorage()
apikit = APIKit()

config_path_env = "CONFIG_PATH"


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
            password="moe123456",
        )
        admin_user.admin = True
        admin_user.save()
        logger.info("已创建管理员 {}, 默认密码为 moe123456，请及时修改！".format(admin_user.email))


def create_app():
    app = Flask(__name__)
    app.config.from_envvar(config_path_env)  # 获取配置文件,仅从环境变量读取,均需要配置环境变量
    configure_logger(app)  # 配置日志记录(放在最前,会被下面调用)

    logger.info("-" * 50)
    logger.info("使用配置文件: {}".format(os.environ.get(config_path_env)))
    # 连接数据库
    from app.models import connect_db

    connect_db(app.config)
    # 注册api蓝本
    register_apis(app)
    # 初始化角色，语言
    from app.models.language import Language
    from app.models.project import ProjectRole
    from app.models.team import TeamRole

    TeamRole.init_system_roles()
    ProjectRole.init_system_roles()
    Language.init_system_languages()
    # 初始化插件
    babel.init_app(app)
    apikit.init_app(app)

    logger.info("-" * 50)
    logger.info("站点支持语言: " + str([str(i) for i in babel.list_translations()]))
    oss.init(app.config)  # 文件储存

    create_or_override_default_admin(app)

    # from app.tasks.ocr import recover_ocr_tasks

    # recover_ocr_tasks()
    return app


CELERY_ABOUT_TO_SHUTDOWN_FLAG = "CELERY_ABOUT_TO_SHUTDOWN_FLAG"


def delete_about_to_shutdown_flag():
    try:
        os.rmdir(CELERY_ABOUT_TO_SHUTDOWN_FLAG)
    except Exception:
        pass


def create_celery():
    delete_about_to_shutdown_flag()
    # 为celery创建app
    app = Flask(__name__)
    app.config.from_envvar(config_path_env)  # 获取配置文件,仅从环境变量读取,均需要配置环境变量
    # 通过app配置创建celery实例
    celery = Celery(
        app.name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_BACKEND_URL"],
        mongodb_backend_settings=app.config["CELERY_MONGODB_BACKEND_SETTINGS"],
    )
    celery.conf.update({"app_config": app.config})
    celery.autodiscover_tasks(
        packages=[
            "app.tasks.email",
            "app.tasks.file_parse",
            "app.tasks.output_project",
            "app.tasks.ocr",
            "app.tasks.import_from_labelplus",
        ],
        related_name=None,
    )
    celery.conf.task_routes = {
        "tasks.ocr_task": {"queue": "ocr"},
        "tasks.output_project_task": {"queue": "output"},
        "tasks.import_from_labelplus_task": {"queue": "output"},
    }
    return celery


celery = create_celery()


def create_about_to_shutdown_flag():
    try:
        os.mkdir(CELERY_ABOUT_TO_SHUTDOWN_FLAG)
    except Exception:
        pass


@worker_shutting_down.connect
def when_shutdown(**kwargs):
    create_about_to_shutdown_flag()


def about_to_shutdown():
    """检测 Celery 是否将要关闭"""
    return os.path.isdir(CELERY_ABOUT_TO_SHUTDOWN_FLAG)


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
