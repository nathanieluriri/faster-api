from __future__ import annotations

from typing import Any

from core.queue.provider import QueueProvider
from core.queue.types import QueueJobResult, QueueTaskKey


class CeleryQueueProvider(QueueProvider):
    backend_name = "celery"

    def __init__(self, celery_app: Any) -> None:
        self._celery_app = celery_app

    def enqueue(self, task_key: QueueTaskKey, payload: dict[str, Any]) -> QueueJobResult:
        result = self._celery_app.send_task(
            "celery_worker.run_async_task",
            args=[str(task_key), payload],
        )
        return QueueJobResult(task_id=result.id, backend=self.backend_name, status="queued")

    def enqueue_in(self, seconds: int, task_key: QueueTaskKey, payload: dict[str, Any]) -> QueueJobResult:
        result = self._celery_app.send_task(
            "celery_worker.run_async_task",
            args=[str(task_key), payload],
            countdown=max(seconds, 0),
        )
        return QueueJobResult(task_id=result.id, backend=self.backend_name, status="scheduled")

    def get_status(self, task_id: str) -> str:
        return self._celery_app.AsyncResult(task_id).status

    def revoke(self, task_id: str) -> None:
        self._celery_app.control.revoke(task_id)
