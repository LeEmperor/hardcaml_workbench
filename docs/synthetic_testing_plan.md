# Synthetic Testing workspace and roomier Session layouts

Activated from owner request: the synthetic demo should open Overview, Timing and
Testing by default; Testing should have useful clearly synthetic FS2 data; Timing
and Testing Session/sidebar regions should be less cramped.

## Scope and rules

- Preserve the current uncommitted frontend/example work and all live demo state.
  No Git staging, commits, pushes, resets or merges.
- Up to two implementation agents, each2 build jobs, separate build dirs under
  `/tmp/opencode/testing-{provider,layout}`. Final parent checks serial at2.
- No ASIC/EDA or hardware simulation is needed: this is explicitly synthetic test
  data through the real existing FS2 provider/supervisor/RPC contract.
- Keep run context and project-scoped simulation independent; no manufactured ASIC
  association, acceptance verdict or inferred cases from human log output.

## A — synthetic provider and seed lifecycle

Own new `demo/synthetic_flow/simulation_provider.py` and self-contained wire helper,
`scripts/synthetic-flow-demo.py`, new native acceptance script and relevant synthetic
harness changes. Prepare copies all provider dependencies into the demo project and
writes optional FS2 companion config using the actual Python executable.

Supply bounded declared suites/cases, deterministic seeds/parameters, passing and
failing outcomes, readable labeled logs/reports and an explicitly synthetic trace
artifact. No dependency on a repo test fixture after prepare. Live events and reruns
use normal job supervision; process failure and semantic failure stay distinct.

Seed creates missing Testing using the exported OCaml preset and stable preset IDs,
then applies definitions additively. Do not duplicate Testing on repeated seed or
rename, overwrite custom workspaces, erase pins, or create a second layout registry.
Explicit seed discovers FS2 suites and submits two labeled representative attempts
(pass and failure) through `/api/v1/simulation`, using stable idempotency keys. Poll
boundedly for results, log useful progress, retain receipts. Ordinary daemon/client
startup and viewing must not launch tests; repeated seed within retained history
must not duplicate attempts. No direct writes to canonical daemon test records.

An existing prepared demo may be missing simulation config/provider files. Provide
an explicit additive upgrade path (seed can install missing owned demo files after
verifying the synthetic manifest, but must not overwrite a user's unrelated
simulation config). Do not require wiping saved layouts or evidence. Use clear
version/ownership checks and actionable conflict errors. The real ASIC launcher
and real example configuration must remain untouched.

## B — Timing/Testing layout width

Own `terminal/workspaces/timing.ml`, `testing.ml`, workspace geometry tests and
necessary existing Timing geometry assertions. Keep Timing Paths/Detail/Provenance
topology intact; widen Session from its hardcoded30-cell region to approximately
one third of a normal120-column viewport while preserving a usable selector.
Testing's left-side region should likewise be approximately one third, with wider
Session/generic-test content and a large FS2 simulation panel. Keep source-level
proportion/height settings clear and reuse Weighted_columns, rather than hardcoded
terminal coordinates. Preserve extras/pins/custom tiles and narrow/zoom fallback.

## Acceptance

- Exported definitions populate all three default synthetic workspaces. Repeated
  seed and renamed Testing keep one preset instance and unchanged saved custom data.
- Real daemon/client show seeded FS2 success/failure, cases/seeds/parameters, logs,
  available report/trace artifacts and targeted rerun with original inputs/new job.
- No new test runs on read/navigation/theme/client restart. Repeated seed uses exact
  existing reservations. Old demo upgrade works without replacing user config.
-120x40 and larger screenshots show widened Timing/Testing Session and usable data;
  tiny viewport geometry stays in bounds and preserve all instances/fallback.
- Existing synthetic ASIC launch/cancel, Timing investigation, FS2 and interrupt
  checks remain meaningful. Final format/lint/full tests/build serial at2.

## Status

**Implemented and verified,2026-10-17.** Final normal full format/lint/tests/build
passed serially at2. Synthetic native HTTP/PTY passed at
`/tmp/opencode/synthetic-flow-kkw_d303/`, including two seeded attempts, explicit
rerun and upgrade/restart preservation. Real-demo binary copies were refreshed and
actual-example native acceptance passed independently. See
[controls, upgrade and both launch pairs](synthetic_testing.md).
Chronological handoffs below retain intermediate verification details.

### B handoff — roomier Timing/Testing layouts (2026-10-17)

- Changed `terminal/workspaces/timing.ml` and `testing.ml` to use existing
  `Common.Weighted_columns`: Timing top Session:selector = 1:2, Testing full
  sidebar:main = 1:2. Exported definitions keep their stable preset IDs and tile
  membership. No additional registry or layout API is required by A.
- Source policy is named constants: Timing `session_weight`, `selector_weight`,
  `session_min_width`, `session_height`, `selector_height`; Testing
  `sidebar_weight`, `main_weight`, all panel minimum heights, and
  `simulation_weight` (3; execution/logs retain default weight 1).
