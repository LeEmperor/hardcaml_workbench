---
id: WB-004
title: Core build, bundle emission and verification status
category: project
feature_sets: [FS0, FS1, FS2]
status: closed
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [project-preparation, status, tiles]
depends_on: []
related: [WB-069, WB-001]
---

# WB-004 — Core preparation status

## Request
Original size: **Ticket**. Show core build, bundle-emission and verification
status in a useful tile, optionally with a stage-checklist-like presentation.

**Owner addition, 2026-10-20:** bundle emission / OCaml elaboration should be its
own stage. The requested design includes a named checklist row ahead of `synthesis`,
rather than only part of a separate preparation tile. Both are now implemented.

## Current baseline
Generic build/test jobs and project-driver RTL generation already exist.
The Overview checklist projects explicit physical-stage observations; it must not
turn a successful build into evidence that synthesis or signoff completed.
FS0/FS1 and accepted FS2 delivery remain closed.

## Scope
- Add a compact project-preparation projection for build, declared bundle emission
  and declared verification, retaining operation identity and outcome source.
- Show unavailable, not requested, running, failed and completed independently.
- Link an observed operation to its existing log or artifact surface.
- Reuse checklist styling if useful, with preparation clearly labeled separately.

## Out of scope
New build engines, new verification providers, and physical-stage normalization.
Do not infer bundle emission from an arbitrary successful Dune command.

## Acceptance criteria
1. Each displayed result identifies its project/target/configuration scope and job.
2. Missing bundle capability is unavailable, never implicitly completed.
3. Running, failure and cancellation replace prior status without hiding its history.
4. Preparation rows cannot mark canonical physical stages complete.
5. Existing job logs/artifacts are reachable without resubmitting the operation.
6. The stage checklist shows an **elaboration / bundle emission** row before
   `synthesis`, labelled as preparation. Its status comes only from the real
   generate-RTL/bundle operation.

## Dependencies
Required: delivered supervisor, driver and tile-host contracts; no new ticket blocker.
Related: none required for this bounded projection.

## Estimate rationale
13 points cover semantic projection, scoped status wiring and interaction validation.
Exclude creation of bundle producers or additional simulation adapters.

## Assumptions and decisions needed
Default: one preparation tile with explicit capability gaps, plus the elaboration
row on the checklist (2026-10-20). Agree that row's order with
[WB-069](../evidence/WB-069-timing-checklist-stage.md)'s timing row.
Selected contract: explicitly configured source build followed by the project's
versioned `flow emit` operation, validating the exact selected methodology and bundle.
Generic RTL generation remains separately labelled evidence, not ASIC publication.

## Scope clarification — 2026-10-25

The owner intends an explicitly EDA-less preparation stage: build the OCaml/project
executable with Dune as needed, then run elaboration and Verilog/bundle emission,
without launching synthesis or subsequent physical implementation. Build and emission
retain separate outcomes even when orchestrated as one user-facing stage; build
success alone does not establish emitted output. Building a current executable must
not silently invoke a stale pinned deployment instead.

Existing `hardcaml_asic` emission APIs already support EDA-less emission. The example's
standalone `project emit --json` uses its fixed project declaration; emitting the exact
selected named flow/profile now uses the example's new emission-only `flow emit`
path through existing methodology preparation/publication machinery. Future
resource-mapping/preparation composition
should retain distinct operation identities and outcomes.

