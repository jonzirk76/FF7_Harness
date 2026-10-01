# Harness capability catalog

Run `python3 -m ff7_harness.cli capabilities` for the machine-readable catalog. Its source is `ff7_harness/capabilities.py`. Read it alongside `status` at the start of a session, because a callable command may still have unverified behavior in the game.

Maturity labels:

- **`live_verified`** — exercised against the installed game or its launcher for the stated effect.
- **`tested_only`** — automated tests pass; no live gameplay use yet.
- **`experimental`** — callable, with no confirmed game effect or an unresolved limitation.

| Capability | Command family | Current maturity | Key limit |
| --- | --- | --- | --- |
| Find FF7 windows | `windows` | Live verified | Reacquire IDs after launch or restart. |
| Capture screenshots | `observe` | Live verified | A destroyed or minimized window may fail. |
| Focused key input | `act` | Live verified | Takes desktop focus; use short pulses and verify the result. |
| Background key input | `act --background` | Experimental | No lasting game response has been confirmed. |
| Low-resolution window video | `clip` | Live verified | No audio; needs a visible FF7 window. |
| Persistent run summary | `status` | Live verified | Recent evidence only; full retrieval remains future work. |
| Objective manager | `goal` | Live verified | Success and urgency still need agent judgment. |
| Evidence-linked facts | `fact` | Live verified | Verification and contradictions need agent judgment. |
| Strategy watchdog | `strategy` | Live verified | Agent supplies progress/information assessments. |
| Fun excursion budget | `fun` | Tested only | Contextual urgency must be recognized by the agent. |

When an experiment changes a capability's maturity or limitation, update the code catalog and this summary in the same descriptive commit. Keep game observations and event IDs in `docs/experiments.md` and the persistent run database. Do not mark a capability live verified on the strength of a unit test alone.
