"""Strategy registry and hot-swap singleton."""
from .base import SchedulingStrategy
from .round_robin import RoundRobinStrategy
from .least_connections import LeastConnectionsStrategy
from .weighted import WeightedRoundRobinStrategy
from .gpu_aware import GPUAwareStrategy

STRATEGIES: dict[str, type[SchedulingStrategy]] = {
    "round_robin": RoundRobinStrategy,
    "least_connections": LeastConnectionsStrategy,
    "weighted": WeightedRoundRobinStrategy,
    "gpu_aware": GPUAwareStrategy,
}

_active: SchedulingStrategy = RoundRobinStrategy()


def get_strategy() -> SchedulingStrategy:
    return _active


def set_strategy(name: str) -> None:
    global _active
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES)}")
    _active = STRATEGIES[name]()
