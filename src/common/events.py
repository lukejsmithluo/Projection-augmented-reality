from __future__ import annotations

import asyncio
from typing import AsyncIterator

from pydantic import BaseModel


class Event(BaseModel):
    """事件基础模型"""

    type: str
    payload: dict = {}


class EventBus:
    """简单事件总线（进程内）"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    async def publish(self, event: Event) -> None:
        """发布事件"""
        await self._queue.put(event)

    async def subscribe(self) -> AsyncIterator[Event]:
        """订阅事件（异步迭代）"""
        while True:
            evt = await self._queue.get()
            yield evt
