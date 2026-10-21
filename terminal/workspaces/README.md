# Workspace definitions

**Current Testing composition:** `stock.sexp` uses cooperative simulation
catalog/attempt/case/detail/artifact/log panes and a compact Session/generic-tests/
execution column. Investigation selection is client/workspace-local, not ASIC Main;
the legacy `simulation` tile remains independently usable. Preset Apply preserves
old extras rather than silently removing them. [Controls/evidence](../../docs/testing_workspace.md).

Start with **`stock.sexp`** to change stock membership, sparse presentation, Fit trees,
or the shipped default window composition. This is the actual stock source, embedded
deterministically by dune and decoded/validated as `Workspace_config.Definition.t`.
The OCaml preset modules are compatibility projections, not a second layout table.
`custom.sexp` is a usable custom-only example with two synthesis tiles addressed by
different keys and deliberately placed in the opposite order to their membership.
Both files use the shared `protocol/workspace_config.ml` slicing-tree vocabulary.

```sh
hardcaml-workbench --project-root /path/to/project --workspace-config terminal/workspaces/custom.sexp
```

The terminal reads and validates the explicit path on the client before connecting.
It sends resolved data, not a filename, to `Initialize_config` before Bootstrap. An
existing session is retained; config is never replayed over saved edits. Resolved
definitions and authoring-key → live-tile mappings come from the daemon snapshot,
so reconnect/rendering does not depend on the file still being present. Omit the
flag on subsequent launches if the file has been removed.

`Presets.builtins : string -> Workspace_config.Definition.t Or_error.t` is the CLI
resolver. `Presets.export_config ()` exports the complete canonical stock catalog
and default window; `export_presets --workspace-config` prints it. The no-argument
exporter retains its legacy synthetic-seeder format. `Presets.decode` accepts
ordinary custom specs and complete stock exports. Reserved definitions in an export
must exactly match stock. To customize a stock definition, give it a nonreserved
key, remove `template.preset`, and reference it with `Custom`.

The palette always offers **Create built-in workspace: Overview / Timing / Testing /
Waveforms**, including in a custom-only session. Current-preset Restore is unavailable
for a custom definition. A named builtin Restore explicitly selects that builtin
and hides extras; it is not a reset to custom config defaults. Reset-to-config is
not exposed by the terminal.

- `definition.ml`: stable preset ID, membership, presentation and Apply/Reset helpers.
- `layout.ml`: responsive placement, duplicate/custom extras and compact fallback.
- `presets.ml`: registered definitions; keyed by ID, not the workspace display name.
- `export_presets.ml`: exports those same definitions for the synthetic demo.

Requested tile geometry and Fit layout constraints are separate. For a taller run
selector, change its requested geometry and Fit leaf height as well as its
`visible_rows` presentation cap. Configured leaves use tile authoring keys, resolved
through persisted IDs even after reorder/hide. Legacy arrangements claim by kind;
further copies and unfamiliar tiles remain visible as extras. Sparse presentation
inherits app defaults and explicit client preferences take precedence.

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
height with named minima/weights. `stock.sexp` exposes the width weights
and minimum tile heights as source policy. `Weighted_columns` divides the full
available width by positive integer weights, clamping undersized columns to descendant
minima and redistributing the remaining width. This also provides Waveforms' narrow
sidebar behavior using the same spec and layout engine as custom trees. It does
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
Fresh startup uses `Initialize_config` with the Overview/Timing/Testing window in
`stock.sexp`. `Presets.bootstrap` completes only unfinished legacy Overview/Timing
placeholders through a single idempotent daemon operation, even after a CLI import
has advanced registry revision. It does not add Testing to existing sessions. Legacy
saved arrangements are never mistaken for incomplete bootstrap. Custom layouts
honor generic Fit as well as requested-size mode. See [FS3 adoption](../../docs/fs3_adoption.md).

## Waveforms integration contract

`Waveforms.definition` registers stable preset ID `waveforms`, with five independent
tiles: `waveform-session`, `waveform-signals`, `waveform-waves`, `waveform-picker`, `waveform-logs`, plus
the existing workspace tabs. Signals and Waves share the upper band; VCD picker and
Logs share the lower band. All use normal host layout, focus, hiding, zoom and
appearance. `Presets.all` is the complete catalog; `Presets.starters` remains the
Overview/Timing/Testing startup definitions from `stock.sexp`. Waveforms is
instantiated explicitly.

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

## Post-merge catalog audit (2026-10-21)

Compared against merged oxcaml `471419a`, including its compiled workspace definitions:

- Overview retains the one-third Session/Runs/checklist/plan sidebar and six compact
  domain summaries; Timing retains its Session/Runs row and Paths/Detail/Context tree.
  Four-row Runs defaults and the vertical compact checklist are in the shared spec.
- Testing retains all six cooperative simulation panes and the compact project-only
  utility column at the delivered **2:3:3** widths. The guide now reflects those
  merged source proportions.
- Restored Testing to the canonical default window, matching the three starters in
  `471419a:terminal/workspaces/presets.ml` (introduced before Waveforms and explicitly
  retained in `994cc85`). Existing saved compositions are not replayed or upgraded.
- Hierarchy remains opt-in as delivered in `471419a` and documented in
  `docs/hierarchy_tile.md`. Any user definition can compose the `hierarchy` kind using
  the same template/tile/tree schema; it needs no new preset or authoring format.
- The duration alignment/cache work (`58f3dfc`, and
  `docs/timing_cache_and_duration_alignment_plan.md`) changes rendering and demand,
  not preset membership. It introduces no separate duration tile or layout policy.
- Removed unused hardcoded stock helpers and the obsolete shell from `common.ml`;
  its types and generic tile constructor remain renderer/test compatibility helpers.
  Stock policy is solely in `stock.sexp`, including Waveforms' 1:4 width clamp.

Regression coverage in `test_workspaces.ml` checks exact starter membership, fresh
initialization versus legacy preservation, cooperative Testing membership/presentation,
and stock/user tree parity. Central workspace/terminal tests, native builds, lint,
configuration and domain/reconnect acceptance passed; see the
[audit and exact evidence](../../docs/workspace_post_merge_audit.md).
