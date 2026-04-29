"""
Cross-service Pydantic schemas — single source of truth.
"""
from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


# ─── Inference ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" | "assistant" | "system"
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 1.0
    stream: bool = False

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: List[ChatChoice]
    usage: Usage


# ─── Request History ─────────────────────────────────────────────────────────

class RequestRecord(BaseModel):
    id: str
    username: Optional[str] = None
    model: Optional[str] = None
    status: str
    node_id: Optional[str] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    messages_json: Optional[str] = None
    response_json: Optional[str] = None


# ─── Scheduler / Nodes ───────────────────────────────────────────────────────

class NodeRegisterRequest(BaseModel):
    node_id: str
    host: str
    port: int
    weight: float = 1.0

class HeartbeatRequest(BaseModel):
    active_connections: int = 0
    status: str = "healthy"
    gpu_util: Optional[float] = None
    memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_temperature: Optional[float] = None
    kv_cache_usage: Optional[float] = None
    avg_token_latency: Optional[float] = None
    num_requests_running: Optional[int] = None
    num_requests_waiting: Optional[int] = None

class NodeInfo(BaseModel):
    node_id: str
    host: str
    port: int
    weight: float
    status: str              # healthy | unhealthy | draining
    active_connections: int
    last_heartbeat: Optional[str] = None
    registered_at: Optional[str] = None

class ScheduleRequest(BaseModel):
    request_id: str
    exclude_nodes: List[str] = []

class ScheduleResponse(BaseModel):
    node_id: str
    node_url: str
    algorithm_used: str
    decision_latency_ms: float

class StrategyInfo(BaseModel):
    current: str
    available: List[str]

class StrategyUpdateRequest(BaseModel):
    strategy: str

class SchedulingLogEntry(BaseModel):
    id: int
    request_id: str
    selected_node: str
    algorithm: str
    candidates: Optional[str] = None
    decision_ms: Optional[float] = None
    active_conns_at_decision: Optional[int] = None
    created_at: str


# ─── Monitoring ──────────────────────────────────────────────────────────────

class MetricsSummary(BaseModel):
    qps: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    error_count: int = 0
    online_nodes: int = 0
    time_series: List[Any] = []

class NodeStats(BaseModel):
    node_id: str
    requests: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    active_conns: int = 0

class AlertRule(BaseModel):
    id: Optional[int] = None
    name: str
    metric: str          # latency_p95 | error_rate | qps | active_conns
    operator: str        # gt | lt | eq
    threshold: float
    window_s: int = 250
    is_active: bool = True
    created_at: Optional[str] = None

class AlertEvent(BaseModel):
    id: Optional[int] = None
    rule_id: int
    triggered_value: float
    message: str
    resolved: bool = False
    fired_at: str
    resolved_at: Optional[str] = None


# ─── Health / Metrics ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str          # ok | busy | error
    version: str = "1.0.0"

class NodeHealthResponse(BaseModel):
    status: str
    node_id: str
    active_connections: int
    vllm_reachable: bool
    model_id: Optional[str] = None

class MetricsJson(BaseModel):
    """JSON metrics endpoint — scraped by monitoring service."""
    source: str
    ts: str
    qps: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    active_conns: int = 0
    gpu_util: Optional[float] = None
    mem_used_gb: Optional[float] = None
