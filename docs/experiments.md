# Experiment notes

Record enough context to understand why a harness change was made. Include the game state or window, action or experiment, observation, conclusion, and verification. Distinguish observations from hypotheses. The runtime database and screenshots provide detailed evidence and are intentionally excluded from Git.

## 2026-09-30 — Launcher capture and persistent foundation

- **Context:** The 2026 Steam rerelease is installed locally as app `3837340` and launches through Proton on an X11 desktop.
- **Observation:** Steam opened a visible window titled `FINAL FANTASY VII Steam Edition LAUNCHER`. The X11 adapter discovered that window and saved a 1286×752 PNG with a timestamped SQLite observation.
- **Finding:** Window discovery and screenshot capture work for the launcher. Gameplay window capture, keyboard input, map transitions, and save behavior remain untested.
- **Harness response:** Added window-scoped screenshots and key actions, an append-only event record, persisted objectives and hypotheses, and a durable 30-minute discretionary exploration budget. The budget follows the agreed rule that no gameplay assists are used and normal in-game saving is allowed.
- **Verification:** Six local tests cover database persistence, action evidence, image difference, fun-budget persistence, urgency interruption, and budget expiry. No gameplay actions were sent during the launcher experiment.
