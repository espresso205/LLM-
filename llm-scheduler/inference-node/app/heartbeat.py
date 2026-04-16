"""Background heartbeat + self-registration with the scheduler."""
import asyncio
import httpx
from .config import settings
from . import connection_counter
from shared.utils import get_logger

log = get_logger(__name__)


async def register_self() -> None:
    payload = {
        "node_id": settings.NODE_ID,
        "host": settings.NODE_HOST,
        "port": settings.NODE_PORT,
        "weight": 1.0,
    }
    headers = {"X-Internal-Token": settings.INTERNAL_TOKEN}
    for attempt in range(10):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{settings.SCHEDULER_URL}/api/nodes/register",
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                log.info(f"Registered as {settings.NODE_ID} with scheduler")
                return
        except Exception as exc:
            wait = min(2 ** attempt, 30)
            log.warning(f"Registration attempt {attempt + 1} failed ({exc}), retrying in {wait}s")
            await asyncio.sleep(wait)
    log.error("Could not register with scheduler after 10 attempts — continuing anyway")


async def heartbeat_loop() -> None:
    await asyncio.sleep(3)  # let startup settle
    headers = {"X-Internal-Token": settings.INTERNAL_TOKEN}
    while True:
        try:
            payload = {
                "active_connections": connection_counter.value,
                "status": "healthy",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{settings.SCHEDULER_URL}/api/nodes/{settings.NODE_ID}/heartbeat",
                    json=payload,
                    headers=headers,
                )
        except Exception as exc:
            log.warning(f"Heartbeat failed: {exc}")
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL_S)
