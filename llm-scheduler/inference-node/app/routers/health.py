"""GET /health and GET /metrics/json — used by scheduler and monitoring."""
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import connection_counter
from ..config import settings
from ..database import get_db
from ..vllm_client import check_vllm_health, get_model_info

router = APIRouter()


@router.get("/health")
async def health():
    vllm_ok = await check_vllm_health()
    conns = connection_counter.value
    status = "ok" if vllm_ok else "error"
    if vllm_ok and conns >= 10:
        status = "busy"
    return {
        "status": status,
        "node_id": settings.NODE_ID,
        "active_connections": conns,
        "vllm_reachable": vllm_ok,
    }


@router.get("/api/model")
async def model_info():
    return await get_model_info()


@router.get("/metrics/json")
async def metrics_json():
    """Scraped by the monitoring service every 15 s."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    # Fetch last 5 minute buckets
    rows = await db.execute_fetchall(
        "SELECT * FROM metrics_1m ORDER BY bucket DESC LIMIT 5"
    )
    total_req = sum(r["request_count"] for r in rows)
    total_err = sum(r["error_count"] for r in rows)
    total_lat = sum(r["total_latency"] for r in rows)

    qps = total_req / 300.0 if rows else 0.0
    avg_lat = (total_lat / total_req) if total_req > 0 else 0.0
    success_rate = ((total_req - total_err) / total_req) if total_req > 0 else 1.0

    return {
        "source": f"node:{settings.NODE_ID}",
        "ts": now.isoformat(),
        "qps": round(qps, 4),
        "latency_p50": round(avg_lat, 2),
        "latency_p95": round(avg_lat * 1.5, 2),   # approximation without histogram
        "success_rate": round(success_rate, 4),
        "error_count": total_err,
        "active_conns": connection_counter.value,
    }
