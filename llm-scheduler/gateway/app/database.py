import aiosqlite
from .config import settings

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'user',
    is_active     INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS request_log (
    id                TEXT PRIMARY KEY,
    user_id           TEXT REFERENCES users(id),
    username          TEXT,
    model             TEXT,
    messages_json     TEXT,
    response_json     TEXT,
    status            TEXT DEFAULT 'pending',
    node_id           TEXT,
    total_tokens      INTEGER,
    latency_ms        REAL,
    error_message     TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    completed_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_req_user    ON request_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_req_created ON request_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_req_username ON request_log(username, created_at DESC);
"""


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(settings.DATABASE_URL)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA_SQL)
    await _db.commit()
    await _seed_admin()


async def _seed_admin() -> None:
    """Create the default admin account if it doesn't exist."""
    import uuid
    from .auth import hash_password

    row = await _db.execute_fetchall(
        "SELECT id FROM users WHERE username=?", (settings.ADMIN_USERNAME,)
    )
    if not row:
        hashed = hash_password(settings.ADMIN_PASSWORD)
        await _db.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (str(uuid.uuid4()), settings.ADMIN_USERNAME, hashed),
        )
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
