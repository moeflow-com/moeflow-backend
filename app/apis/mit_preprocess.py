# Translation preprocess API backed by manga-image-translator worker
from app.core.views import MoeAPIView
from flask import current_app, request

from app.exceptions.base import UploadFileNotFoundError, FileTypeNotSupportError
from app.utils.logging import logger
from app.tasks.mit import preprocess_mit
from app.tasks import queue_task, wait_result_sync
from werkzeug.datastructures import FileStorage
from tempfile import NamedTemporaryFile
import os


tmpfile_prefix = "/var/lib/moeflow-storage/mit-temp"


class MitPreprocessTaskApi(MoeAPIView):
    def post(self):
        blob: FileStorage = request.files.get("file")
        if not blob:
            raise UploadFileNotFoundError("请选择图片")
        tmpfile = NamedTemporaryFile(dir=tmpfile_prefix, delete=False)
        tmpfile.write(blob.read())
        tmpfile.close()
        tmpfile_path = os.path.join(tmpfile_prefix, tmpfile.name)
        task_id = queue_task(preprocess_mit, tmpfile_path, 'CHT')
        return {
            'id': task_id
        }

    def get(self, task_id: str):
        try:
            result = wait_result_sync(task_id, timeout=1)
            return {
                'id': task_id,
                'status': 'success',
                'result': result
            }
        except TimeoutError:
            return {
                'id': task_id,
                'status': 'pending',
            }
        except:
            return {
                'id': task_id,
                'status': 'fail',
            }
