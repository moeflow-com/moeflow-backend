"""
Text segmentation + OCR using manga-image-translator
"""

from ...app import celery


@celery.task(name="tasks.mit_text_segmentation")
def mit_text_extraction(input: dict[str, any]):
    pass
