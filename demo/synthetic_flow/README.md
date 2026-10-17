# Synthetic flow demo

For the two-terminal walkthrough and verified scope, see
[the user guide](../../docs/synthetic_flow.md).

All data and operations are **SYNTHETIC**. This is a stdlib-only CLI4 provider
behind the existing ASIC adapter, with small retained evidence files. It requires
no PDK, EDA executable, full-flow tools or downloaded Python packages.

The demo also includes a standalone FS2 provider, `simulation_provider.py`, with
adjacent `simulation_wire.py`. Prepare copies both into the demo project and writes
the companion simulation configuration. Explicit seed creates the Testing workspace
and representative pass/failure attempts; ordinary startup/viewing never runs tests.
[Controls, upgrade and evidence](../../docs/synthetic_testing.md).

## Prepare and open

From the repository root, using already-built daemon/client binaries:

```sh
python3 scripts/synthetic-flow-demo.py prepare --dir /tmp/opencode/my-synthetic-demo
python3 scripts/synthetic-flow-demo.py daemon --dir /tmp/opencode/my-synthetic-demo
```

`prepare` requires a **new directory** with an existing parent. Omit `--dir` for
a unique directory under `/tmp/opencode`. It prints the concrete next commands.
The ASIC and simulation provider/scenario files are copied into the project, so that prepared demo
does not depend on repository test fixtures or old temporary evidence.
`daemon` explicitly execs the existing binary in the foreground; Ctrl-C stops it.
Preparation never starts a daemon or builds anything.

In another terminal (the endpoint is read from `discovery/daemon.sexp`):

```sh
python3 scripts/synthetic-flow-demo.py seed --dir /tmp/opencode/my-synthetic-demo
python3 scripts/synthetic-flow-demo.py client --dir /tmp/opencode/my-synthetic-demo
```

`--daemon PATH` and `--client PATH` override the built binary locations.
Seeding also requires the built `terminal/workspaces/export_presets.exe` helper;
use `--preset-export PATH` or `WORKBENCH_PRESET_EXPORT` for a separate build dir.
It exports the actual OCaml Overview/Timing/Testing definitions, not a second
Python layout table. Build it alongside the daemon/client before this walkthrough.
Use `--url http://127.0.0.1:PORT` to connect to an externally started daemon.
Daemon/client convenience launches go through the repository's existing
`scripts/with-switch.sh`; the shell need not already have Dune on PATH. The
switch is `$OPAM_SWITCH` or `5.2.0+ox`, matching that helper's existing default.
HTTP project opening explicitly requests this same `Opam_switch` environment,
including when the daemon was started elsewhere. Direct terminal invocations
must include `--environment opam:5.2.0+ox` (or the chosen switch) to use the same
project-session key. The setup prints a full switch-wrapped plain-client command
after seeding. This uses the existing installed switch; nothing is installed.
`seed` performs real HTTP project opening, flow discovery, registration,
observation, summary/finalization adoption, four FS1 index reads per run, artifact
catalog reads and authoritative workspace selection/layout mutations. The complete
HTTP transcript is saved as `seed-http.json`; `seeded.json` retains exact run refs.
FS2 discovery/Launch/Observe use the same native transport, with stable submission
keys and exact payload/attempt receipts in `simulation-seed.json`. Waiting prints
progress. Two deliberately synthetic attempts yield reports and byte-exact binary
traces; invalid requests remain process failures rather than fabricated case results.
The normal project-open operation uses Workbench's existing Dune workspace
discovery; no project build or test target is requested by this demo.

The selected reference has all six explicit completed stages. The failed candidate
has completed synthesis/floorplan/placement/CTS, failed routing and skipped
signoff. Checklist labels are Synthesis, Floorplan, Placement, CTS, Routing and
Signoff; session/run/evidence and stage reasons retain synthetic provenance.
Select either in the normal run selector. Overview, Timing and Testing use the shared
OCaml presets under `terminal/workspaces/`; the exported definitions are retained
as `workspace-presets.json` with the demo evidence. Their ASIC selectors follow Main;
structured simulation remains project-scoped. Timing/checks show imported live
aggregate evidence; FS1 timing/clocks/physical/routing inspection is available
through the normal Space-c-c inspection commands. Their default stage indexes
are preloaded (timing/clocks signoff, physical placement, routing routing).
Seeding creates missing preset workspaces without duplicate instances after rename.
It applies defaults additively before the first terminal opens; reseeding
preserves existing geometry, pins, hidden tiles, custom/duplicate tiles, context
and arrangement names. Stable preset metadata selects definitions after rename.
Use the terminal's explicit Reset arrangement action to restore preset geometry.
The terminal's checklist `j/k` selects stages; `r` prepares the exact advertised
action. **Launch / Launch and view** in the Space-c-c palette starts a **new run
through that endpoint**, never a restart of a stage in the observed run.

## Provider API

The executable created by setup is `project/synthetic-flow`. Its CLI contracts:

* `--version --json`: CLI4 with `namedflow1=true`.
* `flow list --json`, `flow describe --flow synthetic --json`.
* `flow plan --flow synthetic --profile success|failure --endpoint STAGE --json`.
  Returns `hardcaml-asic.methodology-plan` v1, deterministic plan/bundle identities,
  a retained declared-clock configuration and `hardcaml-asic.stage-plan` v1.
