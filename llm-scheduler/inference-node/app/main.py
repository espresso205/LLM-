"""Inference Node FastAPI application entry point."""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db, close_db
from .heartbeat import register_self, heartbeat_loop
from .routers import inference, health, logs

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Register with scheduler and start heartbeat in background
    _background_tasks.append(asyncio.create_task(register_self()))
    _background_tasks.append(asyncio.create_task(heartbeat_loop()))
    yield
    # Cancel background tasks before closing DB
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()
    await close_db()


app = FastAPI(title="LLM Inference Node", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inference.router)
app.include_router(health.router)
app.include_router(logs.router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from shared.metrics import metrics_response, NODE_ACTIVE_CONNECTIONS, NODE_STATUS
    from .config import settings
    from . import connection_counter
    NODE_ACTIVE_CONNECTIONS.labels(node_id=settings.NODE_ID).set(connection_counter.value)
    NODE_STATUS.labels(node_id=settings.NODE_ID).set(1)
    return metrics_response()

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
        # Prevent path traversal: ensure resolved path stays within static dir
        if not file_path.startswith(os.path.normpath(_static_dir)):
            return FileResponse(os.path.join(_static_dir, "index.html"))
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_static_dir, "index.html"))
