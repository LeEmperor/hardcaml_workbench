---
id: WB-054
title: Contextual actions, breadcrumbs and help
category: presentation
feature_sets: [FS5, FS1, FS2]
status: delivered
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [actions, breadcrumbs, help, inspector]
depends_on: []
related: [WB-019, WB-024, WB-053, WB-063]
---

# WB-054 — Contextual actions, breadcrumbs and help

## Request
Add richer contextual actions, breadcrumbs and help, including an explicit action
to close an inspector. Requested size: **Unspecified**.

## Current baseline
The command palette, focused-tile actions, hint controls and Timing investigation
views already exist. Run/context and evidence identities are typed facts.
This request extends discoverability and context rather than creating command routing.

## Scope
- Expose useful actions and availability reasons for the focused view/selection.
- Add concise breadcrumbs showing actual workspace/view/evidence context.
- Make inspector close explicit and document predictable return-focus behavior.

## Out of scope
New evidence backends, a universal navigation framework or replacing the palette.
Contextual commands must reuse existing action identities where available.

## Acceptance criteria
- [x] Representative Timing and Testing views expose selection-appropriate actions.
- [x] Breadcrumbs retain exact provenance or accessible full identities when shortened.
- [x] Inspector close is visible in contextual help and keyboard-reachable.
- [x] Closing returns focus predictably without changing selection or run binding.
- [x] Unavailable actions explain why; hidden hints still have reachable help.

## Dependencies
Required: none; command, host and investigation foundations are delivered.
Related: [WB-019](WB-019-hideable-controls.md) coordinates hint recovery;
[WB-024](WB-024-context-link-label.md) aligns context wording;
[WB-053](WB-053-tile-local-tabs.md) adds optional local actions;
[WB-063](WB-063-testing-workspace.md) can adopt these controls independently.

## Estimate rationale
Eight incremental points cover a bounded set of contextual surfaces and focus/help
integration, excluding separately scoped tab or workspace redesign work.

## Assumptions and decisions needed
Choose representative actions and a compact breadcrumb vocabulary with owner review.
Dense packing remains the baseline; always-visible extra chrome is not assumed.

## Follow-up resolution — 2026-10-20

**Human-review status — 2026-10-21:** owner confirmed Testing and hints are fine.
Those portions are accepted. Clock/timing detail-view review remains blocked because
the current run failed signoff and has no corresponding published reports. Keep that
acceptance gap open without treating missing evidence as a UI regression. The proposed
dedicated Clocks workspace is separate future work, not a completion requirement here.


**Code fixes delivered and automatically verified.** Full-area explorer/artifact
breadcrumbs now render when hints and width permit without consuming evidence rows.
Timing help follows the focused Paths/Detail/Context pane. Testing `e`/`w` keys dispatch
unavailable-action explanations for missing attempt/detail/artifact selections.
Runnable Testing actions lead the contextual catalog using their original command
records and captured identities, without duplicates or extra submission-key allocation.

Eight focused regressions cover rendered screens, keyboard dispatch and production
selection-catalog ordering; all 97 host-view/workspace-host inline tests passed.
After the combined changes settled, full `dune build -j4`, `dune runtest -j4` and
`dune build -j4 @lint` passed. Interactive owner review of breadcrumb placement,
palette ordering and narrow-screen readability remains outstanding. The initial
review findings below are resolved by this follow-up.

## Initial completion review — 2026-10-20 (resolved by follow-up)

**Review-time verdict: partial; completion sign-off withheld.** Independent combined-tree build, tests and
lint passed. Code review found the following gaps in production routing/rendering:

- **P2: inspector breadcrumbs are not rendered.** `terminal/host_view.ml` appends
  breadcrumbs to the workspace footer, but full-area inspection explorers bypass that
  renderer and artifact browsers replace the workspace frame. Render the breadcrumb
  on those surfaces when hints and width permit. Test the actual rendered screens,
  rather than only the `breadcrumbs` helper's string.
- **P2: Timing help disagrees with focused-pane behavior.** With detail open and focus
  on Timing Paths, `main_hint_text` advertises `j/k scroll`, while
  `Timing_workspace.input` changes the path selection and can clear detail. Derive the
  help from both view mode and focused pane; test Paths, Detail and Context separately.
- **P2: unavailable artifact keys are silent.** In `terminal/main.ml`, Testing's
  `e`/`w` routing returns early when no artifact is selected, bypassing the contextual
  placeholders and their reasons. Dispatch an explanatory unavailable action and
  exercise the actual keyboard route with no attempt/artifact selected.
- **P3: runnable Testing actions lose contextual ordering.** Unavailable placeholders
  lead the palette, but the existing runnable rerun commands retain their original
  catalog positions when the placeholders disappear. Promote existing commands while
  preserving their identities; assert ordering with loaded attempts/cases.

Inspector-close routing has no identified blocking defect in this review. Interactive
visual acceptance remains outstanding, including dense/narrow layouts and contextual
reason readability. The initial implementation notes below are qualified by these
open findings; the review did not repeat the reported stale-script baseline comparisons.

