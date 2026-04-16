"""Alert rule CRUD and history endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header

from ..config import settings

router = APIRouter(prefix="/api/alerts")


async def verify_internal_token(x_internal_token: str = Header(...)):
    import hmac
    if not hmac.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid internal token")


@router.get("/rules", dependencies=[Depends(verify_internal_token)])
async def list_rules():
    from ..database import get_db
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM alert_rules ORDER BY created_at DESC")
    return [dict(r) for r in rows]


@router.post("/rules", status_code=201, dependencies=[Depends(verify_internal_token)])
async def create_rule(body: dict):
    from ..database import get_db
    from ..alerts import METRIC_COLUMN_MAP
    db = await get_db()
    required = {"name", "metric", "operator", "threshold"}
    missing = required - body.keys()
    if missing:
        raise HTTPException(400, detail=f"Missing fields: {missing}")
    if body["operator"] not in ("gt", "lt", "eq"):
        raise HTTPException(400, detail="operator must be gt|lt|eq")
    if body["metric"] not in METRIC_COLUMN_MAP:
        raise HTTPException(400, detail=f"Unknown metric: {body['metric']}")
    try:
        threshold_val = float(body["threshold"])
    except (TypeError, ValueError):
        raise HTTPException(400, detail="threshold must be a number")
    try:
        window_val = int(body.get("window_s", 300))
    except (TypeError, ValueError):
        raise HTTPException(400, detail="window_s must be an integer")
    if window_val <= 0:
        raise HTTPException(400, detail="window_s must be positive")

    cur = await db.execute(
        """INSERT INTO alert_rules (name, metric, operator, threshold, window_s, is_active)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (
            body["name"],
            body["metric"],
            body["operator"],
            threshold_val,
            window_val,
        ),
    )
    await db.commit()
    return {"id": cur.lastrowid, **body}


@router.patch("/rules/{rule_id}", dependencies=[Depends(verify_internal_token)])
async def update_rule(rule_id: int, body: dict):
    from ..database import get_db
    db = await get_db()
    rows = await db.execute_fetchall("SELECT id FROM alert_rules WHERE id=?", (rule_id,))
    if not rows:
        raise HTTPException(404, detail="Rule not found")
    if "is_active" in body:
        await db.execute(
            "UPDATE alert_rules SET is_active=? WHERE id=?",
            (1 if body["is_active"] else 0, rule_id),
        )
        await db.commit()
    return {"updated": rule_id}


@router.delete("/rules/{rule_id}", dependencies=[Depends(verify_internal_token)])
async def delete_rule(rule_id: int):
    from ..database import get_db
    db = await get_db()
    await db.execute("DELETE FROM alert_rules WHERE id=?", (rule_id,))
    await db.commit()
    return {"deleted": rule_id}


@router.get("/history", dependencies=[Depends(verify_internal_token)])
async def alert_history(resolved: bool = False, page: int = 1, size: int = 50):
    from ..database import get_db
    db = await get_db()
    page = max(1, page)
    size = max(1, min(200, size))
    offset = (page - 1) * size
    rows = await db.execute_fetchall(
        """SELECT ah.*, ar.name as rule_name FROM alert_history ah
           LEFT JOIN alert_rules ar ON ah.rule_id = ar.id
           WHERE ah.resolved=?
           ORDER BY ah.fired_at DESC LIMIT ? OFFSET ?""",
        (1 if resolved else 0, size, offset),
    )
    total_rows = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM alert_history WHERE resolved=?", (1 if resolved else 0,)
    )
    total = total_rows[0]["cnt"] if total_rows else 0
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "size": size}


@router.post("/history/{alert_id}/resolve", dependencies=[Depends(verify_internal_token)])
async def resolve_alert(alert_id: int):
    from ..database import get_db
    from datetime import datetime, timezone
    db = await get_db()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    await db.execute(
        "UPDATE alert_history SET resolved=1, resolved_at=? WHERE id=?", (now, alert_id)
    )
    await db.commit()
    return {"resolved": alert_id}
