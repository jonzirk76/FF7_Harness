"""Persistent strategy limits that tighten after repeated unproductive attempts."""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .store import Store, now_utc


class StrategyWatchdog:
    def __init__(self, store: Store):
        self.store = store
        self.db = store.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES runs(id),
                objective_id INTEGER NOT NULL REFERENCES objectives(id),
                strategy_key TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                started_at TEXT NOT NULL,
                deadline_at TEXT NOT NULL,
                stall_limit INTEGER NOT NULL,
                stall_count INTEGER NOT NULL DEFAULT 0,
                prior_abandons INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'succeeded', 'abandoned')),
                ended_at TEXT,
                conclusion TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_strategy
                ON strategies(run_id) WHERE status = 'active';
            CREATE TABLE IF NOT EXISTS strategy_assessments (
                id INTEGER PRIMARY KEY,
                strategy_id INTEGER NOT NULL REFERENCES strategies(id),
                source_event_id INTEGER NOT NULL REFERENCES events(id),
                assessed_at TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN ('progress', 'information', 'stalled')),
                note TEXT NOT NULL
            );
        """)

    def active(self) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM strategies WHERE run_id = 1 AND status = 'active'"
        ).fetchone()

    def start(self, strategy_key: str, expected_result: str, objective_id: int,
              seconds: int = 60, stall_limit: int = 3) -> dict[str, Any]:
        if not strategy_key.strip() or not expected_result.strip():
            raise ValueError("strategy key and expected result are required")
        if not 10 <= seconds <= 600:
            raise ValueError("strategy duration must be between 10 and 600 seconds")
        if not 1 <= stall_limit <= 10:
            raise ValueError("stall limit must be between 1 and 10")
        self.expire_if_needed()
        if self.active() is not None:
            raise ValueError("another strategy is active; assess or end it first")
        objective = self.db.execute(
            "SELECT status FROM objectives WHERE run_id = 1 AND id = ?", (objective_id,)
        ).fetchone()
        if objective is None or objective["status"] != "active":
            raise ValueError("strategy objective must exist and be active")
        key = strategy_key.strip().lower()
        prior = self.db.execute(
            """SELECT COUNT(*) FROM strategies WHERE run_id = 1 AND objective_id = ?
               AND strategy_key = ? AND status = 'abandoned'""",
            (objective_id, key),
        ).fetchone()[0]
        allowed_stalls = max(1, stall_limit - prior)
        allowed_seconds = max(10, seconds // (prior + 1))
        started = datetime.now(timezone.utc)
        with self.db:
            cursor = self.db.execute(
                """INSERT INTO strategies(run_id, objective_id, strategy_key, expected_result,
                   started_at, deadline_at, stall_limit, prior_abandons)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                (objective_id, key, expected_result.strip(),
                 started.isoformat(timespec="milliseconds"),
                 (started + timedelta(seconds=allowed_seconds)).isoformat(timespec="milliseconds"),
                 allowed_stalls, prior),
            )
        strategy_id = int(cursor.lastrowid)
        self.store.event("strategy_started", {
            "strategy_id": strategy_id, "strategy_key": key, "objective_id": objective_id,
            "expected_result": expected_result, "allowed_seconds": allowed_seconds,
            "stall_limit": allowed_stalls, "prior_abandons": prior,
        }, time.monotonic_ns())
        return {"strategy_id": strategy_id, "allowed_seconds": allowed_seconds,
                "stall_limit": allowed_stalls, "prior_abandons": prior}

    def end(self, status: str, conclusion: str) -> int:
        if status not in ("succeeded", "abandoned"):
            raise ValueError("strategy ending status must be succeeded or abandoned")
        active = self.active()
        if active is None:
            raise ValueError("no strategy is active")
        with self.db:
            self.db.execute(
                "UPDATE strategies SET status = ?, ended_at = ?, conclusion = ? WHERE id = ?",
                (status, now_utc(), conclusion, active["id"]),
            )
        self.store.event("strategy_ended", {"strategy_id": active["id"],
                                            "status": status, "conclusion": conclusion},
                         time.monotonic_ns())
        return int(active["id"])

    def expire_if_needed(self) -> bool:
        active = self.active()
        if active is None:
            return False
        if datetime.now(timezone.utc) >= datetime.fromisoformat(active["deadline_at"]):
            self.end("abandoned", "strategy deadline elapsed without confirmed success")
            return True
        return False

    def guard(self) -> None:
        if self.expire_if_needed():
            raise ValueError("strategy deadline elapsed; choose a different experiment")

    def assess(self, outcome: str, source_event_id: int, note: str) -> dict[str, Any]:
        if outcome not in ("progress", "information", "stalled"):
            raise ValueError("outcome must be progress, information, or stalled")
        active = self.active()
        if active is None:
            raise ValueError("no strategy is active")
        source = self.db.execute(
            "SELECT occurred_at FROM events WHERE run_id = 1 AND id = ?", (source_event_id,)
        ).fetchone()
        if source is None:
            raise ValueError("source event does not exist in this run")
        if datetime.fromisoformat(source["occurred_at"]) < datetime.fromisoformat(active["started_at"]):
            raise ValueError("source event predates this strategy")
        with self.db:
            self.db.execute(
                """INSERT INTO strategy_assessments(strategy_id, source_event_id, assessed_at,
                   outcome, note) VALUES (?, ?, ?, ?, ?)""",
                (active["id"], source_event_id, now_utc(), outcome, note),
            )
            if outcome == "stalled":
                self.db.execute("UPDATE strategies SET stall_count = stall_count + 1 WHERE id = ?",
                                (active["id"],))
            elif outcome == "information":
                self.db.execute("UPDATE strategies SET stall_count = 0 WHERE id = ?",
                                (active["id"],))
        self.store.event("strategy_assessed", {"strategy_id": active["id"],
                                               "source_event_id": source_event_id,
                                               "outcome": outcome, "note": note}, time.monotonic_ns())
        current = self.active()
        if outcome == "progress":
            self.end("succeeded", note)
        elif current["stall_count"] >= current["stall_limit"]:
            self.end("abandoned", "stall limit reached: " + note)
        elif datetime.now(timezone.utc) >= datetime.fromisoformat(current["deadline_at"]):
            self.end("abandoned", "strategy deadline elapsed: " + note)
        return self.status()

    def status(self) -> dict[str, Any]:
        active = self.active()
        latest = self.db.execute(
            "SELECT * FROM strategies WHERE run_id = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        remaining = None
        if active is not None:
            remaining = max(0, int((datetime.fromisoformat(active["deadline_at"])
                                    - datetime.now(timezone.utc)).total_seconds()))
        return {"active": dict(active) if active else None, "remaining_seconds": remaining,
                "latest": dict(latest) if latest else None}
