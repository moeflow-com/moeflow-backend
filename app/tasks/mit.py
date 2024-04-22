"""
Text segmentation + OCR using manga-image-translator
"""

from dataclasses import dataclass
from typing import Any
from app import celery as celery_app
from celery import Task
from celery.result import AsyncResult
import logging

logger = logging.getLogger(__name__)


gpu_options = {"device": "cuda"}


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
        **gpu_options,
    )
    # XXX unrecommended but should not cause dead lock
    result: dict = detect_text.get(disable_sync_subtasks=False)  # type: ignore
    logger.info("detect_text finished: %s", result)
    return result


def _run_mit_ocr(image_path: str, regions: list[dict]) -> list[dict]:
    ocr: AsyncResult = mit_ocr.delay(
        image_path,
        ocr_key="48px",  # recommended by rowland
        # ocr_key="48px_ctc",
        # ocr_key="mocr",  # XXX: mocr may have different output format
        # use_mocr_merge=True,
        regions=regions,
        verbose=True,
        **gpu_options,
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
    return result[0]


@celery_app.task(name="tasks.preprocess_mit")
def _preprocess_mit(image_path: str, target_lang: str):
    detected = _run_mit_detect_text(image_path)
    ocred = _run_mit_ocr(image_path, detected["textlines"])
    translated_texts = [
        _run_mit_translate(t["text"], target_lang=target_lang) for t in ocred
    ]
    quads = [
        {
            "pts": t["pts"],
            "raw_text": t["text"],
            "translated": translated_texts[i],
        }
        for i, t in enumerate(ocred)
    ]
    return {
        "image_path": image_path,
        "target_lang": target_lang,
        "text_quads": quads,
    }


@dataclass(frozen=True)
class MitTextQuad:
    pts: list[tuple[int, int]]
    raw_text: str
    translated: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pts": self.pts,
            "raw_text": self.raw_text,
            "translated": self.translated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MitTextQuad":
        return cls(
            pts=d["pts"],
            raw_text=d["raw_text"],
            translated=d["translated"],
        )


@dataclass(frozen=True)
class MitPreprocessedImage:
    image_path: str
    target_lang: str
    text_quads: list[MitTextQuad]

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "target_lang": self.target_lang,
            "text_quads": [t.to_dict() for t in self.text_quads],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MitPreprocessedImage":
        return cls(
            image_path=d["image_path"],
            target_lang=d["target_lang"],
            text_quads=[MitTextQuad.from_dict(t) for t in d["text_quads"]],
        )


# export tasks with a better type
mit_detect_text: Task = _mit_detect_text  # type: ignore
mit_ocr: Task = _mit_ocr  # type: ignore
mit_translate: Task = _mit_translate  # type: ignore
mit_inpaint: Task = _mit_inpaint  # type: ignore
preprocess_mit: Task = _preprocess_mit  # type: ignore
