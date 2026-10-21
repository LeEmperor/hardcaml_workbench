# Compose your own windows and workspaces

Stock and user layouts use the same versioned S-expression specification. The actual
shipped definitions are in [`stock.sexp`](../terminal/workspaces/stock.sexp); the
default window composition is at the end of that file. Overview, Timing, Testing
and Waveforms are definitions in this catalog, not separate layout implementations.
The stock file is embedded at build time and validated through the shared codec.

Start with [`custom.sexp`](../terminal/workspaces/custom.sexp) for a smaller working
example: a run selector and two synthesis tiles, with independent presentation and
layout keys. Existing tile implementations remain compiled application features;
configurations compose them without writing OCaml.

## Export, edit and validate

With the native commands installed:

```sh
hardcaml-workbench-workspace config export stock > stock.sexp
hardcaml-workbench-workspace config export example -id my-desk > my-desk.sexp
hardcaml-workbench-workspace config validate my-desk.sexp
```

Export and validation are offline. In a source checkout, use
`_build/default/workspace_cli/main.exe` in place of
`hardcaml-workbench-workspace` after building with `scripts/with-switch.sh`.

To customize a stock definition:

1. Copy the desired definition from the stock export.
2. Change its `key` to a nonreserved key such as `my-overview`.
3. Remove `preset` from its nested `template` (or use `(preset ())`).
4. Reference it with `(definition (Custom my-overview))` in a workspace instance.
5. Change the top-level `id` to identify your composition, and validate the file.

The reserved keys `overview`, `timing`, `testing` and `waveforms` identify immutable
built-ins. Complete stock exports are accepted while their reserved definitions
match the installed catalog. For upgrade-independent files, omit unchanged reserved
definitions and reference them with `Builtin`; copy and rename any definition you
want to own. Built-ins remain available even in an entirely custom composition.

## Windows and reusable workspace definitions

This complete example uses built-ins without copying their definitions:

```sexp
((version 1)
 (id two-desks)
 (definitions ())
 (windows
  (((key primary)
    (name "Main desk")
    (workspaces
     (((key overview) (name "My overview") (definition (Builtin overview)))
      ((key tests) (name "Tests") (definition (Builtin testing))))))
   ((key analysis)
    (name "Analysis desk")
    (workspaces
     (((key timing) (name "Timing") (definition (Builtin timing)))
      ((key waves) (name "Waves") (definition (Builtin waveforms)))))))))
```

`definitions` holds reusable custom definitions. `windows` contains ordered window
declarations, each containing ordered workspace instances. Several instances can
reference the same definition; each receives fresh live identities.

Keys and names have different roles:

- `id` identifies a configuration during repeated application.
- A window `key` is unique within that configuration.
- A workspace instance `key` is unique within its declared window.
- A definition `key` identifies reusable content.
- Each definition's tile `key` identifies a specific tile occurrence.
- `name` is a display label, not an identity or matching rule.

Keys contain 1–128 alphanumeric, dash, underscore or dot characters. Keep keys stable
when editing labels. Moving an instance declaration to another window changes its
authoring identity; additive apply creates a new instance and retains the old one.

## Tile membership, layout and presentation

A definition has a version-1 portable `template`, a parallel `tiles` list and an
optional `layout`. `template.views` owns ordered kinds, visibility and requested
geometry. Each corresponding `tiles` entry supplies its unique key and optional
presentation defaults. The lists must have equal length and matching order.

Layout leaves reference **tile keys**, not kinds. Two `synthesis` tiles can therefore
have different positions and policies even after live reorder/hide operations.
The existing responsive engine supports:

- `Leaf`: tile key, minimum width/height and vertical growth weight.
- `Stack`: vertically arranged children.
- `Columns`: horizontally arranged children.
- `Weighted_columns`: positive width weights paired with child trees.
- `Narrow`: marks a narrow subtree using the shared engine's sizing policy.

Missing/hidden leaves collapse; visible tiles not claimed by a tree remain extras.
If a layout cannot fit, the renderer falls back to its grid or focused-tile view.
Weighted columns divide full available width and clamp against descendant minima.
Requested-size mode uses requested width/height rather than the Fit tree; saved
`x/y` are portable data, not arbitrary terminal free-placement coordinates.

Sparse presentation supports `title`, `run_reference`, `freshness`, `hints`, `frame`,
`padding`, `binding_badge`, `visible_rows`, `compact_summary` and `horizontal_stages`.
An omitted field inherits defaults. S-expression option values use parentheses:
`(padding (1))`, `(hints (false))`; badges are `hidden`, `always` or `exceptions`.
Explicit local appearance/header preferences take precedence over definition defaults.
Content-specific flags take effect on tiles implementing those capabilities.

## First startup and saved sessions

