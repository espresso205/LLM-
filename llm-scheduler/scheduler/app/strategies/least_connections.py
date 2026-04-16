from typing import List
from .base import SchedulingStrategy
from ..registry import NodeInfo


class LeastConnectionsStrategy(SchedulingStrategy):
    name = "least_connections"

    async def pick(self, nodes: List[NodeInfo]) -> NodeInfo:
        if not nodes:
            raise RuntimeError("No healthy nodes available")
        return min(nodes, key=lambda n: n.active_connections)
