# Hardcaml Workbench

A development workbench for inspecting, running, measuring, and debugging Hardcaml designs.

**Current direction (2026-10-15):** configurable Bonsai Term tiles over typed
provider/module contracts, a command palette and named workspaces linked to a shared
Main run context by default. Workspaces can inspect independently; tiles can pin
references. Simulation/testing starts with a generic supervised test runner. ASIC
flow ownership stays with the project and `hardcaml_asic`; development uses the
sibling FIFO specimen and headless tests.

**FS0 demos are implemented and exercised:** workspace/run-context persistence,
palette and generic test/log tiles, synthesis views, installed ASIC discovery/plan/
launch/observation, and L1/L2 summary reuse. Two real synthesis profiles produced
673 and 685 cells; physical acceptance remains `not_evaluated`. Existing Dune,
RTL/artifact and hierarchy workflows remain covered by installed tests.
**FS1 now adds** synthesis resource/check metrics and explicit finalization import
with aggregate timing, physical resources, check verdicts and declared-clock context.
Workbench can also launch collection/acceptance, observe and cancel its owned
finalization, and browse bounded report/artifact text with optional terminal-host
external text opening.
Real physical completion, external acceptance pass/fail inspection and owned-container
cancellation are exercised. FS1 now also delivers retained timing-path exploration,
measured clock reports, stage-specific physical/routing/congestion tables and exact
binary external handoff. These complete the adopted-evidence FS1 scope; embedded
graphical editing, simulation helpers and appearance-gallery polish remain later work. See the
[FS1 evidence and limits](docs/fs1_acceptance.md) and [delivery record](docs/construction_phase_plan.md).

## Documentation

- [Documentation index](docs/README.md) — orientation and reading routes.
- [FS0 controls](docs/fs0_terminal.md) and [acceptance](docs/fs0_acceptance.md) — run the demo and inspect its evidence.
- [Synthesis inspection](docs/synthesis_inspection.md) — FS1 cell tables, sorting/filtering and evidence drilldown.
- [FS1 physical inspection](docs/fs1_acceptance.md) — metrics, timing/check/resource views, exact finalization import, real acceptance and limits.
- [Finalization and reports](docs/fs1_lifecycle_and_artifacts.md) — collect/accept palette commands, reconnect/cancel, paged artifact reading and configured external text viewing.
- [FS1 investigation completion](docs/fs1_investigation.md) — timing paths, measured clocks, physical/routing evidence, binary handoff, exact installed provider and adoption instructions.
- [Feature list](docs/feature_list.md) — concise scope/status and focused feature specs.
- [Feature sets](docs/feature_sets.md) — FS0 initial demos and later themed work groups.
- [Decision log](docs/decisions.md) — accepted run contexts; remaining command/snapshot policy.
- [Architecture](docs/hardcaml_workbench_architecture.md) — product, ownership, providers,
  runs/storage and workspace/window/tile boundaries.
- [Construction plan](docs/construction_phase_plan.md) — active demo phases M0–M5 and progress.
- [Rendering](docs/rendering.md) — styles, layout, interaction and headless UI testing.
- [Appearance handoffs](docs/design/README.md) — imported aesthetic sources and F12/FS5 interpretation.
- [Try the appearance presets](docs/appearance_presets.md) — A–E skins and independent color/icon/density controls.
- [Formatting guide](docs/formatting_guide.md) — retained source conventions.
- [Backlog](docs/backlog/README.md) — explicitly deferred ideas and reactivation triggers.
- [Archive](docs/archive/README.md) — earlier designs, plans and completion evidence.

## Development

Use `scripts/with-switch.sh` for Workbench commands. It selects the existing
`5.2.0+ox` opam switch by default; `OPAM_SWITCH=my-switch` overrides it. The wrapper
does not create a switch or install dependencies. Inspect dependency requirements:

```sh
./scripts/with-switch.sh opam install . --deps-only --with-test --show-actions
```

Review the actions before installing; omit `--show-actions` to apply them. Formatting
and lint tooling also need `ocamlformat` and `ppx_js_style`. Generated opam metadata
comes from `dune-project`. The native package is separate from optional web tooling.

Build and launch the current client against an independent project:

```sh
./scripts/with-switch.sh dune build -j20 terminal/main.exe daemon/main.exe
HARDCAML_WORKBENCH_DAEMON="$PWD/_build/default/daemon/main.exe" \
  ./scripts/with-switch.sh dune exec -j20 hardcaml-workbench -- \
  --project-root /absolute/path/to/project --environment opam:PROJECT_SWITCH
```

Use the project's actual switch. `--environment inherited` means the daemon's
startup environment, not necessarily the current client's shell. Add `--plain`
for noninteractive use. The current `b`/`t` controls submit build/test; `q` exits
the client while the daemon stays alive.

