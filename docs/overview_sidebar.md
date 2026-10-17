# Dense Overview, live color schemes and planned-run tile

Implemented and verified 2026-10-16 following the owner's latest layout review.
This supersedes the paired-panel/horizontal-checklist Overview arrangement in the
[earlier refinement](frontend_refinement.md). Timing's investigation topology is
preserved. [Shared implementation plan](overview_sidebar_plan.md).

**Subsequent owner polish delivered:** planned-run now sits below a shorter
checklist in the left sidebar; right side has six domain summaries. Carbon/black
with bright headers is default, field labels are neutral with value-only status
colors, and Session run shortening uses available width. The next demo is prepared
on genuine retained ASIC example evidence; see [current controls and launch commands](real_asic_example_demo.md).
The older seven-right-panel/Slate-default description below records this first slice.

## Overview arrangement

```text
overview    timing    testing
┌ session ─────────────┐┌ synthesis ──────────────────────────┐
│ project/context      ││ compact typed facts                 │
└──────────────────────┘└─────────────────────────────────────┘
┌ runs ────────────────┐┌ timing ─────────────────────────────┐
│ selected/run list    ││ setup/hold summary                  │
└──────────────────────┘└─────────────────────────────────────┘
┌ stage checklist ─────┐┌ placement ──────────────────────────┐
│ synthesis            │└─────────────────────────────────────┘
│ floorplan            │┌ routing ────────────────────────────┐
│ placement            │└─────────────────────────────────────┘
│ cts                  │┌ checks ─────────────────────────────┐
│ routing              │└─────────────────────────────────────┘
│ signoff              │┌ finalization ───────────────────────┐
│                      │└─────────────────────────────────────┘
│                      │┌ planned-run ────────────────────────┐
└──────────────────────┘└─────────────────────────────────────┘
```

The sidebar takes approximately one third of the available width. Session and
Runs are short, with the vertical checklist below them. Each right-hand panel
owns the full remaining width; synthesis is above timing, not next to it. All
seven right panels are exercised at120×40. At smaller sizes the existing grid or
focused-tile fallback preserves access rather than overlapping/deleting tiles.

Frames now sit adjacent with zero blank-cell gutters by default. They remain
separate, non-overlapping rectangles; this is not a shared-border drawing engine.
Titles use lowercase host-generated names and no leading decorative dot/diamond.
Focus is indicated by frame styling. Selected list markers and pin identity remain.
Provider names, run IDs and evidence are not lowercased or rewritten.

Compact panels prioritize actual metric/check facts before repeated validated/stage
boilerplate. Stale, failed or unavailable warnings remain visible; a validated
summary does not imply engineering acceptance. The normal checklist shows stage
entries without all aggregate rows; Enter retains full selected-stage/aggregate
inspection. Existing detailed synthesis modes remain available.

## Configure proportions and packing

Edit **`terminal/workspaces/overview.ml`**:

| Setting | Current value / meaning |
| --- | --- |
| `sidebar_weight`, `main_weight` | `1`, `2`: full available width split1:2 |
| `session_height` | Minimum7 cells, including frame |
| `selector_height` | Minimum7 cells; live row-cap requests can increase it |
| `checklist_height` | Minimum10 cells; grows into remaining sidebar height |
| `summary_height` | Minimum5 cells for each right panel |

`Common.Weighted_columns` distributes the whole available width, respecting
descendant minimums; it does not merely distribute spare width after minimums.
`Layout.compute ?gutter` defaults to0; explicitly pass1 to restore a blank-cell gap.
Requested geometry and Fit composition remain separate. Live **Run selector:
More/Fewer visible rows** controls still request bounded actual height; in Overview
that growth is within the sidebar rather than adding a horizontal top band.

Sidebar run IDs use whatever width is actually available. Long identifiers may
still shorten in a one-third-width panel; zoom or exact inspection provides more
room. The `runs visible/total (cap n)` title distinguishes two available runs from
a clipped longer list. Raising the cap does not invent additional entries.

Only Overview membership/topology changes. Timing keeps its Session/selector top
band and Paths-left, Detail-over-Provenance investigation arrangement. Shared
lowercase titles, tighter packing and schemes apply there as well.

## Live color schemes

Open **Space c c**, search `color scheme`, and select:

| Palette command | Treatment |
| --- | --- |
| **Color scheme: Carbon** | Near-black neutral background, cool subdued accents |
| **Color scheme: Slate** | Neutral graphite/slate ground; new default |
| **Color scheme: Crimson** | Warm near-black ground with rose/crimson accents, inspired by Ches |
| **Color scheme: Neon** | Previous blue-black/vivid palette, retained for comparison |

Scheme is independent of the A–E skin, Vivid/Selective/Restrained color intensity,
icons and density. It changes the whole current client, including Timing, palette
and simulation views. Status roles remain distinguishable; original text and
semantic evidence are unchanged. Swapping schemes does not mutate the registry,
move tiles, select runs, change pins or invoke providers.

