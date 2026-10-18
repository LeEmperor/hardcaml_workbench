# Workspace composition, palette and tile presentation

Implemented and verified 2026-10-16. This is the frontend follow-on to the
aesthetics merge and completed FS2 milestone. The shared implementation plan is
[frontend_composition_plan.md](frontend_composition_plan.md).

**Subsequent owner-review refinements are delivered:** styled border titles and
palette, reduced vertical spacing, horizontal stages, compact six-domain Overview,
responsive run-selector capacity, and a dedicated Timing investigation workspace.
See [the current guide and evidence](frontend_refinement.md). The earlier layout
and vertical-padding descriptions below record the first composition slice.

## Where to change a workspace

Workspace definitions now have one source directory:

```text
terminal/workspaces/
  overview.ml         Overview membership and composition
  timing.ml           Timing membership and composition
  testing.ml          Generic tests plus FS2 simulation membership/composition
  common.ml           Shared tiles, presentation defaults and layout primitives
  definition.ml       Preset type, membership projection, Apply/Reset operations
  layout.ml           Responsive cell placement, extras and compact fallback
  presets.ml          Stable preset registry
  export_presets.ml   Machine-readable export used by the synthetic demo
```

This is a small OCaml library, `hardcaml_workbench_workspaces`, separate from the
terminal renderer. It declares composition, not provider processes or domain data.
`terminal/overview_layout.ml` is a compatibility shim; it no longer contains an
independent layout implementation. Terminal startup/default helpers and synthetic
seeding consume these definitions.

The current Overview definition is deliberately short:

```ocaml
open Common

let definition : Definition.t =
  { id = "overview"
  ; name = "Overview"
  ; tiles = [ navigation; session; selector; checklist
            ; tile "synthesis"; tile "timing"; tile "checks" ]
  ; layout = shell ~sidebar:[ checklist_leaf ]
      ~evidence:(List.map leaf [ "synthesis"; "timing"; "checks" ])
  }
;;
```

`tiles` specifies default membership, requested geometry and presentation defaults.
`layout` specifies Fit placement:

- `Stack`: wide panels stacked vertically.
- `Columns`: side-by-side regions.
- `Narrow`: a minimum-width sidebar rather than equal-width columns.
- `Leaf`: one occurrence of a tile kind, with minimum width/height and expansion
  weight. First unclaimed occurrence wins; additional copies remain extras.
- `shell`: quiet navigation above a compact Session/sidebar and a wider main
  column containing the shallow run selector and stacked evidence.

The initial run-selector cap is four entries. Its preferred geometry and Fit leaf
height are separate from that cap: raising the cap does not manufacture extra
screen rows. Adjust both the tile/leaf height and `visible_rows` when defining a
taller picker. Runtime row controls show as many rows as fit, up to the chosen cap.

Unclaimed duplicate/custom tiles are retained below the declared tree. If the
composition cannot fit, placement falls back to a grid and then the existing
focused-tile view. Zoom still displays the selected tile independently of Fit.
Requested-size mode still uses saved requested geometry rather than the Fit tree.

## Definitions versus saved arrangements

The daemon persists workspace registry state under its `--state-dir` as
`workspace-<digest>.sexp`, keyed by canonical project and execution environment.
That state includes tile identities, ordering, hidden state, requested geometry,
context linkage, pins and now a stable workspace `preset` ID.

- Preset IDs (`overview`, `timing`, `testing`) select composition, not workspace
  display names. Renaming Overview does not turn it into a generic grid.
- Old snapshots lacking the field infer known presets from their original names
  when loaded. Explicit `preset = None` is a custom arrangement; an unknown ID
  remains unknown/custom instead of silently choosing another preset.
- Fresh revision-zero registries are populated from definitions. Existing saved
  arrangements are not automatically reset or stripped of extra tiles.
- **Apply preset: Overview/Timing/Testing (add missing tiles)** sets the preset
  and adds missing default instances, preserving existing geometry, ordering,
  hidden state, pins, zoom and contexts.
- **Reset arrangement: … (preserve extras and pins)** additionally restores the
  matched preset tiles' requested geometry. It preserves hidden state and order;
  it is not a destructive delete-and-recreate or reset-all operation.
