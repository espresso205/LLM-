"""GET /api/metrics/summary and /api/metrics/nodes."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/metrics")

RANGE_SECONDS = {
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "24h": 86400,
    "7d": 604800,
}


@router.get("/summary")
async def metrics_summary(range: str = Query("1h")):
    from ..database import get_db
    db = await get_db()
    window_s = RANGE_SECONDS.get(range, 3600)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).strftime('%Y-%m-%d %H:%M:%S')

    rows = await db.execute_fetchall(
        """SELECT
               COUNT(*) as snapshots,
               AVG(qps) as avg_qps,
               AVG(latency_p50) as avg_lat_p50,
               AVG(latency_p95) as avg_lat_p95,
               AVG(success_rate) as avg_success,
               SUM(error_count) as total_errors,
               AVG(active_conns) as avg_conns
           FROM metrics_snapshot
           WHERE source='gateway'
             AND ts >= ?""",
        (cutoff,),
    )
    summary = rows[0] if rows else {}

    # Time series for charts — group by minute
    ts_rows = await db.execute_fetchall(
        """SELECT
               strftime('%Y-%m-%dT%H:%M', ts) as bucket,
               AVG(qps) as qps,
               AVG(latency_p95) as latency_p95,
               AVG(success_rate) as success_rate
           FROM metrics_snapshot
           WHERE source='gateway'
             AND ts >= ?
           GROUP BY strftime('%Y-%m-%dT%H:%M', ts)
           ORDER BY bucket ASC""",
        (cutoff,),
    )

    # Count online nodes from latest scheduler snapshot
    node_rows = await db.execute_fetchall(
        """SELECT active_conns FROM metrics_snapshot
           WHERE source='scheduler' ORDER BY ts DESC LIMIT 1"""
    )

    return {
        "qps": round(summary["avg_qps"] or 0, 4),
        "avg_latency_ms": round(summary["avg_lat_p50"] or 0, 2),
        "p95_latency_ms": round(summary["avg_lat_p95"] or 0, 2),
        "success_rate": round(summary["avg_success"] or 1.0, 4),
        "total_requests": summary["snapshots"] or 0,
        "error_count": summary["total_errors"] or 0,
        "online_nodes": node_rows[0]["active_conns"] if node_rows else 0,
        "time_series": [dict(r) for r in ts_rows],
    }


@router.get("/nodes")
async def node_stats(range: str = Query("1h")):
    from ..database import get_db
    db = await get_db()
    window_s = RANGE_SECONDS.get(range, 3600)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).strftime('%Y-%m-%d %H:%M:%S')

    rows = await db.execute_fetchall(
        """SELECT
               source,
               AVG(qps) as avg_qps,
               AVG(latency_p50) as avg_lat,
               AVG(success_rate) as avg_success,
               SUM(error_count) as total_errors,
               AVG(active_conns) as avg_conns
           FROM metrics_snapshot
           WHERE source LIKE 'node:%'
             AND ts >= ?
           GROUP BY source""",
        (cutoff,),
    )
    return [
        {
            "node_id": r["source"].replace("node:", ""),
            "avg_qps": round(r["avg_qps"] or 0, 4),
            "avg_latency_ms": round(r["avg_lat"] or 0, 2),
            "avg_success_rate": round(r["avg_success"] or 1.0, 4),
            "error_count": r["total_errors"] or 0,
            "avg_active_conns": round(r["avg_conns"] or 0, 1),
        }
        for r in rows
    ]
