"""Gateway FastAPI application."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db, close_db
from .routers import auth, inference, history, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="LLM Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inference.router)
app.include_router(history.router)
app.include_router(admin.router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from shared.metrics import metrics_response
    return metrics_response()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/metrics/json")
async def metrics_json():
    from datetime import datetime, timezone
    from .database import get_db

    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT
               COUNT(*) as total,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
               AVG(latency_ms) as avg_lat
           FROM request_log
           WHERE created_at >= datetime('now','-5 minutes')"""
    )
    row = rows[0] if rows else {}
    total = row["total"] or 0
    errors = row["errors"] or 0
    avg_lat = row["avg_lat"] or 0.0
    return {
        "source": "gateway",
        "ts": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "qps": round(total / 300, 4),
        "latency_p50": round(avg_lat, 2),
        "latency_p95": round(avg_lat * 1.5, 2),
        "success_rate": round((total - errors) / total, 4) if total > 0 else 1.0,
        "error_count": errors,
        "active_conns": 0,
    }


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
