from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, Optional, Set, Tuple


@dataclass
class FrontierItem:
    url: str
    depth: int


class Frontier:
    def __init__(self) -> None:
        self._queue: Deque[FrontierItem] = deque()
        self._seen: Set[str] = set()

    def add(self, url: str, depth: int) -> None:
        if url in self._seen:
            return
        self._seen.add(url)
        self._queue.append(FrontierItem(url, depth))

    def extend(self, items: Iterable[Tuple[str, int]]) -> None:
        for url, depth in items:
            self.add(url, depth)

    def pop(self) -> Optional[FrontierItem]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def __len__(self) -> int:
        return len(self._queue)
