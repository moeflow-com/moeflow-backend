# Translation preprocess API backed by manga-image-translator worker
from app.core.views import MoeAPIView
from flask import request

from app.exceptions.base import UploadFileNotFoundError
from app.tasks.mit import (
    mit_ocr,
    mit_detect_text,
    mit_translate,
    mit_detect_text_default_params,
    mit_ocr_default_params,
)
from app.tasks import queue_task, wait_result_sync
from app import app_config
from werkzeug.datastructures import FileStorage
from tempfile import NamedTemporaryFile
import os
from app.utils.logging import logger

MIT_STORAGE_ROOT = app_config.get("MIT_STORAGE_ROOT", "/MIT_STORAGE_ROOT_UNDEFINED")


def _wait_task_result(task_id: str):
    try:
        result = wait_result_sync(task_id, timeout=1)
        return {"task_id": task_id, "status": "success", "result": result}
    except TimeoutError:
        return {
            "task_id": task_id,
            "status": "pending",
        }
    except Exception as e:
        return {"task_id": task_id, "status": "fail", "message": str(e)}


class MitImageApi(MoeAPIView):
    # upload image file for other APIs
    def post(self):
        logger.info("files: %s", request.files)
        blob: None | FileStorage = request.files.get("file")
        logger.info("blob: %s", blob)
        if not (blob and blob.filename.endswith((".jpg", ".jpeg", ".png", ".gif"))):
            raise UploadFileNotFoundError("Please select an image file")
        tmpfile = NamedTemporaryFile(dir=MIT_STORAGE_ROOT, delete=False)
        tmpfile.write(blob.read())
        tmpfile.close()
        return {"filename": tmpfile.name}


class MitImageTaskApi(MoeAPIView):
    def post(self):
        task_params: dict[str, str] = self.get_json()
        logger.info("task_params: %s", task_params)
        tmpfile_name = task_params.pop("filename", None)
        if not tmpfile_name:
            raise ValueError("Filename required")
        tmpfile_path = os.path.join(MIT_STORAGE_ROOT, tmpfile_name)
        if os.path.commonprefix([tmpfile_path, MIT_STORAGE_ROOT]) != MIT_STORAGE_ROOT:
            raise ValueError("Invalid filename")
        if not os.path.isfile(tmpfile_path):
            raise ValueError("File not found")
        task_name = task_params.pop("task_name", None)
        if task_name == "mit_detect_text":
            merged_params = mit_detect_text_default_params.copy()
            merged_params.update(task_params)
            task_id = queue_task(mit_detect_text, tmpfile_path, **merged_params)
            return {"task_id": task_id}
        elif task_name == "mit_ocr":
            merged_params = mit_ocr_default_params.copy()
            merged_params.update(task_params)
            task_id = queue_task(mit_ocr, tmpfile_path, **merged_params)
            return {"task_id": task_id}
        else:
            raise ValueError("Invalid task name")

    def get(self, task_id: str):
        return _wait_task_result(task_id)


class MitTranslateTaskApi(MoeAPIView):
    def post(self):
        task_params = self.get_json()
        task_id = queue_task(mit_translate, **task_params)
        return {"task_id": task_id}

    def get(self, task_id: str):
        return _wait_task_result(task_id)
