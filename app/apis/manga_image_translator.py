# Translation preprocess API backed by manga-image-translator worker
from app.core.views import MoeAPIView
from flask import request

from app.exceptions.base import UploadFileNotFoundError
from app.tasks.mit import preprocess_mit, mit_ocr, mit_detect_text, mit_translate
from app.tasks import queue_task, wait_result_sync
from app import app_config
from werkzeug.datastructures import FileStorage
from tempfile import NamedTemporaryFile
import os

MIT_STORAGE_ROOT = app_config.get("MIT_STORAGE_ROOT", "/MIT_STORAGE_ROOT_UNDEFINED")


def _wait_task_result(task_id: str):
    try:
        result = wait_result_sync(task_id, timeout=1)
        return {"id": task_id, "status": "success", "result": result}
    except TimeoutError:
        return {
            "id": task_id,
            "status": "pending",
        }
    except Exception as e:
        return {"id": task_id, "status": "fail", "message": str(e)}


class MitImageApi(MoeAPIView):
    # upload image file for other APIs
    def post(self):
        blob: None | FileStorage = request.files.get("file", None)
        if not (blob and blob.name.endswith((".jpg", ".jpeg", ".png", ".gif"))):
            raise UploadFileNotFoundError("Please select an image file")
        tmpfile = NamedTemporaryFile(dir=MIT_STORAGE_ROOT, delete=False)
        tmpfile.write(blob.read())
        tmpfile.close()
        return {"filename": tmpfile.name}


class MitImageTaskApi(MoeAPIView):
    _MIT_IMAGE_TASKS = {
        'mit_detect_text': mit_detect_text,
        'mit_ocr': mit_ocr,
    }

    def post(self):
        task_params = self.get_json()
        task_name = task_params.get("task_name", None)
        if task_name not in self._MIT_IMAGE_TASKS:
            raise ValueError("Invalid task name")
        if 'filename' not in task_params:
            raise ValueError("Filename required")
        tmpfile_name = task_params['filename']
        tmpfile_path = os.path.join(MIT_STORAGE_ROOT, tmpfile_name)
        if os.path.commonprefix([tmpfile_path, MIT_STORAGE_ROOT]) != MIT_STORAGE_ROOT:
            raise ValueError("Invalid filename")
        if not os.path.isfile(tmpfile_path):
            raise ValueError("File not found")
        task_id = queue_task(self._MIT_IMAGE_TASKS[task_name], tmpfile_path, **task_params)
        return {"id": task_id}

    def get(self, task_id: str):
        return _wait_task_result(task_id)


class MitTranslateTaskApi(MoeAPIView):
    def post(self):
        task_params = self.get_json()
        text: str = task_params.get('text')
        target_lang = task_params.get('target_lang', 'CHT')
        task_id = queue_task(mit_translate, text, target_lang)
        return {'task_id': task_id}

    def get(self, task_id: str):
        return _wait_task_result(task_id)
