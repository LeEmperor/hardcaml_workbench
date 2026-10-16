# Refined panels, compact Overview and Timing investigation

Implemented and verified 2026-10-16 following the owner's visual review of the
[composition delivery](frontend_composition.md). This is the current frontend guide;
the earlier record retains its historical verification. Shared implementation plan:
[frontend_refinement_plan.md](frontend_refinement_plan.md).

## Visible changes

### Panels and palette

- The Instrument skin uses rounded frames for both tiles and the command palette.
  Short Session and Run selector panels retain their frame when at least 4×3 cells
  are available. Other skins and ASCII/off modes retain their intentional treatments.
- Titles occupy the top border rather than a separate body row. A visible pinned
  identity remains independent of title/header visibility. Turning frames off uses
  a normal title row instead; very small surfaces degrade without exceeding bounds.
- Horizontal padding follows density/explicit padding preferences; default vertical
  inset is zero. Compact/Comfortable does not add two empty rows to short tiles.
- The workspace navigation allocation is one row plus the normal one-row gutter.
- The palette has a styled border title, colored prompt and visible caret, distinct
  selected-row and fuzzy-match emphasis, and a blank row before its footer. Tab /
  Shift-Tab / arrows / Enter / Esc retain their previous semantics and exact targets.

`terminal/panel.ml` owns shared frame/title geometry. Renderer and input paging use
the same geometry rather than subtracting independent guesses about headers/padding.

### Run selector

The wide selector uses actual available display-cell width for run identifiers,
rather than the fixed six-character head/tail utility abbreviation. Long names are
shortened only when necessary, preserving distinguishable beginnings/endings. Exact
identities remain unchanged for selection, pinning and RPCs. Status has a compact
aligned column; the selected run/cursor remains visible when browsing.

The border title reports **RUNS visible/total (CAP n)**. Thus two registered runs
with cap four are different from a clipped list. **Run selector: More visible rows
(+1)** now contributes a minimum-height request to Fit placement, so a fifth/sixth
entry can actually gain space. The request is bounded by terminal size and the
remaining workspace minimums; increasing it cannot manufacture rows when all runs
are already visible or force unbounded geometry. Requested-size mode still obeys
the saved geometry and viewport constraints. Reset presentation restores inheritance.

### Overview

The normal `overview` preset now has:

1. Quiet navigation.
2. Session and a wide Run selector.
3. A horizontal Stage checklist.
4. Paired **Synthesis / Timing**, **Placement / Routing**, and
   **Checks / Finalization** compact panels.

All six panels are exercised at 120×40. Narrower terminals retain the existing
responsive grid/focused-tile fallback; not every panel is forced into an unreadable
rectangle. Added custom/duplicate tiles remain extras and can consume additional
space. There is no silent culling of saved tiles.

The stage strip wraps when needed, retains selected-stage identity/status on a
separate line, and uses the same j/k → Enter detail → r plan workflow. Planning is
explicit and does not launch a run; use the normal palette Launch command afterward.
Hints can be enabled through the existing tile presentation control.

Compact panels are a **presentation mode over the existing typed summaries**, not
new providers. Synthesis keeps its explicit Cells/Details/Metrics/Evidence modes;
terminal-result details remain available. Aggregate area/slack/checks are labeled
aggregate, not attributed to an intermediate stage without evidence. Missing timing,
routing metrics or stage statuses stay unreported, never fabricated as zero/pass.
Validated freshness remains separate from completion and acceptance.

## Timing is an investigation workspace

**Inspect timing paths** now opens/focuses a workspace instead of a full-screen
tile-local timing overlay. The normal `timing` preset contains:

```text
Workspace navigation
Session                 Run selector

Timing · Paths          Timing · Selected path
                        Timing · Provenance
```

The list occupies the left investigation area. Detail and provenance are stacked
on the right, with independent scrolling. The default Timing preset no longer has
a tall stage checklist: stage/corner/group controls belong to the investigation.

### Opening and ownership

- A safe existing Timing arrangement for the exact captured run is reused.
- If context, pins, hidden Paths pane or incompatible zoom make reuse unsafe, a
  separate independent captured-run arrangement is created. Main and existing
  workspace pins/selection are not overwritten to make it fit.
- Pane instances share an explicit **client/workspace-local** path selection and
  query, not a process-global selected path. Other workspaces/clients keep their
  own investigation state. Domain indexes/details still use the shared daemon cache.
- Run/context/pin/source changes invalidate pending detail by workspace epoch,
  generation, exact run/domain/stage and source digest/row identity. Old data cannot
  reappear under a newly selected run.
- Opening cached evidence and browsing loaded rows do not re-extract it. A cold
  explicit Inspect, Enter on an uncached detail, stage change or Refresh uses the
  existing bounded read-only provider API; no EDA launch is implied.

### Controls

Focus **Timing · Paths** with Tab / Shift-Tab:

