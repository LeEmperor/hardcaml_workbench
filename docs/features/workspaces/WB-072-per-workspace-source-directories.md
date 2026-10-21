---
id: WB-072
title: Per-workspace source directories
category: workspaces
feature_sets: [FS3]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [source-layout, refactor, workspaces]
depends_on: []
related: [WB-071, WB-053]
---

# WB-072 — Per-workspace source directories

## Request
Owner note, 2026-10-20: in the project's file hierarchy, the different workspaces
should be split into their own directories.

## Current baseline
Workspace *definitions* already live in `terminal/workspaces/` (`overview.ml`,
`timing.ml`, `testing.ml`, `waveforms.ml`). Their *implementations* sit flat in
`terminal/`: `timing_workspace.ml`, `testing_workspace.ml`, `waveform_*.ml`,
`simulation_*.ml`, `synthesis_view.ml`, `overview_tiles.ml`. Workspace-specific
dispatch and rendering are also spread through `main.ml` (~6.9k lines),
`host_view.ml` (~7.6k) and `workspace_host.ml` (~5.1k).

## Scope
- One directory (dune library or include subdir) per workspace: definition, tiles,
  view state, input handling and its tests together.
- Shared host, palette and layout code stays in a common location.
- Move workspace-specific branches out of `main.ml`, `host_view.ml` and `workspace_host.ml`
  behind a small per-workspace interface where practical.
- Behaviour-preserving: no UI or protocol changes.

## Out of scope
New workspaces (WB-071), tile-local tabs (WB-053) and protocol/daemon layout.

## Acceptance criteria
- [ ] Each workspace's code and tests live under its own directory.
- [ ] `dune build`, `dune runtest`, `@fmt`, `@lint` and the PTY acceptance scripts are unchanged by the move.
- [ ] `terminal/workspaces/README.md` and source maps in docs point at the new paths.
- [ ] No new dependency cycles; the shared host does not depend on individual workspaces.

## Dependencies
None required. Schedule it when no parallel agent work is touching `terminal/`,
because it moves files that almost every terminal ticket edits. Doing WB-071 first
avoids moving code that is about to change.

## Estimate rationale
13 points, medium confidence: moving files is mechanical; untangling the
workspace-specific branches in the three large host files is not.

## Assumptions and decisions needed
- Dune `include_subdirs` within one library versus one library per workspace.
- Directory naming, e.g. `terminal/workspaces/<name>/`.

## References
- [Workspaces README](../../../terminal/workspaces/README.md)
- [Frontend source map](../../frontend_composition.md)
