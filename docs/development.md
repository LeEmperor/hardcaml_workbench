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

There is not yet a local application startup command. Later 1A work will add the native
daemon, compiled web assets, development startup workflow, and installed launcher; this
document should gain those commands when they exist. (The RTL-generator scaffold this
paragraph previously pointed at, `bin/generate.ml`, was removed by the packaging task.)

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

### Bonsai dependency installation prerequisite

Installing `bonsai_web` into the `5.2.0+ox` switch failed on 2026-09-18 with roughly twenty
identical `Error: Syntax error` reports, each on a generated first line of the form
`include ./foo__generated` or `include module type of ./foo__generated`, under
`web/view/kado/src`, `web/view/src`, and `web/view/partial_render_table_styling`.

`bonsai_web` generates OCaml from CSS with Dune rules that invoke
`(bash "%{bin:css_inliner} %{deps} \"()\"")`. Dune `3.24.2` expands `%{deps}` with a `./`
prefix, and `css_inliner` derives the module name by removing the `.css` extension from the
path as given and capitalizing its first character. For `./app.css` the first character is
`.`, so capitalization has no effect, the prefix is retained, and the tool emits an invalid
`include ./app__generated`. Both halves reproduce without Hardcaml or Bonsai involvement:
`css_inliner mystyle.css "()"` produces a correct `include Mystyle__generated`, whereas
`css_inliner ./mystyle.css "()"` produces the broken form, and a two-rule Dune project whose
action echoes `%{deps}` prints `./mystyle.css`.

This is not a package version skew. The installed `ppx_css` and `bonsai_web` are the same
`v0.18~preview.130.106+341` release, and the defect lies in the interaction between Dune and
`css_inliner` rather than in Bonsai. It is also not the opam sandbox failure seen earlier on
this host; the build sandbox ran correctly and produced genuine compiler diagnostics. The
declared `(lang dune ...)` version does not affect the expansion, which was checked for
`3.17`, `3.20`, `3.22`, and `3.24`, so the Dune binary selects the behavior. Older Dune
binaries were not tested, and `bonsai_web.opam` constrains only `dune {>= "3.17.0"}` with no
upper bound, as this repository constrains only `dune {>= "3.22"}`.

The switch was repaired with a local source pin that rewrites ten identical Dune lines across
three files, replacing `%{bin:css_inliner} %{deps}` with
`%{bin:css_inliner} $(basename %{deps})`:

```sh
opam pin add bonsai_web.v0.18~preview.130.106+341 \
  ~/devel/jane/bonsai_web-patched --kind=path
opam install bonsai_web -j 10
```

A full `dune build -p bonsai_web -j 10` then completes, the generated files read
`include App__generated`, and a project depending on `bonsai_web` and `bonsai_web.kado`
typechecks. The pin shadows later upstream `bonsai_web` releases, so remove it with
`opam pin remove bonsai_web` once `css_inliner` reduces its input to a basename. Any other
Jane Street package whose Dune rules call `css_inliner` fails the same way and needs the same
treatment; do not diagnose such a failure as a Bonsai or Workbench source problem.

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

## Shared protocol schemas

The third and fourth 1A construction tasks added the project, target, job, and artifact
schemas to `protocol/`, derived from architecture sections 4 and 18. Recorded 2026-09-18.

Identifiers are abstract types produced by one functor in `id.ml`, so the compiler rejects
passing a `Project_id.t` where a `Target_id.t` is expected, and each one arrives with the
`Map`, `Set`, and `Hashtbl` the backend will need. Every schema derives both `sexp` and
`bin_io`. That is deliberate: the application RPC transport and serialization choice is a
later 1A task, and deriving both now means making that choice does not reopen the schemas.

The backend-neutrality rules the plan asked for are enforced by the types rather than by
convention:

- targets carry namespaced, backend-declared `Target_fact.t` values; there is no part field,
  and `Target.fact` returns an option so an undeclared fact reads as unknown;
- artifact kinds are an open `(namespace, name, role, media)` record, so a backend adds a
  kind without a protocol revision;
- `Build_ref.t` and `Run_ref.t` are optional on jobs and artifacts and carry the backend's
  own identifier verbatim, so the Workbench references a backend's build and run identities
  rather than minting substitutes;
- `Metric.Value.t` has an `Unavailable of { reason }` case, so an absent measurement has no
  numeric representation at all;
- `Structured_result.t` keeps completion, goals, and verification in three separate fields;
- `Job.Exit_status.t` distinguishes `Launch_failed` from `Exited`, which 1B's failure-path
  checks need;
- no protocol value carries a filesystem path. `Project_root.t` is the single exception and
  is documented as an identity for display and provenance, not a handle.

Three refinements to the architecture's example records are recorded in architecture
sections 4.1 and 18: `configurations` replaces `build_configs`, `boards` is not implemented,
and `target`/`configuration` are optional on jobs and artifacts because a generic Dune
project has no targets.

Validation on 2026-09-18, all from the Workbench checkout:

```sh
./scripts/with-switch.sh dune build @fmt      # passes
./scripts/with-switch.sh dune build @lint     # passes
./scripts/with-switch.sh dune runtest         # passes
./scripts/with-switch.sh dune build           # passes
./scripts/with-switch.sh dune build -p hardcaml_workbench   # passes
```

`protocol/test/` holds thirteen expect tests of the representation rules above — an
unavailable metric is not a measurement, a completed stage list is not closure, a dirty
working tree is not an exact source identity, a launch failure is not a nonzero exit — plus
sexp and bin_io round trips. Inline tests need one non-obvious Dune flag in this switch; see
below.

The schemas were also confirmed to compile to JavaScript, which is the reason the shared
protocol exists as its own library. A temporary bytecode executable linking `core` and
`hardcaml_workbench_protocol` compiled with `js_of_ocaml 6.4.0~alpha~dev` and produced
output; the probe was then removed. This did not execute the result, because no JavaScript
runtime is installed on this host.

### Inline expect-test prerequisite

Every inline test in a library below the Dune project root needs
`(inline_tests (flags (-source-tree-root .)))` in this switch. Without it the runner aborts
before reporting, whether the test passes or fails:

```text
Uncaught exception:
  (Sys_error "./../test_protocol.ml: No such file or directory")
  Raised ... Ppx_expect_runtime__Write_corrected_file.f
```

The cause is in `ppx_expect` `v0.18~preview.130.106+341`, not in Dune. Its runtime computes
the file to patch as

```ocaml
Stdlib.Filename.concat source_tree_root (Stdlib.Filename.basename filename)
```

(`lib/ppx_expect/runtime/ppx_expect_runtime.ml`, line 15), which discards the
subdirectory, so the path only resolves for a test file sitting at the source-tree root.
Dune `3.24.2` is doing the right thing: it runs the runner with the library directory as
its working directory and passes the correct relative path back to the build root.
Overriding that path with `.` makes the join resolve, because Dune appends stanza flags
after its own and the last `-source-tree-root` wins.

Verified on 2026-09-18 in `protocol/test/`: passing tests pass, a deliberately wrong
expectation produces a correct diff, and `dune promote` writes back to the source file.
