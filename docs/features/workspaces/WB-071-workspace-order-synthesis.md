---
id: WB-071
title: Workspace order, Timing membership and a dedicated Synthesis workspace
category: workspaces
feature_sets: [FS3, FS1, FS2]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [workspaces, presets, synthesis, ordering]
depends_on: []
related: [WB-015, WB-045, WB-063, WB-028, WB-072]
---

# WB-071 — Workspace order, Timing membership and a dedicated Synthesis workspace

## Request
Owner notes, 2026-10-20:
- The simulation-catalog tile should not be in the Timing workspace.
- Timing should be further along the line, with a dedicated Synthesis workspace
  before it.
- Front-end tools come first: Testing and Waveforms should be squared away before
  the flow-related workspaces.

## Current baseline
Registered presets are `Overview, Timing, Testing`, then `Waveforms`
(`terminal/workspaces/presets.ml`). The Timing preset (`timing.ml`) contains no
simulation-catalog tile. The reported tile is most likely a saved-layout extra:
Apply is additive and unfamiliar tiles stay visible as extras; Restore default
layout hides them. That cause is unconfirmed. Synthesis is an inspector view
(`synthesis_view.ml`), not a workspace.

## Scope
- Reproduce why simulation-catalog appears in Timing. If it is a saved extra, decide
  whether Timing should reject simulation-kind extras, or only fix the default.
- Reorder presets to: Overview, Testing, Waveforms, Synthesis, Timing (proposed).
- Add a Synthesis workspace preset built from the existing synthesis inspector
  views, with Session, run selector and Fit layout like Timing.
- Keep workspace IDs stable so saved layouts and pins survive the reorder.

## Out of scope
New synthesis evidence types, and source-tree reorganisation (WB-072).

## Acceptance criteria
- [ ] Root cause of the simulation-catalog tile in Timing is recorded; the default no longer contains it.
- [ ] Workspace switching and the palette list follow the new order.
- [ ] The Synthesis workspace opens on the selected run's synthesis evidence, with honest missing states.
- [ ] Existing saved workspaces keep their IDs, tiles and pins after upgrade.
- [ ] Default-layout restore and preset export cover the new preset.

## Dependencies
None required. WB-072 moves the same definitions into per-workspace directories;
doing WB-071 first avoids moving code that is about to change.

## Estimate rationale
13 points, medium confidence: reordering is small; the Synthesis preset and the
extra-tile investigation hold most of the work.

## Assumptions and decisions needed
- Is "squared away first" only the workspace order, or also a priority statement?
  It is recorded as both: Testing/Waveforms tickets are listed ahead of flow work in
  the catalog review priorities.
- Which synthesis panes make up the Synthesis default (summary, cells, evidence)?

## References
- [Preset registry](../../../terminal/workspaces/presets.ml)
- [Timing preset](../../../terminal/workspaces/timing.ml)
- [Synthesis inspection](../../synthesis_inspection.md)
- [Default layout restore](../../default_layout_restore.md)
