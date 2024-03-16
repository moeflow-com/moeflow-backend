"""
Text segmentation + OCR using manga-image-translator
"""

from app import celery as celery_app


@celery_app.task(name="tasks.mit_detection")
def mit_detection(path_or_url: str, **kwargs):
    pass  # Real implementation is in manga_translator/moeflow_worker.py
