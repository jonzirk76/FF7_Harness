"""Durable run state and an append-only record of what the harness did."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    app_id INTEGER NOT NULL DEFAULT 3837340,
    edition TEXT NOT NULL DEFAULT '2026 rerelease',
    assist_policy TEXT NOT NULL DEFAULT 'undecided',
    save_marker TEXT,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    occurred_at TEXT NOT NULL,
    monotonic_ns INTEGER NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_run_order ON events(run_id, id);
CREATE TABLE IF NOT EXISTS frames (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE REFERENCES events(id),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    window_id INTEGER NOT NULL,
    previous_frame_id INTEGER REFERENCES frames(id),
    pixel_change REAL
);
CREATE TABLE IF NOT EXISTS objectives (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    parent_id INTEGER REFERENCES objectives(id),
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    success_condition TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'done', 'blocked', 'abandoned')),
    urgency TEXT NOT NULL DEFAULT 'normal' CHECK(urgency IN ('normal', 'urgent'))
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    created_at TEXT NOT NULL,
    subject TEXT NOT NULL,
    claim TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    source_event_id INTEGER REFERENCES events(id),
    status TEXT NOT NULL DEFAULT 'hypothesis' CHECK(status IN ('hypothesis', 'verified', 'retracted'))
);
"""


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "memory.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(objectives)")}
        if "urgency" not in columns:
            self.db.execute("ALTER TABLE objectives ADD COLUMN urgency TEXT NOT NULL DEFAULT 'normal'")
        self.db.execute("INSERT OR IGNORE INTO runs(id, started_at) VALUES (1, ?)", (now_utc(),))
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def event(self, kind: str, payload: dict[str, Any], monotonic_ns: int) -> int:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO events(run_id, occurred_at, monotonic_ns, kind, payload_json) VALUES (1, ?, ?, ?, ?)",
                (now_utc(), monotonic_ns, kind, json.dumps(payload, sort_keys=True)),
            )
        return int(cursor.lastrowid)

    def add_frame(
        self, event_id: int, path: Path, sha256: str, width: int, height: int,
        window_id: int, previous_frame_id: int | None, pixel_change: float | None,
    ) -> int:
        with self.db:
            cursor = self.db.execute(
                """INSERT INTO frames(event_id, path, sha256, width, height, window_id,
                   previous_frame_id, pixel_change) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, str(path.relative_to(self.root)), sha256, width, height,
                 window_id, previous_frame_id, pixel_change),
            )
        return int(cursor.lastrowid)

    def latest_frame(self) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM frames ORDER BY id DESC LIMIT 1").fetchone()

    def set_assist_policy(self, value: str) -> None:
        with self.db:
            self.db.execute("UPDATE runs SET assist_policy = ? WHERE id = 1", (value,))

    def add_objective(self, title: str, success_condition: str, parent_id: int | None = None) -> int:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO objectives(run_id, parent_id, created_at, title, success_condition) VALUES (1, ?, ?, ?, ?)",
                (parent_id, now_utc(), title, success_condition),
            )
        return int(cursor.lastrowid)

    def set_objective_status(self, objective_id: int, status: str) -> None:
        with self.db:
            cursor = self.db.execute(
                "UPDATE objectives SET status = ? WHERE run_id = 1 AND id = ?", (status, objective_id)
            )
        if cursor.rowcount != 1:
            raise ValueError(f"objective {objective_id} does not exist")

    def status(self) -> dict[str, Any]:
        run = dict(self.db.execute("SELECT * FROM runs WHERE id = 1").fetchone())
        objectives = [dict(row) for row in self.db.execute(
            "SELECT id, parent_id, title, success_condition, urgency, status FROM objectives WHERE run_id = 1 ORDER BY id"
        )]
        facts = [dict(row) for row in self.db.execute(
            """SELECT id, subject, claim, confidence, source_event_id, status
               FROM facts WHERE run_id = 1 AND status != 'retracted' ORDER BY id DESC LIMIT 20"""
        )]
        events = [dict(row) for row in self.db.execute(
            "SELECT id, occurred_at, kind, payload_json FROM events WHERE run_id = 1 ORDER BY id DESC LIMIT 10"
        )]
        for event in events:
            event["payload"] = json.loads(event.pop("payload_json"))
        latest = self.latest_frame()
        return {"run": run, "objectives": objectives, "facts": facts,
                "latest_frame": dict(latest) if latest else None,
                "recent_events": events}
