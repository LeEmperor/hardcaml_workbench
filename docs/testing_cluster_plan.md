# FS2 adoption and Testing investigation cluster

Status: **implemented and automatically verified**, 2026-10-17. Tickets:
[WB-034](features/verification/WB-034-fifo-adapter.md),
[WB-032](features/verification/WB-032-test-catalog.md),
[WB-063](features/presentation/WB-063-testing-workspace.md).

Baseline HEAD `849c63b` includes pre-existing unstaged native-indicator and feature
catalog work. Preserve that work in place. The example checkout starts clean at
`2069b6d`. FS2's original milestone remains closed; this is an explicitly activated
adoption/UI extension, not a replacement simulation contract.

## Product outcome

Discover the real FIFO's directed/seeded test catalog, choose exact cases/seed/
parameters, explicitly launch, then investigate a selected attempt and case through
coordinated results, logs and artifact panes. A controlled checker failure must
produce genuine FIFO simulation evidence, not synthetic cases attached to ASIC runs.

## Contracts and boundaries

- Reuse simulation v1 discovery/events/history/rerun/artifact APIs and the existing
  supervisor. No new scheduler, implicit build/discovery/run, or ASIC recipe engine.
- Generic project tests remain separate from structured suites. Process exit0 does
  not imply Passed. Project-scoped simulation does not acquire selected ASIC-run
  provenance. Native waveform rendering and durable full logs remain outside scope.
- Catalog selection captures suite/cases/defaults and exact discovery digest;
  removed/changed choices must not silently retarget a launch. Failed/in-flight
  discovery may display retained catalog but disables launch with a reason.
- New cooperative pane kinds: `simulation-catalog`, `simulation-attempts`,
  `simulation-cases`, `simulation-detail`, `simulation-artifacts`, `simulation-logs`.
  Selection is **client/workspace-local**, separate from ASIC Main. Pane scroll and
  focus remain tile-local. One shared request per workspace, not one per pane.
- The existing `simulation` tile remains a supported independent legacy/full view;
  duplicate standalone tiles retain independent investigation state and old actions.
- Shared Testing definitions compose the new panes with compact Session and generic
  tests/execution access. Apply adds missing tiles, never deletes saved extras or
  changes pins. A fresh Testing arrangement presents the intended default.
- Scope all async responses by client/daemon/project, workspace identity, selected
  attempt, request generation and tile/workspace lifetime. Reconnect preserves
  appropriate selection while invalidating pending work. Artifact export remains
  exact attempt/artifact/hash scoped, with explicit user action.

## Ownership and resource budget

No Git add/commit/push/reset/merge/authorship operations. Preserve live daemons,
canonical ASIC outputs and existing investigations. No physical flow is needed.
Use `scripts/with-switch.sh` for OCaml commands/formatter (from Workbench for sibling
commands). Three agents have **6 build jobs each**, in separate directories;2 remain
reserved. Parent waits for their builds; final serial verification can use20.
Nested provider builds must fit the same allocation. No automatic dependency refresh.

### Agent A — genuine FIFO adapter

Own changes under `../hardcaml_asic_example/`, plus new
`scripts/test-fifo-testing.py` in Workbench for private native acceptance. Read
sibling guidance/status first. Do not edit Workbench terminal modules or docs.

- Reuse actual `Controlled_fifo` and existing independent directed/seeded reference
  stimuli/checker semantics. Preserve ordinary CLI/Dune tests. Add real VCD/report
  capture and an explicit checker-only injected mismatch mode, never a DUT mutation.
- Add a project-owned standalone FS2 provider and strict request/event codec.
  Discovery/runtime perform no builds. Support exact canonical seed/parameters,
  passing directed/seeded cases and deterministic failure with report/trace evidence.
- Provide an explicit conservative build/install/configuration helper using persistent
  `.dev/` binaries, refusing to overwrite unrelated config. Adopt the real example's
  FS2 companion config without changing ASIC config/results or live sessions.
- Build under `/tmp/opencode/testing-cluster-fifo` at `-j6`; copy verified executables
  into a persistent generation/location before writing provider configuration.
- Standalone proof plus private HTTP/PTY acceptance should use the actual project
  root and provider with separate daemon/client state and no real ASIC operations.

### Agent B — pure catalog and investigation model

Own new `terminal/simulation_catalog.ml{,i}` and
`terminal/testing_workspace.ml{,i}`, plus `terminal/simulation_view.ml` and its
tests. Do not edit host/main/dune/layout; C integrates those. Publish interfaces
early so C can consume them. Build `/tmp/opencode/testing-cluster-model` at `-j6`.

