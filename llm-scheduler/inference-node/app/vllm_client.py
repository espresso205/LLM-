"""Async httpx wrapper around the local vLLM server."""
import httpx
from .config import settings
from shared.utils import get_logger

log = get_logger(__name__)

# Cache resolved model name to avoid repeated /v1/models calls under load
_cached_model: str = ""


async def _get_actual_model() -> str:
    """Get the actual model name from vLLM (cached after first success)."""
    global _cached_model
    if _cached_model:
        return _cached_model
    info = await get_model_info()
    models = info.get("data", [])
    if models:
        _cached_model = models[0]["id"]
    return _cached_model


async def forward_chat_completion(payload: dict) -> dict:
    """Forward a chat-completion request to vLLM and return the JSON response."""
    url = f"{settings.VLLM_URL}/v1/chat/completions"
    # Replace placeholder model names with the actual vLLM model
    if payload.get("model") in ("auto", "", None):
        actual = await _get_actual_model()
        if actual:
            payload = {**payload, "model": actual}
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def get_model_info() -> dict:
    """Fetch model list from vLLM."""
    url = f"{settings.VLLM_URL}/v1/models"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning(f"Could not fetch model info from vLLM: {exc}")
        return {"data": []}


async def check_vllm_health() -> bool:
    """Return True if vLLM is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.VLLM_URL}/v1/models")
            return r.status_code == 200
    except Exception:
        return False
