---
id: WB-071
title: Workspace order, Timing membership and a dedicated Synthesis workspace
category: workspaces
feature_sets: [FS3, FS1, FS2]
status: partial
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
related: [WB-015, WB-045, WB-063, WB-028, WB-072, WB-069, WB-009]
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
Fresh startup order is now **Overview, Testing, Waveforms, Timing**. The owner's
existing built-ins were reordered using revision-checked mutations while preserving
IDs, contexts, pins, tiles and extra workspaces. The Timing simulation catalog was
confirmed to be saved extra `tile-38`, not a stock preset member; it was hidden with
a targeted mutation, preserving Testing's catalog. Stock/exported membership is
covered by regression tests. Synthesis remains an inspector view, not a workspace.

## Scope
- Record/fix why simulation-catalog appears in Timing. Delivered policy: the default
  excludes it and the reported saved extra is hidden; custom extras are not globally banned.
- Owner's subsequent request delivers Overview, Testing, Waveforms, Timing now.
  Insert Synthesis before Timing when the dedicated Synthesis workspace is implemented.
- Add a Synthesis workspace preset built from the existing synthesis inspector
  views, with Session, run selector and Fit layout like Timing.
- Keep workspace IDs stable so saved layouts and pins survive the reorder.

## Out of scope
New synthesis evidence types, and source-tree reorganisation (WB-072).

## Acceptance criteria
- [x] Root cause of the simulation-catalog tile in Timing is recorded; the default excludes it.
- [x] Workspace switching and the palette list follow the approved four-workspace order; future Synthesis insertion remains pending.
- [ ] The Synthesis workspace opens on the selected run's synthesis evidence, with honest missing states.
- [x] Existing saved workspaces keep their IDs, tiles and pins after the targeted reorder.
- [ ] Default-layout restore and preset export cover the new preset.

## Partial delivery — Timing usability follow-on

Normal Inspect timing paths now opens the built-in Timing workspace in the current
window, with exact run/source and pin checks, instead of creating temporary tabs.
Explicit **Separate Timing investigation** remains available; **Close separate
investigation** is discoverable in its palette and protects shared/configured workspaces.
The paths column is wider, with detail/provenance stacked on the right.

The [delivery guide](../../timing_workspace_usability.md) records native navigation,
repeat/source-change, pin-conflict, separate/close and actual-a023 acceptance. The
saved reorder advanced revision 179→182 and retained the existing extra investigation.
No automatic deletion or full-layout reset was used.

**Remaining:** design and implement the dedicated Synthesis preset, its selected-run
behavior, restore/export coverage, and insertion before Timing. This ticket is not closed.

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
- [Timing workspace controls, order and acceptance](../../timing_workspace_usability.md)
- [Saved-extra diagnosis](../../timing_workspace_loading.md)
- [Agent implementation plan](../../timing_usability_preload_plan.md)
- [Preset registry](../../../terminal/workspaces/presets.ml)
- [Timing preset](../../../terminal/workspaces/timing.ml)
- [Synthesis inspection](../../synthesis_inspection.md)
- [Default layout restore](../../default_layout_restore.md)