- Timing keeps Paths on the left and Detail above Context on the right. Testing
  keeps Session above project-tests on the left, and selector above FS2,
  execution, logs on the right. Existing resolver/fallback and host policies
  continue to handle missing/hidden membership, duplicates, custom extras,
  pins/requested geometry and zoom. Overview and runtime layout code were not
  changed by B.
- Added two geometry tests in `terminal/workspaces/test_workspaces.ml` covering
  80x24, 120x40, 180x55, bounds/non-overlap/minima, Timing topology, visible FS2,
  and sparse/shuffled membership with duplicate/custom extras. Updated only the
  Session/selector width assertion in `terminal/timing_workspace.ml`; its
  pre-existing user changes remain intact.

Expected acceptance geometry (zero gutter, terminal height minus two global
header/footer rows, framed tile dimensions):

| Terminal | Session / selector | Timing investigation | Testing data |
| --- | --- | --- | --- |
| 80x24 | Existing narrow grid fallback | All 6 tiles retained, width >=24, height >=6 | All 7 tiles retained including FS2, width >=24, height >=6 |
| 120x40 | 40x7 / 80x7 at y=1 | Paths 48x30 at (0,8); Detail 72x17 at (48,8); Context 72x13 at (48,25) | project-tests 40x30 at (0,8); FS2 80x15 at (40,8); execution 80x7 at (40,23); logs 80x8 at (40,30) |
| 180x55 | 60x7 / 120x7 at y=1 | Paths 72x45 at (0,8); Detail 108x26 at (72,8); Context 108x19 at (72,34) | project-tests 60x45 at (0,8); FS2 120x24 at (60,8); execution 120x10 at (60,32); logs 120x11 at (60,42) |

Passed, serial commands using the exact installed switch and isolated build dir:

```sh
opam exec --switch=5.2.0+ox -- ocamlformat --check terminal/workspaces/timing.ml terminal/workspaces/testing.ml terminal/workspaces/test_workspaces.ml terminal/timing_workspace.ml
opam exec --switch=5.2.0+ox -- dune build --build-dir /tmp/opencode/testing-layout -j 2 terminal/workspaces/export_presets.exe
opam exec --switch=5.2.0+ox -- dune runtest --build-dir /tmp/opencode/testing-layout -j 2 terminal/workspaces
opam exec --switch=5.2.0+ox -- dune runtest --build-dir /tmp/opencode/testing-layout -j 2 terminal
opam exec --switch=5.2.0+ox -- dune build --build-dir /tmp/opencode/testing-layout -j 2 terminal/main.exe @terminal/lint
```

A can consume the same `Timing.definition` / `Testing.definition` through
`terminal/workspaces/export_presets.exe` and use the dimensions above for native
acceptance. Provider/seed/native harness integration remains with A/coordinator.

### A handoff — self-contained synthetic FS2 and native acceptance (2026-10-17)

Implemented `demo/synthetic_flow/simulation_provider.py` and adjacent
`simulation_wire.py`; `prepare` copies both into `project/synthetic-provider/`.
They require only the Python standard library. No repository fixture import or
hardware/EDA process is involved. The strict existing FS2 v1 catalog declares
`synthetic-checks`, cases `reset-sequence`, `seeded-pattern`, `injected-mismatch`,
uint64 seeds, `pattern=walking|alternating`, and `steps=8|16|32`. Each selected case
has flushed monotone structured progress, a clearly labeled JSON report and binary
`synthetic-trace` (including NUL/non-UTF8/CRLF). `injected-mismatch` deterministically
fails semantically; valid complete runs always exit 0. Invalid requests fail the
process rather than manufacturing case results. No ASIC association is supplied.

Lifecycle/API:

- `prepare` writes all five required fields of
  `project/hardcaml-workbench-simulation.sexp`, with the actual absolute Python
  executable and absolute copied-provider argument; discovery/run timeouts 10/20s.
- Only explicit `seed` installs/upgrades and calls `/api/v1/simulation` Discover
  and Launch. Ordinary daemon/client startup and reads do not seed or run tests.
- Discover completion is polled against its exact existing supervisor job;
  attempts are explicitly polled with `Observe` (the shared client's ASIC `wait`
  semantics do not apply to simulation). Polls are bounded to 30s per phase and
  notices are flushed at least every two seconds while waiting. Import notices
  also identify the retained synthetic ASIC runs before FS1 imports.
- Stable root-scoped keys are `synthetic-fs2-v1-pass` (seed 42, walking/8,
  reset-sequence+seeded-pattern) and `synthetic-fs2-v1-failure` (seed 314159,
  alternating/16, seeded-pattern+injected-mismatch).
  `simulation-seed.json` atomically stores exact launch payloads **before** RPC,
  then attempt/job receipts and completed details. Retrying uses the exact original
  payload even after config/catalog revisions, preserving active/finished durable
  reservations. A stale digest is refreshed only after the server explicitly
  rejects it after reservation lookup (never after a conflicting key error).
- Workspace bootstrap uses exported stable IDs, creates missing Overview/Timing/
  Testing, then applies all three exported definitions additively. A custom name
  collision gets a distinct display name; renamed preset instances remain the same
  instance. Existing tiles, requested geometry, pins, custom workspaces, selected
  runs/selection revisions and zoom are retained. Initial reference selection is
  initialized only for a first seed with an empty context.
