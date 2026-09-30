"""Persistent, bounded discretionary exploration between urgent objectives."""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .store import Store, now_utc


class FunBudget:
    def __init__(self, store: Store):
        self.store = store
        self.db = store.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS fun_settings (
                run_id INTEGER PRIMARY KEY REFERENCES runs(id),
                minutes_per_excursion INTEGER NOT NULL DEFAULT 30
                    CHECK(minutes_per_excursion BETWEEN 1 AND 240)
            );
            CREATE TABLE IF NOT EXISTS fun_excursions (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES runs(id),
                return_objective_id INTEGER NOT NULL REFERENCES objectives(id),
                title TEXT NOT NULL,
                reason TEXT NOT NULL,
                started_at TEXT NOT NULL,
                deadline_at TEXT NOT NULL,
                ended_at TEXT,
                outcome TEXT,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'finished', 'expired', 'interrupted'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_fun_excursion
                ON fun_excursions(run_id) WHERE status = 'active';
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(objectives)")}
        if "urgency" not in columns:
            self.db.execute("ALTER TABLE objectives ADD COLUMN urgency TEXT NOT NULL DEFAULT 'normal'")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO fun_settings(run_id) VALUES (1)")

    def set_budget(self, minutes: int) -> None:
        if not 1 <= minutes <= 240:
            raise ValueError("budget must be between 1 and 240 minutes")
        with self.db:
            self.db.execute("UPDATE fun_settings SET minutes_per_excursion = ? WHERE run_id = 1",
                            (minutes,))
        self.store.event("fun_budget_changed", {"minutes_per_excursion": minutes}, time.monotonic_ns())

    def set_urgency(self, objective_id: int, urgency: str) -> None:
        if urgency not in ("normal", "urgent"):
            raise ValueError("urgency must be normal or urgent")
        with self.db:
            cursor = self.db.execute("UPDATE objectives SET urgency = ? WHERE run_id = 1 AND id = ?",
                                     (urgency, objective_id))
        if cursor.rowcount != 1:
            raise ValueError(f"objective {objective_id} does not exist")
        self.store.event("objective_urgency_changed", {"objective_id": objective_id,
                                                        "urgency": urgency}, time.monotonic_ns())
        if self.urgent_objective_exists() and self.active() is not None:
            self.end("An urgent objective became active", "interrupted")

    def urgent_objective_exists(self) -> bool:
        return self.db.execute(
            "SELECT 1 FROM objectives WHERE run_id = 1 AND status = 'active' AND urgency = 'urgent' LIMIT 1"
        ).fetchone() is not None

    def active(self) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM fun_excursions WHERE run_id = 1 AND status = 'active'"
        ).fetchone()

    def start(self, title: str, reason: str, return_objective_id: int) -> int:
        if not title.strip() or not reason.strip():
            raise ValueError("title and reason are required")
        if self.active() is not None:
            raise ValueError("a fun excursion is already active")
        if self.urgent_objective_exists():
            raise ValueError("an urgent objective is active; resolve it before starting fun")
        objective = self.db.execute(
            "SELECT status FROM objectives WHERE run_id = 1 AND id = ?", (return_objective_id,)
        ).fetchone()
        if objective is None or objective["status"] != "active":
            raise ValueError("return objective must exist and be active")
        minutes = self.db.execute(
            "SELECT minutes_per_excursion FROM fun_settings WHERE run_id = 1"
        ).fetchone()[0]
        started = datetime.now(timezone.utc)
        with self.db:
            cursor = self.db.execute(
                """INSERT INTO fun_excursions(run_id, return_objective_id, title, reason, started_at, deadline_at)
                   VALUES (1, ?, ?, ?, ?, ?)""",
                (return_objective_id, title.strip(), reason.strip(),
                 started.isoformat(timespec="milliseconds"),
                 (started + timedelta(minutes=minutes)).isoformat(timespec="milliseconds")),
            )
        excursion_id = int(cursor.lastrowid)
        self.store.event("fun_started", {"excursion_id": excursion_id, "title": title,
                                         "return_objective_id": return_objective_id,
                                         "budget_minutes": minutes}, time.monotonic_ns())
        return excursion_id

    def end(self, outcome: str, status: str = "finished") -> int:
        if status not in ("finished", "expired", "interrupted"):
            raise ValueError("invalid excursion ending status")
        active = self.active()
        if active is None:
            raise ValueError("no fun excursion is active")
        with self.db:
            self.db.execute(
                "UPDATE fun_excursions SET status = ?, ended_at = ?, outcome = ? WHERE id = ?",
                (status, now_utc(), outcome, active["id"]),
            )
        self.store.event("fun_ended", {"excursion_id": active["id"], "status": status,
                                       "outcome": outcome}, time.monotonic_ns())
        return int(active["id"])

    def guard(self) -> None:
        active = self.active()
        if active is None:
            return
        if self.urgent_objective_exists():
            self.end("An urgent objective became active", "interrupted")
            raise ValueError("fun excursion interrupted by an urgent objective; reassess before acting")
        if datetime.now(timezone.utc) >= datetime.fromisoformat(active["deadline_at"]):
            self.end("Excursion budget elapsed", "expired")
            raise ValueError("fun excursion budget elapsed; reassess the return objective before acting")

    def status(self) -> dict[str, Any]:
        active = self.active()
        recent = self.db.execute(
            "SELECT * FROM fun_excursions WHERE run_id = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        remaining_seconds = None
        if active is not None:
            remaining_seconds = max(0, int((datetime.fromisoformat(active["deadline_at"])
                                            - datetime.now(timezone.utc)).total_seconds()))
        return {
            "minutes_per_excursion": self.db.execute(
                "SELECT minutes_per_excursion FROM fun_settings WHERE run_id = 1"
            ).fetchone()[0],
            "active": dict(active) if active else None,
            "remaining_seconds": remaining_seconds,
            "latest": dict(recent) if recent else None,
        }
