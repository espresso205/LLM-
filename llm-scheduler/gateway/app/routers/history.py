"""GET /api/history — role-scoped request history."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api")


def _format_ts(ts: str | None) -> str | None:
    """Normalize timestamp to YYYY-MM-DD HH:MM:SS format."""
    if not ts:
        return ts
    # Already in target format (SQLite datetime)
    if len(ts) == 19 and ts[4] == '-' and ts[10] == ' ':
        return ts
    # ISO 8601 format: try to parse and reformat
    try:
        from datetime import datetime
        # Handle formats like 2024-01-01T12:34:56.789012+00:00 or 2024-01-01T12:34:56Z
        ts_clean = ts.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts_clean)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return ts


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query("", description="Filter by status: success|error|pending"),
    username: str = Query("", description="Admin only: filter by username"),
    user: dict = Depends(get_current_user),
):
    db = await get_db()
    offset = (page - 1) * size

    conditions = []
    params: list = []

    # Non-admins can only see their own history
    if user["role"] != "admin":
        conditions.append("user_id = ?")
        params.append(user["id"])
    elif username:
        conditions.append("username = ?")
        params.append(username)

    if status:
        conditions.append("status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = await db.execute_fetchall(
        f"""SELECT id, username, model, status, node_id, total_tokens,
                   latency_ms, error_message, created_at, completed_at
            FROM request_log {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (*params, size, offset),
    )
    total_rows = await db.execute_fetchall(
        f"SELECT COUNT(*) as cnt FROM request_log {where}", params
    )
    total = total_rows[0]["cnt"] if total_rows else 0

    items = []
    for r in rows:
        d = dict(r)
        d["created_at"] = _format_ts(d.get("created_at"))
        d["completed_at"] = _format_ts(d.get("completed_at"))
        items.append(d)

    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/history/{request_id}")
async def get_history_detail(request_id: str, user: dict = Depends(get_current_user)):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM request_log WHERE id=?", (request_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Request not found")
    record = dict(rows[0])
    # Non-admins can only access their own records
    if user["role"] != "admin" and record.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    record["created_at"] = _format_ts(record.get("created_at"))
    record["completed_at"] = _format_ts(record.get("completed_at"))
    return record


@router.delete("/history/{request_id}")
async def delete_history_record(request_id: str, user: dict = Depends(get_current_user)):
    """删除单条历史记录"""
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT user_id FROM request_log WHERE id=?", (request_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    # Non-admins can only delete their own records
    if user["role"] != "admin" and rows[0]["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权删除此记录")
    cursor = await db.execute("DELETE FROM request_log WHERE id=?", (request_id,))
    await db.commit()
    return {"deleted": cursor.rowcount}


@router.delete("/history")
async def delete_history(
    mode: str = Query("all"),
    ids: str = Query(""),
    user: dict = Depends(get_current_user),
):
    """批量删除历史记录。

    mode:
      - all:      清空全部（仅管理员）
      - selected: 按 ids 删除（逗号分隔）
    """
    db = await get_db()
    if mode == "selected":
        if not ids:
            raise HTTPException(status_code=400, detail="ids 参数不能为空")
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        if not id_list:
            raise HTTPException(status_code=400, detail="无效的 ids 参数")
        placeholders = ",".join("?" for _ in id_list)
        if user["role"] == "admin":
            cursor = await db.execute(
                f"DELETE FROM request_log WHERE id IN ({placeholders})", id_list
            )
        else:
            cursor = await db.execute(
                f"DELETE FROM request_log WHERE id IN ({placeholders}) AND user_id=?",
                (*id_list, user["id"]),
            )
        await db.commit()
        return {"deleted": cursor.rowcount}
    else:
        # mode == "all": only admin can clear all
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可清空全部历史")
        cursor = await db.execute("DELETE FROM request_log")
        await db.commit()
        return {"deleted": cursor.rowcount}
