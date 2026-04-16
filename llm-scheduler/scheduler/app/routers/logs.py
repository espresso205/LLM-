"""Strategy management and scheduling decision logs."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_internal_token
from ..database import get_db
from ..strategies.manager import STRATEGIES, get_strategy, set_strategy

router = APIRouter(dependencies=[Depends(verify_internal_token)])


@router.get("/api/strategy")
async def get_strategy_info():
    return {
        "current": get_strategy().name,
        "available": list(STRATEGIES.keys()),
    }


@router.put("/api/strategy")
async def update_strategy(body: dict):
    name = body.get("strategy", "")
    if name not in STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{name}'. Available: {list(STRATEGIES)}",
        )
    set_strategy(name)
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO strategy_config VALUES ('current_strategy', ?)", (name,)
    )
    await db.commit()
    return {"strategy": name, "message": f"Switched to {name}"}


@router.get("/api/logs")
async def get_logs(page: int = 1, size: int = 50, node_id: str = ""):
    db = await get_db()
    offset = (page - 1) * size
    if node_id:
        rows = await db.execute_fetchall(
            """SELECT * FROM scheduling_log WHERE selected_node=?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (node_id, size, offset),
        )
        total_rows = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM scheduling_log WHERE selected_node=?", (node_id,)
        )
    else:
        rows = await db.execute_fetchall(
            "SELECT * FROM scheduling_log ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (size, offset),
        )
        total_rows = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM scheduling_log"
        )
    total = total_rows[0]["cnt"] if total_rows else 0
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "size": size}


@router.delete("/api/logs")
async def delete_logs(mode: str = "all", ids: str = "", before_days: int = 0):
    """删除调度日志。

    mode:
      - all:      清空全部日志
      - selected: 按 ids 删除（逗号分隔的 id 列表）
      - before:   删除 before_days 天之前的日志
    """
    db = await get_db()
    if mode == "selected":
        if not ids:
            raise HTTPException(status_code=400, detail="ids 参数不能为空")
        id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
        if not id_list:
            raise HTTPException(status_code=400, detail="无效的 ids 参数")
        placeholders = ",".join("?" for _ in id_list)
        cursor = await db.execute(
            f"DELETE FROM scheduling_log WHERE id IN ({placeholders})", id_list
        )
        await db.commit()
        return {"deleted": cursor.rowcount}
    elif mode == "before":
        if before_days <= 0:
            raise HTTPException(status_code=400, detail="before_days 必须大于 0")
        cursor = await db.execute(
            "DELETE FROM scheduling_log WHERE created_at < datetime('now', ?)",
            (f"-{before_days} days",),
        )
        await db.commit()
        return {"deleted": cursor.rowcount}
    else:
        cursor = await db.execute("DELETE FROM scheduling_log")
        await db.commit()
        return {"deleted": cursor.rowcount}


@router.get("/metrics/json")
async def metrics_json():
    from datetime import datetime, timezone
    from ..registry import registry

    nodes = await registry.all_nodes()
    healthy = [n for n in nodes if n.status == "healthy"]
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM scheduling_log WHERE created_at >= datetime('now','-5 minutes')"
    )
    recent_count = rows[0]["cnt"] if rows else 0
    return {
        "source": "scheduler",
        "ts": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "qps": round(recent_count / 300, 4),
        "latency_p50": 0,
        "latency_p95": 0,
        "success_rate": 1.0,
        "error_count": 0,
        "active_conns": sum(n.active_connections for n in healthy),
        "online_nodes": len(healthy),
        "total_nodes": len(nodes),
    }
