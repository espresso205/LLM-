"""SQLite database setup for the inference node."""
import aiosqlite
from .config import settings

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS request_log (
    id                TEXT PRIMARY KEY,
    request_body      TEXT,
    response_body     TEXT,
    status            TEXT,
    latency_ms        REAL,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    model             TEXT,
    error_message     TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS metrics_1m (
    bucket        TEXT PRIMARY KEY,
    request_count INTEGER DEFAULT 0,
    error_count   INTEGER DEFAULT 0,
    total_latency REAL    DEFAULT 0,
    max_latency   REAL    DEFAULT 0
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