- **Restore default layout: … (hide extras)** is the explicit recovery option:
  show default occurrences, hide extras/duplicates, restore requested geometry,
  clear zoom and select/persist Fit after success. It preserves IDs, bindings,
  contexts and appearance. [Detailed controls and receipt semantics](default_layout_restore.md).

Rebuild/restart daemon and clients together after this change: the workspace wire
record/mutation vocabulary changed. Saved legacy S-expression snapshots are covered
by migration tests. This does not promise mixed old/new live client compatibility.

The synthetic seeder invokes
`_build/default/terminal/workspaces/export_presets.exe`; there is no independent
Python layout dictionary. `--preset-export PATH` or `WORKBENCH_PRESET_EXPORT`
selects another matching binary. Re-seeding adds missing defaults and selects the
reference run, but no longer hides your extra tiles or resets their geometry.

## Command palette

Open with **Space c c**. The palette is a centered panel capped at **88 columns ×
20 rows**, clamped to the viewport. The actual workspace or active FS1 inspector
remains visible underneath; Esc returns to that same view/selection.

| Input | Behavior |
| --- | --- |
| Text | Ranked, multiword fuzzy search over title, aliases and command ID |
| Tab / Down | Next result, keeping it visible |
| Shift-Tab / Up | Previous result |
| Enter | Execute selected available command against its captured target |
| Esc | Close and restore source view |
| Ctrl-U | Clear query |
| Backspace | Remove the last complete code point |

Selection clamps at the list ends. Matched characters are highlighted separately
from the selected row. Alias/ID-only matches show their matching field as context.
ASCII matching ignores case; other Unicode scalars match exactly. Query edits keep
the selected command by stable identity if it still matches. All field/form
execution, availability, paste and interrupt rules remain authoritative.

The pure matcher and floating/result rendering were adapted after inspecting Ches's
`palette/fuzzy`, `screen/palette_tile`, `screen/picker_text` and `screen/floating`.
Workbench does not acquire an editor/runtime dependency on the Ches checkout.
Long simulation/finalization input forms use the same bounded surface and retain
the query tail. Tiny terminals reclaim padding/chrome; not every help line can be
visible simultaneously there.

## Configurable tile chrome

Default Follow and project-scoped badges are hidden. A pinned tile shows
`PIN backend/run-id`, including when its header is hidden. Explicit badge Hidden
also hides that badge; it never changes the actual binding.

Focus a tile, open the palette, and use:

- **Toggle focused tile header / title / run reference / freshness / hints / frame / padding**.
- **Binding badge: Exceptions (pins only) / Always / Hidden**.
- **Run selector: More visible rows (+1) / Fewer visible rows (-1)**.
- **Reset presentation overrides (inherit)**.

These are client-local overrides keyed by exact tile identity. FS3 now persists
explicit header overrides, global appearance (including scheme), layout mode and
chrome across restart. Other tile overrides remain transient. Reset removes the
explicit header choice rather than freezing the resolved default; polling cannot
replay old choices. A replacement workspace session clears tile/workspace overrides.
Layouts and semantic bindings remain in the daemon-owned persisted registry. See
[current persistence and template semantics](fs3_adoption.md).

Precedence is:

```text
base defaults (including Compact/Comfortable density padding) and kind defaults
  -> compiled workspace-preset defaults
  -> explicit app overrides
  -> explicit workspace-ID overrides
  -> explicit tile-ID overrides
```

`terminal/tile_presentation.ml` owns the sparse policy; `None` inherits a field.
Workspace defaults live in `Common.presentation`/the individual definitions.
The live palette exposes tile overrides; app/workspace policy is available in the
host model and source definitions, not a new separate settings UI.

Compact contributes zero default padding; Comfortable contributes one cell where
space permits. Explicit preset/app/workspace/tile padding overrides win over that
density default. Navigation remains unpadded by default. Resetting a tile restores
the inherited policy rather than freezing whichever density was previously active.

Navigation is still the reusable `workspace-tabs` tile, with header/title/hints,
frame and padding quiet by default. Session is `live-status`. Instances in different
workspaces consume the same daemon project/registry facts; they do not start one
provider per tile or share focus/scroll accidentally. Backend semantic caches remain
shared; this does not claim cross-width rendered-frame caching.

