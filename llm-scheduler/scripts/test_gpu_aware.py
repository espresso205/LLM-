#!/usr/bin/env python3
"""
Unit tests for the GPU-Aware scheduling strategy and field consistency.

Run from the project root:
    PYTHONPATH=. python scripts/test_gpu_aware.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.app.strategies.gpu_aware import GPUAwareStrategy
from scheduler.app.registry import NodeInfo

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}  {detail}")
        failed += 1


def apick(strategy, nodes):
    """Run strategy.pick in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(strategy.pick(nodes))


def make_node(node_id="node-1", **overrides) -> NodeInfo:
    defaults = {
        "node_id": node_id, "host": "localhost", "port": 8003,
        "weight": 1.0, "status": "healthy", "active_connections": 0,
        "gpu_util": None, "memory_used_gb": None, "gpu_memory_total_gb": None,
        "gpu_temperature": None, "kv_cache_usage": None, "avg_token_latency": None,
        "num_requests_running": None, "num_requests_waiting": None,
    }
    defaults.update(overrides)
    return NodeInfo(**defaults)


strategy = GPUAwareStrategy()

print("=" * 60)
print("  GPU-Aware Strategy Unit Tests")
print("=" * 60)
print("\n--- Strategy Logic ---")

# 1. No nodes raises
print("\n  test_no_nodes_raises:")
try:
    apick(strategy, [])
    check("No nodes raises", False, "did not raise")
except RuntimeError:
    check("No nodes raises", True)

# 2. No GPU data gets default low score
print("\n  test_no_gpu_data_vs_kv_data:")
nodes = [make_node("a"), make_node("b", kv_cache_usage=30.0)]
result = apick(strategy, nodes)
check("Node with kv_data preferred over no-data", result.node_id == "b",
      f"got {result.node_id}")

# 3. Low KV cache preferred
print("\n  test_low_kv_cache_preferred:")
nodes = [
    make_node("busy", kv_cache_usage=80.0, num_requests_running=5),
    make_node("free", kv_cache_usage=20.0, num_requests_running=1),
]
result = apick(strategy, nodes)
check("Low KV cache node preferred", result.node_id == "free",
      f"got {result.node_id}")

# 4. Shorter queue preferred
print("\n  test_shorter_queue_preferred:")
nodes = [
    make_node("queued", kv_cache_usage=30.0, num_requests_running=10, num_requests_waiting=5),
    make_node("empty", kv_cache_usage=30.0, num_requests_running=0, num_requests_waiting=0),
]
result = apick(strategy, nodes)
check("Shorter queue preferred", result.node_id == "empty",
      f"got {result.node_id}")

# 5. KV >95% excluded
print("\n  test_kv_threshold_excludes:")
nodes = [
    make_node("full", kv_cache_usage=97.0, num_requests_running=0),
    make_node("ok", kv_cache_usage=50.0, num_requests_running=3),
]
result = apick(strategy, nodes)
check("KV >95% node excluded", result.node_id == "ok",
      f"got {result.node_id}")

# 6. All KV-full fallback to least connections
print("\n  test_all_kv_full_fallback:")
nodes = [
    make_node("a", kv_cache_usage=97.0, active_connections=5),
    make_node("b", kv_cache_usage=98.0, active_connections=1),
]
result = apick(strategy, nodes)
check("All KV-full fallback to least conns", result.node_id == "b",
      f"got {result.node_id}")

# 7. Score bounds
print("\n  test_score_bounds:")
node = make_node("x", kv_cache_usage=0.0, num_requests_running=0)
score = strategy._score(node)
check("Score in [0,1]", 0.0 <= score <= 1.0, f"score={score}")

# 8. Score None for over-threshold
print("\n  test_score_none_over_threshold:")
node = make_node("x", kv_cache_usage=99.0)
score = strategy._score(node)
check("Over-threshold score is None", score is None, f"score={score}")

# 9. Score 0.3 for no data
print("\n  test_score_default_no_data:")
node = make_node("x")
score = strategy._score(node)
check("No-data score is 0.3", score == 0.3, f"score={score}")

# 10. Tie-break by least connections
print("\n  test_tie_break_least_connections:")
nodes = [
    make_node("busy", kv_cache_usage=50.0, num_requests_running=0, active_connections=10),
    make_node("idle", kv_cache_usage=50.0, num_requests_running=0, active_connections=1),
]
result = apick(strategy, nodes)
check("Tie-break by least connections", result.node_id == "idle",
      f"got {result.node_id}")

# 11. KV cache weight dominates
print("\n  test_kv_cache_dominates:")
nodes = [
    make_node("a", kv_cache_usage=10.0, num_requests_running=10),
    make_node("b", kv_cache_usage=60.0, num_requests_running=0),
]
sa = strategy._score(nodes[0])
sb = strategy._score(nodes[1])
check("Score b > score a", sb > sa, f"a={sa:.3f} b={sb:.3f}")
result = apick(strategy, nodes)
check("Correct winner", result.node_id == "b", f"got {result.node_id}")

# ─── Field Consistency ───────────────────────────────────────────────────

print("\n--- Field Consistency ---")

print("\n  test_heartbeat_request_fields:")
from shared.models import HeartbeatRequest
hr_fields = set(HeartbeatRequest.model_fields.keys())
for f in [
    "active_connections", "status",
    "gpu_util", "memory_used_gb", "gpu_memory_total_gb",
    "gpu_temperature", "kv_cache_usage", "avg_token_latency",
    "num_requests_running", "num_requests_waiting",
]:
    check(f"HeartbeatRequest has '{f}'", f in hr_fields, "missing")

print("\n  test_nodeinfo_fields:")
import dataclasses
ni_fields = {f.name for f in dataclasses.fields(NodeInfo)}
for f in [
    "gpu_util", "memory_used_gb", "gpu_memory_total_gb",
    "gpu_temperature", "kv_cache_usage", "avg_token_latency",
    "num_requests_running", "num_requests_waiting",
]:
    check(f"NodeInfo has '{f}'", f in ni_fields, "missing")

print("\n  test_field_names_match:")
gpu_fields_hr = [f for f in hr_fields if f not in ("active_connections", "status")]
gpu_fields_ni = [f for f in ni_fields if f not in (
    "node_id", "host", "port", "weight", "status",
    "active_connections", "last_heartbeat", "registered_at",
)]
check("GPU field count matches", len(gpu_fields_hr) == len(gpu_fields_ni),
      f"HR={len(gpu_fields_hr)} NI={len(gpu_fields_ni)}")
for f in gpu_fields_hr:
    check(f"'{f}' in NodeInfo", f in ni_fields, "missing")

# ─── Summary ─────────────────────────────────────────────────────────────

print(f"\n{'=' * 60}")
print(f"  Results: {passed}/{passed + failed} passed, {failed} failed")
print(f"{'=' * 60}\n")

sys.exit(0 if failed == 0 else 1)