* `flow run` with the same selection, `--expected-plan-identity HASH` and
  `--results-root PATH`: early allocation, terminal observation and execution
  record using execution stage-plan schema 3. The normal adapter's provider,
  toolchain and source-root arguments are accepted. Assignments are rejected.
* `observation inspect ATTEMPT --json`: read-only v2 snapshot with exact stream,
  cursor and stage-plan. `observation read-updates ATTEMPT --stream-id ID
  --after N --json`: cursor-fenced v2 events with explicit stage snapshots.
* `report EXECUTION --json`: report v1 with exact execution, historical plan
  reference and synthesis/checkpoint evidence. Checkpoint identities hash actual
  `segment.json` bytes.
* `inspect EXECUTION --domain timing|clocks|physical|routing --stage STAGE --json`:
  FS1 inspection v1. `--row-id ID --expected-digest HASH` reads detail, rejecting
  stale digests and unknown rows. Execution and inspection source digests hash the
  actual files. Stages without output have explicitly unavailable rows.
* `finalization-inspect ATTEMPT --json`: retained collection receipt. Every seeded
  run with a completed checkpoint has a collection receipt and normalized results,
  including signed synthetic slack, synthesis counts/area and explicit check
  verdicts. The reference's signoff checks pass; the failed/prefix run's signoff
  checks remain unknown. Acceptance is always `not_evaluated`.
* `finalize EXECUTION --operation-store PATH --json`: creates a distinct synthetic
  collection receipt and emits allocation/terminal records for the existing
  finalization adapter. `--accept` is rejected: external postchecks are unsupported.
* `advance ATTEMPT [--cancel]`: explicit mutation, for manual mode.

Stages: `synthesis`, `floorplan`, `placement`, `cts`, `routing`, `signoff`.
Every stage action advertises `{flow: synthetic, profile: <observed profile>,
endpoint: <that stage>, assignments: []}`. Beyond-prefix stages are
`not_requested`. Each launch allocates a unique stream/attempt; idempotency remains
the daemon's existing submission-key behavior. Observation and inspection do not
advance state. Calls, including rejected commands, append to
`project/provider-calls.jsonl`.

Default simulation is six visible stage transitions (1.5 seconds each, about
nine seconds total), long enough to observe with the client's 500ms polling.
Override with `prepare --delay SECONDS` (.01..2). Use
`prepare --manual` for deterministic steps, then run:

```sh
/tmp/opencode/my-synthetic-demo/project/synthetic-flow advance /ABSOLUTE/NEW/ATTEMPT
```

Each command completes the currently running stage and starts the next, or
publishes the terminal outcome. Failure occurs only when the requested prefix
reaches routing. `--cancel` or launcher SIGTERM publishes `cancelled`, with an
`interrupted` execution record. Every run is bounded to 120 seconds, including
manual mode; timeout publishes cancellation. Per-attempt writer locking and
atomic replace prevent partially read stage snapshots. Evidence is immutable
after final publication; only call logging changes on ordinary reads.

Cancellation uses the existing nonblocking daemon lifecycle: cancelling the owned
launcher also stops its automatic observation reader. The provider publishes
`cancelled` on disk, but the daemon may retain the last running checklist and an
observation error until an explicit **Refresh** reconciles that evidence. Wait for
the cancelled operation to finish stopping, then use the normal run Refresh
command (a read-only `Observe` also reconciles stage/status state). This does not
launch another run or resume the cancelled one; automatic convergence after
cancellation is not guaranteed.

## Verification

```sh
# Lightweight standalone provider checks, no daemon/client or Dune invocation:
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-synthetic-flow.py --smoke

# Parent: after serial build, use existing binaries; no build is performed here:
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-synthetic-flow.py --pty \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe
```

The default integration path exercises real HTTP registration, outcomes, explicit
stages, aggregate import, all four FS1 index/detail domains, artifact text pages,
new-prefix launch, duplicate submission and cancellation. `--pty` adds a real
terminal checklist Enter/Esc details, j/k selection and appearance changes with
no producer launches. It selects placement with `jj`, validates `r`'s exact
selection, launches through the normal Launch-and-view palette and requires
exactly one new run and provider launch relative to a complete identity/call
snapshot. It verifies the captured context selection changes exactly once, then
manually advances and observes synthesis → floorplan → placement → completed,
including beyond-prefix `not_requested` states. Old HTTP/cancelled runs cannot
satisfy the new allocation assertion. The harness uses the existing FS0 ANSI
screen reconstruction helper to assert current screen contents, not stale diff
bytes. It retains `daemon.log`, `test-http.json`, `pty.ansi`, per-step screen text,
`pty-verified.json`, result evidence and verification receipts in its printed directory.
Cancellation acceptance waits for launcher/reader lifecycle finalization, then
explicitly observes the cancelled run and requires daemon `cancelled` status,
`Cancelled` requested stages, no observation error and no additional producer
calls or allocations. Its snapshots are retained in `cancellation-verified.json`.
Its directly owned daemon and PTY processes have bounded startup/wait/cleanup.

Provider-only smoke is runnable independently. Full HTTP/PTY acceptance requires
the parent-built binaries; the harness performs no builds or full-flow tool work.
The full command above passed with the existing parent-built binaries on
2026-10-16; retained evidence: `/tmp/opencode/synthetic-flow-ku9weij8`.
Screen assertions normalize presentation casing across skins while protocol
selection, identity, cursor and stage-status assertions remain exact.
This slice supplies illustrative text evidence only: no binary layout/hierarchy,
FS2 suites or real EDA/tool acceptance claims.
