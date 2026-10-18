# FS2 followups after milestone closure

## Canonical ticket crosswalk — 2026-10-17

The [WB catalog](../features/README.md) now owns per-feature scope, estimates,
dependencies and open decisions. The original FS2-F headings below remain stable
historical activation notes so existing links keep working. They are not a second
implementation queue. The accepted FS2 milestone stays closed.

| Earlier followup | Current ticket(s) |
| --- | --- |
| FS2-F01 FIFO adoption | [WB-034](../features/verification/WB-034-fifo-adapter.md), delivered with genuine FIFO/native proof; [controls](../testing_workspace.md) |
| FS2-F02 trace streaming | [WB-040](../features/infrastructure/WB-040-trace-streaming.md) |
| FS2-F03 slow storage | [WB-043](../features/infrastructure/WB-043-slow-storage.md) |
| FS2-F04 uncertain submission/reconnect | [WB-062](../features/verification/WB-062-submission-recovery.md); same-session local-state preservation already improved in FS3 |
| FS2-F05 logs/budgets | [WB-041](../features/infrastructure/WB-041-durable-logs.md) and [WB-042](../features/infrastructure/WB-042-resource-budgets.md) |
| FS2-F06 load/usability | [WB-044](../features/infrastructure/WB-044-load-acceptance.md) remains; [WB-063](../features/presentation/WB-063-testing-workspace.md) implementation verified, owner composition review pending |
| FS2-F07 generated/gate-level simulation | [WB-035](../features/verification/WB-035-generated-rtl-simulation.md) and [WB-036](../features/verification/WB-036-gate-level-simulation.md) |
| FS2-F08 replay | [WB-037](../features/verification/WB-037-archived-replay.md) |
| FS2-F09 waveforms | [WB-028](../features/verification/WB-028-waveform-viewer.md) |
| FS2-F10 catalogs/sweeps/comparisons | [WB-032](../features/verification/WB-032-test-catalog.md) and [WB-030](../features/verification/WB-030-seed-parameter-sweeps.md) cover catalog UI/test sweeps. [WB-012](../features/evidence/WB-012-run-comparison.md) supplies reusable pairing/quantity rules, not case regression diffing. Arbitrary generated-case contracts and suite/case/seed-aligned cross-attempt comparison remain deferred here, outside these initial estimates. |
| FS2-F11 acceptance bridge | [WB-038](../features/verification/WB-038-acceptance-bridge.md) |
| FS2-F12 setup/starters | [WB-039](../features/project/WB-039-simulation-setup.md) for configuration generation; shared Testing starter/templates are already delivered by FS3 |

The new owner requests also include [formal proof](../features/verification/WB-025-formal-verification.md),
[design/build sweeping](../features/exploration/WB-031-design-space-sweeper.md) and
[Quick-Harn comparison](../features/exploration/WB-033-quick-harn-playground.md).
They are new proposed scopes, not retroactive requirements of the closed milestone.

## Original closure and activation notes

Recorded 2026-10-16. The agreed substantial FS2 milestone is **delivered, accepted
and closed**. [Acceptance](../fs2_acceptance.md) records automated evidence and the
owner's scoped manual confirmation. The items below preserve additional scope;
none is an outstanding gate on that milestone. Activate one by adding its concrete
scope to the construction plan rather than reopening all of FS2.

## Recommended next adoption task

### FS2-F01 — FIFO project adoption

**Delivered 2026-10-17:** [actual FIFO/catalog/Testing evidence](../testing_workspace.md).
The original trigger/acceptance below describes the now implemented adoption.

**Trigger:** the owner wants to use structured simulation on `hardcaml_asic_example`.
Expose its actual directed/seeded FIFO Cyclesim tests through the existing provider
contract, with project-owned failure reports and traces. Keep changes small and
retain ordinary CLI/Dune use.

**Acceptance:** actual FIFO directed and seeded success, a deterministic failure,
inspectable report/trace, and a targeted rerun preserving seed/parameters and parent
identity through native HTTP and terminal input. No ASIC physical flow is required.
This follows the delivered real counter provider; it does not replace its independent
contract/acceptance fixture.

## Delivery refinements

### FS2-F02 — Large-trace streaming

**Trigger:** a real waveform exceeds the 64 MiB limit or export memory is material.
Stream to a private file with incremental hashing and bounded memory; choose new
transport/storage limits explicitly rather than silently removing the current cap.

**Acceptance:** measured peak memory, exact digest/bytes, explicit limits, cancellation
and timeout cleanup, changed/missing-page rejection, and viewer launch only after
complete verified publication. Preserve existing ASIC handoff behavior where shared.

