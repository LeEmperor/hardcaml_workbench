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

The native application can also be built explicitly:

```sh
./scripts/with-switch.sh dune build terminal/main.exe daemon/main.exe
```

For automatic development startup, point the launcher at the build-tree daemon. Omit
`--plain` to enter the interactive Bonsai Term UI:

```sh
HARDCAML_WORKBENCH_DAEMON="$PWD/_build/default/daemon/main.exe" \
  ./scripts/with-switch.sh dune exec hardcaml-workbench -- --plain
```

For separate foreground processes:

```sh
./scripts/with-switch.sh dune exec hardcaml-workbench-daemon -- --port 8080
./scripts/with-switch.sh dune exec hardcaml-workbench -- \
  --connect http://127.0.0.1:8080 --project-root /path/on/daemon/host
```

The native client opens generic Dune projects and runs build/test jobs. Browser assets belong to
1E. The removed RTL-generator scaffold does not participate in startup.

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
browser asset. For the browser gate in 1E, use an
aligned compiler/js_of_ocaml package pair or an upstream-supported compatibility fix, change
the web target to JavaScript mode, and require `web/main.bc.js` to build and its protocol codecs
to execute successfully. Do not patch the
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

## Remaining 1A implementation decisions

Recorded 2026-09-19; documentation only. The authoritative choices are in the architecture's
[protocol decisions](hardcaml_workbench_architecture.md#1a-application-protocol-decisions-2026-09-19)
and [launcher/installation decisions](hardcaml_workbench_architecture.md#1a-launcher-installation-and-fixture-decisions-2026-09-19).
Use HTTP with typed S-expression bodies, Async/Cohttp native transport, and long polling.
Package the native launcher/terminal client and daemon independently of optional browser
assets. Follow the [implementation handoff](construction_phase_plan.md#9-completion-and-progress-tracking)
for the remaining work and acceptance evidence. No proposed CLI command is available yet,
and Cohttp compatibility with this switch has not been validated.

The older JavaScript blocker entries above are historical observations. The 2026-09-18
shared-protocol compilation probe and local Bonsai dependency repair are later evidence;
neither establishes a working browser client or a completed browser codec execution check.
Revalidate the browser prerequisites in 1E rather than treating the old diagnosis as current.

## Milestone 1A installed native foundation

Completed and validated on 2026-09-20 with OCaml `5.2.0+ox`, Dune `3.24.2`, Async
`v0.18~preview.130.106+341`, Cohttp Async `6.3.0`, and Bonsai Term
`v0.18~preview.130.106+341`.

`protocol/V1` freezes portable S-expression definitions for `hello`, empty `snapshot`, and
long-poll `updates`. The native server and client use Async/Cohttp outside the protocol
library. The server enforces loopback Host values, same-origin requests, the protocol and
content-type headers, request limits, instance identity, cursors, and poll limits. The daemon
binds loopback only. Automatic startup uses private XDG runtime state, advisory startup and
lifetime locks, atomic discovery metadata, readiness checks, detached execution, and the
installed sibling daemon. A stale PID is never signaled by discovery logic.

The normal client is a Bonsai Term application. `--plain` is a deterministic non-TTY view for
automation and performs the same typed exchange. Client exit leaves the daemon alive. An
explicit `--connect` failure is reported without consulting discovery or starting a daemon.

The native package and browser-only dependency set are separate generated opam packages.
`hardcaml_workbench.opam` contains Async, Cohttp Async, Bonsai, and Bonsai Term, but no
`bonsai_web`, js_of_ocaml, or `ppx_css`. `hardcaml_workbench_web.opam` reserves the optional
browser package; it installs no assets until 1E. `dune describe external-lib-deps` reports the
terminal's internal dependencies as only `hardcaml_workbench_native_http` and
`hardcaml_workbench_protocol`.

The installed workflow is:

```sh
prefix="$(mktemp -d)"
./scripts/with-switch.sh dune build -p hardcaml_workbench @install
./scripts/with-switch.sh dune install --prefix "$prefix" hardcaml_workbench
cd /tmp
XDG_RUNTIME_DIR="$(mktemp -d)" "$prefix/bin/hardcaml-workbench"
```

The daemon can instead be run in the foreground with
`$prefix/bin/hardcaml-workbench-daemon --port 8080`, then attached with
`$prefix/bin/hardcaml-workbench --connect http://127.0.0.1:8080`. SIGINT or SIGTERM performs
bounded shutdown. The automatic daemon persists until explicitly signaled or managed by a
future service integration; there is intentionally no idle shutdown.

Exact validation commands and outcomes:

```sh
./scripts/with-switch.sh opam list --installed --short \
  cohttp-async async async_unix bonsai_term                  # all installed
./scripts/with-switch.sh dune describe external-lib-deps    # boundary confirmed
./scripts/test-native-application.sh                        # passed
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh      # build/test passed externally
./scripts/with-switch.sh dune build -p hardcaml_workbench @install  # passed
./scripts/with-switch.sh opam lint hardcaml_workbench.opam  # passed
./scripts/with-switch.sh opam lint hardcaml_workbench_web.opam # passed
./scripts/with-switch.sh dune build @fmt                    # passed
./scripts/with-switch.sh dune build @lint                   # passed
./scripts/with-switch.sh dune runtest                       # passed
./scripts/with-switch.sh dune build                         # passed
```

`scripts/test-native-application.sh` installs to a temporary prefix and launches from a
separate directory. It checks successful typed exchange, pending project-root handling,
concurrent startup, stale metadata, client exit and reattachment to the same PID, explicit
endpoint failure without replacement, and SIGTERM shutdown. `scripts/test-fixture.sh` requires
an explicit `FIXTURE_OPAM_SWITCH`, copies the miniature counter project outside the Workbench
tree, and runs ordinary Dune build and test commands there.

Browser readiness is not part of this evidence. No JavaScript asset or codec was executed;
the bytecode web scaffold remains only a dependency-boundary check until 1E.

## Milestone 1B generic Dune workflow

Completed on 2026-09-20 under the acceptance scope recorded below. Install to a temporary prefix
and copy the generic fixture outside the checkout:

```sh
prefix="$(mktemp -d)"
fixture="$(mktemp -d)"
./scripts/with-switch.sh dune build -p hardcaml_workbench @install
./scripts/with-switch.sh dune install --prefix "$prefix" hardcaml_workbench
cp -R test/fixtures/example_project/. "$fixture/"
rm -rf "$fixture/_build"
```

Launch the installed interactive client from any directory. The inherited environment is an
explicit selection and means the daemon's startup environment; it is never an implicit
Workbench-switch fallback:

```sh
XDG_RUNTIME_DIR="$(mktemp -d)" \
  "$prefix/bin/hardcaml-workbench" \
  --project-root "$fixture" \
  --environment opam:5.2.0+ox
```

Use `--environment inherited` only when the daemon was deliberately started in the project's
environment. Interactive controls are:

```text
b  submit Dune build      t  submit Dune test
c  cancel selected job   j/k  select next/previous job
d  connection details    r  reconnect and refresh
[/] scroll connection details
q or Ctrl-C  exit client only
```

The project pane labels information as generic Dune workspace structure. A compact endpoint and
connection state remain in the header; `d` replaces the project pane with bounded endpoint,
instance, protocol, and environment diagnostics. Driver-dependent Hardcaml hierarchy, RTL, target,
clock, and part operations remain explicitly unavailable until 1C. Jobs and logs remain in the
daemon after the client exits. Starting the same command again reattaches and retrieves
snapshots/log offsets without resubmitting work.

Long roots in the default project pane are middle-truncated to preserve both their leading location
and final project directory. The diagnostics view puts Project, Root, Requested environment,
Resolved environment, and Dune version in separate label/value blocks. It wraps the complete root
on indented lines, preferring path separators and hard-wrapping an individual component only when
necessary. The details header shows its current and maximum scroll offsets; use `[` and `]` to
reach wrapped fields that do not fit the available pane height.

The selected-job detail uses the job state as the prominent outcome and separately reports an exit
code, terminating signal, or launch failure. Absence of a failure string is never presented as
success. The console distinguishes logs not fetched yet, a running job with no output, a finished
job whose logs have not reached EOF, known EOF with no records, and retrieval failure. In
particular, a successful unchanged Dune build or `dune runtest` may legitimately reach EOF without
emitting output; the UI says only that the job finished without stdout/stderr output and does not
claim a cache hit.
While open, the client retries a lost connection from 250 ms up to 5 seconds. A new daemon
instance clears obsolete local session/log offsets, reports the restart, fetches a new snapshot,
and never replays a previous submission.

Non-TTY automation uses the same typed operations:

```sh
"$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox
"$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox \
  --action build --wait
"$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox \
  --action test --wait
```

The adapter uses Dune 3.22 or newer and was validated with 3.24.2. It probes `dune --version`,
inspects with
`dune describe workspace --root ROOT --format=sexp --lang=0.1`, and runs
`dune build --root ROOT --no-buffer @all` or
`dune runtest --root ROOT --no-buffer`. Dune RPC is not used because 3.24.2 marks it
experimental. Only local workspace entries and project-relative display paths cross the API.

### Resize regression and diagnostics

The fixed client repaints on every dimension change, renders a recoverable small-terminal view,
and writes optional diagnostics outside the terminal stream:

```sh
HARDCAML_WORKBENCH_DIAGNOSTICS=/tmp/hardcaml-workbench-resize.log \
  "$prefix/bin/hardcaml-workbench" \
  --project-root "$fixture" --environment opam:5.2.0+ox
```

Automated PTY evidence:

```sh
./scripts/test-terminal-resize.py "$prefix/bin/hardcaml-workbench" \
  --project-root "$fixture" --environment opam:5.2.0+ox
```

On 2026-09-20 this passed `80x24 -> 120x40 -> 40x10 -> 1x1 -> 80x24 ->
100x24 -> 80x24`. Every transition emitted repaint bytes (5998, 826, 230, 2714, 3198,
2714 respectively), the process remained responsive, diagnostics contained each dimension,
and normal rendering recovered after growth. This is automated PTY evidence, not real-terminal
acceptance.

Human acceptance confirmed that repeated resizing works while navigating in the intended
server-side TUI over SSH. The user also confirmed visible Dune information and unavailable
hierarchy labeling, build/test submission and completion, selection of earlier per-job logs, and
state recovery after `q` and relaunch. This records only those observations: it does not claim that
both Ghostty and Xfce Terminal, with and without tmux, were each retested. The user did not report
seeing the small-terminal fallback and did not confirm crossing its 68x20 character-cell threshold,
so that is not treated as a failure. Automated PTY repaint evidence remains separate from this
human visual acceptance.

### Attached remote daemon

Two SSH workflows must not be conflated. The accepted current deployment runs both daemon and
terminal client on the headless server and carries the terminal over an ordinary SSH session. The
following deferred check instead installs and runs a separate native client on the workstation and
attaches it to the server daemon's HTTP endpoint through a port forward.

On an authorized remote project host:

```sh
ssh project-host
/installed/prefix/bin/hardcaml-workbench-daemon --port 8080
```

On the workstation, in another terminal:

```sh
ssh -N -L 18080:127.0.0.1:8080 project-host
/installed/prefix/bin/hardcaml-workbench \
  --connect http://127.0.0.1:18080 \
  --project-root /absolute/project/path/on/project-host \
  --environment opam:PROJECT_SWITCH
```

Confirm that the displayed root and Dune version are remote, start a build, exit the client while
it is running, reconnect with the same command, and verify one job with continuing logs. Cancel
it from a second attached client and verify both clients observe `Cancelled` while retaining
their own selected rows. This workstation-native/forwarded-endpoint check is explicitly deferred
by the user. It is not recorded as passed, and a local tunnel or second local client is not
substitute evidence. The capability and commands remain here for later validation, but this
deferred check does not block 1B under the user-approved acceptance scope.

### 1B human acceptance and UI follow-up

The user accepted the following server-side interactive workflow on 2026-09-20:

- repeated resize, including while navigating, recovers and remains usable;
- generic Dune items/workspace information is visible and hardware hierarchy is explicitly
  unavailable until project-driver integration;
- jobs, live stdout/stderr, and hotkeys are visible;
- `b` creates a job that completes, and `t` works with observed fixture test output;
- selecting earlier jobs displays their corresponding build/test logs;
- later repeated build/test jobs may complete with no output;
- `q` followed by relaunch restores daemon-owned project and job state.

The user subsequently confirmed that the diagnostics toggle, clear job status/log presentation,
repeated no-output builds/tests, resize behavior, and quit/reopen recovery all pass. The remaining
presentation polish middle-truncates the default root and makes every full diagnostic field
available through bounded wrapping and `[`/`]` scrolling. Workstation-native attachment through a
forwarded HTTP endpoint remains deferred and is not part of this confirmation.

The UI follow-up addresses the two ambiguous presentations exposed by that review. Selected jobs
now show `Complete`, `Failed`, or `Cancelled` prominently with process exit code, signal, launch
failure, and any separate failure reason. Per-job log fetch state retains the protocol EOF bit, so
an empty terminal log is distinguished from not-yet-fetched, still-running, still-draining, and
retrieval-error states. Responses are stored only under the requested job and ignored after a
daemon-instance change, preventing selection or reconnect races from presenting another job's log
as current. Connection diagnostics moved from the default project content into the bounded `d`
details view.

### 1B validation evidence

The following passed serially on 2026-09-20:

```sh
./scripts/with-switch.sh dune build @fmt
./scripts/with-switch.sh dune build @lint
./scripts/with-switch.sh dune runtest
./scripts/with-switch.sh dune build
./scripts/with-switch.sh dune build -p hardcaml_workbench @install
./scripts/with-switch.sh opam lint hardcaml_workbench.opam
./scripts/with-switch.sh opam lint hardcaml_workbench_web.opam
./scripts/with-switch.sh dune describe external-lib-deps
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh
OPAM_SWITCH=5.2.0+ox ./scripts/test-native-application.sh
```

Protocol tests cover every new codec and logs remaining outside snapshots. Adapter tests cover
environment argv, Dune versions, local-only workspace parsing, and typed build/test translation.
Backend tests cover live stdout/stderr, success, nonzero exit, launch failure, signal death,
cancellation, descendant cleanup, shutdown, FIFO scheduling, file-backed bounded log paging and
EOF, deduplication/conflicts, and snapshot/event consistency. RPC tests cover all routes,
capabilities, malformed/instance errors, populated snapshots/events, retained-cursor behavior,
and real log retrieval. Installed acceptance opens a copied external fixture, observes start
output before process completion, runs build/test, reattaches without duplicate jobs, uses two
observers, rejects invalid roots/environments, and retains the 1A lifecycle checks. Dependency
inspection confirms the terminal role still reaches only native HTTP and protocol application
roles, not backend, adapter, or project-integration code.

The acceptance/UI follow-up was revalidated serially on 2026-09-20 with the same four repository
commands, package install build, external fixture script, and installed native application script
listed above. `dune runtest` includes focused presentation-state tests for queued/running versus
terminal outcomes, exit code, signal, launch failure, missing failure reason, empty logs before EOF,
known empty EOF, draining, and retrieval error. The installed PTY command also passed
`80x24 -> 120x40 -> 40x10 -> 1x1 -> 80x24 -> 100x24 -> 80x24`, with repaint byte counts
`6002, 826, 230, 2722, 3202, 2722`; it additionally verified that daemon identity is absent from
the default project pane, appears in the bounded `d` details view, and that the project pane returns
after closing details. This remains automated terminal-protocol evidence rather than a claim about
visual appearance in a particular real terminal.

The subsequent field-rendering PTY regression repeats the same resize sequence, checks that
diagnostics scrolling exposes Requested environment, Resolved environment, and Dune version, then
closes details and verifies that the project pane recovers. Pure presentation tests additionally
check bounded middle truncation, preservation of the final project directory when it fits,
separator-aware full-path wrapping, and fallback wrapping for a component wider than the pane.

The terminal executable now also links a private terminal-presentation helper used for these pure
tests. Its application-role dependency closure remains the native HTTP client and portable
protocol; it has no backend, adapter, or project-integration dependency.

## Milestone 1C discovery slice

The first bounded 1C slice implements optional manifest version 1 and project-driver describe
protocol version 1. It does not implement target selection, elaboration, RTL, hardware hierarchy,
artifacts, or complete provenance. The authoritative contracts are in architecture section 4.1.

The fixture now contains `hardcaml-workbench.sexp` and
`workbench/project_driver.exe`. The driver links the fixture's counter library and genuinely
declares target key `counter` plus configuration key `default`; Workbench does not link or load the
fixture module. The copied fixture remains an ordinary external project and its build, tests, and
driver work directly:

```sh
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh
```

Install and launch from outside the checkout exactly as before. Initial open queues discovery once;
repeat launch and reconnect only observe the daemon-owned result:

```sh
prefix="$(mktemp -d)"
fixture="$(mktemp -d)"
./scripts/with-switch.sh dune build -p hardcaml_workbench @install
./scripts/with-switch.sh dune install --prefix "$prefix" hardcaml_workbench
cp -R test/fixtures/example_project/. "$fixture/"
rm -rf "$fixture/_build"
cd /tmp
XDG_RUNTIME_DIR="$(mktemp -d)" \
  "$prefix/bin/hardcaml-workbench" \
  --project-root "$fixture" --environment opam:5.2.0+ox
```

The project pane shows manifest/driver availability, discovery job state, and target/configuration
summaries. Press `i` to reload the manifest and rerun discovery. This clears old summaries while
the new result is pending, so a failed refresh cannot look current. `r` remains reconnect only and
does not rerun discovery. Deterministic non-TTY refresh is:

```sh
XDG_RUNTIME_DIR="$same_runtime" \
  "$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox \
  --refresh-integration --wait
```

Manifest-only projects use declared aliases. Invalid or unsupported manifests use safe generic
`@all`/`@runtest` aliases, preserve generic build/test, and expose the validation reason. Driver
build/exit, malformed output, protocol incompatibility, missing capability, output limit, and
cancellation failures are job outcomes plus integration diagnostics. Driver stdout is the bounded
structured result; stderr remains diagnostic output in the job log. All supervised build, test,
and driver work for one canonical root, including sessions selecting different environments,
shares one Workbench FIFO; bounded open-time inspection continues to rely on Dune's own lock.

Validation completed on 2026-09-20 with OCaml `5.2.0+ox` and Dune `3.24.2`:

```sh
./scripts/with-switch.sh dune build @fmt                         # passed
./scripts/with-switch.sh dune build @lint                        # passed
./scripts/with-switch.sh dune runtest                            # passed
./scripts/with-switch.sh dune build                              # passed
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh           # passed
OPAM_SWITCH=5.2.0+ox ./scripts/test-native-application.sh        # passed
./scripts/with-switch.sh dune describe external-lib-deps         # boundary confirmed
./scripts/with-switch.sh dune build -p hardcaml_workbench @install # passed
./scripts/with-switch.sh opam lint hardcaml_workbench.opam       # passed
./scripts/with-switch.sh opam lint hardcaml_workbench_web.opam   # passed
```

The installed script performs the temporary-prefix install and outside-checkout launch. It also
runs the PTY regression through `120x40`, `40x10`, `1x1`, `80x24`, `100x24`, and `80x24`; repaint
byte counts were `6002`, `826`, `230`, `2718`, `3202`, and `2718`. The dependency report confirms
the terminal still reaches only native HTTP, presentation, and protocol roles, and that application
libraries have no fixture/Hardcaml dependency. Fixture output records
`OPAM_SWITCH_PREFIX=/home/wayne/.opam/5.2.0+ox`, providing direct evidence that its driver ran in the
explicitly selected project environment.

### 1C live discovery synchronization repair

The first real-terminal 1C check found a gap that the earlier passing tests did not cover. Initial
discovery completed and its structured output was valid, but the still-attached client continued to
show the pending project. Quitting and reopening immediately showed the daemon's cached driver,
target, and configuration without starting another job.

The daemon had already decoded and stored the result and normally published its `Project_upsert`
before the terminal `Job_upsert`. The terminal defect was in project selection: its fallback used
`Option.first_some` with the open response as the preferred argument, so the pending response always
won over the newer snapshot project. The polling loop also discarded incremental events and fetched
a full snapshot after every poll, contrary to the application protocol's ordinary update path.

The terminal now applies sequenced project, job, artifact, removal, and log-availability events to
its local snapshot. It ignores already-applied events, rejects gaps/cursor disagreement, and uses a
full snapshot only for initial attach, retained-event resynchronization, or reconnect. The current
project prefers the event-reduced record and uses the open response only until that project appears.
Submit/refresh/cancel responses add an absent job but do not replace a newer event-applied state.
Driver process-launch failure now follows the same project-result-before-terminal-job ordering as
the other discovery outcomes. Target and configuration names precede their long internal IDs in the
bounded terminal rows so the useful part remains visible.

Regression coverage now includes:

- a pending open response followed by production `Project_upsert` and `Job_upsert` reduction in the
  same client state used by the terminal view, yielding the real target and configuration;
- job-complete/project-result ordering, changed refresh data, failed refresh clearing old summaries,
  duplicate/cursor handling, and an update for another project not replacing the selected project;
- backend publication ordering for successful, malformed, incompatible, nonzero, and process-launch
  failure results;
- an installed no-input PTY that starts from pending discovery and observes `Integration: Driver`
  plus `Four-bit counter` in that same process before resize/navigation checks; and
- installed plain refresh waiting through incremental events and printing the post-refresh target and
  configuration without a second open, reconnect, or fresh snapshot.

Final validation on 2026-09-20 used OCaml `5.2.0+ox` and Dune `3.24.2`:

```sh
./scripts/with-switch.sh dune build @fmt                           # passed
./scripts/with-switch.sh dune build @lint                          # passed
./scripts/with-switch.sh dune runtest                              # passed
./scripts/with-switch.sh dune build                                # passed
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh             # passed
OPAM_SWITCH=5.2.0+ox ./scripts/test-native-application.sh          # passed
./scripts/with-switch.sh dune build -p hardcaml_workbench @install # passed
```

The installed acceptance used fresh temporary prefixes, external fixture copies, and private runtime
directories. Its generic resize run retained repaint counts `6002`, `826`, `230`, `2718`, `3202`,
and `2718`. The discovery run reported `Attached-client live discovery: passed` and then passed the
same resize stages; its repaint counts after the initial wide discovery frame were `924`, `826`,
`230`, `2718`, `3202`, and `2718`. This is automated protocol/PTY evidence. The user's final visual
confirmation in the original SSH/tmux workflow was still pending at that point; the later acceptance
record below supersedes that pending state.

For that fresh-shell retest, create a new install, external fixture, and private daemon runtime, and
save their paths in a sourceable file:

```sh
cd /path/to/hardcaml_workbench
state="$(mktemp /tmp/hardcaml-workbench-1c-live.XXXXXX.env)"
prefix="$(mktemp -d /tmp/hardcaml-workbench-1c-prefix.XXXXXX)"
fixture="$(mktemp -d /tmp/hardcaml-workbench-1c-fixture.XXXXXX)"
runtime="$(mktemp -d /tmp/hardcaml-workbench-1c-runtime.XXXXXX)"
./scripts/with-switch.sh dune build -p hardcaml_workbench @install
./scripts/with-switch.sh dune install --prefix "$prefix" hardcaml_workbench
cp -R test/fixtures/example_project/. "$fixture/"
rm -rf "$fixture/_build"
printf 'export HCW_PREFIX=%q\nexport HCW_FIXTURE=%q\nexport HCW_RUNTIME=%q\n' \
  "$prefix" "$fixture" "$runtime" >"$state"
printf 'Saved session paths: %s\n' "$state"
printf 'Prefix: %s\nFixture: %s\nRuntime: %s\n' "$prefix" "$fixture" "$runtime"
```

In that shell, launch from outside the checkout:

```sh
source "$state"
cd /tmp
XDG_RUNTIME_DIR="$HCW_RUNTIME" \
  "$HCW_PREFIX/bin/hardcaml-workbench" \
  --project-root "$HCW_FIXTURE" \
  --environment opam:5.2.0+ox
```

Without pressing a key, the pending discovery should become `Integration: Driver`,
`driver=available v1`, `Discovery: Complete`, `Target: Four-bit counter`, and
`Configuration: Default four-bit counter`. After `q`, source the printed state file in any fresh
shell and rerun the same launch command to verify cached repeat-open against the same new daemon; it
must retain job 1 and must not rediscover automatically. Pressing `i` should create job 2 and update
the same attached view through incremental events.

## Milestone 1C RTL generation and artifacts slice

The second bounded 1C slice adds client-local target/configuration selection and one supervised
`generate-rtl` driver operation. The fixture driver elaborates the real Hardcaml counter and emits
configuration-specific Verilog: `counter-4.v` has a four-bit `count_o`, while `counter-8.v` has an
eight-bit `count_o`. Driver diagnostics remain in the job log and the structured result names output
files; generated bytes do not pass through the driver result envelope.

The daemon creates a private output directory per job, validates and imports all declared outputs,
registers immutable daemon-lifetime artifacts, and removes driver output directories after use.
Snapshots and events expose metadata and IDs only. `read-artifact` provides bounded content pages;
same-daemon reconnect can retrieve an earlier artifact without revealing its storage path. Artifact
upserts and the job's artifact IDs are published before the terminal successful job event.

The terminal selects the first valid target/configuration by default, preserves valid selections
across refresh, and provides `n`, `m`, `g`, `a`, and `v` for target, configuration, generation,
artifact selection, and content inspection. Plain automation can generate and retrieve content:

```sh
"$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox \
  --action generate-rtl --target "Four-bit counter" \
  --configuration "4-bit counter" --wait
"$prefix/bin/hardcaml-workbench" --plain \
  --project-root "$fixture" --environment opam:5.2.0+ox \
  --artifact "$artifact_id"
```

Provenance captures source state at generation start and completion. It records deterministic
SHA-256 observations excluding `.git` and `_build`, Git commit/dirty context when available, the
selected environment and Dune version, and tool versions reported by the project driver. Clean Git
inputs with equal boundary observations are exact for this model; dirty commits are context only,
and changed or failed observations are represented as unknown rather than overstated.

Validation passed serially on 2026-09-20 with OCaml `5.2.0+ox` and Dune `3.24.2`:

```sh
./scripts/with-switch.sh dune build @fmt                           # passed
./scripts/with-switch.sh dune build @lint                          # passed
./scripts/with-switch.sh dune runtest                              # passed
./scripts/with-switch.sh dune build                                # passed
./scripts/with-switch.sh dune build -p hardcaml_workbench @install # passed
./scripts/with-switch.sh opam lint hardcaml_workbench.opam         # passed
./scripts/with-switch.sh opam lint hardcaml_workbench_web.opam     # passed
./scripts/with-switch.sh dune describe external-lib-deps           # boundary confirmed
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh             # passed
OPAM_SWITCH=5.2.0+ox ./scripts/test-native-application.sh          # passed
```

Focused tests cover protocol framing and validation, adapter argv, refresh reconciliation, stale and
mismatched selections, capability absence, failure/cancellation cleanup, artifact isolation and
retrieval, event ordering, and clean/dirty/non-Git provenance. The installed workflow generates and
retrieves both fixture configurations, verifies reconnect metadata, retains generic and manifest-only
workflows, and repeats the discovery and resize regressions. `dune describe external-lib-deps`
confirms the terminal still reaches only native HTTP, presentation, and protocol roles, and that the
application does not link the fixture's Hardcaml circuit. At that validation point, structured
hierarchy extraction remained the next 1C slice.

The user subsequently completed the full RTL/artifact human checklist in the intended server-side
terminal workflow on 2026-09-20. They confirmed target/configuration selection, distinct four-bit and
eight-bit Verilog, artifact content inspection and isolation, resize/navigation while using those
views, and quit/reconnect recovery without regenerating artifacts. This is human acceptance of the
second bounded slice only. It does not claim hierarchy acceptance or complete milestone 1C, and the
workstation-native SSH-forward check remains explicitly deferred.

## Milestone 1C elaborated hierarchy slice

The final implementation slice adds a version-1 hierarchy sidecar emitted by the same
`generate-rtl` elaboration as Verilog. The fixture genuinely elaborates `counter_top` with repeated
`u_counter_0` and `u_counter_1` occurrences of circuit `counter`; the driver walks Hardcaml
instantiations and its circuit database rather than maintaining a second labeled fixture tree.
Structural keys are deterministic occurrence paths: `/` for the root and a byte-length-prefixed
segment per child, such as `/11:u_counter_0`.

The daemon imports RTL and hierarchy atomically, associates the decoded hierarchy with its project,
target, configuration, generating job, RTL artifacts, and provenance, and serves it through the
additive `read-hierarchy` V1 operation. A driver without `generate-rtl-hierarchy` remains RTL-capable;
an unadvertised sidecar is readable as a generic artifact but not accepted as structured hierarchy.
Validation limits the sidecar to 8 MiB, 10,000 nodes, depth 256, 4,096 combined ports or metadata
entries per node, and 4,096 bytes per string. Registration is the commit point, so a cancellation
received from a registration event cannot leave a cancelled job owning committed artifacts.

The terminal uses `h` to open/close hierarchy inspection, `u` and `o` to select the previous/next
visible node, `e` to collapse/expand, and `[`/`]` to scroll the compact pane. The inspector shows
instance/circuit names, structural key, ports, and metadata. A view is `[current]` only when its
generating job is the newest generation attempt for the exact current target/configuration;
otherwise it is `[historical]`. Plain mode retrieves a hierarchy by immutable artifact ID with
`--hierarchy ARTIFACT_ID`.

Automated validation on 2026-09-20 used OCaml `5.2.0+ox` and Dune `3.24.2`. It covers hierarchy
codecs and framing; malformed, duplicate, disconnected, cyclic, and oversized trees; combined port
name uniqueness; bounded deep-parent rejection; repeated-instance identity; configuration-specific
widths; missing/invalid hierarchy cleanup; RTL-only capability behavior; capability pinning across a
concurrent refresh; the registration-boundary cancellation race; retrieval and reconnect; exact
current/historical selection; identity-stable live job selection; attached-client navigation and
root collapse/expansion; compact inspector scrolling; and resize recovery. The full serial gate is:

```sh
./scripts/with-switch.sh dune build @fmt                           # passed
./scripts/with-switch.sh dune build @lint                          # passed
./scripts/with-switch.sh dune runtest                              # passed
./scripts/with-switch.sh dune build                                # passed
./scripts/with-switch.sh dune build -p hardcaml_workbench @install # passed
./scripts/with-switch.sh opam lint hardcaml_workbench.opam         # passed
./scripts/with-switch.sh opam lint hardcaml_workbench_web.opam     # passed
./scripts/with-switch.sh dune describe external-lib-deps           # boundary confirmed
FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh             # passed
OPAM_SWITCH=5.2.0+ox ./scripts/test-native-application.sh          # passed
```

Final hierarchy UI acceptance passed on 2026-09-20, as recorded below. To repeat it,
first run the setup block at lines 712–726 and
retain the exact state-file path it prints. In a fresh shell, replace the placeholder below with that
path; the shell-local `$state` variable itself is not preserved:

```sh
STATE_FILE=/tmp/hardcaml-workbench-1c-live.XXXXXX.env
source "$STATE_FILE"
cd /tmp

four_output="$(
  XDG_RUNTIME_DIR="$HCW_RUNTIME" \
    "$HCW_PREFIX/bin/hardcaml-workbench" --plain \
    --project-root "$HCW_FIXTURE" \
    --environment opam:5.2.0+ox \
    --action generate-rtl \
    --target "Four-bit counter" \
    --configuration "4-bit counter" \
    --wait
)"
printf '%s\n' "$four_output"
four_hierarchy="$(
  grep -E '^Artifact .*: counter-4 hierarchy ' <<<"$four_output" |
    cut -d' ' -f2 |
    tr -d ':'
)"
test -n "$four_hierarchy"

XDG_RUNTIME_DIR="$HCW_RUNTIME" \
  "$HCW_PREFIX/bin/hardcaml-workbench" --plain \
  --hierarchy "$four_hierarchy"

XDG_RUNTIME_DIR="$HCW_RUNTIME" \
  "$HCW_PREFIX/bin/hardcaml-workbench" \
  --project-root "$HCW_FIXTURE" \
  --environment opam:5.2.0+ox
```

The plain tree must contain `counter_top`, `u_counter_0`, `u_counter_1`,
`/11:u_counter_0`, and `/11:u_counter_1`. In the interactive client, verify that `h` opens
`HARDWARE HIERARCHY [current]`; `o` selects `u_counter_0` and shows `count_o[4]`; `u`, then `e`,
collapses and re-expands the root; `[`/`]` reveal the inspector in a compact terminal; resizing
recovers the same hierarchy; and `q` exits without stopping the daemon. Source the same exact state
file in another fresh shell and relaunch to confirm the existing generation and hierarchy remain
available without automatic rediscovery or RTL regeneration.

### Final 1C human acceptance — 2026-09-20

The user performed the final installed hierarchy checklist in the intended server-side terminal
workflow and confirmed that every item passed:

- Hierarchy appeared live after generation without reopening or manual refresh.
- The real `counter_top` root and both `u_counter_0` / `u_counter_1` occurrences were visible,
  with distinct structural keys and correct four-bit port inspection.
- Node navigation, root collapse/expansion, compact scrolling, and resize recovery worked.
- Generating the eight-bit configuration showed the correct widths; the earlier four-bit result
  remained accessible with historical labeling rather than appearing current for the new selection.
- Quit/reconnect retained the generation results and hierarchies without rediscovery or regeneration.

Together with the preceding automated gates and already accepted discovery and RTL/artifact slices,
this completes milestone 1C. The delivered backend is structured hierarchy from the same project-side
elaboration as RTL, atomically imported with result/provenance association and retrieved by immutable
artifact ID through `read-hierarchy`; it is not a per-node report or a full signal/operator graph.
This acceptance does not claim every terminal/tmux combination was tested. Workstation-native
attachment through an SSH-forwarded HTTP endpoint remains explicitly deferred. The separately
planned D1–D4 dashboard workflow and its own live acceptance requirements are unchanged.
