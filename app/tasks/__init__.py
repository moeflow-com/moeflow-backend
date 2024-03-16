"""
Celery 通过以下语句启动(在项目根目录)：

# STEP 1：设置环境变量 并 启动CELERY
export CONFIG_PATH="../configs/dev.py" && celery -A app.celery worker --loglevel=info
# STEP 2:开启监控程序
flower --port=5555 --broker=redis://localhost:6379/1
"""


import asyncio
import datetime
from typing import Any, Awaitable
from celery import Task
from celery.result import AsyncResult
from app import celery as celery_app


class SyncResult:
    """和celery的delay异步返回类似的结果，用于同步、异步切换"""

    task_id = "sync"


def queue_task(task: Task, *args, **kwargs) -> str:
    result = task.delay(*args, **kwargs)
    result.forget()
    return result.id


async def wait_result(task_id: str, timeout: int = 10) -> Awaitable[Any]:
    start = datetime.datetime.now().timestamp()
    result = AsyncResult(id=task_id, app=celery_app)
    while not result.ready():
        if (datetime.datetime.now().timestamp() - start) > timeout:
            result.forget()
            return None  # type: ignore
        await asyncio.sleep(0.5e3)
    return result.get()  # type: ignore
