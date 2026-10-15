# F10 — Shared run contexts and linked selectors

Status (2026-10-15): **FS0 D1 contexts implemented and persisted**: shared Main,
multiple selectors, independent/relink, revision fences and per-tile run pins.
[Acceptance](../fs0_acceptance.md) covers real switching and exact context/pin
restoration; [terminal](../fs0_terminal.md) documents controls. Requirements below
remain normative; full multi-monitor convergence/adoption acceptance is later.

## User outcome

Overview, Timing and Resources normally inspect the same run. Change it in any
run-selector tile and every linked workspace follows. Detach one workspace to
investigate another run without changing the others; pin individual tiles for
smaller reference comparisons.

```text
Project session
  Main context → R43
    Overview workspace: large run selector + summary tiles
    Timing workspace: compact run selector + timing explorer
    Resources workspace: compact run selector + resource breakdown
  Independent context → R28
    Investigation workspace: its own selector + evidence tiles
```

## Ownership and actions

- A project-scoped context has stable identity, selected provider run (possibly
  none) and selection revision. It is UI/session state, not an ASIC run or job.
- Each workspace binds to a context. Main is the default shared context; display
  names can change without changing identity. Separate project sessions do not
  accidentally share selection just because both have a context called Main.
- A run-selector tile controls its workspace's bound context. Many selectors can
  control that same context across workspaces/windows; none is the primary writer.
- **Select run:** update the shared context once. All following views adopt that
  run; no tool launch, cancellation, focus change or background selection stealing.
- **Make independent:** allocate a context initialized to the current selected run
  and rebind only that workspace. Keep any existing per-tile pinned references.
- **Link to context:** rebind to an existing project context and immediately adopt
  its selected run. Start with Main/independent; richer named groups can follow.
- Hiding/closing selectors and moving tiles do not own context lifetime. Context
  cleanup must preserve references held by remaining workspaces and saved sessions.

## Shared versus local state

Share selected-run identity/revision only. Each tile owns geometry, focus, filter,
browsing cursor, expansion and scroll. A remote selection must be indicated even
when filtered/offscreen, without forcing another user's browsing position to jump.
Exact navigation-versus-activation keys are settled with the command/input design.

The host serializes selection changes through one authoritative session-state
transition path. Consumers use revisions to converge on the latest accepted
selection; late data responses cannot revert it. The concrete transport/storage
mechanism is an implementation choice, not a second provider protocol.

Queries bind to context identity/revision plus explicit run/query/result identity.
Changing selection, unlinking or relinking invalidates obsolete in-flight views.
Uncached data shows loading/unavailable for the new run, never old values under a
new label. Shared context does not require all modules to load simultaneously.

Context switching resolves references into [F11's summary cache](run_summary_cache.md),
not a full result reparse per tile. Selected/pinned small summaries receive retention
priority within budgets. A warm R1→R2→R1 switch reuses unchanged resident entries;
late data can fill its own cache entry without changing another context's display.

## Relationship to evidence and persistence

- Following tile → workspace context → selected run.
- Pinned tile → explicit evidence reference, independent of context selection.
- Move following tile to another workspace → follow destination context.
- Move pinned tile → keep reference. Move whole workspace → keep context binding.
- Persist linkage separately from layout geometry. Restoring two workspaces linked
  to Main restores one shared context, not two independent copies of its run ID.
- Templates describe intended linking/defaults; session snapshots retain concrete
  IDs/selections. Saved missing runs remain unavailable rather than silently replaced.
- Snapshot pinning/retention detail remains D3; a context is never a frozen result.

## Acceptance

Create large/compact selectors in two workspaces linked to Main. Select A then B
from either selector and verify all following tiles update, without shared scroll
or focus. Hide Overview's selector and continue from the other. Detach Timing at B,
change Main to A, verify Timing remains B; relink and verify it adopts A. Pinned
references remain unchanged. Exercise delayed queries across every transition.
Repeat across two windows in M5 and restore linkage after restart in M3.

Dependencies: F04 host/workspaces, F05 run identity, F02 revisioned queries. No ASIC
tool execution is needed for fixture-backed context acceptance.
