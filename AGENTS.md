# Agent operating rules for this repository

Read [docs/workplan.md](docs/workplan.md) and [docs/capabilities.md](docs/capabilities.md) before a play or harness-development session. Run `python3 -m ff7_harness.cli capabilities` and `python3 -m ff7_harness.cli status` to see what is callable, what is verified, and where the game run stands. The long-term objective is to finish the installed original FINAL FANTASY VII through observed play and reusable harness skills.

- Use only the visible game and this run's recorded observations for game knowledge. Do not consult online guides or spoilers, or mine local assets/save files for unseen progression information.
- Preserve `.ff7-harness/` across sessions. Reconcile the current screenshot, objective, and last confirmed save before acting after a reset.
- Use short, observable actions. Record what happened; treat uncertain interpretations as hypotheses. Never infer success from an input event or raw image difference alone.
- No gameplay assists. Normal in-game saving is allowed. Honor the 30-minute fun budget when the recognized situation is not urgent.
- Turn repeated obstacles into small experiments, then implement and verify the smallest reusable skill that addresses the observed gap.
- Update `docs/experiments.md` and make descriptive commits that name the actual game state, experiment, result, and reason for code changes. State clearly when behavior remains untested in live gameplay.
