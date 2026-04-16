import aiosqlite
from .config import settings

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS metrics_snapshot (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    ts           TEXT NOT NULL,
    qps          REAL,
    latency_p50  REAL,
    latency_p95  REAL,
    success_rate REAL,
    error_count  INTEGER,
    active_conns INTEGER,
    gpu_util     REAL,
    mem_used_gb  REAL
);

CREATE INDEX IF NOT EXISTS idx_snap_ts     ON metrics_snapshot(ts DESC);
CREATE INDEX IF NOT EXISTS idx_snap_source ON metrics_snapshot(source, ts DESC);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload    TEXT,
    ts         TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);

CREATE TABLE IF NOT EXISTS alert_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    metric     TEXT NOT NULL,
    operator   TEXT NOT NULL,
    threshold  REAL NOT NULL,
    window_s   INTEGER DEFAULT 300,
    is_active  INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         INTEGER REFERENCES alert_rules(id),
    triggered_value REAL,
    message         TEXT,
    resolved        INTEGER DEFAULT 0,
    fired_at        TEXT DEFAULT (datetime('now')),
    resolved_at     TEXT
);
"""


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(settings.DATABASE_URL)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA_SQL)
    await _db.commit()


async def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
