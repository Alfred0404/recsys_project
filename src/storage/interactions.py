"""Append anonymous demo events to a local SQLite database."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                event TEXT NOT NULL,
                isin TEXT
            )
        """)


def insert_event(path: Path, session_id: str, event: str, isin: str | None) -> int:
    timestamp = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(path)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO interactions (timestamp, session_id, event, isin) VALUES (?, ?, ?, ?)",
            (timestamp, session_id, event, isin),
        )
        return cursor.lastrowid
