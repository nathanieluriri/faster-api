import os

from celery import Celery
from dotenv import load_dotenv

from core.queue.tasks import execute_registered_task
from core import task as _task_registration  # noqa: F401

load_dotenv()

broker_url = os.getenv("CELERY_BROKER_URL")
backend_url = os.getenv("CELERY_RESULT_BACKEND")

celery_app = Celery("worker", broker=broker_url, backend=backend_url)
celery_app.conf.update(task_track_started=True)


@celery_app.task(name="celery_worker.test_scheduler")
async def test_scheduler(message: str) -> str:
    return message


@celery_app.task(name="celery_worker.run_async_task")
async def run_async_task(task_key: str, kwargs: dict):
    return await execute_registered_task(task_key=task_key, payload=kwargs)
