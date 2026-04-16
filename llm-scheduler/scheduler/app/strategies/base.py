"""Abstract base class for scheduling strategies."""
from abc import ABC, abstractmethod
from typing import List
from ..registry import NodeInfo


class SchedulingStrategy(ABC):
    name: str = "base"

    @abstractmethod
    async def pick(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Select one node from the healthy candidate list."""
        ...
