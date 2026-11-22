"""Bounded process-local cache for the HTTP request handlers."""

from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar


Key = TypeVar("Key")
Value = TypeVar("Value")


class TTLCache(Generic[Key, Value]):
    def __init__(self, max_entries: int, ttl: float, *, clock: Callable[[], float] = monotonic):
        self._entries: OrderedDict[Key, tuple[float, Value]] = OrderedDict()
        self._max_entries = max_entries
        self._ttl = ttl
        self._clock = clock
        self._lock = Lock()

    def get(self, key: Key) -> Value | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            deadline, value = entry
            if deadline <= self._clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def put(self, key: Key, value: Value) -> None:
        with self._lock:
            self._entries[key] = (self._clock() + self._ttl, value)
            self._entries.move_to_end(key)
            if len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
