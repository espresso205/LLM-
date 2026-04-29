"""In-memory node registry with async-safe TTL eviction."""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import settings
from shared.utils import get_logger

log = get_logger(__name__)


@dataclass
class NodeInfo:
    node_id: str
    host: str
    port: int
    weight: float = 1.0
    status: str = "healthy"          # healthy | unhealthy | draining
    active_connections: int = 0
    last_heartbeat: float = field(default_factory=time.monotonic)
    registered_at: str = ""
    gpu_util: Optional[float] = None
    memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_temperature: Optional[float] = None
    kv_cache_usage: Optional[float] = None
    avg_token_latency: Optional[float] = None
    num_requests_running: Optional[int] = None
    num_requests_waiting: Optional[int] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: Dict[str, NodeInfo] = {}
        self._lock = asyncio.Lock()

    async def register(self, info: NodeInfo) -> None:
        async with self._lock:
            self._nodes[info.node_id] = info
            log.info(f"Node registered: {info.node_id} @ {info.url}")

    async def deregister(self, node_id: str) -> bool:
        async with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                log.info(f"Node deregistered: {node_id}")
                return True
            return False

    async def heartbeat(self, node_id: str, active_connections: int,
                        status: str, gpu_util=None, memory_used_gb=None,
                        gpu_memory_total_gb=None, gpu_temperature=None,
                        kv_cache_usage=None, avg_token_latency=None,
                        num_requests_running=None, num_requests_waiting=None) -> bool:
        async with self._lock:
            if node := self._nodes.get(node_id):
                node.last_heartbeat = time.monotonic()
                node.active_connections = active_connections
                node.status = status
                if gpu_util is not None:
                    node.gpu_util = gpu_util
                if memory_used_gb is not None:
                    node.memory_used_gb = memory_used_gb
                if gpu_memory_total_gb is not None:
                    node.gpu_memory_total_gb = gpu_memory_total_gb
                if gpu_temperature is not None:
                    node.gpu_temperature = gpu_temperature
                if kv_cache_usage is not None:
                    node.kv_cache_usage = kv_cache_usage
                if avg_token_latency is not None:
                    node.avg_token_latency = avg_token_latency
                if num_requests_running is not None:
                    node.num_requests_running = num_requests_running
                if num_requests_waiting is not None:
                    node.num_requests_waiting = num_requests_waiting
                return True
            return False

    async def all_nodes(self) -> List[NodeInfo]:
        async with self._lock:
            return list(self._nodes.values())

    async def healthy_nodes(self, exclude: List[str] | None = None) -> List[NodeInfo]:
        async with self._lock:
            exclude = exclude or []
            return [
                n for n in self._nodes.values()
                if n.status == "healthy" and n.node_id not in exclude
            ]

    async def get_node(self, node_id: str) -> Optional[NodeInfo]:
        async with self._lock:
            return self._nodes.get(node_id)

    async def evict_stale(self) -> None:
        """Background task: mark nodes unhealthy after heartbeat timeout."""
        while True:
            await asyncio.sleep(5)
            deadline = time.monotonic() - settings.HEARTBEAT_TIMEOUT_S
            async with self._lock:
                for node in self._nodes.values():
                    if node.last_heartbeat < deadline and node.status == "healthy":
                        node.status = "unhealthy"
                        log.warning(f"Node {node.node_id} marked unhealthy (no heartbeat)")


# Module-level singleton
registry = NodeRegistry()
