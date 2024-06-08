from celery import Celery
from flask import Flask
from flask.logging import default_handler as flask_default_handler
import app.config as _app_config
from app.models import connect_db

app_config = {
    k: getattr(_app_config, k) for k in dir(_app_config) if not k.startswith("_")
}


def init_flask_app(app: Flask) -> Flask:
    app.config.from_mapping(app_config)
    connect_db(app.config)
    # print("WTF", app.logger.level)
    # WTF: why is logging so fuking hard in py ecosystem?
    # prevent flask from duplicating logs
    # app.logger.removeHandler(flask_default_handler)
    # app.logger.propagate = False
    return app


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
