"""Background scraper: pulls /metrics/json from gateway, scheduler, and all nodes."""
import asyncio
import httpx
from datetime import datetime, timezone

from .config import settings
from .database import get_db
from shared.utils import get_logger

log = get_logger(__name__)

# Dynamically updated by scheduler scrape
_known_node_urls: list[str] = []


async def scrape_loop() -> None:
    while True:
        await asyncio.sleep(settings.SCRAPE_INTERVAL_S)
        await scrape_all()


async def scrape_all() -> None:
    global _known_node_urls

    # Always scrape gateway and scheduler
    targets = [
        settings.GATEWAY_URL,
        settings.SCHEDULER_URL,
    ]

    # Add nodes from config + dynamically discovered
    targets += settings.node_url_list()
    targets += _known_node_urls

    # Deduplicate
    targets = list(dict.fromkeys(targets))

    headers = {"X-Internal-Token": settings.INTERNAL_TOKEN}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in targets:
            try:
                r = await client.get(f"{url}/metrics/json", headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    await _store(data)
            except Exception as exc:
                log.warning(f"Scrape failed for {url}: {exc}")

        # Discover nodes from scheduler
        try:
            r = await client.get(
                f"{settings.SCHEDULER_URL}/api/nodes",
                headers=headers,
            )
            if r.status_code == 200:
                nodes = r.json()
                _known_node_urls = [n["url"] for n in nodes]
        except Exception as exc:
            log.debug(f"Node discovery failed: {exc}")


async def _store(data: dict) -> None:
    db = await get_db()
    await db.execute(
        """INSERT INTO metrics_snapshot
               (source, ts, qps, latency_p50, latency_p95, success_rate,
                error_count, active_conns, gpu_util, mem_used_gb)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("source", "unknown"),
            data.get("ts", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')),
            data.get("qps"),
            data.get("latency_p50"),
            data.get("latency_p95"),
            data.get("success_rate"),
            data.get("error_count", 0),
            data.get("active_conns", 0),
            data.get("gpu_util"),
            data.get("mem_used_gb"),
        ),
    )
    await db.commit()