The palette (**Space c c**) also offers **Appearance: A - Instrument**, **B - Structured**,
**C - Minimal**, **D - Studio**, and **E - Structured studio**, plus separate color,
icon and density controls. These experimental client-local choices preserve run
contexts and pins; see the [preset guide](docs/appearance_presets.md).

Separate foreground startup is:

```sh
./scripts/with-switch.sh dune exec -j20 hardcaml-workbench-daemon -- --port 8080
# In another terminal:
./scripts/with-switch.sh dune exec -j20 hardcaml-workbench -- \
  --connect http://127.0.0.1:8080 --project-root /absolute/path/to/project \
  --environment opam:PROJECT_SWITCH
```

### Open the accepted real synthesis demo

The retained FS0 state includes real completed synthesis summaries: **balanced
673 cells**, **synth_delay 685 cells**. Acceptance is **`not_evaluated`**; cached
evidence is labeled **`Cached_unverified`** after restart. Open it using the
already compiled binaries, from this checkout, with no build or EDA:

```sh
# Terminal 1: one daemon owns this saved Workbench state.
_build/default/daemon/main.exe --port 41733 \
  --state-dir /tmp/opencode/workbench-fs0-91em64rl/real/state

# Terminal 2: use a 120-column × 40-row terminal.
_build/default/terminal/main.exe --connect http://127.0.0.1:41733 \
  --project-root /home/wayne/devel/jane/hardcaml_asic_example \
  --environment inherited
```

Use the printed daemon URL if you choose a different port.

**For a full dashboard:** press **Space c c → Switch to Overview**, then
**Apply default layout (add missing tiles)**. The old acceptance state deliberately
moved Overview's only selector into Timing, so it can initially be empty. This
additive action supplies a run selector, synthesis, placement, CTS, routing, timing,
checks, finalization, ASIC controls, execution/tests/logs and navigation. Existing
tiles, pins and contexts are preserved. Unsupported/not-requested stages are labeled;
no tool execution occurs merely from adding their views.

**Layout: Fit tiles to window** (the new client default) fills the available surface.
**Layout: Requested tile sizes** restores the earlier shelf sizing. Layout commands
are separate from Appearance commands. At small sizes the focused tile is shown
with a compact-mode notice; use Tab/zoom or hide tiles to inspect them.

**For the focused two-run comparison:** in the client, press
**Space c c**, type **Switch to FS0 Real Demo 1792063225057192206**, and press
**Enter**. This saved workspace shows a **pinned balanced synthesis tile (673)**
beside a **following synthesis tile (685)** linked to Main. The active workspace
is client-local, so choose it again when starting a new client. Tab changes tile
focus; the palette provides **Zoom focused tile** and **Unzoom workspace**. To
add a synthesis view elsewhere, use the palette's **Add synthesis tile**. This saved
workspace intentionally contains only two synthesis tiles; Fit expands them across
the surface without adding stages or changing the saved 56×14 preferred sizes.

Both tiles use real retained evidence. Opening them loads Workbench's cached
summaries. Focus either synthesis tile and press **Enter** for its cell table;
`/` filters, `s` cycles sort, Enter inspects the selected row, `e` shows full evidence,
and Esc returns. These inspection controls are local and do not launch provider work.
Keep the example configuration and retained
`/tmp/opencode/workbench-fs0-6_1ymcsd/results` provider evidence in place. Exit the
client with `q`; stop the foreground daemon with Ctrl-C before another daemon uses
the same state directory.

Reproduce the automated cached-data HTTP/PTY check with:

```sh
python3 -B scripts/test-fs0.py --reopen-real /tmp/opencode/workbench-fs0-91em64rl
```

It creates a new dedicated demo workspace in that state and fresh retained screen
evidence, without EDA or builds. See [FS0 acceptance](docs/fs0_acceptance.md) for
exact run identities, successful screens and limitations.

Run repository checks serially because they share Dune's build lock:

```sh
./scripts/with-switch.sh dune build -j20 @fmt
./scripts/with-switch.sh dune build -j20 @lint
./scripts/with-switch.sh dune runtest -j20
./scripts/with-switch.sh dune build -j20
```

Relevant integration checks, when changing those boundaries:

```sh
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh
./scripts/test-native-application.sh
./scripts/capture-terminal-baseline.sh --check
python3 -B scripts/test-fs0.py
```

The fixture uses an explicitly selected compatible switch. The installed-application
script tests an isolated install; legacy capture checks retain the original inspector
baselines, while `--capture-fs0 DIR` captures the new host with synthetic fixtures.
Historical toolchain investigations and detailed acceptance
records remain in the [archive](docs/archive/README.md). Record new phase evidence
in the construction plan rather than starting another general development diary.