Some recovery chrome (global footer and fallback header) remains host-owned and
toggleable. This slice does not turn every host pixel into an independently
persisted tile or add arbitrary nested floating windows.

## Typed status emphasis and synthetic evidence

`terminal/evidence_style.ml` supplies semantic spans from typed facts. Synthesis
freshness/metrics and terminal outcomes/checks use those spans rather than searching
raw strings for words. **Validated** describes freshness, not passing synthesis;
validated evidence can correctly contain a failed check or timing verdict.
Validated, pending and failed values have independently verified terminal colors.
Restrained appearance remains deliberately quieter.

Full source/report/log text is retained without keyword coloring or arbitrary
substring removal. Display controls affect known chrome rows, not original evidence.

New synthetic datasets use stage labels **Synthesis, Floorplan, Placement, CTS,
Routing, Signoff**. Synthetic identity remains in runs, reports and provenance.
Existing prepared demos contain copied provider code/evidence; use a fresh demo to
see the new labels rather than relabeling retained old evidence.

## Build and try

The ordinary `_build` daemon/client/exporter were rebuilt and tested together.
For future edits, from this checkout, with no other build running:

```sh
scripts/with-switch.sh dune build -j 2 \
  daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
```

Restart matching daemon/client binaries. For an existing workspace choose
**Apply preset: Overview (add missing tiles)** and **Layout: Fit tiles to window**.
Use Reset only if you also want default requested geometry restored. Extra saved
tiles remain visible and can consume space; hide them explicitly if desired.

For a fresh synthetic review, follow [synthetic_flow.md](synthetic_flow.md) using
this checkout and a new demo directory. No provider or EDA build is performed by
the setup script.

## Verification and retained evidence

Final full checks passed serially at `-j 2` in the normal `_build` directory:
`dune build @fmt @lint`, `dune runtest`, and `dune build`. Matching final source was
also built under `/tmp/opencode/frontend-presentation` and passed native acceptance:

| Check | Final evidence under `/tmp/opencode` |
| --- | --- |
| Frontend HTTP/PTY, **41 explicit checks**, plus screen assertions | `frontend-composition-359220233ca9/result.json` |
| FS2 actual Cyclesim/native HTTP/PTY | `fs2-native-me_1anb2/result.json` |
| Synthetic provider, real HTTP, checklist and FS1 PTY | `synthetic-flow-huttcbvv/` |
| Five-mode Ctrl-C/terminal restoration | `workbench-terminal-interrupt-v31tg44p/results.json` |

Frontend evidence includes ANSI/text/cell attributes and SVG captures at 80×24,
120×40 and 180×55, exact noncontiguous fuzzy underline positions, visible source
cells outside the overlay, Tab/Shift-Tab execution, Esc inspector restoration,
independent following/pinned synthesis views, typed status colors, actual chrome
controls, selector row limits and renamed-preset Apply/Reset with retained pins/extras.
Actual density commands change inherited padding and preserve explicit tile padding;
reset restores inheritance without registry changes.
Protocol/layout tests cover legacy migration and 1,280 sparse-membership/viewport
cases, including duplicates and unknown tiles. No physical flow was needed.

One coordinator run combining compilation and PTY exceeded its outer 120-second
tool budget (`frontend-composition-4217485f653e`). That incomplete run is not passing
evidence; its private daemon was stopped. A standalone rerun passed at
`frontend-composition-65388d67165f`. Final density-preservation review then found and
fixed a regression where explicit presentation plumbing had made the existing
density axis inert. The final evidence table above supersedes earlier runs and
includes actual density/override regression checks. Initial formatting differences
and intermediate agent compile/precedence findings were resolved before final
verification. Allow a 300-second harness budget for this multi-interaction test.

Reproduce against prebuilt normal binaries:

```sh
python3 -B scripts/test-frontend-composition.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe \
  --timeout 300
```

The test prepares only private state and stops only its own processes. Allow several
minutes; it performs many real input/repaint observations, not just synthetic frames.
Human aesthetic approval of the new arrangement remains a separate review step.
