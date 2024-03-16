"""
Text segmentation + OCR using manga-image-translator
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Optional
from app import celery as celery_app
from app.tasks import queue_task, wait_result
from celery import Task, chain
from celery.result import AsyncResult
from app.utils.logging import logger


@celery_app.task(name="tasks.mit.detect_text")
def _mit_detect_text(path_or_url: str, **kwargs):
    pass  # Real implementation is in manga_translator/moeflow_worker.py


@celery_app.task(name="tasks.mit.ocr")
def _mit_ocr(path_or_url: str, **kwargs):
    pass


@celery_app.task(name="tasks.mit.translate")
def _mit_translate(**kwargs):
    pass


@celery_app.task(name="tasks.mit.inpaint")
def _mit_inpaint(path_or_url: str, **kwargs):
    pass


def _run_mit_detect_text(image_path: str) -> dict:
    detect_text: AsyncResult = mit_detect_text.delay(
        image_path,
        detector_key="default",
        # mostly defaults from manga-image-translator/args.py
        detect_size=2560,
        text_threshold=0.5,
        box_threshold=0.7,
        unclip_ratio=2.3,
        invert=False,
        gamma_correct=False,
        rotate=False,
        verbose=True,
    )
    # XXX unrecommended but should not cause dead lock
    result: dict = detect_text.get(disable_sync_subtasks=False)  # type: ignore
    logger.info("detect_text finished: %s", result)
    return result


def _run_mit_ocr(image_path: str, regions: list[dict]) -> list[dict]:
    ocr: AsyncResult = mit_ocr.delay(
        image_path,
        # ocr_key="48px", # recommended by rowland
        # ocr_key="48px_ctc",
        ocr_key="mocr",  # just use this with use_mocr_merge
        use_mocr_merge=True,
        regions=regions,
        verbose=True,
    )
    # XXX unrecommended but should not cause dead lock
    ocred: list[dict] = ocr.get(disable_sync_subtasks=False)
    logger.info("ocr finished: %s", ocred)
    for t in ocred:
        logger.info("ocr extracted text: %s", t)
    return ocred


def _run_mit_translate(
    text: str,
    translator: str = "gpt3.5",
    target_lang: str = "CHT",
) -> str:
    t: AsyncResult = mit_translate.delay(
        query=text,
        translator=translator,
        target_lang=target_lang,
    )
    # XXX unrecommended but should not cause dead lock

    result: str = t.get(disable_sync_subtasks=False)
    logger.info("translated %s %s", text, result)
    return result


@celery_app.task(name="tasks.preprocess_mit")
def _preprocess_mit(image_path: str, target_lang: str):
    detected = _run_mit_detect_text(image_path)
    ocred = _run_mit_ocr(image_path, detected["textlines"])
    translated_texts = [
        _run_mit_translate(t["text"], target_lang=target_lang) for t in ocred
    ]
    quads = [
        MitTextQuad(
            pts=t["pts"],
            raw_text=t["text"],
            translated=translated_texts[i],
        )
        for i, t in enumerate(ocred)
    ]
    return MitPreprocessedImage(
        image_path=image_path,
        target_lang=target_lang,
        text_quads=quads,
    )


@dataclass(frozen=True)
class MitTextQuad:
    pts: list[tuple[int, int]]
    raw_text: str
    translated: str


@dataclass(frozen=True)
class MitPreprocessedImage:
    image_path: str
    target_lang: str
    text_quads: list[MitTextQuad]


# export tasks with a better type
mit_detect_text: Task = _mit_detect_text  # type: ignore
mit_ocr: Task = _mit_ocr  # type: ignore
mit_translate: Task = _mit_translate  # type: ignore
mit_inpaint: Task = _mit_inpaint  # type: ignore
preprocess_mit: Task = _preprocess_mit  # type: ignore