- Shared HTTP client now accepts tuple record entries, emits valid UTF-8 sexps,
  and retains typed HTTP error bodies so stale-digest recovery is precise.

Upgrade/control commands (no implicit build):

```sh
python3 scripts/synthetic-flow-demo.py prepare --dir /tmp/opencode/NEW_DEMO
python3 scripts/synthetic-flow-demo.py daemon --dir /tmp/opencode/NEW_DEMO --daemon /ABS/daemon/main.exe
python3 scripts/synthetic-flow-demo.py seed --dir /tmp/opencode/NEW_DEMO --preset-export /ABS/terminal/workspaces/export_presets.exe
python3 scripts/synthetic-flow-demo.py client --dir /tmp/opencode/NEW_DEMO --client /ABS/terminal/main.exe
```

For an older prepared demo, use that same explicit `seed --dir EXISTING_DEMO`
command after starting its daemon. It verifies the original synthetic manifest
label/roots, preflights every destination, then adds missing files/config without
touching state/evidence. `manifest.json` records FS2 owner/version and per-file
SHA256. Identical or unmodified owned files can be upgraded; unrelated/edited
config/provider files and symlinks are refused before any destination is written.
The error identifies the path and asks to preserve it/use a new directory or
explicitly relocate the conflict. No wipe/migration of saved layouts is needed.

Testing controls: switch to Testing, Tab to focus the simulation tile, then
`Space c c` → `Simulation: Reopen … synthetic-checks`, `Simulation: Select case …`,
`Simulation: Rerun case … (original inputs; current project)`, and
`Simulation: Toggle stream-labelled job logs`. Zoom focused tile when inspecting
lower report/trace/log sections at 120x40; unzoom restores the widened Session.
Artifact reads use the existing hash-fenced `Read_artifact_bytes` API, not a text
conversion. Reruns go through the existing supervisor and retain parent identity,
original seed/parameters and selected case subset, with a new job/attempt.

Passed native evidence:

- `/tmp/opencode/synthetic-flow-wy_46b8q/`: final new native HTTP/PTY acceptance,
  `testing-result.json`, `testing-http.json`, `simulation-seed.json`,
  `standalone-verified.json`, `upgrade-verified.json`, exact exported report/trace
  bytes, stdout/stderr log receipts, and `pty-rerun.json`. ANSI + reconstructed
  screen captures `pty-120x40-{overview,timing,testing,failure,selected-case,logs,
  rerun,testing-rerun-full,restart}` and `pty-180x55-{overview-large,timing-large,
  testing-large,failure-large}` use B's widened layouts. Includes active-key retry,
  visible live progress, config/catalog revisions, stale unreserved receipt,
  renamed Testing reseed, missing Testing/custom-name collision, exact extra tile
  pin/geometry and context preservation (including explicitly cleared selection),
  read/theme/client-restart non-launch,
  daemon-restart durable retry and no duplicate seed attempts. Exactly two seeded
  attempts plus one explicit PTY targeted rerun.
- `/tmp/opencode/synthetic-flow-xy0yuwys/`: existing synthetic-flow provider +
  real HTTP/PTY launch/Timing/ASIC cancellation regression passed. Its supervisor
  oracle now requires exactly one simulation discovery and two completed run jobs
  after fresh seed, then unchanged supervisor IDs during read-only browsing and
  planning; it does not relax generic-job expectations into an allow-all scope.
- `/tmp/opencode/workbench-terminal-interrupt-dxuryee7/`: all five raw Ctrl-C
  regression cases passed, no jobs/artifacts created.

Commands completed using source after B's layout changes and serial build phases
at `-j 2`, all in `/tmp/opencode/testing-provider`:

```sh
bash scripts/with-switch.sh dune build --build-dir /tmp/opencode/testing-provider -j 2 daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
python3 scripts/test-synthetic-testing.py
python3 scripts/test-synthetic-flow.py --pty --daemon /tmp/opencode/testing-provider/default/daemon/main.exe --client /tmp/opencode/testing-provider/default/terminal/main.exe --preset-export /tmp/opencode/testing-provider/default/terminal/workspaces/export_presets.exe
bash scripts/with-switch.sh python3 scripts/test-terminal-interrupt.py --daemon /tmp/opencode/testing-provider/default/daemon/main.exe --client /tmp/opencode/testing-provider/default/terminal/main.exe
bash scripts/with-switch.sh dune runtest --build-dir /tmp/opencode/testing-provider -j 2
bash scripts/with-switch.sh dune build --build-dir /tmp/opencode/testing-provider -j 2 @lint daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
git diff --check
```

Python syntax checks passed for all six provider/helper/demo/acceptance files.
`--smoke` on the new harness exercises copied stdlib-only provider and legacy
upgrade/conflict checks; `--skip-pty` is diagnostic only. Neither harness builds.
No A blockers. Coordinator can review the retained captures/results and run final
combined checks if further source changes land. A did not edit terminal OCaml or
layouts and performed no Git staging/commit/push/reset operations.
