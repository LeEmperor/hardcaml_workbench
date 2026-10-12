# Documentation archive

Historical plans, design snapshots and validation evidence live here. They are
not active requirements; use the current [architecture](../hardcaml_workbench_architecture.md),
[plan](../construction_phase_plan.md) and [rendering guide](../rendering.md).

## 2026-10-12 consolidation

The snapshots retain their bodies, including old statuses, proposals and code
references. Relative links inside them were written for their original location
directly under `docs/`; treat them as historical references, not a current
navigation tree. In particular, links to the removed scaf worktree are historical.
The files are grouped together to preserve same-document-set references where
possible. Active documents link to current locations.

| Snapshot | Why retained |
| --- | --- |
| [Architecture](2026-10-12/hardcaml_workbench_architecture.md) | Detailed original architecture, wire/driver decisions and first module/tile proposal |
| [September plan](2026-10-12/construction_phase_plan_2026_09.md) | Completed 1A–1C evidence and former scaf D1–D4 roadmap |
| [Initial replacement plan](2026-10-12/construction_phase_plan.md) | W0–W6 proposal before window/run/provider refinement |
| [Philosophy](2026-10-12/project_idea_and_philosophy.md) | Earlier product rationale, now consolidated into architecture |
| [Development evidence](2026-10-12/development.md) | Recorded build/install, protocol, fixture and human acceptance checks; old toolchain investigations |
| [Prettification](2026-10-12/prettification.md) | Original UI audit and P0–P5 proposal |
| [Fixed layout](2026-10-12/terminal_layout_spec.md) | Previous fixed-dashboard cell budgets and wireframes |
| [Baseline captures](2026-10-12/terminal_baseline_captures.md) | Capture method and old-screen observations |

The current development commands are in the repository [README](../../README.md).
Generated baseline files remain under `test/baselines/terminal/`; this consolidation
does not regenerate them or change the application.

When archiving another design, record its date and replacement here. Keep
completion evidence distinct from unimplemented proposals. Git history also
retains every committed version; this directory makes important snapshots easy
to find without reconstructing that history.