### FS2-F03 — Slow-storage responsiveness

**Trigger:** measured capture/history/fsync delays affect input, queries or cancellation.
Move remaining synchronous artifact capture, metadata persistence, loading and pruning
off the Async event loop while preserving serialized reservations and atomic records.

**Acceptance:** inject slow I/O and measure query/cancel responsiveness; retain durable
idempotency, partial cancellation results, budget enforcement and corruption behavior.

### FS2-F04 — Reconnect and uncertain-submission recovery

**Trigger:** locating an accepted attempt after a lost/superseded response is cumbersome.
Make pending submission identity/reconciliation visible without automatically creating
another attempt. Preserve investigation selection and improve history-page restoration.

**Acceptance:** delayed/lost receipt, reconnect and navigation races recover the exact
accepted attempt; no duplicate launch, stale retargeting, or replay after daemon restart.

### FS2-F05 — Durable logs and output budgets

**Trigger:** historical failure investigation needs full logs, or producer/log disk use
needs stronger bounds. Define log retention, stream/offset indexing, per-job byte limits,
temporary-output policy and eviction behavior separately from normalized test records.

**Acceptance:** restart-persistent bounded stdout/stderr if activated, explicit truncation
and eviction, honest missing logs, and bounded disk use under noisy/failed producers.
Existing normalized history/artifact retention must remain independent.

### FS2-F06 — Multi-client/load acceptance and usability

**Trigger:** actual simultaneous users, larger regressions, or specific navigation feedback.
Extend measured concurrent-client/high-event-volume/reconnect coverage; improve forms,
failure navigation and layout based on observed tasks rather than a speculative redesign.

**Acceptance:** recorded latency/memory workload, independent selections, shared execution
without duplicate launches, hide/reopen without cancellation, usable failure scrolling,
and scoped owner review of changed interactions.

## Additional capabilities

### FS2-F07 — Generated-RTL and gate-level adapters

**Trigger:** a real project needs simulation of named generated or physical outputs.
Implement a concrete adapter and explicit input selection/staging. Consume exact
netlist/build/output/collateral references; never infer association from viewed ASIC run.

**Acceptance:** a real simulation records the actual consumed inputs, proves linkage to
the claimed output, rejects stale/missing inputs, and supports correctly attributed
reruns/artifacts. Current RPC provenance validation alone is not this demonstration.

### FS2-F08 — Archived-build replay

**Trigger:** original-input reruns on the current project are insufficient.
Specify source/build/tool/environment capture and retention, plus an explicit replay
mode distinct from current-project rerun.

**Acceptance:** replay uses the retained original identities after the working project
changes; missing retained inputs fail explicitly rather than falling back to current
inputs. Do not claim reproducibility merely from seed preservation.

### FS2-F09 — Embedded waveforms

**Trigger:** external viewer handoff cannot serve a concrete debugging workflow.
Scope signal selection, time navigation and lazy trace access, with format/size bounds
and exact attempt/case provenance. This is separate from already delivered trace export.

**Acceptance:** real waveform navigation on a declared format, bounded loading and
responsive interaction, exact identity on selection changes, and explicit unsupported
formats. Coordinate with the general waveform/graph backlog rather than duplicate it.

### FS2-F10 — Richer regression catalogs and comparisons

**Trigger:** a project needs dynamic cases, seed sweeps, or cross-attempt regression
comparison beyond v1's predeclared catalog and one seed per submission.

**Acceptance:** a versioned compatible extension with stable generated-case identities,
bounded scheduling/events, explicit seed expansion and captured inputs. Comparisons
align actual suite/case/input identities and do not equate absent results with passes.

### FS2-F11 — ASIC acceptance evidence bridge

**Trigger:** the adopted ASIC acceptance policy explicitly requires FS2-produced results.
Define evidence import, provenance, completeness and policy ownership; simulation case
success must not automatically become an ASIC signoff verdict.

**Acceptance:** an explicit acceptance operation consumes verified exact simulation
evidence, with passing/failing/missing/stale cases tested and the original process,
simulation and ASIC verdicts preserved separately.

### FS2-F12 — FS3 setup and starter-workspace integration

**Trigger:** FS3 adoption work needs convenient simulation configuration and layouts.
FS2 supplies the provider configuration/view identifiers; FS3 exposes optional setup
and portable workspace templates without changing simulation semantics.

**Acceptance:** generated configuration round-trips through the FS2 parser, project-only
operation remains valid, templates preserve no accidental attempt/run selection, and
existing-project initialization does not overwrite local configuration.
