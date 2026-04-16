"""Monitoring FastAPI application."""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db, close_db
from .collector import scrape_loop
from .alerts import alert_loop
from .routers import metrics, alerts

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    _background_tasks.append(asyncio.create_task(scrape_loop()))
    _background_tasks.append(asyncio.create_task(alert_loop()))
    yield
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()
    await close_db()


app = FastAPI(title="LLM Monitoring", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(alerts.router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from shared.metrics import metrics_response
    return metrics_response()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/events")
async def receive_event(body: dict, x_internal_token: str = Header(...)):
    import hmac
    from .config import settings
    if not hmac.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid internal token")
    from .database import get_db
    import json
    db = await get_db()
    await db.execute(
        "INSERT INTO events (source, event_type, payload) VALUES (?, ?, ?)",
        (body.get("source", "unknown"), body.get("event_type", "unknown"),
         json.dumps(body.get("payload"))),
    )
    await db.commit()
    return {"received": True}


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
