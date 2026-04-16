"""Async-safe active connection counter for the inference node."""
import asyncio


class _Counter:
    def __init__(self) -> None:
        self._value = 0
        self._lock = asyncio.Lock()

    @property
    def value(self) -> int:
        return self._value

    async def increment(self) -> None:
        async with self._lock:
            self._value += 1

    async def decrement(self) -> None:
        async with self._lock:
            self._value = max(0, self._value - 1)


connection_counter = _Counter()
