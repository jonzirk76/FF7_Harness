"""Agent-facing catalog of callable harness abilities and their evidence."""

from __future__ import annotations

from typing import Any


CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "name": "discover_ff7_windows",
        "command": "windows",
        "maturity": "live_verified",
        "requires": "A visible X11 window whose title contains FINAL FANTASY VII.",
        "effect": "Returns matching window IDs and titles.",
        "evidence": "Live launcher and game window discovery; docs/experiments.md.",
        "limits": "Window IDs change after launch or restart; reacquire them.",
    },
    {
        "name": "observe_window",
        "command": "observe --window-id ID --label TEXT",
        "maturity": "live_verified",
        "requires": "A current visible FF7 window ID.",
        "effect": "Stores a timestamped PNG and SQLite observation.",
        "evidence": "Launcher, title, menu, dialogue, and field frames in the run database.",
        "limits": "A destroyed or minimized window may not capture; a frame alone does not establish state.",
    },
    {
        "name": "focused_key_action",
        "command": "act --window-id ID --key KEY --seconds N",
        "maturity": "live_verified",
        "requires": "Visible game window; known or deliberately probed key; focus interruption acceptable.",
        "effect": "Activates the window, presses and releases one key, and stores before/after frames.",
        "evidence": "Focused Return reached New Game; Up changed menu selection and moved Cloud twice.",
        "limits": "Takes desktop focus. Window-replacement recovery has a regression test but awaits a second live transition test.",
    },
    {
        "name": "background_key_action",
        "command": "act --window-id ID --key KEY --seconds N --background",
        "maturity": "experimental",
        "requires": "Visible game window; another window may remain focused.",
        "effect": "Sends X11 key events to the target without calling windowactivate.",
        "evidence": "Editor stayed focused during an opening-sequence probe; no lasting game response confirmed.",
        "limits": "Do not rely on it for game control until a stable interactive-state test succeeds.",
    },
    {
        "name": "record_window_clip",
        "command": "clip --window-id ID --seconds N --fps F --width W",
        "maturity": "live_verified",
        "requires": "Visible FF7 window, FFmpeg with x11grab and libx264, X11 DISPLAY.",
        "effect": "Stores a low-resolution MP4 and timestamped SQLite clip metadata.",
        "evidence": "8-second 640x360 4-fps clip with 32 frames; opening sequence contact-sheet review.",
        "limits": "No audio; capture is window-targeted but needs a visible window. Duration is capped at 30 seconds.",
    },
    {
        "name": "read_run_state",
        "command": "status",
        "maturity": "live_verified",
        "requires": "Persistent run directory.",
        "effect": "Returns objectives, recent events, latest frame and clip, facts, fun state, and strategy state.",
        "evidence": "Reopened run after launcher and field experiments; persistence tests.",
        "limits": "Shows recent events and facts only; semantic retrieval and save reconciliation are pending.",
    },
    {
        "name": "manage_objectives",
        "command": "goal add|set|urgency ...",
        "maturity": "live_verified",
        "requires": "An explicit observable success condition for each new goal.",
        "effect": "Persists goal hierarchy, status, and urgency.",
        "evidence": "First-control goal was completed; platform-following goal is active in SQLite.",
        "limits": "Success and urgency are agent-assessed; no automatic game-state classifier yet.",
    },
    {
        "name": "record_fact",
        "command": "fact SUBJECT CLAIM --confidence C --source-event ID [--status verified]",
        "maturity": "live_verified",
        "requires": "An existing source event and justified confidence/status.",
        "effect": "Persists a provenance-linked hypothesis or verified fact.",
        "evidence": "Menu and first-platform movement facts linked to live observations; restart test.",
        "limits": "Verification is currently agent-assessed; contradiction handling and broader retrieval are pending.",
    },
    {
        "name": "bound_strategy",
        "command": "strategy start|assess|end|status ...",
        "maturity": "live_verified",
        "requires": "Active objective, stable strategy key, expected visible result, evidence-linked assessments.",
        "effect": "Persists a deadline and stall limit; retries of abandoned keys get less time and tolerance.",
        "evidence": "Opening wait and background-input attempts were abandoned; expired movement action was blocked.",
        "limits": "Assessment of progress/information is supplied by the agent; automatic scoring is pending.",
    },
    {
        "name": "manage_fun_excursion",
        "command": "fun start|end|status|budget ...",
        "maturity": "tested_only",
        "requires": "Active return objective and no active urgent objective.",
        "effect": "Persists a discretionary excursion with a default 30-minute deadline.",
        "evidence": "Persistence, urgency interruption, and expiry tests; no live excursion yet.",
        "limits": "Contextual urgency must be recognized and marked by the agent.",
    },
)


def catalog() -> dict[str, Any]:
    return {"schema_version": 1, "capabilities": list(CAPABILITIES)}
