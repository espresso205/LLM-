import random
from typing import List
from .base import SchedulingStrategy
from ..registry import NodeInfo


class WeightedRoundRobinStrategy(SchedulingStrategy):
    name = "weighted"

    async def pick(self, nodes: List[NodeInfo]) -> NodeInfo:
        if not nodes:
            raise RuntimeError("No healthy nodes available")
        weights = [max(n.weight, 0.001) for n in nodes]
        return random.choices(nodes, weights=weights, k=1)[0]
