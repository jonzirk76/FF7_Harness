# FF7 Harness

An experimental harness for an AI agent to learn and play the **2026 Steam rerelease of the original FINAL FANTASY VII** on Linux. The intended design pairs persistent memory and reusable control skills with an LLM supervisor. This repository currently contains the first executable slice: X11 window discovery, screenshots, short keyboard inputs, an append-only event log, and durable objectives.

The repeatable play-and-build procedure is in [docs/workplan.md](docs/workplan.md). It uses only observations from the running game and the run database; no game guides or spoilers are used.

The [capability catalog](docs/capabilities.md) distinguishes live-verified commands from tested or experimental ones; `python3 -m ff7_harness.cli capabilities` returns its machine-readable form.

## Ground rules

- Use normal gameplay. Do not activate speed, encounter suppression, or battle boost.
- Saving through the game's normal save interface is allowed and should eventually be a reusable skill. A database record is not a game save.
- Record what happened after an input. A changed image alone does not establish that Cloud moved or that an objective succeeded.
- Keep the run directory across process and model restarts. The default `.ff7-harness/` directory is ignored by Git.
- Bind knowledge to a save checkpoint before relying on it after a game reload. The current version has no save reconciliation yet.
- Agents may spend a **30-minute fun budget per excursion** discovering novel experiences or doing side content when the recognized situation has no urgent objective. Enjoyment is a valid reason; the excursion need not produce measurable progress. Record the attraction, a return objective, and the outcome. Reassess urgency and the main goal before another excursion. Do not chain excursions solely to extend the budget.

## Local prerequisites

Python 3.10+, Pillow, X11, `xdotool`, and ImageMagick's `import` command. The game is launched normally through Steam. This adapter targets an existing visible window; it does not modify game files or read process memory.

On the development machine, the 2026 release is installed as Steam app `3837340`, the desktop is X11, and the required utilities are present. A live game window has not yet been tested.

## First use

Run these from the repository root:

```bash
python3 -m ff7_harness.cli init
python3 -m ff7_harness.cli windows
python3 -m ff7_harness.cli goal add "Reach the next field" --success "A distinct field scene is visible"
python3 -m ff7_harness.cli observe --window-id WINDOW_ID --label "starting scene"
python3 -m ff7_harness.cli act --window-id WINDOW_ID --key Up --seconds 0.15
python3 -m ff7_harness.cli status
```

After creating a main objective, a discretionary excursion can be recorded with:

```bash
python3 -m ff7_harness.cli fun start "Explore an interesting side path" --reason "Curiosity" --return-to 1
python3 -m ff7_harness.cli fun status
python3 -m ff7_harness.cli fun end --outcome "Returned after exploring the side path"
```

The default limit is 30 minutes per excursion; `fun budget MINUTES` changes it. `goal add` accepts `--urgency urgent`, and `goal urgency ID urgent` updates an existing goal. An active urgent goal prevents starting an excursion and interrupts one already in progress. Once the time limit is reached, the next `act` call stops and asks the agent to reassess the return objective. The budget and excursion survive process restarts. Current urgency is supplied by the agent; automatic recognition of timed events is future perception work.

`act` captures before and after, timestamps the request and result, releases its key even when interrupted, and reports a coarse image difference. It only targets the specified window ID. Key bindings must be established experimentally; `Up` is an example, not an assertion about the game's controls. Input changes focus to the target window.

An action can replace its window (the launcher does this when Play starts). The harness now discovers the replacement and records the after-frame against its new window ID. `act --background` sends X11 events to the specified window without activating it. In the observed opening sequence it produced no confirmed lasting change; focused input advanced the game. Normal `act` focuses the target window.

For animation context, `python3 -m ff7_harness.cli clip --window-id WINDOW_ID --seconds 8 --fps 4 --width 640` records a low-resolution MP4 of only the visible FF7 window. The clip and timestamps live in the persistent run directory; `status` shows the latest clip. This capture does not require the game window to be active, though it should be visible.

A strategy watchdog keeps passive waits and repeated actions bounded. Start a named strategy with `strategy start KEY --objective ID --expected "VISIBLE RESULT" --seconds 60 --stall-limit 3`, then assess observations with `strategy assess progress|information|stalled --source-event EVENT_ID --note "WHAT HAPPENED"`. `strategy status` shows the deadline. Once the deadline or stall limit is reached, the next action or clip is stopped until a new strategy is chosen. Reusing an abandoned key gives it less time and fewer tolerated stalls. Observations and evidence assessments remain available after a deadline so a result captured during an attempt can still be recorded.

To place the run elsewhere, add `--data-dir /path/to/run` **before** the subcommand on every invocation. Each run directory has one SQLite database and a `frames/` directory. SQLite records relative frame paths so moving the run directory preserves the links.

## Architecture roadmap

1. **I/O and evidence:** Current slice. Verify capture and controls with the live game. Add window reacquisition and handling for launch/loading.
2. **State perception:** Classify field, menu, dialogue, battle, loading, and unknown. Track character and landmarks with uncertainty. Detect camera motion separately from character motion.
3. **Navigation:** Learn local movement basis and exits from short probes, then store map transitions and routes. Field scenes, the world map, and vehicles need separate policies.
4. **Game skills:** Add operations with explicit preconditions, expected results, timeouts, and recovery: `interact`, `navigate_to`, `save_game`, menu actions, and battle actions.
5. **Supervisor and watchdog:** The first persistent watchdog now bounds named strategies. Add automatic progress signals and a supervisor that carries the objective, retrieved evidence, screenshot, and available skills into each decision.
6. **Save reconciliation:** Associate objectives and facts with observed save checkpoints, and branch or invalidate current-state beliefs after reloads.

The database separates events, frames, objectives, and hypotheses. Free-text retrieval and other game-state tables should be added when real observations show their required shapes. The event log remains the audit trail from which derived beliefs can be corrected.

## Experiment and commit practice

Make regular, descriptive commits as the harness develops. Explain the observed game state or experiment, what happened, and why that finding led to the change. Say clearly when a behavior has only been tested with a simulated frame or the launcher. Keep a short human-readable record in [docs/experiments.md](docs/experiments.md); the detailed screenshots and SQLite event history remain in the ignored run directory.