Durable preparation receipts/history across daemon restart and discovery/adoption of
externally launched emission are explicitly deferred to the
[preparation-history backlog](../../backlog/README.md#preparation-history-and-external-emission-adoption).
They do not block WB-004's initial supervised operation and UI. Missing session
history must not imply that an operation was never run.

## Delivery and verification — 2026-10-25

Implemented and owner-accepted; closure is recorded below. See
[controls, configuration and evidence](../../project_preparation.md).

- Source build and selected-flow emission are separate supervised jobs with exact
  inputs, outcomes, logs and bundle artifacts; no stale pinned executable fallback.
- Compact preparation tile and typed Elaboration checklist item precede physical
  Synthesis. Unavailable, unrequested/session-unknown, active, failed, cancelled and
  completed states remain distinct, with prior attempts inspectable.
- Project test-command results are labelled as process outcomes. Generic RTL
  observations retain target/configuration identity and never claim ASIC publication.
- Snapshot/action fencing, config revalidation, submission deduplication, cancellation,
  receipt/manifest/file validation and session-only history are covered by tests.
- Full combined build/tests/lint and final native HTTP/PTY checks passed. Real FIFO
  source build/emission, exact profile/overrides, 25 imported artifact reads, verified
  reuse and mismatch rejection passed with zero traced provider/EDA executions.
- No core `hardcaml_asic` change was needed; the example exposes existing methodology
  preparation/publication through the new CLI. Existing resource-preparation edits
  were preserved.

## Owner workflow follow-up — 2026-10-26

The owner confirmed initial functionality and requested consistent staging and
timing. Implemented and automatically verified:

- `r` stages Elaboration inputs without processes, then manual launch uses the exact
  backend receipt. `R` stages and launches immediately, for preparation and physical
  checklist stages. Physical quick launch waits for its exact captured preview.
- Persistent quick-launch preference defaults to launch-and-view; launch without
  switching context is selectable. Preparation creates no ASIC run and retains context.
- Elaboration has an aligned total-preparation duration (build plus emission), live
  while active and frozen at terminal finish when known.
- Stock Overview includes preparation above Synthesis. Explicit default restoration
  from legacy/config-backed layouts is tested at 120x40 and 180x55, retaining IDs,
  pins and contexts; saved layouts are not silently rewritten on reconnect.
- Full combined build/tests/lint and preparation/checklist native HTTP/PTY checks
  pass. Backend tests cover zero-work staging, stale/config-changed tokens and
   duplicate launch receipts. Subsequent owner acceptance is recorded below.

### Palette refinement — 2026-10-26

Implemented action-first names and ranked prefix queries for staged launch-and-view,
selected-stage quick launch, and named synthesis/elaboration quick launch. Preference
titles describe behavior without keybinding names. Named physical launches always
request context viewing while preserving the saved generic quick-launch setting;
elaboration retains context because it allocates no ASIC run. Actual incremental
typing/Enter behavior, preference retention and pending-plan selection/capability
withdrawal pass native HTTP/PTY regression. See the updated
[palette controls](../../project_preparation.md#palette-launch-queries).

### Planned-run presentation refinement — 2026-10-26

Elaboration input plans now use compact lowercase status, endpoint, launch,
flow/profile and assignment rows matching physical planned-run styling. Exact receipt
IDs, paths, environment, provider endpoint and staging explanations move to Enter
details. Ready/stale/consumed/unavailable states retain appropriate roles and icons;
icon-aware wrapping also fixes detail scroll bounds. Combined build/tests/lint pass.

## Owner acceptance and closure — 2026-10-26

The owner confirmed the initial feature and successive staging, palette and visual
refinements work well, then accepted the compact elaboration planned-run display.
WB-004 is **closed, owner-accepted**, including:

- EDA-less current-source build and selected-flow bundle emission, separate outcomes,
  preparation tile, Elaboration checklist row and elapsed-time presentation.
- Stage-only `r`, stage-and-launch `R`, manual launch and persistent context-viewing
  preference, with preparation retaining context because no ASIC run is allocated.
- Action-first palette names/search defaults and explicit named-stage quick launch.
- Compact planned-run summary with full receipt/provenance details on Enter.

Owner workflow acceptance complements the recorded automated checks; it does not
claim every failure/cancellation case was manually repeated. Verification in this
scope remains the project test-command outcome, not an aggregate bundle/signoff
verdict. Session-history limits remain explicit.

Restart/external-emission adoption stays in the linked preparation-history backlog.
Resource-mapping/preparation composition and exact-bundle verification remain later
scope and do not block closure. No implementation acceptance remains open on WB-004.

## References
- [Driver operations](../../../project_integration/driver_protocol.ml)
- [Existing checklist projection](../../../terminal/overview_tiles.ml)
- [Execution foundation](../../fs0_execution_module.md)
