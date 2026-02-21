from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NewType


QueueTaskKey = NewType("QueueTaskKey", str)


@dataclass(frozen=True)
class QueueJobResult:
    task_id: str
    backend: str
    status: str
    metadata: dict[str, Any] | None = None
