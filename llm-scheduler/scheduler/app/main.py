"""Scheduler FastAPI application."""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db, close_db, get_db
from .registry import registry
from .strategies.manager import set_strategy
from .routers import nodes, schedule, logs
from .config import settings

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Restore strategy from DB
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT value FROM strategy_config WHERE key='current_strategy'"
    )
    if row:
        try:
            set_strategy(row[0]["value"])
        except ValueError:
            pass
    # Start TTL eviction background task
    _background_tasks.append(asyncio.create_task(registry.evict_stale()))
    yield
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()
    await close_db()


app = FastAPI(title="LLM Scheduler", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)
app.include_router(schedule.router)
app.include_router(logs.router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from shared.metrics import metrics_response
    return metrics_response()


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "version": "1.0.0"}

# Serve Vue frontend
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        return FileResponse(os.path.join(_static_dir, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        file_path = os.path.normpath(os.path.join(_static_dir, full_path))
        if not file_path.startswith(os.path.normpath(_static_dir)):
            return FileResponse(os.path.join(_static_dir, "index.html"))
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_static_dir, "index.html"))
