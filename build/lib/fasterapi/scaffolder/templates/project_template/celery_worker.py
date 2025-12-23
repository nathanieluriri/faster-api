import os
from celery import Celery
from dotenv import load_dotenv
import asyncio
import importlib
import celery_aio_pool as aio_pool

from core.task import ASYNC_TASK_REGISTRY


load_dotenv()

broker_url = os.getenv("CELERY_BROKER_URL")
backend_url = os.getenv("CELERY_RESULT_BACKEND")

celery_app = Celery("worker", broker=broker_url, backend=backend_url,)
celery_app.conf.update(task_track_started=True)

@celery_app.task(name="celery_worker.test_scheduler")
async def test_scheduler(message):
    print(message)
    

@celery_app.task(name="celery_worker.run_async_task")
async def run_async_task(task_key: str, kwargs: dict):
    """
    task_key example: 'delete_tokeens'
    kwargs example: {'filter_dict': {'_id': '...'}}
    """
    
    # 3. Lookup the function object from the registry
    target_func = ASYNC_TASK_REGISTRY.get(task_key)

    if not target_func:
        valid_keys = ", ".join(ASYNC_TASK_REGISTRY.keys())
        raise ValueError(f"Task key '{task_key}' is not registered. Available keys: {valid_keys}")

    # 4. Execute the function
    # Since the function object is already imported, we just call it.
    return await target_func(**kwargs)