# Play and build workplan

## Mission and boundaries

The long-term objective is to finish the installed 2026 Steam rerelease of the original FINAL FANTASY VII using the agent harness. Play from evidence available to a player: the visible game, its own menus and dialogue, and observations recorded during this run. Do not consult walkthroughs, story summaries, maps, videos, wikis, or other game guides. Do not inspect game assets or save files for unseen story or progression information. The current run uses no gameplay assists; normal in-game saving is allowed.

This is an experimental playthrough. A failed attempt is useful if it narrows what the agent believes and leaves a reusable observation. Do not invent success from an input event or an image difference. Completion requires visible end-of-game evidence recorded in the run, with the final objective marked done only after that evidence is reviewed.

## State that must survive a context reset

Keep the run directory (`.ff7-harness/` by default) intact. At the start of every session, read `python3 -m ff7_harness.cli capabilities` and `python3 -m ff7_harness.cli status`, inspect the latest screenshot and relevant recent events, and reconcile the visible game with the recorded objective and last known save. The database is the run's memory; `docs/experiments.md` records why harness code changed. A model's recollection is a hypothesis until it agrees with the current game observation.

Record or retrieve these items as capabilities are added:

| Memory | What it answers | Current state |
| --- | --- | --- |
| Timestamped observations and actions | What was actually seen and tried? | SQLite events, frame files, and low-resolution clips exist. |
| Objective tree and urgency | What is the agent trying to achieve, and how will it know? | Persisted objectives exist. |
| Facts, hypotheses, provenance | What is known, and why is it believed? | Basic fact rows exist; retrieval and revision need work. |
| Save checkpoints and branches | Which game state does a memory apply to? | Needs implementation and in-game validation. |
| Locations, landmarks, exits, routes | How can a known place be reached again? | Build after observing real field movement. |
| Encounters, menus, resources, failed attempts | Which operations and strategies worked? | Menu and movement facts plus bounded strategy attempts exist; deeper state needs play evidence. |
| Fun excursions | What drew the agent away, and when should it return? | Durable 30-minute excursions exist. |

## The normal play loop

1. **Observe.** Capture the current game window. Identify the mode (for example, title, field, dialogue, menu, battle, loading, or unknown), visible landmarks, party condition when available, and any signs of urgency. Give uncertain interpretations a confidence level.
2. **Choose a concrete objective.** State the current goal, a small next step, and an observable success condition. Mark urgency when the visible situation calls for immediate action. Keep the previous goal recorded when exploring a side path.
3. **Choose one bounded action or skill.** Specify the expected result and a timeout before acting. Use a short input pulse while controls or geometry are unknown. Reuse a tested skill once its preconditions match.
4. **Observe the result.** Capture after the action. Decide whether the expected result occurred, nothing happened, another mode opened, or the state is still unclear. Image change alone is not proof of movement or progress.
5. **Update memory.** Record new observations and attempts. Promote a hypothesis only when evidence supports it. Record a failed route or interaction so it is not retried without a changed premise.
6. **Continue or adapt.** Advance the objective when its success condition is visible. If progress stalls, run a small diagnostic experiment or improve the harness. If a discretionary excursion ends, reassess the saved return objective.

Keep action batches short enough that a transition, battle, dialogue, or unexpected event can interrupt them. A future supervisor should carry the objective and evidence into every model call, rather than regenerate purpose from a screenshot alone.

## When play becomes an experiment

Pause ordinary navigation when an action gives no confirmed effect, the mode is uncertain, a route repeats, or the agent cannot explain a transition. Write one question that a small experiment can answer, such as “does this key move the character in this field state?” or “is this edge an exit?” Record the starting frame, action parameters, resulting frame, interpretation, and remaining uncertainty. Vary one factor at a time where practical. A failed experiment should be preserved and should change the next attempt.

Use the following triggers for harness work:

| Repeated observation | Smallest useful harness improvement | Verification in play |
| --- | --- | --- |
| Key sends are ambiguous | Control calibration and key-release checks | A short press produces a repeatable, recognized result. |
| Screen moves but character motion is unclear | Character and landmark tracking | Distinguish character motion, camera motion, and animation. |
| The same transition is rediscovered | Location identity and exit graph | Return by a recorded route. |
| Dialogue or menu inputs are brittle | Mode-specific interaction skill | Enter, choose, and exit while confirming each state. |
| Battle choices require repeated guesswork | Battle state and resource tracking | Complete an encounter and explain the observed outcome. |
| Reload changes what is true | Save checkpoint reconciliation | Resume with correct objectives and facts. |
| Repeated actions yield no progress or information | Progress watchdog and recovery | Stop the loop, classify the cause, and choose a new strategy. |
| Retrieval omits relevant prior evidence | Structured queries, then text search | Retrieve the pertinent observation with provenance. |

