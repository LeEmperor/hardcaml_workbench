# Workspace definitions

**Current Testing composition:** `testing.ml` now uses cooperative simulation
catalog/attempt/case/detail/artifact/log panes and a compact Session/generic-tests/
execution column. Investigation selection is client/workspace-local, not ASIC Main;
the legacy `simulation` tile remains independently usable. Preset Apply preserves
old extras rather than silently removing them. [Controls/evidence](../../docs/testing_workspace.md).

Start with `overview.ml`, `timing.ml`, `testing.ml`, or `waveforms.ml` to change a workspace's
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

## Waveforms integration contract

`Waveforms.definition` registers stable preset ID `waveforms`, with four independent
tiles: `waveform-signals`, `waveform-waves`, `waveform-picker`, `waveform-logs`, plus
the existing workspace tabs. Signals and Waves share the upper band; VCD picker and
Logs share the lower band. All use normal host layout, focus, hiding, zoom and
appearance. `Presets.all` is the complete catalog; `Presets.starters` remains the
three automatic startup definitions. Waveforms is instantiated explicitly.

`Waveforms.create ~window` returns one `Instantiate_template` registry mutation.
Submit through the normal daemon transport, await acknowledgement, then identify
the result with `Waveforms.created ~before ~after`. The helper rejects replacement
sessions and ambiguous multiple creations. `Waveforms.find` locates an existing
workspace by stable preset ID even after rename. Never infer identity from its name.

`Waveforms.pin` stores exact project key/ID and full retained artifact identity,
including attempt, optional case and digest. Log provenance is either an explicit
unavailable reason or **daemon instance plus job ID**. `Waveforms.log_job` refuses
another daemon instance; a failed/expired read must remain unavailable.

`Workspace_host.set_waveform_pin` coordinates the workspace's panes. Its
`waveform_identity` lifetime token fences pending artifact/log requests. Retargeting
or reconnecting rotates the token; an equal pin and workspace switching preserve it.
Pane removal/move/retyping or replacement sessions prune pins; hide/zoom/resize
preserve them. Parsed waveform state stays with the transport/render owner, keyed
by workspace and lifetime, avoiding a dependency on the waveform renderer here.

The daemon persists actual workspace/layout state. Exact artifact pins are stored
separately using `Workspace_host.waveform_preferences` and
`save_waveform_preferences ~state_directory` in a bounded atomic terminal sidecar
`waveforms-<project-key-digest>.sexp`, following terminal preference conventions.
Load on the I/O worker and call `restore_waveform_preferences` **once after the first
registry receipt**. Restoration checks project/environment, registry session and
exact pane membership; it does not restore parsed data or logs as verified. Save
after explicit retargeting and pruning. Reload the exact retained artifact, showing
unavailable if it has expired; never silently use the current Testing selection.

`Host_view.render ?render_pane` accepts a callback
`Workspace.Tile.t -> width:int -> height:int -> Bonsai_term.View.t option`. Dimensions
are the actual body viewport. The host supplies titles/frames/padding, clips the
body, and overlays the global palette last. Main supplies the callback closing over
waveform state, so `Host_view` never imports `Waveform_view` (which uses host roles).
