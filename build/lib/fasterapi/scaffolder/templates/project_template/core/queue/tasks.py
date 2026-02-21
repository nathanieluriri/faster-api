from __future__ import annotations

from typing import Any, Awaitable, Callable

TaskFunc = Callable[..., Awaitable[Any]]
_TASK_REGISTRY: dict[str, TaskFunc] = {}


def register_task(task_key: str, func: TaskFunc) -> None:
    if task_key in _TASK_REGISTRY:
        raise ValueError(f"Task key '{task_key}' is already registered")
    _TASK_REGISTRY[task_key] = func


def task(task_key: str) -> Callable[[TaskFunc], TaskFunc]:
    def decorator(func: TaskFunc) -> TaskFunc:
        register_task(task_key, func)
        return func

    return decorator


async def execute_registered_task(task_key: str, payload: dict[str, Any]) -> Any:
    target = _TASK_REGISTRY.get(task_key)
    if target is None:
        valid_keys = ", ".join(sorted(_TASK_REGISTRY)) or "<none>"
        raise ValueError(f"Task key '{task_key}' is not registered. Available keys: {valid_keys}")
    return await target(**payload)


def list_registered_task_keys() -> list[str]:
    return sorted(_TASK_REGISTRY.keys())
