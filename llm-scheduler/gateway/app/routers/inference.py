"""POST /v1/chat/completions — validate auth, proxy through scheduler → node."""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..auth import get_current_user
from ..database import get_db
from ..retry import forward_with_retry
from shared.utils import get_logger

log = get_logger(__name__)
router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    request_id = str(uuid.uuid4())
    db = await get_db()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    # Record pending
    await db.execute(
        """INSERT INTO request_log
               (id, user_id, username, model, messages_json, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
        (
            request_id,
            user["id"],
            user["username"],
            body.get("model", ""),
            json.dumps(body.get("messages", [])),
            now,
        ),
    )
    await db.commit()

    status = "error"
    response_data = None
    error_msg = None
    node_id = None
    latency_ms = 0.0
    total_tokens = 0
    actual_model = None

    try:
        from shared.utils import timer
        with timer() as t:
            response_data, node_id, actual_model = await forward_with_retry(request_id, body)
        latency_ms = t["ms"]
        status = "success"
        total_tokens = response_data.get("usage", {}).get("total_tokens", 0)
        if not actual_model:
            actual_model = response_data.get("model", "")

        # Prometheus instrumentation
        from shared.metrics import INFERENCE_REQUESTS, INFERENCE_LATENCY, INFERENCE_TOKENS
        INFERENCE_REQUESTS.labels(service="gateway", model=actual_model or "unknown", status="success").inc()
        INFERENCE_LATENCY.labels(service="gateway", model=actual_model or "unknown").observe(latency_ms / 1000)
        if total_tokens:
            INFERENCE_TOKENS.labels(service="gateway", type="total").inc(total_tokens)

        return JSONResponse(content={**response_data, "_node_id": node_id})

    except Exception as exc:
        error_msg = str(exc)
        log.error(f"Request {request_id} failed: {exc}")

        # Prometheus instrumentation
        from shared.metrics import INFERENCE_REQUESTS
        INFERENCE_REQUESTS.labels(service="gateway", model=body.get("model", "unknown"), status="error").inc()

        raise HTTPException(status_code=502, detail="Upstream inference error")

    finally:
        completed = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        try:
            await db.execute(
                """UPDATE request_log SET
                       status=?, response_json=?, node_id=?, total_tokens=?,
                       latency_ms=?, error_message=?, completed_at=?, model=?
                   WHERE id=?""",
                (
                    status,
                    json.dumps(response_data) if response_data else None,
                    node_id,
                    total_tokens,
                    latency_ms,
                    error_msg,
                    completed,
                    actual_model if status == "success" else None,
                    request_id,
                ),
            )
            await db.commit()
        except Exception as db_exc:
            log.error(f"Failed to update request_log for {request_id}: {db_exc}")
