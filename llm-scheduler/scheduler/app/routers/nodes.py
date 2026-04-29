"""Node CRUD + heartbeat endpoints."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_internal_token
from ..database import get_db
from ..registry import NodeInfo, registry
from shared.models import HeartbeatRequest, NodeRegisterRequest

router = APIRouter(prefix="/api/nodes", dependencies=[Depends(verify_internal_token)])


@router.post("/register", status_code=201)
async def register_node(body: NodeRegisterRequest):
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    info = NodeInfo(
        node_id=body.node_id,
        host=body.host,
        port=body.port,
        weight=body.weight,
        registered_at=now,
        last_heartbeat=time.monotonic(),
    )
    await registry.register(info)
    # Persist to DB for recovery
    await db.execute(
        """INSERT OR REPLACE INTO nodes (node_id, host, port, weight, status, registered_at, last_heartbeat)
           VALUES (?, ?, ?, ?, 'healthy', ?, ?)""",
        (body.node_id, body.host, body.port, body.weight, now, now),
    )
    await db.commit()
    return {"node_id": body.node_id, "registered_at": now}


@router.post("/{node_id}/heartbeat")
async def heartbeat(node_id: str, body: HeartbeatRequest):
    from ..strategies.manager import get_strategy
    db = await get_db()
    found = await registry.heartbeat(
        node_id,
        active_connections=body.active_connections,
        status=body.status,
        gpu_util=body.gpu_util,
        memory_used_gb=body.memory_used_gb,
        gpu_memory_total_gb=body.gpu_memory_total_gb,
        gpu_temperature=body.gpu_temperature,
        kv_cache_usage=body.kv_cache_usage,
        avg_token_latency=body.avg_token_latency,
        num_requests_running=body.num_requests_running,
        num_requests_waiting=body.num_requests_waiting,
    )
    if not found:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not registered")
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE nodes SET status=?, last_heartbeat=? WHERE node_id=?",
        (body.status, now, node_id),
    )
    await db.commit()
    return {"received": True, "strategy": get_strategy().name}


@router.get("")
async def list_nodes():
    nodes = await registry.all_nodes()
    return [
        {
            "node_id": n.node_id,
            "host": n.host,
            "port": n.port,
            "weight": n.weight,
            "status": n.status,
            "active_connections": n.active_connections,
            "url": n.url,
            "registered_at": n.registered_at,
            "gpu_util": n.gpu_util,
            "memory_used_gb": n.memory_used_gb,
            "gpu_memory_total_gb": n.gpu_memory_total_gb,
            "gpu_temperature": n.gpu_temperature,
            "kv_cache_usage": n.kv_cache_usage,
            "avg_token_latency": n.avg_token_latency,
            "num_requests_running": n.num_requests_running,
            "num_requests_waiting": n.num_requests_waiting,
        }
        for n in nodes
    ]


@router.get("/{node_id}")
async def get_node(node_id: str):
    node = await registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "node_id": node.node_id,
        "host": node.host,
        "port": node.port,
        "weight": node.weight,
        "status": node.status,
        "active_connections": node.active_connections,
        "url": node.url,
        "registered_at": node.registered_at,
        "gpu_util": node.gpu_util,
        "memory_used_gb": node.memory_used_gb,
        "gpu_memory_total_gb": node.gpu_memory_total_gb,
        "gpu_temperature": node.gpu_temperature,
        "kv_cache_usage": node.kv_cache_usage,
        "avg_token_latency": node.avg_token_latency,
        "num_requests_running": node.num_requests_running,
        "num_requests_waiting": node.num_requests_waiting,
    }


@router.delete("/{node_id}/deregister")
async def deregister_node(node_id: str):
    db = await get_db()
    removed = await registry.deregister(node_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.execute("DELETE FROM nodes WHERE node_id=?", (node_id,))
    await db.commit()
    return {"removed": node_id}
