# Development and Local Validation

## Workbench switch

Run Workbench development commands through `scripts/with-switch.sh`. The wrapper uses the
`5.2.0+ox` opam switch by default and fails with a clear message if the selected switch does
not exist. Override it without changing the script when necessary:

```sh
OPAM_SWITCH=my-switch ./scripts/with-switch.sh dune build
```

The wrapper selects an existing switch; it does not create one or install dependencies. To
inspect the declared build and test dependency actions with the opam version used by the
default switch:

```sh
./scripts/with-switch.sh opam install . --deps-only --with-test --show-actions
```

After reviewing the actions, omit `--show-actions` to apply them. Opam 2.1 does not support
the newer `--with-dev-setup` command-line option. Install the development-only packages
declared in `dune-project` explicitly when setting up this switch:

```sh
./scripts/with-switch.sh opam install ocamlformat ocaml-lsp-server ppx_js_style
```

## Build and validation workflow

From the Workbench checkout, run:

```sh
./scripts/with-switch.sh dune build @fmt
./scripts/with-switch.sh dune build @lint
./scripts/with-switch.sh dune runtest
./scripts/with-switch.sh dune build
```

Run these commands serially because they share Dune's `_build` lock. The wrapper validates
the Workbench's own build environment only. An independent project opened by the Workbench
must be built and tested in that project's selected environment.

The application-role foundation can also be built explicitly:

```sh
./scripts/with-switch.sh dune build daemon/main.exe web/main.bc
```

There is not yet a local application startup command. The current `bin/generate.ml` is an
unlaunched RTL-generator scaffold, not the Workbench daemon or launcher. Later 1A work will
add the native daemon, compiled web assets, development startup workflow, and installed
launcher; this document should gain those commands when they exist.

## Baseline recorded for milestone 1A

The first 1A construction check was run on 2026-09-14 with:

- OCaml `5.2.0+ox`
- Dune `3.22.2`
- opam `2.1.5`

Format, lint, tests, and the default build all completed successfully with the commands
above. The dependency dry run completed successfully and reported no missing package
installs. It proposed recompiling `conf-zlib`, `cryptokit`, and `hardcaml_waveterm` because
of upstream or system changes; the existing switch nevertheless completed all repository
checks. Applying those switch-local rebuilds is optional maintenance rather than a source
dependency correction required by this baseline.

The packaging audit identified these source corrections, which the next 1A task applied:

- `dune-project` and the generated opam metadata described an installed library of
  synthesizable blocks rather than the standalone Workbench application.
- Native application dependencies such as `core_unix` and the Bonsai/JavaScript build
  dependencies were marked `:with-test`, even though the installed daemon and web assets
  require them to build.
- `hardcaml`, `hardcaml_circuits`, and their preprocessors were unconditional dependencies
  of an application-owned hardware library. They do not belong in the application package;
  the independent fixture and project-side integration own circuit source.
- Add transport and server dependencies only after the RPC transport and serialization
  decision required by 1A is recorded in the architecture.

Keep `hardcaml_workbench.opam` generated from `dune-project`; do not edit it independently.

### JavaScript toolchain prerequisite

The application-role build initially exposed an incompatibility between OxCaml
`5.2.0minus40` and js_of_ocaml `6.3.2+ox`. The compiler emits
`WITH_STACK_PREEMPTIBLE` and `WITH_STACK_BIND_PREEMPTIBLE` bytecodes, while the installed
js_of_ocaml compiler does not recognize them and fails with `Bad_instruction(156)`. The
current OxCaml opam repository (`bb455526`) and upstream js_of_ocaml (`13b9d9e2`) were
checked on 2026-09-14 and did not yet contain support for these instructions.

For the structure-only packaging task, `web/main.bc` validates that Bonsai code can depend
on the portable protocol without reaching native libraries. This bytecode file is not a
browser asset. Before the shared protocol is compiled for JavaScript later in 1A, use an
aligned compiler/js_of_ocaml package pair or an upstream-supported compatibility fix, change
the web target to JavaScript mode, and require `web/main.bc.js` to build. Do not patch the
shared opam switch ad hoc or treat the bytecode target as completion of that later check.

## Application packaging foundation

The second 1A construction task replaced the synthesizable-library scaffold with private
Dune libraries for the shared protocol, project integration, native backend, and native
adapters, plus private daemon and web entry points. The application package no longer
declares Hardcaml circuit libraries, hardware preprocessors, or hardware test frameworks as
its dependencies. No project SDK is present; 1C will add one only if the driver integration
demonstrates a need for it.

`dune describe external-lib-deps` verifies the intended direction:

```text
web -> protocol -> core
  +-> bonsai / bonsai_web / js_of_ocaml

daemon -> backend / adapters -> project_integration -> protocol
          +-> core_unix
```

The opam package temporarily uses Dune's `allow_empty` setting because all application
targets are private. Remove it when the later 1A installation task adds the public launcher,
daemon, and frontend asset install stanzas.

The repository format, lint, test, default build, explicit role build, and package build all
pass. `opam lint hardcaml_workbench.opam` also passes, and the corrected dependency dry run
reports no missing installs. As in the initial baseline, opam still proposes the unrelated
switch-local `conf-zlib` rebuild and its installed reverse dependencies.