| Input | Effect |
| --- | --- |
| j/k or arrows | Select path locally |
| Enter | Request exact selected-path detail, or reuse its cached detail |
| `/` | Edit literal filter; Enter/Esc finishes filter mode |
| `s` | Cycle numeric/name sorting |
| `c` / `g` / `p` | Cycle actual corner / group / producer axes |
| `v` | Toggle existing near/violated view |
| `t` | Cycle inspection stage |
| `r` | Explicitly refresh current evidence |
| Tab / Shift-Tab | Change pane focus |
| Space c c | Palette over the current workspace |

In Detail/Provenance, j/k and the existing paging controls scroll that pane without
changing the selected path. Esc closes the selected detail reader locally; it does
not cancel a producer or switch back to Overview. Use workspace navigation to return.

Detail starts with four compact summary lines: path, reported value/status,
corner/group, and reported endpoints. The actual provider detail begins on line five.
Unreported endpoints remain `—`; they are not parsed heuristically from a label.
Raw source JSON, complete fields/names/IDs, execution references and digests live in
the scrollable Provenance pane. Full evidence is retained; provider text stays neutral
rather than being keyword-colored. Non-timing Clocks/Physical/Routing full-screen
inspectors remain available and are covered by regression checks.

## Source map

| File | What to adjust |
| --- | --- |
| `terminal/panel.ml{,i}` | Reusable border/title/frame geometry |
| `terminal/palette_view.ml` / `host_view.ml` | Palette framing, caret, footer and themed rendering |
| `terminal/workspaces/overview.ml` | Compact domain membership and horizontal composition |
| `terminal/workspaces/timing.ml` | Investigation pane membership and proportions |
| `terminal/workspaces/common.ml` / `layout.ml` | Shared tiles, one-row navigation and bounded responsive height requests |
| `terminal/overview_summary.ml{,i}` | Compact typed domain facts and provenance |
| `terminal/overview_tiles.ml` → `Stage_strip` | Horizontal stage model/rendering |
| `terminal/timing_workspace.ml{,i}` | Cooperative pane state, selection, input and content ordering |
| `terminal/workspace_host.ml` / `main.ml` | Captured opening, local ownership, request fences and runtime routing |

The source preset options `compact_summary` and `horizontal_stages` are sparse and
optional. Detailed tile kinds reuse their existing semantic modules. No new backend
scheduler or per-tile provider instance was introduced.

## Upgrade and try

The normal `_build` binaries were rebuilt together. Restart daemon/client to load
them; existing processes are not changed automatically. From this checkout, future
builds can remain small and serial:

```sh
scripts/with-switch.sh dune build -j 2 \
  daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
```

For a clean visual review use a **fresh synthetic demo directory** following
[synthetic_flow.md](synthetic_flow.md). It uses the same exported workspace definitions.
The seeded reference supplies summaries and populated timing indexes; Inspect timing
paths focuses the composed investigation.

Existing saved arrangements are preserved. **Apply preset** adds missing defaults;
**Reset arrangement** also restores requested sizes, but neither deletes or hides
old tiles. Thus an older Timing workspace may retain its summary/checklist extras.
Hide unwanted extras explicitly or use a fresh demo for the intended default layout.
Runtime appearance overrides remain client-local; this slice does not add persisted
presentation preferences or freeform drag-and-drop layout editing.

## Verification

Final normal-checkout `dune build @fmt @lint`, `dune runtest`, and `dune build` all
passed serially with `-j 2`. Agent builds used two jobs each, at most six concurrent
jobs; no physical tools, live demo state changes, or Git staging/commits/pushes.

Final post-polish native evidence under `/tmp/opencode`:

| Suite | Result / evidence |
| --- | --- |
| Refinement actual HTTP/PTY | **57 checks**: `frontend-refinement-e41e2e8d24b9/result.json` |
| Separate two-registered-run capacity | **12 checks**: `frontend-refinement-e41e2e8d24b9-two-runs/result.json` |
| Full composition regression | **44 checks**: `frontend-composition-25481b162854/result.json` |
| Synthetic HTTP/PTY launch/cancel | `synthetic-flow-y0hx51su/` |
| FS2 actual Cyclesim HTTP/PTY | **45 checks**: `fs2-native-n3pc_ana/result.json` |
| Terminal interrupt/restoration | **5/5**: `workbench-terminal-interrupt-49omjzgu/results.json` |

Evidence includes actual SVG/text/ANSI/cell-attribute captures at 80×24, 120×40,
180×55 and 240×80. Final Timing capture proves the complete six-line synthetic
detail begins on line five at120×40; Context scrolling exposes exact selected-row
source/fields/digest without changing Detail. Other checks cover palette footer gap,
short frames, long run strings, actual selector growth, all six stages, exactly-once
planning, independent panes/workspaces, protected Main/pins and run-change invalidation.

Earlier `frontend-refinement-fb0ee09a5c18` passed 49 checks before the final content
hierarchy polish; final evidence above supersedes those screenshots. Intermediate
agent host assertions/compile results in the plan are chronological notes, not
unresolved blockers. No claim of owner visual approval is made before that review.

Reproduce the final focused acceptance with prebuilt normal binaries:

```sh
python3 -B scripts/test-frontend-refinement.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe \
  --timeout 300
```
