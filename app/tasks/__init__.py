"""
Celery 通过以下语句启动(在项目根目录)：

# STEP 1：设置环境变量 并 启动CELERY
export CONFIG_PATH="../configs/dev.py" && celery -A app.celery worker --loglevel=info
# STEP 2:开启监控程序
flower --port=5555 --broker=redis://localhost:6379/1
"""

import asyncio
import datetime
from typing import Any
from celery import Task
from celery.result import AsyncResult
from celery.exceptions import TimeoutError as CeleryTimeoutError
from app import celery as celery_app
from asgiref.sync import async_to_sync


_FORCE_SYNC_TASK: bool = celery_app.conf["app_config"].get("TESTING", False)


class SyncResult:
    """和celery的delay异步返回类似的结果，用于同步、异步切换"""

    task_id = "sync"


def queue_task(task: Task, *args, **kwargs) -> str:
    result = task.delay(*args, **kwargs)
    result.forget()
    return result.id


def wait_result_sync(task_id: str, timeout: int = 10) -> Any:
    result = AsyncResult(id=task_id, app=celery_app)
    try:
        return result.get(timeout=timeout)
    except CeleryTimeoutError:
        raise TimeoutError


@async_to_sync
async def wait_result(task_id: str, timeout: int = 10) -> Any:
    start = datetime.datetime.now().timestamp()
    result = AsyncResult(id=task_id, app=celery_app)
    while not result.ready():
        if (datetime.datetime.now().timestamp() - start) > timeout:
            result.forget()
            raise TimeoutError
        await asyncio.sleep(0.5e3)
    return result.get()  # type: ignore