Schemes are currently client-local until restart. Slate is the default and the
fallback when loading an older appearance value without a scheme field. Crimson
was adapted from the read-only Ches `ui/theme.ml` palette; Workbench does not add a
runtime dependency on the Ches checkout. The palette/roles are implemented in
`terminal/appearance.ml` and `terminal/host_view.ml`.

## Planned-run tile

`planned-run` is a project-scoped view of the daemon's current plan preview, with
client intent/receipt fences. It is added at the bottom of Overview's right stack.

1. Focus **stage checklist** and choose a stage with j/k.
2. Press **r** to explicitly prepare the new run's plan.
3. The tile shows planning state and, once confirmed, the exact flow/profile/endpoint
   and assignments. Its first two body rows retain state and endpoint in short panels.
4. Focus **planned-run**, press **Enter** for complete metadata/plan identity/JSON;
   use j/k, arrows or brackets to scroll, and Esc to return.
5. Use the existing explicit **Launch** or **Launch and view in captured context**
   palette command to start execution.

**Ready means a plan is ready, not a queued job or an allocated execution.** The
tile never derives its identity from the historical run currently selected in
Overview. Changing that selection does not retarget the plan. There is no second
scheduler; rendering, scrolling, scheme changes and metadata inspection are read-only.

The subsequent [launch consistency fix](launch_stage_consistency.md) adds exact
durable submission/allocation tracking alongside this readiness. After Launch, the
tile reports its last matching producer lifecycle and run identity instead of
claiming no job was allocated. A retained plan may still be explicitly reusable.

States are **empty, pending, failed, stale and ready**. A new Plan immediately
invalidates local ready status, even for a retry of the same selection. Confirmation
requires a poll issued after the accepted Plan receipt. Late prior receipts/polls,
superseded commands and daemon/project changes cannot revive the old local intent.
Launch rechecks exact preview identity and readiness immediately before dispatch.
Old retained metadata, if present, is labeled unconfirmed rather than ready.

The backend exposes one shared project preview but no server observation revision
or remote retry generation/pending selection. Remote same-selection attempts cannot
be individually attributed. Lost local receipts remain failed/unconfirmed until an
explicit retry, and expired operation evidence makes a retained preview stale.
These limits are explicit rather than filled with guessed queue or run identities.

## Upgrade and try

Normal `_build` daemon/client/exporter are rebuilt. Restart matching daemon/client
processes to use them. No live user session or saved demo state was changed during
implementation.

For an existing arrangement, use **Apply preset: Overview (add missing tiles)**,
then **Layout: Fit tiles to window**. This adds planned-run while preserving pins,
contexts, hidden state, ordering and custom/duplicate extras. Extra tiles may consume
space; hide unwanted ones explicitly. Reset arrangement restores matched requested
geometry, not a destructive delete-and-recreate operation.

A fresh synthetic demo using [the launcher guide](synthetic_flow.md) shows the clean
default. Use a new directory name such as `synthetic-sidebar` if previous demo
directories already exist. No provider/physical build is required.

## Verification

Final normal-checkout format/lint, full test suite and full build passed serially
at `-j 2`. Agents used2 jobs each, at most6 concurrent jobs. The existing staged
work was preserved; this pass did not stage, commit, reset or merge anything.

Actual private HTTP/PTY evidence under `/tmp/opencode`:

| Suite | Result and evidence |
| --- | --- |
| Final normal-binary sidebar/schemes/plan acceptance | **106 checks**, `overview-sidebar-835bf5f34f02/result.json` |
| Agent integration run, matching source | **106 checks**, `overview-sidebar-fc8ea86f95ec/result.json` |
| Composition regression | **45 checks**, `frontend-composition-b5bc7783c26e/result.json` |
| Refinement regression | **96 checks**, `frontend-refinement-7dad2f910d25/result.json` |
| Two-run fixture | **12 checks**, `frontend-refinement-7dad2f910d25-two-runs/result.json` |
| Synthetic launch/cancellation | `synthetic-flow-d0emyda4/` |
| FS2 native Cyclesim | **45 checks**, `fs2-native-y2sbyizx/result.json` |
| Terminal interrupts/restoration | **5/5**, `workbench-terminal-interrupt-wbg9s_ny/results.json` |

Sidebar evidence includes SVG/text/ANSI/cell attributes at80×24,120×40,180×55,
four scheme captures in each of Overview/Timing, and `scheme-samples.json` with
actual background/accent colors. It verifies proportional layout, vertical stages,
stacked full-width summaries, lowercase unadorned titles, non-overlapping tight
frames and real sidebar-only row growth. Scheme tests preserve geometry, selected
runs/pins, registry and provider call counts.

Plan acceptance includes empty → explicit Placement plan → ready → full identity
inspection, historical-run selection independence, delayed CTS pending → injected
failure → retry-ready, disabled launch during failure, then exactly one explicit
launch allocating a separate execution. The real daemon clears preview when a new
Plan begins; retained-preview stale/supersession races are additionally covered by
pure tests, not claimed as native provider behavior.

Reproduce with prebuilt normal binaries (allow several minutes):

```sh
python3 -B scripts/test-overview-sidebar.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe \
  --timeout 600
```

Owner visual selection among schemes/layout refinements remains a separate review.