Build only the part needed to resolve the observed gap. Test it against the trace that exposed the gap and one distinct case when available. Record the experiment and a descriptive commit before returning to play. Do not turn a single unverified interpretation into a hard-coded game fact.

## Database growth and retrieval

Keep raw observations and action outcomes append-only. Derived records should point back to their evidence and carry a status such as hypothesis, verified, or retracted. Store negative results too: a blocked route, ineffective key, or failed interaction changes the next decision. Give locations and routes stable IDs only after repeatable observations; screen coordinates may shift with camera motion. Associate current-state claims with a confirmed save checkpoint when checkpoint support exists, and revalidate them after a reload.

For each decision, retrieve a compact packet in this order: current objective and success condition; latest frame and mode estimate; matching save/checkpoint; current location and known exits; recent failed attempts; then relevant facts and experiments. Use structured SQLite queries first. Add full-text retrieval when the event history becomes too large to scan, and embeddings only if observed retrieval failures justify them. Retrieval must return provenance and uncertainty, not just a confident-sounding summary. The run database remains local and survives model/context resets.

## Session and recovery rules

- **Start:** Read run status; find the current game window; capture a fresh frame; compare it with the last observation and recorded save checkpoint. Resume the recorded objective only after that comparison.
- **During play:** Save through the game's interface when available and appropriate. Record the visible confirmation and associate later facts with that checkpoint once checkpoint support exists. Preserve surprising or irreversible states before experimenting when the game permits it.
- **Stall:** After several actions with neither progress nor new information, stop repeating the input. Check focus, mode, loading, collision, control mapping, and objective assumptions. Escalate with a screenshot and a concise trace if deterministic checks do not explain the state.
- **Urgency:** Timed prompts, active encounters, or another visibly time-sensitive situation suspend discretionary exploration. When urgency is uncertain, observe first and avoid starting a fun excursion until it is resolved.
- **Fun:** When nothing is urgent, an agent may spend up to 30 minutes per excursion on curiosity or side content. Enjoyment is sufficient reason. Record the attraction and return objective; end early if the situation changes. At expiry, reassess the main goal before another excursion.
- **Stop:** Record the last visible state, active objective, unresolved question, relevant frame/event IDs, and the last confirmed save. Do not mark an objective done simply because the session ended.

## Milestones and evidence gates

These are capability gates, not predictions about the game's plot. Work on the next gate only when play exposes the need.

Gate 1 was met on 2026-10-01: the game window was captured, New Game was selected, and two short Up inputs produced repeatable movement in the first field scene.

| Gate | Play experiment | Evidence required | Likely harness work |
| --- | --- | --- | --- |
| 1. Reach controllable play | From the known launcher, discover the game window and enter a controllable state. | A fresh in-game frame and a safe input with a confirmed effect. | Window reacquisition, input calibration, capture during transitions. |
| 2. Traverse one local area | Probe movement and a nearby boundary or exit. | Repeatable movement observations and one confirmed transition. | Mode detection, character/landmark tracking, local movement basis. |
| 3. Handle a changed mode | Follow the game into dialogue, menu, or battle as encountered. | Enter/act/exit trace with verified state changes. | Mode-specific skills and resource observations. |
| 4. Resume after a restart | Save normally, stop the harness, and reopen both. | Reconciled game state, objective, and applicable facts. | Checkpoint and branch-aware memory. |
| 5. Navigate and plan repeatedly | Revisit known places while pursuing observed objectives. | Recorded routes and recovery from at least one wrong turn. | Navigation graph, task manager, progress watchdog, retrieval. |
| 6. Finish the game | Continue the same loop through new modes and obstacles. | Visible completion evidence and a coherent run history. | Add only the skills demanded by play. |

## Immediate next experiment

The current run is at a first field scene on a platform. A visible dialogue asked Cloud to follow, and the persistent objective is to follow the group toward an observed transition or interaction. At the next session start, capture a fresh frame and reconcile it with the last movement observation; no game save has been confirmed. Use short directional probes to learn the local movement basis and identify a route, then build a reusable navigation operation from the traces. Focused Return and Up have confirmed effects in the observed states. Background input has no confirmed effect in this game and should remain experimental. Do not infer the route from outside knowledge.

Use `docs/experiments.md` for the human-readable result, leave frames and the SQLite database in the ignored run directory, and make a commit whose description connects the observation to any harness change.
