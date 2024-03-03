"""
导出项目
"""
from app.constants.project import (
    ImportFromLabelplusErrorType,
    ImportFromLabelplusStatus,
)
from flask import Flask

from app import celery

from app.models import connect_db
from . import SyncResult
from celery.utils.log import get_task_logger
from app.utils.labelplus import load_from_labelplus
from app.constants.source import SourcePositionType
from celery.result import AsyncResult

logger = get_task_logger(__name__)


@celery.task(name="tasks.import_from_labelplus_task")
def import_from_labelplus_task(project_id):
    """
    压缩整个项目

    :param project_id: 项目ID
    :return:
    """
    from app.models.project import Project
    from app.models.team import Team

    (Project, Team)
    connect_db(celery.conf.app_config)
    app = Flask(__name__)
    app.config.from_object(celery.conf.app_config)

    project: Project = Project.objects(id=project_id).first()
    if project is None:
        return f"从 Labelplus 导入失败：项目不存在，Project {project_id}"
    target = project.targets().first()
    creator = project.users(role=project.role_cls.by_system_code("creator")).first()
    if target is None:
        project.update(
            import_from_labelplus_txt="",
            import_from_labelplus_status=ImportFromLabelplusStatus.ERROR,
            import_from_labelplus_error_type=ImportFromLabelplusErrorType.NO_TARGET,
        )
        return f"失败：目标语言不存在，Project {project_id}"
    if creator is None:
        project.update(
            import_from_labelplus_txt="",
            import_from_labelplus_status=ImportFromLabelplusStatus.ERROR,
            import_from_labelplus_error_type=ImportFromLabelplusErrorType.NO_CREATOR,
        )
        return f"失败：创建者不存在，Project {project_id}"
    try:
        with app.app_context():
            if target and creator:
                project.update(
                    import_from_labelplus_percent=0,
                    import_from_labelplus_status=ImportFromLabelplusStatus.RUNNING,
                )
                labelplus_data = load_from_labelplus(project.import_from_labelplus_txt)
                file_count = len(labelplus_data)
                for file_index, labelplus_file in enumerate(labelplus_data):
                    file = project.create_file(labelplus_file["file_name"])
                    for labelplus_label in labelplus_file["labels"]:
                        source = file.create_source(
                            content="",
                            x=labelplus_label["x"],
                            y=labelplus_label["y"],
                            position_type=SourcePositionType.IN
                            if labelplus_label["position_type"] == SourcePositionType.IN
                            else SourcePositionType.OUT,
                        )
                        source.create_translation(
                            content=labelplus_label["translation"],
                            target=target,
                            user=creator,
                        )
                    project.update(
                        import_from_labelplus_percent=int(
                            (file_index / file_count) * 100
                        )
                    )
    except Exception:
        logger.exception(Exception)
        project.update(
            import_from_labelplus_txt="",
            import_from_labelplus_status=ImportFromLabelplusStatus.ERROR,
            import_from_labelplus_error_type=ImportFromLabelplusErrorType.PARSE_FAILED,
        )
        return f"失败：解析/创建时发生错误，详见 log，Project {project_id}"
    project.update(
        import_from_labelplus_txt="",
        import_from_labelplus_percent=0,
        import_from_labelplus_status=ImportFromLabelplusStatus.SUCCEEDED,
    )
    return f"成功：Project {project_id}"


def import_from_labelplus(project_id, /, *, run_sync=False) -> SyncResult | AsyncResult:
    alive_workers = celery.control.ping()
    if len(alive_workers) == 0 or run_sync:
        # 同步执行
        import_from_labelplus_task(project_id)
        return SyncResult()
    else:
        # 异步执行
        return import_from_labelplus_task.delay(project_id)
