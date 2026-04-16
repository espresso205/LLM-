"""POST /api/schedule — pick a node using the active strategy."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_internal_token
from ..database import get_db
from ..registry import registry
from ..strategies.manager import get_strategy
from shared.models import ScheduleRequest
from shared.utils import get_logger, timer

log = get_logger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(verify_internal_token)])


@router.post("/schedule")
async def schedule(body: ScheduleRequest):
    db = await get_db()
    candidates = await registry.healthy_nodes(exclude=body.exclude_nodes)

    if not candidates:
        raise HTTPException(
            status_code=503,
            detail="No healthy inference nodes available",
        )

    strategy = get_strategy()
    with timer() as t:
        chosen = await strategy.pick(candidates)

    decision_ms = t["ms"]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    # Prometheus instrumentation
    from shared.metrics import SCHEDULE_DECISIONS, SCHEDULE_LATENCY
    SCHEDULE_DECISIONS.labels(algorithm=strategy.name, node_id=chosen.node_id).inc()
    SCHEDULE_LATENCY.labels(algorithm=strategy.name).observe(decision_ms / 1000)

    await db.execute(
        """INSERT INTO scheduling_log
               (request_id, selected_node, algorithm, candidates, decision_ms, active_conns_at_decision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            body.request_id,
            chosen.node_id,
            strategy.name,
            json.dumps([n.node_id for n in candidates]),
            decision_ms,
            chosen.active_connections,
            now,
        ),
    )
    await db.commit()

    log.info(
        f"Scheduled request {body.request_id} → {chosen.node_id} "
        f"({strategy.name}, {decision_ms:.2f}ms)"
    )

    return {
        "node_id": chosen.node_id,
        "node_url": chosen.url,
        "algorithm_used": strategy.name,
        "decision_latency_ms": decision_ms,
    }
