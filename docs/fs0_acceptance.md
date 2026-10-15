# FS0 native acceptance evidence

Executed 2026-10-15 using the parent's already built
`_build/default/{daemon,terminal}/main.exe`. **Fixture and real synthesis FS0
acceptance passed.** Real balanced/synth_delay counts were **673/685**;
acceptance remains **`not_evaluated`**. The initial timeout CLI failure is retained
below, followed by the successful explicitly authorized configuration correction.

## Reusable harness

`scripts/test-fs0.py` uses Python's standard library, starts its own loopback daemon,
and invokes the native terminal with `--api --plain --project-root ROOT --connect
URL --asic-operation SEXP --wait`. Run is first submitted without wait, and fresh
clients poll Get for early allocation, then use `Get --wait` for completion.
Workspace commands use the corresponding
`--workspace-operation` without wait. It preserves raw stdout, stderr, argv, exit
status and elapsed time per command, daemon logs, PTY bytes, state, fake-provider
calls and a machine-readable outcome. It stops its own daemon on success/failure.

```sh
# Fixtures only; creates a unique retained evidence directory.
python3 -B scripts/test-fs0.py

# Fixtures first, then strictly serial balanced and synth_delay synthesis.
python3 -B scripts/test-fs0.py --real

python3 -B scripts/test-fs0.py --help
```

