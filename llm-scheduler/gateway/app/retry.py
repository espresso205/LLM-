"""httpx retry logic with node exclusion for the gateway."""
import asyncio
import httpx
from shared.utils import get_logger
from .config import settings

log = get_logger(__name__)

MAX_RETRIES = 3
RETRY_STATUS = {502, 503, 504}


async def _pick_node(request_id: str, exclude: list[str]) -> dict:
    headers = {"X-Internal-Token": settings.INTERNAL_TOKEN}
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"{settings.SCHEDULER_URL}/api/schedule",
            json={"request_id": request_id, "exclude_nodes": exclude},
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def forward_with_retry(request_id: str, payload: dict) -> tuple[dict, str, str]:
    """
    Returns (response_json, node_id, actual_model).
    Raises the last exception if all retries fail.
    """
    tried: list[str] = []
    last_exc: Exception | None = None
    resolved_model = ""

    for attempt in range(MAX_RETRIES):
        try:
            sched = await _pick_node(request_id, tried)
        except Exception as exc:
            raise RuntimeError(f"Scheduler unavailable: {exc}") from exc

        node_id = sched["node_id"]
        node_url = sched["node_url"]
        tried.append(node_id)

        # Resolve "auto" model name from the actual node
        actual_payload = payload
        if payload.get("model") in ("auto", "", None):
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    mr = await c.get(f"{node_url}/api/model",
                                     headers={"X-Internal-Token": settings.INTERNAL_TOKEN})
                    if mr.status_code == 200:
                        models = mr.json().get("data", [])
                        if models:
                            resolved_model = models[0]["id"]
                            actual_payload = {**payload, "model": resolved_model}
            except Exception:
                pass  # keep original payload if lookup fails
        else:
            resolved_model = payload.get("model", "")

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(
                    f"{node_url}/v1/chat/completions",
                    json=actual_payload,
                )
            if r.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(
                    f"Retryable {r.status_code}", request=r.request, response=r
                )
            r.raise_for_status()
            return r.json(), node_id, resolved_model

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            wait = 0.1 * (2 ** attempt)
            log.warning(
                f"Request {request_id} attempt {attempt + 1} via {node_id} failed: {exc}. "
                f"Retrying in {wait:.2f}s"
            )
            await asyncio.sleep(wait)

    raise last_exc  # type: ignore[misc]
