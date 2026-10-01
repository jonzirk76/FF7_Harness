"""Small CLI for observing a live window and persisting run state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from uuid import uuid4

from .capabilities import catalog
from .fun import FunBudget
from .io import AdapterError, capture, discover_windows, press
from .store import Store, now_utc
from .video import VideoError, latest_clip, record_clip
from .vision import dimensions, pixel_change
from .watchdog import StrategyWatchdog


DEFAULT_DATA = Path(".ff7-harness")


def record_frame(store: Store, window_id: int, label: str) -> dict[str, object]:
    png = capture(window_id)
    width, height = dimensions(png)
    previous = store.latest_frame()
    change = None
    previous_id = None
    if previous is not None and previous["window_id"] == window_id:
        old_path = store.root / previous["path"]
        if old_path.exists():
            change = pixel_change(old_path.read_bytes(), png)
            previous_id = previous["id"]
    frames_dir = store.root / "frames"
    frames_dir.mkdir(exist_ok=True)
    filename = f"{time.time_ns()}-{uuid4().hex}.png"
    path = frames_dir / filename
    temporary = frames_dir / (filename + ".tmp")
    temporary.write_bytes(png)
    temporary.replace(path)
    digest = hashlib.sha256(png).hexdigest()
    event_id = store.event("observation", {
        "label": label, "window_id": window_id, "path": str(path.relative_to(store.root)),
        "pixel_change": change,
    }, time.monotonic_ns())
    frame_id = store.add_frame(event_id, path, digest, width, height, window_id, previous_id, change)
    return {"frame_id": frame_id, "path": str(path), "width": width, "height": height,
            "pixel_change": change, "window_id": window_id}


def record_after_action(store: Store, window_id: int) -> dict[str, object]:
    try:
        return record_frame(store, window_id, "after action")
    except AdapterError as original_error:
        replacements = [window for window in discover_windows() if window.id != window_id]
        if len(replacements) != 1:
            raise original_error
        return record_frame(store, replacements[0].id, "after window transition")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FF7 Steam harness: window I/O and persistent memory")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA,
                        help="persistent run directory (default: .ff7-harness)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="initialize the persistent database")
    commands.add_parser("windows", help="list visible FF7 windows")
    commands.add_parser("capabilities", help="show available operations and verification status")
    commands.add_parser("status", help="show persisted run, objectives, and recent events")

    observe = commands.add_parser("observe", help="capture a game window")
    observe.add_argument("--window-id", type=int, required=True)
    observe.add_argument("--label", default="manual observation")

    clip = commands.add_parser("clip", help="record a short, low-resolution FF7 window video")
    clip.add_argument("--window-id", type=int, required=True)
    clip.add_argument("--seconds", type=int, default=8)
    clip.add_argument("--fps", type=int, default=4)
    clip.add_argument("--width", type=int, default=640)

    act = commands.add_parser("act", help="press one key and capture before and after")
    act.add_argument("--window-id", type=int, required=True)
    act.add_argument("--key", required=True, help="X11 key name, such as Up or Return")
    act.add_argument("--seconds", type=float, default=0.15)
    act.add_argument("--settle-seconds", type=float, default=0.25)
    act.add_argument("--background", action="store_true",
                     help="send X11 events to an inactive window; game support is unverified")

    goal = commands.add_parser("goal", help="create or update an objective")
    goal_sub = goal.add_subparsers(dest="goal_command", required=True)
    goal_add = goal_sub.add_parser("add")
    goal_add.add_argument("title")
    goal_add.add_argument("--success", required=True, help="observable success condition")
    goal_add.add_argument("--parent", type=int)
    goal_add.add_argument("--urgency", choices=("normal", "urgent"), default="normal")
    goal_set = goal_sub.add_parser("set")
    goal_set.add_argument("id", type=int)
    goal_set.add_argument("status", choices=("active", "done", "blocked", "abandoned"))
    goal_urgency = goal_sub.add_parser("urgency")
    goal_urgency.add_argument("id", type=int)
    goal_urgency.add_argument("urgency", choices=("normal", "urgent"))

    fun = commands.add_parser("fun", help="manage bounded discretionary exploration")
    fun_sub = fun.add_subparsers(dest="fun_command", required=True)
    fun_sub.add_parser("status")
    fun_budget = fun_sub.add_parser("budget")
    fun_budget.add_argument("minutes", type=int)
    fun_start = fun_sub.add_parser("start")
    fun_start.add_argument("title")
    fun_start.add_argument("--reason", required=True)
    fun_start.add_argument("--return-to", type=int, required=True, dest="return_to")
    fun_end = fun_sub.add_parser("end")
    fun_end.add_argument("--outcome", required=True)

    strategy = commands.add_parser("strategy", help="bound and assess a play strategy")
    strategy_sub = strategy.add_subparsers(dest="strategy_command", required=True)
    strategy_sub.add_parser("status")
    strategy_start = strategy_sub.add_parser("start")
    strategy_start.add_argument("key", help="stable key reused for the same strategy")
    strategy_start.add_argument("--objective", type=int, required=True)
    strategy_start.add_argument("--expected", required=True)
    strategy_start.add_argument("--seconds", type=int, default=60)
    strategy_start.add_argument("--stall-limit", type=int, default=3)
    strategy_assess = strategy_sub.add_parser("assess")
    strategy_assess.add_argument("outcome", choices=("progress", "information", "stalled"))
    strategy_assess.add_argument("--source-event", type=int, required=True)
    strategy_assess.add_argument("--note", required=True)
    strategy_end = strategy_sub.add_parser("end")
    strategy_end.add_argument("status", choices=("succeeded", "abandoned"))
    strategy_end.add_argument("--conclusion", required=True)

    fact = commands.add_parser("fact", help="store an observation-backed hypothesis")
    fact.add_argument("subject")
    fact.add_argument("claim")
    fact.add_argument("--confidence", type=float, required=True)
    fact.add_argument("--source-event", type=int, required=True)
    fact.add_argument("--status", choices=("hypothesis", "verified"), default="hypothesis")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "windows":
            print(json.dumps([window.__dict__ for window in discover_windows()], indent=2))
            return 0
        if args.command == "capabilities":
            print(json.dumps(catalog(), indent=2))
            return 0
        with Store(args.data_dir) as store:
            fun_budget = FunBudget(store)
            watchdog = StrategyWatchdog(store)
            if args.command == "init":
                store.set_assist_policy("No gameplay assists; normal in-game saves allowed")
                result: object = {"database": str(store.root / "memory.sqlite3"),
                                  "edition": "2026 rerelease", "fun": fun_budget.status()}
            elif args.command == "status":
                result = store.status()
                result["fun"] = fun_budget.status()
                result["latest_clip"] = latest_clip(store)
                result["strategy"] = watchdog.status()
            elif args.command == "observe":
                result = record_frame(store, args.window_id, args.label)
            elif args.command == "clip":
                watchdog.guard()
                result = record_clip(store, args.window_id, args.seconds, args.fps, args.width)
            elif args.command == "act":
                watchdog.guard()
                fun_budget.guard()
                if not 0 <= args.settle_seconds <= 5:
                    raise ValueError("settle-seconds must be between 0 and 5")
                requested_id = store.event("action_requested", {
                    "window_id": args.window_id, "key": args.key, "seconds": args.seconds,
                    "background": args.background,
                }, time.monotonic_ns())
                try:
                    before = record_frame(store, args.window_id, "before action")
                    press(args.window_id, args.key, args.seconds, focus=not args.background)
                    time.sleep(args.settle_seconds)
                    after = record_after_action(store, args.window_id)
                except Exception as exc:
                    store.event("action_failed", {"request_event_id": requested_id, "error": str(exc)},
                                time.monotonic_ns())
                    raise
                store.event("action_completed", {
                    "request_event_id": requested_id, "before_frame_id": before["frame_id"],
                    "after_frame_id": after["frame_id"], "pixel_change": after["pixel_change"],
                    "window_transition": after["window_id"] != before["window_id"],
                }, time.monotonic_ns())
                result = {"before": before, "after": after,
                          "note": "pixel_change measures visual difference, not player movement"}
            elif args.command == "goal":
                if args.goal_command == "add":
                    objective_id = store.add_objective(args.title, args.success, args.parent)
                    if args.urgency == "urgent":
                        fun_budget.set_urgency(objective_id, "urgent")
                    result = {"objective_id": objective_id, "urgency": args.urgency}
                elif args.goal_command == "set":
                    store.set_objective_status(args.id, args.status)
                    result = {"objective_id": args.id, "status": args.status}
                else:
                    fun_budget.set_urgency(args.id, args.urgency)
                    result = {"objective_id": args.id, "urgency": args.urgency}
            elif args.command == "fun":
                if args.fun_command == "budget":
                    fun_budget.set_budget(args.minutes)
                    result = fun_budget.status()
                elif args.fun_command == "start":
                    result = {"excursion_id": fun_budget.start(args.title, args.reason, args.return_to),
                              "fun": fun_budget.status()}
                elif args.fun_command == "end":
                    result = {"excursion_id": fun_budget.end(args.outcome), "fun": fun_budget.status()}
                else:
                    result = fun_budget.status()
            elif args.command == "strategy":
                if args.strategy_command == "start":
                    result = watchdog.start(args.key, args.expected, args.objective,
                                            args.seconds, args.stall_limit)
                elif args.strategy_command == "assess":
                    result = watchdog.assess(args.outcome, args.source_event, args.note)
                elif args.strategy_command == "end":
                    result = {"strategy_id": watchdog.end(args.status, args.conclusion),
                              "strategy": watchdog.status()}
                else:
                    result = watchdog.status()
            elif args.command == "fact":
                if not 0 <= args.confidence <= 1:
                    raise ValueError("confidence must be between 0 and 1")
                with store.db:
                    cursor = store.db.execute(
                        """INSERT INTO facts(run_id, created_at, subject, claim, confidence,
                           source_event_id, status) VALUES (1, ?, ?, ?, ?, ?, ?)""",
                        (now_utc(), args.subject, args.claim, args.confidence,
                         args.source_event, args.status),
                    )
                result = {"fact_id": cursor.lastrowid}
            else:
                raise AssertionError(args.command)
        print(json.dumps(result, indent=2))
        return 0
    except (AdapterError, VideoError, ValueError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
