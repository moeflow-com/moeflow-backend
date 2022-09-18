"""
Celery 通过以下语句启动(在项目根目录)：

# STEP 1：设置环境变量 并 启动CELERY
export CONFIG_PATH="../configs/dev.py" && celery -A app.celery worker --loglevel=info
# STEP 2:开启监控程序
flower --port=5555 --broker=redis://localhost:6379/1
"""


class SyncResult:
    """和celery的delay异步返回类似的结果，用于同步、异步切换"""

    task_id = "sync"
