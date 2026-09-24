import os

from celery import Celery
from dotenv import load_dotenv

from core.queue.tasks import execute_registered_task
from core.settings import get_settings
from core import task as _task_registration  # noqa: F401

load_dotenv()

broker_url = os.getenv("CELERY_BROKER_URL") or get_settings().redis_url
backend_url = os.getenv("CELERY_RESULT_BACKEND") or broker_url

celery_app = Celery("worker", broker=broker_url, backend=backend_url)
celery_app.conf.update(
    task_track_started=True,
    # Fail fast when the broker is down so API requests that enqueue work don't hang for ~20s.
    task_publish_retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 0.5, "interval_max": 1},
)


@celery_app.task(name="celery_worker.test_scheduler")
async def test_scheduler(message: str) -> str:
    return message


@celery_app.task(name="celery_worker.run_async_task")
async def run_async_task(task_key: str, kwargs: dict):
    return await execute_registered_task(task_key=task_key, payload=kwargs)
