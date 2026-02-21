from __future__ import annotations

from typing import Any, Protocol

from core.queue.types import QueueJobResult, QueueTaskKey


class QueueProvider(Protocol):
    backend_name: str

    def enqueue(self, task_key: QueueTaskKey, payload: dict[str, Any]) -> QueueJobResult:
        ...

    def enqueue_in(self, seconds: int, task_key: QueueTaskKey, payload: dict[str, Any]) -> QueueJobResult:
        ...

    def get_status(self, task_id: str) -> str:
        ...

    def revoke(self, task_id: str) -> None:
        ...
