# Native FS2 provider API (WB-066)

Public library/package: `hardcaml_workbench_provider`. Only Core, Core_unix and
ppx_jane are required. Tests remain independent executables; this is adapter plumbing.

The actual public modules are `Hardcaml_workbench_provider.Wire`, `Validation`,
and `Runner`. Wire exposes the unchanged FS2 types, Limits, Backend_id, Build_ref,
Run_ref, Parameter, Case, Suite, Discovery, Asic_input, Selection, Progress,
Case_status, Outcome and Provider.{Request,Artifact,Event}.

```ocaml
val Runner.main :
  ?argv:string array ->
  discovery:Wire.Discovery.t ->
  validate_selection:(Wire.Selection.t -> unit Core.Or_error.t) ->
  run:(Runner.context -> unit Core.Or_error.t) -> unit -> unit

type Runner.context = {
  request : Wire.Provider.Request.t;
  artifact_dir : string;
  emit : Wire.Provider.Event.payload -> unit;
}

val Runner.run_child :
  prog:string -> args:string list ->
  on_stdout_line:(string -> unit) -> unit Core.Or_error.t
val Runner.artifact_path : context -> string -> string
```

`main` accepts exact `discover --protocol-version 1` and
`run --protocol-version 1 --request ABS --events ABS --artifact-dir ABS`.
Projects may parse prefix arguments (e.g. `--simulator PATH`) themselves and pass
the remaining argv **including argv[0]** through `~argv`. Callbacks can close over
the simulator path. `run_child` invokes argv directly, inherits stderr, forwards
each stdout line to the callback, and also logs each line to provider stdout.
Nonzero child status is an error. No shell or implicit build/install is involved.

The runner validates bounded strict requests and project-specific selections
before opening events. The callback emits Started and Finished explicitly; the
original request's case and parameter order is preserved for both project callbacks
(daemon submissions are already normalized upstream). The
emitter assigns sequence numbers, validates lifecycle/progress and flushes every
line. Callback errors/exceptions and incomplete streams exit nonzero with stderr.
Validation exposes the daemon's existing pure validators (same signatures).

No generic seed-to-PRNG mapping is imposed. Projects must preserve their existing
full uint64 interpretation; do not convert through a signed OCaml int or float.

Development verification uses `/tmp/opencode/native-provider-library` and a private
installation prefix `/tmp/opencode/native-provider-prefix`. A reusable SDK is also
installed persistently at
`/home/wayne/devel/jane/hardcaml_asic_example/.dev/workbench-provider-sdk`.
Set `OCAMLPATH=<prefix>/lib` when building an external adapter. No global opam
switch installation was performed. These local prefixes are development installs,
not a claim that the package has been published to an opam repository.

## Building and checking

From the Workbench checkout (the parent `/tmp/opencode` must already exist):

```sh
scripts/with-switch.sh dune build \
  --build-dir /tmp/opencode/native-provider-library -j 6 \
  --only-packages hardcaml_workbench_provider @install @provider/test/runtest
scripts/with-switch.sh dune install \
  --build-dir /tmp/opencode/native-provider-library \
  --prefix /tmp/opencode/native-provider-prefix hardcaml_workbench_provider
```

The package's generated opam build uses the focused provider test alias, so
`--with-test` does not invoke unrelated application executables. Development
process tests use Python 3; installed provider applications do not require Python.
`provider/test/frozen_wire.ml` is an independent pre-extraction encoding snapshot.
The conformance test compares sexps and raw bin_io bytes for every moved type and
event constructor, including uint64-max seed and Unicode/control-character text.
Foreground process tests exercise strict request failures before events, illegal
transitions, progress invariants, per-line/stream/event/artifact limits, immediate
flush, child stdout forwarding and nonzero child/callback errors. Protocol tests
separately enforce compile-time identity of daemon/provider types.

## Project boundary

Define the catalog and translate requests/results in a project-owned
`test_provider.ml`. The adapter may launch any project test executable through its
existing CLI with `Runner.run_child`. The executable does not need Workbench types,
events or assertions. Inspect `../examples/fs2_cyclesim/test_provider.ml` for a
complete native adapter around a separate simulator. The actual ASIC example uses
the same pattern around its unchanged `fifo_sim.exe`.

Seed interpretation is deliberately project-local, not imposed by this library.
Raw child stdout is logged, but only the adapter's explicit typed events establish
case results. A reported failed case may correctly accompany exit zero.

Combined native/Python standalone and private daemon HTTP/restart acceptance:
`/tmp/opencode/native-provider-s0e__xh7/result.json`. Installed real FIFO generation
verification: `/tmp/opencode/native-provider-dk6v5t_n/result.json`. The FIFO proof
includes byte-identical reports/VCDs; the counter proof excludes its variable VCD
date stanza. See `../docs/native_provider_plan.md` for final scope and commands.
