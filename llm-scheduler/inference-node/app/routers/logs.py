"""GET /api/logs — local request log, paginated."""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from ..config import settings

router = APIRouter()


async def verify_internal_token(x_internal_token: str = Header(...)):
    if not hmac.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid internal token")


@router.get("/api/logs", dependencies=[Depends(verify_internal_token)])
async def get_logs(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    from ..database import get_db
    db = await get_db()
    offset = (page - 1) * size
    rows = await db.execute_fetchall(
        """SELECT id, status, latency_ms, model, prompt_tokens, completion_tokens,
                  error_message, created_at
           FROM request_log ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (size, offset),
    )
    total_row = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM request_log")
    total = total_row[0]["cnt"] if total_row else 0
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }
