import os
from celery import Celery
from dotenv import load_dotenv
import asyncio
import celery_aio_pool as aio_pool
load_dotenv()

broker_url = os.getenv("CELERY_BROKER_URL")
backend_url = os.getenv("CELERY_RESULT_BACKEND")

celery_app = Celery("worker", broker=broker_url, backend=backend_url,)
celery_app.conf.update(task_track_started=True)

@celery_app.task(name="celery_worker.test_scheduler")
async def test_scheduler(message):
    print(message)
    