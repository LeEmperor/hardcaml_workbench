# Hardcaml Workbench

A development workbench for inspecting, running, measuring, and debugging Hardcaml designs.

**Current direction (2026-10-12):** a configurable Bonsai Term workspace containing
monitor-sized windows and movable tiles over backend feature modules. Each window
selects a run; its tiles follow that selection or explicitly pin a reference run.
ASIC flow ownership stays with the project and `hardcaml_asic`. Development will
use a dedicated sibling test-asic repository and headless interaction tests.

The existing daemon, Dune jobs, RTL/artifact and hierarchy workflows are
implemented. The provider/catalog and multi-window tile design is planned.

## Documentation

- [Architecture](docs/hardcaml_workbench_architecture.md) — product, ownership, providers,
  runs/storage and workspace/window/tile boundaries.
- [Construction plan](docs/construction_phase_plan.md) — active P0–P7 phases and progress.
- [Rendering](docs/rendering.md) — styles, layout, interaction and headless UI testing.
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
./scripts/with-switch.sh dune build terminal/main.exe daemon/main.exe
HARDCAML_WORKBENCH_DAEMON="$PWD/_build/default/daemon/main.exe" \
  ./scripts/with-switch.sh dune exec hardcaml-workbench -- \
  --project-root /absolute/path/to/project --environment opam:PROJECT_SWITCH
```

Use the project's actual switch. `--environment inherited` means the daemon's
startup environment, not necessarily the current client's shell. Add `--plain`
for noninteractive use. The current `b`/`t` controls submit build/test; `q` exits
the client while the daemon stays alive. Separate foreground startup is:

```sh
./scripts/with-switch.sh dune exec hardcaml-workbench-daemon -- --port 8080
# In another terminal:
./scripts/with-switch.sh dune exec hardcaml-workbench -- \
  --connect http://127.0.0.1:8080 --project-root /absolute/path/to/project \
  --environment opam:PROJECT_SWITCH
```

Run repository checks serially because they share Dune's build lock:

```sh
./scripts/with-switch.sh dune build @fmt
./scripts/with-switch.sh dune build @lint
./scripts/with-switch.sh dune runtest
./scripts/with-switch.sh dune build
```

Relevant integration checks, when changing those boundaries:

```sh
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh
./scripts/test-native-application.sh
./scripts/capture-terminal-baseline.sh --check
```

The fixture uses an explicitly selected compatible switch. The installed-application
script tests an isolated install; capture checks concern the current renderer, not
the planned tile UI. Historical toolchain investigations and detailed acceptance
records remain in the [archive](docs/archive/README.md). Record new phase evidence
in the construction plan rather than starting another general development diary.