Options: `--client`, `--daemon`, `--evidence` (must not already exist),
`--example-root`, `--project`, `--provider`, `--tools`, and `--outer-timeout`
(positive, at most 1800 seconds), plus `--stage-timeout-seconds` (positive,
opt-in for newly created config only). New configs default to `()` for the optional
stage timeout, compatible with the retained prebuilt project. Defaults use the exact recommended executable
pair and tool paths in `fs0_environment_inventory.md`. The harness never builds
Workbench/provider, installs dependencies, invokes Git, or removes evidence.
The generic fixture test uses the daemon's bounded runtime `dune build -j20
--root ROOT --no-buffer @runtest` in an owned temporary Dune project.

Real opt-in configuration is created **only if absent**, using exclusive file
creation. Existing configuration is preserved and remains authoritative. A rerun
with an existing config therefore uses its existing results root; the harness
does not silently retarget it to the new evidence directory. For a fresh real
namespace, the owner must deliberately prepare the configuration before rerunning.
Config is read once per daemon. State is always separate from provider results.

The created example configuration points at:

```text
project  /home/wayne/devel/jane/hardcaml_asic_example/_build_namedflow_real/default/bin/project.exe
provider /tmp/opencode/namedflow-real-20261015/provider/bin/hardcaml-asic-flow
results  /tmp/opencode/workbench-fs0-6_1ymcsd/results
tools    /home/wayne/devel/jane/hardcaml_asic_example/_flow_tools
timeout  () (provider default per-stage budget; no optional --timeout argument)
```

Python, support tools and PDK use the inventory's `.venv/bin/python`, `tt`, and
`pdk` under that tools root. The daemon receives all three 20-thread environment
variables. The retained installed provider supplies Docker's 20-CPU/thread
limits. No placement/signoff request was submitted. Real profiles run serially.
Workbench enforces a hard **1800-second shared launcher/automatic-observer deadline**
starting before metadata lookup, with bounded owned-child cleanup; allocation does
not restart it. Client wait is at most **1800 seconds**. Provider-default per-stage
timeouts remain in force. Failure stops before the next profile.

## Executed fixture acceptance

Primary retained evidence:
`/tmp/opencode/workbench-fs0-6_1ymcsd/fixture/`.

- Generic project-scoped test returned `Complete`, emitted the fixture marker and
  created `_build/default/generic-passed` containing `passed`.
- Actual 120×40 PTY rendered Overview. Input **Space c c**, filtered command
  `Make workspace independent`, and Enter caused a persisted workspace revision
  increase and independent Overview context. `2`, Tab, `j`, `k`, `1` and `q` were
  sent; client exited zero. Raw rendering/input-result evidence is `pty.ansi` and
  the before/after workspace responses. This checks rendering and real transport
  submission beyond reducer tests; it is not a full visual/layout audit.
- Discover and Describe returned `standard` with both profiles. Plan used explicit
  `synthesis`; Run passed the complete returned preview unchanged.
- Allocated exact run IDs `stream-balanced` and `stream-synth_delay`; terminal
  synthesis summaries had counts **50** and **73**, completion `completed`,
  acceptance **`not_evaluated`**, and unsupported timing `[]`.
- Repeating the same launch keys produced no additional registered runs.
- Workspace operations linked both workspaces to Main, selected balanced, made
  Timing independent, selected delay there, pinned balanced and moved that tile to
  Timing. A stale global CAS was rejected with `Conflict`.
- Three alternating warm loads of both runs retained exact summary records.
  Public report calls stayed **2 → 2**, including restart.
- Restart changed daemon identity, restored the complete workspace snapshot
  exactly (session, revision, contexts/selections, tile pin and move), and loaded
  L2 summaries with **`Cached_unverified`**. Every summary field except freshness
  matched the pre-restart record, including digest, exact execution reference,
  plan identity, count and original observation time.
- Actual HTTP requests with an old daemon identity returned `Instance_changed`;
  current identity plus nonexistent project returned `Not_found`.

`fixture/verified.json` contains full original summaries, workspace and both
daemon identities. `fixture/raw-http.jsonl` retains instance/project checks.

## Initial real attempt: preserved timeout CLI failure

Command: `python3 -B scripts/test-fs0.py --real`.
Root: `/tmp/opencode/workbench-fs0-6_1ymcsd/`.

Real discovery, description and balanced synthesis preview succeeded. Launch key
`fs0-balanced` failed **before allocation**, because the inventoried prebuilt
project rejects the timeout argument forwarded by the adapter:

```text
run:fs0-balanced: (monitor.ml.Error
  (Failure
    "ASIC command failed: project flow run: unknown option '--timeout'.
Usage: project describe | emit | preflight | run [OPTIONS]
       project flow list | describe | plan | run [OPTIONS]
...")
... backend/asic_process.ml ...)
```

This is a **project command-line parsing error**, not a JSON report parsing error
or an EDA failure. The terminal returned exit **1** while stdout retained the full
`(Ok SNAPSHOT)` containing the failed operation. Exit status was checked before
treating the snapshot as completion evidence.

Exact evidence:

- `real/001-asic.*`: discovery.
- `real/002-asic.*`: description.
- `real/003-asic.*`: balanced preview, full returned plan JSON/identity.
- `real/004-asic.json`: actual terminal argv, elapsed time and exit 1.
- `real/004-asic.stdout`: full daemon response/operation failure.
- `real/004-asic.stderr`: full exception and project usage, without truncation.
- `real/state/`: retained registry/cache state.
- `outcome.json`: fixture pass and real exception.

No real allocation, report, cell count, acceptance result, warm identity or restart
identity is available from this attempt. synth_delay was not launched. The provider
and project binaries were preserved. This historical attempt used the then-required
600-second timeout. The user subsequently explicitly authorized changing only
the newly created example config's `stage_timeout_seconds` to `()`.

## Successful real rerun

Executed `python3 -B scripts/test-fs0.py --real` after the authorized config-only
timeout correction. Full retained evidence:
**`/tmp/opencode/workbench-fs0-91em64rl/`**. Fixture HTTP/PTY/cache/restart checks
passed first, including early allocation for both fake profiles and report calls
remaining 2 → 2. Then real profiles ran serially to completion, followed by warm
switching, workspace operations and daemon restart/L2 checks.

The example config's results root was preserved:
`/tmp/opencode/workbench-fs0-6_1ymcsd/results`. The initial failure had allocated
nothing there. Fresh successful run state and command evidence are under the new
`workbench-fs0-91em64rl/real/` directory, physically separate from results.
No adapter, provider or project executable was changed; no Git command, install
or overlapping build/flow was run during this rerun.

| Profile | Cell count | Public run/stream ID | Completion | Acceptance |
| --- | ---: | --- | --- | --- |
| balanced | 673 | `8158dc95a6e44b1a993a95721ebc0ab0` | completed | not_evaluated |
| synth_delay | 685 | `c0db1f70fa484c829bc9062896290ed3` | completed | not_evaluated |

Exact report references, under the configured results root:

```text
balanced:
  synthesis-669357-063b144e08d44fc81921455c055e9df7/execution-8158dc95a6e44b1a993a95721ebc0ab0.json
synth_delay:
  synthesis-670587-205b13e7078f1c4c1656cb4411028998/execution-c0db1f70fa484c829bc9062896290ed3.json
```

Balanced plan identity:
`99c7d37913f89576d7006451a9c4da9c2ea023887179d47d3912cc607b4fd5c5`.
Delay plan identity:
`69103f13d8593d442f79f93b8b3f59a72b32bca3c014755bfa1a85e9d83ffa8a`.
Normalized report digests respectively:
`62a96dcb402eff089e4486bfc17182903257d456add65290303d569250142fa8`,
`663d1d95ccdf2c487e4e9c8fdb28fe2a1b3f7a8e8e65adf27e64e1a658dba565`.

For each profile, the Run submission client returned and exited before new Get
clients observed allocation with the launcher still **`executing`**. These
snapshots are saved as `real/{balanced,synth_delay}-early-allocation.json`,
including exact attempt/stream references and operation state. Subsequent
`Get --wait` clients observed completion, demonstrating daemon-owned work survives
submission-client detach. This records allocation before launcher completion;
it does not independently timestamp the provider pipe's EOF syscall.

Three alternating warm loads retained each original summary exactly. After daemon
restart, all summary fields except freshness matched exactly, including the
digests above, execution references, plans, counts and original observation times.
Freshness correctly became `Cached_unverified`. The complete workspace snapshot
(linked and independent contexts, selected runs, pinned/moved tile) restored exactly.
Daemon identity changed from `669303-1792061175345541978-34ae941c` to
`671839-1792061228017916619-2a3ccdcc`; old-instance and unknown-project HTTP checks
also passed. Duplicate launch keys did not allocate additional runs.

`real/verified.json` contains full summaries, workspace and both daemon identities;
`outcome.json` records both fixture and real `passed` outcomes. Every native client
command has `.json`, `.stdout`, `.stderr` evidence. Real provider call counts are
not instrumented (`null` in verified.json); zero extra reports is directly counted
by the fake provider, while the real warm/restart checks assert returned identity
and data stability. Timing remains `[]` (unsupported), not zero slack. The counts
are checkpoint boundary snapshots, not per-step attribution or signoff acceptance.

## Cached real synthesis tile: live PTY reopening

After the frontend's explicit synthesis-tile/compact-renderer fix, executed:

```sh
python3 -B scripts/test-fs0.py --reopen-real /tmp/opencode/workbench-fs0-91em64rl
```

**Passed**, with fresh evidence at **`/tmp/opencode/workbench-fs0-unzwt0kn/`**.
This mode skips fixture builds and EDA, reuses the accepted `real/state` in place
(single owned daemon), and verifies cached summaries against the original
`real/verified.json`. It never writes configuration or provider results, and
submits no Run, Observe, Refresh or discovery operation. Its explicit ASIC
requests are Load_summary and Get; loaded terminal runs create no automatic
observation interest. Existing acceptance evidence is preserved.

The harness created a dedicated Main-linked workspace using typed workspace RPC:

```text
Title:          FS0 Real Demo 1792063225057192206
Workspace:      workspace-10
Pinned tile:    tile-11 (balanced, 673)
Following tile: tile-12 (Main selects synth_delay, 685)
```

At **120×40**, an actual interactive client opened **Space c c**, searched for
`Switch to FS0 Real Demo 1792063225057192206`, and pressed Enter. While attached:

1. Zoomed synthesis tile displayed **Cell count: 673** and `Cached_unverified`.
2. Typed RPC changed Main's selected run to the exact delay Run_ref. The current
   rendered screen changed to **685**, with no stale **Cell count: 673**.
3. Typed RPC pinned that tile to the exact balanced Run_ref. Its current screen
   returned to **673**, with no **Cell count: 685**, while Main remained on delay.
4. A second synthesis tile followed Main. Unzooming rendered **673 and 685
   simultaneously**, labeled PIN and FOLLOW. Both showed completion `completed`,
   acceptance `not_evaluated` and freshness `Cached_unverified`.
5. RPC assertions verified selected run, pin/follow bindings and unchanged registry
   during rendering. Client exited zero. Daemon restart restored the entire final
   registry exactly, including the dedicated workspace and both synthesis tiles.

Evidence files `01-balanced`, `02-delay`, `03-pinned-balanced`, and
`04-pinned-and-following` each have `.ansi` transcripts and reconstructed `.txt`
screens. Assertions use a small standard-library ANSI screen reconstruction to
test the current screen, rather than searching old incremental rendering bytes.
`reopen-verified.json` records full original evidence identities and the saved
workspace; all typed commands have their usual argv/exit/stdout/stderr evidence.
`reopen-pty.ansi` retains the full interactive transcript.

One earlier reopen attempt is retained at
`/tmp/opencode/workbench-fs0-2d5es66i/`: its harness screen decoder initially
omitted ANSI CSI E (next-line) handling, misplacing unchanged rows. The actual
terminal stream already contained 673/685 and cached freshness correctly. Only
the harness decoder was corrected. Its earlier dedicated workspace is preserved;
the successful demo title above identifies the complete two-tile workspace.

See the repository README's **Open the accepted real synthesis demo** section
for native launch commands. Repeated `--reopen-real` runs add a uniquely named demo
workspace and intentionally change Main selection, preserving existing tiles and
provider evidence. `--client`, `--daemon`, `--example-root`, `--evidence` and
`--outer-timeout` work as usual; `--real` and `--reopen-real` are mutually exclusive.
No Dune, build, EDA, install or Git command was run for this reopening check.

## Other retained attempts and scope

Two earlier harness-development attempts remain intact:
`/tmp/opencode/workbench-fs0-cr7kq9ec` (assertion expected `Succeeded`, whereas the
generic job correctly returned `Complete`) and
`/tmp/opencode/workbench-fs0-t7st4vtt` (harness tokenizer initially mishandled
adjacent Sexplib quoted atoms). Both were harness-only fixes. No real launch
occurred in those attempts. Final fixture-only verification after strengthening
count/CAS assertions passed with `python3 -B scripts/test-fs0.py`; its complete
retained evidence is `/tmp/opencode/workbench-fs0-etbs6c68/`, including
`fixture/verified.json` and `outcome.json`.

This acceptance does not replace the parent's already passed build/runtest suite.
It does not cover every malformed-provider, cancellation, resize, concurrent-client
race or interactive launch-and-view path. The fixture specifically proves native
HTTP, command submission, two-profile summaries and durable workspace/L2 identity;
the real installed-provider rerun additionally proves serial physical synthesis,
early allocation/client-detach survival and stable warm/restart evidence identity.
