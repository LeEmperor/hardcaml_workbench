---
id: WB-004
title: Core build, bundle emission and verification status
category: project
feature_sets: [FS0, FS1, FS2]
status: partial
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
own stage. It is now a named checklist row ahead of `synthesis`, rather than only
part of a separate preparation tile.

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
TBD: which existing project/provider operation authoritatively means “bundle emitted”;
do not invent a universal bundle lifecycle before that contract is selected.

## References
- [Driver operations](../../../project_integration/driver_protocol.ml)
- [Existing checklist projection](../../../terminal/overview_tiles.ml)
- [Execution foundation](../../fs0_execution_module.md)
