# Workspace definitions

**Current Testing composition:** `testing.ml` now uses cooperative simulation
catalog/attempt/case/detail/artifact/log panes and a compact Session/generic-tests/
execution column. Investigation selection is client/workspace-local, not ASIC Main;
the legacy `simulation` tile remains independently usable. Preset Apply preserves
old extras rather than silently removing them. [Controls/evidence](../../docs/testing_workspace.md).

Start with `overview.ml`, `timing.ml`, or `testing.ml` to change a workspace's
default tile membership and Fit composition. Shared tile defaults and the small
`Stack` / `Columns` / `Weighted_columns` / `Narrow` / `Leaf` vocabulary live in `common.ml`.

- `definition.ml`: stable preset ID, membership, presentation and Apply/Reset helpers.
- `layout.ml`: responsive placement, duplicate/custom extras and compact fallback.
- `presets.ml`: registered definitions; keyed by ID, not the workspace display name.
- `export_presets.ml`: exports those same definitions for the synthetic demo.

Requested tile geometry and Fit layout constraints are separate. For a taller run
selector, change its requested geometry and Fit leaf height as well as its
`visible_rows` presentation cap. A leaf claims the first unclaimed instance of its
kind; further copies and unfamiliar tiles remain visible as extras.

Saved live arrangements remain under the daemon's state directory as
`workspace-<digest>.sexp`. Changing these source definitions does not delete user
tiles, pins, contexts, ordering or hidden state. Apply adds missing tiles; explicit
Reset also restores matched requested geometry. Rebuild daemon/client/exporter
together, then select the desired preset from the palette.

**Restore default layout: … (hide extras)** is the stronger explicit recovery
operation: it atomically shows defaults, hides extras/duplicates, restores sizes
and clears zoom, then the initiating client selects/persists Fit after success.
IDs, bindings, contexts, selections and appearance are retained. Apply/Reset above
remain additive. `Definition.restore` uses the same definitions; no separate layout
table or implicit startup restoration is involved. [Controls](../../docs/default_layout_restore.md).

See [the full source map, customization guide and verification](../../docs/frontend_composition.md)
for display overrides, migration, palette controls and synthetic startup.

The [current sidebar polish](../../docs/real_asic_example_demo.md) makes Overview a
one-third sidebar (Session, Runs, vertical checklist, planned-run) and six-panel
right domain-summary stack. Checklist and planned-run divide the remaining sidebar
height with named minima/weights. `overview.ml` exposes the width weights
and minimum tile heights as source policy. `Weighted_columns` divides the full
available width by positive integer weights, respecting descendant minima; it does
not distribute just the spare width. Timing retains Paths/Detail/Provenance panes.
Optional `compact_summary` and `horizontal_stages` presentation fields control
content independently; short titles live in the shared border.
`Layout.compute` accepts bounded per-index minimum-height requests so the visible
run-row setting can increase actual selector height when the viewport permits.
Its optional `gutter` defaults to zero (adjacent, disjoint frame rectangles); use
one for a blank cell between tiles. Insufficient dimensions use the existing grid
or focused-tile fallback without changing saved geometry or membership.

FS3 portable templates carry the stable preset ID alongside exact membership and
requested geometry. `Definition.template` supplies the same definitions to CLI
`starter overview|timing|testing`; imports do not fill/reset sparse arrangements.
`Presets.bootstrap` initializes fresh Overview/Timing through a single idempotent
daemon operation, even after a CLI import has advanced registry revision. Legacy
saved arrangements are never mistaken for incomplete bootstrap. Custom layouts
honor generic Fit as well as requested-size mode. See [FS3 adoption](../../docs/fs3_adoption.md).
