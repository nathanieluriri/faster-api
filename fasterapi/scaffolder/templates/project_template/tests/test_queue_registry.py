import asyncio

from core.queue.tasks import execute_registered_task, register_task

def test_queue_registry_executes_task():
    async def _sample_task(value: int) -> int:
        return value + 1

    register_task("test_queue_registry_executes_task", _sample_task)
    result = asyncio.run(
        execute_registered_task(
            task_key="test_queue_registry_executes_task",
            payload={"value": 2},
        )
    )
    assert result == 3
