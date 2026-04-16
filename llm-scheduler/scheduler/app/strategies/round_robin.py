import itertools
from typing import List
from .base import SchedulingStrategy
from ..registry import NodeInfo


class RoundRobinStrategy(SchedulingStrategy):
    name = "round_robin"

    def __init__(self) -> None:
        self._counter = itertools.count()

    async def pick(self, nodes: List[NodeInfo]) -> NodeInfo:
        if not nodes:
            raise RuntimeError("No healthy nodes available")
        return nodes[next(self._counter) % len(nodes)]
