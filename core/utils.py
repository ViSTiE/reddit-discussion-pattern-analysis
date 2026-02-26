import sqlite3
import struct
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

import numpy as np

from core.config import config
from core.logger import get_logger

log = get_logger(__name__)

config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    subreddit TEXT,
    title TEXT NOT NULL,
    body TEXT,
    upvotes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL REFERENCES raw_posts(id),
    problem_summary TEXT NOT NULL,
    target_group TEXT,
    market_type TEXT,
    buyer_type TEXT,
    pain_score REAL DEFAULT 0,
    monetization_score REAL DEFAULT 0,
    complexity_score REAL DEFAULT 0,
    engagement_score REAL DEFAULT 0,
    frequency_score REAL DEFAULT 0,
    momentum_score REAL DEFAULT 0,
    final_score REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    problem_id INTEGER PRIMARY KEY REFERENCES problems(id),
    vector BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    centroid BLOB NOT NULL,
    size INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problem_clusters (
    problem_id INTEGER NOT NULL REFERENCES problems(id),
    cluster_id INTEGER NOT NULL REFERENCES clusters(id),
    PRIMARY KEY (problem_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_problems_post_id ON problems(post_id);
CREATE INDEX IF NOT EXISTS idx_problems_final_score ON problems(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_problems_created_at ON problems(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_posts_source ON raw_posts(source);
CREATE INDEX IF NOT EXISTS idx_raw_posts_created_at ON raw_posts(created_at);
"""


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
    log.info("Database initialized at %s", config.DB_PATH)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(config.DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def vector_to_blob(vec: np.ndarray) -> bytes:
    arr = vec.astype(np.float32)
    return struct.pack(f"{len(arr)}f", *arr)


def blob_to_vector(blob: bytes) -> np.ndarray:
    count = len(blob) // 4
    return np.array(struct.unpack(f"{count}f", blob), dtype=np.float32)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def post_exists(post_id: str) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM raw_posts WHERE id = ?", (post_id,)).fetchone()
        return row is not None
