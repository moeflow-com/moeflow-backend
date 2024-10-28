import os
import logging

from flask import Flask

from .factory import (
    app_config,
    create_celery,
    create_flask_app,
    init_flask_app,
    oss,
    gs_vision,
)

from app.utils.logging import configure_root_logger, configure_extra_logs

configure_root_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 基本路径
APP_PATH = os.path.abspath(os.path.dirname(__file__))
FILE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "files"))  # 一般文件
TMP_PATH = os.path.abspath(os.path.join(FILE_PATH, "tmp"))  # 临时文件存放地址
STORAGE_PATH = os.path.abspath(os.path.join(APP_PATH, "..", "storage"))  # 储存地址

# Singletons
flask_app = create_flask_app(
    Flask(
        __name__,
        **{
            "static_url_path": "/storage",
            "static_folder": STORAGE_PATH,
        }
        if app_config["STORAGE_TYPE"] == "LOCAL_STORAGE"
        else {},
    )
)
configure_extra_logs(flask_app)
celery = create_celery(flask_app)
init_flask_app(flask_app)


def create_app():
    return flask_app


__all__ = [
    "oss",
    "gs_vision",
    "flask_app",
    "app_config",
    "celery",
    "APP_PATH",
    "STORAGE_PATH",
    "TMP_PATH",
    "FILE_PATH",
]
