"""Shared Prometheus metrics for all llm-scheduler services.

Each service imports the collectors it needs and exposes them via /metrics.
Labels are added per-service at instrumentation time.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response


# ---- Inference ----
INFERENCE_REQUESTS = Counter(
    "llm_inference_requests_total",
    "Total inference requests processed",
    ["service", "model", "status"],
)

INFERENCE_TOKENS = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["service", "type"],
)

INFERENCE_LATENCY = Histogram(
    "llm_inference_latency_seconds",
    "End-to-end inference latency in seconds",
    ["service", "model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 180.0),
)


# ---- Scheduling ----
SCHEDULE_DECISIONS = Counter(
    "llm_schedule_decisions_total",
    "Total scheduling decisions",
    ["algorithm", "node_id"],
)

SCHEDULE_LATENCY = Histogram(
    "llm_schedule_decision_seconds",
    "Scheduling decision latency in seconds",
    ["algorithm"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)


# ---- Node health ----
NODE_ACTIVE_CONNECTIONS = Gauge(
    "llm_node_active_connections",
    "Active connections on node",
    ["node_id"],
)

NODE_STATUS = Gauge(
    "llm_node_status",
    "Node status (1=healthy, 0=unhealthy)",
    ["node_id"],
)


# ---- LTR Queue ----
LTR_QUEUE_SIZE = Gauge(
    "llm_ltr_queue_size",
    "Current number of requests waiting in the LTR priority queue",
)

LTR_QUEUE_WAIT_SECONDS = Histogram(
    "llm_ltr_queue_wait_seconds",
    "Time requests spend waiting in the LTR queue before dispatch",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

LTR_STARVATION_BOOSTS = Counter(
    "llm_ltr_starvation_boosts_total",
    "Number of times starvation prevention boosted a request's priority",
)


def metrics_response() -> Response:
    """Generate a Starlette Response with Prometheus exposition text."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
