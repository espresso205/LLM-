"""POST /v1/chat/completions — proxy to vLLM with logging."""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import connection_counter
from ..config import settings
from ..database import get_db
from ..vllm_client import forward_chat_completion
from shared.utils import get_logger, timer

log = get_logger(__name__)
router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    body = await request.json()
    request_id = str(uuid.uuid4())
    db = await get_db()

    await connection_counter.increment()
    started = datetime.now(timezone.utc).isoformat()
    status = "error"
    response_data = None
    error_msg = None
    latency_ms = 0.0
    prompt_tokens = 0
    completion_tokens = 0

    try:
        with timer() as t:
            response_data = await forward_chat_completion(body)
        latency_ms = t["ms"]
        status = "success"

        usage = response_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        log.info(f"[{settings.NODE_ID}] request {request_id} OK in {latency_ms:.0f}ms")
        return JSONResponse(content=response_data)

    except Exception as exc:
        error_msg = str(exc)
        log.error(f"[{settings.NODE_ID}] request {request_id} FAILED: {exc}")
        raise HTTPException(status_code=502, detail="Upstream inference error")

    finally:
        await connection_counter.decrement()
        completed = datetime.now(timezone.utc).isoformat()

        # Record minute-level metrics bucket
        bucket = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        try:
            await db.execute(
                """
                INSERT INTO metrics_1m (bucket, request_count, error_count, total_latency, max_latency)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(bucket) DO UPDATE SET
                    request_count = request_count + 1,
                    error_count   = error_count + excluded.error_count,
                    total_latency = total_latency + excluded.total_latency,
                    max_latency   = MAX(max_latency, excluded.max_latency)
                """,
                (bucket, 1 if status == "error" else 0, latency_ms, latency_ms),
            )
            await db.execute(
                """
                INSERT INTO request_log
                    (id, request_body, response_body, status, latency_ms,
                     prompt_tokens, completion_tokens, model, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    json.dumps(body),
                    json.dumps(response_data) if response_data else None,
                    status,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    body.get("model", ""),
                    error_msg,
                    started,
                ),
            )
            await db.commit()
        except Exception as db_exc:
            log.error(f"Failed to log request {request_id} to database: {db_exc}")
