"""Task queue — asyncio-based in-process queue, swappable to Azure Service Bus."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class TaskQueue(Protocol):
    async def enqueue(self, task_id: str, payload: dict[str, Any]) -> None: ...
    async def start_worker(self, handler: Callable[[str, dict[str, Any]], Awaitable[None]]) -> None: ...
    async def stop(self) -> None: ...


class InProcessQueue:
    """Asyncio-based in-process task queue."""

    def __init__(self, max_size: int = 100):
        self._queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=max_size)
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

    async def enqueue(self, task_id: str, payload: dict[str, Any]) -> None:
        await self._queue.put((task_id, payload))
        logger.info("task_enqueued", task_id=task_id)

    async def start_worker(
        self, handler: Callable[[str, dict[str, Any]], Awaitable[None]]
    ) -> None:
        self._running = True

        async def _worker() -> None:
            while self._running:
                try:
                    task_id, payload = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                    try:
                        await handler(task_id, payload)
                    except Exception:
                        logger.exception("task_failed", task_id=task_id)
                    finally:
                        self._queue.task_done()
                except asyncio.TimeoutError:
                    continue

        self._worker_task = asyncio.create_task(_worker())

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