- Catalog model: stable suite/case cursor and explicit selected case subset, filters,
  exact digest validity, validation reason, declared defaults/parameters. Pure
  browsing/toggling must not mutate attempt investigation or launch anything.
- Extend `Simulation_view.Form.create` compatibly with optional captured selection
  so catalog subsets use the existing multi-step seed/parameter/confirmation flow.
- Testing model: cooperative pane kinds above, shared Simulation_view state plus
  catalog and selected artifact; project-only identity and reset/reconnect behavior.
  Supply pane-specific typed rows using canonical row metadata, not duplicated text
  parsing. Detail starts with concise outcome/case failure and captured inputs;
  artifacts/logs remain separate. Full IDs/provenance are available in detail.
- Model tests cover stale discovery/subset edits, missing/changed cases, exact
  selection, independent workspace states, attempt/case/artifact changes and late
  responses. Retain existing Simulation_view.rows and independent tile behavior.

### Agent C — host/UI composition and dispatch

Own `terminal/main.ml`, `terminal/workspace_host.ml`, `terminal/host_view.ml`,
`terminal/workspaces/`, `terminal/dune`, and focused new UI tests/harness
`scripts/test-testing-workspace.py` if useful. No sibling/provider edits.
Build `/tmp/opencode/testing-cluster-ui` at `-j6`.

- Integrate B's models with client/workspace-local selection and shared request
  polling; retain standalone `simulation` behavior and existing native icons.
- Expose catalog browsing/filtering, suite/case subset selection and explicit launch
  form using current digest. Preserve authoritative disabled reasons and captured
  palette commands. Discovery is explicit; navigation/render never invokes it.
- Compose useful default Testing layout at120x40 and180x55 with bounded narrow
  fallback. Avoid ASIC run selector dominating project-only simulation investigation.
- Attempt/case/artifact selection updates cooperative panes; per-pane scrolling
  does not change selection. Logs read only the exact selected attempt job and
  honor historical unavailability. Failed-case rerun/export/viewer remain captured.
- Native UI tests cover new pane workflows, filters, subset forms, independence,
  stale transitions, generic tests separation and additive preset preservation.

### Coordinator

Own shared plan, feature-ticket/status/docs reconciliation, integration review and
final verification. Resolve interfaces without concurrent edits. Refresh prepared
real-demo Workbench binaries only after checks; never restart user processes or
seed/reselect the live investigation. Record exact evidence and honest limits.

## Verification gates

1. Real FIFO standalone pass/failure/VCD/report/seed proof, no physical tools.
2. Pure catalog/model and host tests; current full format/lint/runtest/build.
3. Actual real-FIFO public HTTP plus PTY catalog/launch/investigation/targeted-rerun
   acceptance in private state; records must retain actual simulator evidence.
4. Synthetic tests for late responses, missing/failed discovery, changed catalog,
   artifact unavailability and multi-workspace/tile independence as applicable.
5. Existing FS2, checklist launch, native indicator and interrupt regressions as
   affected. Read flags; allow300–600 seconds for PTY, not unlimited parallel jobs.
6. Persistent real provider installation/config and updated daemon/client copies;
   daemon/client restart only when owner decides active work is finished.

## Progress and evidence

- [x] Inspect current dirty Workbench baseline and clean example checkout.
- [x] Genuine FIFO provider and persistent adoption.
- [x] Catalog and cooperative investigation model.
- [x] Host/action/renderer and shared Testing definition integration.
- [x] Real/synthetic native acceptance and regression checks.
- [x] Ticket/status/user guide updates and binary refresh.

## Final implementation and evidence

User controls and exact reproduction commands: [Testing workspace guide](testing_workspace.md).

### Genuine project adoption

The example's `simulation/fifo_sim.ml` uses the real DUT and independent list model,
with existing directed traffic and an expanded full-uint64 seeded generator. Native
VCD and S-expression reports retain exact seed/parameters/checker observations.
`checker=mismatch` changes an expected value only; matching normal/failure runs
produce identical DUT waveforms. Ordinary CLI/Dune tests preserve the single-int
seed behavior. No dependency upgrade or physical flow was required.

Provider generation:
`hardcaml_asic_example/.dev/fifo-simulation/af97d67d923441a0a654e27b6afd728f/`.
Root companion configuration and installation ownership manifest point to persistent
copies. The helper refuses unrelated/edited configuration; runtime does not build.

### Catalog and investigation

