# Experiment notes

Record enough context to understand why a harness change was made. Include the game state or window, action or experiment, observation, conclusion, and verification. Distinguish observations from hypotheses. The runtime database and screenshots provide detailed evidence and are intentionally excluded from Git.

## 2026-09-30 — Launcher capture and persistent foundation

- **Context:** The 2026 Steam rerelease is installed locally as app `3837340` and launches through Proton on an X11 desktop.
- **Observation:** Steam opened a visible window titled `FINAL FANTASY VII Steam Edition LAUNCHER`. The X11 adapter discovered that window and saved a 1286×752 PNG with a timestamped SQLite observation.
- **Finding:** Window discovery and screenshot capture work for the launcher. Gameplay window capture, keyboard input, map transitions, and save behavior remain untested.
- **Harness response:** Added window-scoped screenshots and key actions, an append-only event record, persisted objectives and hypotheses, and a durable 30-minute discretionary exploration budget. The budget follows the agreed rule that no gameplay assists are used and normal in-game saving is allowed.
- **Verification:** Six local tests cover database persistence, action evidence, image difference, fun-budget persistence, urgency interruption, and budget expiry. No gameplay actions were sent during the launcher experiment.

## 2026-10-01 — Launcher transition and opening sequence

- **Starting state:** The launcher showed a Play button. A fresh capture matched the prior launcher image.
- **Action and observation:** A short Return press activated Play. The launcher window disappeared and a new `FINAL FANTASY VII Steam Edition` window appeared at 3840×2160. The original `act` command recorded a failed after-capture because it still targeted the destroyed launcher window; a direct observation of the new window showed the game title screen.
- **Harness response:** When the original window disappears after input and exactly one new FF7 window is visible, capture the replacement and record a completed action with a window transition. Added an explicit experimental background-input mode.
- **Animation experiment:** FFmpeg captured only the game window while the editor stayed active. An 8-second 640×360 clip at 4 fps produced 32 frames, persisted in SQLite and the run directory. The sequence showed continuing opening credits rather than a frozen state.
- **Input comparison:** Background Return kept the editor focused but produced no confirmed lasting change during the opening sequence. Focused Return brought up the New Game menu. A focused Up press moved its cursor to New Game, and focused Return started the opening scene. Background game input remains unverified and should not be relied on.
- **Watchdog experiment:** A short clip showed the same opening-credit sequence after a bounded wait, so `wait_for_opening` was abandoned. The background-input attempt was also abandoned after no lasting menu appeared. The persistent watchdog now lowers both time and stall tolerance when the same strategy is retried; its deadline blocked an expired movement probe before a key was sent.
- **First control:** The opening scene reached a platform dialogue asking the character to follow. Focused Return closed the dialogue. Two 0.2-second focused Up presses then moved Cloud repeatedly against fixed platform scenery. The first-control objective was marked done, and following the visible route was recorded as the next goal. No game save has been confirmed yet.
- **Harness response:** Added low-resolution window clips with SQLite metadata, a provenance-linked strategy watchdog, visible verified facts in `status`, and a regression test for the launcher-to-game window replacement.
