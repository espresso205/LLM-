import aiosqlite
from .config import settings

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS nodes (
    node_id       TEXT PRIMARY KEY,
    host          TEXT NOT NULL,
    port          INTEGER NOT NULL,
    weight        REAL DEFAULT 1.0,
    status        TEXT DEFAULT 'healthy',
    registered_at TEXT DEFAULT (datetime('now')),
    last_heartbeat TEXT
);

CREATE TABLE IF NOT EXISTS scheduling_log (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id              TEXT NOT NULL,
    selected_node           TEXT NOT NULL,
    algorithm               TEXT NOT NULL,
    candidates              TEXT,
    decision_ms             REAL,
    active_conns_at_decision INTEGER,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strategy_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_log_created_at ON scheduling_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_log_selected_node ON scheduling_log(selected_node);

INSERT OR IGNORE INTO strategy_config VALUES ('current_strategy', 'round_robin');
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