`Simulation_catalog` owns declared suite/case browsing, explicit subsets, filters,
defaults and stale-discovery validation. `Testing_workspace` owns shared attempt/
case/artifact selection and typed per-pane rows. Host state is workspace/client-local;
the six panes share one request stream, while the legacy `simulation` tile remains
independent. Generic project tests and execution remain available as process views.

Cursor-follow operates on typed selected-row metadata after cell wrapping. Long
catalog/history/artifact lists keep selection visible; manual tile scroll pauses
follow. Full artifact identity/digest is in Detail, not repeated in every list row.

Catalog palette/keyboard commands capture exact suite, selection, digest and
workspace lifetime. Changed inputs/discovery/defaults or replaced workspace reject
the captured action before opening a form; disabled actions carry only a reason.
The existing backend validates the captured launch digest/config again. Legacy log
toggle is exposed only for the standalone tile; cooperative Logs has its own pane.

### Final verification

Full normal build, repository-wide format/lint and full tests passed serially at
`-j20` after final capture-fence integration. Agent builds used 6 jobs each in separate
directories; parent builds ran after agents stopped, within one 20-job pool.

| Proof | Result and `/tmp/opencode` evidence |
| --- | --- |
| Genuine FIFO standalone/HTTP/new+legacy PTY | `fifo-testing-wx4xhzjp/`:21 cooperative assertions and6 geometry checks; actual catalog-form pass/failure, exact report/VCD bytes, rerun lineage and stable multi-case selection |
| Cooperative synthetic HTTP/PTY | `testing-workspace-w56bs6_c/verified.json`:15 checks |
| Synthetic demo upgrade and legacy coverage | `synthetic-flow-58wxhzay/testing-result.json`:44 checks |
| Native indicators/Off | `terminal-indicators-06485dae9a88/result.json`:351 checks |
| Independent FS2 counter/native regression | `fs2-native-xh0meb_6/result.json`:45 checks |
| Checklist launch full matrix | `checklist-workflow-5eba10136566/result.json`:61 checks |
| Interrupt/restoration | `workbench-terminal-interrupt-268f0z3w/results.json`:5/5 |

The broader regression runs preceded the final catalog-capture-only tightening;
normal full build/format/lint/tests and both real/synthetic cluster native suites
were rerun afterward. Their final receipts above supersede intermediate cluster
results; unrelated suites were not rerun without a new regression concern.

The real proof additionally has 8 valid standalone runs/12 case outcomes and 12
invalid requests rejected before events/artifacts. Directed evidence checks 7,330
edges/87,955 values; the long expanded-seed example checks 20,018 edges/240,211 values.
Original project tests pass 7,330 directed edges and 20,017 original seeded edges.
These are distinct documented stimulus mappings, not contradictory counts.

Model/reducer tests cover changed/removed catalogs and captured defaults/subsets,
late responses, workspace lifetimes and navigation across 25 attempts, 40 artifacts
and up to 1,024 cases. Native tests demonstrate independent workspaces, additive
preservation of hidden legacy extras/pins and explicit unavailable logs after
daemon restart. This is not an exhaustive network fault or multi-monitor matrix.

### Resolved intermediate findings and remaining limits

- A prior prebuilt-client multi-case selection issue did not reproduce after current
  response merging; both real cases were checked repeatedly across polling.
- The first wide PTY snapshots matched old 120-column frames immediately after resize.
  Final harnesses send SIGWINCH and assert actual right/bottom borders and footer at
  120x40 and 180x55. Earlier wide captures are superseded, not acceptance evidence.
- Existing synthetic/indicator harnesses now assert the cooperative default and add
  a separate legacy tile explicitly for old full-view coverage; no producer or
  identity assertions were removed.
- WB-032 and WB-034 are delivered with automated evidence. WB-063 implementation is
  complete; its status remains partial solely for the explicit owner visual/workflow
  review. No owner aesthetic approval is inferred from PTY assertions.
- Full durable logs, embedded waveforms, sweeps, new simulation schemas and automatic
  ASIC acceptance remain separately ticketed. Existing live sessions/state and
  canonical ASIC results were preserved; no Git staging/commits/pushes occurred.

### Prepared binaries

Normal binaries and persistent real-demo daemon/client/exporter copies are updated.
Receipt in the example:
`.dev/workbench-real-demo/receipts/refresh-binaries-3dc29d7ad10a45c58a856bab877984b4/`.
No process was restarted. After active jobs finish, restart the matching pair,
create/open Testing and explicitly discover the FIFO suite. Do not reseed the live
ASIC investigation to enable testing; the FS2 configuration is already present.
