"""GPU-Aware scheduling strategy — scores nodes by KV Cache availability and queue depth.

Design rationale:
  GPU utilization is unsuitable for LLM scheduling because even a single inference
  request saturates GPU compute during the prefill phase.  Temperature is irrelevant
  to scheduling decisions.  The real capacity indicators for LLM serving are:

  1. KV Cache usage — determines how many more sequences the node can accept.
     When KV Cache is full, new requests must wait for existing sequences to finish.
  2. Queue depth (running + waiting) — directly predicts expected wait time.

  References:
    - Jaillet et al., "Online Scheduling for LLM Inference with KV Cache
      Constraints", arXiv:2502.07115, 2025.
    - LLM-d, "Predicted-Latency Based Scheduling for LLMs", 2025.
    - BentoML, "KV Cache Utilization-Aware Load Balancing", 2025.
"""
from typing import List, Tuple
from .base import SchedulingStrategy
from ..registry import NodeInfo

_DEFAULT_SCORE = 0.3


class GPUAwareStrategy(SchedulingStrategy):
    name = "gpu_aware"

    # Weight coefficients
    ALPHA = 0.6  # KV Cache available capacity
    BETA = 0.4   # Queue depth (inverse)

    # Hard threshold — KV Cache > 95% means node cannot accept new sequences
    KV_CACHE_THRESHOLD = 0.95

    async def pick(self, nodes: List[NodeInfo]) -> NodeInfo:
        if not nodes:
            raise RuntimeError("No healthy nodes available")

        scored: List[Tuple[NodeInfo, float]] = []

        for node in nodes:
            score = self._score(node)
            if score is not None:
                scored.append((node, score))

        if not scored:
            # All nodes failed hard thresholds — fallback: pick least connections
            return min(nodes, key=lambda n: n.active_connections)

        # Sort descending by score, tie-break by least connections
        scored.sort(key=lambda x: (-x[1], x[0].active_connections))
        return scored[0][0]

    def _score(self, node: NodeInfo) -> float | None:
        """Return health score [0, 1] or None if node fails hard threshold."""

        kv = node.kv_cache_usage  # 0-100 from vLLM
        running = node.num_requests_running or 0
        waiting = node.num_requests_waiting or 0

        # No vLLM telemetry available — give low default score (not excluded)
        if kv is None:
            return _DEFAULT_SCORE

        # Hard threshold: KV Cache near full → cannot accept new sequences
        kv_rate = kv / 100.0  # normalize to [0, 1]
        if kv_rate > self.KV_CACHE_THRESHOLD:
            return None  # excluded

        # KV Cache available capacity factor (higher = more room)
        kv_factor = 1.0 - kv_rate

        # Queue depth factor: inverse relationship — fewer queued = better
        queue_depth = running + waiting
        queue_factor = 1.0 / (1.0 + queue_depth)

        score = self.ALPHA * kv_factor + self.BETA * queue_factor
        return max(0.0, min(1.0, score))