## Initial implementation notes
- **Contextual action set** (`Workspace_host.contextual`, applied to the palette catalog
  and to key dispatch). Entries for the focused view lead the palette. An action that
  exists but can't run right now stays listed with a short `[reason]` and never
  disappears. A contextual entry never replaces an existing command ID. Existing
  actions are reused: `Browse_inspection`/`Browse_artifacts`, the explorer/Timing key
  handler, and the Testing rerun/export IDs.
  - Always: `inspector.close` "Close inspector (Space c x)". Reason when nothing is
    open: `no inspector open on the focused tile`.
  - Explorer or any Timing pane: `inspector.open-detail` (Enter), `inspector.refresh`
    (r), `inspector.stage` (t), `inspector.near` (v), `inspector.source` (d). Palette
    execution replays the same step as the key (`Inspector_input`). Reasons: `no run
    selected`, `no timing paths opened for this run; use Inspect timing paths`, `index
    not loaded yet`, `no rows match the current filter`, `no row selected`, `detail
    already open; Space c x closes it`, `near/violated applies to timing paths only`,
    `source view already open`.
  - Run-scoped tiles (not project-scoped or run-selector): `context.inspect-timing` and
    `context.artifacts` for the tile's own resolved run. Reason: `no run selected`.
  - Testing panes: when the real command is absent, `simulation.rerun-case` (r) and
    `simulation.rerun-failed` (f) are listed with `no attempt selected`, `attempt detail
    not loaded`, `no case selected` or `no failed cases in this attempt`. The Artifacts
    pane also lists `testing.artifact.export` (e) and `testing.artifact.waveform` (w)
    with `no artifact selected`. These placeholders run `Unavailable`, which only posts
    the reason, so pressing r/f now explains instead of doing nothing.
- **Explicit close / return focus** (`Workspace_host.close_inspector`). Space c x or
  the palette closes the focused tile's inspector in one step. Esc keeps its
  step-by-step behavior (detail → table → closed). An FS1 explorer or a
  reports/artifacts browser belongs to the focused tile, so focus stays on that tile.
  An open Timing Detail/provenance reader closes and focus returns to the workspace's
  `timing · paths` tile (if visible), where the path was selected. Selected row,
  artifact cursor, tile bindings, run selection and the registry are never changed.
  The existing generation counters fence late detail responses.
- **Breadcrumbs**: `workspace › view › run (stage)`, ASCII ` > ` in ASCII/Off icon
  modes. They come from the active workspace name, the focused tile, its resolved run
  (`display_run`) and its open inspector. Views: `inspect <domain>`,
  `reports/artifacts`, `timing paths` / `path detail` / `path provenance`, or the tile
  kind with hyphens as spaces (`session`, `workspaces`, `stage checklist`, …). The stage
  comes only from an open inspector/Timing view. A segment without a typed fact (no
  run, project-scoped Testing/Waveforms panes) is omitted. The crumb is right-aligned on
  the existing main hint row, only when it fits after a two-cell gap. It falls back to
  `view › run (stage)` (the workspace stays in the global header), and otherwise to
  nothing. Segments are dropped whole and never clipped. No new row; hidden main hints
  or a notice also hide it. Full run identity stays in the session tile, the inspector
  heading and Timing provenance. The global header `| Linked: Main |` is unchanged.
- **Help**: the main footer names only working controls. Timing panes with a view show
  `j/k select | Enter detail | / filter | Ctrl-C exit`, because q doesn't exit there.
  With a reader open they show `j/k scroll | Esc or Space c x close detail`. The
  explorer heading and the artifact browser rows add `Space c x close`. With every hint
  area hidden, the palette (Space c c) still lists `Close inspector (Space c x)` and the
  WB-019 restore commands.
- **Verification**:
  - `./scripts/with-switch.sh dune build -j20`, `dune runtest -j20` and `@lint` pass.
    `@fmt` shows only the known `waveform_data`/`waveform_probe` failures.
  - New `terminal/host_view.ml` tests (`WB-054 …`):
    - Timing availability reasons: no run, unopened index, empty filter, open detail.
    - Testing reasons and placeholders.
    - Close: Timing focus return, selection kept, unchanged registry, Space c x chord,
      explorer and artifact close keeping focus.
    - Breadcrumbs: full/short/none at exact widths, a 200- vs 60-column render, all
      three icon modes, no invented run/stage without a selection, inspector naming.
  - `scripts/test-frontend-refinement.py` extended with a real PTY check. It confirms
    the explorer advertises `Space c x close`, that Space c x closes it back to the
    Timing workspace with an identical registry, and that the palette shows `Close
    inspector (Space c x)` with `no inspector open on the focused tile`. These pass. The
    run then stops at the known pre-existing `refinement-overview-final` failure.
  - PTY scripts also passed: `test-fs3-adoption.py`, `test-frontend-composition.py`,
    `test-default-layout-restore.py`, `test-overview-sidebar.py`,
    `test-checklist-launch-workflow.py`, `test-launch-stage-consistency.py`.
    `test-terminal-indicators.py` stops at its known `cooperative-testing-default`
    failure.

## References
- [Frontend composition](../../frontend_composition.md)
- [Investigation contract](../../fs1_investigation.md)
- [Simulation contract](../../fs2_simulation_contract.md)