```sh
hardcaml-workbench --project-root /absolute/project \
  --workspace-config /absolute/my-desk.sexp
```

The terminal reads a bounded file on the **client**, resolves built-ins and sends
data to the daemon. No daemon access to the client pathname is required.

- A fresh session receives the entire composition in one atomic operation.
- Without a selected file, fresh startup uses the window composition in `stock.sexp`
  (currently Overview and Timing). Testing and Waveforms remain available to create.
- Existing sessions win over startup configuration, including sessions edited before
  the first terminal attaches. Legacy unfinished bootstrap remains supported.
- Live identities, context/run selections, pins, geometry and visibility are saved
  separately from portable files. New workspaces link to Main; new tiles Follow.
- Resolved definitions and tile-key mappings are persisted with the session. Remove
  `--workspace-config` when reconnecting without the original file; layout still works.
- An explicitly supplied missing or invalid file fails before connection. Launch
  without that flag to access saved state or stock defaults. Invalid saved registry
  data is reported rather than silently replaced.

Editing a file does not automatically change an existing session.

## Explicit additive application

For an already-open project on a running daemon:

```sh
hardcaml-workbench-workspace config apply \
  -endpoint http://127.0.0.1:8080 -project PROJECT-ID my-desk.sexp
```

Application is revision-checked and atomic across all declared windows/workspaces.
It creates missing keyed windows, instances and tiles. Repeating the command does
not duplicate existing keys. Invalid input or a stale revision publishes nothing;
conflicts are reported without automatic retry.

Existing live edits and previously instantiated layout/presentation policy win.
Changed names, kinds, trees or definition references do not reset an existing keyed
instance. Removed keys remain live. New tiles appear as extras when not covered by
the saved tree. To try a revised complete layout, give the workspace instance a new
key and apply it as a fresh instance. Reset-to-config and removal reconciliation are
not part of this delivery.

The older `export`, `import`, `clone` and `starter` commands still work with portable
workspace templates. Those templates contain membership/visibility/geometry and
optional preset identity; they do not export custom trees or presentation policy.
`config export` exports shipped examples, not the entire current live session.

## Built-in recovery

The palette always offers **Create built-in workspace: Overview / Timing / Testing /
Waveforms**, including from a custom-only session. This adds a workspace without
replacing custom ones.

**Restore default layout: NAME (hide extras)** explicitly selects a shipped preset
for the current workspace. It restores default membership/geometry/visibility,
clears zoom and detaches saved configuration layout policy, while retaining IDs,
pins, contexts and authoring mappings. Reapply does not reattach that frozen policy.
The current-preset Restore is disabled for custom definitions; named built-in Restore
is distinct from resetting to custom defaults. See [recovery controls](default_layout_restore.md).

## Compatibility and extending the specification

The composition envelope is version 1; portable template version 1 remains supported.
New clients read legacy snapshots using defaulted configuration fields. Rebuild/restart
daemon and clients together: older executables are not guaranteed to understand new
operations or persisted configuration fields. No downgrade migration is provided.

The shared contract is `protocol/workspace_config.ml`. When adding a compositional
capability, extend this contract, validation and renderer projection together; update
stock examples to exercise it. Add compatibility defaults for genuinely optional
fields and a version/migration policy for incompatible changes. Avoid introducing
stock-only fields or a second layout table in OCaml.

Current limits: 4 MiB encoded configuration, 128 definitions, 32 windows, 256 workspace
instances, 4,096 stored tiles and 4,096 instantiated tiles per application. Trees are
bounded to depth 32 and 4,096 nodes per definition. Existing template geometry and
label limits also apply. Windows are logical registry containers; live surface
attachment/monitor orchestration remains WB-047 work.

## Verification

Targeted protocol, backend persistence, workspace and terminal tests passed with
`-j20`; native daemon/client/CLI/setup build and `@lint` passed. Modified OCaml files
were formatted. Repository-wide `@fmt` still reports existing differences in untouched
`backend/asic_service.ml` and `terminal/waveform_data.ml`, `.mli`, and `waveform_probe.ml`.

Native evidence (2026-10-21):

- New composition CLI/HTTP/PTY checks:
  `/tmp/opencode/workspace-config-zbzojw2o/result.json`.
- Existing FS3 adoption:
  `/tmp/opencode/fs3-adoption-574hfszu/result.json`.
- Built-in restore, exact provenance preservation and viewport checks:
  `/tmp/opencode/default-layout-restore-gekveke6/result.json`.

Reproduce the new focused acceptance with `python3 scripts/test-workspace-config.py`
after building matching native binaries. It uses private metadata-only fixtures and
does not run project builds or provider jobs. See the
[agent-sized implementation plan](workspace_configuration_plan.md).
