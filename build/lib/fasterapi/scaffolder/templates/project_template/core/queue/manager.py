from __future__ import annotations

from threading import Lock
from typing import Any

from core.queue.provider import QueueProvider
from core.queue.types import QueueJobResult, QueueTaskKey


class QueueManager:
    _instance: "QueueManager | None" = None
    _lock = Lock()

    def __init__(self, provider: QueueProvider) -> None:
        self._provider = provider

    @classmethod
    def configure(cls, provider: QueueProvider) -> "QueueManager":
        with cls._lock:
            cls._instance = cls(provider=provider)
            return cls._instance

    @classmethod
    def get_instance(cls) -> "QueueManager":
        if cls._instance is None:
            raise RuntimeError("QueueManager is not configured")
        return cls._instance

    def enqueue(self, task_key: str, payload: dict[str, Any]) -> QueueJobResult:
        return self._provider.enqueue(QueueTaskKey(task_key), payload)

    def enqueue_in(self, seconds: int, task_key: str, payload: dict[str, Any]) -> QueueJobResult:
        return self._provider.enqueue_in(seconds=seconds, task_key=QueueTaskKey(task_key), payload=payload)

    def get_status(self, task_id: str) -> str:
        return self._provider.get_status(task_id)

    def revoke(self, task_id: str) -> None:
        self._provider.revoke(task_id)
