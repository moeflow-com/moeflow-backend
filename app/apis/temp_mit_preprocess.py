# Translation preprocess API
from app.core.views import MoeAPIView
from flask import Request

from app.utils.logging import logger


class TempMitPreprocessApi(MoeAPIView):
    def post(self: Request):
        logger.debug('TempMitPreprocessApi POST', self)

    def get(self: Request):
        job_id = self.args.get('job_id', None)
        logger.debug('TempMitPreprocessApi GET', self, job_id)
