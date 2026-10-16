# Workspace definitions

Start with `overview.ml`, `timing.ml`, or `testing.ml` to change a workspace's
default tile membership and Fit composition. Shared tile defaults and the small
`Stack` / `Columns` / `Narrow` / `Leaf` vocabulary live in `common.ml`.

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

See [the full source map, customization guide and verification](../../docs/frontend_composition.md)
for display overrides, migration, palette controls and synthetic startup.
