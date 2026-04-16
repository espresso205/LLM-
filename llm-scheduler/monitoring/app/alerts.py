"""Alert rule evaluator — runs after each scrape cycle."""
import asyncio
from datetime import datetime, timezone, timedelta

from .database import get_db
from shared.utils import get_logger

log = get_logger(__name__)

METRIC_COLUMN_MAP = {
    "qps": "qps",
    "latency_p50": "latency_p50",
    "latency_p95": "latency_p95",
    "success_rate": "success_rate",
    "error_count": "error_count",
    "active_conns": "active_conns",
}

OPERATORS = {
    "gt": lambda v, t: v > t,
    "lt": lambda v, t: v < t,
    "eq": lambda v, t: abs(v - t) < 1e-9,
}


async def evaluate_alerts() -> None:
    db = await get_db()
    rules = await db.execute_fetchall(
        "SELECT * FROM alert_rules WHERE is_active=1"
    )

    for rule in rules:
        col = METRIC_COLUMN_MAP.get(rule["metric"])
        if not col:
            continue
        op_fn = OPERATORS.get(rule["operator"])
        if not op_fn:
            continue

        window_s = rule["window_s"]
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).strftime('%Y-%m-%d %H:%M:%S')
        rows = await db.execute_fetchall(
            f"""SELECT AVG({col}) as val FROM metrics_snapshot
                WHERE source='gateway'
                  AND ts >= ?
                  AND {col} IS NOT NULL""",
            (cutoff,),
        )
        if not rows or rows[0]["val"] is None:
            continue

        value = rows[0]["val"]
        if op_fn(value, rule["threshold"]):
            msg = (
                f"Alert '{rule['name']}': {rule['metric']} "
                f"{rule['operator']} {rule['threshold']} "
                f"(current: {value:.4f})"
            )
            log.warning(msg)
            # Only fire if not already active (unresolved)
            active = await db.execute_fetchall(
                "SELECT id FROM alert_history WHERE rule_id=? AND resolved=0",
                (rule["id"],),
            )
            if not active:
                await db.execute(
                    """INSERT INTO alert_history (rule_id, triggered_value, message)
                       VALUES (?, ?, ?)""",
                    (rule["id"], value, msg),
                )
                await db.commit()


async def alert_loop() -> None:
    while True:
        await asyncio.sleep(15)
        try:
            await evaluate_alerts()
        except Exception as exc:
            log.warning(f"Alert evaluation error: {exc}")
